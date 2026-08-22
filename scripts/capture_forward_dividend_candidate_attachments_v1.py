from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.forward_dividend_acquisition_v1 import (
    CASH_DIVIDEND_CANDIDATE,
    PROVIDER_COMMIT,
    PROVIDER_REPOSITORY,
)

SCHEMA = "idx_trade_forward_dividend_attachment_capture_v1_1"
DISCOVERY_SCHEMA = "idx_trade_forward_dividend_announcement_capture_v1"
ALLOWED_HOST = "www.idx.co.id"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_provider(checkout: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )

    head = proc.stdout.strip()

    if head != PROVIDER_COMMIT:
        raise RuntimeError(
            f"provider commit mismatch: {head} != {PROVIDER_COMMIT}"
        )

    provider_src = checkout / "python" / "src"

    if not provider_src.is_dir():
        raise RuntimeError(
            f"provider python/src missing: {provider_src}"
        )

    return provider_src


def validate_attachment(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise RuntimeError("ATTACHMENT_ROW_INVALID")

    filename = str(row.get("pdf_filename") or "").strip()
    url = str(row.get("full_save_path") or "").strip()

    if not filename:
        raise RuntimeError("ATTACHMENT_FILENAME_MISSING")

    if Path(filename).name != filename:
        raise RuntimeError("ATTACHMENT_FILENAME_UNSAFE")

    if not filename.lower().endswith(".pdf"):
        raise RuntimeError("ATTACHMENT_FILENAME_NOT_PDF")

    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise RuntimeError("ATTACHMENT_URL_NOT_HTTPS")

    if parsed.hostname != ALLOWED_HOST:
        raise RuntimeError("ATTACHMENT_URL_HOST_INVALID")

    if not parsed.path:
        raise RuntimeError("ATTACHMENT_URL_PATH_MISSING")

    return {
        "pdf_filename": filename,
        "url": url,
        "original_filename": str(
            row.get("original_filename") or ""
        ),
        "is_attachment": bool(row.get("is_attachment")),
    }


def select_exact_candidate(
    discovery: dict[str, Any],
    *,
    ticker: str,
    announcement_id: str = "",
    announcement_number: str = "",
) -> dict[str, Any]:
    announcement_id = str(
        announcement_id or ""
    ).strip()

    announcement_number = str(
        announcement_number or ""
    ).strip()

    if bool(announcement_id) == bool(announcement_number):
        raise RuntimeError(
            "CANDIDATE_SELECTOR_EXACTLY_ONE_REQUIRED"
        )

    candidates = discovery.get("candidates")

    if not isinstance(candidates, list):
        raise RuntimeError(
            "DISCOVERY_CANDIDATES_INVALID"
        )

    matches = []

    for row in candidates:
        if not isinstance(row, dict):
            continue

        row_ticker = str(
            row.get("ticker") or ""
        ).strip().upper()

        if row_ticker != ticker:
            continue

        if announcement_id:
            matched = (
                str(
                    row.get("announcement_id")
                    or ""
                ).strip()
                == announcement_id
            )
        else:
            matched = (
                str(
                    row.get("announcement_number")
                    or ""
                ).strip()
                == announcement_number
            )

        if matched:
            matches.append(row)

    if len(matches) != 1:
        raise RuntimeError(
            f"EXACT_CANDIDATE_COUNT_INVALID:"
            f"{len(matches)}"
        )

    candidate = matches[0]

    if (
        candidate.get("classification")
        != CASH_DIVIDEND_CANDIDATE
    ):
        raise RuntimeError(
            "CANDIDATE_NOT_CASH_DIVIDEND"
        )

    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Download immutable official IDX PDF attachments for one "
            "exact generic cash-dividend discovery candidate."
        )
    )
    parser.add_argument("--provider-checkout", required=True)
    parser.add_argument("--discovery-manifest", required=True)
    parser.add_argument("--ticker", required=True)

    identity = parser.add_mutually_exclusive_group(
        required=True
    )

    identity.add_argument("--announcement-id")
    identity.add_argument("--announcement-number")

    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    provider_checkout = Path(
        args.provider_checkout
    ).expanduser().resolve()

    manifest_path = Path(
        args.discovery_manifest
    ).expanduser().resolve()

    output = Path(args.output_dir).expanduser().resolve()

    if output.exists():
        raise SystemExit(f"STOP: output already exists: {output}")

    if not manifest_path.is_file():
        raise SystemExit(
            f"STOP: discovery manifest missing: {manifest_path}"
        )

    discovery_bytes = manifest_path.read_bytes()
    discovery_sha = sha256_bytes(discovery_bytes)

    try:
        discovery = json.loads(discovery_bytes.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            "DISCOVERY_MANIFEST_INVALID_JSON"
        ) from exc

    if discovery.get("schema_version") != DISCOVERY_SCHEMA:
        raise RuntimeError("DISCOVERY_SCHEMA_MISMATCH")

    if discovery.get("status") != "COMPLETE":
        raise RuntimeError("DISCOVERY_NOT_COMPLETE")

    if discovery.get("provider_commit") != PROVIDER_COMMIT:
        raise RuntimeError("DISCOVERY_PROVIDER_COMMIT_MISMATCH")

    ticker = str(
        args.ticker
    ).strip().upper()

    announcement_id = str(
        args.announcement_id or ""
    ).strip()

    announcement_number = str(
        args.announcement_number or ""
    ).strip()

    candidate = select_exact_candidate(
        discovery,
        ticker=ticker,
        announcement_id=announcement_id,
        announcement_number=announcement_number,
    )

    raw_attachments = candidate.get("attachments")

    if not isinstance(raw_attachments, list) or not raw_attachments:
        raise RuntimeError("CANDIDATE_ATTACHMENTS_EMPTY")

    attachments = [
        validate_attachment(row)
        for row in raw_attachments
    ]

    filenames = [row["pdf_filename"] for row in attachments]
    urls = [row["url"] for row in attachments]

    if len(set(filenames)) != len(filenames):
        raise RuntimeError("ATTACHMENT_FILENAME_DUPLICATE")

    if len(set(urls)) != len(urls):
        raise RuntimeError("ATTACHMENT_URL_DUPLICATE")

    provider_src = verify_provider(provider_checkout)
    sys.path.insert(0, str(provider_src))

    from idx.core.client import DEFAULT_HEADERS  # type: ignore
    from curl_cffi import requests  # type: ignore

    output.parent.mkdir(parents=True, exist_ok=True)

    stage = Path(
        tempfile.mkdtemp(
            prefix=f".{output.name}.partial.",
            dir=output.parent,
        )
    )

    try:
        captured: list[dict[str, Any]] = []

        for index, row in enumerate(attachments, start=1):
            captured_at = datetime.now(
                timezone.utc
            ).isoformat()

            response = requests.get(
                row["url"],
                headers=DEFAULT_HEADERS,
                impersonate="chrome",
                timeout=30,
            )

            raw = bytes(response.content)

            if response.status_code != 200:
                raise RuntimeError(
                    f"ATTACHMENT_HTTP_{response.status_code}"
                )

            if not raw.startswith(b"%PDF-"):
                raise RuntimeError("ATTACHMENT_NOT_PDF")

            target = stage / row["pdf_filename"]
            target.write_bytes(raw)

            captured.append(
                {
                    "index": index,
                    "pdf_filename": row["pdf_filename"],
                    "original_filename": row["original_filename"],
                    "url": row["url"],
                    "captured_at_utc": captured_at,
                    "http_status": int(response.status_code),
                    "content_type": str(
                        response.headers.get("content-type", "")
                    ),
                    "byte_count": len(raw),
                    "sha256": sha256_bytes(raw),
                    "pdf_magic": True,
                }
            )

        # The outer batch is published by renaming a `.partial.<id>`
        # directory to its final name. Do not persist that transient path in
        # an immutable child manifest. The attachment output is
        # `<batch>/evidence/<candidate>` and discovery is `<batch>/discovery`,
        # so this relative binding survives the atomic publish rename.
        source_discovery_reference = (
            "../../discovery/DISCOVERY_MANIFEST.json"
            if "/batches/" in str(manifest_path).replace("\\", "/")
            else os.path.relpath(
                manifest_path,
                start=output,
            ).replace("\\", "/")
        )

        result = {
            "schema_version": SCHEMA,
            "status": "COMPLETE_AWAITING_SEMANTIC_REVIEW",
            "provider_repository": PROVIDER_REPOSITORY,
            "provider_commit": PROVIDER_COMMIT,
            "request_policy": (
                "ONE_ATTEMPT_PER_ATTACHMENT_NO_RETRY"
            ),
            "retry_count": 0,
            "source_discovery_manifest_path": source_discovery_reference,
            "source_discovery_manifest_relpath": source_discovery_reference,
            "source_discovery_manifest_sha256": discovery_sha,
            "candidate": {
                "ticker": candidate["ticker"],
                "announcement_id": candidate["announcement_id"],
                "announcement_number": candidate[
                    "announcement_number"
                ],
                "announcement_timestamp": candidate[
                    "announcement_timestamp"
                ],
                "title": candidate["title"],
                "form_id": candidate["form_id"],
                "classification": candidate["classification"],
            },
            "attachment_count": len(captured),
            "attachments": captured,
        }

        manifest = stage / "ATTACHMENT_CAPTURE_MANIFEST.json"
        manifest.write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        os.replace(stage, output)

    except Exception:
        print(
            f"FAILED_CAPTURE_STAGE_PRESERVED={stage}",
            file=sys.stderr,
        )
        raise

    print(output / "ATTACHMENT_CAPTURE_MANIFEST.json")
    print(f"attachment_count={len(captured)}")

    for row in captured:
        print(
            f"{row['pdf_filename']} "
            f"bytes={row['byte_count']} "
            f"sha256={row['sha256']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
