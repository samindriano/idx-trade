from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.forward_dividend_acquisition_v1 import (
    ANNOUNCEMENT_ENDPOINT,
    PROVIDER_COMMIT,
    PROVIDER_REPOSITORY,
    UPSTREAM_BASE_URL,
    candidate_payload,
    extract_dividend_candidates,
    normalize_ticker,
)

SCHEMA = "idx_trade_forward_dividend_announcement_capture_v1"
PAGE_SIZE = 100
MAX_PAGES_PER_TICKER = 20


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_date(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def verify_provider(checkout: Path) -> Path:
    if not checkout.is_dir():
        raise RuntimeError(f"provider checkout missing: {checkout}")

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture prospective IDX ListedCompany announcements for "
            "arbitrary required tickers and discover dividend candidates."
        )
    )
    parser.add_argument("--provider-checkout", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--date-from", required=True)
    parser.add_argument("--date-to", required=True)
    args = parser.parse_args()

    provider_checkout = Path(
        args.provider_checkout
    ).expanduser().resolve()

    output = Path(args.output_dir).expanduser().resolve()

    if output.exists():
        raise SystemExit(f"STOP: output already exists: {output}")

    date_from = parse_date(args.date_from)
    date_to = parse_date(args.date_to)

    if date_to < date_from:
        raise SystemExit("STOP: date window reversed")

    tickers = sorted(
        {normalize_ticker(value) for value in args.ticker}
    )

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

    raw_dir = stage / "raw"
    raw_dir.mkdir()

    raw_artifacts: list[dict[str, Any]] = []
    all_candidates = []

    try:
        for ticker in tickers:
            offset = 0
            page = 1
            observed_total: int | None = None

            while True:
                if page > MAX_PAGES_PER_TICKER:
                    raise RuntimeError(
                        f"pagination safety cap exceeded: {ticker}"
                    )

                params = {
                    "kodeEmiten": ticker,
                    "emitenType": "*",
                    "indexFrom": offset,
                    "pageSize": PAGE_SIZE,
                    "dateFrom": date_from.replace("-", ""),
                    "dateTo": date_to.replace("-", ""),
                    "lang": "id",
                    "keyword": "",
                }

                captured_at = datetime.now(
                    timezone.utc
                ).isoformat()

                response = requests.get(
                    UPSTREAM_BASE_URL + ANNOUNCEMENT_ENDPOINT,
                    params=params,
                    headers=DEFAULT_HEADERS,
                    impersonate="chrome",
                    timeout=30,
                )

                raw = bytes(response.content)

                name = f"{ticker}_p{page:03d}.json"
                path = raw_dir / name
                path.write_bytes(raw)

                artifact = {
                    "ticker": ticker,
                    "page": page,
                    "index_from": offset,
                    "endpoint": ANNOUNCEMENT_ENDPOINT,
                    "params": params,
                    "captured_at_utc": captured_at,
                    "http_status": int(response.status_code),
                    "content_type": str(
                        response.headers.get("content-type", "")
                    ),
                    "path": str(Path("raw") / name),
                    "byte_count": len(raw),
                    "sha256": sha256_bytes(raw),
                }
                raw_artifacts.append(artifact)

                if response.status_code != 200:
                    raise RuntimeError(
                        f"HTTP {response.status_code}: {ticker}"
                    )

                if "json" not in artifact["content_type"].lower():
                    raise RuntimeError(
                        f"non-JSON response: {ticker}"
                    )

                try:
                    payload = response.json()
                except Exception as exc:
                    raise RuntimeError(
                        f"invalid JSON response: {ticker}"
                    ) from exc

                if not isinstance(payload, dict):
                    raise RuntimeError(
                        f"response not object: {ticker}"
                    )

                replies = payload.get("Replies")
                if not isinstance(replies, list):
                    raise RuntimeError(
                        f"Replies missing: {ticker}"
                    )

                result_count = payload.get("ResultCount")
                if isinstance(result_count, int):
                    if result_count < 0:
                        raise RuntimeError(
                            f"negative ResultCount: {ticker}"
                        )
                    if (
                        observed_total is not None
                        and observed_total != result_count
                    ):
                        raise RuntimeError(
                            f"ResultCount changed during pagination: {ticker}"
                        )
                    observed_total = result_count

                all_candidates.extend(
                    extract_dividend_candidates(
                        payload,
                        expected_ticker=ticker,
                    )
                )

                if observed_total is not None:
                    if offset + len(replies) > observed_total:
                        raise RuntimeError(
                            f"page exceeds ResultCount: {ticker}"
                        )
                    if not replies and offset < observed_total:
                        raise RuntimeError(
                            f"empty page before ResultCount exhausted: {ticker}"
                        )

                if not replies:
                    break

                offset += len(replies)

                if observed_total is not None:
                    if offset >= observed_total:
                        break
                elif len(replies) < PAGE_SIZE:
                    break
                else:
                    raise RuntimeError(
                        f"pagination unbounded without ResultCount: {ticker}"
                    )

                page += 1

        by_identity = {}

        for row in all_candidates:
            identity = (
                row.ticker,
                row.announcement_id or row.announcement_number,
            )
            previous = by_identity.get(identity)
            if previous is not None and previous != row:
                raise RuntimeError(
                    "candidate conflict across pages"
                )
            by_identity[identity] = row

        candidates = tuple(
            sorted(
                by_identity.values(),
                key=lambda row: (
                    row.ticker,
                    row.announcement_timestamp,
                    row.announcement_id,
                    row.announcement_number,
                ),
            )
        )

        manifest = {
            "schema_version": SCHEMA,
            "status": "COMPLETE",
            "provider_repository": PROVIDER_REPOSITORY,
            "provider_commit": PROVIDER_COMMIT,
            "upstream_base_url": UPSTREAM_BASE_URL,
            "endpoint": ANNOUNCEMENT_ENDPOINT,
            "request_policy": (
                "DIRECT_IDX_NO_RETRY_PAGINATED_PER_TICKER"
            ),
            "retry_count": 0,
            "date_from": date_from,
            "date_to": date_to,
            "required_tickers": tickers,
            "raw_artifacts": raw_artifacts,
            "candidate_count": len(candidates),
            "candidates": candidate_payload(candidates),
        }

        manifest_path = stage / "DISCOVERY_MANIFEST.json"
        manifest_path.write_text(
            json.dumps(
                manifest,
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

    print(output / "DISCOVERY_MANIFEST.json")
    print(f"required_tickers={len(tickers)}")
    print(f"candidate_count={len(candidates)}")

    for row in candidates:
        print(
            f"{row.ticker} "
            f"{row.classification} "
            f"{row.announcement_id or row.announcement_number} "
            f"{row.title}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
