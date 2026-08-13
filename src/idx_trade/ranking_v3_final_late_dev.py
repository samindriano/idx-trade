from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .provenance import sha256_file
from .ranking_v2_candidate import _assert_clean_output_dir, _normalize_candidate_table
from .ranking_v3_structure_lite import (
    CALENDAR_SHA256,
    PANEL_SHA256,
    SECURITY_MASTER_SHA256,
    STRUCTURE_ADDENDUM_GIT_BLOB,
    STRUCTURE_SPEC_GIT_BLOB,
    STRUCTURE_SPEC_SHA256,
    V2_MANIFEST_SHA256,
    V2_PREPARED_SHA256,
    V3_B_CANDIDATE,
    V3_B_CONTROL,
    V3_B_FEATURE_COLUMNS,
    _feature_order_hash,
    _normalized_git_blob_sha1,
    _normalized_sha256,
    _read_calendar,
    _structure_model,
)
from .research_stage5 import assign_within_date_buckets
from .research_v2_features import V2_FULL_FEATURE_COLUMNS
from .research_v2_models import HGB_XS_MARKET, candidate_feature_columns, pointwise_model, pointwise_raw_score
from .research_v2_validation import RANKING_V2_FOLDS, RankingV2Fold, evaluate_v2_scores, split_v2_model_table
from .research_v3_structure_lite import STRUCTURE_LITE_FEATURE_COLUMNS, build_structure_lite_features
from .stage5_ranking_holdout import _assert_environment


LATE_FOLDS: tuple[RankingV2Fold, ...] = tuple(RANKING_V2_FOLDS[4:])
LATE_FOLD_NAMES = tuple(fold.name for fold in LATE_FOLDS)
MAX_LATE_SIGNAL_INDEX = 1224
SEALED_AFTER_LATE = 1225

V2_REFERENCE_SUMMARY_SHA256 = "24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d"
V2_REFERENCE_PREDICTIONS_SHA256 = "5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179"

LATE_SPEC_SHA256 = "c1acbe99656b0a0a0adabc7840ad779ee0553b59b7441a24607a53322d1b369f"
LATE_SPEC_GIT_BLOB = "08eba22b5f36efb160cc01abbfb5cb82d079f36e"
LATE_ADDENDUM_SHA256 = "fa6c856f6cc45714b8ba5b4817a06fab2f9141fe66be7982c0c2a30ee1fd799e"
LATE_ADDENDUM_GIT_BLOB = "8ae7147af61c9aeaf9993576cac198c8ab8c9387"

CONTROL_SCORE_ATOL = 1e-12
METRIC_ATOL = 1e-12
MEDIAN_PR_CONFIRM = 0.001
ROC_NONINFERIORITY = -0.005

METRIC_COLUMNS = (
    "positive_rate",
    "pr_auc",
    "pr_auc_delta_vs_base",
    "roc_auc",
    "q1_tp_rate",
    "q5_tp_rate",
    "q5_minus_q1",
    "top_decile_tp_rate",
    "top_decile_lift",
)


def assert_late_fold_allowed(name: str) -> None:
    if name not in LATE_FOLD_NAMES:
        raise PermissionError(f"{name} is not authorized for final V3 late-development confirmation")


