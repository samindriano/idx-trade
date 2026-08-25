"""Outcome-blind completion artifacts for V4-X1 pre-access readiness.

This module is deliberately a thin, immutable bridge over the existing
production score artifacts and the existing V4-X1 gate.  It does not score,
rerank, materialize targets, read outcomes, or mutate the live runtime.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from idx_trade.prospective_evaluation_gate_v1 import (
    CANONICAL_TARGET_ID,
    RANKING_SEMANTICS,
    _load_score_artifact,
    inspect_persisted_access_status,
    _validate_score_manifest,
    validate_session_inventory,
)
from idx_trade.prospective_preaccess_adapters_v1 import (
    CODE_PIN_MANIFEST_SHA256,
    MODEL_FINGERPRINT,
    MODEL_GENERATION,
    MODEL_NAME,
    PRODUCTION_SCORE_MANIFEST_SCHEMA,
    ProductionAdapterError,
    _validate_score_manifest as _validate_production_manifest,
    gate_shape_inventory_sha256,
    project_score_frame_to_gate_shape,
    sha256_file,
)


PROJECTION_RULE_ID = "V4_X1_EXACT_DATE_TICKER_ALPHA_CONSENSUS_NO_RERANK_NO_TRANSFORM_V1"
COMPLETION_SCHEMA = "v4_x1_preaccess_artifact_completion_v1"
INVENTORY_SCHEMA = "v4_x1_admitted_gate_inventory_v1"
COUNTER_ATTESTATION_SCHEMA = "v4_x1_counter_attestation_v1"
PAPER_ATTESTATION_SCHEMA = "v4_x1_paper_continuity_attestation_v1"
BENCHMARK_ATTESTATION_SCHEMA = "v4_x1_benchmark_attestation_v1"
ACCESS_AUDIT_SCHEMA = "v4_x1_preaccess_audit_v1"
TARGET_ATTESTATION_SCHEMA = "v4_x1_target_attestation_v1"
SAFE_SESSION_AUDIT_SCHEMA = "idx_trade_forward_session_audit_safe_input_v1"
SAFE_SESSION_AUDIT_ATTESTATION_SCHEMA = "v4_x1_paper_continuity_attestation_v1"

_SAFE_AUDIT_FORBIDDEN_TOKENS = frozenset(
    {"outcome", "realized", "label", "vault", "nav", "pnl", "return", "target", "score", "alpha"}
)
_SAFE_AUDIT_TOP_KEYS = frozenset({"schema_version", "outcome_blind", "sessions", "source_reference"})
_SAFE_AUDIT_SESSION_KEYS = frozenset(
    {
        "session_date",
        "forward_position",
        "terminal_state",
        "continuity_valid",
        "execution_provenance_valid",
        "preclassified_invalidity",
        "invalidity_reason",
        "execution_material_drag",
        "material_drag_rule_id",
        "paperstate_path",
        "paperstate_sha256",
        "execution_path",
        "execution_sha256",
        "missed_execution_path",
        "missed_execution_sha256",
    }
)


class CompletionArtifactError(ProductionAdapterError):
    """Raised when a completion artifact cannot be created safely."""


def _canonical_payload_sha(payload: Mapping[str, Any], field: str) -> str:
    body = dict(payload)
    body.pop(field, None)
    return sha256_bytes(_json_bytes(body))


def _safe_audit_key_check(value: object, *, path: str = "safe_audit") -> None:
    """Reject outcome-bearing metadata before any paper artifact is built."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).strip().lower()
            if key_text != "outcome_blind" and any(token in key_text for token in _SAFE_AUDIT_FORBIDDEN_TOKENS):
                raise CompletionArtifactError(f"SAFE_AUDIT_FORBIDDEN_METADATA:{path}.{key}")
            _safe_audit_key_check(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _safe_audit_key_check(child, path=f"{path}[{index}]")


def _safe_metadata_path(value: str | Path, *, label: str, root: Path | None = None) -> Path:
    path = Path(value).expanduser().resolve()
    lowered = str(path).replace("\\", "/").lower()
    if any(token in part for part in lowered.split("/") for token in ("outcome", "realized", "label", "vault")):
        raise CompletionArtifactError(f"{label}_PROTECTED_PATH_REFUSED")
    if root is not None and path != root.resolve() and root.resolve() not in path.parents:
        raise CompletionArtifactError(f"{label}_OUTSIDE_EVIDENCE_ROOT")
    if not path.is_file():
        raise CompletionArtifactError(f"{label}_MISSING")
    return path


def _verified_safe_json(path: str | Path, *, expected_sha256: str | None, label: str, root: Path | None = None) -> tuple[Path, dict[str, Any], str]:
    safe = _safe_metadata_path(path, label=label, root=root)
    actual = sha256_file(safe)
    if expected_sha256 is not None and actual != str(expected_sha256).lower():
        raise CompletionArtifactError(f"{label}_SHA256_MISMATCH")
    try:
        payload = json.loads(safe.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompletionArtifactError(f"{label}_UNREADABLE") from exc
    if not isinstance(payload, dict):
        raise CompletionArtifactError(f"{label}_NOT_OBJECT")
    _safe_audit_key_check(payload, path=label.lower())
    return safe, payload, actual


def _verify_paperstate_snapshot(
    path_value: str,
    sha_value: str,
    *,
    expected_session: str,
    expected_parent: tuple[str, str] | None,
    evidence_root: Path,
) -> tuple[Path, str]:
    path, payload, actual = _verified_safe_json(
        path_value, expected_sha256=sha_value, label="PAPERSTATE", root=evidence_root
    )
    if payload.get("schema_version") != "idx_trade_forward_dividend_runtime_state_v1_1":
        raise CompletionArtifactError("PAPERSTATE_SCHEMA_MISMATCH")
    if payload.get("session_date") != expected_session:
        raise CompletionArtifactError("PAPERSTATE_SESSION_MISMATCH")
    if not isinstance(payload.get("state"), Mapping) or not isinstance(payload.get("hashes"), Mapping):
        raise CompletionArtifactError("PAPERSTATE_REQUIRED_METADATA_MISSING")
    declared_payload_sha = str(payload.get("snapshot_payload_sha256") or "").lower()
    if not declared_payload_sha or _canonical_payload_sha(payload, "snapshot_payload_sha256") != declared_payload_sha:
        raise CompletionArtifactError("PAPERSTATE_PAYLOAD_SHA256_MISMATCH")
    previous = payload.get("previous_snapshot")
    if not isinstance(previous, Mapping):
        raise CompletionArtifactError("PAPERSTATE_PARENT_REFERENCE_MISSING")
    parent_path = previous.get("path")
    parent_sha = previous.get("sha256")
    parent_date = previous.get("session_date")
    if not all(isinstance(value, str) and value for value in (parent_path, parent_sha, parent_date)):
        raise CompletionArtifactError("PAPERSTATE_PARENT_REFERENCE_INVALID")
    if str(parent_date) >= expected_session:
        raise CompletionArtifactError("PAPERSTATE_PARENT_NOT_PRIOR")
    parent = _safe_metadata_path(parent_path, label="PAPERSTATE_PARENT", root=evidence_root)
    if sha256_file(parent) != str(parent_sha).lower():
        raise CompletionArtifactError("PAPERSTATE_PARENT_SHA256_MISMATCH")
    if expected_parent is not None:
        expected_path, expected_sha = expected_parent
        if parent != Path(expected_path).resolve() or str(parent_sha).lower() != str(expected_sha).lower():
            raise CompletionArtifactError("PAPERSTATE_PARENT_CHAIN_MISMATCH")
    return path, actual


def produce_paper_attestation_from_safe_audit(
    source_path: str | Path,
    *,
    output_path: str | Path,
    expected_sessions: Iterable[str],
    predecessor_session_date: str,
    evidence_root: str | Path | None = None,
) -> dict[str, Any]:
    """Consume a normalized Session Audit/PaperState ledger without runtime imports.

    The input is a public, metadata-only bridge produced by the E2E audit lane.
    It is intentionally narrower than the E2E auditor: only immutable paths,
    hashes, terminal state, and PaperState parent identity cross this boundary.
    """

    source, payload, source_sha = _verified_safe_json(
        source_path, expected_sha256=None, label="SESSION_AUDIT"
    )
    root = Path(evidence_root).expanduser().resolve() if evidence_root is not None else source.parent
    if source != root and root not in source.parents:
        raise CompletionArtifactError("SESSION_AUDIT_OUTSIDE_EVIDENCE_ROOT")
    if payload.get("schema_version") != SAFE_SESSION_AUDIT_SCHEMA or payload.get("outcome_blind") is not True:
        raise CompletionArtifactError("SESSION_AUDIT_SCHEMA_OR_SCOPE_INVALID")
    if set(payload) - _SAFE_AUDIT_TOP_KEYS:
        raise CompletionArtifactError("SESSION_AUDIT_UNDECLARED_TOP_LEVEL_FIELD")
    raw_sessions = payload.get("sessions")
    if not isinstance(raw_sessions, list):
        raise CompletionArtifactError("SESSION_AUDIT_SESSIONS_MISSING")
    expected = [str(value) for value in expected_sessions]
    if expected != sorted(set(expected)):
        raise CompletionArtifactError("EXPECTED_SESSION_BLOCK_INVALID")
    observed_dates = [str(item.get("session_date")) for item in raw_sessions if isinstance(item, Mapping)]
    if len(raw_sessions) != len(observed_dates) or observed_dates != sorted(set(observed_dates)):
        raise CompletionArtifactError("SESSION_AUDIT_DUPLICATE_OR_MALFORMED_SESSION")
    if observed_dates != expected:
        return {
            "status": "NOT_AVAILABLE",
            "reason": "SESSION_AUDIT_INCOMPLETE_OR_NONCONTIGUOUS",
            "source_path": str(source),
            "source_sha256": source_sha,
            "observed_session_count": len(observed_dates),
            "required_session_count": len(expected),
        }

    normalized: list[dict[str, Any]] = []
    previous_snapshot: tuple[str, str] | None = None
    missed_count = 0
    for position, item in enumerate(raw_sessions, start=1):
        if not isinstance(item, Mapping) or set(item) - _SAFE_AUDIT_SESSION_KEYS:
            raise CompletionArtifactError("SESSION_AUDIT_UNDECLARED_SESSION_FIELD")
        if item.get("forward_position") != position:
            raise CompletionArtifactError("SESSION_AUDIT_POSITION_GAP_OR_DUPLICATE")
        state = str(item.get("terminal_state") or "")
        if state not in {"EXECUTION", "MISSED_EXECUTION_NO_CERTIFIED_OPEN"}:
            raise CompletionArtifactError("SESSION_AUDIT_TERMINAL_STATE_INVALID")
        if item.get("continuity_valid") is not True:
            raise CompletionArtifactError("SESSION_AUDIT_CONTINUITY_INVALID")
        if item.get("implementation_defect") is True or item.get("provenance_invalid") is True:
            raise CompletionArtifactError("SESSION_AUDIT_INVALIDITY_NOT_ADMISSIBLE")
        paper_path = item.get("paperstate_path")
        paper_sha = item.get("paperstate_sha256")
        if not isinstance(paper_path, str) or not isinstance(paper_sha, str):
            raise CompletionArtifactError("SESSION_AUDIT_PAPERSTATE_REFERENCE_MISSING")
        verified_paper_path, verified_paper_sha = _verify_paperstate_snapshot(
            paper_path,
            paper_sha,
            expected_session=observed_dates[position - 1],
            expected_parent=previous_snapshot,
            evidence_root=root,
        )
        previous_snapshot = (str(verified_paper_path), verified_paper_sha)
        if state == "EXECUTION":
            if item.get("execution_provenance_valid") is not True:
                raise CompletionArtifactError("SESSION_AUDIT_EXECUTION_PROVENANCE_INVALID")
            if item.get("missed_execution_path") is not None or item.get("missed_execution_sha256") is not None:
                raise CompletionArtifactError("SESSION_AUDIT_EXECUTION_AND_MISSED_BOTH_PRESENT")
            terminal_path, terminal_sha = item.get("execution_path"), item.get("execution_sha256")
            if not isinstance(terminal_path, str) or not isinstance(terminal_sha, str):
                raise CompletionArtifactError("SESSION_AUDIT_EXECUTION_REFERENCE_MISSING")
            _verified_safe_json(terminal_path, expected_sha256=terminal_sha, label="EXECUTION", root=root)
            if item.get("preclassified_invalidity") is True:
                raise CompletionArtifactError("SESSION_AUDIT_EXECUTION_PRECLASSIFIED_INVALID")
        else:
            missed_count += 1
            if item.get("execution_provenance_valid") is not False:
                raise CompletionArtifactError("SESSION_AUDIT_MISSED_EXECUTION_PROVENANCE_INVALID")
            if item.get("execution_path") is not None or item.get("execution_sha256") is not None:
                raise CompletionArtifactError("SESSION_AUDIT_EXECUTION_AND_MISSED_BOTH_PRESENT")
            terminal_path, terminal_sha = item.get("missed_execution_path"), item.get("missed_execution_sha256")
            if not isinstance(terminal_path, str) or not isinstance(terminal_sha, str):
                raise CompletionArtifactError("SESSION_AUDIT_MISSED_REFERENCE_MISSING")
            _, missed_payload, _ = _verified_safe_json(
                terminal_path, expected_sha256=terminal_sha, label="MISSED_EXECUTION", root=root
            )
            if missed_payload.get("status") != "MISSED_EXECUTION_NO_CERTIFIED_OPEN":
                raise CompletionArtifactError("SESSION_AUDIT_MISSED_STATUS_INVALID")
            if item.get("preclassified_invalidity") is not True or not str(item.get("invalidity_reason") or "").strip():
                raise CompletionArtifactError("SESSION_AUDIT_MISSED_INVALIDITY_NOT_PRECLASSIFIED")
        normalized.append(
            {
                "session_date": observed_dates[position - 1],
                "forward_position": position,
                "terminal_state": state,
                "paperstate_path": str(verified_paper_path),
                "paperstate_sha256": verified_paper_sha,
            }
        )

    output = Path(output_path).resolve()
    paper_payload = {
        "schema_version": PAPER_ATTESTATION_SCHEMA,
        "predecessor_session_date": str(predecessor_session_date),
        "session_count": len(normalized),
        "first_session_date": normalized[0]["session_date"],
        "last_session_date": normalized[-1]["session_date"],
        "continuity_valid": True,
        "execution_provenance_valid": missed_count == 0,
        "preclassified_invalidity": missed_count > 0,
        "invalidity_reason": "MISSED_EXECUTION_NO_CERTIFIED_OPEN" if missed_count else "",
        "execution_material_drag": False,
        "material_drag_rule_id": "SESSION_AUDIT_METADATA_ONLY_NO_ECONOMIC_VALUES",
        "transitions": [
            {"session_date": row["session_date"], "forward_position": row["forward_position"]}
            for row in normalized
        ],
        "source_session_audit_path": str(source),
        "source_session_audit_sha256": source_sha,
        "missed_execution_count": missed_count,
        "outcome_scope": "NO_NAV_NO_RETURNS_NO_PNL_NO_OUTCOMES",
    }
    paper_sha = _atomic_json(output, paper_payload)
    return {
        "status": "READY_FOR_FINAL_GATE_REVALIDATION",
        "paper_attestation_path": str(output),
        "paper_attestation_sha256": paper_sha,
        "source_session_audit_path": str(source),
        "source_session_audit_sha256": source_sha,
        "session_count": len(normalized),
        "missed_execution_count": missed_count,
    }


def build_prior_access_audit(
    canonical_output_root: str | Path | None,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Map the existing status-only inspector without declaring arbitrary emptiness clean."""

    if canonical_output_root is None:
        return {
            "status": "NOT_AVAILABLE",
            "reason": "PRIOR_ACCESS_AUDIT_NOT_AVAILABLE_CANONICAL_ROOT_UNSET",
            "protected_outcomes_accessed": False,
        }
    root = Path(canonical_output_root).expanduser().resolve()
    inspection = inspect_persisted_access_status(root)
    status = str(inspection.get("status") or "")
    if status == "SYNTHETIC_REHEARSAL_COMPLETE":
        payload = {
            "schema_version": ACCESS_AUDIT_SCHEMA,
            "review_complete": True,
            "unauthorized_access_known": False,
            "prior_access_marker_exists": False,
            "source_status_path": str(root),
            "source_status": status,
            "scope": "EXPLICIT_SYNTHETIC_REHEARSAL_ONLY",
        }
        if output_path is None:
            raise CompletionArtifactError("PRIOR_ACCESS_OUTPUT_REQUIRED")
        sha = _atomic_json(Path(output_path).resolve(), payload)
        return {"status": "READY", "path": str(Path(output_path).resolve()), "sha256": sha, **payload}
    if status in {"REAL_ACCESS_ALREADY_COMPLETED", "INTEGRITY_FAILURE", "ORPHAN_OR_INTERRUPTED_STATE"}:
        return {"status": "PROVENANCE_INVALID", "reason": f"PERSISTED_ACCESS_STATUS:{status}", **inspection}
    return {
        "status": "NOT_AVAILABLE",
        "reason": "PRIOR_ACCESS_AUDIT_REQUIRES_EXPLICIT_NONEMPTY_CANONICAL_STATUS",
        "persisted_status": status,
        "protected_outcomes_accessed": False,
    }


def build_local_composite_benchmark(
    data_root: str | Path,
    *,
    sessions: Iterable[str],
    predecessor_session_date: str,
    output_root: str | Path,
) -> dict[str, Any]:
    """Build only the public IDX Composite artifact from existing EOD evidence."""

    root = Path(data_root).resolve()
    output = Path(output_root).resolve()
    requested = [str(predecessor_session_date), *[str(value) for value in sessions]]
    if requested != sorted(set(requested)):
        raise CompletionArtifactError("BENCHMARK_SESSION_ORDER_INVALID")
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for session in requested:
        source_file = root / "forward_monitoring" / "sessions" / session / "idx_index_summary.csv"
        if not source_file.is_file():
            missing.append(session)
            continue
        try:
            frame = pd.read_csv(source_file)
        except Exception as exc:
            raise CompletionArtifactError(f"BENCHMARK_SOURCE_UNREADABLE:{session}") from exc
        required = {"session_date", "index_code", "close", "source", "source_ref", "source_sha256", "source_retrieved_at"}
        if not required.issubset(frame.columns):
            raise CompletionArtifactError(f"BENCHMARK_SOURCE_SCHEMA_INVALID:{session}")
        selected = frame[frame["index_code"].astype(str).str.upper().eq("COMPOSITE")]
        if len(selected) != 1 or str(selected.iloc[0]["session_date"]) != session:
            raise CompletionArtifactError(f"BENCHMARK_COMPOSITE_IDENTITY_INVALID:{session}")
        row = selected.iloc[0]
        close = pd.to_numeric(pd.Series([row["close"]]), errors="coerce").iloc[0]
        if pd.isna(close) or float(close) <= 0:
            raise CompletionArtifactError(f"BENCHMARK_CLOSE_INVALID:{session}")
        rows.append({
            "session_date": session,
            "benchmark_close": float(close),
            "source": str(row["source"]),
            "source_ref": str(row["source_ref"]),
            "source_sha256": str(row["source_sha256"]),
            "source_csv_sha256": sha256_file(source_file),
            "source_retrieved_at": str(row["source_retrieved_at"]),
        })
    result: dict[str, Any] = {
        "status": "PARTIAL_NOT_GATE_READY" if missing else "READY_FOR_FINAL_GATE_REVALIDATION",
        "benchmark_identity": "IDX_OFFICIAL_INDEX_SUMMARY_COMPOSITE",
        "requested_session_count": len(requested),
        "session_count": len(rows),
        "missing_sessions": missing,
        "publication_time_claim": "NONE",
        "rows": rows,
    }
    if missing:
        return result
    artifact = output / "benchmark.parquet"
    frame = pd.DataFrame(rows)[["session_date", "benchmark_close"]]
    artifact_sha = _atomic_immutable_bytes(artifact, _parquet_bytes(frame))
    attestation = output / "benchmark_attestation.json"
    attestation_sha = _atomic_json(
        attestation,
        {
            "schema_version": BENCHMARK_ATTESTATION_SCHEMA,
            "status": "PINNED",
            "benchmark_identity": "IDX_OFFICIAL_INDEX_SUMMARY_COMPOSITE",
            "artifact_path": str(artifact),
            "artifact_sha256": artifact_sha,
            "source_rows": rows,
            "publication_time_claim": "NONE",
        },
    )
    result.update({"artifact_path": str(artifact), "artifact_sha256": artifact_sha, "attestation_path": str(attestation), "attestation_sha256": attestation_sha})
    return result


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_immutable_bytes(path: Path, payload: bytes) -> str:
    """Create bytes once; an existing equal object is idempotent, mismatch fails."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    expected = sha256_bytes(payload)
    if path.exists():
        if not path.is_file() or sha256_file(path) != expected:
            raise CompletionArtifactError(f"IMMUTABLE_ARTIFACT_CONFLICT:{path}")
        return expected
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, path)
        except FileExistsError:
            if not path.is_file() or sha256_file(path) != expected:
                raise CompletionArtifactError(f"IMMUTABLE_ARTIFACT_CONFLICT:{path}")
        return expected
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> str:
    return _atomic_immutable_bytes(path, _json_bytes(payload))


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    # No timestamped metadata and no compression are used so the same input
    # projection is byte-stable across an idempotent rerun.
    frame.to_parquet(buffer, index=False, compression=None, engine="pyarrow")
    return buffer.getvalue()


def _safe_source_manifest(
    manifest_path: Path,
    *,
    source_root: Path,
    expected_session: str,
) -> tuple[dict[str, Any], Path, pd.DataFrame, str, str]:
    manifest_path = manifest_path.resolve()
    source_root = source_root.resolve()
    if not manifest_path.is_file() or source_root not in manifest_path.parents:
        raise CompletionArtifactError("SOURCE_MANIFEST_OUTSIDE_BOUNDARY")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompletionArtifactError("SOURCE_MANIFEST_UNREADABLE") from exc
    if not isinstance(payload, dict):
        raise CompletionArtifactError("SOURCE_MANIFEST_NOT_OBJECT")
    try:
        disposition = _validate_production_manifest(payload)
    except Exception as exc:
        raise CompletionArtifactError(f"SOURCE_MANIFEST_INVALID:{exc}") from exc
    session = str(payload.get("session_date") or "")
    if session != expected_session:
        raise CompletionArtifactError("SOURCE_SESSION_IDENTITY_MISMATCH")
    output = payload.get("output")
    artifact_value = output.get("artifact_path") if isinstance(output, Mapping) else None
    artifact = Path(str(artifact_value)).resolve()
    if not artifact.is_file() or source_root not in artifact.parents:
        raise CompletionArtifactError("SOURCE_ARTIFACT_OUTSIDE_BOUNDARY")
    declared_sha = str(output.get("artifact_sha256") or "").lower()
    actual_sha = sha256_file(artifact)
    if actual_sha != declared_sha:
        raise CompletionArtifactError("SOURCE_ARTIFACT_SHA256_MISMATCH")
    try:
        frame = pd.read_parquet(artifact)
    except Exception as exc:
        raise CompletionArtifactError("SOURCE_ARTIFACT_UNREADABLE") from exc
    declared_columns = output.get("columns")
    if list(frame.columns) != [str(value) for value in declared_columns or []]:
        raise CompletionArtifactError("SOURCE_ARTIFACT_COLUMNS_MISMATCH")
    if frame.empty:
        raise CompletionArtifactError("SOURCE_ARTIFACT_EMPTY")
    return payload, artifact, frame, actual_sha, sha256_file(manifest_path)


def project_verified_score_session(
    source_manifest_path: str | Path,
    *,
    source_root: str | Path,
    output_root: str | Path,
    expected_session: str,
) -> dict[str, Any]:
    """Publish one exact, immutable gate-shape projection from a real score run."""

    source_manifest = Path(source_manifest_path).resolve()
    source_root_path = Path(source_root).resolve()
    output_root_path = Path(output_root).resolve()
    payload, source_artifact, source_frame, source_sha, source_manifest_sha = _safe_source_manifest(
        source_manifest, source_root=source_root_path, expected_session=expected_session
    )
    try:
        projected = project_score_frame_to_gate_shape(source_frame)
    except Exception as exc:
        raise CompletionArtifactError(f"SOURCE_PROJECTION_REJECTED:{exc}") from exc
    if list(projected.columns) != ["date", "ticker", "alpha_consensus"]:
        raise CompletionArtifactError("PROJECTION_SHAPE_INVALID")
    if projected["ticker"].tolist() != source_frame["ticker"].tolist():
        raise CompletionArtifactError("PROJECTION_TICKER_ORDER_CHANGED")
    if projected["alpha_consensus"].tolist() != source_frame["alpha_consensus"].tolist():
        raise CompletionArtifactError("PROJECTION_SCORE_CHANGED")
    if projected["date"].astype(str).tolist() != source_frame["date"].astype(str).tolist():
        raise CompletionArtifactError("PROJECTION_DATE_ORDER_CHANGED")
    dates = pd.to_datetime(projected["date"], errors="coerce")
    if dates.isna().any() or dates.dt.date.astype(str).nunique() != 1:
        raise CompletionArtifactError("PROJECTION_SESSION_INVALID")
    if dates.dt.date.astype(str).iloc[0] != expected_session:
        raise CompletionArtifactError("PROJECTION_SESSION_MISMATCH")

    session_dir = output_root_path / "projected_scores" / expected_session
    artifact_path = session_dir / "score_artifact.parquet"
    manifest_path = session_dir / "manifest.json"
    artifact_sha = _atomic_immutable_bytes(artifact_path, _parquet_bytes(projected))
    projected_manifest: dict[str, Any] = {
        "schema_version": PRODUCTION_SCORE_MANIFEST_SCHEMA,
        "model_id": MODEL_NAME,
        "generation": MODEL_GENERATION,
        "model_fingerprint": MODEL_FINGERPRINT,
        "ranking": RANKING_SEMANTICS,
        "session_date": expected_session,
        "status": "DONE",
        "output": {
            "artifact_path": str(artifact_path),
            "artifact_sha256": artifact_sha,
            "columns": ["date", "ticker", "alpha_consensus"],
        },
        "guards": {
            "historical_prediction_generated": False,
            "model_refit": False,
            "model_retuned": False,
            "protected_outcome_accessed": False,
            "provider_calls": False,
            "realized_forward_outcome_loaded": False,
            "science_changed": False,
        },
        "metadata": {
            "projection_rule_id": PROJECTION_RULE_ID,
            "source_production_artifact_path": str(source_artifact),
            "source_production_artifact_sha256": source_sha,
            "source_production_manifest_path": str(source_manifest),
            "source_production_manifest_sha256": source_manifest_sha,
            "source_production_manifest_schema_version": payload.get("schema_version"),
            "source_production_model_fingerprint": payload.get("model_fingerprint"),
            "safety_scope": "OUTCOME_BLIND_SCORE_SIDE_ONLY",
        },
    }
    manifest_sha = _atomic_json(manifest_path, projected_manifest)
    # Re-enter the exact frozen per-score gate validators after publication;
    # the projection helper is not itself an admission decision.
    _validate_score_manifest(
        manifest_path,
        session_date=pd.Timestamp(expected_session),
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha,
    )
    _load_score_artifact(
        artifact_path,
        session_date=pd.Timestamp(expected_session),
        session_index=0,
        artifact_sha256=artifact_sha,
        manifest_sha256=manifest_sha,
    )
    return {
        "session_date": expected_session,
        "source_artifact_path": str(source_artifact),
        "source_artifact_sha256": source_sha,
        "source_manifest_path": str(source_manifest),
        "source_manifest_sha256": source_manifest_sha,
        "projected_artifact_path": str(artifact_path),
        "projected_artifact_sha256": artifact_sha,
        "projected_manifest_path": str(manifest_path),
        "projected_manifest_sha256": manifest_sha,
        "rows": len(projected),
        "projection_rule_id": PROJECTION_RULE_ID,
        "validated_by_existing_gate_contract": True,
    }


def build_admitted_inventory(
    projections: Iterable[Mapping[str, Any]],
    *,
    official_sessions: Iterable[str],
    output_root: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build the partial admitted inventory; 100-row final validation stays gate-owned."""

    schedule = [str(value) for value in official_sessions]
    index_by_date = {value: index + 1 for index, value in enumerate(schedule)}
    rows: list[dict[str, Any]] = []
    for position, item in enumerate(sorted(projections, key=lambda value: str(value["session_date"])), start=1):
        session = str(item["session_date"])
        if session not in index_by_date:
            raise CompletionArtifactError("ADMITTED_SESSION_NOT_IN_OFFICIAL_CALENDAR")
        rows.append(
            {
                "forward_position": position,
                "session_index": index_by_date[session],
                "session_date": session,
                "score_artifact_path": str(item["projected_artifact_path"]),
                "score_artifact_sha256": str(item["projected_artifact_sha256"]).lower(),
                "score_manifest_path": str(item["projected_manifest_path"]),
                "score_manifest_sha256": str(item["projected_manifest_sha256"]).lower(),
            }
        )
    columns = [
        "forward_position",
        "session_index",
        "session_date",
        "score_artifact_path",
        "score_artifact_sha256",
        "score_manifest_path",
        "score_manifest_sha256",
    ]
    inventory = pd.DataFrame(rows, columns=columns)
    from idx_trade.prospective_preaccess_readiness_v1 import validate_partial_session_inventory

    partial = validate_partial_session_inventory(inventory)
    gate_identity = gate_shape_inventory_sha256(inventory)
    root = Path(output_root).resolve()
    inventory_path = root / "admitted_inventory.csv"
    inventory_sha = _atomic_immutable_bytes(
        inventory_path, inventory.to_csv(index=False, lineterminator="\n").encode("utf-8")
    )
    manifest = {
        "schema_version": INVENTORY_SCHEMA,
        "status": partial["status"],
        "inventory_kind": "PARTIAL_ADMITTED_GATE_SHAPE" if len(inventory) < 100 else "FINAL_GATE_ADMITTED",
        "session_count": len(inventory),
        "required_session_count": 100,
        "inventory_path": str(inventory_path),
        "inventory_sha256": inventory_sha,
        "partial_admitted_gate_shape_sha256": gate_identity,
        "canonical_admitted_gate_inventory_sha256": gate_identity if len(inventory) == 100 else "NOT_AVAILABLE",
        "source_projection_count": len(rows),
        "outcome_scope": "NO_TARGETS_NO_OUTCOMES_NO_LABELS",
    }
    manifest_path = root / "admitted_inventory_manifest.json"
    manifest_sha = _atomic_json(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    manifest["manifest_sha256"] = manifest_sha
    return inventory, manifest


def reconcile_runtime_counter(
    counter_status_path: str | Path,
    inventory: pd.DataFrame,
    *,
    attestation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Reconcile status-only counter facts without changing the live counter."""

    status_path = Path(counter_status_path).resolve()
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        counter = payload["x1_counter"]
        completed = int(counter["completed"])
        target = int(counter["target"])
        remaining = int(counter["remaining"])
        sessions = [str(value) for value in counter["sessions"]]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise CompletionArtifactError("COUNTER_STATUS_UNREADABLE") from exc
    observed = inventory["session_date"].astype(str).tolist()
    if completed != len(sessions) or remaining != target - completed:
        raise CompletionArtifactError("COUNTER_STATUS_INTERNAL_COUNTS_INVALID")
    if sessions != sorted(set(sessions)) or sessions != observed:
        raise CompletionArtifactError("COUNTER_SESSIONS_DO_NOT_MATCH_ADMITTED_INVENTORY")
    inventory_identity = gate_shape_inventory_sha256(inventory)
    result: dict[str, Any] = {
        "status": "ACCUMULATING" if completed < 100 else "READY_FOR_ATTESTATION",
        "completed": completed,
        "target": target,
        "remaining": remaining,
        "sessions": sessions,
        "session_inventory_sha256": inventory_identity if completed == 100 else "NOT_AVAILABLE",
        "runtime_counter_changed": False,
        "attestation_path": None,
        "attestation_sha256": None,
    }
    if completed < 100:
        return result
    if target != 100 or len(inventory) != 100:
        raise CompletionArtifactError("COUNTER_NOT_EXACTLY_100")
    if attestation_path is None:
        result["status"] = "PENDING_ATTESTATION"
        return result
    path = Path(attestation_path).resolve()
    attestation = {
        "schema_version": COUNTER_ATTESTATION_SCHEMA,
        "current": 100,
        "target": 100,
        "session_inventory_sha256": inventory_identity,
    }
    sha = _atomic_json(path, attestation)
    result.update({"status": "ATTESTED", "attestation_path": str(path), "attestation_sha256": sha})
    return result


def write_preflight_bundle(
    path: str | Path,
    *,
    fixture_root: str | Path,
    inventory: pd.DataFrame,
    counter: tuple[str, str],
    target: tuple[str, str],
    paper: tuple[str, str],
    benchmark: tuple[str, str],
    access_audit: tuple[str, str],
) -> tuple[str, str]:
    """Write a bundle only after the existing 100-row inventory validator passes."""

    root = Path(fixture_root).resolve()
    if len(inventory) != 100:
        raise CompletionArtifactError("PREFLIGHT_BUNDLE_REQUIRES_EXACT_100_INVENTORY")
    _, _, inventory_sha = validate_session_inventory(inventory, fixture_root=root)
    inventory_file = root / "admitted_inventory.csv"
    if not inventory_file.is_file():
        raise CompletionArtifactError("PREFLIGHT_INVENTORY_BYTES_MISSING")
    pairs = {
        "counter": counter,
        "target": target,
        "paper": paper,
        "benchmark": benchmark,
        "access_audit": access_audit,
    }
    for label, (artifact_path, expected_sha) in pairs.items():
        file_path = Path(artifact_path).resolve()
        if not file_path.is_file() or root not in file_path.parents:
            raise CompletionArtifactError(f"PREFLIGHT_{label.upper()}_OUTSIDE_FIXTURE")
        if sha256_file(file_path) != str(expected_sha).lower():
            raise CompletionArtifactError(f"PREFLIGHT_{label.upper()}_SHA_MISMATCH")
    payload = {
        "schema_version": "v4_x1_prospective_preflight_bundle_v1",
        "fixture_root": str(root),
        "session_inventory_path": str(inventory_file),
        "session_inventory_sha256": sha256_file(inventory_file),
        "counter_attestation_path": str(Path(counter[0]).resolve()),
        "counter_attestation_sha256": str(counter[1]).lower(),
        "target_attestation_path": str(Path(target[0]).resolve()),
        "target_attestation_sha256": str(target[1]).lower(),
        "paper_attestation_path": str(Path(paper[0]).resolve()),
        "paper_attestation_sha256": str(paper[1]).lower(),
        "benchmark_attestation_path": str(Path(benchmark[0]).resolve()),
        "benchmark_attestation_sha256": str(benchmark[1]).lower(),
        "access_audit_path": str(Path(access_audit[0]).resolve()),
        "access_audit_sha256": str(access_audit[1]).lower(),
        "inventory_identity": inventory_sha,
        "scope": "SYNTHETIC_REHEARSAL_ONLY",
    }
    bundle_path = Path(path).resolve()
    bundle_sha = _atomic_json(bundle_path, payload)
    return str(bundle_path), bundle_sha


def write_synthetic_score_session(
    root: str | Path, session_date: str, *, row_count: int = 3, session_index: int = 1
) -> dict[str, Any]:
    """Write a deterministic gate-compatible score fixture, never a real score."""

    tickers = [f"SYN{index:03d}" for index in range(row_count)]
    frame = pd.DataFrame(
        {
            "date": [session_date] * row_count,
            "ticker": tickers,
            "alpha_consensus": [1.0 - index / max(row_count, 1) for index in range(row_count)],
        }
    )
    root_path = Path(root).resolve()
    directory = root_path / "scores" / session_date
    artifact = directory / "score_artifact.parquet"
    manifest = directory / "manifest.json"
    artifact_sha = _atomic_immutable_bytes(artifact, _parquet_bytes(frame))
    payload = {
        "schema_version": PRODUCTION_SCORE_MANIFEST_SCHEMA,
        "model_id": MODEL_NAME,
        "generation": MODEL_GENERATION,
        "model_fingerprint": MODEL_FINGERPRINT,
        "ranking": RANKING_SEMANTICS,
        "session_date": session_date,
        "status": "DONE",
        "output": {
            "artifact_path": str(artifact),
            "artifact_sha256": artifact_sha,
            "columns": ["date", "ticker", "alpha_consensus"],
        },
        "guards": {name: False for name in (
            "historical_prediction_generated", "model_refit", "model_retuned",
            "protected_outcome_accessed", "provider_calls", "realized_forward_outcome_loaded",
            "science_changed",
        )},
    }
    manifest_sha = _atomic_json(manifest, payload)
    return {
        "session_date": session_date,
        "session_index": session_index,
        "projected_artifact_path": str(artifact),
        "projected_artifact_sha256": artifact_sha,
        "projected_manifest_path": str(manifest),
        "projected_manifest_sha256": manifest_sha,
    }


def write_synthetic_attestations(
    root: str | Path,
    *,
    inventory: pd.DataFrame,
    predecessor_session_date: str,
    contract_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create only synthetic/non-protected inputs for gate rehearsal."""

    root_path = Path(root).resolve()
    root_path.mkdir(parents=True, exist_ok=True)
    first = str(inventory["session_date"].iloc[0])
    last = str(inventory["session_date"].iloc[-1])
    contract_target: dict[str, Any] | None = None
    if contract_path is not None:
        try:
            contract_payload = json.loads(Path(contract_path).read_text(encoding="utf-8"))
            candidate = contract_payload.get("target_identity")
            if not isinstance(candidate, dict):
                raise ValueError("contract target identity is missing")
            contract_target = dict(candidate)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise CompletionArtifactError("SYNTHETIC_CONTRACT_UNREADABLE") from exc
    if contract_target is None:
        contract_target = {
            "status": "RESOLVED",
            "target_id": CANONICAL_TARGET_ID,
            "horizon": {"h5": 5, "h10": 10},
            "definition": {"entry_price": "Open_(t+1)"},
            "transform": "SYNTHETIC_ONLY",
            "support": "SYNTHETIC_ONLY",
            "provenance": {"scope": "SYNTHETIC_ONLY"},
            "hashes": {"synthetic": True},
            "target_spec_path": "synthetic_target_spec.json",
            "target_spec_sha256": "synthetic",
            "construction_code": {"path": "synthetic_target_code.py", "sha256": "synthetic"},
        }
    target_identity_sha = hashlib.sha256(
        json.dumps(contract_target, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    source_manifest = root_path / "synthetic_target_source.json"
    source_payload = {
        "schema_version": "synthetic_target_source_v1",
        "canonical_target_id": str(contract_target.get("target_id") or CANONICAL_TARGET_ID),
        "target_identity_sha256": target_identity_sha,
        "target_identity": contract_target,
        "scope": "SYNTHETIC_ONLY_NO_PROTECTED_TARGET_ACCESS",
    }
    source_sha = _atomic_json(source_manifest, source_payload)
    target_path = root_path / "target_attestation.json"
    target_payload: dict[str, Any] = {
        "schema_version": TARGET_ATTESTATION_SCHEMA,
        "canonical_target_id": str(contract_target.get("target_id") or CANONICAL_TARGET_ID),
        "target_identity_sha256": target_identity_sha,
        "resolved": True,
        "required_session_count": 100,
        "matured_session_count": 100,
        "first_session_date": first,
        "last_session_date": last,
        "resolution_lineage": "SYNTHETIC_FIXTURE_ONLY_NO_PROTECTED_TARGET_ACCESS",
        "source_manifest_path": str(source_manifest),
        "source_manifest_sha256": source_sha,
    }
    if contract_path is not None:
        target_payload.update(
            {
                "horizon": contract_target.get("horizon"),
                "prediction": contract_target.get("prediction"),
                "definition": contract_target.get("definition"),
                "transform": contract_target.get("transform"),
                "support": contract_target.get("support"),
                "provenance": contract_target.get("provenance"),
                "target_hashes": contract_target.get("hashes"),
                "target_spec_path": contract_target.get("target_spec_path"),
                "target_spec_sha256": contract_target.get("target_spec_sha256"),
                "construction_code": contract_target.get("construction_code"),
            }
        )
    target_sha = _atomic_json(target_path, target_payload)
    paper_path = root_path / "paper_attestation.json"
    paper_payload = {
        "schema_version": PAPER_ATTESTATION_SCHEMA,
        "predecessor_session_date": predecessor_session_date,
        "session_count": 100,
        "first_session_date": first,
        "last_session_date": last,
        "continuity_valid": True,
        "execution_provenance_valid": True,
        "preclassified_invalidity": False,
        "invalidity_reason": "",
        "execution_material_drag": False,
        "material_drag_rule_id": "SYNTHETIC_NO_EXECUTION_COSTS",
        "transitions": [
            {"session_date": str(row.session_date), "forward_position": int(row.forward_position)}
            for row in inventory.itertuples(index=False)
        ],
    }
    paper_sha = _atomic_json(paper_path, paper_payload)
    dates = [predecessor_session_date] + inventory["session_date"].astype(str).tolist()
    benchmark = pd.DataFrame({"session_date": dates, "benchmark_close": [1000.0 + index for index in range(len(dates))]})
    benchmark_artifact = root_path / "benchmark.parquet"
    benchmark_sha = _atomic_immutable_bytes(benchmark_artifact, _parquet_bytes(benchmark))
    benchmark_path = root_path / "benchmark_attestation.json"
    benchmark_payload = {
        "schema_version": BENCHMARK_ATTESTATION_SCHEMA,
        "status": "PINNED",
        "benchmark_identity": "SYNTHETIC_IHSG_SHAPE_ONLY_NO_REAL_SERIES",
        "artifact_path": str(benchmark_artifact),
        "artifact_sha256": benchmark_sha,
    }
    benchmark_attestation_sha = _atomic_json(benchmark_path, benchmark_payload)
    access_path = root_path / "access_audit.json"
    access_sha = _atomic_json(
        access_path,
        {
            "schema_version": ACCESS_AUDIT_SCHEMA,
            "review_complete": True,
            "unauthorized_access_known": False,
            "prior_access_marker_exists": False,
            "scope": "SYNTHETIC_ONLY_NO_PROTECTED_ACCESS",
        },
    )
    return {
        "counter": None,
        "target": (str(target_path), target_sha),
        "paper": (str(paper_path), paper_sha),
        "benchmark": (str(benchmark_path), benchmark_attestation_sha),
        "access_audit": (str(access_path), access_sha),
    }


__all__ = [
    "CompletionArtifactError",
    "PROJECTION_RULE_ID",
    "SAFE_SESSION_AUDIT_SCHEMA",
    "build_admitted_inventory",
    "build_local_composite_benchmark",
    "build_prior_access_audit",
    "project_verified_score_session",
    "produce_paper_attestation_from_safe_audit",
    "reconcile_runtime_counter",
    "sha256_bytes",
    "write_preflight_bundle",
    "write_synthetic_attestations",
    "write_synthetic_score_session",
]
