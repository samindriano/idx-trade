"""Bridge-aware adapter for the accepted prospective Foreign Flow V2 producer.

The accepted V2 materializer remains authoritative.  This adapter only resolves
which verified session artifact supplies the post-historical rolling context:
canonical EOD when valid, otherwise an independently verified bridge-only
capture.  It never rewrites canonical sessions and never changes V2 formulas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .foreign_flow_representation_v2_runner import read_verified_flow_archive
from .forward_foreign_flow_context_bridge import (
    load_context_bridge_session,
    verify_context_bridge_session,
)
from .forward_foreign_flow_representation_v2 import (
    _merge_unique,
    _normalise_flow,
    _normalise_market,
    _read_verified_forward_flow,
    _read_verified_forward_market,
    materialize_representation_v2_for_session,
)
from .forward_foreign_flow_setup import enrich_prospective_foreign_flow_setup
from .provenance import sha256_file


# Bridge fallback is only authorized for the pre-monitor gap plus the monitor
# start session itself when its preserved canonical capture is invalid.  Any
# later session belongs to the existing canonical EOD runtime and must not be
# silently replaced by a bridge capture.
BRIDGE_FALLBACK_THROUGH = pd.Timestamp("2026-08-10")


def _date(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"invalid date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


def _session_index(path: Path) -> pd.DatetimeIndex:
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError("bridge calendar has no date column")
    values = pd.to_datetime(frame["date"], errors="coerce")
    if values.isna().any():
        raise RuntimeError("bridge calendar contains malformed dates")
    sessions = pd.DatetimeIndex(values).tz_localize(None).normalize().sort_values()
    if len(sessions) == 0 or sessions.has_duplicates:
        raise RuntimeError("bridge calendar is empty or duplicated")
    return sessions


def _verified_calendar(
    path: str | Path,
    expected_sha256: str,
    *,
    role: str,
) -> tuple[Path, str, pd.DatetimeIndex]:
    """Load one pinned calendar without conflating its authority or role."""

    resolved = Path(path).expanduser().resolve()
    expected = str(expected_sha256).lower()
    if not resolved.is_file() or sha256_file(resolved) != expected:
        raise RuntimeError(f"{role} calendar missing or hash-mismatched")
    return resolved, expected, _session_index(resolved)


def _session_set_sha256(sessions: pd.DatetimeIndex) -> str:
    payload = "\n".join(pd.Timestamp(session).date().isoformat() for session in sessions)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _combined_session_index(
    historical_sessions: pd.DatetimeIndex,
    bridge_sessions: pd.DatetimeIndex,
    *,
    historical_cutoff: pd.Timestamp,
    source_session: pd.Timestamp,
) -> tuple[pd.DatetimeIndex, pd.Timestamp]:
    """Validate the pinned calendar seam and return the in-memory union.

    The historical calendar and the bridge extension must share exactly one
    seam date.  The extension may contain ordinary non-trading gaps, but it
    may not overlap the historical range anywhere else or omit the source's
    next official session.
    """

    cutoff = _date(historical_cutoff)
    source = _date(source_session)
    if len(historical_sessions) == 0 or len(bridge_sessions) < 2:
        raise RuntimeError("calendar seam requires non-empty historical and bridge calendars")
    if _date(historical_sessions[-1]) != cutoff:
        raise RuntimeError("historical calendar does not end at the historical market cutoff")
    if _date(bridge_sessions[0]) != cutoff:
        raise RuntimeError("bridge calendar must begin at the historical calendar seam")

    historical_set = set(historical_sessions)
    bridge_set = set(bridge_sessions)
    overlap = historical_set.intersection(bridge_set)
    if overlap != {cutoff}:
        raise RuntimeError("calendar seam has missing or non-seam overlap")
    if any(_date(day) <= cutoff for day in bridge_sessions[1:]):
        raise RuntimeError("bridge calendar contains dates before or at the seam")

    combined = pd.DatetimeIndex(list(historical_sessions) + list(bridge_sessions[1:]))
    if combined.has_duplicates or not combined.is_monotonic_increasing:
        raise RuntimeError("combined calendar is duplicated or out of order")
    if source <= cutoff or source not in bridge_set:
        raise RuntimeError("source session is absent from bridge extension after the seam")
    source_position = int(combined.get_loc(source))
    if source_position >= len(combined) - 1:
        raise RuntimeError("source has no next official feature session")
    target = combined[source_position + 1]
    if target not in bridge_set or target <= source:
        raise RuntimeError("source-to-target calendar transition is invalid")
    return combined, target


def _canonical_dir(runtime_root: Path, session: pd.Timestamp) -> Path:
    return runtime_root / "forward_monitoring" / "sessions" / session.date().isoformat()


def _resolve_extension_session(
    runtime_root: Path,
    session: pd.Timestamp,
    *,
    calendar_path: Path,
    calendar_sha256: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Resolve exactly one verified source for one extension session."""

    session = _date(session)
    key = session.date().isoformat()
    canonical_present = _canonical_dir(runtime_root, session).exists()
    canonical_error: str | None = None
    canonical_market: pd.DataFrame | None = None
    canonical_flow: pd.DataFrame | None = None
    canonical_meta: dict[str, Any] | None = None

    if canonical_present:
        try:
            canonical_market, market_meta = _read_verified_forward_market(runtime_root, key)
            canonical_flow, flow_meta = _read_verified_forward_flow(runtime_root, key)
            canonical_meta = {
                "kind": "CANONICAL_EOD",
                "session_date": key,
                "market": market_meta,
                "flow": flow_meta,
            }
        except Exception as error:  # fail closed unless an authorized bridge is verified below
            canonical_error = f"{type(error).__name__}: {error}"

    bridge_eligible = session <= BRIDGE_FALLBACK_THROUGH
    bridge_valid = bridge_eligible and verify_context_bridge_session(
        runtime_root,
        session,
        calendar_path=calendar_path,
        calendar_sha256=calendar_sha256,
    )

    if canonical_market is not None and canonical_flow is not None:
        if bridge_valid:
            raise RuntimeError(f"AMBIGUOUS_CONTEXT_SOURCES: canonical and bridge both valid for {key}")
        return canonical_market, canonical_flow, canonical_meta or {"kind": "CANONICAL_EOD", "session_date": key}

    if not bridge_eligible:
        if canonical_error is not None:
            raise RuntimeError(f"POST_MONITOR_SESSION_REQUIRES_VALID_CANONICAL_EOD {key}: {canonical_error}")
        raise RuntimeError(f"POST_MONITOR_SESSION_REQUIRES_CANONICAL_EOD: {key}")

    if bridge_valid:
        market, flow, bridge_meta = load_context_bridge_session(
            runtime_root,
            session,
            calendar_path=calendar_path,
            calendar_sha256=calendar_sha256,
        )
        bridge_meta["canonical_directory_present"] = canonical_present
        bridge_meta["canonical_validation_error"] = canonical_error
        bridge_meta["canonical_bytes_mutated"] = False
        bridge_meta["canonical_session_repair"] = False
        bridge_meta["bridge_fallback_through"] = BRIDGE_FALLBACK_THROUGH.date().isoformat()
        return market, flow, bridge_meta

    if canonical_error is not None:
        raise RuntimeError(f"INVALID_CANONICAL_AND_NO_VERIFIED_BRIDGE {key}: {canonical_error}")
    raise RuntimeError(f"MISSING_CONTEXT_SESSION: {key}")


