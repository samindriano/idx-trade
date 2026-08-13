from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .forward_100_evaluator import (
    BLOCK_SESSIONS,
    O2_FEATURE_ORDER_SHA256,
    O2_MODEL_SHA256,
    PROTOCOL_COMMIT,
    PROTOCOL_SHA256,
    PROTOCOL_STATUS,
    REAL_FORWARD_MARKER,
    SYNTHETIC_MARKER,
    ForwardEvaluationBlocked,
    _canonical_hash,
    _write_json,
    _write_synthetic_marker,
    evaluate_o2,
    evaluate_reliability,
    joint_interpretation,
    materialize_outcome_frame,
    validate_named_artifacts,
    validate_o2_scores,
)
from .forward_model_runtime import O2_MODEL_ID
from .provenance import environment_manifest, sha256_file
from .reliability_v1_forward_shadow import (
    PROTECTED_FLAGS as RELIABILITY_PROTECTED_FLAGS,
    RELIABILITY_FORMULA_VERSION,
    RELIABILITY_MODEL_ID,
)
from .storage import write_parquet_atomic


RELIABILITY_SPEC_COMMIT = "3239a319fbd4ff492b16a74d899a20edc9affa7f"
GUARDED_SCHEMA = "idx-trade/forward-100-synthetic-evaluation-artifacts-guarded-v1"
SUPERSEDES_UNGUARDED_ENTRYPOINT = "forward_100_evaluator.run_synthetic_forward_evaluation"


