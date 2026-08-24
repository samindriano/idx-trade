from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .prospective_evaluation_v1 import (
    MODEL_FINGERPRINT,
    MODEL_GENERATION,
    MODEL_NAME,
    PROTOCOL_COMMIT,
    PROTOCOL_STATUS,
    ProspectiveEvaluationBlocked,
    alpha_verdict,
    economic_verdict,
    evaluate_alpha_metrics,
    evaluate_benchmark,
    evaluate_pending_orders,
    evaluate_portfolio_metrics,
    evaluate_turnover,
    execution_verdict,
    overall_verdict,
    validate_alpha_session_alignment,
    validate_exclusion_ledger,
)
from .provenance import sha256_file


ACCESS_GATE_SCHEMA = "v4_x1_prospective_protected_access_gate_v1"
REQUIRED_SESSION_COUNT = 100

# These pins were fixed before this access-gate implementation existed.
PROTOCOL_GIT_BLOB_SHA1 = "f76af5733db3c6a2c7a99b1e80268004ece1e616"
EVALUATOR_IMPLEMENTATION_COMMIT = "0bf9ff5bc4b3ef6639d48823c75437f0359c6bc7"
EVALUATOR_GIT_BLOB_SHA1 = "ce7a6d356b0b1ab52277c50411fdfb86ac59ad4c"

MODE_SYNTHETIC_REHEARSAL = "SYNTHETIC_REHEARSAL"
MODE_PROTECTED_PROSPECTIVE = "PROTECTED_PROSPECTIVE"
ALLOWED_MODES = frozenset({MODE_SYNTHETIC_REHEARSAL, MODE_PROTECTED_PROSPECTIVE})

REAL_ACCESS_MARKER = "V4_X1_PROTECTED_OUTCOME_ACCESS_STARTED"
REHEARSAL_ACCESS_MARKER = "V4_X1_PROTECTED_OUTCOME_REHEARSAL_STARTED"

PREACCESS_FILENAME = "pre_outcome_access_attestation.json"
MARKER_FILENAME = "outcome_access_marker.json"
RESULT_FILENAME = "prospective_evaluation_result.json"
FINAL_MANIFEST_FILENAME = "prospective_evaluation_result_manifest.json"
FAILURE_FILENAME = "post_access_failure.json"

_SCORE_MANIFEST_FALSE_GUARDS = (
    "provider_calls",
    "protected_outcome_accessed",
    "realized_forward_outcome_loaded",
    "historical_prediction_generated",
    "model_refit",
    "model_retuned",
    "science_changed",
)


class ProspectiveAccessGateBlocked(RuntimeError):
    """Raised before or after access whenever the precommitted gate cannot proceed safely."""


@dataclass(frozen=True)
class ProtectedEvaluationBundle:
    """Data returned only after the access marker has been durably written.

    The protected loader is intentionally injected by the caller.  This module
    contains no provider discovery, vault path discovery, network call, or
    automatic unlock shortcut.
    """

    target_frame: pd.DataFrame
    ledger: pd.DataFrame
    metadata: Mapping[str, Any]
    nav_frame: pd.DataFrame | None = None
    execution_frame: pd.DataFrame | None = None
    order_frame: pd.DataFrame | None = None


@dataclass(frozen=True)
class _PreparedAccess:
    session_inventory: pd.DataFrame
    expected_sessions: pd.DataFrame
    score_frame: pd.DataFrame
    inventory_sha256: str
    counter: dict[str, Any]
    target: dict[str, Any]
    paper: dict[str, Any]
    benchmark: dict[str, Any]
    access_audit: dict[str, Any]
    benchmark_frame: pd.DataFrame | None
    protocol_blob_sha1: str
    evaluator_blob_sha1: str


