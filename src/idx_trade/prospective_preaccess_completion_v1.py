"""Outcome-blind completion artifacts for V4-X1 pre-access readiness.

The module is a control-plane bridge over already-frozen V4-X1 evidence.  It
may read verified score-side artifacts and operational metadata, but it never
scores, reranks, materializes real targets, calls providers, or mutates the
forward runtime/counter/scheduler.
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
    _validate_score_manifest,
    inspect_persisted_access_status,
    validate_session_inventory,
)
from idx_trade.prospective_preaccess_adapters_v1 import (
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
CANONICAL_INVENTORY_SCHEMA = "v4_x1_canonical_admitted_gate_inventory_v1"
COUNTER_ATTESTATION_SCHEMA = "v4_x1_counter_attestation_v1"
PAPER_ATTESTATION_SCHEMA = "v4_x1_paper_continuity_attestation_v1"
BENCHMARK_ATTESTATION_SCHEMA = "v4_x1_benchmark_attestation_v1"
ACCESS_AUDIT_SCHEMA = "v4_x1_preaccess_audit_v1"
TARGET_ATTESTATION_SCHEMA = "v4_x1_target_attestation_v1"
SAFE_SESSION_AUDIT_SCHEMA = "idx_trade_forward_session_audit_safe_bridge_v2"
SOURCE_SESSION_AUDIT_SCHEMA = "idx_trade_forward_session_audit_v1"
CANONICAL_REAL_ACCESS_ROOT_ID = "V4_X1_PROSPECTIVE_REAL_EVALUATION_OUTPUT_V1"

_PROTECTED_PATH_TOKENS = ("outcome", "realized", "label", "vault", "protected_target")
_SAFE_AUDIT_FORBIDDEN_TOKENS = frozenset(
    {"outcome", "realized", "label", "vault", "nav", "pnl", "return", "target", "score", "alpha"}
)
_SAFE_LEDGER_OVERALL = frozenset(
    {"SESSION_HEALTHY", "SESSION_HEALTHY_LEGITIMATE_NOOP", "SESSION_MISSED_EXECUTION_NO_CERTIFIED_OPEN"}
)


class CompletionArtifactError(ProductionAdapterError):
    """Raised when a completion artifact cannot be created safely."""


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_payload_sha(payload: Mapping[str, Any], field: str) -> str:
    body = dict(payload)
    body.pop(field, None)
    return sha256_bytes(_json_bytes(body))


def _path_has_protected_semantics(path: Path) -> bool:
    parts = str(path.resolve()).replace("\\", "/").lower().split("/")
    return any(token in part for part in parts for token in _PROTECTED_PATH_TOKENS)


def _is_under(path: Path, root: Path) -> bool:
    path = path.resolve()
    root = root.resolve()
    return path == root or root in path.parents


def assert_isolated_staging_root(
    output_root: str | Path,
    *,
    source_roots: Iterable[str | Path] = (),
    forbidden_roots: Iterable[str | Path] = (),
) -> Path:
    output = Path(output_root).expanduser().resolve()
    if _path_has_protected_semantics(output):
        raise CompletionArtifactError("STAGING_ROOT_PROTECTED_PATH_REFUSED")
    for label, roots in (("SOURCE", source_roots), ("FORBIDDEN", forbidden_roots)):
        for value in roots:
            root = Path(value).expanduser().resolve()
            if _is_under(output, root) or _is_under(root, output):
                raise CompletionArtifactError(f"STAGING_ROOT_OVERLAPS_{label}_ROOT:{root}")
    return output


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_immutable_bytes(path: Path, payload: bytes) -> str:
    """Publish exactly once using exclusive hard-link creation."""

    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    expected = sha256_bytes(payload)
    if path.exists():
        if not path.is_file() or sha256_file(path) != expected:
            raise CompletionArtifactError(f"IMMUTABLE_ARTIFACT_CONFLICT:{path}")
        return expected

    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
            _fsync_directory(path.parent)
        except FileExistsError:
            if not path.is_file() or sha256_file(path) != expected:
                raise CompletionArtifactError(f"IMMUTABLE_ARTIFACT_CONFLICT:{path}")
        except OSError as exc:
            raise CompletionArtifactError(f"IMMUTABLE_EXCLUSIVE_PUBLISH_UNAVAILABLE:{path}") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass

    if not path.is_file() or sha256_file(path) != expected:
        raise CompletionArtifactError(f"IMMUTABLE_ARTIFACT_POST_PUBLISH_MISMATCH:{path}")
    return expected


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> str:
    return _atomic_immutable_bytes(path, _json_bytes(payload))


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False, compression=None, engine="pyarrow")
    return buffer.getvalue()


def _safe_audit_key_check(value: object, *, path: str = "safe_audit") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).strip().lower()
            if key_text not in {"outcome_blind", "protected_outcomes_accessed"} and any(
                token in key_text for token in _SAFE_AUDIT_FORBIDDEN_TOKENS
            ):
                raise CompletionArtifactError(f"SAFE_AUDIT_FORBIDDEN_METADATA:{path}.{key}")
            _safe_audit_key_check(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _safe_audit_key_check(child, path=f"{path}[{index}]")


def _safe_metadata_path(value: str | Path, *, label: str, root: Path | None = None) -> Path:
    path = Path(value).expanduser().resolve()
    if _path_has_protected_semantics(path):
        raise CompletionArtifactError(f"{label}_PROTECTED_PATH_REFUSED")
    if root is not None and not _is_under(path, root):
        raise CompletionArtifactError(f"{label}_OUTSIDE_EVIDENCE_ROOT")
    if not path.is_file():
        raise CompletionArtifactError(f"{label}_MISSING")
    return path


def _read_json_bytes(
    path: str | Path,
    *,
    expected_sha256: str | None,
    label: str,
    root: Path | None = None,
    inspect_keys: bool = True,
) -> tuple[Path, dict[str, Any], str]:
    safe = _safe_metadata_path(path, label=label, root=root)
    raw = safe.read_bytes()
    actual = sha256_bytes(raw)
    if expected_sha256 is not None and actual != str(expected_sha256).lower():
        raise CompletionArtifactError(f"{label}_SHA256_MISMATCH")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CompletionArtifactError(f"{label}_UNREADABLE") from exc
    if not isinstance(payload, dict):
        raise CompletionArtifactError(f"{label}_NOT_OBJECT")
    if inspect_keys:
        _safe_audit_key_check(payload, path=label.lower())
    return safe, payload, actual


def _safe_source_manifest(
    manifest_path: Path,
    *,
    source_root: Path,
    expected_session: str,
) -> tuple[dict[str, Any], Path, pd.DataFrame, str, str]:
    manifest_path = manifest_path.resolve()
    source_root = source_root.resolve()
    if not manifest_path.is_file() or not _is_under(manifest_path, source_root):
        raise CompletionArtifactError("SOURCE_MANIFEST_OUTSIDE_BOUNDARY")
    raw = manifest_path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CompletionArtifactError("SOURCE_MANIFEST_UNREADABLE") from exc
    if not isinstance(payload, dict):
        raise CompletionArtifactError("SOURCE_MANIFEST_NOT_OBJECT")
    try:
        _validate_production_manifest(payload)
    except Exception as exc:
        raise CompletionArtifactError(f"SOURCE_MANIFEST_INVALID:{exc}") from exc
    if str(payload.get("session_date") or "") != expected_session:
        raise CompletionArtifactError("SOURCE_SESSION_IDENTITY_MISMATCH")
    output = payload.get("output")
    artifact_value = output.get("artifact_path") if isinstance(output, Mapping) else None
    artifact = Path(str(artifact_value)).expanduser().resolve()
    if not artifact.is_file() or not _is_under(artifact, source_root):
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
    if sha256_file(artifact) != actual_sha or sha256_file(manifest_path) != sha256_bytes(raw):
        raise CompletionArtifactError("SOURCE_CHANGED_DURING_PROJECTION")
    return payload, artifact, frame, actual_sha, sha256_bytes(raw)


def _validate_projection_candidate(
    projected: pd.DataFrame,
    manifest_payload: Mapping[str, Any],
    *,
    final_artifact_path: Path,
    expected_session: str,
    artifact_sha: str,
    manifest_sha: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix="v4x1-score-candidate-") as directory:
        root = Path(directory)
        candidate_artifact = root / "score_artifact.parquet"
        candidate_manifest = root / "manifest.json"
        candidate_artifact.write_bytes(_parquet_bytes(projected))
        candidate_manifest.write_bytes(_json_bytes(manifest_payload))
        _validate_score_manifest(
            candidate_manifest,
            session_date=pd.Timestamp(expected_session),
            artifact_path=final_artifact_path,
            artifact_sha256=artifact_sha,
        )
        _load_score_artifact(
            candidate_artifact,
            session_date=pd.Timestamp(expected_session),
            session_index=0,
            artifact_sha256=artifact_sha,
            manifest_sha256=manifest_sha,
        )


def project_verified_score_session(
    source_manifest_path: str | Path,
    *,
    source_root: str | Path,
    output_root: str | Path,
    expected_session: str,
) -> dict[str, Any]:
    source_root_path = Path(source_root).expanduser().resolve()
    output_root_path = assert_isolated_staging_root(output_root, source_roots=(source_root_path,))
    source_manifest = Path(source_manifest_path).expanduser().resolve()
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
    artifact_path = (session_dir / "score_artifact.parquet").resolve()
    manifest_path = (session_dir / "manifest.json").resolve()
    artifact_bytes = _parquet_bytes(projected)
    artifact_sha = sha256_bytes(artifact_bytes)
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
            "safety_scope": "SCORE_SIDE_ONLY",
        },
    }
    manifest_bytes = _json_bytes(projected_manifest)
    manifest_sha = sha256_bytes(manifest_bytes)
    _validate_projection_candidate(
        projected,
        projected_manifest,
        final_artifact_path=artifact_path,
        expected_session=expected_session,
        artifact_sha=artifact_sha,
        manifest_sha=manifest_sha,
    )
    if sha256_file(source_artifact) != source_sha or sha256_file(source_manifest) != source_manifest_sha:
        raise CompletionArtifactError("SOURCE_CHANGED_BEFORE_PROJECTION_PUBLISH")
    _atomic_immutable_bytes(artifact_path, artifact_bytes)
    _atomic_immutable_bytes(manifest_path, manifest_bytes)
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
    schedule = [str(value) for value in official_sessions]
    index_by_date = {value: index + 1 for index, value in enumerate(schedule)}
    rows: list[dict[str, Any]] = []
    for position, item in enumerate(sorted(projections, key=lambda value: str(value["session_date"])), start=1):
        session = str(item["session_date"])
        if session not in index_by_date:
            raise CompletionArtifactError("ADMITTED_SESSION_NOT_IN_OFFICIAL_CALENDAR")
        artifact = Path(str(item["projected_artifact_path"])).resolve()
        manifest = Path(str(item["projected_manifest_path"])).resolve()
        if sha256_file(artifact) != str(item["projected_artifact_sha256"]).lower():
            raise CompletionArtifactError("ADMITTED_PROJECTED_ARTIFACT_DRIFT")
        if sha256_file(manifest) != str(item["projected_manifest_sha256"]).lower():
            raise CompletionArtifactError("ADMITTED_PROJECTED_MANIFEST_DRIFT")
        rows.append(
            {
                "forward_position": position,
                "session_index": index_by_date[session],
                "session_date": session,
                "score_artifact_path": str(artifact),
                "score_artifact_sha256": str(item["projected_artifact_sha256"]).lower(),
                "score_manifest_path": str(manifest),
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
    gate_identity = gate_shape_inventory_sha256(inventory) if not inventory.empty else "NOT_AVAILABLE"
    root = Path(output_root).expanduser().resolve()
    inventory_path = root / "admitted_inventory.csv"
    inventory_sha = _atomic_immutable_bytes(
        inventory_path, inventory.to_csv(index=False, lineterminator="\n").encode("utf-8")
    )
    manifest = {
        "schema_version": INVENTORY_SCHEMA,
        "status": partial["status"],
        "inventory_kind": "PARTIAL_ADMITTED_GATE_SHAPE",
        "session_count": len(inventory),
        "required_session_count": 100,
        "inventory_path": str(inventory_path.resolve()),
        "inventory_sha256": inventory_sha,
        "partial_admitted_gate_shape_sha256": gate_identity,
        "canonical_admitted_gate_inventory_sha256": "NOT_AVAILABLE",
        "source_projection_count": len(rows),
        "outcome_scope": "NO_TARGETS_NO_OUTCOMES_NO_LABELS",
    }
    manifest_path = root / "admitted_inventory_manifest.json"
    manifest_sha = _atomic_json(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path.resolve())
    manifest["manifest_sha256"] = manifest_sha
    return inventory, manifest


def finalize_canonical_admitted_inventory(
    inventory: pd.DataFrame,
    *,
    output_root: str | Path,
) -> dict[str, Any]:
    root = Path(output_root).expanduser().resolve()
    normalized, _score_frame, identity = validate_session_inventory(inventory, fixture_root=root)
    for row in normalized.itertuples(index=False):
        if sha256_file(row.score_artifact_path) != str(row.score_artifact_sha256).lower():
            raise CompletionArtifactError("CANONICAL_INVENTORY_CHILD_ARTIFACT_DRIFT")
        if sha256_file(row.score_manifest_path) != str(row.score_manifest_sha256).lower():
            raise CompletionArtifactError("CANONICAL_INVENTORY_CHILD_MANIFEST_DRIFT")
    normalized2, _score_frame2, identity2 = validate_session_inventory(normalized, fixture_root=root)
    if identity2 != identity:
        raise CompletionArtifactError("CANONICAL_INVENTORY_IDENTITY_DRIFT")
    path = root / "canonical_admitted_inventory.csv"
    raw = normalized2.assign(session_date=normalized2["session_date"].dt.date.astype(str)).to_csv(
        index=False, lineterminator="\n"
    ).encode("utf-8")
    inventory_sha = _atomic_immutable_bytes(path, raw)
    manifest_payload = {
        "schema_version": CANONICAL_INVENTORY_SCHEMA,
        "status": "CANONICAL_ADMITTED_100_OF_100",
        "session_count": 100,
        "required_session_count": 100,
        "inventory_path": str(path.resolve()),
        "inventory_file_sha256": inventory_sha,
        "canonical_admitted_gate_inventory_sha256": identity,
    }
    manifest_path = root / "canonical_admitted_inventory_manifest.json"
    manifest_sha = _atomic_json(manifest_path, manifest_payload)
    return {
        **manifest_payload,
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": manifest_sha,
        "validated_inventory": normalized2,
    }


def reconcile_runtime_counter(
    counter_status_path: str | Path,
    inventory: pd.DataFrame,
    *,
    attestation_path: str | Path | None = None,
    canonical_inventory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    status_path = Path(counter_status_path).expanduser().resolve()
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        counter = payload["x1_counter"]
        completed = int(counter["completed"])
        target = int(counter["target"])
        remaining = int(counter["remaining"])
        sessions = [str(value) for value in counter["sessions"]]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise CompletionArtifactError("COUNTER_STATUS_UNREADABLE") from exc
    if target != 100:
        raise CompletionArtifactError("COUNTER_TARGET_NOT_100")
    observed = inventory["session_date"].astype(str).tolist()
    if completed != len(sessions) or remaining != 100 - completed:
        raise CompletionArtifactError("COUNTER_STATUS_INTERNAL_COUNTS_INVALID")
    if sessions != sorted(set(sessions)) or sessions != observed:
        raise CompletionArtifactError("COUNTER_SESSIONS_DO_NOT_MATCH_ADMITTED_INVENTORY")
    result: dict[str, Any] = {
        "status": "ACCUMULATING" if completed < 100 else "PENDING_CANONICAL_INVENTORY",
        "completed": completed,
        "target": target,
        "remaining": remaining,
        "sessions": sessions,
        "session_inventory_sha256": "NOT_AVAILABLE",
        "runtime_counter_changed": False,
        "attestation_path": None,
        "attestation_sha256": None,
    }
    if completed < 100:
        return result
    if completed != 100 or len(inventory) != 100:
        raise CompletionArtifactError("COUNTER_NOT_EXACTLY_100")
    if canonical_inventory is None:
        return result
    canonical_sha = str(canonical_inventory.get("canonical_admitted_gate_inventory_sha256") or "").lower()
    if len(canonical_sha) != 64:
        raise CompletionArtifactError("COUNTER_CANONICAL_INVENTORY_IDENTITY_MISSING")
    root = Path(str(canonical_inventory.get("inventory_path") or "")).resolve().parent
    _normalized, _scores, current_sha = validate_session_inventory(inventory, fixture_root=root)
    if current_sha != canonical_sha:
        raise CompletionArtifactError("COUNTER_CANONICAL_INVENTORY_IDENTITY_STALE")
    result["session_inventory_sha256"] = canonical_sha
    if attestation_path is None:
        result["status"] = "READY_FOR_ATTESTATION"
        return result
    path = Path(attestation_path).expanduser().resolve()
    attestation = {
        "schema_version": COUNTER_ATTESTATION_SCHEMA,
        "current": 100,
        "target": 100,
        "session_inventory_sha256": canonical_sha,
    }
    sha = _atomic_json(path, attestation)
    result.update({"status": "ATTESTED", "attestation_path": str(path), "attestation_sha256": sha})
    return result


def build_prior_access_audit(
    canonical_output_root: str | Path | None,
    *,
    output_path: str | Path | None = None,
    canonical_root_id: str | None = None,
) -> dict[str, Any]:
    if canonical_output_root is None or canonical_root_id != CANONICAL_REAL_ACCESS_ROOT_ID:
        return {
            "status": "NOT_AVAILABLE",
            "reason": "PRIOR_ACCESS_AUDIT_NOT_AVAILABLE_CANONICAL_ROOT_UNSET",
            "protected_outcomes_accessed": False,
        }
    root = Path(canonical_output_root).expanduser().resolve()
    inspection = inspect_persisted_access_status(root)
    status = str(inspection.get("status") or "")
    if status == "PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT":
        if output_path is None:
            raise CompletionArtifactError("PRIOR_ACCESS_OUTPUT_REQUIRED")
        payload = {
            "schema_version": ACCESS_AUDIT_SCHEMA,
            "review_complete": True,
            "unauthorized_access_known": False,
            "prior_access_marker_exists": False,
            "canonical_root_id": CANONICAL_REAL_ACCESS_ROOT_ID,
            "canonical_output_root": str(root),
            "source_status": status,
        }
        sha = _atomic_json(Path(output_path).expanduser().resolve(), payload)
        return {"status": "READY", "path": str(Path(output_path).resolve()), "sha256": sha, **payload}
    if status == "SYNTHETIC_REHEARSAL_COMPLETE":
        return {
            "status": "PROVENANCE_INVALID",
            "reason": "SYNTHETIC_STATE_CONTAMINATES_REAL_ACCESS_ROOT",
            **inspection,
        }
    if status in {"REAL_ACCESS_ALREADY_COMPLETED", "INTEGRITY_FAILURE", "ORPHAN_OR_INTERRUPTED_STATE"}:
        return {"status": "PROVENANCE_INVALID", "reason": f"PERSISTED_ACCESS_STATUS:{status}", **inspection}
    return {
        "status": "NOT_AVAILABLE",
        "reason": f"PRIOR_ACCESS_AUDIT_UNHANDLED_STATUS:{status}",
        "protected_outcomes_accessed": False,
    }


def _stage_by_name(ledger: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    stages = ledger.get("stages")
    if not isinstance(stages, list):
        raise CompletionArtifactError("SESSION_AUDIT_STAGES_MISSING")
    result: dict[str, Mapping[str, Any]] = {}
    for item in stages:
        if not isinstance(item, Mapping) or not isinstance(item.get("stage"), str):
            raise CompletionArtifactError("SESSION_AUDIT_STAGE_MALFORMED")
        name = str(item["stage"])
        if name in result:
            raise CompletionArtifactError("SESSION_AUDIT_DUPLICATE_STAGE")
        result[name] = item
    return result


def _verify_ledger_guards(ledger: Mapping[str, Any]) -> None:
    guards = ledger.get("guards")
    if not isinstance(guards, Mapping):
        raise CompletionArtifactError("SESSION_AUDIT_GUARDS_MISSING")
    for key in (
        "protected_outcomes_accessed",
        "real_protected_loader_called",
        "real_outcome_access_marker_written",
        "provider_capture_triggered",
        "model_changed",
        "forward_counter_changed",
    ):
        if guards.get(key) is not False:
            raise CompletionArtifactError(f"SESSION_AUDIT_GUARD_NOT_FALSE:{key}")


def _verify_paperstate_snapshot(
    path_value: str,
    sha_value: str,
    *,
    expected_session: str,
    expected_parent: tuple[str, str, str],
    evidence_root: Path,
) -> tuple[Path, str, tuple[str, str, str]]:
    path, payload, actual = _read_json_bytes(
        path_value, expected_sha256=sha_value, label="PAPERSTATE", root=evidence_root, inspect_keys=False
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
    parent_path = str(previous.get("path") or "")
    parent_sha = str(previous.get("sha256") or "").lower()
    parent_date = str(previous.get("session_date") or "")
    if not parent_path or len(parent_sha) != 64 or not parent_date:
        raise CompletionArtifactError("PAPERSTATE_PARENT_REFERENCE_INVALID")
    if parent_date >= expected_session:
        raise CompletionArtifactError("PAPERSTATE_PARENT_NOT_PRIOR")
    parent = _safe_metadata_path(parent_path, label="PAPERSTATE_PARENT", root=evidence_root)
    if sha256_file(parent) != parent_sha:
        raise CompletionArtifactError("PAPERSTATE_PARENT_SHA256_MISMATCH")
    expected_path, expected_sha, expected_date = expected_parent
    if parent != Path(expected_path).resolve() or parent_sha != expected_sha.lower() or parent_date != expected_date:
        raise CompletionArtifactError("PAPERSTATE_PARENT_CHAIN_MISMATCH")
    return path, actual, (str(path), actual, expected_session)


def _verify_terminal_execution(
    stage: Mapping[str, Any],
    *,
    session: str,
    paper_path: Path,
    paper_sha: str,
    evidence_root: Path,
) -> None:
    path = stage.get("artifact_path")
    sha = stage.get("artifact_sha256")
    if not isinstance(path, str) or not isinstance(sha, str):
        raise CompletionArtifactError("SESSION_AUDIT_EXECUTION_REFERENCE_MISSING")
    _, payload, _ = _read_json_bytes(path, expected_sha256=sha, label="EXECUTION", root=evidence_root, inspect_keys=False)
    if payload.get("schema_version") != "idx_trade_e2e_paper_execution_v1" or payload.get("status") != "EXECUTION_COMPLETE":
        raise CompletionArtifactError("SESSION_AUDIT_EXECUTION_SCHEMA_OR_STATUS_INVALID")
    if payload.get("execution_session_date") != session:
        raise CompletionArtifactError("SESSION_AUDIT_EXECUTION_SESSION_MISMATCH")
    runtime_path = Path(str(payload.get("runtime_snapshot_path") or "")).resolve()
    runtime_sha = str(payload.get("runtime_snapshot_sha256") or "").lower()
    if runtime_path != paper_path.resolve() or runtime_sha != paper_sha.lower():
        raise CompletionArtifactError("SESSION_AUDIT_EXECUTION_PAPERSTATE_MISMATCH")


def _verify_terminal_missed(
    stage: Mapping[str, Any],
    *,
    session: str,
    paper_path: Path,
    paper_sha: str,
    expected_parent: tuple[str, str, str],
    evidence_root: Path,
) -> None:
    path = stage.get("artifact_path")
    sha = stage.get("artifact_sha256")
    if not isinstance(path, str) or not isinstance(sha, str):
        raise CompletionArtifactError("SESSION_AUDIT_MISSED_REFERENCE_MISSING")
    _, payload, _ = _read_json_bytes(
        path, expected_sha256=sha, label="MISSED_EXECUTION", root=evidence_root, inspect_keys=False
    )
    if payload.get("schema_version") != "idx_trade_e2e_paper_missed_execution_v1" or payload.get("status") != "MISSED_EXECUTION_NO_CERTIFIED_OPEN":
        raise CompletionArtifactError("SESSION_AUDIT_MISSED_SCHEMA_OR_STATUS_INVALID")
    if payload.get("execution_session_date", payload.get("session_date")) != session:
        raise CompletionArtifactError("SESSION_AUDIT_MISSED_SESSION_MISMATCH")
    runtime_path = Path(str(payload.get("runtime_snapshot_path") or payload.get("resulting_runtime_snapshot_path") or "")).resolve()
    runtime_sha = str(payload.get("runtime_snapshot_sha256") or payload.get("resulting_runtime_snapshot_sha256") or "").lower()
    if runtime_path != paper_path.resolve() or runtime_sha != paper_sha.lower():
        raise CompletionArtifactError("SESSION_AUDIT_MISSED_PAPERSTATE_MISMATCH")
    prior_path = Path(str(payload.get("prior_runtime_snapshot_path") or "")).resolve()
    prior_sha = str(payload.get("prior_runtime_snapshot_sha256") or "").lower()
    exp_path, exp_sha, _exp_date = expected_parent
    if prior_path != Path(exp_path).resolve() or prior_sha != exp_sha.lower():
        raise CompletionArtifactError("SESSION_AUDIT_MISSED_PRIOR_SNAPSHOT_MISMATCH")


def produce_paper_attestation_from_safe_audit(
    source_path: str | Path,
    *,
    output_path: str | Path,
    expected_sessions: Iterable[str],
    predecessor_session_date: str,
    evidence_root: str | Path | None = None,
) -> dict[str, Any]:
    bridge_path, bridge, bridge_sha = _read_json_bytes(
        source_path, expected_sha256=None, label="SESSION_AUDIT_BRIDGE", inspect_keys=False
    )
    root = Path(evidence_root).expanduser().resolve() if evidence_root is not None else bridge_path.parent
    if not _is_under(bridge_path, root):
        raise CompletionArtifactError("SESSION_AUDIT_BRIDGE_OUTSIDE_EVIDENCE_ROOT")
    if bridge.get("schema_version") != SAFE_SESSION_AUDIT_SCHEMA or bridge.get("outcome_blind") is not True:
        raise CompletionArtifactError("SESSION_AUDIT_BRIDGE_SCHEMA_OR_SCOPE_INVALID")
    expected = [str(value) for value in expected_sessions]
    if expected != sorted(set(expected)) or not expected:
        raise CompletionArtifactError("EXPECTED_SESSION_BLOCK_INVALID")
    if str(bridge.get("predecessor_session_date") or "") != str(predecessor_session_date):
        raise CompletionArtifactError("SESSION_AUDIT_PREDECESSOR_DATE_MISMATCH")
    predecessor_path = bridge.get("predecessor_paperstate_path")
    predecessor_sha = str(bridge.get("predecessor_paperstate_sha256") or "").lower()
    if not isinstance(predecessor_path, str) or len(predecessor_sha) != 64:
        raise CompletionArtifactError("SESSION_AUDIT_PREDECESSOR_REFERENCE_MISSING")
    predecessor = _safe_metadata_path(predecessor_path, label="PAPERSTATE_PREDECESSOR", root=root)
    if sha256_file(predecessor) != predecessor_sha:
        raise CompletionArtifactError("SESSION_AUDIT_PREDECESSOR_SHA256_MISMATCH")
    ledger_refs = bridge.get("session_ledgers")
    if not isinstance(ledger_refs, list) or len(ledger_refs) != len(expected):
        raise CompletionArtifactError("SESSION_AUDIT_LEDGER_COVERAGE_MISMATCH")

    parent: tuple[str, str, str] = (str(predecessor), predecessor_sha, predecessor_session_date)
    transitions: list[dict[str, Any]] = []
    missed_count = 0
    source_hashes: list[str] = []
    for position, (session, reference) in enumerate(zip(expected, ledger_refs), start=1):
        if not isinstance(reference, Mapping) or reference.get("session_date") != session or reference.get("forward_position") != position:
            raise CompletionArtifactError("SESSION_AUDIT_LEDGER_REFERENCE_INVALID")
        ledger_path = reference.get("audit_path")
        ledger_sha = str(reference.get("audit_sha256") or "").lower()
        if not isinstance(ledger_path, str) or len(ledger_sha) != 64:
            raise CompletionArtifactError("SESSION_AUDIT_LEDGER_IDENTITY_MISSING")
        _, ledger, actual_ledger_sha = _read_json_bytes(
            ledger_path, expected_sha256=ledger_sha, label="SESSION_AUDIT_LEDGER", root=root, inspect_keys=False
        )
        source_hashes.append(actual_ledger_sha)
        if ledger.get("schema") != SOURCE_SESSION_AUDIT_SCHEMA:
            raise CompletionArtifactError("SESSION_AUDIT_SOURCE_SCHEMA_MISMATCH")
        if ledger.get("execution_session_date") != session or ledger.get("ledger_anchor") != "execution_session_date":
            raise CompletionArtifactError("SESSION_AUDIT_SOURCE_SESSION_MISMATCH")
        _verify_ledger_guards(ledger)
        overall = str(ledger.get("overall_status") or "")
        if overall not in _SAFE_LEDGER_OVERALL:
            raise CompletionArtifactError(f"SESSION_AUDIT_SOURCE_NOT_ADMISSIBLE:{overall}")
        stages = _stage_by_name(ledger)
        paper_stage = stages.get("paperstate_continuity")
        execution_stage = stages.get("paper_execution")
        if not paper_stage or paper_stage.get("status") != "PASS":
            raise CompletionArtifactError("SESSION_AUDIT_PAPERSTATE_STAGE_NOT_PASS")
        paper_path_value = paper_stage.get("artifact_path")
        paper_sha_value = paper_stage.get("artifact_sha256")
        if not isinstance(paper_path_value, str) or not isinstance(paper_sha_value, str):
            raise CompletionArtifactError("SESSION_AUDIT_PAPERSTATE_REFERENCE_MISSING")
        paper_path, paper_sha, current_parent = _verify_paperstate_snapshot(
            paper_path_value,
            paper_sha_value,
            expected_session=session,
            expected_parent=parent,
            evidence_root=root,
        )
        if overall == "SESSION_MISSED_EXECUTION_NO_CERTIFIED_OPEN":
            if not execution_stage or execution_stage.get("status") != "LEGITIMATE_NOOP":
                raise CompletionArtifactError("SESSION_AUDIT_MISSED_TERMINAL_STAGE_INVALID")
            open_stage = stages.get("official_open_evidence")
            if not open_stage or open_stage.get("status") != "PENDING_EXPECTED":
                raise CompletionArtifactError("SESSION_AUDIT_MISSED_OPEN_CONFLICT")
            observed = execution_stage.get("observed")
            if not isinstance(observed, Mapping) or observed.get("continuity_transition") != "MISSED_EXECUTION_NO_CERTIFIED_OPEN":
                raise CompletionArtifactError("SESSION_AUDIT_MISSED_CONTINUITY_NOT_CERTIFIED")
            _verify_terminal_missed(
                execution_stage,
                session=session,
                paper_path=paper_path,
                paper_sha=paper_sha,
                expected_parent=parent,
                evidence_root=root,
            )
            missed_count += 1
        elif overall == "SESSION_HEALTHY":
            if not execution_stage or execution_stage.get("status") != "PASS":
                raise CompletionArtifactError("SESSION_AUDIT_EXECUTION_STAGE_NOT_PASS")
            _verify_terminal_execution(
                execution_stage,
                session=session,
                paper_path=paper_path,
                paper_sha=paper_sha,
                evidence_root=root,
            )
        else:
            if execution_stage and execution_stage.get("status") not in {"LEGITIMATE_NOOP", "NOT_APPLICABLE", "PASS"}:
                raise CompletionArtifactError("SESSION_AUDIT_NOOP_TERMINAL_STAGE_INVALID")
            if execution_stage and execution_stage.get("status") == "PASS":
                _verify_terminal_execution(
                    execution_stage,
                    session=session,
                    paper_path=paper_path,
                    paper_sha=paper_sha,
                    evidence_root=root,
                )
        transitions.append({"session_date": session, "forward_position": position})
        parent = current_parent

    paper_payload = {
        "schema_version": PAPER_ATTESTATION_SCHEMA,
        "predecessor_session_date": predecessor_session_date,
        "session_count": len(expected),
        "first_session_date": expected[0],
        "last_session_date": expected[-1],
        "continuity_valid": True,
        "execution_provenance_valid": missed_count == 0,
        "preclassified_invalidity": missed_count > 0,
        "invalidity_reason": "MISSED_EXECUTION_NO_CERTIFIED_OPEN" if missed_count else "",
        "execution_material_drag": False,
        "material_drag_rule_id": "SESSION_AUDIT_METADATA_ONLY_NO_ECONOMIC_METRICS",
        "transitions": transitions,
        "source_session_audit_bridge_path": str(bridge_path),
        "source_session_audit_bridge_sha256": bridge_sha,
        "source_session_audit_ledger_sha256": source_hashes,
        "missed_execution_count": missed_count,
        "outcome_scope": "NO_NAV_NO_RETURNS_NO_PNL_NO_TARGET_VALUES",
    }
    output = Path(output_path).expanduser().resolve()
    paper_sha = _atomic_json(output, paper_payload)
    return {
        "status": "READY_FOR_FINAL_GATE_REVALIDATION",
        "paper_attestation_path": str(output),
        "paper_attestation_sha256": paper_sha,
        "session_count": len(expected),
        "missed_execution_count": missed_count,
    }


def build_local_composite_benchmark(
    data_root: str | Path,
    *,
    sessions: Iterable[str],
    predecessor_session_date: str,
    output_root: str | Path,
) -> dict[str, Any]:
    root = Path(data_root).expanduser().resolve()
    output = Path(output_root).expanduser().resolve()
    prospective = [str(value) for value in sessions]
    requested = [str(predecessor_session_date), *prospective]
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
        source_name = str(row["source"])
        if not source_name.upper().startswith("IDX"):
            raise CompletionArtifactError(f"BENCHMARK_SOURCE_NOT_IDX:{session}")
        close = pd.to_numeric(pd.Series([row["close"]]), errors="coerce").iloc[0]
        if pd.isna(close) or not float(close) > 0:
            raise CompletionArtifactError(f"BENCHMARK_CLOSE_INVALID:{session}")
        rows.append(
            {
                "session_date": session,
                "benchmark_close": float(close),
                "source": source_name,
                "source_ref": str(row["source_ref"]),
                "source_sha256": str(row["source_sha256"]),
                "source_csv_sha256": sha256_file(source_file),
                "source_retrieved_at": str(row["source_retrieved_at"]),
            }
        )
    complete = not missing
    final_boundary = len(prospective) == 100
    result: dict[str, Any] = {
        "status": (
            "PARTIAL_NOT_GATE_READY"
            if missing
            else "READY_FOR_FINAL_GATE_REVALIDATION"
            if final_boundary
            else "PARTIAL_BOUNDARY_COMPLETE_NOT_FINAL"
        ),
        "benchmark_identity": "IDX_OFFICIAL_INDEX_SUMMARY_COMPOSITE",
        "required_boundary_dates": requested,
        "available_boundary_dates": [row["session_date"] for row in rows],
        "missing_boundary_dates": missing,
        "requested_session_count": len(requested),
        "prospective_session_count": len(prospective),
        "session_count": len(rows),
        "gate_ready": bool(complete and final_boundary),
        "publication_time_claim": "NONE",
        "rows": rows,
    }
    if not result["gate_ready"]:
        return result
    artifact = output / "benchmark.parquet"
    frame = pd.DataFrame(rows)[["session_date", "benchmark_close"]]
    artifact_bytes = _parquet_bytes(frame)
    artifact_sha = sha256_bytes(artifact_bytes)
    attestation = output / "benchmark_attestation.json"
    attestation_payload = {
        "schema_version": BENCHMARK_ATTESTATION_SCHEMA,
        "status": "PINNED",
        "benchmark_identity": "IDX_OFFICIAL_INDEX_SUMMARY_COMPOSITE",
        "artifact_path": str(artifact.resolve()),
        "artifact_sha256": artifact_sha,
        "source_rows": rows,
        "publication_time_claim": "NONE",
    }
    _atomic_immutable_bytes(artifact, artifact_bytes)
    attestation_sha = _atomic_json(attestation, attestation_payload)
    result.update(
        {
            "artifact_path": str(artifact.resolve()),
            "artifact_sha256": artifact_sha,
            "attestation_path": str(attestation.resolve()),
            "attestation_sha256": attestation_sha,
        }
    )
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
    root = Path(fixture_root).expanduser().resolve()
    if len(inventory) != 100:
        raise CompletionArtifactError("PREFLIGHT_BUNDLE_REQUIRES_EXACT_100_INVENTORY")
    _, _, inventory_identity = validate_session_inventory(inventory, fixture_root=root)
    inventory_file = root / "canonical_admitted_inventory.csv"
    if not inventory_file.is_file():
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
        if not file_path.is_file() or not _is_under(file_path, root):
            raise CompletionArtifactError(f"PREFLIGHT_{label.upper()}_OUTSIDE_FIXTURE")
        if sha256_file(file_path) != str(expected_sha).lower():
            raise CompletionArtifactError(f"PREFLIGHT_{label.upper()}_SHA_MISMATCH")
    payload = {
        "schema_version": "v4_x1_prospective_preflight_bundle_v1",
        "fixture_root": str(root),
        "session_inventory_path": str(inventory_file.resolve()),
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
        "inventory_identity": inventory_identity,
        "scope": "SYNTHETIC_REHEARSAL_ONLY",
    }
    bundle_path = Path(path).expanduser().resolve()
    bundle_sha = _atomic_json(bundle_path, payload)
    return str(bundle_path), bundle_sha


def write_synthetic_score_session(
    root: str | Path,
    session_date: str,
    *,
    row_count: int = 3,
    session_index: int = 1,
    production_shape: bool = False,
) -> dict[str, Any]:
    tickers = [f"SYN{index:03d}" for index in range(row_count)]
    base = {
        "date": [session_date] * row_count,
        "ticker": tickers,
        "alpha_consensus": [1.0 - index / max(row_count, 1) for index in range(row_count)],
    }
    if production_shape:
        frame = pd.DataFrame(
            {
                "ticker": tickers,
                "date": [session_date] * row_count,
                "raw_control_h5": [0.1 + index / 1000 for index in range(row_count)],
                "alpha_control_h5": [0.2 + index / 1000 for index in range(row_count)],
                "raw_control_h10": [0.3 + index / 1000 for index in range(row_count)],
                "alpha_control_h10": [0.4 + index / 1000 for index in range(row_count)],
                "alpha_control_consensus": [0.3 + index / 1000 for index in range(row_count)],
                "raw_challenger_h5": [0.5 + index / 1000 for index in range(row_count)],
                "alpha_h5": [0.6 + index / 1000 for index in range(row_count)],
                "raw_challenger_h10": [0.7 + index / 1000 for index in range(row_count)],
                "alpha_h10": [0.8 + index / 1000 for index in range(row_count)],
                "alpha_consensus": base["alpha_consensus"],
                "rank_consensus": list(range(1, row_count + 1)),
                "rank_control_consensus": list(range(row_count, 0, -1)),
            }
        )
    else:
        frame = pd.DataFrame(base)
    root_path = Path(root).expanduser().resolve()
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
        "rows": row_count,
        "output": {
            "artifact_path": str(artifact.resolve()),
            "artifact_sha256": artifact_sha,
            "columns": list(frame.columns),
        },
        "guards": {
            name: False
            for name in (
                "historical_prediction_generated",
                "model_refit",
                "model_retuned",
                "protected_outcome_accessed",
                "provider_calls",
                "realized_forward_outcome_loaded",
                "science_changed",
            )
        },
    }
    manifest_sha = _atomic_json(manifest, payload)
    return {
        "session_date": session_date,
        "session_index": session_index,
        "projected_artifact_path": str(artifact.resolve()),
        "projected_artifact_sha256": artifact_sha,
        "projected_manifest_path": str(manifest.resolve()),
        "projected_manifest_sha256": manifest_sha,
    }


def write_synthetic_attestations(
    root: str | Path,
    *,
    inventory: pd.DataFrame,
    predecessor_session_date: str,
    contract_path: str | Path | None = None,
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    root_path.mkdir(parents=True, exist_ok=True)
    first = str(inventory["session_date"].iloc[0])[:10]
    last = str(inventory["session_date"].iloc[-1])[:10]
    contract_target: dict[str, Any]
    if contract_path is not None:
        contract_payload = json.loads(Path(contract_path).read_text(encoding="utf-8"))
        candidate = contract_payload.get("target_identity")
        if not isinstance(candidate, dict):
            raise CompletionArtifactError("SYNTHETIC_CONTRACT_TARGET_MISSING")
        contract_target = dict(candidate)
    else:
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
    target_identity_sha = sha256_bytes(_json_bytes(contract_target))
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
        "source_manifest_path": str(source_manifest.resolve()),
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
    return {"target": (str(target_path.resolve()), target_sha)}


__all__ = [
    "ACCESS_AUDIT_SCHEMA",
    "BENCHMARK_ATTESTATION_SCHEMA",
    "CANONICAL_REAL_ACCESS_ROOT_ID",
    "COMPLETION_SCHEMA",
    "CompletionArtifactError",
    "PAPER_ATTESTATION_SCHEMA",
    "PROJECTION_RULE_ID",
    "SAFE_SESSION_AUDIT_SCHEMA",
    "assert_isolated_staging_root",
    "build_admitted_inventory",
    "build_local_composite_benchmark",
    "build_prior_access_audit",
    "finalize_canonical_admitted_inventory",
    "gate_shape_inventory_sha256",
    "project_verified_score_session",
    "produce_paper_attestation_from_safe_audit",
    "reconcile_runtime_counter",
    "sha256_bytes",
    "write_preflight_bundle",
    "write_synthetic_attestations",
    "write_synthetic_score_session",
]
