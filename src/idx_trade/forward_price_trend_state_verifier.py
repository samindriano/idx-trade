"""Strict fail-closed verifier for the prospective Price State V1 sidecar.

This verifier intentionally re-establishes semantic provenance rather than
checking stored hashes only.  It is the required acceptance/runtime verifier
for ``price_trend_confirmation_state_v1`` prospective artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .forward_price_trend_state import (
    ACCEPTED_PRICE_STATE_COMMIT,
    ARTIFACT_FILENAME,
    MANIFEST_FILENAME,
    OUTPUT_COLUMNS,
    SIDECAR_SCHEMA,
    STATE_COLUMNS,
    _calendar_union,
    _context_fingerprint,
    _date,
    _read_calendar,
    _read_verified_forward_market,
    _validate_state_artifact,
)
from .provenance import sha256_file


def _distributions(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    return {
        column: {
            str(key): int(value)
            for key, value in frame[column].value_counts(dropna=False).sort_index().items()
        }
        for column in STATE_COLUMNS
    }


def verify_prospective_price_trend_state_strict(
    runtime_root: str | Path,
    feature_session: str | pd.Timestamp,
) -> bool:
    """Verify artifact, manifest, calendars, and canonical parent semantics.

    The verification is intentionally stronger than a byte-pin check:

    - exact output schema and state-distribution summaries are reconciled;
    - the pinned historical/forward calendars are re-read and the exact
      source ``t`` -> target ``t+1`` relation is recomputed;
    - every stored canonical forward source is re-opened through the same
      DATA_READY/outcome-blind/path/calendar/hash gates used by production;
    - the deterministic provenance fingerprint is recomputed.
    """

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
        if manifest.get("outcome_blind") is not True:
            return False
        if manifest.get("forward_outcomes_accessed") is not False:
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
        artifact = _validate_state_artifact(
            pd.read_parquet(artifact_path), source=source, target=target
        )
        if len(artifact) != int(manifest.get("row_count", -1)):
            return False
        if artifact["ticker"].nunique() != int(manifest.get("ticker_count", -1)):
            return False
        if manifest.get("state_distributions") != _distributions(artifact):
            return False

        provenance = manifest.get("input_provenance")
        if not isinstance(provenance, dict):
            return False
        if provenance.get("accepted_price_state_commit") != ACCEPTED_PRICE_STATE_COMMIT:
            return False

        pins: dict[str, tuple[Path, str]] = {}
        for path_key, hash_key in (
            ("historical_panel_path", "historical_panel_sha256"),
            ("historical_calendar_path", "historical_calendar_sha256"),
            ("forward_calendar_path", "forward_calendar_sha256"),
        ):
            path = Path(str(provenance.get(path_key) or "")).expanduser().resolve()
            expected = str(provenance.get(hash_key) or "").lower()
            if not path.is_file() or len(expected) != 64 or sha256_file(path) != expected:
                return False
            pins[path_key] = (path, expected)

        historical_calendar = pins["historical_calendar_path"][0]
        forward_calendar = pins["forward_calendar_path"][0]
        historical_sessions = _read_calendar(historical_calendar, label="historical")
        forward_sessions = _read_calendar(forward_calendar, label="forward")
        sessions = _calendar_union(historical_sessions, forward_sessions)

        if source not in set(forward_sessions):
            return False
        forward_position = int(forward_sessions.get_loc(source))
        if forward_position >= len(forward_sessions) - 1:
            return False
        if forward_sessions[forward_position + 1] != target:
            return False
        union_position = int(sessions.get_loc(source))
        if union_position >= len(sessions) - 1 or sessions[union_position + 1] != target:
            return False
        if provenance.get("combined_session_first") != sessions[0].date().isoformat():
            return False
        if provenance.get("combined_session_last") != sessions[-1].date().isoformat():
            return False
        if int(provenance.get("combined_session_count", -1)) != len(sessions):
            return False

        forward_sources = provenance.get("forward_sources")
        if not isinstance(forward_sources, list) or not forward_sources:
            return False
        source_key = source.date().isoformat()
        seen: set[str] = set()
        source_seen = False
        forward_calendar_sha = pins["forward_calendar_path"][1]
        for item in forward_sources:
            if not isinstance(item, dict):
                return False
            key = str(item.get("session_date") or "")
            session = _date(key)
            if key in seen or session > source or session not in set(forward_sessions):
                return False
            seen.add(key)
            _, verified_meta = _read_verified_forward_market(
                runtime,
                key,
                forward_calendar_path=forward_calendar,
                forward_calendar_sha256=forward_calendar_sha,
            )
            for field in (
                "session_date",
                "parent_manifest_path",
                "parent_manifest_sha256",
                "snapshot_path",
                "snapshot_sha256",
                "row_count",
            ):
                if item.get(field) != verified_meta.get(field):
                    return False
            if key == source_key:
                source_seen = True
        if not source_seen:
            return False

        expected_fingerprint = _context_fingerprint(
            {key: value for key, value in provenance.items() if key != "input_fingerprint"}
        )
        if provenance.get("input_fingerprint") != expected_fingerprint:
            return False
        return True
    except Exception:
        return False