def _normal_date(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    timestamp = timestamp.normalize()
    if pd.isna(timestamp):
        raise ForwardEvaluationBlocked("invalid session date")
    return timestamp


def _text(value: object) -> str:
    if value is None:
        return ""
    try:
        if bool(pd.isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _valid_sha(value: object) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", _text(value).lower()))


def _path_inside(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    return resolved == root or root in resolved.parents


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ForwardEvaluationBlocked(f"malformed {label}: {path}") from exc
    if not isinstance(payload, dict):
        raise ForwardEvaluationBlocked(f"{label} must be a JSON object: {path}")
    return payload


def _read_parquet(path: Path, *, label: str) -> pd.DataFrame:
    try:
        frame = pd.read_parquet(path)
    except Exception as exc:  # parquet engines raise several implementation-specific exceptions
        raise ForwardEvaluationBlocked(f"unreadable {label}: {path}") from exc
    if not isinstance(frame, pd.DataFrame):
        raise ForwardEvaluationBlocked(f"{label} is not a DataFrame: {path}")
    return frame


def _require_columns(frame: pd.DataFrame, required: set[str], *, label: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ForwardEvaluationBlocked(f"{label} missing columns: {sorted(missing)}")


def _reliability_declared(row: object) -> bool:
    values = (
        _text(getattr(row, "reliability_path")),
        _text(getattr(row, "reliability_sha256")),
        _text(getattr(row, "reliability_manifest_path")),
        _text(getattr(row, "reliability_manifest_sha256")),
    )
    if any(values) and not all(values):
        raise ForwardEvaluationBlocked("partial Reliability sidecar declaration")
    return all(values)


def validate_guarded_session_inventory(
    inventory: pd.DataFrame,
    *,
    fixture_root: Path,
) -> tuple[pd.DataFrame, bool]:
    """Validate the synthetic inventory against the real O2/Reliability contracts.

    Unlike the superseded synthetic validator, this uses the accepted Reliability
    V1 manifest identity and protected-flag schema exactly. Missing Reliability
    sidecars are allowed only as an all-or-none declaration per session and are
    surfaced as a pre-outcome INCONCLUSIVE_DATA disposition by the runner.
    """

    required = {
        "session_date",
        "session_index",
        "o2_score_path",
        "o2_score_sha256",
        "o2_manifest_path",
        "o2_manifest_sha256",
        "reliability_path",
        "reliability_sha256",
        "reliability_manifest_path",
        "reliability_manifest_sha256",
        "protected",
    }
    _require_columns(inventory, required, label="session inventory")
    data = inventory.copy()
    if len(data) != BLOCK_SESSIONS:
        raise ForwardEvaluationBlocked("session inventory must contain exactly 100 rows")
    data["session_date"] = pd.to_datetime(data["session_date"], errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
    if data["session_date"].isna().any():
        raise ForwardEvaluationBlocked("session inventory contains invalid dates")
    data["session_index"] = pd.to_numeric(data["session_index"], errors="raise").astype(int)
    data = data.sort_values(["session_index", "session_date"], kind="mergesort").reset_index(drop=True)
    if data["session_date"].duplicated().any() or data["session_index"].duplicated().any():
        raise ForwardEvaluationBlocked("session inventory contains duplicate dates or indices")
    if not np.array_equal(
        np.diff(data["session_index"].to_numpy(dtype=int)),
        np.ones(BLOCK_SESSIONS - 1, dtype=int),
    ):
        raise ForwardEvaluationBlocked("session indices are not consecutive")
    if not data["session_date"].is_monotonic_increasing:
        raise ForwardEvaluationBlocked("session dates are not strictly ordered")
    if data["protected"].astype(bool).any():
        raise ForwardEvaluationBlocked("guarded synthetic evaluator refuses protected artifacts")

    root = Path(fixture_root).resolve()
    reliability_presence: list[bool] = []
    for row in data.itertuples(index=False):
        declared = _reliability_declared(row)
        reliability_presence.append(declared)

        declarations = [
            ("o2_score_path", "o2_score_sha256", False),
            ("o2_manifest_path", "o2_manifest_sha256", False),
            ("reliability_path", "reliability_sha256", not declared),
            ("reliability_manifest_path", "reliability_manifest_sha256", not declared),
        ]
        for path_column, sha_column, optional in declarations:
            path_text = _text(getattr(row, path_column))
            sha_text = _text(getattr(row, sha_column)).lower()
            if optional and not path_text and not sha_text:
                continue
            if not path_text or not _valid_sha(sha_text):
                raise ForwardEvaluationBlocked(f"invalid artifact declaration: {path_column}")
            path = Path(path_text).resolve()
            if not _path_inside(path, root):
                raise ForwardEvaluationBlocked(f"artifact escapes synthetic fixture root: {path_column}")
            if not path.is_file() or sha256_file(path) != sha_text:
                raise ForwardEvaluationBlocked(f"artifact hash mismatch: {path}")

        session_key = row.session_date.date().isoformat()
        o2_manifest = _read_json(Path(str(row.o2_manifest_path)).resolve(), label="O2 session manifest")
        o2_checks = {
            "status": o2_manifest.get("status") == "DONE",
            "session_date": o2_manifest.get("session_date") == session_key,
            "session_index": int(o2_manifest.get("official_session_index", -1)) == int(row.session_index),
            "model_id": o2_manifest.get("model_id") == O2_MODEL_ID,
            "score_sha": o2_manifest.get("score_artifact_sha256") == row.o2_score_sha256,
            "model_sha": o2_manifest.get("model_sha256") == O2_MODEL_SHA256,
            "feature_sha": o2_manifest.get("feature_order_sha256") == O2_FEATURE_ORDER_SHA256,
            "outcome_blind": o2_manifest.get("outcome_blind") is True,
            "outcomes_locked": o2_manifest.get("fresh_forward_outcomes_accessed") is False,
            "marker_locked": o2_manifest.get("forward_outcome_access_marker_written") is False,
        }
        failed_o2 = sorted(name for name, passed in o2_checks.items() if not passed)
        if failed_o2:
            raise ForwardEvaluationBlocked(f"O2 manifest contract mismatch {session_key}: {failed_o2}")

        if declared:
            reliability_manifest = _read_json(
                Path(str(row.reliability_manifest_path)).resolve(),
                label="Reliability manifest",
            )
            reliability_checks = {
                "status": reliability_manifest.get("status") == "READY",
                "session_date": reliability_manifest.get("session_date") == session_key,
                "session_index": int(reliability_manifest.get("official_session_index", -1)) == int(row.session_index),
                "model_id": reliability_manifest.get("model_id") == RELIABILITY_MODEL_ID,
                "formula_version": reliability_manifest.get("formula_version") == RELIABILITY_FORMULA_VERSION,
                "spec_commit": reliability_manifest.get("spec_commit") == RELIABILITY_SPEC_COMMIT,
                "artifact_sha": reliability_manifest.get("reliability_artifact_sha256") == row.reliability_sha256,
                "o2_score_sha": reliability_manifest.get("o2_source_score_artifact_sha256") == row.o2_score_sha256,
                "o2_manifest_sha": reliability_manifest.get("o2_source_session_manifest_sha256") == row.o2_manifest_sha256,
                "o2_model_sha": reliability_manifest.get("o2_model_sha256") == O2_MODEL_SHA256,
                "o2_feature_sha": reliability_manifest.get("o2_feature_order_sha256") == O2_FEATURE_ORDER_SHA256,
                "outcome_access": reliability_manifest.get("outcome_access") == "LOCKED",
                "protected_flags": reliability_manifest.get("runtime_flags") == RELIABILITY_PROTECTED_FLAGS,
            }
            failed_reliability = sorted(name for name, passed in reliability_checks.items() if not passed)
            if failed_reliability:
                raise ForwardEvaluationBlocked(
                    f"Reliability manifest contract mismatch {session_key}: {failed_reliability}"
                )

    return data, bool(all(reliability_presence))


def _load_bound_o2_scores(sessions: pd.DataFrame) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    for row in sessions.itertuples(index=False):
        session = row.session_date
        path = Path(str(row.o2_score_path)).resolve()
        frame = _read_parquet(path, label="O2 score artifact")
        _require_columns(
            frame,
            {
                "ticker",
                "session_date",
                "o2_eligible",
                "score",
                "model_id",
                "model_sha256",
                "feature_order_sha256",
            },
            label="O2 score artifact",
        )
        dates = pd.to_datetime(frame["session_date"], errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
        if dates.isna().any() or not dates.eq(session).all():
            raise ForwardEvaluationBlocked(f"O2 score artifact date mismatch for {session.date().isoformat()}")
        if not frame["model_id"].astype(str).eq(O2_MODEL_ID).all():
            raise ForwardEvaluationBlocked("O2 score artifact model identity mismatch")
        if not frame["model_sha256"].astype(str).eq(O2_MODEL_SHA256).all():
            raise ForwardEvaluationBlocked("O2 score artifact model SHA mismatch")
        if not frame["feature_order_sha256"].astype(str).eq(O2_FEATURE_ORDER_SHA256).all():
            raise ForwardEvaluationBlocked("O2 score artifact feature-order SHA mismatch")
        piece = frame[["ticker", "o2_eligible", "score"]].copy()
        piece["date"] = session
        piece["session_index"] = int(row.session_index)
        pieces.append(piece[["ticker", "date", "session_index", "o2_eligible", "score"]])
    if not pieces:
        raise ForwardEvaluationBlocked("no O2 score artifacts loaded")
    return validate_o2_scores(pd.concat(pieces, ignore_index=True), sessions)


def _same_float(left: pd.Series, right: pd.Series) -> bool:
    a = pd.to_numeric(left, errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(right, errors="coerce").to_numpy(dtype=float)
    if len(a) != len(b):
        return False
    return bool(np.all((a == b) | (np.isnan(a) & np.isnan(b))))


def _load_bound_reliability(
    sessions: pd.DataFrame,
    o2_scores: pd.DataFrame,
) -> pd.DataFrame | None:
    pieces: list[pd.DataFrame] = []
    for row in sessions.itertuples(index=False):
        if not _text(row.reliability_path):
            continue
        session = row.session_date
        path = Path(str(row.reliability_path)).resolve()
        frame = _read_parquet(path, label="Reliability sidecar artifact")
        _require_columns(
            frame,
            {
                "ticker",
                "date",
                "session_index",
                "o2_eligible",
                "o2_score",
                "score_margin_reliability",
                "model_id",
                "formula_version",
            },
            label="Reliability sidecar artifact",
        )
        dates = pd.to_datetime(frame["date"], errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
        if dates.isna().any() or not dates.eq(session).all():
            raise ForwardEvaluationBlocked(f"Reliability artifact date mismatch for {session.date().isoformat()}")
        indices = pd.to_numeric(frame["session_index"], errors="coerce")
        if indices.isna().any() or not indices.astype(int).eq(int(row.session_index)).all():
            raise ForwardEvaluationBlocked("Reliability artifact session-index mismatch")
        if not frame["model_id"].astype(str).eq(RELIABILITY_MODEL_ID).all():
            raise ForwardEvaluationBlocked("Reliability artifact model identity mismatch")
        if not frame["formula_version"].astype(str).eq(RELIABILITY_FORMULA_VERSION).all():
            raise ForwardEvaluationBlocked("Reliability artifact formula-version mismatch")

        side = frame.copy()
        side["ticker"] = side["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
        if side["ticker"].eq("").any() or side["ticker"].duplicated().any():
            raise ForwardEvaluationBlocked("Reliability artifact ticker identity is invalid")
        source = o2_scores.loc[o2_scores["date"].eq(session), ["ticker", "o2_eligible", "score"]].copy()
        source = source.sort_values("ticker", kind="mergesort").reset_index(drop=True)
        side = side.sort_values("ticker", kind="mergesort").reset_index(drop=True)
        if source["ticker"].tolist() != side["ticker"].tolist():
            raise ForwardEvaluationBlocked("Reliability artifact support differs from exact O2 source support")
        if not source["o2_eligible"].astype(bool).reset_index(drop=True).equals(
            side["o2_eligible"].astype(bool).reset_index(drop=True)
        ):
            raise ForwardEvaluationBlocked("Reliability artifact O2 eligibility differs from source")
        if not _same_float(source["score"], side["o2_score"]):
            raise ForwardEvaluationBlocked("Reliability artifact O2 scores differ from hash-pinned source")

        piece = side[["ticker", "score_margin_reliability"]].copy()
        piece["date"] = session
        pieces.append(piece[["ticker", "date", "score_margin_reliability"]])

    if not pieces:
        return None
    reliability = pd.concat(pieces, ignore_index=True)
    if reliability.duplicated(["date", "ticker"]).any():
        raise ForwardEvaluationBlocked("Reliability bound inputs contain duplicate keys")
    return reliability


def _session_artifact_inventory(sessions: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in sessions.itertuples(index=False):
        declared = bool(_text(row.reliability_path))
        rows.append(
            {
                "date": row.session_date.date().isoformat(),
                "index": int(row.session_index),
                "o2_score_sha256": str(row.o2_score_sha256),
                "o2_manifest_sha256": str(row.o2_manifest_sha256),
                "reliability_sha256": str(row.reliability_sha256) if declared else None,
                "reliability_manifest_sha256": str(row.reliability_manifest_sha256) if declared else None,
            }
        )
    return rows


def run_guarded_synthetic_forward_evaluation(
    *,
    output_dir: Path,
    marker_root: Path,
    fixture_root: Path,
    protocol_path: Path,
    session_inventory: pd.DataFrame,
    shared_artifacts: Mapping[str, Mapping[str, str]],
    outcome_loader: Callable[[], pd.DataFrame],
    code_commit: str,
    event_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run the frozen evaluator on synthetic data with real-contract provenance guards.

    Score and Reliability inputs are loaded directly from the exact hash-pinned
    artifact paths in the 100-session inventory. Callers cannot inject an
    alternate in-memory score/sidecar frame. The frozen protocol hash is a
    module constant and cannot be overridden by a caller.
    """

    output_dir = Path(output_dir)
    fixture_root = Path(fixture_root).resolve()
    marker_root = Path(marker_root)
    protocol_path = Path(protocol_path)
    if not re.fullmatch(r"[0-9a-f]{40}", str(code_commit)):
        raise ForwardEvaluationBlocked("evaluator code commit must be a full 40-hex commit SHA")
    if (marker_root / REAL_FORWARD_MARKER).exists():
        raise ForwardEvaluationBlocked("real forward marker exists; synthetic runner refuses this location")
    if (marker_root / SYNTHETIC_MARKER).exists():
        raise ForwardEvaluationBlocked(f"synthetic one-shot already consumed: {marker_root / SYNTHETIC_MARKER}")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ForwardEvaluationBlocked("synthetic output directory must be new or empty")
    if not protocol_path.is_file() or sha256_file(protocol_path) != PROTOCOL_SHA256:
        raise ForwardEvaluationBlocked("frozen protocol hash mismatch")

    sessions, reliability_complete = validate_guarded_session_inventory(
        session_inventory,
        fixture_root=fixture_root,
    )
    verified_shared_artifacts = validate_named_artifacts(shared_artifacts, fixture_root=fixture_root)
    scores = _load_bound_o2_scores(sessions)
    reliability = _load_bound_reliability(sessions, scores)
    reliability_pre_outcome_disposition = (
        "READY_FOR_FROZEN_RELIABILITY_EVALUATION"
        if reliability_complete
        else "RELIABILITY_FORWARD_INCONCLUSIVE_DATA"
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = output_dir / "session_identity_inventory.parquet"
    write_parquet_atomic(sessions, inventory_path)
    pre_payload = {
        "schema": "idx-trade/forward-100-pre-outcome-contract-guarded-v1",
        "status": "SYNTHETIC_PRE_OUTCOME_CONTRACT_READY",
        "protocol_status": PROTOCOL_STATUS,
        "protocol_path": str(protocol_path),
        "protocol_sha256": PROTOCOL_SHA256,
        "protocol_commit": PROTOCOL_COMMIT,
        "evaluator_code_commit": code_commit,
        "evaluator_entrypoint": "forward_100_evaluator_guarded.run_guarded_synthetic_forward_evaluation",
        "supersedes_entrypoint": SUPERSEDES_UNGUARDED_ENTRYPOINT,
        "o2_model_sha256": O2_MODEL_SHA256,
        "o2_feature_order_sha256": O2_FEATURE_ORDER_SHA256,
        "sessions": [
            {"date": row.session_date.date().isoformat(), "index": int(row.session_index)}
            for row in sessions.itertuples(index=False)
        ],
        "session_artifacts": _session_artifact_inventory(sessions),
        "session_inventory_sha256": sha256_file(inventory_path),
        "shared_artifacts": verified_shared_artifacts,
        "source_artifact_hashes_verified": True,
        "evaluated_inputs_loaded_from_hash_pinned_artifacts": True,
        "reliability_sidecars_complete": reliability_complete,
        "reliability_pre_outcome_disposition": reliability_pre_outcome_disposition,
        "synthetic_fixture_only": True,
        "protected_forward_outcomes_accessed": False,
        "real_forward_marker_written": False,
        "runtime_flags": {
            "provider_call": False,
            "model_refit": False,
            "threshold_optimization": False,
            "second_counter": False,
            "o2_1_evaluation": False,
            "pre_marker_outcome_access": False,
        },
        "environment": environment_manifest(
            source_paths=[Path(__file__), protocol_path],
            config={"phase": "SYNTHETIC_FORWARD_100_EVALUATOR_GUARDED", "protected_outcomes": False},
        ),
    }
    pre_payload["content_sha256"] = _canonical_hash(pre_payload)
    pre_path = output_dir / "pre_outcome_contract.json"
    _write_json(pre_path, pre_payload)
    if event_hook:
        event_hook("pre_outcome_manifest_written")

    marker = _write_synthetic_marker(
        marker_root,
        pre_manifest_sha256=sha256_file(pre_path),
        sessions=sessions,
    )
    if event_hook:
        event_hook("synthetic_marker_written")
    outcomes = outcome_loader()
    if event_hook:
        event_hook("outcome_loader_returned")

    outcome_frame = materialize_outcome_frame(scores, outcomes)
    o2_result = evaluate_o2(outcome_frame, sessions, provenance_and_maturity_pass=True)
    reliability_rows, reliability_sessions, reliability_result = evaluate_reliability(
        outcome_frame,
        reliability,
        sessions,
        sidecars_valid_and_complete=reliability_complete,
    )
    if not reliability_complete and reliability_result["decision"] != "RELIABILITY_FORWARD_INCONCLUSIVE_DATA":
        raise ForwardEvaluationBlocked("missing Reliability sidecars did not remain INCONCLUSIVE_DATA")
    joint = joint_interpretation(o2_result["decision"], reliability_result["decision"])

    artifact_paths = {
        "session_identity_inventory": inventory_path,
        "pre_outcome_contract": pre_path,
        "resolved_unresolved_outcomes": output_dir / "resolved_unresolved_outcomes.parquet",
        "o2_aggregate_metrics": output_dir / "o2_aggregate_metrics.json",
        "o2_half_metrics": output_dir / "o2_half_metrics.json",
        "o2_decision": output_dir / "o2_decision.json",
        "reliability_rows": output_dir / "reliability_rows.parquet",
        "reliability_sessions": output_dir / "reliability_sessions.parquet",
        "reliability_aggregate_metrics": output_dir / "reliability_aggregate_metrics.json",
        "reliability_decision": output_dir / "reliability_decision.json",
        "joint_interpretation": output_dir / "joint_interpretation.json",
        "runtime_flags": output_dir / "runtime_flags.json",
    }
    write_parquet_atomic(outcome_frame, artifact_paths["resolved_unresolved_outcomes"])
    _write_json(artifact_paths["o2_aggregate_metrics"], o2_result["aggregate"])
    _write_json(
        artifact_paths["o2_half_metrics"],
        {"first_50": o2_result["first_50"], "last_50": o2_result["last_50"]},
    )
    _write_json(
        artifact_paths["o2_decision"],
        {key: value for key, value in o2_result.items() if key not in {"aggregate", "first_50", "last_50"}},
    )
    write_parquet_atomic(reliability_rows, artifact_paths["reliability_rows"])
    write_parquet_atomic(reliability_sessions, artifact_paths["reliability_sessions"])
    _write_json(
        artifact_paths["reliability_aggregate_metrics"],
        {
            "aggregate": reliability_result["aggregate"],
            "first_50": reliability_result["first_50"],
            "last_50": reliability_result["last_50"],
        },
    )
    _write_json(artifact_paths["reliability_decision"], reliability_result)
    _write_json(artifact_paths["joint_interpretation"], joint)
    runtime_flags = {
        "synthetic_fixture_only": True,
        "real_forward_marker_written": False,
        "protected_forward_outcomes_accessed": False,
        "provider_call": False,
        "model_refit": False,
        "threshold_optimization": False,
        "second_counter": False,
        "o2_1_evaluated": False,
        "evaluated_inputs_loaded_from_hash_pinned_artifacts": True,
        "reliability_pre_outcome_disposition": reliability_pre_outcome_disposition,
        "synthetic_marker_path": str(marker),
        "synthetic_marker_sha256": sha256_file(marker),
    }
    _write_json(artifact_paths["runtime_flags"], runtime_flags)
    hashes = {name: sha256_file(path) for name, path in sorted(artifact_paths.items())}
    manifest = {
        "schema": GUARDED_SCHEMA,
        "status": "SYNTHETIC_FORWARD_100_EVALUATION_COMPLETE",
        "evaluator_entrypoint": "forward_100_evaluator_guarded.run_guarded_synthetic_forward_evaluation",
        "artifacts": {
            name: {"path": str(artifact_paths[name]), "sha256": hashes[name]}
            for name in sorted(hashes)
        },
        "o2_decision": o2_result["decision"],
        "reliability_decision": reliability_result["decision"],
        "runtime_flags": runtime_flags,
    }
    manifest["content_sha256"] = _canonical_hash(manifest)
    final_manifest = output_dir / "artifact_manifest.json"
    _write_json(final_manifest, manifest)
    return {
        "status": manifest["status"],
        "o2": o2_result,
        "reliability": reliability_result,
        "joint": joint,
        "reliability_pre_outcome_disposition": reliability_pre_outcome_disposition,
        "artifact_manifest_path": str(final_manifest),
        "artifact_manifest_sha256": sha256_file(final_manifest),
        "synthetic_marker_path": str(marker),
    }
