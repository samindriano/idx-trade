from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from . import forward_monitoring as base


# Operator-visible V2 monitoring begins on the date the live monitoring contract
# was activated. Historical development ended earlier, but sessions before this
# date are intentionally outside the 100-session operator counter.
FORWARD_MONITOR_START_DATE = pd.Timestamp("2026-08-10")


def _eligible_calendar(sessions: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if len(sessions) == 0:
        return sessions
    normalized = pd.DatetimeIndex(sessions).tz_localize(None).normalize().unique().sort_values()
    return normalized[normalized >= FORWARD_MONITOR_START_DATE]


def sync_forward_calendar(
    paths: base.RuntimePaths,
    *,
    through: pd.Timestamp | None = None,
) -> pd.DatetimeIndex:
    """Sync only sessions eligible for the operator-facing forward monitor."""

    end = base._normal_date(through if through is not None else base._closed_through_date())
    start = FORWARD_MONITOR_START_DATE
    if end < start:
        return pd.DatetimeIndex([])
    result = base.run_exchange_session_backfill(start, end, paths.calendar_root)
    if not bool(result.get("complete")):
        raise RuntimeError(f"official forward calendar sync incomplete: {result}")
    return _eligible_calendar(base._read_sessions(paths.calendar_root / "exchange_sessions.csv"))


def _load_forward_calendar(paths: base.RuntimePaths) -> pd.DatetimeIndex:
    return _eligible_calendar(base._read_sessions(paths.calendar_root / "exchange_sessions.csv"))


def capture_session(
    runtime_root: str | Path,
    *,
    target_date: str | pd.Timestamp | None = None,
    batch_size: int = 100,
) -> dict[str, Any]:
    """Delegate capture to the stable engine with the Aug-10 monitor calendar."""

    if target_date is not None:
        requested = base._normal_date(target_date)
        if requested < FORWARD_MONITOR_START_DATE:
            raise ValueError(
                "target is before the forward monitor start date: "
                f"start={FORWARD_MONITOR_START_DATE.date().isoformat()} "
                f"requested={requested.date().isoformat()}"
            )

    original_sync = base.sync_forward_calendar
    base.sync_forward_calendar = sync_forward_calendar
    try:
        result = base.capture_session(
            runtime_root,
            target_date=target_date,
            batch_size=batch_size,
        )
        if result.get("status") == "DATA_READY":
            from .forward_model_runtime import request_model_worker

            request_model_worker(runtime_root, [result["session_date"]])
        return result
    finally:
        base.sync_forward_calendar = original_sync


def monitoring_status(runtime_root: str | Path) -> dict[str, Any]:
    paths = base.runtime_paths(runtime_root)
    if not paths.runtime_root.exists():
        raise FileNotFoundError(f"runtime root does not exist: {paths.runtime_root}")

    base._reconcile_stale(paths)
    calendar = _load_forward_calendar(paths)
    states = base._session_states(paths)
    earliest = base._earliest_missing(paths, calendar) if len(calendar) else None

    ready_dates = [
        pd.Timestamp(date).date().isoformat()
        for date in calendar
        if states.get(pd.Timestamp(date).date().isoformat()) is not None
        and states[pd.Timestamp(date).date().isoformat()]["state"] == "DATA_READY"
    ]
    if ready_dates:
        from .forward_model_runtime import request_model_worker

        request_model_worker(runtime_root, ready_dates)
    from .o2_1_sealed_shadow_runtime import shadow_status

    shadow = shadow_status(runtime_root)
    from .reliability_v1_forward_shadow import reliability_v1_status

    reliability = reliability_v1_status(runtime_root)

    session_rows: list[dict[str, Any]] = []
    for date in calendar:
        key = pd.Timestamp(date).date().isoformat()
        row = states.get(key)
        session_rows.append(
            {
                "session_date": key,
                "state": str(row["state"]) if row is not None else "AVAILABLE",
                "error_code": row["error_code"] if row is not None else None,
                "error_message": row["error_message"] if row is not None else None,
                "completed_at": row["completed_at"] if row is not None else None,
            }
        )

    start_key = FORWARD_MONITOR_START_DATE.date().isoformat()
    connection = base._connect(paths)
    try:
        models = [
            dict(row)
            for row in connection.execute(
                """
                SELECT * FROM model_runs
                WHERE session_date >= ?
                ORDER BY session_date, generation, model_id
                """,
                (start_key,),
            ).fetchall()
        ]
        ready_count = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM session_snapshots
                WHERE state='DATA_READY' AND session_date >= ?
                """,
                (start_key,),
            ).fetchone()[0]
        )
    finally:
        connection.close()

    return {
        "schema_version": base.MONITOR_SCHEMA_VERSION,
        "runtime_ready": True,
        "runtime_root": str(paths.runtime_root),
        "monitor_start_date": start_key,
        "calendar_ready": bool(len(calendar)),
        "calendar_first_session": calendar.min().date().isoformat() if len(calendar) else None,
        "calendar_last_session": calendar.max().date().isoformat() if len(calendar) else None,
        "next_missing_session": earliest.date().isoformat() if earliest is not None else None,
        "data_ready_sessions": ready_count,
        "sessions": session_rows[-30:],
        "model_runs": models[-200:],
        "o2_1_shadow": shadow,
        "reliability_v1_shadow": reliability,
        "outcome_access": "LOCKED",
        "forward_outcomes_accessed": False,
        "generated_at_utc": base._utcnow(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="IDX Trade operator-facing outcome-blind forward monitoring runtime"
    )
    parser.add_argument("command", choices=("status", "capture", "sync-calendar", "run-models"))
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--date", default=None)
    parser.add_argument("--dates", nargs="*", default=None)
    parser.add_argument("--batch-size", type=int, default=100)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "status":
        result = monitoring_status(args.runtime_root)
    elif args.command == "sync-calendar":
        sessions = sync_forward_calendar(base.runtime_paths(args.runtime_root))
        result = {
            "status": "CALENDAR_READY",
            "monitor_start_date": FORWARD_MONITOR_START_DATE.date().isoformat(),
            "sessions": len(sessions),
            "first": sessions.min().date().isoformat() if len(sessions) else None,
            "last": sessions.max().date().isoformat() if len(sessions) else None,
        }
    elif args.command == "capture":
        result = capture_session(
            args.runtime_root,
            target_date=args.date,
            batch_size=args.batch_size,
        )
    else:
        from .forward_model_runtime import release_worker_lock, run_queued_model_jobs

        try:
            result = run_queued_model_jobs(args.runtime_root, session_dates=args.dates)
        finally:
            release_worker_lock(args.runtime_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "error_code": type(error).__name__.upper(),
                    "error_message": str(error),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise
