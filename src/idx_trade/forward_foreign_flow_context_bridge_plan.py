"""Read-only readiness planner for the Foreign Flow rolling-context bridge."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .forward_foreign_flow_context_bridge import verify_context_bridge_session
from .forward_foreign_flow_context_bridge_run import (
    BRIDGE_FALLBACK_THROUGH,
    _read_verified_forward_flow,
    _read_verified_forward_market,
)
from .provenance import sha256_file


def _date(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"invalid date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


def _sessions(path: Path) -> pd.DatetimeIndex:
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError("bridge calendar has no date column")
    values = pd.to_datetime(frame["date"], errors="coerce")
    if values.isna().any():
        raise RuntimeError("bridge calendar contains malformed dates")
    result = pd.DatetimeIndex(values).tz_localize(None).normalize().sort_values()
    if len(result) == 0 or result.has_duplicates:
        raise RuntimeError("bridge calendar is empty or duplicated")
    return result


def plan_context_bridge(
    runtime_root: str | Path,
    *,
    historical_cutoff: str | pd.Timestamp,
    source_session: str | pd.Timestamp,
    official_sessions_path: str | Path,
    official_sessions_sha256: str,
) -> dict[str, Any]:
    """Inspect local artifacts only; perform zero provider calls and zero writes."""

    root = Path(runtime_root).expanduser().resolve()
    cutoff = _date(historical_cutoff)
    source = _date(source_session)
    calendar = Path(official_sessions_path).expanduser().resolve()
    if not calendar.is_file() or sha256_file(calendar) != official_sessions_sha256.lower():
        raise RuntimeError("bridge official calendar missing or hash-mismatched")
    sessions = _sessions(calendar)
    if source not in set(sessions):
        raise RuntimeError("source session is absent from bridge official calendar")
    required = sessions[(sessions > cutoff) & (sessions <= source)]
    if len(required) == 0:
        raise RuntimeError("no post-historical context sessions are required")

    rows: list[dict[str, Any]] = []
    bridge_required: list[str] = []
    canonical_required: list[str] = []
    ambiguous: list[str] = []
    invalid_canonical: list[str] = []

    for day in required:
        session = pd.Timestamp(day)
        key = session.date().isoformat()
        canonical_dir = root / "forward_monitoring" / "sessions" / key
        canonical_present = canonical_dir.exists()
        canonical_valid = False
        canonical_error: str | None = None
        if canonical_present:
            try:
                _read_verified_forward_market(root, key)
                _read_verified_forward_flow(root, key)
                canonical_valid = True
            except Exception as error:
                canonical_error = f"{type(error).__name__}: {error}"
                invalid_canonical.append(key)

        bridge_valid = verify_context_bridge_session(
            root,
            session,
            calendar_path=calendar,
            calendar_sha256=official_sessions_sha256.lower(),
        )

        if canonical_valid and bridge_valid and session <= BRIDGE_FALLBACK_THROUGH:
            status = "AMBIGUOUS_CANONICAL_AND_BRIDGE"
            ambiguous.append(key)
        elif canonical_valid:
            status = "CANONICAL_READY"
        elif session <= BRIDGE_FALLBACK_THROUGH and bridge_valid:
            status = "BRIDGE_READY"
        elif session <= BRIDGE_FALLBACK_THROUGH:
            status = "NEED_BRIDGE_CAPTURE"
            bridge_required.append(key)
        else:
            status = "NEED_CANONICAL_EOD"
            canonical_required.append(key)

        rows.append(
            {
                "session_date": key,
                "status": status,
                "canonical_present": canonical_present,
                "canonical_valid": canonical_valid,
                "canonical_error": canonical_error,
                "bridge_valid": bridge_valid,
                "bridge_eligible": bool(session <= BRIDGE_FALLBACK_THROUGH),
            }
        )

    ready = not bridge_required and not canonical_required and not ambiguous
    return {
        "status": "CONTEXT_BRIDGE_READY" if ready else "CONTEXT_BRIDGE_ACTION_REQUIRED",
        "runtime_root": str(root),
        "historical_cutoff": cutoff.date().isoformat(),
        "source_session": source.date().isoformat(),
        "bridge_fallback_through": BRIDGE_FALLBACK_THROUGH.date().isoformat(),
        "official_sessions_path": str(calendar),
        "official_sessions_sha256": official_sessions_sha256.lower(),
        "required_session_count": int(len(required)),
        "bridge_capture_required": bridge_required,
        "canonical_eod_required": canonical_required,
        "ambiguous_sessions": ambiguous,
        "invalid_canonical_sessions": sorted(set(invalid_canonical)),
        "sessions": rows,
        "provider_calls": 0,
        "writes": 0,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "operator_counter_modified": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Foreign Flow context bridge planner")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--historical-cutoff", required=True)
    parser.add_argument("--source-session", required=True)
    parser.add_argument("--official-sessions", type=Path, required=True)
    parser.add_argument("--official-sessions-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = plan_context_bridge(
        args.runtime_root,
        historical_cutoff=args.historical_cutoff,
        source_session=args.source_session,
        official_sessions_path=args.official_sessions,
        official_sessions_sha256=args.official_sessions_sha256,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if result["status"] == "CONTEXT_BRIDGE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
