from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd

from .provenance import sha256_file
from .ranking_v2_candidate import _assert_clean_output_dir, _normalize_candidate_table, _read_table
from .research_v2_models import HGB_XS_MARKET, candidate_feature_columns, pointwise_model, pointwise_raw_score
from .research_v2_validation import RANKING_V2_FOLDS, RankingV2Fold, evaluate_v2_scores, split_v2_model_table
from .stage5_ranking_holdout import _assert_environment


V3_A_HYPOTHESIS_ID = "V3-A-RECENCY-V1"
V3_A_CONTROL = "V3-A-RECENCY-V1-CONTROL-001"
V3_A_HL252 = "V3-A-RECENCY-V1-HL252-002"
V3_A_HL504 = "V3-A-RECENCY-V1-HL504-003"
V3_A_CANDIDATES = (V3_A_CONTROL, V3_A_HL252, V3_A_HL504)
V3_A_VARIANTS = (V3_A_HL252, V3_A_HL504)
HALF_LIFE_BY_CANDIDATE = {V3_A_HL252: 252, V3_A_HL504: 504}
DISCOVERY_FOLDS = tuple(RANKING_V2_FOLDS[:4])
SEALED_FOLD_NAMES = frozenset(fold.name for fold in RANKING_V2_FOLDS[4:])

PREPARED_CACHE_SHA256 = "522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5"
PREPARED_CACHE_MANIFEST_SHA256 = "6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143"
RECENCY_SPEC_SHA256 = "53c5bc3e90af12fea62a73815e1e85352e836d69938ce0e9287437a52c1d58fa"
RECENCY_SPEC_GIT_BLOB = "b6e055ad4fe5e964e29892ef2bd0d9b8a4921c83"
RECENCY_REVIEW_ADDENDUM_GIT_BLOB = "1ee532c849636c47dab12ba3702ce7590abfcd74"
V2_SUBSTANTIVE_CODE_HEAD = "5f2ed2f53aececfd7c338d3f9f65db1efae372b6"

WEIGHT_MEAN_ATOL = 1e-12
CONTROL_SCORE_ATOL = 1e-12
METRIC_ATOL = 1e-12
PAIRED_PR_PROMOTION = 0.001
NONINFERIORITY_TOLERANCE = 0.005

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


def preregistered_ledger_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ordinal, candidate in enumerate(V3_A_CANDIDATES, start=1):
        rows.append(
            {
                "hypothesis_id": V3_A_HYPOTHESIS_ID,
                "candidate_id": candidate,
                "candidate_ordinal": ordinal,
                "result_status": "SPECIFIED_NOT_RUN",
                "result_viewed": False,
                "verdict": "pending run",
                "cumulative_candidate_count": 0,
            }
        )
    return rows


@dataclass(frozen=True)
class WeightStats:
    candidate: str
    fold: str
    half_life: int | None
    rows: int
    minimum: float
    maximum: float
    mean: float
    total: float


def candidate_half_life(candidate: str) -> int | None:
    if candidate == V3_A_CONTROL:
        return None
    try:
        return HALF_LIFE_BY_CANDIDATE[candidate]
    except KeyError as exc:
        raise ValueError(f"unknown V3-A candidate: {candidate}") from exc


def assert_discovery_fold_allowed(fold: RankingV2Fold) -> None:
    if fold.name in SEALED_FOLD_NAMES or fold not in DISCOVERY_FOLDS:
        raise PermissionError(f"{fold.name} is sealed for V3-A recency and must not be scored")


