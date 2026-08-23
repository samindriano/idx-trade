"""Bounded, resumable-by-artifact IDX dividend announcement batch capture.

This research-only collector keeps going after a single issuer transport or
schema failure so the final manifest distinguishes successful coverage from
unresolved tickers.  It never promotes an incomplete corpus to a complete
status and never treats missing announcements as evidence of no event.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.forward_dividend_acquisition_v1 import (  # noqa: E402
    ANNOUNCEMENT_ENDPOINT,
    PROVIDER_COMMIT,
    PROVIDER_REPOSITORY,
    UPSTREAM_BASE_URL,
    candidate_payload,
    extract_dividend_candidates,
    normalize_ticker,
)

SCHEMA = "idx_trade_historical_dividend_corpus_batch_v1"
PAGE_SIZE = 9999
MAX_ATTEMPTS = 2
RETRYABLE_STATUS = frozenset({403, 429, 500, 502, 503, 504})
INTER_REQUEST_DELAY_SECONDS = 1.0
RETRY_DELAY_SECONDS = 5.0


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_date(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def classify_failure(status: int | None, error: str) -> str:
    if status in RETRYABLE_STATUS:
        return f"HTTP_{status}"
    if status is None:
        return "TRANSPORT_ERROR"
    return error


def read_tickers(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        if not rows.fieldnames or "ticker" not in rows.fieldnames:
            raise RuntimeError("TICKER_CSV_MISSING_TICKER_COLUMN")
        values = {normalize_ticker(row.get("ticker")) for row in rows}
    return sorted(values)


def verify_provider(checkout: Path) -> Path:
    if not checkout.is_dir():
        raise RuntimeError(f"PROVIDER_CHECKOUT_MISSING:{checkout}")
    proc = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = proc.stdout.strip()
    if head != PROVIDER_COMMIT:
        raise RuntimeError(f"PROVIDER_COMMIT_MISMATCH:{head}")
    provider_src = checkout / "python" / "src"
    if not provider_src.is_dir():
        raise RuntimeError(f"PROVIDER_SOURCE_MISSING:{provider_src}")
    return provider_src


def _request_one(
    *,
    requests: Any,
    url: str,
    params: dict[str, Any],
    headers: dict[str, str],
) -> tuple[Any, int]:
    last_response = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                impersonate="chrome",
                timeout=30,
            )
            last_response = response
        except Exception:
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(RETRY_DELAY_SECONDS)
            continue

        if response.status_code not in RETRYABLE_STATUS:
            return response, attempt
        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_DELAY_SECONDS)
        else:
            return response, attempt

    if last_response is None:  # pragma: no cover - defensive
        raise RuntimeError("REQUEST_NO_RESPONSE")
    return last_response, MAX_ATTEMPTS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-checkout", required=True, type=Path)
    parser.add_argument("--ticker-csv", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--date-from", required=True)
    parser.add_argument("--date-to", required=True)
    args = parser.parse_args()

    output = args.output_dir.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"STOP_OUTPUT_EXISTS:{output}")

    date_from = parse_date(args.date_from)
    date_to = parse_date(args.date_to)
    if date_to < date_from:
        raise SystemExit("STOP_DATE_WINDOW_REVERSED")

    tickers = read_tickers(args.ticker_csv.expanduser().resolve())
    provider_src = verify_provider(args.provider_checkout.expanduser().resolve())
    sys.path.insert(0, str(provider_src))

    from idx.core.client import DEFAULT_HEADERS  # type: ignore
    from curl_cffi import requests  # type: ignore

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.partial.", dir=output.parent)
    )
    raw_dir = stage / "raw"
    raw_dir.mkdir()

    ticker_results: list[dict[str, Any]] = []
    raw_artifacts: list[dict[str, Any]] = []
    candidates: list[Any] = []
    url = UPSTREAM_BASE_URL + ANNOUNCEMENT_ENDPOINT

    try:
        for ticker_index, ticker in enumerate(tickers):
            params = {
                "kodeEmiten": ticker,
                "emitenType": "*",
                "indexFrom": 0,
                "pageSize": PAGE_SIZE,
                "dateFrom": date_from.replace("-", ""),
                "dateTo": date_to.replace("-", ""),
                "lang": "id",
                "keyword": "",
            }
            retrieved_at = datetime.now(timezone.utc).isoformat()
            status: int | None = None
            content_type = ""
            raw = b""
            error = ""
            attempts = 0

            try:
                response, attempts = _request_one(
                    requests=requests,
                    url=url,
                    params=params,
                    headers=DEFAULT_HEADERS,
                )
                status = int(response.status_code)
                content_type = str(response.headers.get("content-type", ""))
                raw = bytes(response.content)
                raw_name = f"{ticker}_p001.json"
                raw_path = raw_dir / raw_name
                raw_path.write_bytes(raw)
                raw_record = {
                    "ticker": ticker,
                    "page": 1,
                    "params": params,
                    "retrieved_at_utc": retrieved_at,
                    "http_status": status,
                    "content_type": content_type,
                    "path": str(Path("raw") / raw_name),
                    "byte_count": len(raw),
                    "sha256": sha256_bytes(raw),
                    "attempts": attempts,
                }
                raw_artifacts.append(raw_record)

                if status != 200:
                    raise RuntimeError(f"HTTP_{status}")
                if "json" not in content_type.lower():
                    raise RuntimeError("NON_JSON_RESPONSE")
                payload = response.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("RESPONSE_NOT_OBJECT")
                replies = payload.get("Replies")
                result_count = payload.get("ResultCount")
                if not isinstance(replies, list):
                    raise RuntimeError("REPLIES_NOT_LIST")
                if not isinstance(result_count, int) or result_count < 0:
                    raise RuntimeError("RESULT_COUNT_INVALID")
                if len(replies) != result_count:
                    raise RuntimeError(
                        f"RESULT_COUNT_MISMATCH:{len(replies)}:{result_count}"
                    )
                extracted = extract_dividend_candidates(
                    payload, expected_ticker=ticker
                )
                candidates.extend(extracted)
                ticker_results.append({
                    "ticker": ticker,
                    "status": "COMPLETE",
                    "http_status": status,
                    "attempts": attempts,
                    "row_count": len(replies),
                    "records_total": result_count,
                    "candidate_count": len(extracted),
                    "raw_sha256": raw_record["sha256"],
                })
            except Exception as exc:
                if raw:
                    raw_path = raw_dir / f"{ticker}_p001.json"
                    if not raw_path.exists():
                        raw_path.write_bytes(raw)
                error = str(exc)
                ticker_results.append({
                    "ticker": ticker,
                    "status": "FAILED",
                    "http_status": status,
                    "attempts": attempts,
                    "error_class": classify_failure(status, error),
                    "error": error,
                    "raw_sha256": sha256_bytes(raw) if raw else None,
                })

            if ticker_index + 1 < len(tickers):
                time.sleep(INTER_REQUEST_DELAY_SECONDS)

        by_identity: dict[tuple[str, str], Any] = {}
        for row in candidates:
            identity = (row.ticker, row.announcement_id or row.announcement_number)
            previous = by_identity.get(identity)
            if previous is not None and previous != row:
                raise RuntimeError("CANDIDATE_IDENTITY_CONFLICT")
            by_identity[identity] = row

        final_candidates = tuple(
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
        failed = [row for row in ticker_results if row["status"] != "COMPLETE"]
        manifest = {
            "schema_version": SCHEMA,
            "status": "COMPLETE" if not failed else "INCOMPLETE",
            "provider_repository": PROVIDER_REPOSITORY,
            "provider_commit": PROVIDER_COMMIT,
            "upstream_base_url": UPSTREAM_BASE_URL,
            "endpoint": ANNOUNCEMENT_ENDPOINT,
            "request_policy": "DIRECT_IDX_ONE_RETRY_TRANSIENT_PER_TICKER",
            "max_attempts": MAX_ATTEMPTS,
            "inter_request_delay_seconds": INTER_REQUEST_DELAY_SECONDS,
            "retry_delay_seconds": RETRY_DELAY_SECONDS,
            "date_from": date_from,
            "date_to": date_to,
            "required_tickers": tickers,
            "ticker_results": ticker_results,
            "failed_tickers": [row["ticker"] for row in failed],
            "raw_artifacts": raw_artifacts,
            "candidate_count": len(final_candidates),
            "candidates": candidate_payload(final_candidates),
        }
        (stage / "DISCOVERY_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(stage, output)
    except Exception:
        print(f"FAILED_BATCH_STAGE_PRESERVED={stage}", file=sys.stderr)
        raise

    print(json.dumps({
        "status": manifest["status"],
        "required_tickers": len(tickers),
        "failed_tickers": len(manifest["failed_tickers"]),
        "candidate_count": manifest["candidate_count"],
        "manifest": str(output / "DISCOVERY_MANIFEST.json"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