def _git_blob_sha1(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _assert_contract_files(
    *,
    structure_spec_path: Path,
    structure_addendum_path: Path,
    late_spec_path: Path,
    late_addendum_path: Path,
) -> dict[str, str]:
    identities = {
        "structure_spec_sha256": _normalized_sha256(structure_spec_path),
        "structure_spec_git_blob": _normalized_git_blob_sha1(structure_spec_path),
        "structure_addendum_git_blob": _normalized_git_blob_sha1(structure_addendum_path),
        "late_spec_sha256": _normalized_sha256(late_spec_path),
        "late_spec_git_blob": _normalized_git_blob_sha1(late_spec_path),
        "late_addendum_sha256": _normalized_sha256(late_addendum_path),
        "late_addendum_git_blob": _normalized_git_blob_sha1(late_addendum_path),
    }
    expected = {
        "structure_spec_sha256": STRUCTURE_SPEC_SHA256,
        "structure_spec_git_blob": STRUCTURE_SPEC_GIT_BLOB,
        "structure_addendum_git_blob": STRUCTURE_ADDENDUM_GIT_BLOB,
        "late_spec_sha256": LATE_SPEC_SHA256,
        "late_spec_git_blob": LATE_SPEC_GIT_BLOB,
        "late_addendum_sha256": LATE_ADDENDUM_SHA256,
        "late_addendum_git_blob": LATE_ADDENDUM_GIT_BLOB,
    }
    for key, value in expected.items():
        if identities[key] != value:
            raise RuntimeError(f"final V3 late-dev contract mismatch {key}: expected={value} actual={identities[key]}")
    return identities


def _read_v2_late_subset(path: Path) -> pd.DataFrame:
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise RuntimeError("late-development confirmation requires frozen V2 prepared Parquet")
    frame = pd.read_parquet(path, filters=[("signal_session_index", "<=", MAX_LATE_SIGNAL_INDEX)])
    if frame.empty:
        raise RuntimeError("late-development V2 subset is empty")
    values = pd.to_numeric(frame["signal_session_index"], errors="raise").astype(int)
    if int(values.max()) > MAX_LATE_SIGNAL_INDEX:
        raise RuntimeError("late-development prepared read materialized session 1225+")
    return frame


def _read_panel_late_bounded(path: Path, max_date: pd.Timestamp) -> pd.DataFrame:
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise RuntimeError("late-development Structure-Lite panel must be Parquet for physical date filtering")
    frame = pd.read_parquet(path, filters=[("date", "<=", max_date)])
    if frame.empty:
        raise RuntimeError("late-development signal panel subset is empty")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    if (frame["date"] > max_date).any():
        raise RuntimeError("late-development panel materialized post-boundary dates")
    return frame


def _coverage_report(cache: pd.DataFrame) -> dict[str, Any]:
    overall: dict[str, Any] = {}
    for column in STRUCTURE_LITE_FEATURE_COLUMNS:
        values = pd.to_numeric(cache[column], errors="coerce")
        finite = np.isfinite(values.to_numpy(dtype=float))
        overall[column] = {
            "rows": int(len(values)),
            "finite_rows": int(finite.sum()),
            "finite_rate": float(finite.mean()) if len(values) else 0.0,
            "missing_rate": float(1.0 - finite.mean()) if len(values) else 1.0,
        }
    validation: dict[str, dict[str, Any]] = {}
    indices = pd.to_numeric(cache["signal_session_index"], errors="raise").astype(int)
    for fold in LATE_FOLDS:
        block = cache[indices.between(fold.validation_start, fold.validation_end)]
        validation[fold.name] = {
            "rows": int(len(block)),
            "dates": int(block["date"].nunique()),
            "tickers": int(block["ticker"].nunique()),
            "finite_rate": {
                column: float(
                    np.isfinite(pd.to_numeric(block[column], errors="coerce").to_numpy(dtype=float)).mean()
                )
                for column in STRUCTURE_LITE_FEATURE_COLUMNS
            },
        }
    return {"overall": overall, "late_validation": validation}


def prepare_late_cache(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    v2_prepared_path: Path,
    v2_manifest_path: Path,
    structure_spec_path: Path,
    structure_addendum_path: Path,
    late_spec_path: Path,
    late_addendum_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    _assert_clean_output_dir(output_dir)
    contract = _assert_contract_files(
        structure_spec_path=structure_spec_path,
        structure_addendum_path=structure_addendum_path,
        late_spec_path=late_spec_path,
        late_addendum_path=late_addendum_path,
    )
    source_hashes = {
        "panel": sha256_file(panel_path),
        "calendar": sha256_file(calendar_path),
        "security_master": sha256_file(security_master_path),
        "v2_prepared": sha256_file(v2_prepared_path),
        "v2_manifest": sha256_file(v2_manifest_path),
    }
    expected = {
        "panel": PANEL_SHA256,
        "calendar": CALENDAR_SHA256,
        "security_master": SECURITY_MASTER_SHA256,
        "v2_prepared": V2_PREPARED_SHA256,
        "v2_manifest": V2_MANIFEST_SHA256,
    }
    if source_hashes != expected:
        raise RuntimeError(f"late-development source hash mismatch: expected={expected} actual={source_hashes}")

    sessions = _read_calendar(calendar_path)
    if len(sessions) < MAX_LATE_SIGNAL_INDEX:
        raise RuntimeError("official calendar does not cover session 1224")
    max_date = pd.Timestamp(sessions[MAX_LATE_SIGNAL_INDEX - 1])

    panel = _read_panel_late_bounded(panel_path, max_date)
    structure = build_structure_lite_features(
        panel,
        sessions,
        max_signal_session_index=MAX_LATE_SIGNAL_INDEX,
    )
    if int(pd.to_numeric(structure["signal_session_index"], errors="raise").max()) > MAX_LATE_SIGNAL_INDEX:
        raise RuntimeError("Structure-Lite builder escaped final late-development boundary")

    v2_raw = _read_v2_late_subset(v2_prepared_path)
    v2 = _normalize_candidate_table(v2_raw, HGB_XS_MARKET)
    if int(v2["signal_session_index"].max()) > MAX_LATE_SIGNAL_INDEX:
        raise RuntimeError("normalized V2 table escaped final late-development boundary")

    structure_keyed = structure.set_index(["ticker", "date"])
    keys = pd.MultiIndex.from_frame(v2[["ticker", "date"]])
    if not keys.is_unique:
        raise RuntimeError("late-development V2 keys are not unique")
    missing = keys.difference(structure_keyed.index)
    if len(missing):
        raise RuntimeError(f"late-development Structure-Lite join has {len(missing)} orphan V2 rows")

    joined = v2.copy()
    aligned = structure_keyed.reindex(keys)
    for column in STRUCTURE_LITE_FEATURE_COLUMNS:
        joined[column] = aligned[column].to_numpy()

    original_columns = list(v2.columns)
    if not joined.loc[:, original_columns].equals(v2.loc[:, original_columns]):
        raise RuntimeError("late-development cache changed existing V2 columns")
    if tuple(V3_B_FEATURE_COLUMNS[: len(V2_FULL_FEATURE_COLUMNS)]) != tuple(V2_FULL_FEATURE_COLUMNS):
        raise RuntimeError("late-development candidate does not preserve exact V2 feature prefix")
    if tuple(V3_B_FEATURE_COLUMNS) != tuple((*V2_FULL_FEATURE_COLUMNS, *STRUCTURE_LITE_FEATURE_COLUMNS)):
        raise RuntimeError("late-development candidate feature order differs from frozen V3-B")
    if joined.duplicated(["ticker", "date"]).any():
        raise RuntimeError("late-development cache contains duplicate ticker/date rows")

    for column in STRUCTURE_LITE_FEATURE_COLUMNS:
        values = pd.to_numeric(joined[column], errors="coerce").to_numpy(dtype=float)
        if np.isinf(values).any():
            raise RuntimeError(f"late-development structure feature contains infinity: {column}")

    cache_path = output_dir / "ranking_v3_final_structure_lite_late_dev_cache.parquet"
    joined.to_parquet(cache_path, index=False)
    coverage = _coverage_report(joined)
    manifest = {
        "status": "RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CACHE_FROZEN",
        "code_commit": code_commit,
        "source_sha256": source_hashes,
        "contract_identity": contract,
        "cache_path": str(cache_path),
        "cache_sha256": sha256_file(cache_path),
        "rows": int(len(joined)),
        "tickers": int(joined["ticker"].nunique()),
        "first_signal_session_index": int(joined["signal_session_index"].min()),
        "last_signal_session_index": int(joined["signal_session_index"].max()),
        "v2_feature_columns": list(V2_FULL_FEATURE_COLUMNS),
        "structure_feature_columns": list(STRUCTURE_LITE_FEATURE_COLUMNS),
        "candidate_feature_columns": list(V3_B_FEATURE_COLUMNS),
        "candidate_feature_order_sha256": _feature_order_hash(tuple(V3_B_FEATURE_COLUMNS)),
        "coverage": coverage,
        "late_folds_materialized": list(LATE_FOLD_NAMES),
        "post_1224_materialized": False,
        "outcome_metrics_computed": False,
        "fresh_forward_accessed": False,
        "independent_validation_claim": False,
    }
    manifest_path = output_dir / "ranking_v3_final_structure_lite_late_dev_cache_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest


def _assert_late_cache(
    *,
    cache_path: Path,
    manifest_path: Path,
    structure_spec_path: Path,
    structure_addendum_path: Path,
    late_spec_path: Path,
    late_addendum_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, str]]:
    contract = _assert_contract_files(
        structure_spec_path=structure_spec_path,
        structure_addendum_path=structure_addendum_path,
        late_spec_path=late_spec_path,
        late_addendum_path=late_addendum_path,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CACHE_FROZEN":
        raise RuntimeError("late-development cache manifest is not frozen")
    if bool(manifest.get("outcome_metrics_computed", True)):
        raise RuntimeError("late-development prepare manifest unexpectedly contains outcomes")
    if bool(manifest.get("post_1224_materialized", True)):
        raise RuntimeError("late-development manifest claims session 1225+ materialization")
    actual_cache = sha256_file(cache_path)
    if actual_cache != manifest.get("cache_sha256"):
        raise RuntimeError("late-development cache SHA mismatch")
    table = pd.read_parquet(cache_path)
    table = _normalize_candidate_table(table, HGB_XS_MARKET)
    maximum = int(pd.to_numeric(table["signal_session_index"], errors="raise").max())
    if maximum > MAX_LATE_SIGNAL_INDEX:
        raise RuntimeError("late-development cache contains session 1225+")
    required = set(STRUCTURE_LITE_FEATURE_COLUMNS)
    if not required.issubset(table.columns):
        raise RuntimeError(f"late-development cache missing structure columns: {sorted(required - set(table.columns))}")
    return table, manifest, {"cache": actual_cache, "manifest": sha256_file(manifest_path), **contract}


def _read_late_reference(reference_dir: Path) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, str]]:
    summary_path = reference_dir / "ranking_v2_hgb_xs_market_summary.json"
    predictions_path = reference_dir / "ranking_v2_hgb_xs_market_predictions.parquet"
    if not summary_path.is_file() or not predictions_path.is_file():
        raise FileNotFoundError("frozen V2 reference artifacts missing")
    actual_hashes = {
        "summary": sha256_file(summary_path),
        "predictions": sha256_file(predictions_path),
    }
    if actual_hashes["summary"] != V2_REFERENCE_SUMMARY_SHA256:
        raise RuntimeError("frozen V2 reference summary SHA mismatch")
    if actual_hashes["predictions"] != V2_REFERENCE_PREDICTIONS_SHA256:
        raise RuntimeError("frozen V2 reference predictions SHA mismatch")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "RANKING_V2_CANDIDATE_COMPLETE":
        raise RuntimeError("frozen V2 reference summary is not complete")
    if summary.get("candidate") != HGB_XS_MARKET:
        raise RuntimeError("frozen V2 reference is not HGB_XS_MARKET")
    if summary.get("prepared_cache_sha256") != V2_PREPARED_SHA256:
        raise RuntimeError("frozen V2 reference prepared cache mismatch")
    if tuple(summary.get("feature_columns", [])) != tuple(candidate_feature_columns(HGB_XS_MARKET)):
        raise RuntimeError("frozen V2 reference feature order mismatch")

    predictions = pd.read_parquet(predictions_path, filters=[("fold", "in", list(LATE_FOLD_NAMES))])
    predictions = predictions[predictions["fold"].isin(LATE_FOLD_NAMES)].copy().reset_index(drop=True)
    if tuple(dict.fromkeys(predictions["fold"].astype(str))) != LATE_FOLD_NAMES:
        raise RuntimeError("frozen V2 reference did not materialize exactly F5/F6")

    metric_rows = []
    for fold in LATE_FOLDS:
        block = predictions[predictions["fold"].eq(fold.name)].copy().reset_index(drop=True)
        if block.empty:
            raise RuntimeError(f"frozen V2 reference missing {fold.name}")
        metric_rows.append({"fold": fold.name, **evaluate_v2_scores(block, block["score"].to_numpy(dtype=float))})
    return summary, pd.DataFrame(metric_rows), predictions, actual_hashes