def recency_weights(
    signal_session_index: Iterable[int] | np.ndarray | pd.Series,
    *,
    train_end: int,
    half_life: int,
) -> np.ndarray:
    if half_life <= 0:
        raise ValueError("half_life must be positive")
    sessions = np.asarray(signal_session_index, dtype=np.float64)
    if sessions.ndim != 1 or sessions.size == 0:
        raise ValueError("training session indices must be one-dimensional and non-empty")
    if not np.isfinite(sessions).all():
        raise ValueError("training session indices must be finite")
    ages = float(train_end) - sessions
    if (ages < 0).any():
        raise ValueError("training row appears after the frozen training end")
    raw = np.exp2(-ages / float(half_life)).astype(np.float64, copy=False)
    if not np.isfinite(raw).all() or (raw <= 0.0).any():
        raise RuntimeError("raw recency weights must be finite and positive")
    total = float(raw.sum(dtype=np.float64))
    if not np.isfinite(total) or total <= 0.0:
        raise RuntimeError("recency weight sum must be finite and positive")
    normalized = (raw * (float(raw.size) / total)).astype(np.float64, copy=False)
    if not np.isfinite(normalized).all() or (normalized <= 0.0).any():
        raise RuntimeError("normalized recency weights must be finite and positive")
    if abs(float(normalized.mean(dtype=np.float64)) - 1.0) > WEIGHT_MEAN_ATOL:
        raise RuntimeError("fold-local recency weights must have mean 1 within tolerance")
    return normalized


def _weight_stats(candidate: str, fold: RankingV2Fold, weights: np.ndarray | None, rows: int) -> WeightStats:
    half_life = candidate_half_life(candidate)
    if weights is None:
        values = np.ones(rows, dtype=np.float64)
    else:
        values = np.asarray(weights, dtype=np.float64)
    return WeightStats(
        candidate=candidate,
        fold=fold.name,
        half_life=half_life,
        rows=int(rows),
        minimum=float(values.min()),
        maximum=float(values.max()),
        mean=float(values.mean(dtype=np.float64)),
        total=float(values.sum(dtype=np.float64)),
    )


def _fit_candidate(train: pd.DataFrame, fold: RankingV2Fold, candidate: str):
    assert_discovery_fold_allowed(fold)
    y_train = train["binary_target"].to_numpy(dtype=int)
    model = pointwise_model(HGB_XS_MARKET)
    half_life = candidate_half_life(candidate)
    if half_life is None:
        model.fit(train, y_train)
        weights = None
    else:
        weights = recency_weights(
            train["signal_session_index"].to_numpy(dtype=int),
            train_end=fold.train_end,
            half_life=half_life,
        )
        model.fit(train, y_train, model__sample_weight=weights)
    return model, _weight_stats(candidate, fold, weights, len(train))


def _score_one_candidate(
    table: pd.DataFrame,
    candidate: str,
    *,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, list[WeightStats], dict[str, str]]:
    if candidate not in V3_A_CANDIDATES:
        raise ValueError(f"unknown V3-A candidate: {candidate}")
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    weight_stats: list[WeightStats] = []
    model_hashes: dict[str, str] = {}

    for fold in DISCOVERY_FOLDS:
        assert_discovery_fold_allowed(fold)
        train, validation = split_v2_model_table(table, fold)
        model, stats = _fit_candidate(train, fold, candidate)
        weight_stats.append(stats)
        score = pointwise_raw_score(model, validation)
        if not np.isfinite(score).all():
            raise RuntimeError(f"{candidate} {fold.name} produced non-finite ranking scores")
        metrics = evaluate_v2_scores(validation, score)
        metrics_rows.append(
            {
                "candidate": candidate,
                "fold": fold.name,
                "train_start": fold.train_start,
                "train_end": fold.train_end,
                "gap_start": fold.gap_start,
                "gap_end": fold.gap_end,
                "validation_start": fold.validation_start,
                "validation_end": fold.validation_end,
                "train_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                **metrics,
            }
        )
        scored = validation[["ticker", "date", "signal_session_index", "binary_target"]].copy()
        scored.insert(0, "fold", fold.name)
        scored.insert(0, "candidate", candidate)
        scored["score"] = score
        prediction_rows.append(scored)

        model_path = output_dir / f"ranking_v3_recency_{candidate.lower()}_{fold.name.lower()}.joblib"
        joblib.dump(model, model_path)
        model_hashes[model_path.name] = sha256_file(model_path)

    return (
        pd.DataFrame(metrics_rows),
        pd.concat(prediction_rows, ignore_index=True),
        weight_stats,
        model_hashes,
    )


