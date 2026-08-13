"""Headless, idempotent catch-up runner for the existing forward monitor."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd

from . import forward_monitoring as base
from . import forward_monitoring_runtime as runtime
from .forward_ohlcv import enrich_session_ohlcv
from .provenance import sha256_file, write_manifest_atomic


JAKARTA = ZoneInfo("Asia/Jakarta")
MARKET_CLOSE_CUTOFF_HOUR = 17
EOD_CAPTURE_HOUR = 18


def _now_jakarta() -> datetime:
    return datetime.now(tz=JAKARTA)


def _run_log_dir(runtime_root: str | Path) -> Path:
    return base.runtime_paths(runtime_root).monitor_root / "eod_automation"


def _before_cutoff(now: datetime) -> bool:
    return now.hour < EOD_CAPTURE_HOUR


def run_eod_catchup(
    runtime_root: str | Path,
    *,
    batch_size: int = 100,
) -> dict[str, object]:
    """Capture every missing closed session chronologically through the stable engine."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    root = Path(runtime_root).expanduser().resolve()
    started_at = _now_jakarta()
    run_id = f"{started_at.astimezone(ZoneInfo('UTC')).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    log_dir = _run_log_dir(root)
    log_path = log_dir / "runs" / f"{run_id}.json"
    result: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "RUNNING",
        "runtime_root": str(root),
        "started_at_jakarta": started_at.isoformat(),
        "started_at_utc": started_at.astimezone(ZoneInfo("UTC")).isoformat(),
        "market_close_cutoff_hour_jakarta": MARKET_CLOSE_CUTOFF_HOUR,
        "capture_hour_jakarta": EOD_CAPTURE_HOUR,
        "captured_sessions": [],
        "stopped_on_first_failure": False,
        "outcome_access": "LOCKED",
        "forward_outcomes_accessed": False,
    }

    def persist() -> None:
        write_manifest_atomic(log_path, result)
        latest = log_dir / "latest.json"
        write_manifest_atomic(latest, result | {"run_log_path": str(log_path), "run_log_sha256": sha256_file(log_path)})

    try:
        if _before_cutoff(started_at):
            result.update(
                {
                    "status": "BEFORE_EOD_CUTOFF",
                    "error_code": "BEFORE_EOD_CUTOFF",
                    "error_message": "No real EOD capture is allowed before 18:00 Asia/Jakarta.",
                }
            )
            persist()
            return result

        paths = base.runtime_paths(root)
        closed_through = base._closed_through_date()
        sessions = runtime.sync_forward_calendar(paths, through=closed_through)
        result["closed_through_session"] = closed_through.date().isoformat()
        result["official_calendar_validation"] = "PASS_EXACT_IDX_SESSION_CALENDAR"
        result["calendar_first_session"] = sessions.min().date().isoformat() if len(sessions) else None
        result["calendar_last_session"] = sessions.max().date().isoformat() if len(sessions) else None

        # Legacy DATA_READY sessions predate the OHLCV sidecar. Enrich them
        # before catching up new sessions; the original model_input/manifest
        # remain immutable and a failed enrichment stops the cycle.
        result["open_enrichment"] = []
        result["legacy_open_repair_status"] = "COMPLETE"
        for row in base._session_states(paths).values():
            if row["state"] != "DATA_READY":
                continue
            session_key = str(row["session_date"])
            sidecar = paths.session_root / session_key / "session_ohlcv.parquet"
            if sidecar.exists():
                continue
            enrichment = enrich_session_ohlcv(root, session_key, fetch_missing=True, batch_size=batch_size)
            result["open_enrichment"].append(enrichment)
            if enrichment.get("status") != "OPEN_COMPLETE":
                # Legacy sidecars are a repair lane.  They must never rewrite
                # or invalidate the old DATA_READY snapshot, nor prevent the
                # canonical EOD engine from catching up newer sessions.
                result["legacy_open_repair_status"] = "INCOMPLETE"

        attempted_sessions: set[str] = set()
        while True:
            sessions = runtime._load_forward_calendar(paths)
            earliest = base._earliest_missing(paths, sessions) if len(sessions) else None
            result["next_missing_session"] = earliest.date().isoformat() if earliest is not None else None
            if earliest is None:
                result["status"] = "NO_MISSING_SESSION"
                break
            expected_session = earliest.date().isoformat()
            if expected_session in attempted_sessions:
                raise RuntimeError(
                    "EOD catch-up made no chronological progress after a DATA_READY capture: "
                    f"session={expected_session}"
                )
            attempted_sessions.add(expected_session)
            captured = runtime.capture_session(root, target_date=earliest, batch_size=batch_size)
            if captured.get("status") != "DATA_READY":
                result.update(
                    {
                        "status": "DATA_FAILED",
                        "stopped_on_first_failure": True,
                        "failure": captured,
                    }
                )
                break
            try:
                captured_session = base._normal_date(captured.get("session_date"))
            except (TypeError, ValueError) as error:
                raise RuntimeError("DATA_READY capture did not return a valid session_date") from error
            if captured_session != earliest:
                raise RuntimeError(
                    "DATA_READY capture returned a different session than requested: "
                    f"requested={expected_session} "
                    f"returned={captured_session.date().isoformat()}"
                )
            captured = dict(captured)
            captured["session_date_validation"] = "PASS_CALENDAR_AND_EXACT_SOURCE_DATE"
            result["captured_sessions"].append(captured)

        result["finished_at_jakarta"] = _now_jakarta().isoformat()
        persist()
        return result
    except Exception as error:
        result.update(
            {
                "status": "DATA_FAILED",
                "stopped_on_first_failure": True,
                "error_code": type(error).__name__.upper(),
                "error_message": str(error),
                "finished_at_jakarta": _now_jakarta().isoformat(),
            }
        )
        persist()
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IDX Trade headless forward EOD catch-up")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_eod_catchup(args.runtime_root, batch_size=args.batch_size)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("status") in {"NO_MISSING_SESSION", "BEFORE_EOD_CUTOFF"} else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            json.dumps(
                {"status": "ERROR", "error_code": type(error).__name__.upper(), "error_message": str(error)},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise
