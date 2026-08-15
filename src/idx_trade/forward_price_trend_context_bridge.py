"""Read-only bridge-aware runtime adapter for accepted Price State V1.

This module resolves the already captured market context between the accepted
historical Clean-V2 panel and a completed canonical EOD source session.  It
never calls a provider, never captures/repairs a session, and never changes the
accepted Price / Trend / Confirmation State V1 formulas.

Policy mirrors the independently reviewed Foreign Flow context bridge:

- historical context ends at the pinned seam;
- bridge-only market artifacts may supply extension sessions only through
  2026-08-10;
- sessions after 2026-08-10 require valid canonical EOD ``model_input``;
- canonical + bridge both valid on a bridge-eligible date is ambiguous and
  fails closed;
- the historical and bridge calendars remain separate pinned authorities and
  are unioned only in memory.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .forward_price_trend_state import (
    ACCEPTED_PRICE_STATE_COMMIT,
    ARTIFACT_FILENAME,
    MANIFEST_FILENAME,
    OUTPUT_COLUMNS,
    SIDECAR_SCHEMA,
    STATE_COLUMNS,
    _context_fingerprint,
    _date,
    _merge_unique,
    _normalise_market,
    _validate_state_artifact,
    materialize_price_trend_state_for_session,
)
from .canonical_eod_calendar_parent_attestation import (
    ACCEPTED_BRIDGE_CALENDAR_SHA256,
    verify_canonical_eod_calendar_parent_attestation,
)
from .provenance import sha256_file


BRIDGE_FALLBACK_THROUGH = pd.Timestamp("2026-08-10")
RUNTIME_CONTEXT_POLICY = "PINNED_HISTORY_PLUS_VERIFIED_BRIDGE_THROUGH_2026_08_10_THEN_CANONICAL_EOD"

# Exact scientific/runtime identities established by the accepted Foreign Flow
# V2 census and calendar-bridge remediation.  These strings are documentation
# and convenience defaults; generic test/forensic callers may supply an
# explicit RuntimeContextPins instance instead.
APPROVED_RUNTIME_ROOT = r"D:\Documents\Project\idx-trade-data-gate-20260808v"
APPROVED_HISTORICAL_PANEL = (
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809"
    r"\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet"
)
APPROVED_HISTORICAL_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
APPROVED_HISTORICAL_CALENDAR = (
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809"
    r"\official_exchange_sessions_1260.csv"
)
APPROVED_HISTORICAL_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
APPROVED_BRIDGE_CALENDAR = (
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\context_bridge"
    r"\calendar\ranges\2026-07-31_2026-08-13\exchange_sessions.csv"
)
APPROVED_BRIDGE_CALENDAR_SHA256 = "51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e"
APPROVED_COMBINED_SESSION_SET_SHA256 = "dd51d3dbcb29915ff80612d84a912da237331e979ee3847bd8fd4984ead413dd"

BRIDGE_SCHEMA = "idx-trade/foreign-flow-forward-context-bridge-v1"
BRIDGE_STATUS = "FOREIGN_FLOW_CONTEXT_BRIDGE_READY"
BRIDGE_MARKET_FILENAME = "market_context.parquet"
BRIDGE_FLOW_FILENAME = "foreign_flow.parquet"
BRIDGE_RAW_FILENAME = "idx_stock_summary.raw.json"
BRIDGE_MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class RuntimeContextPins:
    historical_panel_path: Path
    historical_panel_sha256: str
    historical_calendar_path: Path
    historical_calendar_sha256: str
    bridge_calendar_path: Path
    bridge_calendar_sha256: str
    expected_combined_session_set_sha256: str | None = None


def approved_runtime_context_pins() -> RuntimeContextPins:
    """Return the exact accepted 2026-08-15 runtime-context identity."""

    return RuntimeContextPins(
        historical_panel_path=Path(APPROVED_HISTORICAL_PANEL),
        historical_panel_sha256=APPROVED_HISTORICAL_PANEL_SHA256,
        historical_calendar_path=Path(APPROVED_HISTORICAL_CALENDAR),
        historical_calendar_sha256=APPROVED_HISTORICAL_CALENDAR_SHA256,
        bridge_calendar_path=Path(APPROVED_BRIDGE_CALENDAR),
        bridge_calendar_sha256=APPROVED_BRIDGE_CALENDAR_SHA256,
        expected_combined_session_set_sha256=APPROVED_COMBINED_SESSION_SET_SHA256,
    )


def _session_index(path: Path) -> pd.DatetimeIndex:
    frame = pd.read_csv(path)
    column = "date" if "date" in frame.columns else "session_date" if "session_date" in frame.columns else None
    if column is None:
        raise RuntimeError(f"official calendar has no date column: {path}")
    values = pd.to_datetime(frame[column], errors="coerce")
    if values.isna().any():
        raise RuntimeError(f"official calendar contains malformed dates: {path}")
    if isinstance(values.dtype, pd.DatetimeTZDtype):
        values = values.dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
    sessions = pd.DatetimeIndex(values.dt.normalize()).sort_values()
    if len(sessions) == 0 or sessions.has_duplicates:
        raise RuntimeError(f"official calendar is empty or duplicated: {path}")
    return sessions


def _verified_calendar(path: Path, expected_sha256: str, *, role: str) -> tuple[Path, str, pd.DatetimeIndex]:
    resolved = path.expanduser().resolve()
    expected = str(expected_sha256).lower()
    if len(expected) != 64 or not resolved.is_file() or sha256_file(resolved) != expected:
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
    expected_sha256: str | None,
) -> tuple[pd.DatetimeIndex, pd.Timestamp]:
    cutoff = _date(historical_cutoff)
    source = _date(source_session)
    if len(historical_sessions) == 0 or len(bridge_sessions) < 2:
        raise RuntimeError("calendar seam requires non-empty historical and bridge calendars")
    if _date(historical_sessions[-1]) != cutoff:
        raise RuntimeError("historical calendar does not end at historical market cutoff")
    if _date(bridge_sessions[0]) != cutoff:
        raise RuntimeError("bridge calendar must begin at historical calendar seam")
    overlap = set(historical_sessions).intersection(set(bridge_sessions))
    if overlap != {cutoff}:
        raise RuntimeError("calendar seam has missing or non-seam overlap")
    if any(_date(day) <= cutoff for day in bridge_sessions[1:]):
        raise RuntimeError("bridge calendar contains dates before or at seam")

    combined = pd.DatetimeIndex(list(historical_sessions) + list(bridge_sessions[1:]))
    if combined.has_duplicates or not combined.is_monotonic_increasing:
        raise RuntimeError("combined calendar is duplicated or out of order")
    combined_sha = _session_set_sha256(combined)
    if expected_sha256 is not None and combined_sha != str(expected_sha256).lower():
        raise RuntimeError("combined official session-set hash mismatch")
    if source <= cutoff or source not in set(bridge_sessions):
        raise RuntimeError("source session is absent from bridge extension after seam")
    position = int(combined.get_loc(source))
    if position >= len(combined) - 1:
        raise RuntimeError("source has no next official feature session")
    target = combined[position + 1]
    if target not in set(bridge_sessions) or target <= source:
        raise RuntimeError("source-to-target calendar transition is invalid")
    return combined, target


def _canonical_session_dir(runtime_root: Path, session: pd.Timestamp) -> Path:
    return runtime_root / "forward_monitoring" / "sessions" / session.date().isoformat()


def _read_parent_calendar(
    parent: Mapping[str, Any],
    session: pd.Timestamp,
    *,
    runtime_root: Path | None = None,
) -> tuple[Path, str, Path | None]:
    calendar = Path(str(parent.get("calendar_path") or "")).expanduser().resolve()
    expected = str(parent.get("calendar_sha256") or "").lower()
    if len(expected) == 64 and calendar.is_file() and sha256_file(calendar) == expected:
        if session not in set(_session_index(calendar)):
            raise RuntimeError("canonical session is absent from its own pinned calendar")
        return calendar, expected, None

    if runtime_root is not None:
        attestation = (
            runtime_root.resolve()
            / "forward_monitoring"
            / "provenance_attestations"
            / "canonical_eod_calendar_parent_v1"
            / session.date().isoformat()
            / "attestation.json"
        )
        accepted_bridge = Path(APPROVED_BRIDGE_CALENDAR).expanduser().resolve()
        if verify_canonical_eod_calendar_parent_attestation(
            attestation,
            expected_session=session,
            expected_bridge_calendar_path=accepted_bridge,
            expected_bridge_calendar_sha256=ACCEPTED_BRIDGE_CALENDAR_SHA256,
        ):
            return calendar, expected, attestation
    raise RuntimeError("canonical parent calendar missing or hash-mismatched")


def _read_verified_canonical_market(
    runtime_root: Path,
    session: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    session = _date(session)
    key = session.date().isoformat()
    directory = _canonical_session_dir(runtime_root, session).resolve()
    manifest_path = (directory / "manifest.json").resolve()
    snapshot_path = (directory / "model_input.parquet").resolve()
    if not manifest_path.is_file() or not snapshot_path.is_file():
        raise FileNotFoundError(f"canonical DATA_READY artifacts missing for {key}")
    parent = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(parent, Mapping):
        raise RuntimeError(f"canonical manifest is not an object for {key}")
    if parent.get("status") != "DATA_READY" or str(parent.get("session_date")) != key:
        raise RuntimeError(f"canonical session manifest is not exact DATA_READY for {key}")
    if parent.get("outcome_blind") is not True or parent.get("forward_outcomes_accessed") is not False:
        raise RuntimeError(f"canonical session manifest is not outcome-blind for {key}")
    declared_snapshot = Path(str(parent.get("snapshot_path") or "")).expanduser().resolve()
    if declared_snapshot != snapshot_path:
        raise RuntimeError(f"canonical snapshot path identity mismatch for {key}")
    expected_snapshot_sha = str(parent.get("snapshot_sha256") or "").lower()
    if len(expected_snapshot_sha) != 64 or sha256_file(snapshot_path) != expected_snapshot_sha:
        raise RuntimeError(f"canonical snapshot hash mismatch for {key}")
    parent_calendar, parent_calendar_sha, calendar_attestation = _read_parent_calendar(
        parent,
        session,
        runtime_root=runtime_root,
    )

    market = _normalise_market(pd.read_parquet(snapshot_path))
    if market.empty or not market["session_date"].eq(session).all():
        raise RuntimeError(f"canonical snapshot session mismatch for {key}")
    metadata = {
        "kind": "CANONICAL_EOD",
        "session_date": key,
        "parent_manifest_path": str(manifest_path),
        "parent_manifest_sha256": sha256_file(manifest_path),
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": expected_snapshot_sha,
        "parent_calendar_path": str(parent_calendar),
        "parent_calendar_sha256": parent_calendar_sha,
        "row_count": int(len(market)),
    }
    if calendar_attestation is not None:
        metadata["calendar_parent_attestation_path"] = str(calendar_attestation)
        metadata["calendar_parent_attestation_sha256"] = sha256_file(calendar_attestation)
    return market, metadata


def _bridge_session_dir(runtime_root: Path, session: pd.Timestamp) -> Path:
    return runtime_root / "forward_monitoring" / "context_bridge" / "sessions" / session.date().isoformat()


def _read_verified_bridge_market(
    runtime_root: Path,
    session: pd.Timestamp,
    *,
    bridge_calendar_path: Path,
    bridge_calendar_sha256: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    session = _date(session)
    key = session.date().isoformat()
    directory = _bridge_session_dir(runtime_root, session).resolve()
    manifest_path = (directory / BRIDGE_MANIFEST_FILENAME).resolve()
    market_path = (directory / BRIDGE_MARKET_FILENAME).resolve()
    flow_path = (directory / BRIDGE_FLOW_FILENAME).resolve()
    raw_path = (directory / BRIDGE_RAW_FILENAME).resolve()
    if not all(path.is_file() for path in (manifest_path, market_path, flow_path, raw_path)):
        raise FileNotFoundError(f"bridge artifacts missing for {key}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise RuntimeError(f"bridge manifest is not an object for {key}")
    if manifest.get("status") != BRIDGE_STATUS or manifest.get("schema") != BRIDGE_SCHEMA:
        raise RuntimeError(f"bridge status/schema mismatch for {key}")
    if manifest.get("bridge_only") is not True or manifest.get("canonical_session_repair") is not False:
        raise RuntimeError(f"bridge role semantics invalid for {key}")
    if manifest.get("outcome_blind") is not True or manifest.get("forward_outcomes_accessed") is not False:
        raise RuntimeError(f"bridge artifact is not outcome-blind for {key}")
    if manifest.get("outcomes_or_labels_accessed") is not False:
        raise RuntimeError(f"bridge artifact accessed outcomes/labels for {key}")
    if manifest.get("model_fit") is not False or manifest.get("model_scoring") is not False:
        raise RuntimeError(f"bridge artifact contains model access for {key}")
    if str(manifest.get("session_date")) != key:
        raise RuntimeError(f"bridge session date mismatch for {key}")

    calendar = bridge_calendar_path.expanduser().resolve()
    expected_calendar_sha = str(bridge_calendar_sha256).lower()
    if not calendar.is_file() or sha256_file(calendar) != expected_calendar_sha:
        raise RuntimeError("bridge calendar missing or hash-mismatched")
    if Path(str(manifest.get("calendar_path") or "")).expanduser().resolve() != calendar:
        raise RuntimeError(f"bridge calendar path identity mismatch for {key}")
    if str(manifest.get("calendar_sha256") or "").lower() != expected_calendar_sha:
        raise RuntimeError(f"bridge calendar hash pin mismatch for {key}")
    if session not in set(_session_index(calendar)):
        raise RuntimeError(f"bridge session is absent from bridge calendar for {key}")

    for path, path_key, hash_key in (
        (market_path, "market_context_path", "market_context_sha256"),
        (flow_path, "foreign_flow_path", "foreign_flow_sha256"),
        (raw_path, "source_raw_path", "source_raw_sha256"),
    ):
        declared = Path(str(manifest.get(path_key) or "")).expanduser().resolve()
        expected_sha = str(manifest.get(hash_key) or "").lower()
        if declared != path or len(expected_sha) != 64 or sha256_file(path) != expected_sha:
            raise RuntimeError(f"bridge {path_key} identity/hash mismatch for {key}")

    source = manifest.get("stock_summary_source")
    if not isinstance(source, Mapping) or source.get("completeness_status") != "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE":
        raise RuntimeError(f"bridge Stock Summary completeness is invalid for {key}")
    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    records_total = int(source.get("records_total", -1))
    if not isinstance(raw_payload, Mapping) or int(raw_payload.get("recordsTotal", -1)) != records_total:
        raise RuntimeError(f"bridge raw Stock Summary recordsTotal mismatch for {key}")
    if int(manifest.get("foreign_flow_rows", -1)) != records_total:
        raise RuntimeError(f"bridge Foreign Flow row-count provenance mismatch for {key}")

    market = _normalise_market(pd.read_parquet(market_path))
    if market.empty or not market["session_date"].eq(session).all():
        raise RuntimeError(f"bridge market session mismatch for {key}")
    if int(manifest.get("market_rows", -1)) != len(market):
        raise RuntimeError(f"bridge market row-count mismatch for {key}")
    return market, {
        "kind": "BRIDGE_ONLY",
        "session_date": key,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "market_context_path": str(market_path),
        "market_context_sha256": sha256_file(market_path),
        "foreign_flow_path": str(flow_path),
        "foreign_flow_sha256": sha256_file(flow_path),
        "source_raw_path": str(raw_path),
        "source_raw_sha256": sha256_file(raw_path),
        "bridge_calendar_path": str(calendar),
        "bridge_calendar_sha256": expected_calendar_sha,
        "row_count": int(len(market)),
        "canonical_session_repair": False,
    }


def _canonical_present(runtime_root: Path, session: pd.Timestamp) -> bool:
    return _canonical_session_dir(runtime_root, session).exists()


def _bridge_present(runtime_root: Path, session: pd.Timestamp) -> bool:
    return _bridge_session_dir(runtime_root, session).exists()


def _resolve_extension_market(
    runtime_root: Path,
    session: pd.Timestamp,
    *,
    bridge_calendar_path: Path,
    bridge_calendar_sha256: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    session = _date(session)
    key = session.date().isoformat()
    canonical_exists = _canonical_present(runtime_root, session)
    bridge_exists = _bridge_present(runtime_root, session)
    canonical_market: pd.DataFrame | None = None
    canonical_meta: dict[str, Any] | None = None
    canonical_error: str | None = None
    if canonical_exists:
        try:
            canonical_market, canonical_meta = _read_verified_canonical_market(runtime_root, session)
        except Exception as error:
            canonical_error = f"{type(error).__name__}: {error}"

    bridge_eligible = session <= BRIDGE_FALLBACK_THROUGH
    bridge_market: pd.DataFrame | None = None
    bridge_meta: dict[str, Any] | None = None
    bridge_error: str | None = None
    if bridge_exists and bridge_eligible:
        try:
            bridge_market, bridge_meta = _read_verified_bridge_market(
                runtime_root,
                session,
                bridge_calendar_path=bridge_calendar_path,
                bridge_calendar_sha256=bridge_calendar_sha256,
            )
        except Exception as error:
            bridge_error = f"{type(error).__name__}: {error}"

    if canonical_market is not None:
        if bridge_market is not None:
            raise RuntimeError(f"AMBIGUOUS_CONTEXT_SOURCES: canonical and bridge both valid for {key}")
        return canonical_market, canonical_meta or {"kind": "CANONICAL_EOD", "session_date": key}

    if not bridge_eligible:
        if canonical_error:
            raise RuntimeError(f"POST_MONITOR_SESSION_REQUIRES_VALID_CANONICAL_EOD {key}: {canonical_error}")
        raise RuntimeError(f"POST_MONITOR_SESSION_REQUIRES_CANONICAL_EOD: {key}")

    if bridge_market is not None:
        assert bridge_meta is not None
        bridge_meta["canonical_directory_present"] = canonical_exists
        bridge_meta["canonical_validation_error"] = canonical_error
        bridge_meta["bridge_fallback_through"] = BRIDGE_FALLBACK_THROUGH.date().isoformat()
        return bridge_market, bridge_meta

    details = "; ".join(part for part in (canonical_error, bridge_error) if part)
    if canonical_exists or bridge_exists:
        raise RuntimeError(f"INVALID_CONTEXT_AND_NO_VERIFIED_SOURCE {key}: {details}")
    raise RuntimeError(f"MISSING_CONTEXT_SESSION: {key}")


def _state_distributions(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    return {
        column: {
            str(key): int(value)
            for key, value in frame[column].value_counts(dropna=False).sort_index().items()
        }
        for column in STATE_COLUMNS
    }


def produce_price_trend_state_with_context_bridge(
    *,
    runtime_root: str | Path,
    source_session: str | pd.Timestamp,
    pins: RuntimeContextPins,
) -> dict[str, Any]:
    """Materialize accepted Price State V1 using only verified stored context."""

    runtime = Path(runtime_root).expanduser().resolve()
    source = _date(source_session)
    historical_panel = pins.historical_panel_path.expanduser().resolve()
    historical_sha = str(pins.historical_panel_sha256).lower()
    if len(historical_sha) != 64 or not historical_panel.is_file() or sha256_file(historical_panel) != historical_sha:
        raise RuntimeError("historical market panel missing or hash-mismatched")

    historical_calendar, historical_calendar_sha, historical_sessions = _verified_calendar(
        pins.historical_calendar_path,
        pins.historical_calendar_sha256,
        role="historical",
    )
    bridge_calendar, bridge_calendar_sha, bridge_sessions = _verified_calendar(
        pins.bridge_calendar_path,
        pins.bridge_calendar_sha256,
        role="bridge extension",
    )

    historical_market = _normalise_market(pd.read_parquet(historical_panel))
    historical_cutoff = historical_market["session_date"].max()
    historical_start = historical_sessions[0]
    if historical_market["session_date"].min() < historical_start:
        raise RuntimeError("historical market begins before pinned historical calendar")
    if not historical_market["session_date"].isin(set(historical_sessions)).all():
        raise RuntimeError("historical market contains dates outside pinned historical calendar")
    if historical_cutoff >= source:
        raise RuntimeError("context bridge is only for source sessions after historical cutoff")

    sessions, target = _combined_session_index(
        historical_sessions,
        bridge_sessions,
        historical_cutoff=historical_cutoff,
        source_session=source,
        expected_sha256=pins.expected_combined_session_set_sha256,
    )
    extension_sessions = sessions[(sessions > historical_cutoff) & (sessions <= source)]
    if len(extension_sessions) == 0:
        raise RuntimeError("no runtime-context extension sessions are required")

    market = historical_market
    session_sources: list[dict[str, Any]] = []
    for day in extension_sessions:
        part, meta = _resolve_extension_market(
            runtime,
            pd.Timestamp(day),
            bridge_calendar_path=bridge_calendar,
            bridge_calendar_sha256=bridge_calendar_sha,
        )
        market = _merge_unique(market, part, label="price-state bridge market context")
        session_sources.append(meta)

    available_sessions = set(pd.to_datetime(market["session_date"]).dt.normalize())
    missing = [
        pd.Timestamp(day).date().isoformat()
        for day in extension_sessions
        if pd.Timestamp(day) not in available_sessions
    ]
    if missing:
        raise RuntimeError("MISSING_PRICE_STATE_ROLLING_CONTEXT_SESSIONS: " + ",".join(missing))
    market = market.loc[market["session_date"].le(source)].reset_index(drop=True)

    provenance: dict[str, Any] = {
        "runtime_context_policy": RUNTIME_CONTEXT_POLICY,
        "historical_panel_path": str(historical_panel),
        "historical_panel_sha256": historical_sha,
        "historical_calendar_path": str(historical_calendar),
        "historical_calendar_sha256": historical_calendar_sha,
        "bridge_calendar_path": str(bridge_calendar),
        "bridge_calendar_sha256": bridge_calendar_sha,
        "combined_session_set_sha256": _session_set_sha256(sessions),
        "combined_session_count": int(len(sessions)),
        "combined_session_first": sessions[0].date().isoformat(),
        "combined_session_last": sessions[-1].date().isoformat(),
        "historical_cutoff": historical_cutoff.date().isoformat(),
        "source_session": source.date().isoformat(),
        "feature_session": target.date().isoformat(),
        "extension_session_sources": session_sources,
        "bridge_fallback_through": BRIDGE_FALLBACK_THROUGH.date().isoformat(),
        "canonical_session_repair": False,
        "provider_calls": 0,
        "outcome_blind": True,
    }

    output_directory = (
        runtime
        / "forward_monitoring"
        / "prospective"
        / "price_trend_confirmation_state_v1"
        / target.date().isoformat()
    )
    result = materialize_price_trend_state_for_session(
        market_history=market,
        official_sessions=sessions,
        source_session=source,
        output_directory=output_directory,
        input_provenance=provenance,
    )
    result["runtime_context"] = {
        "historical_cutoff": historical_cutoff.date().isoformat(),
        "extension_sessions": [pd.Timestamp(day).date().isoformat() for day in extension_sessions],
        "source_kinds": [str(item.get("kind")) for item in session_sources],
        "historical_calendar_sha256": historical_calendar_sha,
        "bridge_calendar_sha256": bridge_calendar_sha,
        "combined_session_set_sha256": _session_set_sha256(sessions),
        "combined_session_count": int(len(sessions)),
        "bridge_fallback_through": BRIDGE_FALLBACK_THROUGH.date().isoformat(),
        "provider_calls": 0,
        "outcome_blind": True,
    }
    return result


def _verify_source_meta(
    runtime_root: Path,
    meta: Mapping[str, Any],
    *,
    bridge_calendar_path: Path,
    bridge_calendar_sha256: str,
) -> bool:
    kind = str(meta.get("kind") or "")
    session = _date(meta.get("session_date"))
    if kind == "CANONICAL_EOD":
        _, fresh = _read_verified_canonical_market(runtime_root, session)
    elif kind == "BRIDGE_ONLY":
        _, fresh = _read_verified_bridge_market(
            runtime_root,
            session,
            bridge_calendar_path=bridge_calendar_path,
            bridge_calendar_sha256=bridge_calendar_sha256,
        )
        # Runtime-only diagnostic fields are deterministic but not emitted by
        # the raw bridge loader; compare the pinned identity fields below.
    else:
        return False
    identity_fields = (
        "kind",
        "session_date",
        "row_count",
    )
    for field in identity_fields:
        if meta.get(field) != fresh.get(field):
            return False
    if kind == "CANONICAL_EOD":
        fields = (
            "parent_manifest_path",
            "parent_manifest_sha256",
            "snapshot_path",
            "snapshot_sha256",
            "parent_calendar_path",
            "parent_calendar_sha256",
        )
        if "calendar_parent_attestation_path" in fresh:
            fields += (
                "calendar_parent_attestation_path",
                "calendar_parent_attestation_sha256",
            )
    else:
        fields = (
            "manifest_path",
            "manifest_sha256",
            "market_context_path",
            "market_context_sha256",
            "foreign_flow_path",
            "foreign_flow_sha256",
            "source_raw_path",
            "source_raw_sha256",
            "bridge_calendar_path",
            "bridge_calendar_sha256",
            "canonical_session_repair",
        )
    return all(meta.get(field) == fresh.get(field) for field in fields)


def verify_price_trend_state_context_bridge_strict(
    runtime_root: str | Path,
    feature_session: str | pd.Timestamp,
    *,
    pins: RuntimeContextPins,
) -> bool:
    """Re-establish the full bridge/canonical provenance for one sidecar."""

    runtime = Path(runtime_root).expanduser().resolve()
    target = _date(feature_session)
    directory = (
        runtime
        / "forward_monitoring"
        / "prospective"
        / "price_trend_confirmation_state_v1"
        / target.date().isoformat()
    ).resolve()
    artifact_path = directory / ARTIFACT_FILENAME
    manifest_path = directory / MANIFEST_FILENAME
    if not artifact_path.is_file() or not manifest_path.is_file():
        return False

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "PRICE_TREND_CONFIRMATION_STATE_V1_FORWARD_READY":
            return False
        if manifest.get("schema") != SIDECAR_SCHEMA:
            return False
        if manifest.get("accepted_price_state_commit") != ACCEPTED_PRICE_STATE_COMMIT:
            return False
        if manifest.get("output_columns") != list(OUTPUT_COLUMNS):
            return False
        if manifest.get("outcome_blind") is not True or manifest.get("forward_outcomes_accessed") is not False:
            return False
        if any(
            manifest.get(key) is not False
            for key in (
                "outcomes_or_labels_accessed",
                "outcome_metrics_computed",
                "model_fit",
                "model_scoring",
                "trade_recommendation",
            )
        ):
            return False
        if int(manifest.get("provider_calls", -1)) != 0:
            return False
        if Path(str(manifest.get("artifact_path") or "")).expanduser().resolve() != artifact_path:
            return False
        if str(manifest.get("artifact_sha256") or "").lower() != sha256_file(artifact_path):
            return False

        source = _date(manifest.get("source_session"))
        if _date(manifest.get("feature_session")) != target:
            return False
        artifact = _validate_state_artifact(pd.read_parquet(artifact_path), source=source, target=target)
        if len(artifact) != int(manifest.get("row_count", -1)):
            return False
        if artifact["ticker"].nunique() != int(manifest.get("ticker_count", -1)):
            return False
        if manifest.get("state_distributions") != _state_distributions(artifact):
            return False

        provenance = manifest.get("input_provenance")
        if not isinstance(provenance, dict):
            return False
        if provenance.get("accepted_price_state_commit") != ACCEPTED_PRICE_STATE_COMMIT:
            return False
        if provenance.get("runtime_context_policy") != RUNTIME_CONTEXT_POLICY:
            return False
        if provenance.get("bridge_fallback_through") != BRIDGE_FALLBACK_THROUGH.date().isoformat():
            return False
        if provenance.get("canonical_session_repair") is not False:
            return False
        if int(provenance.get("provider_calls", -1)) != 0 or provenance.get("outcome_blind") is not True:
            return False

        historical_panel = pins.historical_panel_path.expanduser().resolve()
        historical_sha = str(pins.historical_panel_sha256).lower()
        if str(Path(str(provenance.get("historical_panel_path") or "")).expanduser().resolve()) != str(historical_panel):
            return False
        if provenance.get("historical_panel_sha256") != historical_sha:
            return False
        if not historical_panel.is_file() or sha256_file(historical_panel) != historical_sha:
            return False

        historical_calendar, historical_calendar_sha, historical_sessions = _verified_calendar(
            pins.historical_calendar_path,
            pins.historical_calendar_sha256,
            role="historical",
        )
        bridge_calendar, bridge_calendar_sha, bridge_sessions = _verified_calendar(
            pins.bridge_calendar_path,
            pins.bridge_calendar_sha256,
            role="bridge extension",
        )
        if Path(str(provenance.get("historical_calendar_path") or "")).expanduser().resolve() != historical_calendar:
            return False
        if provenance.get("historical_calendar_sha256") != historical_calendar_sha:
            return False
        if Path(str(provenance.get("bridge_calendar_path") or "")).expanduser().resolve() != bridge_calendar:
            return False
        if provenance.get("bridge_calendar_sha256") != bridge_calendar_sha:
            return False

        historical_market = _normalise_market(pd.read_parquet(historical_panel))
        cutoff = historical_market["session_date"].max()
        sessions, recomputed_target = _combined_session_index(
            historical_sessions,
            bridge_sessions,
            historical_cutoff=cutoff,
            source_session=source,
            expected_sha256=pins.expected_combined_session_set_sha256,
        )
        if recomputed_target != target:
            return False
        if provenance.get("combined_session_set_sha256") != _session_set_sha256(sessions):
            return False
        if int(provenance.get("combined_session_count", -1)) != len(sessions):
            return False
        if provenance.get("combined_session_first") != sessions[0].date().isoformat():
            return False
        if provenance.get("combined_session_last") != sessions[-1].date().isoformat():
            return False
        if provenance.get("historical_cutoff") != cutoff.date().isoformat():
            return False

        expected_extension = sessions[(sessions > cutoff) & (sessions <= source)]
        sources = provenance.get("extension_session_sources")
        if not isinstance(sources, list) or len(sources) != len(expected_extension):
            return False
        for day, meta in zip(expected_extension, sources, strict=True):
            if not isinstance(meta, Mapping):
                return False
            if str(meta.get("session_date")) != pd.Timestamp(day).date().isoformat():
                return False
            if not _verify_source_meta(
                runtime,
                meta,
                bridge_calendar_path=bridge_calendar,
                bridge_calendar_sha256=bridge_calendar_sha,
            ):
                return False
            # Re-run source resolution to enforce ambiguity and post-monitor
            # canonical-only policy at verification time too.
            _, resolved_meta = _resolve_extension_market(
                runtime,
                pd.Timestamp(day),
                bridge_calendar_path=bridge_calendar,
                bridge_calendar_sha256=bridge_calendar_sha,
            )
            if str(resolved_meta.get("kind")) != str(meta.get("kind")):
                return False

        expected_fingerprint = _context_fingerprint(
            {key: value for key, value in provenance.items() if key != "input_fingerprint"}
        )
        if provenance.get("input_fingerprint") != expected_fingerprint:
            return False
        return True
    except Exception:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Produce bridge-aware Price State V1 from stored context only")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--source-session", required=True)
    parser.add_argument("--historical-panel", type=Path, required=True)
    parser.add_argument("--historical-panel-sha256", required=True)
    parser.add_argument("--historical-calendar", type=Path, required=True)
    parser.add_argument("--historical-calendar-sha256", required=True)
    parser.add_argument("--bridge-calendar", type=Path, required=True)
    parser.add_argument("--bridge-calendar-sha256", required=True)
    parser.add_argument("--combined-session-set-sha256")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    pins = RuntimeContextPins(
        historical_panel_path=args.historical_panel,
        historical_panel_sha256=args.historical_panel_sha256,
        historical_calendar_path=args.historical_calendar,
        historical_calendar_sha256=args.historical_calendar_sha256,
        bridge_calendar_path=args.bridge_calendar,
        bridge_calendar_sha256=args.bridge_calendar_sha256,
        expected_combined_session_set_sha256=args.combined_session_set_sha256,
    )
    result = produce_price_trend_state_with_context_bridge(
        runtime_root=args.runtime_root,
        source_session=args.source_session,
        pins=pins,
    )
    target = result["feature_session"]
    result["strict_verified"] = verify_price_trend_state_context_bridge_strict(
        args.runtime_root,
        target,
        pins=pins,
    )
    if result["strict_verified"] is not True:
        raise RuntimeError("bridge-aware Price State sidecar failed strict verification")
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