def _read_reference_artifacts(
    reference_dir: Path,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, str]]:
    summary_path = reference_dir / "ranking_v2_hgb_xs_market_summary.json"
    metrics_path = reference_dir / "ranking_v2_hgb_xs_market_fold_metrics.csv"
    predictions_path = reference_dir / "ranking_v2_hgb_xs_market_predictions.parquet"
    for path in (summary_path, metrics_path, predictions_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "RANKING_V2_CANDIDATE_COMPLETE":
        raise RuntimeError("reference V2 summary is not a completed candidate run")
    if summary.get("candidate") != HGB_XS_MARKET:
        raise RuntimeError("reference V2 summary is not HGB_XS_MARKET")
    if summary.get("prepared_cache_sha256") != PREPARED_CACHE_SHA256:
        raise RuntimeError("reference V2 summary cache identity does not match frozen cache")
    if tuple(summary.get("feature_columns", [])) != tuple(candidate_feature_columns(HGB_XS_MARKET)):
        raise RuntimeError("reference V2 feature order does not match frozen HGB_XS_MARKET features")

    artifact_hashes = summary.get("artifact_sha256", {})
    actual_hashes = {
        "summary": sha256_file(summary_path),
        "fold_metrics": sha256_file(metrics_path),
        "predictions": sha256_file(predictions_path),
    }
    for key in ("fold_metrics", "predictions"):
        expected = artifact_hashes.get(key)
        if not isinstance(expected, str) or expected != actual_hashes[key]:
            raise RuntimeError(f"reference V2 {key} artifact hash mismatch")

    # F5/F6 remain sealed. The full immutable files are hashed for provenance,
    # but outcome rows are materialized only for F1-F4 using a parquet predicate.
    # The F5/F6 metrics CSV is never parsed by this runner.
    allowed = [fold.name for fold in DISCOVERY_FOLDS]
    predictions = pd.read_parquet(predictions_path, filters=[("fold", "in", allowed)])
    predictions = predictions[predictions["fold"].isin(allowed)].copy().reset_index(drop=True)
    if set(predictions["fold"].astype(str).unique()) != set(allowed):
        raise RuntimeError("reference V2 predictions do not contain exactly F1-F4 after sealed-fold filtering")

    metric_rows: list[dict[str, Any]] = []
    for fold in DISCOVERY_FOLDS:
        block = predictions[predictions["fold"].eq(fold.name)].copy().reset_index(drop=True)
        if block.empty:
            raise RuntimeError(f"reference V2 predictions missing {fold.name}")
        metric_rows.append({"fold": fold.name, **evaluate_v2_scores(block, block["score"].to_numpy(dtype=float))})
    metrics = pd.DataFrame(metric_rows)
    return summary, metrics, predictions, actual_hashes


def _normalize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["fold", "ticker", "date", "signal_session_index", "binary_target"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"prediction artifact missing identity columns: {sorted(missing)}")
    result = frame[required].copy()
    result["ticker"] = result["ticker"].astype(str)
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    result["signal_session_index"] = pd.to_numeric(result["signal_session_index"], errors="raise").astype(int)
    result["binary_target"] = pd.to_numeric(result["binary_target"], errors="raise").astype(int)
    return result.reset_index(drop=True)


def prove_control_equivalence(
    *,
    control_metrics: pd.DataFrame,
    control_predictions: pd.DataFrame,
    reference_metrics: pd.DataFrame,
    reference_predictions: pd.DataFrame,
    reference_hashes: dict[str, str],
) -> dict[str, Any]:
    allowed = {fold.name for fold in DISCOVERY_FOLDS}
    new_pred = control_predictions[control_predictions["fold"].isin(allowed)].copy().reset_index(drop=True)
    ref_pred = reference_predictions[reference_predictions["fold"].isin(allowed)].copy().reset_index(drop=True)
    if len(new_pred) != len(ref_pred):
        raise RuntimeError("V3-A control row count does not match frozen V2 reference")
    new_identity = _normalize_identity(new_pred)
    ref_identity = _normalize_identity(ref_pred)
    if not new_identity.equals(ref_identity):
        raise RuntimeError("V3-A control row identity/order does not match frozen V2 reference")

    new_score = pd.to_numeric(new_pred["score"], errors="raise").to_numpy(dtype=float)
    ref_score = pd.to_numeric(ref_pred["score"], errors="raise").to_numpy(dtype=float)
    if not np.allclose(new_score, ref_score, rtol=0.0, atol=CONTROL_SCORE_ATOL, equal_nan=False):
        maximum = float(np.max(np.abs(new_score - ref_score)))
        raise RuntimeError(f"V3-A control score equivalence failed: max_abs_diff={maximum}")

    new_metrics = control_metrics.set_index("fold")
    ref_metrics = reference_metrics[reference_metrics["fold"].isin(allowed)].copy().set_index("fold")
    if tuple(new_metrics.index) != tuple(ref_metrics.index):
        raise RuntimeError("V3-A control fold order does not match frozen V2 metrics")
    diffs: dict[str, float] = {}
    for column in METRIC_COLUMNS:
        if column not in new_metrics.columns or column not in ref_metrics.columns:
            raise RuntimeError(f"control equivalence metric missing: {column}")
        left = pd.to_numeric(new_metrics[column], errors="raise").to_numpy(dtype=float)
        right = pd.to_numeric(ref_metrics[column], errors="raise").to_numpy(dtype=float)
        maximum = float(np.max(np.abs(left - right)))
        diffs[column] = maximum
        if not np.allclose(left, right, rtol=0.0, atol=METRIC_ATOL, equal_nan=False):
            raise RuntimeError(f"V3-A control metric equivalence failed for {column}: max_abs_diff={maximum}")

    return {
        "status": "V3_A_CONTROL_EQUIVALENCE_PASS",
        "folds": [fold.name for fold in DISCOVERY_FOLDS],
        "row_count": int(len(new_pred)),
        "score_atol": CONTROL_SCORE_ATOL,
        "metric_atol": METRIC_ATOL,
        "max_score_abs_diff": float(np.max(np.abs(new_score - ref_score))) if len(new_score) else 0.0,
        "max_metric_abs_diff": diffs,
        "reference_artifact_sha256": reference_hashes,
    }


def _aggregate_candidate(metrics: pd.DataFrame) -> dict[str, Any]:
    if tuple(metrics["fold"].astype(str)) != tuple(fold.name for fold in DISCOVERY_FOLDS):
        raise ValueError("candidate metrics must contain V2F1-V2F4 exactly once in order")
    pr = pd.to_numeric(metrics["pr_auc_delta_vs_base"], errors="raise").to_numpy(dtype=float)
    roc = pd.to_numeric(metrics["roc_auc"], errors="raise").to_numpy(dtype=float)
    spread = pd.to_numeric(metrics["q5_minus_q1"], errors="raise").to_numpy(dtype=float)
    top = pd.to_numeric(metrics["top_decile_lift"], errors="raise").to_numpy(dtype=float)
    finite = bool(np.isfinite(np.concatenate([pr, roc, spread, top])).all())
    return {
        "all_metrics_finite": finite,
        "median_pr_auc_delta": float(np.median(pr)),
        "q25_pr_auc_delta": float(np.quantile(pr, 0.25)),
        "worst_pr_auc_delta": float(np.min(pr)),
        "positive_pr_delta_folds": int(np.sum(pr > 0.0)),
        "median_roc_auc": float(np.median(roc)),
        "roc_gt_half_folds": int(np.sum(roc > 0.5)),
        "median_q5_minus_q1": float(np.median(spread)),
        "worst_q5_minus_q1": float(np.min(spread)),
        "positive_q5_minus_q1_folds": int(np.sum(spread > 0.0)),
        "median_top_decile_lift": float(np.median(top)),
        "v3d4_pr_auc_delta": float(pr[-1]),
        "v3d4_roc_auc": float(roc[-1]),
        "v3d4_q5_minus_q1": float(spread[-1]),
    }


def _absolute_sanity(aggregate: dict[str, Any]) -> bool:
    return bool(
        aggregate["all_metrics_finite"]
        and aggregate["median_pr_auc_delta"] > 0.0
        and aggregate["positive_pr_delta_folds"] >= 3
        and aggregate["median_roc_auc"] > 0.5
        and aggregate["roc_gt_half_folds"] >= 3
        and aggregate["median_q5_minus_q1"] > 0.0
        and aggregate["positive_q5_minus_q1_folds"] >= 3
    )


def _paired_metrics(candidate_metrics: pd.DataFrame, control_metrics: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    candidate = candidate_metrics.set_index("fold")
    control = control_metrics.set_index("fold")
    if tuple(candidate.index) != tuple(control.index):
        raise ValueError("paired V3-A comparison requires identical fold order")
    paired = pd.DataFrame(index=candidate.index)
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
    summary = {
        "median_pr_auc_delta_improvement": float(np.median(pr)),
        "q25_pr_auc_delta_improvement": float(np.quantile(pr, 0.25)),
        "worst_pr_auc_delta_improvement": float(np.min(pr)),
        "pr_not_below_control_folds": int(np.sum(pr >= 0.0)),
        "median_roc_auc_change": float(np.median(roc)),
        "median_q5_minus_q1_change": float(np.median(spread)),
        "q5_not_below_control_folds": int(np.sum(spread >= 0.0)),
        "median_top_decile_lift_change": float(np.median(paired["top_decile_lift_change"].to_numpy(dtype=float))),
    }
    return paired.reset_index(), summary


def _paired_promotion(summary: dict[str, Any]) -> bool:
    return bool(
        summary["median_pr_auc_delta_improvement"] >= PAIRED_PR_PROMOTION
        and summary["q25_pr_auc_delta_improvement"] >= 0.0
        and summary["worst_pr_auc_delta_improvement"] >= 0.0
        and summary["pr_not_below_control_folds"] >= 3
        and summary["median_roc_auc_change"] >= -NONINFERIORITY_TOLERANCE
        and summary["median_q5_minus_q1_change"] >= -NONINFERIORITY_TOLERANCE
        and summary["q5_not_below_control_folds"] >= 3
    )


def _select_promoted(results: dict[str, dict[str, Any]]) -> str | None:
    passing = [candidate for candidate in V3_A_VARIANTS if results[candidate]["promoted"]]
    if not passing:
        return None
    if len(passing) == 1:
        return passing[0]

    def key(candidate: str) -> tuple[float, float, float, float, int, int]:
        paired = results[candidate]["paired_aggregate"]
        simplicity = 1 if candidate == V3_A_HL504 else 0
        ordinal = 3 if candidate == V3_A_HL504 else 2
        return (
            float(paired["median_pr_auc_delta_improvement"]),
            float(paired["q25_pr_auc_delta_improvement"]),
            float(paired["worst_pr_auc_delta_improvement"]),
            float(paired["median_q5_minus_q1_change"]),
            simplicity,
            -ordinal,
        )

    return max(passing, key=key)


def _write_frame(frame: pd.DataFrame, path: Path) -> str:
    if path.suffix.lower() == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    return sha256_file(path)


def _git_blob_sha1(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _assert_contract_files(
    *,
    prepared_table_path: Path,
    prepared_manifest_path: Path,
    spec_path: Path,
    addendum_path: Path,
) -> dict[str, str]:
    hashes = {
        "prepared_table": sha256_file(prepared_table_path),
        "prepared_manifest": sha256_file(prepared_manifest_path),
        "recency_spec": sha256_file(spec_path),
        "recency_addendum": sha256_file(addendum_path),
        "recency_spec_git_blob": _git_blob_sha1(spec_path),
        "recency_addendum_git_blob": _git_blob_sha1(addendum_path),
    }
    if hashes["prepared_table"] != PREPARED_CACHE_SHA256:
        raise RuntimeError("V3-A prepared cache hash mismatch")
    if hashes["prepared_manifest"] != PREPARED_CACHE_MANIFEST_SHA256:
        raise RuntimeError("V3-A prepared cache manifest hash mismatch")
    if hashes["recency_spec"] != RECENCY_SPEC_SHA256:
        raise RuntimeError("V3-A recency spec SHA-256 mismatch")
    if hashes["recency_spec_git_blob"] != RECENCY_SPEC_GIT_BLOB:
        raise RuntimeError("V3-A recency spec Git blob mismatch")
    if hashes["recency_addendum_git_blob"] != RECENCY_REVIEW_ADDENDUM_GIT_BLOB:
        raise RuntimeError("V3-A review addendum Git blob mismatch")
    return hashes


def run_discovery(
    *,
    prepared_table_path: Path,
    prepared_manifest_path: Path,
    reference_v2_dir: Path,
    output_dir: Path,
    code_commit: str,
    spec_path: Path,
    addendum_path: Path,
) -> dict[str, Any]:
    started = time.perf_counter()
    environment = _assert_environment()
    contract_hashes = _assert_contract_files(
        prepared_table_path=prepared_table_path,
        prepared_manifest_path=prepared_manifest_path,
        spec_path=spec_path,
        addendum_path=addendum_path,
    )
    _assert_clean_output_dir(output_dir)

    read_started = time.perf_counter()
    raw_table = _read_table(prepared_table_path)
    table = _normalize_candidate_table(raw_table, HGB_XS_MARKET)
    read_seconds = time.perf_counter() - read_started

    reference_summary, reference_metrics, reference_predictions, reference_hashes = _read_reference_artifacts(
        reference_v2_dir
    )

    control_started = time.perf_counter()
    control_dir = output_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=False)
    control_metrics, control_predictions, control_weight_stats, control_model_hashes = _score_one_candidate(
        table, V3_A_CONTROL, output_dir=control_dir
    )
    control_seconds = time.perf_counter() - control_started

    equivalence = prove_control_equivalence(
        control_metrics=control_metrics,
        control_predictions=control_predictions,
        reference_metrics=reference_metrics,
        reference_predictions=reference_predictions,
        reference_hashes=reference_hashes,
    )
    equivalence["reference_summary_identity"] = {
        "sha256": reference_hashes["summary"],
        "code_commit": reference_summary.get("code_commit"),
        "environment": reference_summary.get("environment"),
    }
    equivalence_path = output_dir / "v3_a_control_equivalence.json"
    equivalence_path.write_text(json.dumps(equivalence, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    candidate_metrics: dict[str, pd.DataFrame] = {V3_A_CONTROL: control_metrics}
    candidate_predictions: dict[str, pd.DataFrame] = {V3_A_CONTROL: control_predictions}
    weight_stats_by_candidate: dict[str, list[WeightStats]] = {V3_A_CONTROL: control_weight_stats}
    model_hashes_by_candidate: dict[str, dict[str, str]] = {V3_A_CONTROL: control_model_hashes}
    runtime_seconds: dict[str, float] = {V3_A_CONTROL: control_seconds}

    # Variants are not fitted until the mandatory control-equivalence gate above passes.
    for candidate in V3_A_VARIANTS:
        candidate_started = time.perf_counter()
        candidate_dir = output_dir / candidate.lower()
        candidate_dir.mkdir(parents=True, exist_ok=False)
        metrics, predictions, stats, hashes = _score_one_candidate(table, candidate, output_dir=candidate_dir)
        candidate_metrics[candidate] = metrics
        candidate_predictions[candidate] = predictions
        weight_stats_by_candidate[candidate] = stats
        model_hashes_by_candidate[candidate] = hashes
        runtime_seconds[candidate] = time.perf_counter() - candidate_started

    all_metrics = pd.concat([candidate_metrics[c] for c in V3_A_CANDIDATES], ignore_index=True)
    all_predictions = pd.concat([candidate_predictions[c] for c in V3_A_CANDIDATES], ignore_index=True)

    aggregates: dict[str, dict[str, Any]] = {}
    result_detail: dict[str, dict[str, Any]] = {}
    paired_frames: list[pd.DataFrame] = []
    control_aggregate = _aggregate_candidate(candidate_metrics[V3_A_CONTROL])
    aggregates[V3_A_CONTROL] = control_aggregate
    result_detail[V3_A_CONTROL] = {
        "absolute_sanity_pass": _absolute_sanity(control_aggregate),
        "promoted": False,
        "verdict": "CONTROL_REFERENCE",
    }

    for candidate in V3_A_VARIANTS:
        aggregate = _aggregate_candidate(candidate_metrics[candidate])
        aggregates[candidate] = aggregate
        paired, paired_aggregate = _paired_metrics(candidate_metrics[candidate], candidate_metrics[V3_A_CONTROL])
        paired.insert(0, "candidate", candidate)
        paired_frames.append(paired)
        absolute = _absolute_sanity(aggregate)
        paired_pass = _paired_promotion(paired_aggregate)
        promoted = bool(absolute and paired_pass)
        if promoted:
            candidate_verdict = "PROMOTE_FOR_NEXT_RESEARCH_STEP"
        elif not absolute:
            candidate_verdict = "KILL"
        else:
            candidate_verdict = "KEEP_DIAGNOSTIC"
        result_detail[candidate] = {
            "absolute_sanity_pass": absolute,
            "paired_promotion_pass": paired_pass,
            "paired_aggregate": paired_aggregate,
            "promoted": promoted,
            "verdict": candidate_verdict,
        }

    selected = _select_promoted(result_detail)
    decision = (
        "V3_A_RECENCY_PROMOTE_FOR_NEXT_RESEARCH_STEP"
        if selected is not None
        else "V3_A_RECENCY_KILL_KEEP_V2_CONTROL"
    )

    metrics_path = output_dir / "ranking_v3_a_recency_f1_f4_metrics.csv"
    predictions_path = output_dir / "ranking_v3_a_recency_f1_f4_predictions.parquet"
    paired_path = output_dir / "ranking_v3_a_recency_paired_comparison.csv"
    aggregate_path = output_dir / "ranking_v3_a_recency_aggregate.json"
    verdict_path = output_dir / "ranking_v3_a_recency_verdict.json"
    weights_path = output_dir / "ranking_v3_a_recency_weight_stats.csv"
    runtime_path = output_dir / "ranking_v3_a_recency_runtime.json"

    artifact_hashes: dict[str, str] = {}
    artifact_hashes[metrics_path.name] = _write_frame(all_metrics, metrics_path)
    artifact_hashes[predictions_path.name] = _write_frame(all_predictions, predictions_path)
    paired_frame = pd.concat(paired_frames, ignore_index=True)
    artifact_hashes[paired_path.name] = _write_frame(paired_frame, paired_path)

    weight_rows = [stats.__dict__ for candidate in V3_A_CANDIDATES for stats in weight_stats_by_candidate[candidate]]
    artifact_hashes[weights_path.name] = _write_frame(pd.DataFrame(weight_rows), weights_path)

    aggregate_payload = {
        "hypothesis_id": V3_A_HYPOTHESIS_ID,
        "candidate_aggregates": aggregates,
        "candidate_results": result_detail,
        "selected_candidate": selected,
    }
    aggregate_path.write_text(json.dumps(aggregate_payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    artifact_hashes[aggregate_path.name] = sha256_file(aggregate_path)

    verdict_payload = {
        "status": decision,
        "selected_candidate": selected,
        "discovery_folds": [fold.name for fold in DISCOVERY_FOLDS],
        "sealed_folds_not_scored": sorted(SEALED_FOLD_NAMES),
        "control_equivalence_status": equivalence["status"],
        "independent_validation_claim": False,
        "reserved_v2_forward_outcomes_accessed": False,
    }
    verdict_path.write_text(json.dumps(verdict_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    artifact_hashes[verdict_path.name] = sha256_file(verdict_path)

    runtime_payload = {
        "table_read_normalize_seconds": read_seconds,
        "candidate_fit_score_seconds": runtime_seconds,
        "total_seconds": time.perf_counter() - started,
        "execution_mode": "sequential_reference",
        "python": sys.version,
        "platform": platform.platform(),
    }
    runtime_path.write_text(json.dumps(runtime_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    artifact_hashes[runtime_path.name] = sha256_file(runtime_path)
    artifact_hashes[equivalence_path.name] = sha256_file(equivalence_path)

    ledger_path = output_dir / "ranking_v3_a_recency_ledger_rows.json"
    ledger_rows = []
    for ordinal, candidate in enumerate(V3_A_CANDIDATES, start=1):
        result = result_detail[candidate]
        ledger_rows.append(
            {
                "hypothesis_id": V3_A_HYPOTHESIS_ID,
                "candidate_id": candidate,
                "candidate_ordinal": ordinal,
                "fold_set": "V2F1-V2F4",
                "result_status": "COMPLETE",
                "result_viewed": True,
                "verdict": result["verdict"],
                "cumulative_candidate_count": ordinal,
                "code_commit": code_commit,
                "weight_formula": "uniform_1.0" if candidate == V3_A_CONTROL else "2**(-age/H)",
                "weight_normalization": "fold_local_mean_1.0",
            }
        )
    ledger_path.write_text(json.dumps(ledger_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    artifact_hashes[ledger_path.name] = sha256_file(ledger_path)

    for hashes in model_hashes_by_candidate.values():
        artifact_hashes.update(hashes)

    summary = {
        "status": decision,
        "hypothesis_id": V3_A_HYPOTHESIS_ID,
        "code_commit": code_commit,
        "prepared_cache_sha256": contract_hashes["prepared_table"],
        "prepared_cache_manifest_sha256": contract_hashes["prepared_manifest"],
        "recency_spec_sha256": contract_hashes["recency_spec"],
        "recency_spec_git_blob": contract_hashes["recency_spec_git_blob"],
        "recency_review_addendum_sha256": contract_hashes["recency_addendum"],
        "recency_review_addendum_git_blob": contract_hashes["recency_addendum_git_blob"],
        "v2_substantive_code_head": V2_SUBSTANTIVE_CODE_HEAD,
        "environment": environment,
        "feature_columns": list(candidate_feature_columns(HGB_XS_MARKET)),
        "candidates": list(V3_A_CANDIDATES),
        "discovery_folds": [fold.__dict__ for fold in DISCOVERY_FOLDS],
        "sealed_folds": sorted(SEALED_FOLD_NAMES),
        "control_equivalence": equivalence,
        "selected_candidate": selected,
        "artifact_sha256": artifact_hashes,
        "runtime": runtime_payload,
        "probability_claim": False,
        "independent_validation_claim": False,
        "fresh_forward_accessed": False,
        "f5_f6_scored": False,
    }
    summary_path = output_dir / "ranking_v3_a_recency_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen Ranking V3-A recency discovery on V2F1-V2F4 only")
    parser.add_argument("--prepared-table", type=Path, required=True)
    parser.add_argument("--prepared-manifest", type=Path, required=True)
    parser.add_argument("--reference-v2-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--addendum", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = run_discovery(
        prepared_table_path=args.prepared_table,
        prepared_manifest_path=args.prepared_manifest,
        reference_v2_dir=args.reference_v2_dir,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
        spec_path=args.spec,
        addendum_path=args.addendum,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
