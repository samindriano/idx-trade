"""Cloud runner for Stockbit Stream routine capture V2."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from idx_trade.stockbit_stream_archive import StreamArchiveError, verify_universe_manifest
from idx_trade.stockbit_stream_capture_v2 import (
    IDENTITY_ROSTER_STALE_DAYS,
    archive_from_env,
    build_runtime_universe,
    capture_stream_v2,
)
from idx_trade.stockbit_stream_v2_primitives import V2ZapiClient


def _validated_identity_roster_as_of(
    identity_manifest: Mapping[str, Any], capture_date: str
) -> str:
    """Return the pinned identity as-of date and fail closed once it is stale."""
    try:
        value = identity_manifest["derivation"]["as_of_panel_date"]
        roster_as_of = str(value)
        roster_day = date.fromisoformat(roster_as_of)
        capture_day = date.fromisoformat(capture_date)
    except (KeyError, TypeError, ValueError) as exc:
        raise StreamArchiveError(
            "identity manifest must contain derivation.as_of_panel_date in YYYY-MM-DD form"
        ) from exc
    if roster_day > capture_day:
        raise StreamArchiveError("identity roster as-of date is after capture date")
    age_days = (capture_day - roster_day).days
    if age_days > IDENTITY_ROSTER_STALE_DAYS:
        raise StreamArchiveError(
            f"identity roster is stale: as_of={roster_as_of}, age_days={age_days}, "
            f"max_age_days={IDENTITY_ROSTER_STALE_DAYS}"
        )
    return roster_as_of


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity-csv", type=Path, required=True)
    parser.add_argument("--identity-manifest", type=Path, required=True)
    parser.add_argument("--slot", required=True)
    parser.add_argument("--top-n", type=int, default=200)
    parser.add_argument("--capture-date")
    args = parser.parse_args()

    capture_date = args.capture_date or datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
    api_key = os.environ.get("ZAPI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "BLOCKED", "detail": "ZAPI_API_KEY missing"}))
        return 2
    try:
        identity_manifest = verify_universe_manifest(args.identity_csv, args.identity_manifest)
        identity_roster_as_of = _validated_identity_roster_as_of(identity_manifest, capture_date)
        universe = build_runtime_universe(
            api_key=api_key,
            identity_csv=args.identity_csv,
            capture_date=capture_date,
            top_n=args.top_n,
            identity_roster_as_of=identity_roster_as_of,
        )
        result = capture_stream_v2(
            client=V2ZapiClient(api_key),
            archive=archive_from_env(),
            universe=universe,
            slot=args.slot,
            hmac_salt=os.environ.get("STOCKBIT_STREAM_HMAC_SALT", ""),
        )
        summary = {
            "status": result["status"],
            "logical_slot_id": result.get("logical_slot_id"),
            "attempt_id": result.get("attempt_id"),
            "run_id": result["run_id"],
            "slot": args.slot,
            "top_n": args.top_n,
            "source_session": universe.source_session,
            "identity_manifest_status": identity_manifest.get("status"),
            "identity_source_sha256": universe.identity_source_sha256,
            "identity_roster_as_of": universe.identity_roster_as_of,
            "identity_roster_age_days": universe.selection_diagnostics.get("identity_roster_age_days"),
            "identity_roster_status": universe.selection_diagnostics.get("identity_roster_status"),
            "universe_sha256": universe.universe_sha256,
            "planned_calls": result.get("planned_calls"),
            "completed_calls": result.get("completed_calls"),
            "successful_responses": result.get("successful_responses"),
            "normalized_post_rows": result.get("normalized_post_rows"),
            "response_classification_counts": result.get("response_classification_counts"),
            "quota_after_error": result.get("quota_after_error"),
            "manifest_sha256": result.get("manifest_sha256"),
            "model_accessed": False,
            "outcome_accessed": False,
            "counter_mutated": False,
        }
        print(json.dumps(summary, sort_keys=True))
        return 0 if result["status"] == "DATA_READY" else 2
    except (StreamArchiveError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED_OR_FAILED", "detail": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
