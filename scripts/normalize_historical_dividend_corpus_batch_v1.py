"""Offline normalization of an immutable historical dividend raw corpus."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import os
import tempfile
from typing import Any

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.forward_dividend_acquisition_v1 import (  # noqa: E402
    ANNOUNCEMENT_ENDPOINT,
    PROVIDER_COMMIT,
    PROVIDER_REPOSITORY,
    UPSTREAM_BASE_URL,
    candidate_payload,
    extract_dividend_candidates,
)

SCHEMA = "idx_trade_historical_dividend_corpus_normalized_v1"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_date(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def normalize(*, input_root: Path, output_root: Path) -> dict[str, Any]:
    input_root = input_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    if output_root.exists():
        raise RuntimeError(f"OUTPUT_EXISTS:{output_root}")

    source_manifest_path = input_root / "DISCOVERY_MANIFEST.json"
    source = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source.get("schema_version") != "idx_trade_historical_dividend_corpus_batch_v1":
        raise RuntimeError("SOURCE_SCHEMA_INVALID")
    required = source.get("required_tickers")
    if not isinstance(required, list) or not required:
        raise RuntimeError("SOURCE_TICKERS_INVALID")

    stage = Path(tempfile.mkdtemp(prefix=f".{output_root.name}.partial.", dir=output_root.parent))
    normalized_rows: list[dict[str, Any]] = []
    all_candidates: list[Any] = []
    ticker_results: list[dict[str, Any]] = []
    try:
        for ticker in sorted(str(x) for x in required):
            raw_path = input_root / "raw" / f"{ticker}_p001.json"
            if not raw_path.is_file():
                raise RuntimeError(f"RAW_MISSING:{ticker}")
            raw = raw_path.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError(f"PAYLOAD_NOT_OBJECT:{ticker}")
            replies = payload.get("Replies")
            result_count = payload.get("ResultCount")
            if not isinstance(replies, list) or not isinstance(result_count, int):
                raise RuntimeError(f"SOURCE_SCHEMA_INVALID:{ticker}")
            if len(replies) != result_count:
                raise RuntimeError(f"RESULT_COUNT_MISMATCH:{ticker}")
            extracted = extract_dividend_candidates(payload, expected_ticker=ticker)
            all_candidates.extend(extracted)
            normalized_rows.append({
                "ticker": ticker,
                "source_raw_sha256": sha256_bytes(raw),
                "source_row_count": len(replies),
                "source_records_total": result_count,
                "candidate_count": len(extracted),
            })
            ticker_results.append({
                "ticker": ticker,
                "status": "COMPLETE",
                "source_raw_sha256": sha256_bytes(raw),
                "row_count": len(replies),
                "records_total": result_count,
                "candidate_count": len(extracted),
            })

        by_identity: dict[tuple[str, str], Any] = {}
        for row in all_candidates:
            identity = (row.ticker, row.announcement_id or row.announcement_number)
            previous = by_identity.get(identity)
            if previous is not None and previous != row:
                raise RuntimeError("CANDIDATE_IDENTITY_CONFLICT")
            by_identity[identity] = row
        candidates = tuple(sorted(by_identity.values(), key=lambda row: (
            row.ticker,
            row.announcement_timestamp,
            row.announcement_id,
            row.announcement_number,
        )))
        manifest = {
            "schema_version": SCHEMA,
            "status": "COMPLETE",
            "source_manifest_sha256": sha256_bytes(source_manifest_path.read_bytes()),
            "provider_repository": PROVIDER_REPOSITORY,
            "provider_commit": PROVIDER_COMMIT,
            "upstream_base_url": UPSTREAM_BASE_URL,
            "endpoint": ANNOUNCEMENT_ENDPOINT,
            "date_from": parse_date(str(source["date_from"])),
            "date_to": parse_date(str(source["date_to"])),
            "required_tickers": sorted(str(x) for x in required),
            "ticker_results": ticker_results,
            "normalized_rows": normalized_rows,
            "candidate_count": len(candidates),
            "candidates": candidate_payload(candidates),
        }
        (stage / "NORMALIZED_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(stage, output_root)
    except Exception:
        print(f"FAILED_NORMALIZATION_STAGE_PRESERVED={stage}", file=sys.stderr)
        raise
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    manifest = normalize(input_root=args.input_root, output_root=args.output_root)
    print(json.dumps({
        "status": manifest["status"],
        "required_tickers": len(manifest["required_tickers"]),
        "candidate_count": manifest["candidate_count"],
        "normalized_manifest": str(args.output_root.resolve() / "NORMALIZED_MANIFEST.json"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
