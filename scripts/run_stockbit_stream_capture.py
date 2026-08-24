"""Headless CLI for the isolated Stockbit Stream prospective archive.

This runner owns no local IDX scheduler and has no model, outcome, sentiment,
or counter integration.  It fails before provider access when private durable
storage or the pinned universe is unavailable.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from idx_trade.stockbit_stream_archive import (
    SLOTS,
    StorageConfigurationError,
    StreamArchiveError,
    ZapiClient,
    build_store_from_env,
    capture_stream_run,
    load_universe,
    verify_universe_manifest,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-csv", required=True, type=Path)
    parser.add_argument("--universe-manifest", required=True, type=Path)
    parser.add_argument("--slot", required=True, choices=SLOTS)
    parser.add_argument("--capture-date", help="Asia/Jakarta date; defaults to today")
    return parser


def _capture_date(raw: str | None) -> str:
    if raw is not None:
        datetime.strptime(raw, "%Y-%m-%d")
        return raw
    return datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()


def main() -> int:
    args = _parser().parse_args()
    try:
        manifest = verify_universe_manifest(args.universe_csv, args.universe_manifest)
        rows = load_universe(args.universe_csv)
        store = build_store_from_env()
        api_key = os.environ.get("ZAPI_API_KEY", "")
        client = ZapiClient(api_key)
        result = capture_stream_run(
            client=client,
            store=store,
            universe_rows=rows,
            slot=args.slot,
            capture_date=_capture_date(args.capture_date),
            hmac_salt=os.environ.get("STOCKBIT_STREAM_HMAC_SALT", ""),
            universe_sha=str(manifest["output_sha256"]),
        )
        print(json.dumps({
            "status": result["status"],
            "run_id": result["run_id"],
            "planned_calls": result.get("planned_calls"),
            "completed_calls": result.get("completed_calls"),
            "successful_responses": result.get("successful_responses"),
            "normalized_post_rows": result.get("normalized_post_rows"),
            "manifest_sha256": result.get("manifest_sha256"),
            "storage_verification": result.get("storage_verification"),
            "provider_calls": result.get("provider_calls"),
            "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }, sort_keys=True))
        return 0 if result["status"] == "DATA_READY" else 2
    except StorageConfigurationError as exc:
        print(json.dumps({"status": "BLOCKED_STORAGE_CREDENTIAL_SETUP", "detail": str(exc)}, sort_keys=True))
        return 2
    except StreamArchiveError as exc:
        print(json.dumps({"status": "BLOCKED_OR_FAILED", "detail": str(exc)}, sort_keys=True))
        return 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED_OR_FAILED", "detail": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
