"""Outcome-blind production-shape adapters for V4-X1 pre-access readiness.

The readiness core intentionally accepts prepared metadata only.  This module
bridges that core to the existing runtime shapes without loading score-table
values, targets, labels, outcomes, or changing runtime state.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from idx_trade.prospective_preaccess_readiness_v1 import (
    CANONICAL_TARGET_ID,
    MODEL_FINGERPRINT,
    MODEL_GENERATION,
    MODEL_NAME,
    PROTECTED_STATUS,
    RANKING_SEMANTICS,
    PreAccessReadinessError,
    build_readiness_report,
    inspect_access_state,
    validate_partial_session_inventory,
)


ADAPTER_SCHEMA_VERSION = "v4_x1_prospective_preaccess_adapters_v1"
PRODUCTION_SCORE_MANIFEST_SCHEMA = "v4_x1_prospective_score_manifest_v2"
MODEL_RUN_DIRECTORY = "v4_x1_clean_geometry3_prospective_v1"
GATE_SCORE_COLUMNS = frozenset({"ticker", "alpha_consensus"})
GATE_SCORE_DATE_COLUMNS = frozenset({"date", "session_date"})
_RANKING_PROOF_FORMULA = "0.5*H5_WITHIN_DATE_PERCENTILE_RANK+0.5*H10_WITHIN_DATE_PERCENTILE_RANK"

# Independent operator trust anchor.  This is intentionally duplicated here
# rather than imported from a downstream gate module: adapter discovery must
# reject a rewritten pin manifest before trusting any declarations inside it.
CODE_PIN_MANIFEST_SHA256 = "0012dc4822f676388c427e018c63873b9450ee6cc6067cd67638a439a7f0f65b"
_DISCOVERY_PROTECTED_TOKENS = frozenset(
    {"outcome", "outcomes", "label", "labels", "realized", "vault", "protected"}
)
_FORBIDDEN_METADATA_TOKENS = frozenset(
    {
        "canonical_target",
        "realized_return",
        "forward_return",
        "outcome",
        "label",
        "target",
        "nav",
        "pnl",
        "dividend",
        "payoff",
        "profit",
        "loss",
    }
)
_SCORE_GUARDS = (
    "historical_prediction_generated",
    "model_refit",
    "model_retuned",
    "protected_outcome_accessed",
    "provider_calls",
    "realized_forward_outcome_loaded",
    "science_changed",
)
_FORBIDDEN_COLUMNS = (
    "canonical_target",
    "realized_return",
    "forward_return",
    "outcome",
    "label",
    "target",
    "nav",
    "pnl",
    "dividend",
    "payoff",
)


class ProductionAdapterError(PreAccessReadinessError):
    """Raised when a real production artifact cannot be mapped safely."""


def _canonical_hash(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git_blob_sha1_file(path: str | Path) -> str:
    payload = Path(path).read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def _session_hash(session_dates: Iterable[str]) -> str:
    canonical = "\n".join(str(value) for value in session_dates)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _forbidden_metadata_paths(
    value: object,
    *,
    path: str = "manifest",
    ignored_keys: frozenset[str] = frozenset(),
) -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).strip().lower()
            child_path = f"{path}.{key}"
            if key_text in ignored_keys:
                continue
            if any(token in key_text for token in _FORBIDDEN_METADATA_TOKENS):
                found.append(child_path)
            found.extend(
                _forbidden_metadata_paths(
                    child, path=child_path, ignored_keys=ignored_keys
                )
            )
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found.extend(
                _forbidden_metadata_paths(
                    child, path=f"{path}[{index}]", ignored_keys=ignored_keys
                )
            )
    return found


def sha256_file(path: str | Path) -> str:
    """Hash bytes without deserializing the artifact payload."""

    file_path = Path(path)
    if not file_path.is_file():
        raise ProductionAdapterError(f"FILE_MISSING:{file_path}")
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_reference(value: object, *, base_dir: Path | None = None, label: str) -> Path:
    text = str(value or "").strip()
    if not text:
        raise ProductionAdapterError(f"{label}_REFERENCE_EMPTY")
    candidate = Path(text)
    if not candidate.is_absolute():
        if base_dir is None:
            raise ProductionAdapterError(f"{label}_REFERENCE_NOT_ABSOLUTE")
        candidate = base_dir / candidate
    resolved = candidate.resolve()
    # The core rejects protected semantic path components before any read.
    from idx_trade.prospective_preaccess_readiness_v1 import assert_safe_reference

    assert_safe_reference(str(resolved), label=label)
    return resolved


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _read_json(path: Path, *, label: str) -> tuple[dict[str, Any], str]:
    payload_bytes = path.read_bytes()
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProductionAdapterError(f"{label}_JSON_INVALID") from exc
    if not isinstance(payload, dict):
        raise ProductionAdapterError(f"{label}_JSON_OBJECT_REQUIRED")
    return payload, hashlib.sha256(payload_bytes).hexdigest()


def _component_missing(name: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "NOT_AVAILABLE",
        "reason": reason,
        "source_discovery": "READ_ONLY_LOCAL_ARTIFACT_AUDIT",
    }


def _component_invalid(name: str, reason: str, **details: Any) -> dict[str, Any]:
    return {
        "name": name,
        "status": "PROVENANCE_INVALID",
        "reason": reason,
        "source_discovery": "READ_ONLY_LOCAL_ARTIFACT_AUDIT",
        **details,
    }


def _is_protected_component(name: str) -> bool:
    lowered = str(name).strip().lower()
    return any(token in lowered for token in _DISCOVERY_PROTECTED_TOKENS)


def _iter_safe_files(root: Path) -> Iterable[Path]:
    """Enumerate metadata candidates without entering protected subtrees."""

    if not root.is_dir():
        return
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            entries = list(os.scandir(current))
        except OSError as exc:
            raise ProductionAdapterError(f"DISCOVERY_DIRECTORY_UNREADABLE:{current}") from exc
        for entry in sorted(entries, key=lambda item: item.name.lower()):
            if _is_protected_component(entry.name):
                continue
            candidate = Path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                pending.append(candidate)
            elif entry.is_file(follow_symlinks=False):
                yield candidate


def load_official_schedule(
    calendar_path: str | Path,
    *,
    summary_path: str | Path | None = None,
) -> tuple[list[str], dict[str, Any]]:
    """Load the existing official date-only schedule and its summary metadata."""

    calendar = _resolve_reference(calendar_path, label="CALENDAR")
    if summary_path is None:
        summary = calendar.with_name("exchange_session_summary.json")
    else:
        summary = _resolve_reference(summary_path, label="CALENDAR_SUMMARY")
    if not summary.is_file():
        raise ProductionAdapterError("CALENDAR_SUMMARY_MISSING")

    summary_payload, summary_sha = _read_json(summary, label="CALENDAR_SUMMARY")
    if summary_payload.get("complete") is not True:
        raise ProductionAdapterError("CALENDAR_SUMMARY_NOT_COMPLETE")
    if not str(summary_payload.get("source") or "").startswith("IDX_"):
        raise ProductionAdapterError("CALENDAR_SOURCE_NOT_OFFICIAL_IDX")

    frame = pd.read_csv(calendar)
    date_column = "date" if "date" in frame.columns else "session_date"
    if date_column not in frame.columns or len(frame.columns) != 1:
        raise ProductionAdapterError("CALENDAR_SCHEMA_UNEXPECTED")
    parsed = pd.to_datetime(frame[date_column], errors="coerce")
    if parsed.isna().any() or parsed.duplicated().any():
        raise ProductionAdapterError("CALENDAR_DATES_INVALID_OR_DUPLICATED")
    dates = [value.date().isoformat() for value in parsed.tolist()]
    if dates != sorted(dates) or not dates:
        raise ProductionAdapterError("CALENDAR_ORDER_INVALID")
    declared_count = summary_payload.get("exchange_sessions", summary_payload.get("session_count"))
    if not isinstance(declared_count, int) or declared_count != len(dates):
        raise ProductionAdapterError("CALENDAR_DECLARED_COUNT_MISMATCH")
    declared_first = summary_payload.get("first_session")
    declared_last = summary_payload.get("last_session")
    if declared_first is not None and str(declared_first) != dates[0]:
        raise ProductionAdapterError("CALENDAR_DECLARED_FIRST_SESSION_MISMATCH")
    if declared_last is not None and str(declared_last) != dates[-1]:
        raise ProductionAdapterError("CALENDAR_DECLARED_LAST_SESSION_MISMATCH")
    declared_sessions_sha = str(summary_payload.get("sessions_sha256") or "").lower()
    if declared_sessions_sha != _session_hash(dates):
        raise ProductionAdapterError("CALENDAR_SESSIONS_SHA256_MISMATCH")
    return dates, {
        "status": "READY",
        "source": str(summary_payload.get("source")),
        "source_identity": summary_payload.get("source_identity"),
        "calendar_path": str(calendar),
        "calendar_sha256": sha256_file(calendar),
        "summary_path": str(summary),
        "summary_sha256": summary_sha,
        "summary_sessions_sha256": declared_sessions_sha,
        "session_count": len(dates),
        "first_session": dates[0],
        "last_session": dates[-1],
        "complete": True,
    }


def _ranking_evidence(manifest: Mapping[str, Any], columns: list[object]) -> dict[str, Any]:
    declared = manifest.get("ranking")
    if declared == RANKING_SEMANTICS:
        return {"status": "READY", "kind": "DIRECT_MANIFEST_RANKING"}
    science = manifest.get("science")
    if (
        isinstance(science, Mapping)
        and science.get("consensus_formula") == _RANKING_PROOF_FORMULA
        and {"alpha_consensus", "rank_consensus"}.issubset(
            {str(column) for column in columns}
        )
    ):
        return {
            "status": "READY",
            "kind": "DETERMINISTIC_FROZEN_PRODUCTION_CONTRACT_PROOF",
            "formula": _RANKING_PROOF_FORMULA,
        }
    return {
        "status": "NOT_AVAILABLE",
        "kind": "RANKING_SEMANTICS_UNPROVEN",
    }


def _score_gate_admission(manifest: Mapping[str, Any], columns: list[object]) -> dict[str, Any]:
    column_names = [str(column) for column in columns]
    date_columns = [column for column in column_names if column in GATE_SCORE_DATE_COLUMNS]
    exact_shape = len(date_columns) == 1 and set(column_names) == {
        date_columns[0],
        *GATE_SCORE_COLUMNS,
    }
    ranking = _ranking_evidence(manifest, columns)
    if not exact_shape:
        return {
            "status": "NOT_AVAILABLE",
            "reason": "PRODUCTION_SCORE_SCHEMA_NOT_GATE_COMPATIBLE",
            "observed_columns": column_names,
            "required_columns": sorted(GATE_SCORE_COLUMNS | GATE_SCORE_DATE_COLUMNS),
            "projection_required": True,
            "ranking_evidence": ranking,
        }
    if ranking["status"] != "READY":
        return {
            "status": "NOT_AVAILABLE",
            "reason": "PRODUCTION_SCORE_RANKING_SEMANTICS_NOT_PROVEN",
            "observed_columns": column_names,
            "projection_required": True,
            "ranking_evidence": ranking,
        }
    return {
        "status": "READY",
        "reason": "PRODUCTION_SCORE_SHAPE_GATE_COMPATIBLE_REQUIRES_FINAL_GATE_REVALIDATION",
        "observed_columns": column_names,
        "projection_required": False,
        "ranking_evidence": ranking,
        "final_gate_revalidation_required": True,
    }


def _validate_score_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if manifest.get("schema_version") != PRODUCTION_SCORE_MANIFEST_SCHEMA:
        raise ProductionAdapterError("SCORE_MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("model_id") != MODEL_NAME:
        raise ProductionAdapterError("SCORE_MANIFEST_MODEL_ID_MISMATCH")
    if manifest.get("generation") != MODEL_GENERATION:
        raise ProductionAdapterError("SCORE_MANIFEST_GENERATION_MISMATCH")
    if manifest.get("model_fingerprint") != MODEL_FINGERPRINT:
        raise ProductionAdapterError("SCORE_MANIFEST_FINGERPRINT_MISMATCH")
    if manifest.get("status") != "DONE":
        raise ProductionAdapterError("SCORE_MANIFEST_NOT_DONE")
    guards = manifest.get("guards")
    if not isinstance(guards, Mapping):
        raise ProductionAdapterError("SCORE_MANIFEST_GUARDS_MISSING")
    bad = [name for name in _SCORE_GUARDS if guards.get(name) is not False]
    if bad:
        raise ProductionAdapterError(f"SCORE_MANIFEST_GUARD_NOT_FALSE:{','.join(bad)}")
    output = manifest.get("output")
    if not isinstance(output, Mapping):
        raise ProductionAdapterError("SCORE_MANIFEST_OUTPUT_MISSING")
    columns = output.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ProductionAdapterError("SCORE_MANIFEST_COLUMNS_MISSING")
    forbidden = [
        str(column)
        for column in columns
        if any(token in str(column).strip().lower() for token in _FORBIDDEN_COLUMNS)
    ]
    if forbidden:
        raise ProductionAdapterError(f"SCORE_MANIFEST_FORBIDDEN_COLUMNS:{','.join(forbidden)}")
    # Guard flags are safety attestations, not outcome-bearing score metadata;
    # their names intentionally contain protected/outcome tokens.
    forbidden_metadata = sorted(
        _forbidden_metadata_paths(manifest, ignored_keys=frozenset({"guards"}))
    )
    if forbidden_metadata:
        raise ProductionAdapterError(
            f"SCORE_MANIFEST_FORBIDDEN_METADATA:{','.join(forbidden_metadata)}"
        )
    ranking = _ranking_evidence(manifest, columns)
    return {
        "production_evidence_status": "READY",
        "ranking_evidence": ranking,
        "score_gate_admission": _score_gate_admission(manifest, columns),
        "observed_columns": [str(column) for column in columns],
    }


def discover_score_inventory(
    model_runs_root: str | Path,
    *,
    official_sessions: Iterable[str],
    data_root: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Discover exact V4-X1 score manifests and rehash bytes, never reading rows."""

    runs_root = _resolve_reference(model_runs_root, label="MODEL_RUNS_ROOT")
    root = _resolve_reference(data_root, label="DATA_ROOT")
    schedule = list(official_sessions)
    session_index = {value: index + 1 for index, value in enumerate(schedule)}
    # The exact model-run directory is the discovery boundary. Do not open
    # unrelated model manifests merely to inspect their identity.
    candidates = sorted(runs_root.glob(f"*/{MODEL_RUN_DIRECTORY}/manifest.json"))
    rows: list[dict[str, Any]] = []
    inspected = 0
    score_admissions: list[dict[str, Any]] = []
    for manifest_path in candidates:
        manifest, manifest_sha = _read_json(manifest_path, label="SCORE_MANIFEST")
        inspected += 1
        disposition = _validate_score_manifest(manifest)
        score_admissions.append(
            {
                "session_date": str(manifest.get("session_date") or ""),
                **disposition,
            }
        )
        session_date = str(manifest.get("session_date") or "")
        if session_date not in session_index:
            raise ProductionAdapterError("SCORE_MANIFEST_SESSION_NOT_IN_OFFICIAL_CALENDAR")
        output = manifest["output"]
        artifact_path = _resolve_reference(
            output.get("artifact_path"), base_dir=manifest_path.parent, label="SCORE_ARTIFACT"
        )
        if not _under(artifact_path, root):
            raise ProductionAdapterError("SCORE_ARTIFACT_OUTSIDE_DATA_ROOT")
        declared_sha = str(output.get("artifact_sha256") or "").lower()
        actual_sha = sha256_file(artifact_path)
        if actual_sha != declared_sha:
            raise ProductionAdapterError("SCORE_ARTIFACT_SHA256_MISMATCH")
        try:
            row_count = int(manifest.get("rows"))
        except (TypeError, ValueError) as exc:
            raise ProductionAdapterError("SCORE_MANIFEST_ROW_COUNT_INVALID") from exc
        if row_count <= 0:
            raise ProductionAdapterError("SCORE_MANIFEST_ROW_COUNT_INVALID")
        rows.append(
            {
                "session_date": session_date,
                "session_index": session_index[session_date],
                "score_artifact_path": str(artifact_path),
                "score_artifact_sha256": actual_sha,
                "score_manifest_path": str(manifest_path.resolve()),
                "score_manifest_sha256": manifest_sha,
                "score_rows_declared": row_count,
                "production_evidence_status": disposition["production_evidence_status"],
                "score_gate_admission_status": disposition["score_gate_admission"]["status"],
            }
        )

    rows.sort(key=lambda row: row["session_date"])
    if len({row["session_date"] for row in rows}) != len(rows):
        raise ProductionAdapterError("SCORE_INVENTORY_DUPLICATE_SESSION_DATE")
    for position, row in enumerate(rows, start=1):
        row["forward_position"] = position
    columns = [
        "forward_position",
        "session_index",
        "session_date",
        "score_artifact_path",
        "score_artifact_sha256",
        "score_manifest_path",
        "score_manifest_sha256",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    return frame, {
        "status": "READY" if rows else "ACCUMULATING",
        "source_kind": "V4_X1_SCORE_MANIFESTS",
        "model_runs_root": str(runs_root),
        "data_root": str(root),
        "candidate_manifest_count": len(candidates),
        "exact_model_manifest_count": inspected,
        "verified_session_count": len(rows),
        "artifact_values_loaded": False,
        "artifact_bytes_rehashed": True,
        "production_evidence_status": "READY" if rows else "ACCUMULATING",
        "score_gate_admission": {
            "status": (
                "PROVENANCE_INVALID"
                if any(item["score_gate_admission"]["status"] == "PROVENANCE_INVALID" for item in score_admissions)
                else (
                    "READY"
                    if score_admissions and all(
                        item["score_gate_admission"]["status"] == "READY"
                        for item in score_admissions
                    )
                    else "NOT_AVAILABLE"
                )
            ),
            "reason": (
                "ALL_PRODUCTION_SCORE_MANIFESTS_GATE_COMPATIBLE_REQUIRES_FINAL_GATE_REVALIDATION"
                if score_admissions and all(
                    item["score_gate_admission"]["status"] == "READY"
                    for item in score_admissions
                )
                else "PRODUCTION_SCORE_MANIFESTS_REQUIRE_DETERMINISTIC_GATE_SHAPE_PROJECTION"
            ),
            "projection_contract": "EXACT_DATE_TICKER_ALPHA_CONSENSUS_NO_RERANK_NO_TRANSFORM",
            "sessions": score_admissions,
        },
    }


def gate_shape_inventory_sha256(inventory: pd.DataFrame) -> str:
    """Compute the exact final-gate inventory identity, excluding local paths."""

    partial = validate_partial_session_inventory(inventory)
    records = [
        {
            "forward_position": int(row["forward_position"]),
            "session_index": int(row["session_index"]),
            "session_date": str(row["session_date"]),
            "score_artifact_sha256": str(row["score_artifact_sha256"]).lower(),
            "score_manifest_sha256": str(row["score_manifest_sha256"]).lower(),
        }
        for row in partial["rows"]
    ]
    return _canonical_hash(records)


def project_score_frame_to_gate_shape(
    frame: pd.DataFrame,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Project score-side columns only; never rerank or transform scores.

    This pure helper is intentionally not wired to the real runtime in this
    lane. A future producer must verify the immutable production manifest and
    artifact hash before calling it, then publish a separately hashed
    gate-compatible artifact/manifest bound back to those source hashes.
    """

    if not isinstance(frame, pd.DataFrame):
        raise ProductionAdapterError("SCORE_PROJECTION_FRAME_REQUIRED")
    column_names = [str(column) for column in frame.columns]
    if len(set(column_names)) != len(column_names):
        raise ProductionAdapterError("SCORE_PROJECTION_DUPLICATE_COLUMNS")
    date_columns = [column for column in frame.columns if str(column) in GATE_SCORE_DATE_COLUMNS]
    if len(date_columns) != 1:
        raise ProductionAdapterError("SCORE_PROJECTION_DATE_COLUMN_AMBIGUOUS")
    date_column = date_columns[0]
    missing = sorted(GATE_SCORE_COLUMNS - set(column_names))
    if missing:
        raise ProductionAdapterError(f"SCORE_PROJECTION_REQUIRED_COLUMN_MISSING:{','.join(missing)}")
    forbidden = [
        column
        for column in column_names
        if any(token in column.strip().lower() for token in _FORBIDDEN_METADATA_TOKENS)
    ]
    if forbidden:
        raise ProductionAdapterError(
            f"SCORE_PROJECTION_FORBIDDEN_COLUMNS:{','.join(forbidden)}"
        )
    if metadata is not None:
        forbidden_metadata = sorted(
            _forbidden_metadata_paths(metadata, path="production_score_metadata")
        )
        if forbidden_metadata:
            raise ProductionAdapterError(
                "SCORE_PROJECTION_FORBIDDEN_METADATA:" + ",".join(forbidden_metadata)
            )
    if frame.empty:
        raise ProductionAdapterError("SCORE_PROJECTION_EMPTY")
    parsed_dates = pd.to_datetime(frame[date_column], errors="coerce")
    if parsed_dates.isna().any() or parsed_dates.dt.normalize().nunique() != 1:
        raise ProductionAdapterError("SCORE_PROJECTION_SESSION_IDENTITY_INVALID")
    projected = frame[[date_column, "ticker", "alpha_consensus"]].copy()
    if projected["ticker"].astype(str).str.strip().eq("").any():
        raise ProductionAdapterError("SCORE_PROJECTION_TICKER_INVALID")
    if projected["ticker"].astype(str).str.strip().duplicated().any():
        raise ProductionAdapterError("SCORE_PROJECTION_DUPLICATE_TICKER")
    scores = pd.to_numeric(projected["alpha_consensus"], errors="coerce")
    if scores.isna().any() or not scores.map(lambda value: math.isfinite(float(value))).all():
        raise ProductionAdapterError("SCORE_PROJECTION_SCORE_INVALID")
    return projected


def describe_gate_score_projection(
    production_manifest: Mapping[str, Any],
    *,
    projected_artifact_sha256: str,
    source_artifact_sha256: str,
    source_manifest_sha256: str,
) -> dict[str, Any]:
    """Return the future projection binding contract without writing files."""

    columns = production_manifest.get("output", {}).get("columns")
    if not isinstance(columns, list):
        raise ProductionAdapterError("SCORE_PROJECTION_SOURCE_COLUMNS_MISSING")
    disposition = _validate_score_manifest(production_manifest)
    return {
        "schema_version": "v4_x1_gate_score_projection_descriptor_v1",
        "status": "DESIGNED_NOT_PUBLISHED",
        "projection": {
            "columns": ["date", "ticker", "alpha_consensus"],
            "operation": "EXACT_COLUMN_SELECTION_NO_RERANK_NO_TRANSFORM",
        },
        "source": {
            "artifact_sha256": str(source_artifact_sha256).lower(),
            "manifest_sha256": str(source_manifest_sha256).lower(),
            "production_evidence_status": disposition["production_evidence_status"],
        },
        "projected_artifact_sha256": str(projected_artifact_sha256).lower(),
        "outcome_blind": True,
        "final_gate_revalidation_required": True,
    }


def adapt_runtime_counter(
    pipeline_status_path: str | Path,
    *,
    inventory_sha256: str | None = None,
    discovered_inventory: pd.DataFrame | None = None,
    production_source_gate_shape_sha256: str | None = None,
    canonical_admitted_gate_inventory_sha256: str | None = None,
    # Backward-compatible input alias; it is never emitted as a canonical
    # identity and is normalized to the explicitly named source identity.
    gate_shape_inventory_sha256: str | None = None,
) -> dict[str, Any]:
    """Map runtime status and cross-bind it to discovered score sessions."""

    if (
        production_source_gate_shape_sha256 is not None
        and gate_shape_inventory_sha256 is not None
        and production_source_gate_shape_sha256 != gate_shape_inventory_sha256
    ):
        return _component_invalid("counter", "COUNTER_SOURCE_GATE_IDENTITY_CONFLICT")
    if production_source_gate_shape_sha256 is None:
        production_source_gate_shape_sha256 = gate_shape_inventory_sha256
    canonical_identity = canonical_admitted_gate_inventory_sha256 or "NOT_AVAILABLE"
    path = _resolve_reference(pipeline_status_path, label="COUNTER_STATUS")
    payload, source_sha = _read_json(path, label="COUNTER_STATUS")
    counter = payload.get("x1_counter")
    if not isinstance(counter, Mapping):
        return _component_missing("counter", "X1_COUNTER_NOT_PRESENT")
    try:
        completed = int(counter.get("completed"))
        target = int(counter.get("target"))
        remaining = int(counter.get("remaining"))
    except (TypeError, ValueError) as exc:
        raise ProductionAdapterError("COUNTER_STATUS_NUMERIC_FIELDS_INVALID") from exc
    sessions = counter.get("sessions")
    if not isinstance(sessions, list) or not all(isinstance(value, str) for value in sessions):
        raise ProductionAdapterError("COUNTER_STATUS_SESSION_LIST_INVALID")
    if completed != len(sessions) or target != 100 or remaining != target - completed:
        return _component_invalid("counter", "COUNTER_STATUS_INTERNAL_COUNTS_INVALID")
    if len(set(sessions)) != len(sessions):
        return _component_invalid("counter", "COUNTER_STATUS_DUPLICATE_SESSIONS")
    parsed_sessions = pd.to_datetime(sessions, errors="coerce")
    if parsed_sessions.isna().any() or not parsed_sessions.is_monotonic_increasing:
        return _component_invalid("counter", "COUNTER_STATUS_CHRONOLOGY_INVALID")

    expected_sessions: list[str] | None = None
    if discovered_inventory is not None:
        validated = validate_partial_session_inventory(discovered_inventory)
        expected_sessions = [str(row["session_date"]) for row in validated["rows"]]
        if sessions != expected_sessions:
            return _component_invalid(
                "counter",
                "COUNTER_STATUS_SESSIONS_DO_NOT_MATCH_DISCOVERED_SCORE_SESSIONS",
                observed_session_dates=list(sessions),
                discovered_session_dates=expected_sessions,
            )
        if completed != len(expected_sessions):
            return _component_invalid(
                "counter",
                "COUNTER_STATUS_COMPLETED_DOES_NOT_MATCH_DISCOVERED_SCORE_COUNT",
                completed=completed,
                discovered_score_session_count=len(expected_sessions),
            )

    if completed < target:
        status = "ACCUMULATING"
        reason = "RUNTIME_STATUS_ONLY_NOT_CANONICAL_ATTESTATION"
    else:
        status = "PENDING_EXPECTED"
        reason = "RUNTIME_100_COMPLETED_BUT_CANONICAL_COUNTER_ATTESTATION_MISSING"
    return {
        "name": "counter",
        "status": status,
        "reason": reason,
        "source_path": str(path),
        "source_sha256": source_sha,
        "source_kind": "V4_X1_PIPELINE_LATEST_STATUS",
        "completed": completed,
        "target": target,
        "remaining": remaining,
        "session_dates": list(sessions),
        "artifact_verification": counter.get("artifact_verification"),
        "inventory_sha256_binding": False,
        "rolling_partial_inventory_sha256": inventory_sha256,
        "production_source_gate_shape_sha256": production_source_gate_shape_sha256,
        "canonical_admitted_gate_inventory_sha256": canonical_identity,
        "canonical_inventory_sha256_binding": canonical_identity != "NOT_AVAILABLE",
        "canonical_attestation_present": False,
        "discovered_score_session_count": len(expected_sessions) if expected_sessions is not None else None,
        "protected_outcome_accessed": False,
    }


def discover_sealed_target_producer(
    *,
    repo_root: str | Path,
    data_root: str | Path,
) -> dict[str, Any]:
    """Prove absence/presence by filenames and frozen references only.

    This function deliberately does not open a target artifact or construct a
    target.  A source-code reference to a former materializer is not treated as
    a sealed producer unless the producer path and a persisted attestation are
    both present.
    """

    repo = _resolve_reference(repo_root, label="REPO_ROOT")
    root = _resolve_reference(data_root, label="DATA_ROOT")
    semantic_source = repo / "src" / "idx_trade" / "v4_x1_canonical_target_v1.py"
    target_names = sorted(
        path.name
        for path in _iter_safe_files(root)
        if any(token in path.name.lower() for token in ("target_attestation", "target_manifest"))
    )
    return {
        "name": "target_attestation",
        "status": "NOT_AVAILABLE",
        "reason": "SEALED_PROSPECTIVE_TARGET_MATERIALIZER_OR_ATTESTATION_NOT_FOUND",
        "producer_reference": "src/idx_trade/v4_x1_canonical_target_v1.py",
        "producer_path_exists": semantic_source.is_file(),
        "historical_materializer_reference": "src/idx_trade/ranking_v4_3_target_execution.py",
        "historical_materializer_promotion_allowed": False,
        "future_architecture": (
            "RETAINED_PINNED_HISTORICAL_TARGET_SEMANTICS->ISOLATED_SEALED_PRODUCER->"
            "PROTECTED_TARGET_STORE->PUBLIC_METADATA_ONLY_ATTESTATION"
        ),
        "persisted_target_attestation_filenames": target_names,
        "target_values": PROTECTED_STATUS,
    }


def discover_named_component(
    *,
    name: str,
    data_root: str | Path,
    filename_tokens: tuple[str, ...],
) -> dict[str, Any]:
    """Discover candidate filenames without opening any optional component."""

    root = _resolve_reference(data_root, label="DATA_ROOT")
    names = sorted(
        path.name
        for path in _iter_safe_files(root)
        if all(token.lower() in path.name.lower() for token in filename_tokens)
    )
    if not names:
        return _component_missing(name, f"NO_{name.upper()}_ARTIFACT_DISCOVERED")
    return {
        "name": name,
        "status": "PENDING_EXPECTED",
        "reason": "CANDIDATE_METADATA_REQUIRES_EXPLICIT_ATTESTATION_ADAPTER",
        "candidate_filenames": names,
    }


def _adapt_code_pins_verified(path: Path, payload: Mapping[str, Any], source_sha: str) -> dict[str, Any]:
    if payload.get("schema_version") != "v4_x1_prospective_evaluation_code_pin_v1":
        raise ProductionAdapterError("CODE_PIN_SCHEMA_MISMATCH")
    if payload.get("status") != "AUDITED_SYNTHETIC_ONLY_REAL_ACCESS_BLOCKED":
        raise ProductionAdapterError("CODE_PIN_STATUS_NOT_FROZEN_BLOCKED")
    model = payload.get("model")
    if not isinstance(model, Mapping) or any(
        model.get(key) != expected
        for key, expected in {
            "model_id": MODEL_NAME,
            "generation": MODEL_GENERATION,
            "fingerprint": MODEL_FINGERPRINT,
        }.items()
    ):
        raise ProductionAdapterError("CODE_PIN_MODEL_IDENTITY_MISMATCH")

    access_policy = payload.get("access_policy")
    if not isinstance(access_policy, Mapping):
        raise ProductionAdapterError("CODE_PIN_ACCESS_POLICY_MISSING")
    policy_checks = {
        "real_loader_allowed": False,
        "real_outcome_marker_allowed": False,
        "protected_outcomes_accessed": False,
        "requires_explicit_human_authorization": True,
    }
    bad_policy = [key for key, expected in policy_checks.items() if access_policy.get(key) is not expected]
    if bad_policy:
        raise ProductionAdapterError(f"CODE_PIN_ACCESS_POLICY_DIRTY:{','.join(bad_policy)}")

    sections = ("protocol", "evaluator", "gate", "contract", "target_construction")
    section_summary: dict[str, Any] = {}
    for section_name in sections:
        section = payload.get(section_name)
        if not isinstance(section, Mapping):
            raise ProductionAdapterError(f"CODE_PIN_SECTION_MISSING:{section_name}")
        declared_path = section.get("path")
        resolved = _resolve_reference(declared_path, base_dir=path.parent, label="CODE_PIN")
        if not resolved.is_file():
            raise ProductionAdapterError(f"CODE_PIN_FILE_MISSING:{section_name}")
        entry: dict[str, Any] = {
            "path": str(resolved),
            "exists": True,
        }
        if section_name in {"protocol", "evaluator", "gate", "target_construction"}:
            source_commit = str(section.get("source_commit") or "").lower()
            if len(source_commit) != 40 or any(char not in "0123456789abcdef" for char in source_commit):
                raise ProductionAdapterError(f"CODE_PIN_SOURCE_COMMIT_INVALID:{section_name}")
            entry["source_commit"] = source_commit
        if section_name in {"protocol", "evaluator", "gate", "target_construction"}:
            declared_blob = str(section.get("git_blob_sha1") or "").lower()
            if len(declared_blob) != 40 or any(char not in "0123456789abcdef" for char in declared_blob):
                raise ProductionAdapterError(f"CODE_PIN_GIT_BLOB_INVALID:{section_name}")
            actual_blob = _git_blob_sha1_file(resolved)
            if actual_blob != declared_blob:
                raise ProductionAdapterError(f"CODE_PIN_GIT_BLOB_MISMATCH:{section_name}")
            entry.update({"git_blob_sha1": actual_blob, "git_blob_verified": True})
        if section_name in {"contract", "target_construction"}:
            declared_sha = str(section.get("sha256") or "").lower()
            actual_sha = sha256_file(resolved)
            if actual_sha != declared_sha:
                raise ProductionAdapterError(f"CODE_PIN_SHA256_MISMATCH:{section_name}")
            entry.update({"sha256": actual_sha, "sha256_verified": True})
        section_summary[section_name] = entry

    target_identity = payload.get("target_identity")
    target_spec_path = None
    if (
        not isinstance(target_identity, Mapping)
        or target_identity.get("status") != "RESOLVED"
        or target_identity.get("canonical_target_id") != CANONICAL_TARGET_ID
    ):
        raise ProductionAdapterError("CODE_PIN_TARGET_IDENTITY_UNRESOLVED")
    target_spec_path = _resolve_reference(
        target_identity.get("target_spec_path"), base_dir=path.parent, label="TARGET_SPEC"
    )
    target_spec_sha = str(target_identity.get("target_spec_sha256") or "").lower()
    if not target_spec_path.is_file() or sha256_file(target_spec_path) != target_spec_sha:
        raise ProductionAdapterError("CODE_PIN_TARGET_SPEC_SHA256_MISMATCH")
    section_summary["target_identity"] = {
        "canonical_target_id": target_identity.get("canonical_target_id"),
        "target_spec_path": str(target_spec_path),
        "target_spec_sha256": target_spec_sha,
        "target_spec_verified": True,
    }
    return {
        "name": "code_pins",
        "status": "READY",
        "reason": "FROZEN_CODE_PIN_MANIFEST_AND_BLOBS_VERIFIED_OUTCOME_BLIND",
        "source_path": str(path),
        "source_sha256": source_sha,
        "schema_version": payload.get("schema_version"),
        "pin_status": payload.get("status"),
        "section_summary": section_summary,
        "verification_scope": "METADATA_ONLY_FINAL_GATE_REVALIDATES_TOCTOU_AND_ACCESS",
        "explicit_human_authorization_required": True,
        "protected_outcome_accessed": False,
    }


def adapt_code_pins(repo_root: str | Path) -> dict[str, Any]:
    """Verify frozen code pins and access policy without opening outcomes."""

    repo = _resolve_reference(repo_root, label="REPO_ROOT")
    path = repo / "config" / "v4_x1_prospective_evaluation_code_pin_v1.json"
    if not path.is_file():
        return _component_missing("code_pins", "CODE_PIN_MANIFEST_MISSING")
    try:
        payload, source_sha = _read_json(path, label="CODE_PIN_MANIFEST")
        if source_sha != CODE_PIN_MANIFEST_SHA256:
            return _component_invalid(
                "code_pins",
                "CODE_PIN_MANIFEST_TRUST_ANCHOR_MISMATCH",
                source_path=str(path),
                expected_sha256=CODE_PIN_MANIFEST_SHA256,
                observed_sha256=source_sha,
                verification_scope="METADATA_ONLY_FINAL_GATE_REVALIDATES_TOCTOU_AND_ACCESS",
            )
        return _adapt_code_pins_verified(path, payload, source_sha)
    except (OSError, ProductionAdapterError, PreAccessReadinessError) as exc:
        return _component_invalid(
            "code_pins",
            str(exc),
            source_path=str(path),
            verification_scope="METADATA_ONLY_FINAL_GATE_REVALIDATES_TOCTOU_AND_ACCESS",
        )


def build_production_readiness(
    *,
    repo_root: str | Path,
    data_root: str | Path,
    as_of_session: object,
) -> dict[str, Any]:
    """Assemble a real-shape, outcome-blind readiness report."""

    repo = _resolve_reference(repo_root, label="REPO_ROOT")
    root = _resolve_reference(data_root, label="DATA_ROOT")
    monitoring = root / "forward_monitoring"
    calendar_path = monitoring / "calendar" / "exchange_sessions.csv"
    summary_path = monitoring / "calendar" / "exchange_session_summary.json"
    official_sessions, schedule = load_official_schedule(calendar_path, summary_path=summary_path)
    inventory, inventory_source = discover_score_inventory(
        monitoring / "model_runs", official_sessions=official_sessions, data_root=root
    )
    rolling_inventory_sha = ""
    gate_inventory_sha = ""
    if not inventory.empty:
        # The pure core remains authoritative for the rolling/path-aware hash;
        # the final gate identity deliberately excludes filesystem paths.
        partial = validate_partial_session_inventory(inventory)
        rolling_inventory_sha = partial["partial_inventory_sha256"]
        gate_inventory_sha = gate_shape_inventory_sha256(inventory)
    counter = adapt_runtime_counter(
        monitoring / "eod_automation" / "v4_x1_pipeline" / "latest.json",
        inventory_sha256=rolling_inventory_sha or None,
        discovered_inventory=inventory,
        production_source_gate_shape_sha256=gate_inventory_sha or None,
        canonical_admitted_gate_inventory_sha256=None,
    )
    target = discover_sealed_target_producer(repo_root=repo, data_root=root)
    paper = discover_named_component(
        name="paper_attestation", data_root=root, filename_tokens=("paper", "state")
    )
    benchmark = discover_named_component(
        name="benchmark_attestation", data_root=root, filename_tokens=("benchmark",)
    )
    prior_access = discover_named_component(
        name="prior_access_audit", data_root=root, filename_tokens=("access", "audit")
    )
    code_pins = adapt_code_pins(repo)
    access_state = inspect_access_state(persisted_status="PERSISTED_STATUS_NOT_DISCOVERED")
    access_state.update(
        {
            "reason": "NO_PERSISTED_PREACCESS_STATUS_ARTIFACT_DISCOVERED",
            "source_discovery": "READ_ONLY_LOCAL_ARTIFACT_AUDIT",
        }
    )
    contract_identity = {
        "model": {
            "model_id": MODEL_NAME,
            "generation": MODEL_GENERATION,
            "fingerprint": MODEL_FINGERPRINT,
            "ranking": RANKING_SEMANTICS,
        },
        "target_identity": {"status": "RESOLVED", "target_id": CANONICAL_TARGET_ID},
        "scientific_boundary": {
            "protected_outcomes_accessed": False,
            "real_loader_called": False,
            "real_marker_written": False,
        },
    }
    readiness = build_readiness_report(
        inventory=inventory,
        official_trading_sessions=official_sessions,
        as_of_session=as_of_session,
        access_state=access_state,
        contract_identity=contract_identity,
        counter=counter,
        target_attestation=target,
        paper_attestation=paper,
        benchmark_attestation=benchmark,
        prior_access_audit=prior_access,
        code_pins=code_pins,
    )
    readiness["inventory"]["rolling_partial_inventory_sha256"] = readiness["inventory"].get(
        "partial_inventory_sha256"
    )
    readiness["inventory"]["production_source_gate_shape_sha256"] = gate_inventory_sha or None
    readiness["inventory"]["canonical_admitted_gate_inventory_sha256"] = "NOT_AVAILABLE"
    score_gate_admission = inventory_source.get(
        "score_gate_admission",
        {"status": "NOT_AVAILABLE", "reason": "SCORE_GATE_ADMISSION_NOT_COMPUTED"},
    )
    readiness["score_gate_admission"] = score_gate_admission
    readiness["components"]["score_gate_admission"] = {
        "name": "score_gate_admission",
        **score_gate_admission,
    }
    if score_gate_admission.get("status") == "PROVENANCE_INVALID":
        readiness["overall_status"] = "PREACCESS_PROVENANCE_INVALID"
        readiness["existing_gate_preflight_eligible"] = False
    return {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "audit_mode": "OUTCOME_BLIND_LOCAL_PRODUCTION_SHAPE_AUDIT",
        "repo_root": str(repo),
        "data_root": str(root),
        "as_of_session": str(as_of_session),
        "sources": {
            "schedule": schedule,
            "inventory": inventory_source,
            "inventory_identities": {
                "rolling_partial_inventory_sha256": rolling_inventory_sha or None,
                "production_source_gate_shape_sha256": gate_inventory_sha or None,
                "canonical_admitted_gate_inventory_sha256": "NOT_AVAILABLE",
            },
            "counter": counter,
            "target_discovery": target,
            "paper_discovery": paper,
            "benchmark_discovery": benchmark,
            "prior_access_discovery": prior_access,
            "code_pins": code_pins,
        },
        "readiness": readiness,
        "guards": {
            "target_values_loaded": False,
            "protected_outcomes_accessed": False,
            "provider_calls": False,
            "counter_changed": False,
            "runtime_mutated": False,
        },
    }
