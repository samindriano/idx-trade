"""Outcome-blind production-shape adapters for V4-X1 pre-access readiness.

The readiness core intentionally accepts prepared metadata only.  This module
bridges that core to the existing runtime shapes without loading score-table
values, targets, labels, outcomes, or changing runtime state.
"""

from __future__ import annotations

import hashlib
import json
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
)


ADAPTER_SCHEMA_VERSION = "v4_x1_prospective_preaccess_adapters_v1"
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
    dates = [value.date().isoformat() for value in parsed.sort_values().tolist()]
    if dates != sorted(dates) or not dates:
        raise ProductionAdapterError("CALENDAR_ORDER_INVALID")
    return dates, {
        "status": "READY",
        "source": str(summary_payload.get("source")),
        "source_identity": summary_payload.get("source_identity"),
        "calendar_path": str(calendar),
        "calendar_sha256": sha256_file(calendar),
        "summary_path": str(summary),
        "summary_sha256": summary_sha,
        "summary_sessions_sha256": summary_payload.get("sessions_sha256"),
        "session_count": len(dates),
        "first_session": dates[0],
        "last_session": dates[-1],
        "complete": True,
    }


def _validate_score_manifest(manifest: Mapping[str, Any]) -> None:
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
    candidates = sorted(runs_root.rglob("manifest.json"))
    rows: list[dict[str, Any]] = []
    inspected = 0
    for manifest_path in candidates:
        manifest, manifest_sha = _read_json(manifest_path, label="SCORE_MANIFEST")
        if manifest.get("model_id") != MODEL_NAME:
            continue
        inspected += 1
        _validate_score_manifest(manifest)
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
    }


def adapt_runtime_counter(
    pipeline_status_path: str | Path,
    *,
    inventory_sha256: str | None = None,
) -> dict[str, Any]:
    """Map the current pipeline status; never call it a canonical attestation."""

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
        raise ProductionAdapterError("COUNTER_STATUS_INTERNAL_COUNTS_INVALID")
    status = "ACCUMULATING" if completed < target else "PROVENANCE_INVALID"
    return {
        "name": "counter",
        "status": status,
        "reason": "RUNTIME_STATUS_ONLY_NOT_CANONICAL_ATTESTATION",
        "source_path": str(path),
        "source_sha256": source_sha,
        "source_kind": "V4_X1_PIPELINE_LATEST_STATUS",
        "completed": completed,
        "target": target,
        "remaining": remaining,
        "session_dates": list(sessions),
        "artifact_verification": counter.get("artifact_verification"),
        "inventory_sha256_binding": False,
        "observed_inventory_sha256": inventory_sha256,
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
    producer = repo / "src" / "idx_trade" / "ranking_v4_3_target_execution.py"
    target_names = sorted(
        path.name
        for path in root.rglob("*")
        if path.is_file()
        and any(token in path.name.lower() for token in ("target_attestation", "target_manifest"))
    )
    if not producer.is_file() or not target_names:
        return {
            "name": "target_attestation",
            "status": "NOT_AVAILABLE",
            "reason": "SEALED_PROSPECTIVE_TARGET_MATERIALIZER_OR_ATTESTATION_NOT_FOUND",
            "producer_reference": "src/idx_trade/ranking_v4_3_target_execution.py",
            "producer_path_exists": producer.is_file(),
            "persisted_target_attestation_filenames": target_names,
            "target_values": PROTECTED_STATUS,
        }
    return {
        "name": "target_attestation",
        "status": "PENDING_EXPECTED",
        "reason": "PRODUCER_AND_ATTESTATION_DISCOVERED_REQUIRES_SEPARATE_REVIEW",
        "producer_reference": "src/idx_trade/ranking_v4_3_target_execution.py",
        "producer_path_exists": True,
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
        for path in root.rglob("*")
        if path.is_file() and all(token.lower() in path.name.lower() for token in filename_tokens)
    )
    if not names:
        return _component_missing(name, f"NO_{name.upper()}_ARTIFACT_DISCOVERED")
    return {
        "name": name,
        "status": "PENDING_EXPECTED",
        "reason": "CANDIDATE_METADATA_REQUIRES_EXPLICIT_ATTESTATION_ADAPTER",
        "candidate_filenames": names,
    }


def adapt_code_pins(repo_root: str | Path) -> dict[str, Any]:
    """Read the frozen pin manifest as metadata; final gate revalidates blobs."""

    repo = _resolve_reference(repo_root, label="REPO_ROOT")
    path = repo / "config" / "v4_x1_prospective_evaluation_code_pin_v1.json"
    if not path.is_file():
        return _component_missing("code_pins", "CODE_PIN_MANIFEST_MISSING")
    payload, source_sha = _read_json(path, label="CODE_PIN_MANIFEST")
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
    sections = ("protocol", "evaluator", "gate", "contract", "target_construction")
    missing = []
    section_summary: dict[str, Any] = {}
    for section_name in sections:
        section = payload.get(section_name)
        if not isinstance(section, Mapping):
            missing.append(section_name)
            continue
        declared_path = section.get("path")
        if declared_path:
            resolved = _resolve_reference(declared_path, base_dir=path.parent, label="CODE_PIN")
            section_summary[section_name] = {
                "path": str(resolved),
                "exists": resolved.is_file(),
                "source_commit": section.get("source_commit"),
                "git_blob_sha1": section.get("git_blob_sha1"),
            }
            if not resolved.is_file():
                missing.append(section_name)
        else:
            missing.append(section_name)
    if missing:
        return {
            "name": "code_pins",
            "status": "PROVENANCE_INVALID",
            "reason": f"CODE_PIN_REFERENCES_MISSING:{','.join(missing)}",
            "source_path": str(path),
            "source_sha256": source_sha,
            "section_summary": section_summary,
            "verification_scope": "METADATA_ONLY_FINAL_GATE_REVALIDATES_GIT_BLOBS",
        }
    return {
        "name": "code_pins",
        "status": "READY",
        "reason": "FROZEN_CODE_PIN_MANIFEST_METADATA_PRESENT",
        "source_path": str(path),
        "source_sha256": source_sha,
        "schema_version": payload.get("schema_version"),
        "pin_status": payload.get("status"),
        "section_summary": section_summary,
        "verification_scope": "METADATA_ONLY_FINAL_GATE_REVALIDATES_GIT_BLOBS",
        "protected_outcome_accessed": False,
    }


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
    inventory_sha = ""
    if not inventory.empty:
        # The pure core is the authority for the canonical inventory identity.
        from idx_trade.prospective_preaccess_readiness_v1 import validate_partial_session_inventory

        inventory_sha = validate_partial_session_inventory(inventory)["partial_inventory_sha256"]
    counter = adapt_runtime_counter(
        monitoring / "eod_automation" / "v4_x1_pipeline" / "latest.json",
        inventory_sha256=inventory_sha or None,
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
    return {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "audit_mode": "OUTCOME_BLIND_LOCAL_PRODUCTION_SHAPE_AUDIT",
        "repo_root": str(repo),
        "data_root": str(root),
        "as_of_session": str(as_of_session),
        "sources": {
            "schedule": schedule,
            "inventory": inventory_source,
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
