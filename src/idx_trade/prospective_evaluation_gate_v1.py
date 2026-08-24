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

# Frozen before this protected-access adapter was implemented.
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
_LEDGER_INVALID_STATES = frozenset(
    {
        "OPERATIONAL_FAILURE",
        "DATA_INCOMPLETE",
        "EXCLUDED_IMPLEMENTATION_DEFECT",
        "NOT_YET_TARGET_MATURED",
    }
)


class ProspectiveAccessGateBlocked(RuntimeError):
    """Raised whenever a precommitted access/evaluation invariant cannot be proven."""


@dataclass(frozen=True)
class ProtectedEvaluationBundle:
    """Protected payload supplied only after a durable access marker exists.

    The loader is injected by the caller. This module performs no vault discovery,
    provider call, network access, or automatic outcome unlock.
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
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def _json_value(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return [_json_value(record) for record in value.to_dict(orient="records")]
    if isinstance(value, pd.Series):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        _json_value(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(_json_value(dict(payload)), sort_keys=True, indent=2, ensure_ascii=False)
        + "\n"
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


def _resolve_path(value: Any, *, base_dir: Path | None = None) -> Path:
    text = str(value or "").strip()
    if not text:
        raise ProspectiveAccessGateBlocked("empty artifact path")
    path = Path(text).expanduser()
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
    path = _resolve_path(path_value, base_dir=base_dir)
    _require_under_root(path, fixture_root, label=label)
    expected = str(expected_sha256 or "").strip().lower()
    if len(expected) != 64:
        raise ProspectiveAccessGateBlocked(f"invalid {label} sha256 declaration")
    if not path.is_file():
        raise ProspectiveAccessGateBlocked(f"missing {label}: {path}")
    if sha256_file(path) != expected:
        raise ProspectiveAccessGateBlocked(f"{label} sha256 mismatch")
    return path


def _read_table(path: Path, *, label: str) -> pd.DataFrame:
    try:
        if path.suffix.lower() in {".parquet", ".pq"}:
            return pd.read_parquet(path)
        if path.suffix.lower() == ".csv":
            return pd.read_csv(path)
    except Exception as exc:
        raise ProspectiveAccessGateBlocked(f"failed to read {label}: {path}") from exc
    raise ProspectiveAccessGateBlocked(f"unsupported {label} format: {path.suffix}")


def _inventory_hash(data: pd.DataFrame) -> str:
    records = []
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


def _load_score_artifact(
    path: Path,
    *,
    session_date: pd.Timestamp,
    session_index: int,
    artifact_sha256: str,
    manifest_sha256: str,
) -> pd.DataFrame:
    frame = _read_table(path, label="V4-X1 score artifact")
    _require_columns(frame, {"ticker", "alpha_consensus"}, label="V4-X1 score artifact")
    date_col = "date" if "date" in frame.columns else "session_date" if "session_date" in frame.columns else None
    if date_col is None:
        raise ProspectiveAccessGateBlocked("V4-X1 score artifact lacks date/session_date")
    dates = _normalize_dates(frame[date_col], label="V4-X1 score artifact")
    if not dates.eq(session_date).all():
        raise ProspectiveAccessGateBlocked("V4-X1 score artifact contains the wrong session")
    tickers = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    scores = pd.to_numeric(frame["alpha_consensus"], errors="coerce")
    if tickers.eq("").any() or tickers.duplicated().any():
        raise ProspectiveAccessGateBlocked("V4-X1 score artifact contains invalid/duplicate tickers")
    if scores.empty or not np.isfinite(scores.to_numpy(dtype=float)).all():
        raise ProspectiveAccessGateBlocked("V4-X1 score artifact contains non-finite alpha_consensus")
    return pd.DataFrame(
        {
            "session_date": session_date,
            "session_index": int(session_index),
            "ticker": tickers,
            "alpha_consensus": scores.to_numpy(dtype=float),
            "score_artifact_sha256": artifact_sha256,
            "score_manifest_sha256": manifest_sha256,
        }
    ).sort_values(["session_date", "ticker"], kind="mergesort").reset_index(drop=True)


def _validate_score_manifest(
    manifest_path: Path,
    *,
    session_date: pd.Timestamp,
    artifact_path: Path,
    artifact_sha256: str,
) -> None:
    manifest = _read_json(manifest_path, label="V4-X1 score manifest")
    checks = {
        "status": manifest.get("status") == "DONE",
        "model_id": str(manifest.get("model_id") or "") == MODEL_NAME,
        "generation": str(manifest.get("generation") or "") == MODEL_GENERATION,
        "fingerprint": str(manifest.get("model_fingerprint") or "") == MODEL_FINGERPRINT,
        "session_date": str(manifest.get("session_date") or "") == session_date.date().isoformat(),
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise ProspectiveAccessGateBlocked(f"V4-X1 score manifest identity mismatch: {failed}")
    output = manifest.get("output")
    if not isinstance(output, dict):
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest output is missing")
    if str(output.get("artifact_sha256") or "").lower() != artifact_sha256:
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest child artifact hash mismatch")
    if output.get("artifact_path") and _resolve_path(output["artifact_path"]) != artifact_path:
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest child artifact path mismatch")
    guards = manifest.get("guards")
    if not isinstance(guards, dict):
        raise ProspectiveAccessGateBlocked("V4-X1 score manifest guards are missing")
    bad = [name for name in _SCORE_MANIFEST_FALSE_GUARDS if guards.get(name) is not False]
    if bad:
        raise ProspectiveAccessGateBlocked(f"V4-X1 score manifest guard changed: {bad}")


def validate_session_inventory(
    inventory: pd.DataFrame,
    *,
    fixture_root: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    columns = [
        "forward_position",
        "session_index",
        "session_date",
        "score_artifact_path",
        "score_artifact_sha256",
        "score_manifest_path",
        "score_manifest_sha256",
    ]
    _require_columns(inventory, set(columns), label="session inventory")
    data = inventory[columns].copy()
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
    if not data["session_date"].is_monotonic_increasing or np.any(
        np.diff(data["session_index"].to_numpy(dtype=int)) <= 0
    ):
        raise ProspectiveAccessGateBlocked("session inventory date/index order is not strictly increasing")
    if data["score_artifact_path"].astype(str).duplicated().any() or data[
        "score_manifest_path"
    ].astype(str).duplicated().any():
        raise ProspectiveAccessGateBlocked("session inventory reuses score artifact/manifest paths")

    score_parts: list[pd.DataFrame] = []
    for row in data.itertuples(index=False):
        artifact = _verified_path(
            row.score_artifact_path,
            row.score_artifact_sha256,
            label="score artifact",
            fixture_root=fixture_root,
        )
        manifest = _verified_path(
            row.score_manifest_path,
            row.score_manifest_sha256,
            label="score manifest",
            fixture_root=fixture_root,
        )
        artifact_sha = str(row.score_artifact_sha256).lower()
        manifest_sha = str(row.score_manifest_sha256).lower()
        _validate_score_manifest(
            manifest,
            session_date=row.session_date,
            artifact_path=artifact,
            artifact_sha256=artifact_sha,
        )
        score_parts.append(
            _load_score_artifact(
                artifact,
                session_date=row.session_date,
                session_index=int(row.session_index),
                artifact_sha256=artifact_sha,
                manifest_sha256=manifest_sha,
            )
        )
        mask = data["forward_position"].eq(row.forward_position)
        data.loc[mask, "score_artifact_path"] = str(artifact)
        data.loc[mask, "score_manifest_path"] = str(manifest)
        data.loc[mask, "score_artifact_sha256"] = artifact_sha
        data.loc[mask, "score_manifest_sha256"] = manifest_sha
    return data, pd.concat(score_parts, ignore_index=True), _inventory_hash(data)


def _read_verified_json_attestation(
    path_value: Any,
    sha_value: Any,
    *,
    label: str,
    fixture_root: Path | None,
) -> tuple[Path, dict[str, Any]]:
    path = _verified_path(path_value, sha_value, label=label, fixture_root=fixture_root)
    return path, _read_json(path, label=label)


def _expected_boundary(expected_sessions: pd.DataFrame) -> tuple[str, str]:
    return (
        expected_sessions.iloc[0]["session_date"].date().isoformat(),
        expected_sessions.iloc[-1]["session_date"].date().isoformat(),
    )


def _validate_counter(
    path_value: Any,
    sha_value: Any,
    *,
    inventory_sha256: str,
    fixture_root: Path | None,
) -> dict[str, Any]:
    path, payload = _read_verified_json_attestation(
        path_value, sha_value, label="forward counter attestation", fixture_root=fixture_root
    )
    if int(payload.get("current", -1)) != 100 or int(payload.get("target", -1)) != 100:
        raise ProspectiveAccessGateBlocked("canonical forward counter is not exactly 100/100")
    if str(payload.get("session_inventory_sha256") or "").lower() != inventory_sha256:
        raise ProspectiveAccessGateBlocked("counter attestation is not bound to the exact session inventory")
    return {"path": str(path), "sha256": str(sha_value).lower(), **payload}


def _validate_target(
    path_value: Any,
    sha_value: Any,
    *,
    expected_sessions: pd.DataFrame,
    fixture_root: Path | None,
) -> dict[str, Any]:
    path, payload = _read_verified_json_attestation(
        path_value, sha_value, label="canonical target attestation", fixture_root=fixture_root
    )
    target_id = str(payload.get("canonical_target_id") or "").strip()
    if not target_id or payload.get("resolved") is not True:
        raise ProspectiveAccessGateBlocked("canonical V4-X1 target is not uniquely resolved")
    if int(payload.get("required_session_count", -1)) != 100 or int(
        payload.get("matured_session_count", -1)
    ) != 100:
        raise ProspectiveAccessGateBlocked("canonical target is not mature for all 100 sessions")
    first, last = _expected_boundary(expected_sessions)
    if str(payload.get("first_session_date") or "") != first or str(
        payload.get("last_session_date") or ""
    ) != last:
        raise ProspectiveAccessGateBlocked("canonical target attestation session boundary mismatch")
    if not str(payload.get("resolution_lineage") or "").strip():
        raise ProspectiveAccessGateBlocked("canonical target resolution lineage is missing")
    source = _verified_path(
        payload.get("source_manifest_path"),
        payload.get("source_manifest_sha256"),
        label="canonical target source manifest",
        fixture_root=fixture_root,
        base_dir=path.parent,
    )
    return {
        "path": str(path),
        "sha256": str(sha_value).lower(),
        **payload,
        "source_manifest_path": str(source),
        "source_manifest_sha256": str(payload.get("source_manifest_sha256")).lower(),
    }


def _validate_paper(
    path_value: Any,
    sha_value: Any,
    *,
    expected_sessions: pd.DataFrame,
    fixture_root: Path | None,
) -> dict[str, Any]:
    path, payload = _read_verified_json_attestation(
        path_value, sha_value, label="PaperState continuity attestation", fixture_root=fixture_root
    )
    first, last = _expected_boundary(expected_sessions)
    predecessor = pd.to_datetime(payload.get("predecessor_session_date"), errors="coerce")
    if pd.isna(predecessor) or predecessor.normalize() >= pd.Timestamp(first):
        raise ProspectiveAccessGateBlocked("PaperState predecessor session is missing/invalid")
    if int(payload.get("session_count", -1)) != 100 or str(
        payload.get("first_session_date") or ""
    ) != first or str(payload.get("last_session_date") or "") != last:
        raise ProspectiveAccessGateBlocked("PaperState attestation session boundary mismatch")
    continuity = payload.get("continuity_valid") is True
    execution = payload.get("execution_provenance_valid") is True
    preclassified = payload.get("preclassified_invalidity") is True
    reason = str(payload.get("invalidity_reason") or "").strip()
    if not (continuity and execution):
        if not preclassified or not reason:
            raise ProspectiveAccessGateBlocked(
                "PaperState/execution invalidity must be classified before outcomes load"
            )
    elif preclassified:
        raise ProspectiveAccessGateBlocked("valid PaperState cannot also be preclassified invalid")
    return {
        "path": str(path),
        "sha256": str(sha_value).lower(),
        **payload,
        "predecessor_session_date": predecessor.normalize().date().isoformat(),
        "operationally_valid": bool(continuity and execution),
    }


def _validate_benchmark(
    path_value: Any,
    sha_value: Any,
    *,
    expected_sessions: pd.DataFrame,
    predecessor_session_date: str,
    fixture_root: Path | None,
) -> tuple[dict[str, Any], pd.DataFrame | None]:
    path, payload = _read_verified_json_attestation(
        path_value, sha_value, label="benchmark attestation", fixture_root=fixture_root
    )
    status = str(payload.get("status") or "").strip().upper()
    if status == "UNAVAILABLE":
        return {"path": str(path), "sha256": str(sha_value).lower(), **payload, "status": status}, None
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
    if frame["session_date"].duplicated().any() or not np.isfinite(
        frame["benchmark_close"].to_numpy(dtype=float)
    ).all() or (frame["benchmark_close"] <= 0).any():
        raise ProspectiveAccessGateBlocked("benchmark artifact has invalid keys/values")
    required_dates = set(expected_sessions["session_date"])
    required_dates.add(pd.Timestamp(predecessor_session_date))
    if not required_dates.issubset(set(frame["session_date"])):
        raise ProspectiveAccessGateBlocked("pinned benchmark lacks the exact evaluation boundary")
    return (
        {
            "path": str(path),
            "sha256": str(sha_value).lower(),
            **payload,
            "status": status,
            "artifact_path": str(artifact),
            "artifact_sha256": str(payload.get("artifact_sha256")).lower(),
        },
        frame.sort_values("session_date", kind="mergesort").reset_index(drop=True),
    )


def _validate_access_audit(
    path_value: Any,
    sha_value: Any,
    *,
    fixture_root: Path | None,
) -> dict[str, Any]:
    path, payload = _read_verified_json_attestation(
        path_value, sha_value, label="prospective outcome access audit", fixture_root=fixture_root
    )
    if payload.get("review_complete") is not True:
        raise ProspectiveAccessGateBlocked("pre-outcome access audit is not complete")
    if payload.get("unauthorized_access_known") is not False:
        raise ProspectiveAccessGateBlocked("known/ambiguous prior outcome access blocks confirmation")
    if payload.get("prior_access_marker_exists") is not False:
        raise ProspectiveAccessGateBlocked("a prior protected outcome access marker already exists")
    return {"path": str(path), "sha256": str(sha_value).lower(), **payload}


def _verify_code_pins(
    *, protocol_path: Path, evaluator_path: Path, evaluator_commit: str
) -> tuple[str, str]:
    protocol_blob = git_blob_sha1_file(protocol_path)
    evaluator_blob = git_blob_sha1_file(evaluator_path)
    if protocol_blob != PROTOCOL_GIT_BLOB_SHA1:
        raise ProspectiveAccessGateBlocked("frozen evaluation protocol Git blob changed")
    if evaluator_blob != EVALUATOR_GIT_BLOB_SHA1:
        raise ProspectiveAccessGateBlocked("frozen evaluator Git blob changed")
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
    scoped_root = root if normalized_mode == MODE_SYNTHETIC_REHEARSAL else None
    if normalized_mode == MODE_SYNTHETIC_REHEARSAL:
        if root is None or not root.is_dir():
            raise ProspectiveAccessGateBlocked("synthetic rehearsal requires existing fixture_root")
    elif not final_access_authorized:
        raise ProspectiveAccessGateBlocked("real protected access requires explicit final authorization")

    protocol = Path(protocol_path).resolve()
    evaluator = Path(evaluator_path).resolve()
    if not protocol.is_file() or not evaluator.is_file():
        raise ProspectiveAccessGateBlocked("protocol/evaluator pin path is missing")
    protocol_blob, evaluator_blob = _verify_code_pins(
        protocol_path=protocol, evaluator_path=evaluator, evaluator_commit=evaluator_commit
    )

    inventory, score_frame, inventory_sha = validate_session_inventory(
        session_inventory, fixture_root=scoped_root
    )
    expected = inventory[["session_date", "session_index"]].copy()
    counter = _validate_counter(
        counter_attestation_path,
        counter_attestation_sha256,
        inventory_sha256=inventory_sha,
        fixture_root=scoped_root,
    )
    target = _validate_target(
        target_attestation_path,
        target_attestation_sha256,
        expected_sessions=expected,
        fixture_root=scoped_root,
    )
    paper = _validate_paper(
        paper_attestation_path,
        paper_attestation_sha256,
        expected_sessions=expected,
        fixture_root=scoped_root,
    )
    benchmark, benchmark_frame = _validate_benchmark(
        benchmark_attestation_path,
        benchmark_attestation_sha256,
        expected_sessions=expected,
        predecessor_session_date=paper["predecessor_session_date"],
        fixture_root=scoped_root,
    )
    access_audit = _validate_access_audit(
        access_audit_path, access_audit_sha256, fixture_root=scoped_root
    )
    return _PreparedAccess(
        session_inventory=inventory,
        expected_sessions=expected,
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
    first, last = _expected_boundary(prepared.expected_sessions)
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
        "session_count": 100,
        "first_session": first,
        "last_session": last,
        "session_inventory_sha256": prepared.inventory_sha256,
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
    target_frame: pd.DataFrame, score_frame: pd.DataFrame, *, canonical_target_id: str
) -> pd.DataFrame:
    _require_columns(
        target_frame,
        {"session_date", "ticker", "canonical_target"},
        label="protected target frame",
    )
    targets = target_frame[["session_date", "ticker", "canonical_target"]].copy()
    targets["session_date"] = _normalize_dates(targets["session_date"], label="protected target frame")
    targets["ticker"] = (
        targets["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    targets["canonical_target"] = pd.to_numeric(targets["canonical_target"], errors="coerce")
    if targets["ticker"].eq("").any() or targets.duplicated(["session_date", "ticker"]).any():
        raise ProspectiveAccessGateBlocked("protected target frame has invalid/duplicate keys")
    if not np.isfinite(targets["canonical_target"].to_numpy(dtype=float)).all():
        raise ProspectiveAccessGateBlocked("protected target frame contains non-finite targets")
    key_check = score_frame[["session_date", "ticker"]].merge(
        targets[["session_date", "ticker"]],
        on=["session_date", "ticker"],
        how="outer",
        indicator=True,
    )
    if not key_check["_merge"].eq("both").all():
        raise ProspectiveAccessGateBlocked("protected target keys do not exactly match frozen score keys")
    alpha = score_frame.merge(targets, on=["session_date", "ticker"], validate="one_to_one")
    alpha["canonical_target_id"] = canonical_target_id
    return alpha.sort_values(["session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def _validate_bundle_metadata(bundle: ProtectedEvaluationBundle, prepared: _PreparedAccess) -> None:
    metadata = dict(bundle.metadata)
    expected = {
        "canonical_target_id": str(prepared.target["canonical_target_id"]),
        "target_source_manifest_sha256": str(prepared.target["source_manifest_sha256"]).lower(),
        "paper_attestation_sha256": str(prepared.paper["sha256"]).lower(),
        "counter_attestation_sha256": str(prepared.counter["sha256"]).lower(),
        "session_inventory_sha256": prepared.inventory_sha256,
    }
    for key, expected_value in expected.items():
        if str(metadata.get(key) or "").strip().lower() != expected_value.lower():
            raise ProspectiveAccessGateBlocked(f"protected loader metadata mismatch: {key}")


def _validate_nav_bundle(bundle: ProtectedEvaluationBundle, prepared: _PreparedAccess) -> pd.DataFrame:
    if bundle.nav_frame is None or bundle.execution_frame is None or bundle.order_frame is None:
        raise ProspectiveAccessGateBlocked(
            "operationally valid evaluation requires NAV, execution, and order frames"
        )
    nav = bundle.nav_frame.copy()
    _require_columns(nav, {"session_date", "nav"}, label="protected NAV frame")
    nav["session_date"] = _normalize_dates(nav["session_date"], label="protected NAV frame")
    nav = nav.sort_values("session_date", kind="mergesort").reset_index(drop=True)
    if nav["session_date"].duplicated().any() or len(nav) != 101:
        raise ProspectiveAccessGateBlocked("NAV path must contain one predecessor mark plus 100 marks")
    if nav.iloc[1:]["session_date"].tolist() != prepared.expected_sessions["session_date"].tolist():
        raise ProspectiveAccessGateBlocked("NAV marking dates do not match the frozen 100-session block")
    if nav.iloc[0]["session_date"].date().isoformat() != prepared.paper["predecessor_session_date"]:
        raise ProspectiveAccessGateBlocked("NAV predecessor does not match PaperState attestation")
    return nav


def _evaluate_loaded_bundle(bundle: ProtectedEvaluationBundle, prepared: _PreparedAccess) -> dict[str, Any]:
    _validate_bundle_metadata(bundle, prepared)
    target_id = str(prepared.target["canonical_target_id"])
    alpha_frame = _validate_target_bundle(
        bundle.target_frame, prepared.score_frame, canonical_target_id=target_id
    )
    try:
        validate_alpha_session_alignment(alpha_frame, prepared.expected_sessions)
        alpha = evaluate_alpha_metrics(alpha_frame)
        alpha_state = alpha_verdict(
            mean_ic=float(alpha["mean_ic"]),
            ci_low=float(alpha["bootstrap_ci_95"][0]),
            valid=True,
        )
        ledger = validate_exclusion_ledger(bundle.ledger, prepared.expected_sessions)
    except ProspectiveEvaluationBlocked as exc:
        raise ProspectiveAccessGateBlocked(str(exc)) from exc

    ledger_valid = not ledger["state"].isin(_LEDGER_INVALID_STATES).any()
    if not prepared.paper["operationally_valid"]:
        return {
            "schema_version": ACCESS_GATE_SCHEMA,
            "protocol_status": PROTOCOL_STATUS,
            "protocol_commit": PROTOCOL_COMMIT,
            "model": {"name": MODEL_NAME, "generation": MODEL_GENERATION, "fingerprint": MODEL_FINGERPRINT},
            "canonical_target_id": target_id,
            "operational_valid": False,
            "ledger": ledger,
            "alpha": alpha,
            "portfolio": None,
            "diagnostics": {"benchmark": {"benchmark_status": prepared.benchmark["status"]}},
            "verdicts": {
                "alpha": alpha_state,
                "economics": "ECONOMIC_INVALID_OPERATIONAL",
                "execution": "EXECUTION_BROKEN",
                "overall": "PROSPECTIVE_INVALID_OPERATIONAL",
            },
            "operational_invalidity_reason": str(prepared.paper.get("invalidity_reason") or ""),
        }

    nav = _validate_nav_bundle(bundle, prepared)
    try:
        portfolio = evaluate_portfolio_metrics(nav)
        turnover = evaluate_turnover(bundle.execution_frame)  # type: ignore[arg-type]
        pending = evaluate_pending_orders(bundle.order_frame)  # type: ignore[arg-type]
        economics = economic_verdict(
            net_total_return=float(portfolio["net_total_return"]),
            sharpe_0=float(portfolio["sharpe_0"]),
            valid=True,
        )
        execution = execution_verdict(
            invariants_valid=True, state_reconstructable=True, material_drag=False
        )
        operational_valid = bool(ledger_valid)
        overall = overall_verdict(
            operational_valid=operational_valid,
            alpha=alpha_state,
            economics=economics,
            execution=execution,
        )
        benchmark = (
            {"benchmark_status": "BENCHMARK_UNAVAILABLE"}
            if prepared.benchmark_frame is None
            else evaluate_benchmark(nav, prepared.benchmark_frame)
        )
    except ProspectiveEvaluationBlocked as exc:
        raise ProspectiveAccessGateBlocked(str(exc)) from exc
    return {
        "schema_version": ACCESS_GATE_SCHEMA,
        "protocol_status": PROTOCOL_STATUS,
        "protocol_commit": PROTOCOL_COMMIT,
        "model": {"name": MODEL_NAME, "generation": MODEL_GENERATION, "fingerprint": MODEL_FINGERPRINT},
        "canonical_target_id": target_id,
        "operational_valid": operational_valid,
        "ledger": ledger,
        "alpha": alpha,
        "portfolio": portfolio,
        "diagnostics": {
            "turnover": turnover,
            "pending_orders": pending,
            "benchmark": benchmark,
        },
        "verdicts": {
            "alpha": alpha_state,
            "economics": economics,
            "execution": execution,
            "overall": overall,
        },
    }


def _existing_result(output_dir: Path, *, mode: str) -> dict[str, Any] | None:
    preaccess = output_dir / PREACCESS_FILENAME
    marker = output_dir / MARKER_FILENAME
    result = output_dir / RESULT_FILENAME
    manifest = output_dir / FINAL_MANIFEST_FILENAME
    failure = output_dir / FAILURE_FILENAME
    if not any(path.exists() for path in (preaccess, marker, result, manifest, failure)):
        return None
    if preaccess.exists() and marker.exists() and result.exists() and manifest.exists() and not failure.exists():
        final = _read_json(manifest, label="final evaluation manifest")
        marker_payload = _read_json(marker, label="outcome access marker")
        if str(final.get("mode") or "") != mode or str(marker_payload.get("mode") or "") != mode:
            raise ProspectiveAccessGateBlocked("persisted evaluation mode mismatch")
        if sha256_file(result) != str(final.get("result_sha256") or ""):
            raise ProspectiveAccessGateBlocked("persisted result hash mismatch")
        if sha256_file(marker) != str(final.get("marker_sha256") or ""):
            raise ProspectiveAccessGateBlocked("persisted marker hash mismatch")
        if sha256_file(preaccess) != str(final.get("preaccess_attestation_sha256") or ""):
            raise ProspectiveAccessGateBlocked("persisted preaccess hash mismatch")
        return _read_json(result, label="persisted prospective evaluation result")
    raise ProspectiveAccessGateBlocked(
        "partial prior outcome-access state exists; fail closed for forensic recovery"
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
    """Run a one-shot protected evaluation with marker-before-loader ordering.

    Rehearsal mode proves the mechanism on synthetic/non-prospective fixtures.
    Real mode remains inert until an explicit final authorization is supplied at
    the 100/100 maturity gate. A successful rerun returns the immutable result
    without invoking the protected loader again.
    """

    normalized_mode = str(mode).strip().upper()
    if normalized_mode not in ALLOWED_MODES:
        raise ProspectiveAccessGateBlocked("unknown prospective access mode")
    destination = Path(output_dir).resolve()
    if normalized_mode == MODE_SYNTHETIC_REHEARSAL:
        if fixture_root is None:
            raise ProspectiveAccessGateBlocked("synthetic rehearsal requires fixture_root")
        _require_under_root(destination, Path(fixture_root).resolve(), label="output directory")

    destination.mkdir(parents=True, exist_ok=True)
    persisted = _existing_result(destination, mode=normalized_mode)
    if persisted is not None:
        if event_hook is not None:
            event_hook("IDEMPOTENT_RESULT_REUSED")
        return persisted
    if any(destination.iterdir()):
        raise ProspectiveAccessGateBlocked("output directory must be empty before first access")

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
            raise ProspectiveAccessGateBlocked("protected loader returned wrong bundle type")
        evaluated = _evaluate_loaded_bundle(bundle, prepared)
        result_payload = {
            "access_gate_schema": ACCESS_GATE_SCHEMA,
            "access_mode": normalized_mode,
            "session_inventory_sha256": prepared.inventory_sha256,
            "preaccess_attestation_sha256": preaccess_sha,
            "outcome_access_marker_sha256": marker_sha,
            **evaluated,
        }
        _write_json_exclusive(result_path, result_payload)
        result_sha = sha256_file(result_path)
        _write_json_exclusive(
            manifest_path,
            {
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
            },
        )
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
            "protected access started but evaluation failed; manual recovery required"
        ) from exc
