from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

PROVIDER_REPOSITORY = "nichsedge/idx-bei"
PROVIDER_COMMIT = "75d6c0f74fa360d225794c70c383348977de6798"
UPSTREAM_HOST = "www.idx.co.id"
SCHEMA = "idx_trade_forward_ca_dividend_attachment_capture_v1"
EXPECTED_ANNOUNCEMENT_RAW_SHA256 = "6e8ced1891addecdb9a1029d064c75d072ebcbeb4319ad633d30e43fac004473"
EXPECTED_ANNOUNCEMENT_DATE = "2026-08-19"
EXPECTED_CODE = "BBCA"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_provider(checkout: Path) -> None:
    proc = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = proc.stdout.strip()
    if head != PROVIDER_COMMIT:
        raise SystemExit(f"provider commit mismatch: {head} != {PROVIDER_COMMIT}")


def _announcement_date(value: Any) -> str | None:
    text = str(value or "").strip()
    match = re.search(r"20\d{2}-\d{2}-\d{2}", text)
    return match.group(0) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture official IDX dividend announcement attachments exactly once each.")
    parser.add_argument("--provider-checkout", required=True)
    parser.add_argument("--probe-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    checkout = Path(args.provider_checkout).expanduser().resolve()
    probe_dir = Path(args.probe_dir).expanduser().resolve()
    out = Path(args.output_dir).expanduser().resolve()
    if not checkout.is_dir():
        raise SystemExit(f"provider checkout missing: {checkout}")
    if out.exists():
        raise SystemExit(f"output dir already exists: {out}")

    announcements_path = probe_dir / "announcements.json"
    if not announcements_path.is_file():
        raise SystemExit(f"announcements raw missing: {announcements_path}")
    source_sha = _sha256_path(announcements_path)
    if source_sha != EXPECTED_ANNOUNCEMENT_RAW_SHA256:
        raise SystemExit(
            f"announcement raw SHA mismatch: {source_sha} != {EXPECTED_ANNOUNCEMENT_RAW_SHA256}"
        )

    _verify_provider(checkout)
    provider_src = checkout / "python" / "src"
    if not provider_src.is_dir():
        raise SystemExit(f"provider python/src missing: {provider_src}")
    sys.path.insert(0, str(provider_src))
    from idx.core.client import DEFAULT_HEADERS  # type: ignore
    from curl_cffi import requests  # type: ignore

    payload = json.loads(announcements_path.read_text(encoding="utf-8"))
    replies = payload.get("Replies") if isinstance(payload, dict) else None
    if not isinstance(replies, list):
        raise SystemExit("announcement Replies missing")

    matches: list[dict[str, Any]] = []
    for item in replies:
        if not isinstance(item, dict):
            continue
        announcement = item.get("pengumuman") if isinstance(item.get("pengumuman"), dict) else {}
        code = str(announcement.get("Kode_Emiten") or "").strip().upper()
        title = str(announcement.get("JudulPengumuman") or announcement.get("PerihalPengumuman") or "")
        date_value = _announcement_date(announcement.get("TglPengumuman"))
        if code == EXPECTED_CODE and date_value == EXPECTED_ANNOUNCEMENT_DATE and "dividen" in title.lower():
            matches.append(item)

    if len(matches) != 1:
        raise SystemExit(f"expected exactly one matching BBCA dividend announcement, got {len(matches)}")

    match = matches[0]
    announcement = match.get("pengumuman") if isinstance(match.get("pengumuman"), dict) else {}
    attachments = match.get("attachments") if isinstance(match.get("attachments"), list) else []
    attachment_rows = [x for x in attachments if isinstance(x, dict)]
    if not attachment_rows:
        raise SystemExit("matching announcement has no attachments")

    out.mkdir(parents=True)
    captured: list[dict[str, Any]] = []
    for index, row in enumerate(attachment_rows, start=1):
        url = str(row.get("FullSavePath") or "").strip()
        if not url.startswith("https://www.idx.co.id/"):
            raise SystemExit(f"unexpected attachment URL: {url}")
        captured_at = datetime.now(timezone.utc).isoformat()
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            impersonate="chrome",
            timeout=30,
        )
        raw = bytes(response.content)
        filename = str(row.get("PDFFilename") or f"attachment_{index}.pdf").strip()
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        target = out / filename
        target.write_bytes(raw)
        captured.append(
            {
                "index": index,
                "url": url,
                "pdf_filename": filename,
                "original_filename": str(row.get("OriginalFilename") or ""),
                "is_attachment": bool(row.get("IsAttachment")),
                "captured_at_utc": captured_at,
                "http_status": int(response.status_code),
                "content_type": str(response.headers.get("content-type", "")),
                "byte_count": len(raw),
                "sha256": _sha256_bytes(raw),
                "pdf_magic": raw[:5] == b"%PDF-",
            }
        )
        if response.status_code != 200:
            raise SystemExit(f"attachment HTTP {response.status_code}: {url}")
        if raw[:5] != b"%PDF-":
            raise SystemExit(f"attachment is not a PDF: {url}")

    manifest = {
        "schema_version": SCHEMA,
        "status": "COMPLETE_AWAITING_OFFLINE_REVIEW",
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_commit": PROVIDER_COMMIT,
        "transport": "curl_cffi_direct_one_shot",
        "request_policy": "ONE_ATTEMPT_PER_ATTACHMENT_NO_RETRY_HELPER",
        "source_probe_dir": str(probe_dir),
        "source_announcement_raw_path": str(announcements_path),
        "source_announcement_raw_sha256": source_sha,
        "announcement": {
            "id": announcement.get("Id2"),
            "number": announcement.get("NoPengumuman"),
            "date": announcement.get("TglPengumuman"),
            "code": str(announcement.get("Kode_Emiten") or "").strip(),
            "title": announcement.get("JudulPengumuman"),
            "form_id": announcement.get("Form_Id"),
        },
        "attachment_request_count": len(captured),
        "retry_count": 0,
        "attachments": captured,
    }
    manifest_path = out / "ATTACHMENT_CAPTURE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest_path)
    for row in captured:
        print(
            f"{row['pdf_filename']}: http={row['http_status']} bytes={row['byte_count']} sha256={row['sha256']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