def _normalize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["fold", "ticker", "date", "signal_session_index", "binary_target"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise RuntimeError(f"late-development predictions missing identity columns: {sorted(missing)}")
    out = frame[required].copy()
    out["ticker"] = out["ticker"].astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    out["signal_session_index"] = pd.to_numeric(out["signal_session_index"], errors="raise").astype(int)
    out["binary_target"] = pd.to_numeric(out["binary_target"], errors="raise").astype(int)
    return out.reset_index(drop=True)


def prove_late_control_equivalence(
    *,
    control_metrics: pd.DataFrame,
    control_predictions: pd.DataFrame,
    reference_metrics: pd.DataFrame,
    reference_predictions: pd.DataFrame,
    reference_hashes: dict[str, str],
) -> dict[str, Any]:
    new = control_predictions[control_predictions["fold"].isin(LATE_FOLD_NAMES)].copy().reset_index(drop=True)
    ref = reference_predictions[reference_predictions["fold"].isin(LATE_FOLD_NAMES)].copy().reset_index(drop=True)
    if len(new) != len(ref):
        raise RuntimeError("late-development control row count differs from frozen V2")
    if not _normalize_identity(new).equals(_normalize_identity(ref)):
        raise RuntimeError("late-development control row identity/order differs from frozen V2")
    new_score = pd.to_numeric(new["score"], errors="raise").to_numpy(dtype=float)
    ref_score = pd.to_numeric(ref["score"], errors="raise").to_numpy(dtype=float)
    if not np.allclose(new_score, ref_score, rtol=0.0, atol=CONTROL_SCORE_ATOL, equal_nan=False):
        raise RuntimeError(
            f"late-development control score equivalence failed: max={float(np.max(np.abs(new_score-ref_score)))}"
        )
    left = control_metrics.set_index("fold")
    right = reference_metrics.set_index("fold")
    if tuple(left.index) != LATE_FOLD_NAMES or tuple(right.index) != LATE_FOLD_NAMES:
        raise RuntimeError("late-development control metric fold order mismatch")
    metric_diff: dict[str, float] = {}
    for column in METRIC_COLUMNS:
        a = pd.to_numeric(left[column], errors="raise").to_numpy(dtype=float)
        b = pd.to_numeric(right[column], errors="raise").to_numpy(dtype=float)
        maximum = float(np.max(np.abs(a - b)))
        metric_diff[column] = maximum
        if not np.allclose(a, b, rtol=0.0, atol=METRIC_ATOL, equal_nan=False):
            raise RuntimeError(f"late-development control metric equivalence failed {column}: max={maximum}")
    return {
        "status": "V3_FINAL_LATE_DEV_CONTROL_EQUIVALENCE_PASS",
        "folds": list(LATE_FOLD_NAMES),
        "row_count": int(len(new)),
        "max_score_abs_diff": float(np.max(np.abs(new_score - ref_score))) if len(new_score) else 0.0,
        "max_metric_abs_diff": metric_diff,
        "reference_artifact_sha256": reference_hashes,
    }


def _score_candidate(
    table: pd.DataFrame,
    candidate: str,
    *,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    if candidate not in {V3_B_CONTROL, V3_B_CANDIDATE}:
        raise ValueError(f"unknown final V3 late-development candidate: {candidate}")
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    for fold in LATE_FOLDS:
        assert_late_fold_allowed(fold.name)
        train, validation = split_v2_model_table(table, fold)
        model = pointwise_model(HGB_XS_MARKET) if candidate == V3_B_CONTROL else _structure_model()
        model.fit(train, train["binary_target"].to_numpy(dtype=int))
        score = pointwise_raw_score(model, validation)
        if not np.isfinite(score).all():
            raise RuntimeError(f"{candidate} {fold.name} produced non-finite scores")
        metrics_rows.append(
            {
                "candidate": candidate,
                "fold": fold.name,
                "train_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                "validation_dates": int(validation["date"].nunique()),
                "validation_tickers": int(validation["ticker"].nunique()),
                **evaluate_v2_scores(validation, score),
            }
        )
        scored = validation[["ticker", "date", "signal_session_index", "binary_target"]].copy()
        scored.insert(0, "fold", fold.name)
        scored.insert(0, "candidate", candidate)
        scored["score"] = score
        prediction_rows.append(scored)
        model_path = output_dir / f"ranking_v3_final_{candidate.lower()}_{fold.name.lower()}.joblib"
        joblib.dump(model, model_path)
        model_hashes[model_path.name] = sha256_file(model_path)
    return pd.DataFrame(metrics_rows), pd.concat(prediction_rows, ignore_index=True), model_hashes


def _absolute_gate(candidate_metrics: pd.DataFrame) -> tuple[bool, dict[str, Any]]:
    metrics = candidate_metrics.set_index("fold")
    if tuple(metrics.index) != LATE_FOLD_NAMES:
        raise RuntimeError("late-development absolute gate requires F5/F6 exactly")
    pr = pd.to_numeric(metrics["pr_auc_delta_vs_base"], errors="raise").to_numpy(dtype=float)
    roc = pd.to_numeric(metrics["roc_auc"], errors="raise").to_numpy(dtype=float)
    spread = pd.to_numeric(metrics["q5_minus_q1"], errors="raise").to_numpy(dtype=float)
    finite = bool(np.isfinite(np.concatenate([pr, roc, spread])).all())
    detail = {
        "all_required_finite": finite,
        "positive_pr_both": bool(np.all(pr > 0.0)),
        "roc_gt_half_both": bool(np.all(roc > 0.5)),
        "positive_q5_q1_both": bool(np.all(spread > 0.0)),
    }
    return bool(all(detail.values())), detail


def _paired_confirmation(
    candidate_metrics: pd.DataFrame,
    control_metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any], bool]:
    candidate = candidate_metrics.set_index("fold")
    control = control_metrics.set_index("fold")
    if tuple(candidate.index) != LATE_FOLD_NAMES or tuple(control.index) != LATE_FOLD_NAMES:
        raise RuntimeError("late-development paired gate requires F5/F6 exactly")
    paired = pd.DataFrame(index=LATE_FOLD_NAMES)
    paired.index.name = "fold"
    paired["pr_auc_delta_improvement"] = (
        pd.to_numeric(candidate["pr_auc_delta_vs_base"], errors="raise")
        - pd.to_numeric(control["pr_auc_delta_vs_base"], errors="raise")
    )
    paired["roc_auc_change"] = (
        pd.to_numeric(candidate["roc_auc"], errors="raise") - pd.to_numeric(control["roc_auc"], errors="raise")
    )
    paired["q5_minus_q1_change"] = (
        pd.to_numeric(candidate["q5_minus_q1"], errors="raise")
        - pd.to_numeric(control["q5_minus_q1"], errors="raise")
    )
    paired["top_decile_lift_change"] = (
        pd.to_numeric(candidate["top_decile_lift"], errors="raise")
        - pd.to_numeric(control["top_decile_lift"], errors="raise")
    )
    pr = paired["pr_auc_delta_improvement"].to_numpy(dtype=float)
    roc = paired["roc_auc_change"].to_numpy(dtype=float)
    spread = paired["q5_minus_q1_change"].to_numpy(dtype=float)
    top = paired["top_decile_lift_change"].to_numpy(dtype=float)
    summary = {
        "pr_nonnegative_both": bool(np.all(pr >= 0.0)),
        "median_pr_auc_delta_improvement": float(np.median(pr)),
        "worst_pr_auc_delta_improvement": float(np.min(pr)),
        "median_roc_auc_change": float(np.median(roc)),
        "q5_q1_nonnegative_both": bool(np.all(spread >= 0.0)),
        "median_q5_minus_q1_change": float(np.median(spread)),
        "worst_q5_minus_q1_change": float(np.min(spread)),
        "median_top_decile_lift_change": float(np.median(top)),
    }
    passed = bool(
        summary["pr_nonnegative_both"]
        and summary["median_pr_auc_delta_improvement"] >= MEDIAN_PR_CONFIRM
        and summary["median_roc_auc_change"] >= ROC_NONINFERIORITY
        and summary["q5_q1_nonnegative_both"]
    )
    return paired.reset_index(), summary, passed


def _top_decile_overlap(
    control_predictions: pd.DataFrame,
    candidate_predictions: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for fold in LATE_FOLD_NAMES:
        control = control_predictions[control_predictions["fold"].eq(fold)].copy().reset_index(drop=True)
        candidate = candidate_predictions[candidate_predictions["fold"].eq(fold)].copy().reset_index(drop=True)
        identity = ["ticker", "date", "signal_session_index", "binary_target"]
        if not control[identity].equals(candidate[identity]):
            raise RuntimeError(f"late-development top-decile identity mismatch for {fold}")
        control_bucket = assign_within_date_buckets(control, score_column="score", buckets=10, output_column="decile")
        candidate_bucket = assign_within_date_buckets(candidate, score_column="score", buckets=10, output_column="decile")
        left = control_bucket[control_bucket["decile"].eq(10)]
        right = candidate_bucket[candidate_bucket["decile"].eq(10)]
        left_keys = set(zip(left["date"], left["ticker"], strict=False))
        right_keys = set(zip(right["date"], right["ticker"], strict=False))
        union = left_keys | right_keys
        overlap = left_keys & right_keys
        rows.append(
            {
                "fold": fold,
                "jaccard": float(len(overlap) / len(union)) if union else 1.0,
                "overlap_rows": int(len(overlap)),
                "entrants": int(len(right_keys - left_keys)),
                "exits": int(len(left_keys - right_keys)),
            }
        )
    return pd.DataFrame(rows)


def run_late_confirmation(
    *,
    cache_path: Path,
    cache_manifest_path: Path,
    reference_v2_dir: Path,
    structure_spec_path: Path,
    structure_addendum_path: Path,
    late_spec_path: Path,
    late_addendum_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    environment = _assert_environment()
    _assert_clean_output_dir(output_dir)
    table, cache_manifest, contract_hashes = _assert_late_cache(
        cache_path=cache_path,
        manifest_path=cache_manifest_path,
        structure_spec_path=structure_spec_path,
        structure_addendum_path=structure_addendum_path,
        late_spec_path=late_spec_path,
        late_addendum_path=late_addendum_path,
    )

    reference_summary, reference_metrics, reference_predictions, reference_hashes = _read_late_reference(
        reference_v2_dir
    )

    control_dir = output_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=False)
    control_started = time.perf_counter()
    control_metrics, control_predictions, control_models = _score_candidate(
        table, V3_B_CONTROL, output_dir=control_dir
    )
    control_seconds = time.perf_counter() - control_started

    equivalence = prove_late_control_equivalence(
        control_metrics=control_metrics,
        control_predictions=control_predictions,
        reference_metrics=reference_metrics,
        reference_predictions=reference_predictions,
        reference_hashes=reference_hashes,
    )
    equivalence["reference_summary_identity"] = {
        "sha256": reference_hashes["summary"],
        "code_commit": reference_summary.get("code_commit"),
    }
    equivalence_path = output_dir / "ranking_v3_final_late_dev_control_equivalence.json"
    equivalence_path.write_text(json.dumps(equivalence, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    candidate_dir = output_dir / "structure_lite"
    candidate_dir.mkdir(parents=True, exist_ok=False)
    candidate_started = time.perf_counter()
    candidate_metrics, candidate_predictions, candidate_models = _score_candidate(
        table, V3_B_CANDIDATE, output_dir=candidate_dir
    )
    candidate_seconds = time.perf_counter() - candidate_started

    absolute_pass, absolute_detail = _absolute_gate(candidate_metrics)
    paired_frame, paired_summary, paired_pass = _paired_confirmation(candidate_metrics, control_metrics)
    overlap = _top_decile_overlap(control_predictions, candidate_predictions)

    if absolute_pass and paired_pass:
        decision = "V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS"
        final_architecture = V3_B_CANDIDATE
    else:
        decision = "V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2"
        final_architecture = HGB_XS_MARKET

    metrics_path = output_dir / "ranking_v3_final_structure_lite_f5_f6_metrics.csv"
    predictions_path = output_dir / "ranking_v3_final_structure_lite_f5_f6_predictions.parquet"
    paired_path = output_dir / "ranking_v3_final_structure_lite_f5_f6_paired.csv"
    overlap_path = output_dir / "ranking_v3_final_structure_lite_f5_f6_top_decile_overlap.csv"
    aggregate_path = output_dir / "ranking_v3_final_structure_lite_f5_f6_aggregate.json"
    verdict_path = output_dir / "ranking_v3_final_structure_lite_f5_f6_verdict.json"
    runtime_path = output_dir / "ranking_v3_final_structure_lite_f5_f6_runtime.json"

    pd.concat([control_metrics, candidate_metrics], ignore_index=True).to_csv(metrics_path, index=False)
    pd.concat([control_predictions, candidate_predictions], ignore_index=True).to_parquet(predictions_path, index=False)
    paired_frame.to_csv(paired_path, index=False)
    overlap.to_csv(overlap_path, index=False)

    aggregate = {
        "absolute_gate_pass": absolute_pass,
        "absolute_gate_detail": absolute_detail,
        "paired_gate_pass": paired_pass,
        "paired": paired_summary,
        "f5_f6": {
            "control": control_metrics.to_dict(orient="records"),
            "structure_lite": candidate_metrics.to_dict(orient="records"),
        },
        "candidate_count_after_confirmation": 9,
    }
    aggregate_path.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    verdict = {
        "status": decision,
        "final_historical_development_architecture": final_architecture,
        "same_v3_b_candidate_reused": True,
        "new_candidate_ordinal_created": False,
        "cumulative_candidate_count": 9,
        "v2f5_v2f6_consumed_once": True,
        "fresh_forward_accessed": False,
        "forward_marker_written": False,
        "independent_validation_claim": False,
    }
    verdict_path.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    runtime = {
        "mode": "sequential_reference",
        "control_seconds": control_seconds,
        "structure_lite_seconds": candidate_seconds,
        "total_seconds": time.perf_counter() - started,
        "python": sys.version,
        "platform": platform.platform(),
        "environment": environment,
    }
    runtime_path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    artifact_paths = [
        equivalence_path,
        metrics_path,
        predictions_path,
        paired_path,
        overlap_path,
        aggregate_path,
        verdict_path,
        runtime_path,
    ]
    artifacts = {path.name: sha256_file(path) for path in artifact_paths}
    artifacts.update(control_models)
    artifacts.update(candidate_models)

    summary = {
        "status": decision,
        "code_commit": code_commit,
        "folds": list(LATE_FOLD_NAMES),
        "candidate_ids": [V3_B_CONTROL, V3_B_CANDIDATE],
        "new_candidate_ordinal_created": False,
        "cumulative_candidate_count": 9,
        "cache_sha256": contract_hashes["cache"],
        "cache_manifest_sha256": contract_hashes["manifest"],
        "contract_identity": contract_hashes,
        "reference_sha256": reference_hashes,
        "control_equivalence_status": equivalence["status"],
        "candidate_feature_columns": list(V3_B_FEATURE_COLUMNS),
        "candidate_feature_order_sha256": _feature_order_hash(tuple(V3_B_FEATURE_COLUMNS)),
        "absolute_gate_pass": absolute_pass,
        "paired_gate_pass": paired_pass,
        "paired_summary": paired_summary,
        "coverage": cache_manifest.get("coverage", {}),
        "artifact_sha256": artifacts,
        "v2f5_v2f6_consumed_once": True,
        "post_1224_materialized": False,
        "fresh_forward_accessed": False,
        "forward_marker_written": False,
        "independent_validation_claim": False,
    }
    summary_path = output_dir / "ranking_v3_final_structure_lite_f5_f6_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Final V3 Structure-Lite one-shot F5/F6 confirmation")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--panel", type=Path, required=True)
    prepare.add_argument("--calendar", type=Path, required=True)
    prepare.add_argument("--security-master", type=Path, required=True)
    prepare.add_argument("--v2-prepared", type=Path, required=True)
    prepare.add_argument("--v2-manifest", type=Path, required=True)
    prepare.add_argument("--structure-spec", type=Path, required=True)
    prepare.add_argument("--structure-addendum", type=Path, required=True)
    prepare.add_argument("--late-spec", type=Path, required=True)
    prepare.add_argument("--late-addendum", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--code-commit", required=True)

    run = sub.add_parser("run")
    run.add_argument("--cache", type=Path, required=True)
    run.add_argument("--cache-manifest", type=Path, required=True)
    run.add_argument("--reference-v2-dir", type=Path, required=True)
    run.add_argument("--structure-spec", type=Path, required=True)
    run.add_argument("--structure-addendum", type=Path, required=True)
    run.add_argument("--late-spec", type=Path, required=True)
    run.add_argument("--late-addendum", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--code-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        result = prepare_late_cache(
            panel_path=args.panel,
            calendar_path=args.calendar,
            security_master_path=args.security_master,
            v2_prepared_path=args.v2_prepared,
            v2_manifest_path=args.v2_manifest,
            structure_spec_path=args.structure_spec,
            structure_addendum_path=args.structure_addendum,
            late_spec_path=args.late_spec,
            late_addendum_path=args.late_addendum,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    else:
        result = run_late_confirmation(
            cache_path=args.cache,
            cache_manifest_path=args.cache_manifest,
            reference_v2_dir=args.reference_v2_dir,
            structure_spec_path=args.structure_spec,
            structure_addendum_path=args.structure_addendum,
            late_spec_path=args.late_spec,
            late_addendum_path=args.late_addendum,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