def git_blob_sha1_file(path: str | Path) -> str:
    payload = Path(path).read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def _json_value(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return [_json_value(record) for record in value.to_dict(orient="records")]
    if isinstance(value, pd.Series):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        _json_value(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _canonical_hash(payload: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(_json_value(dict(payload)), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    try:
        with path.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ProspectiveAccessGateBlocked(f"immutable output already exists: {path.name}") from exc


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProspectiveAccessGateBlocked(f"malformed {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ProspectiveAccessGateBlocked(f"{label} must be a JSON object: {path}")
    return payload


def _normalize_dates(values: pd.Series, *, label: str) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
    if dates.isna().any():
        raise ProspectiveAccessGateBlocked(f"{label} contains invalid dates")
    return dates


def _require_columns(frame: pd.DataFrame, required: set[str], *, label: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ProspectiveAccessGateBlocked(f"{label} missing columns: {missing}")


def _resolve_declared_path(value: Any, *, base_dir: Path | None = None) -> Path:
    path = Path(str(value or "")).expanduser()
    if not str(path):
        raise ProspectiveAccessGateBlocked("empty artifact path")
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path.resolve()


def _require_under_root(path: Path, root: Path | None, *, label: str) -> None:
    if root is None:
        return
    resolved_root = root.resolve()
    if path != resolved_root and resolved_root not in path.parents:
        raise ProspectiveAccessGateBlocked(f"rehearsal {label} escapes fixture root")


def _verified_path(
    path_value: Any,
    expected_sha256: Any,
    *,
    label: str,
    fixture_root: Path | None,
    base_dir: Path | None = None,
) -> Path:
    path = _resolve_declared_path(path_value, base_dir=base_dir)
    _require_under_root(path, fixture_root, label=label)
    expected = str(expected_sha256 or "").strip().lower()
    if len(expected) != 64:
        raise ProspectiveAccessGateBlocked(f"invalid {label} sha256 declaration")
    if not path.is_file():
        raise ProspectiveAccessGateBlocked(f"missing {label}: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ProspectiveAccessGateBlocked(f"{label} sha256 mismatch")
    return path


def _read_table(path: Path, *, label: str) -> pd.DataFrame:
    suffix = path.suffix.lower()
    try:
        if suffix in {".parquet", ".pq"}:
            return pd.read_parquet(path)
        if suffix == ".csv":
            return pd.read_csv(path)
    except Exception as exc:  # parser details are retained as chained evidence, not silently coerced
        raise ProspectiveAccessGateBlocked(f"failed to read {label}: {path}") from exc
    raise ProspectiveAccessGateBlocked(f"unsupported {label} format: {path.suffix}")


def _inventory_hash(data: pd.DataFrame) -> str:
    records: list[dict[str, Any]] = []
    for row in data.itertuples(index=False):
        records.append(
            {
                "forward_position": int(row.forward_position),
                "session_index": int(row.session_index),
                "session_date": row.session_date.date().isoformat(),
                "score_artifact_path": str(Path(str(row.score_artifact_path)).resolve()),
                "score_artifact_sha256": str(row.score_artifact_sha256).lower(),
                "score_manifest_path": str(Path(str(row.score_manifest_path)).resolve()),
                "score_manifest_sha256": str(row.score_manifest_sha256).lower(),
            }
        )
    return _canonical_hash(records)


def _load_and_validate_score_artifact(
    path: Path,
    *,
    session_date: pd.Timestamp,
    artifact_sha256: str,
    manifest_sha256: str,
) -> pd.DataFrame:
    frame = _read_table(path, label="V4-X1 score artifact")
    _require_columns(frame, {"ticker", "alpha_consensus"}, label="V4-X1 score artifact")
    date_column = "date" if "date" in frame.columns else "session_date" if "session_date" in frame.columns else None
    if date_column is None:
        raise ProspectiveAccessGateBlocked("V4-X1 score artifact has no date/session_date column")
    dates = _normalize_dates(frame[date_column], label="V4-X1 score artifact")
    if not dates.eq(session_date).all():
        raise ProspectiveAccessGateBlocked("V4-X1 score artifact contains rows from the wrong session")
    tickers = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    if tickers.eq("").any() or tickers.duplicated().any():
        raise ProspectiveAccessGateBlocked("V4-X1 score artifact contains invalid/duplicate tickers")
    scores = pd.to_numeric(frame["alpha_consensus"], errors="coerce")
    if scores.empty or not np.isfinite(scores.to_numpy(dtype=float)).all():
        raise ProspectiveAccessGateBlocked("V4-X1 score artifact contains non-finite alpha_consensus")
    result = pd.DataFrame(
        {
            "session_date": session_date,
            "ticker": tickers,
            "alpha_consensus": scores.to_numpy(dtype=float),
            "score_artifact_sha256": artifact_sha256,
            "score_manifest_sha256": manifest_sha256,
        }
    )
    return result.sort_values(["session_date", "ticker"], kind="mergesort").reset_index(drop=True)


def _validate_score_manifest(
    manifest_path: Path,
    *,
    session_date: pd.Timestamp,
    score_artifact_path: Path,
    score_artifact_sha256: str,
) -> None:
    manifest = _read_json(manifest_path, label="V4-X1 score manifest")
    if manifest.get("status") != "DONE":
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest is not DONE")
    if str(manifest.get("model_id") or "") != MODEL_NAME:
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest model_id changed")
    if str(manifest.get("generation") or "") != MODEL_GENERATION:
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest generation changed")
    if str(manifest.get("model_fingerprint") or "") != MODEL_FINGERPRINT:
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest fingerprint changed")
    if str(manifest.get("session_date") or "") != session_date.date().isoformat():
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest session_date mismatch")
    output = manifest.get("output")
    if not isinstance(output, dict):
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest output is missing")
    if str(output.get("artifact_sha256") or "").lower() != score_artifact_sha256:
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest child artifact hash mismatch")
    declared_path = output.get("artifact_path")
    if declared_path:
        if _resolve_declared_path(declared_path) != score_artifact_path:
            raise ProspectiveAccessGateBlocked("V4-X1 score manifest child artifact path mismatch")
    guards = manifest.get("guards")
    if not isinstance(guards, dict):
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest guards are missing")
    bad_guards = [name for name in _SCORE_MANIFEST_FALSE_GUARDS if guards.get(name) is not False]
    if bad_guards:
        raise ProspectiveAccessGateBlocked(f"V4-X1 score manifest guard changed: {bad_guards}")


def validate_session_inventory(
    inventory: pd.DataFrame,
    *,
    fixture_root: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    required = {
        "forward_position",
        "session_index",
        "session_date",
        "score_artifact_path",
        "score_artifact_sha256",
        "score_manifest_path",
        "score_manifest_sha256",
    }
    _require_columns(inventory, required, label="session inventory")
    data = inventory[list(required)].copy()
    if len(data) != REQUIRED_SESSION_COUNT:
        raise ProspectiveAccessGateBlocked("session inventory must contain exactly 100 rows")
    data["forward_position"] = pd.to_numeric(data["forward_position"], errors="raise").astype(int)
    data["session_index"] = pd.to_numeric(data["session_index"], errors="raise").astype(int)
    data["session_date"] = _normalize_dates(data["session_date"], label="session inventory")
    data = data.sort_values("forward_position", kind="mergesort").reset_index(drop=True)
    if data["forward_position"].tolist() != list(range(1, REQUIRED_SESSION_COUNT + 1)):
        raise ProspectiveAccessGateBlocked("forward positions must be exactly 1..100")
    if data["session_date"].duplicated().any() or data["session_index"].duplicated().any():
        raise ProspectiveAccessGateBlocked("session inventory contains duplicate date/index identity")
    if not data["session_date"].is_monotonic_increasing:
        raise ProspectiveAccessGateBlocked("session inventory dates are not strictly increasing")
    if np.any(np.diff(data["session_index"].to_numpy(dtype=int)) <= 0):
        raise ProspectiveAccessGateBlocked("session inventory indices are not strictly increasing")
    if data["score_artifact_path"].astype(str).duplicated().any() or data["score_manifest_path"].astype(str).duplicated().any():
        raise ProspectiveAccessGateBlocked("session inventory reuses score artifact/manifest paths")

    score_frames: list[pd.DataFrame] = []
    for row in data.itertuples(index=False):
        artifact_path = _verified_path(
            row.score_artifact_path,
            row.score_artifact_sha256,
            label="score artifact",
            fixture_root=fixture_root,
        )
        manifest_path = _verified_path(
            row.score_manifest_path,
            row.score_manifest_sha256,
            label="score manifest",
            fixture_root=fixture_root,
        )
        artifact_sha = str(row.score_artifact_sha256).lower()
        manifest_sha = str(row.score_manifest_sha256).lower()
        _validate_score_manifest(
            manifest_path,
            session_date=row.session_date,
            score_artifact_path=artifact_path,
            score_artifact_sha256=artifact_sha,
        )
        score_frames.append(
            _load_and_validate_score_artifact(
                artifact_path,
                session_date=row.session_date,
                artifact_sha256=artifact_sha,
                manifest_sha256=manifest_sha,
            )
        )
        data.loc[data["forward_position"].eq(row.forward_position), "score_artifact_path"] = str(artifact_path)
        data.loc[data["forward_position"].eq(row.forward_position), "score_manifest_path"] = str(manifest_path)
        data.loc[data["forward_position"].eq(row.forward_position), "score_artifact_sha256"] = artifact_sha
        data.loc[data["forward_position"].eq(row.forward_position), "score_manifest_sha256"] = manifest_sha

    score_frame = pd.concat(score_frames, ignore_index=True)
    expected_sessions = data[["session_date", "session_index"]].copy()
    return data, score_frame, _inventory_hash(data)


def _read_verified_json_attestation(
    path_value: Any,
    sha256_value: Any,
    *,
    label: str,
    fixture_root: Path | None,
) -> tuple[Path, dict[str, Any]]:
    path = _verified_path(
        path_value,
        sha256_value,
        label=label,
        fixture_root=fixture_root,
    )
    return path, _read_json(path, label=label)


def _validate_counter_attestation(
    path_value: Any,
    sha256_value: Any,
    *,
    inventory_sha256: str,
    fixture_root: Path | None,
) -> dict[str, Any]:
    path, payload = _read_verified_json_attestation(
        path_value,
        sha256_value,
        label="forward counter attestation",
        fixture_root=fixture_root,
    )
    if int(payload.get("current", -1)) != REQUIRED_SESSION_COUNT or int(payload.get("target", -1)) != REQUIRED_SESSION_COUNT:
        raise ProspectiveAccessGateBlocked("canonical forward counter is not exactly 100/100")
    if str(payload.get("session_inventory_sha256") or "").lower() != inventory_sha256:
        raise ProspectiveAccessGateBlocked("forward counter attestation is not bound to the exact session inventory")
    return {"path": str(path), "sha256": str(sha256_value).lower(), **payload}


def _validate_target_attestation(
    path_value: Any,
    sha256_value: Any,
    *,
    fixture_root: Path | None,
) -> dict[str, Any]:
    path, payload = _read_verified_json_attestation(
        path_value,
        sha256_value,
        label="canonical target attestation",
        fixture_root=fixture_root,
    )
    target_id = str(payload.get("canonical_target_id") or "").strip()
    if not target_id or payload.get("resolved") is not True:
        raise ProspectiveAccessGateBlocked("canonical V4-X1 target is not uniquely resolved")
    if int(payload.get("required_session_count", -1)) != REQUIRED_SESSION_COUNT:
        raise ProspectiveAccessGateBlocked("canonical target required-session count changed")
    if int(payload.get("matured_session_count", -1)) != REQUIRED_SESSION_COUNT:
        raise ProspectiveAccessGateBlocked("canonical target is not mature for all 100 sessions")
    if not str(payload.get("resolution_lineage") or "").strip():
        raise ProspectiveAccessGateBlocked("canonical target resolution lineage is missing")
    source_path = _verified_path(
        payload.get("source_manifest_path"),
        payload.get("source_manifest_sha256"),
        label="canonical target source manifest",
        fixture_root=fixture_root,
        base_dir=path.parent,
    )
    return {
        "path": str(path),
        "sha256": str(sha256_value).lower(),
        **payload,
        "source_manifest_path": str(source_path),
        "source_manifest_sha256": str(payload.get("source_manifest_sha256")).lower(),
    }


def _validate_paper_attestation(
    path_value: Any,
    sha256_value: Any,
    *,
    fixture_root: Path | None,
) -> dict[str, Any]:
    path, payload = _read_verified_json_attestation(
        path_value,
        sha256_value,
        label="PaperState continuity attestation",
        fixture_root=fixture_root,
    )
    continuity_valid = payload.get("continuity_valid") is True
    execution_valid = payload.get("execution_provenance_valid") is True
    preclassified = payload.get("preclassified_invalidity") is True
    reason = str(payload.get("invalidity_reason") or "").strip()
    if not (continuity_valid and execution_valid):
        if not preclassified or not reason:
            raise ProspectiveAccessGateBlocked(
                "PaperState/execution invalidity must be explicitly classified before protected outcomes load"
            )
    elif preclassified:
        raise ProspectiveAccessGateBlocked("valid PaperState may not be simultaneously preclassified invalid")
    return {
        "path": str(path),
        "sha256": str(sha256_value).lower(),
        **payload,
        "operationally_valid": bool(continuity_valid and execution_valid),
    }


def _validate_benchmark_attestation(
    path_value: Any,
    sha256_value: Any,
    *,
    fixture_root: Path | None,
    expected_sessions: pd.DataFrame,
) -> tuple[dict[str, Any], pd.DataFrame | None]:
    path, payload = _read_verified_json_attestation(
        path_value,
        sha256_value,
        label="benchmark attestation",
        fixture_root=fixture_root,
    )
    status = str(payload.get("status") or "").strip().upper()
    if status == "UNAVAILABLE":
        return {"path": str(path), "sha256": str(sha256_value).lower(), **payload, "status": status}, None
    if status != "PINNED":
        raise ProspectiveAccessGateBlocked("benchmark status must be PINNED or UNAVAILABLE")
    artifact = _verified_path(
        payload.get("artifact_path"),
        payload.get("artifact_sha256"),
        label="benchmark artifact",
        fixture_root=fixture_root,
        base_dir=path.parent,
    )
    frame = _read_table(artifact, label="benchmark artifact")
    _require_columns(frame, {"session_date", "benchmark_close"}, label="benchmark artifact")
    frame = frame[["session_date", "benchmark_close"]].copy()
    frame["session_date"] = _normalize_dates(frame["session_date"], label="benchmark artifact")
    frame["benchmark_close"] = pd.to_numeric(frame["benchmark_close"], errors="coerce")
    if frame["session_date"].duplicated().any() or not np.isfinite(frame["benchmark_close"].to_numpy(dtype=float)).all() or (frame["benchmark_close"] <= 0).any():
        raise ProspectiveAccessGateBlocked("benchmark artifact has invalid keys/values")
    required_dates = set(expected_sessions["session_date"])
    available_dates = set(frame["session_date"])
    if not required_dates.issubset(available_dates):
        raise ProspectiveAccessGateBlocked("pinned benchmark does not cover all 100 prospective sessions")
    return (
        {
            "path": str(path),
            "sha256": str(sha256_value).lower(),
            **payload,
            "status": status,
            "artifact_path": str(artifact),
            "artifact_sha256": str(payload.get("artifact_sha256")).lower(),
        },
        frame.sort_values("session_date", kind="mergesort").reset_index(drop=True),
    )


def _validate_access_audit(
    path_value: Any,
    sha256_value: Any,
    *,
    fixture_root: Path | None,
) -> dict[str, Any]:
    path, payload = _read_verified_json_attestation(
        path_value,
        sha256_value,
        label="prospective outcome access audit",
        fixture_root=fixture_root,
    )
    if payload.get("review_complete") is not True:
        raise ProspectiveAccessGateBlocked("pre-outcome access audit is not complete")
    if payload.get("unauthorized_access_known") is not False:
        raise ProspectiveAccessGateBlocked("known/ambiguous prior prospective outcome access blocks confirmatory evaluation")
    if payload.get("prior_access_marker_exists") is not False:
        raise ProspectiveAccessGateBlocked("a prior protected outcome access marker already exists")
    return {"path": str(path), "sha256": str(sha256_value).lower(), **payload}


def _verify_frozen_code_pins(
    *,
    protocol_path: Path,
    evaluator_path: Path,
    evaluator_commit: str,
) -> tuple[str, str]:
    protocol_blob = git_blob_sha1_file(protocol_path)
    evaluator_blob = git_blob_sha1_file(evaluator_path)
    if protocol_blob != PROTOCOL_GIT_BLOB_SHA1:
        raise ProspectiveAccessGateBlocked("frozen V4-X1 evaluation protocol Git blob changed")
    if evaluator_blob != EVALUATOR_GIT_BLOB_SHA1:
        raise ProspectiveAccessGateBlocked("frozen V4-X1 evaluator Git blob changed")
    if str(evaluator_commit).strip() != EVALUATOR_IMPLEMENTATION_COMMIT:
        raise ProspectiveAccessGateBlocked("evaluator implementation commit pin changed")
    return protocol_blob, evaluator_blob


def prepare_pre_outcome_access(
    *,
    mode: str,
    session_inventory: pd.DataFrame,
    counter_attestation_path: str | Path,
    counter_attestation_sha256: str,
    target_attestation_path: str | Path,
    target_attestation_sha256: str,
    paper_attestation_path: str | Path,
    paper_attestation_sha256: str,
    benchmark_attestation_path: str | Path,
    benchmark_attestation_sha256: str,
    access_audit_path: str | Path,
    access_audit_sha256: str,
    protocol_path: str | Path,
    evaluator_path: str | Path,
    evaluator_commit: str = EVALUATOR_IMPLEMENTATION_COMMIT,
    fixture_root: str | Path | None = None,
    final_access_authorized: bool = False,
) -> _PreparedAccess:
    normalized_mode = str(mode).strip().upper()
    if normalized_mode not in ALLOWED_MODES:
        raise ProspectiveAccessGateBlocked("unknown prospective access mode")
    root = Path(fixture_root).resolve() if fixture_root is not None else None
    if normalized_mode == MODE_SYNTHETIC_REHEARSAL:
        if root is None or not root.is_dir():
            raise ProspectiveAccessGateBlocked("synthetic rehearsal requires an existing fixture_root")
    elif not final_access_authorized:
        raise ProspectiveAccessGateBlocked("real protected outcome access requires explicit final authorization")

    protocol = Path(protocol_path).resolve()
    evaluator = Path(evaluator_path).resolve()
    if not protocol.is_file() or not evaluator.is_file():
        raise ProspectiveAccessGateBlocked("protocol/evaluator pin path is missing")
    protocol_blob, evaluator_blob = _verify_frozen_code_pins(
        protocol_path=protocol,
        evaluator_path=evaluator,
        evaluator_commit=evaluator_commit,
    )

    inventory, score_frame, inventory_sha = validate_session_inventory(
        session_inventory,
        fixture_root=root if normalized_mode == MODE_SYNTHETIC_REHEARSAL else None,
    )
    expected_sessions = inventory[["session_date", "session_index"]].copy()
    counter = _validate_counter_attestation(
        counter_attestation_path,
        counter_attestation_sha256,
        inventory_sha256=inventory_sha,
        fixture_root=root if normalized_mode == MODE_SYNTHETIC_REHEARSAL else None,
    )
    target = _validate_target_attestation(
        target_attestation_path,
        target_attestation_sha256,
        fixture_root=root if normalized_mode == MODE_SYNTHETIC_REHEARSAL else None,
    )
    paper = _validate_paper_attestation(
        paper_attestation_path,
        paper_attestation_sha256,
        fixture_root=root if normalized_mode == MODE_SYNTHETIC_REHEARSAL else None,
    )
    benchmark, benchmark_frame = _validate_benchmark_attestation(
        benchmark_attestation_path,
        benchmark_attestation_sha256,
        fixture_root=root if normalized_mode == MODE_SYNTHETIC_REHEARSAL else None,
        expected_sessions=expected_sessions,
    )
    access_audit = _validate_access_audit(
        access_audit_path,
        access_audit_sha256,
        fixture_root=root if normalized_mode == MODE_SYNTHETIC_REHEARSAL else None,
    )

    return _PreparedAccess(
        session_inventory=inventory,
        expected_sessions=expected_sessions,
        score_frame=score_frame,
        inventory_sha256=inventory_sha,
        counter=counter,
        target=target,
        paper=paper,
        benchmark=benchmark,
        access_audit=access_audit,
        benchmark_frame=benchmark_frame,
        protocol_blob_sha1=protocol_blob,
        evaluator_blob_sha1=evaluator_blob,
    )


def _preaccess_payload(prepared: _PreparedAccess, *, mode: str) -> dict[str, Any]:
    return {
        "schema_version": ACCESS_GATE_SCHEMA,
        "status": "PRE_OUTCOME_ACCESS_GATES_PASS",
        "mode": mode,
        "model_name": MODEL_NAME,
        "model_generation": MODEL_GENERATION,
        "model_fingerprint": MODEL_FINGERPRINT,
        "protocol_status": PROTOCOL_STATUS,
        "protocol_commit": PROTOCOL_COMMIT,
        "protocol_git_blob_sha1": prepared.protocol_blob_sha1,
        "evaluator_commit": EVALUATOR_IMPLEMENTATION_COMMIT,
        "evaluator_git_blob_sha1": prepared.evaluator_blob_sha1,
        "session_count": REQUIRED_SESSION_COUNT,
        "session_inventory_sha256": prepared.inventory_sha256,
        "first_session": prepared.expected_sessions.iloc[0]["session_date"].date().isoformat(),
        "last_session": prepared.expected_sessions.iloc[-1]["session_date"].date().isoformat(),
        "counter_attestation_sha256": prepared.counter["sha256"],
        "canonical_target_id": prepared.target["canonical_target_id"],
        "target_attestation_sha256": prepared.target["sha256"],
        "target_source_manifest_sha256": prepared.target["source_manifest_sha256"],
        "paper_attestation_sha256": prepared.paper["sha256"],
        "paper_operationally_valid": prepared.paper["operationally_valid"],
        "paper_preclassified_invalidity": bool(prepared.paper.get("preclassified_invalidity") is True),
        "benchmark_status": prepared.benchmark["status"],
        "benchmark_attestation_sha256": prepared.benchmark["sha256"],
        "access_audit_sha256": prepared.access_audit["sha256"],
        "unauthorized_access_known": False,
    }


def _marker_payload(prepared: _PreparedAccess, *, mode: str, preaccess_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": ACCESS_GATE_SCHEMA,
        "marker": REAL_ACCESS_MARKER if mode == MODE_PROTECTED_PROSPECTIVE else REHEARSAL_ACCESS_MARKER,
        "mode": mode,
        "model_name": MODEL_NAME,
        "model_fingerprint": MODEL_FINGERPRINT,
        "session_inventory_sha256": prepared.inventory_sha256,
        "canonical_target_id": prepared.target["canonical_target_id"],
        "preaccess_attestation_sha256": preaccess_sha256,
        "protocol_git_blob_sha1": prepared.protocol_blob_sha1,
        "evaluator_git_blob_sha1": prepared.evaluator_blob_sha1,
        "evaluator_commit": EVALUATOR_IMPLEMENTATION_COMMIT,
    }


def _validate_target_bundle(
    target_frame: pd.DataFrame,
    score_frame: pd.DataFrame,
    *,
    canonical_target_id: str,
) -> pd.DataFrame:
    _require_columns(target_frame, {"session_date", "ticker", "canonical_target"}, label="protected target frame")
    targets = target_frame[["session_date", "ticker", "canonical_target"]].copy()
    targets["session_date"] = _normalize_dates(targets["session_date"], label="protected target frame")
    targets["ticker"] = targets["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    targets["canonical_target"] = pd.to_numeric(targets["canonical_target"], errors="coerce")
    if targets["ticker"].eq("").any() or targets.duplicated(["session_date", "ticker"]).any():
        raise ProspectiveAccessGateBlocked("protected target frame has invalid/duplicate keys")
    if not np.isfinite(targets["canonical_target"].to_numpy(dtype=float)).all():
        raise ProspectiveAccessGateBlocked("protected target frame contains non-finite canonical targets")

    score_keys = score_frame[["session_date", "ticker"]]
    target_keys = targets[["session_date", "ticker"]]
    key_check = score_keys.merge(target_keys, on=["session_date", "ticker"], how="outer", indicator=True)
    if not key_check["_merge"].eq("both").all():
        raise ProspectiveAccessGateBlocked("protected target keys do not exactly match frozen score keys")

    alpha = score_frame.merge(targets, on=["session_date", "ticker"], how="inner", validate="one_to_one")
    alpha["canonical_target_id"] = canonical_target_id
    return alpha.sort_values(["session_date", "ticker"], kind="mergesort").reset_index(drop=True)


def _validate_bundle_metadata(bundle: ProtectedEvaluationBundle, prepared: _PreparedAccess) -> None:
    metadata = dict(bundle.metadata)
    expected = {
        "canonical_target_id": str(prepared.target["canonical_target_id"]),
        "target_source_manifest_sha256": str(prepared.target["source_manifest_sha256"]).lower(),
        "paper_attestation_sha256": str(prepared.paper["sha256"]).lower(),
        "counter_attestation_sha256": str(prepared.counter["sha256"]).lower(),
        "session_inventory_sha256": prepared.inventory_sha256,
    }
    for key, value in expected.items():
        if str(metadata.get(key) or "").strip().lower() != str(value).strip().lower():
            raise ProspectiveAccessGateBlocked(f"protected loader metadata binding mismatch: {key}")


def _validate_valid_paper_bundle(
    bundle: ProtectedEvaluationBundle,
    prepared: _PreparedAccess,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if bundle.nav_frame is None or bundle.execution_frame is None or bundle.order_frame is None:
        raise ProspectiveAccessGateBlocked("operationally valid paper evaluation requires NAV, execution, and order frames")
    nav = bundle.nav_frame.copy()
    _require_columns(nav, {"session_date", "nav"}, label="protected NAV frame")
    nav["session_date"] = _normalize_dates(nav["session_date"], label="protected NAV frame")
    nav = nav.sort_values("session_date", kind="mergesort").reset_index(drop=True)
    if nav["session_date"].duplicated().any() or len(nav) != REQUIRED_SESSION_COUNT + 1:
        raise ProspectiveAccessGateBlocked("protected NAV path must contain one predecessor mark plus 100 session marks")
    expected_dates = prepared.expected_sessions["session_date"].tolist()
    if nav.iloc[1:]["session_date"].tolist() != expected_dates:
        raise ProspectiveAccessGateBlocked("protected NAV marking dates do not match the frozen 100-session block")
    if not (nav.iloc[0]["session_date"] < prepared.expected_sessions.iloc[0]["session_date"]):
        raise ProspectiveAccessGateBlocked("protected NAV predecessor mark must precede the first prospective session")
    return nav, bundle.execution_frame.copy(), bundle.order_frame.copy()


def _evaluate_loaded_bundle(
    bundle: ProtectedEvaluationBundle,
    prepared: _PreparedAccess,
) -> dict[str, Any]:
    _validate_bundle_metadata(bundle, prepared)
    target_id = str(prepared.target["canonical_target_id"])
    alpha_frame = _validate_target_bundle(bundle.target_frame, prepared.score_frame, canonical_target_id=target_id)
    try:
        validate_alpha_session_alignment(alpha_frame, prepared.expected_sessions)
        alpha = evaluate_alpha_metrics(alpha_frame)
        alpha_state = alpha_verdict(alpha)
        ledger = validate_exclusion_ledger(bundle.ledger, prepared.expected_sessions)
    except ProspectiveEvaluationBlocked as exc:
        raise ProspectiveAccessGateBlocked(str(exc)) from exc

    if not prepared.paper["operationally_valid"]:
        return {
            "schema_version": ACCESS_GATE_SCHEMA,
            "model": {
                "name": MODEL_NAME,
                "generation": MODEL_GENERATION,
                "fingerprint": MODEL_FINGERPRINT,
            },
            "canonical_target_id": target_id,
            "alpha": alpha,
            "portfolio": None,
            "turnover": None,
            "pending_orders": None,
            "benchmark": {"benchmark_status": prepared.benchmark["status"]},
            "exclusion_ledger": ledger,
            "verdicts": {
                "alpha": alpha_state,
                "economic": "ECONOMIC_INVALID_OPERATIONAL",
                "execution": "EXECUTION_BROKEN",
                "overall": "PROSPECTIVE_INVALID_OPERATIONAL",
            },
            "operational_invalidity_reason": str(prepared.paper.get("invalidity_reason") or ""),
        }

    nav, execution_frame, order_frame = _validate_valid_paper_bundle(bundle, prepared)
    try:
        portfolio = evaluate_portfolio_metrics(nav)
        turnover = evaluate_turnover(execution_frame)
        pending = evaluate_pending_orders(order_frame)
        economic_state = economic_verdict(portfolio)
        execution_state = execution_verdict(continuity_valid=True, invariants_valid=True, material_drag=False)
        overall_state = overall_verdict(
            operational_valid=True,
            alpha_state=alpha_state,
            economic_state=economic_state,
            execution_state=execution_state,
        )
        if prepared.benchmark_frame is None:
            benchmark = {"benchmark_status": "BENCHMARK_UNAVAILABLE"}
        else:
            benchmark = evaluate_benchmark(nav, prepared.benchmark_frame)
    except ProspectiveEvaluationBlocked as exc:
        raise ProspectiveAccessGateBlocked(str(exc)) from exc

    return {
        "schema_version": ACCESS_GATE_SCHEMA,
        "model": {
            "name": MODEL_NAME,
            "generation": MODEL_GENERATION,
            "fingerprint": MODEL_FINGERPRINT,
        },
        "canonical_target_id": target_id,
        "alpha": alpha,
        "portfolio": portfolio,
        "turnover": turnover,
        "pending_orders": pending,
        "benchmark": benchmark,
        "exclusion_ledger": ledger,
        "verdicts": {
            "alpha": alpha_state,
            "economic": economic_state,
            "execution": execution_state,
            "overall": overall_state,
        },
    }


def _existing_result(output_dir: Path, *, mode: str) -> dict[str, Any] | None:
    preaccess = output_dir / PREACCESS_FILENAME
    marker = output_dir / MARKER_FILENAME
    result = output_dir / RESULT_FILENAME
    manifest = output_dir / FINAL_MANIFEST_FILENAME
    failure = output_dir / FAILURE_FILENAME
    present = {path.name: path.exists() for path in (preaccess, marker, result, manifest, failure)}
    if not any(present.values()):
        return None
    if marker.exists() and result.exists() and manifest.exists() and preaccess.exists() and not failure.exists():
        final_manifest = _read_json(manifest, label="final evaluation manifest")
        marker_payload = _read_json(marker, label="outcome access marker")
        if str(final_manifest.get("mode") or "") != mode or str(marker_payload.get("mode") or "") != mode:
            raise ProspectiveAccessGateBlocked("persisted evaluation mode mismatch")
        if sha256_file(result) != str(final_manifest.get("result_sha256") or ""):
            raise ProspectiveAccessGateBlocked("persisted evaluation result hash mismatch")
        if sha256_file(marker) != str(final_manifest.get("marker_sha256") or ""):
            raise ProspectiveAccessGateBlocked("persisted evaluation marker hash mismatch")
        if sha256_file(preaccess) != str(final_manifest.get("preaccess_attestation_sha256") or ""):
            raise ProspectiveAccessGateBlocked("persisted preaccess attestation hash mismatch")
        return _read_json(result, label="persisted prospective evaluation result")
    raise ProspectiveAccessGateBlocked(
        "partial prior outcome-access state exists; fail closed for manual forensic recovery"
    )


def run_protected_evaluation_once(
    *,
    mode: str,
    output_dir: str | Path,
    protected_loader: Callable[[], ProtectedEvaluationBundle],
    session_inventory: pd.DataFrame,
    counter_attestation_path: str | Path,
    counter_attestation_sha256: str,
    target_attestation_path: str | Path,
    target_attestation_sha256: str,
    paper_attestation_path: str | Path,
    paper_attestation_sha256: str,
    benchmark_attestation_path: str | Path,
    benchmark_attestation_sha256: str,
    access_audit_path: str | Path,
    access_audit_sha256: str,
    protocol_path: str | Path,
    evaluator_path: str | Path,
    evaluator_commit: str = EVALUATOR_IMPLEMENTATION_COMMIT,
    fixture_root: str | Path | None = None,
    final_access_authorized: bool = False,
    event_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run exactly one guarded evaluation, writing the access marker before the loader.

    Rehearsal mode exists solely to prove ordering/idempotency with synthetic or
    otherwise non-prospective fixtures.  Real mode is deliberately inert unless
    the caller supplies explicit final authorization after all 100 sessions are
    complete.  All pre-access gates execute before the protected loader callback.
    """

    normalized_mode = str(mode).strip().upper()
    if normalized_mode not in ALLOWED_MODES:
        raise ProspectiveAccessGateBlocked("unknown prospective access mode")
    destination = Path(output_dir).resolve()
    if normalized_mode == MODE_SYNTHETIC_REHEARSAL:
        if fixture_root is None:
            raise ProspectiveAccessGateBlocked("synthetic rehearsal requires fixture_root")
        root = Path(fixture_root).resolve()
        _require_under_root(destination, root, label="output directory")

    destination.mkdir(parents=True, exist_ok=True)
    persisted = _existing_result(destination, mode=normalized_mode)
    if persisted is not None:
        if event_hook is not None:
            event_hook("IDEMPOTENT_RESULT_REUSED")
        return persisted
    if any(destination.iterdir()):
        raise ProspectiveAccessGateBlocked("output directory must be empty before first access attempt")

    prepared = prepare_pre_outcome_access(
        mode=normalized_mode,
        session_inventory=session_inventory,
        counter_attestation_path=counter_attestation_path,
        counter_attestation_sha256=counter_attestation_sha256,
        target_attestation_path=target_attestation_path,
        target_attestation_sha256=target_attestation_sha256,
        paper_attestation_path=paper_attestation_path,
        paper_attestation_sha256=paper_attestation_sha256,
        benchmark_attestation_path=benchmark_attestation_path,
        benchmark_attestation_sha256=benchmark_attestation_sha256,
        access_audit_path=access_audit_path,
        access_audit_sha256=access_audit_sha256,
        protocol_path=protocol_path,
        evaluator_path=evaluator_path,
        evaluator_commit=evaluator_commit,
        fixture_root=fixture_root,
        final_access_authorized=final_access_authorized,
    )

    preaccess_path = destination / PREACCESS_FILENAME
    marker_path = destination / MARKER_FILENAME
    result_path = destination / RESULT_FILENAME
    manifest_path = destination / FINAL_MANIFEST_FILENAME
    failure_path = destination / FAILURE_FILENAME

    _write_json_exclusive(preaccess_path, _preaccess_payload(prepared, mode=normalized_mode))
    preaccess_sha = sha256_file(preaccess_path)
    if event_hook is not None:
        event_hook("PREATTESTATION_WRITTEN")

    _write_json_exclusive(
        marker_path,
        _marker_payload(prepared, mode=normalized_mode, preaccess_sha256=preaccess_sha),
    )
    marker_sha = sha256_file(marker_path)
    if event_hook is not None:
        event_hook("MARKER_WRITTEN")

    try:
        if event_hook is not None:
            event_hook("LOADER_CALLED")
        bundle = protected_loader()
        if not isinstance(bundle, ProtectedEvaluationBundle):
            raise ProspectiveAccessGateBlocked("protected loader returned the wrong bundle type")
        result = _evaluate_loaded_bundle(bundle, prepared)
        result_payload = {
            "access_gate_schema": ACCESS_GATE_SCHEMA,
            "access_mode": normalized_mode,
            "session_inventory_sha256": prepared.inventory_sha256,
            "preaccess_attestation_sha256": preaccess_sha,
            "outcome_access_marker_sha256": marker_sha,
            **result,
        }
        _write_json_exclusive(result_path, result_payload)
        result_sha = sha256_file(result_path)
        final_manifest = {
            "schema_version": ACCESS_GATE_SCHEMA,
            "status": "PROSPECTIVE_EVALUATION_COMPLETE",
            "mode": normalized_mode,
            "result_sha256": result_sha,
            "marker_sha256": marker_sha,
            "preaccess_attestation_sha256": preaccess_sha,
            "session_inventory_sha256": prepared.inventory_sha256,
            "model_fingerprint": MODEL_FINGERPRINT,
            "protocol_git_blob_sha1": prepared.protocol_blob_sha1,
            "evaluator_git_blob_sha1": prepared.evaluator_blob_sha1,
            "evaluator_commit": EVALUATOR_IMPLEMENTATION_COMMIT,
        }
        _write_json_exclusive(manifest_path, final_manifest)
        if event_hook is not None:
            event_hook("FINAL_RESULT_WRITTEN")
        return _read_json(result_path, label="prospective evaluation result")
    except Exception as exc:
        if not failure_path.exists():
            try:
                _write_json_exclusive(
                    failure_path,
                    {
                        "schema_version": ACCESS_GATE_SCHEMA,
                        "status": "POST_ACCESS_EVALUATION_FAILED_CLOSED",
                        "mode": normalized_mode,
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                        "marker_sha256": marker_sha,
                        "preaccess_attestation_sha256": preaccess_sha,
                    },
                )
            except Exception:
                pass
        if isinstance(exc, ProspectiveAccessGateBlocked):
            raise
        raise ProspectiveAccessGateBlocked(
            "protected access started but evaluation failed; manual forensic recovery required"
        ) from exc