def produce_with_context_bridge(
    *,
    runtime_root: str | Path,
    source_session: str | pd.Timestamp,
    archive_root: str | Path,
    archive_manifest_sha256: str,
    historical_panel_path: str | Path,
    historical_panel_sha256: str,
    historical_sessions_path: str | Path,
    historical_sessions_sha256: str,
    bridge_sessions_path: str | Path,
    bridge_sessions_sha256: str,
    security_master_path: str | Path,
    security_master_sha256: str,
) -> dict[str, Any]:
    """Produce prospective V2 + Setup State from a pinned calendar union.

    The bridge calendar remains the authority for bridge capture verification.
    The historical calendar is a separate pinned input; only their validated
    union is passed in memory to the V2 materializer.
    """

    runtime = Path(runtime_root).expanduser().resolve()
    source = _date(source_session)
    historical_calendar_path, historical_calendar_sha, historical_sessions = _verified_calendar(
        historical_sessions_path,
        historical_sessions_sha256,
        role="historical",
    )
    bridge_calendar_path, bridge_calendar_sha, bridge_sessions = _verified_calendar(
        bridge_sessions_path,
        bridge_sessions_sha256,
        role="bridge extension",
    )

    archive_flow, archive_meta = read_verified_flow_archive(
        Path(archive_root).expanduser().resolve(), archive_manifest_sha256
    )
    panel_path = Path(historical_panel_path).expanduser().resolve()
    master_path = Path(security_master_path).expanduser().resolve()
    if not panel_path.is_file() or sha256_file(panel_path) != historical_panel_sha256.lower():
        raise RuntimeError("historical market panel hash mismatch")
    if not master_path.is_file() or sha256_file(master_path) != security_master_sha256.lower():
        raise RuntimeError("security master hash mismatch")

    historical_market = pd.read_parquet(panel_path).rename(columns={"date": "session_date"})
    historical_market = _normalise_market(historical_market)
    historical_cutoff = historical_market["session_date"].max()
    historical_start = _date(historical_sessions[0])
    if historical_market["session_date"].min() < historical_start:
        raise RuntimeError("historical market begins before pinned historical calendar")
    if historical_cutoff >= source:
        raise RuntimeError("bridge adapter is only for source sessions after historical market cutoff")
    sessions, target = _combined_session_index(
        historical_sessions,
        bridge_sessions,
        historical_cutoff=historical_cutoff,
        source_session=source,
    )

    archive_dates = pd.to_datetime(archive_flow["session_date"], errors="coerce")
    if archive_dates.isna().any():
        raise RuntimeError("historical Foreign Flow archive has malformed session dates")
    if getattr(archive_dates.dt, "tz", None) is not None:
        archive_dates = archive_dates.dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
    archive_dates = archive_dates.dt.normalize()
    # The accepted Foreign Flow archive is broader than the accepted market
    # panel. Rows before the pinned historical calendar have no validated
    # market/volume context and must not enter the materializer input.
    archive_flow = archive_flow.loc[
        archive_dates.ge(historical_start) & archive_dates.le(historical_cutoff)
    ].copy()
    archive_flow = _normalise_flow(archive_flow)

    extension_sessions = sessions[(sessions > historical_cutoff) & (sessions <= source)]
    if len(extension_sessions) == 0:
        raise RuntimeError("no bridge extension sessions are required")

    market_parts: list[pd.DataFrame] = [historical_market]
    flow_parts: list[pd.DataFrame] = [archive_flow]
    session_sources: list[dict[str, Any]] = []
    for day in extension_sessions:
        market, flow, meta = _resolve_extension_session(
            runtime,
            pd.Timestamp(day),
            calendar_path=bridge_calendar_path,
            calendar_sha256=bridge_calendar_sha,
        )
        market_parts.append(_normalise_market(market))
        flow_parts.append(_normalise_flow(flow))
        session_sources.append(meta)

    market = historical_market
    flow = archive_flow
    for part in market_parts[1:]:
        market = _merge_unique(market, part, ["ticker", "session_date"], label="bridge market context")
    for part in flow_parts[1:]:
        flow = _merge_unique(flow, part, ["ticker", "session_date"], label="bridge Foreign Flow context")

    available_market = set(pd.to_datetime(market["session_date"]).dt.normalize())
    available_flow = set(pd.to_datetime(flow["session_date"]).dt.normalize())
    missing = [
        pd.Timestamp(day).date().isoformat()
        for day in extension_sessions
        if pd.Timestamp(day) not in available_market or pd.Timestamp(day) not in available_flow
    ]
    if missing:
        raise RuntimeError("MISSING_BRIDGE_ROLLING_CONTEXT_SESSIONS: " + ",".join(missing))

    provenance = {
        "archive": {
            key: archive_meta[key]
            for key in (
                "archive_root",
                "archive_manifest_path",
                "archive_manifest_sha256",
                "archive_normalized_session_count",
                "archive_normalized_row_count",
                "archive_normalized_artifact_count",
                "archive_normalized_first_session",
                "archive_normalized_last_session",
            )
        },
        "historical_panel_path": str(panel_path),
        "historical_panel_sha256": historical_panel_sha256.lower(),
        # Setup State's existing validator consumes the bridge file because it
        # contains the seam/source/target transition.  The complete materializer
        # session index is the in-memory union below, never a new calendar file.
        "official_sessions_path": str(bridge_calendar_path),
        "official_sessions_sha256": bridge_calendar_sha,
        "official_sessions_role": "PINNED_BRIDGE_EXTENSION_CALENDAR_FOR_SETUP_SEAM",
        "historical_sessions_path": str(historical_calendar_path),
        "historical_sessions_sha256": historical_calendar_sha,
        "bridge_sessions_path": str(bridge_calendar_path),
        "bridge_sessions_sha256": bridge_calendar_sha,
        "combined_session_set_sha256": _session_set_sha256(sessions),
        "combined_session_count": len(sessions),
        "combined_session_first": sessions[0].date().isoformat(),
        "combined_session_last": sessions[-1].date().isoformat(),
        "security_master_path": str(master_path),
        "security_master_sha256": security_master_sha256.lower(),
        "source_session": source.date().isoformat(),
        "feature_session": target.date().isoformat(),
        "rolling_context_policy": "PINNED_HISTORY_PLUS_VERIFIED_CANONICAL_OR_BRIDGE_SESSIONS",
        "extension_session_sources": session_sources,
        "bridge_namespace": str(runtime / "forward_monitoring" / "context_bridge"),
        "bridge_fallback_through": BRIDGE_FALLBACK_THROUGH.date().isoformat(),
        "canonical_session_repair": False,
        "operator_calendar_mutated": False,
        "operator_counter_modified": False,
        "no_model_access": True,
        "outcome_blind": True,
    }

    output_dir = (
        runtime
        / "forward_monitoring"
        / "prospective"
        / "foreign_flow_representation_v2"
        / target.date().isoformat()
    )
    materialized = materialize_representation_v2_for_session(
        flow=flow,
        market=market,
        security_master=pd.read_csv(master_path),
        official_sessions=sessions,
        source_session=source,
        output_directory=output_dir,
        input_provenance=provenance,
    )
    materialized["prospective_setup_state"] = enrich_prospective_foreign_flow_setup(
        materialized["artifact_path"],
        materialized["manifest_path"],
    )
    materialized["context_bridge"] = {
        "historical_cutoff": historical_cutoff.date().isoformat(),
        "extension_sessions": [pd.Timestamp(day).date().isoformat() for day in extension_sessions],
        "source_kinds": [str(item.get("kind")) for item in session_sources],
        "historical_calendar_path": str(historical_calendar_path),
        "historical_calendar_sha256": historical_calendar_sha,
        "bridge_calendar_path": str(bridge_calendar_path),
        "bridge_calendar_sha256": bridge_calendar_sha,
        "combined_session_set_sha256": _session_set_sha256(sessions),
        "combined_session_count": len(sessions),
        "bridge_fallback_through": BRIDGE_FALLBACK_THROUGH.date().isoformat(),
        "operator_calendar_mutated": False,
        "operator_counter_modified": False,
    }
    return materialized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge-aware Foreign Flow prospective V2 producer")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--source-session", required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--archive-manifest-sha256", required=True)
    parser.add_argument("--historical-panel", type=Path, required=True)
    parser.add_argument("--historical-panel-sha256", required=True)
    parser.add_argument("--historical-sessions", type=Path, required=True)
    parser.add_argument("--historical-sessions-sha256", required=True)
    parser.add_argument("--bridge-sessions", type=Path, required=True)
    parser.add_argument("--bridge-sessions-sha256", required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--security-master-sha256", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = produce_with_context_bridge(
        runtime_root=args.runtime_root,
        source_session=args.source_session,
        archive_root=args.archive_root,
        archive_manifest_sha256=args.archive_manifest_sha256,
        historical_panel_path=args.historical_panel,
        historical_panel_sha256=args.historical_panel_sha256,
        historical_sessions_path=args.historical_sessions,
        historical_sessions_sha256=args.historical_sessions_sha256,
        bridge_sessions_path=args.bridge_sessions,
        bridge_sessions_sha256=args.bridge_sessions_sha256,
        security_master_path=args.security_master,
        security_master_sha256=args.security_master_sha256,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
