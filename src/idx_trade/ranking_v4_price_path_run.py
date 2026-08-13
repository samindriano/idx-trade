from __future__ import annotations

import argparse
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
from .ranking_v2_candidate import _assert_clean_output_dir
from .ranking_v3_structure_lite import V3_B_CANDIDATE
from .ranking_v4_price_path import (
    V4_B1_CANDIDATE,
    V4_B2_CANDIDATE,
    V4_B_CONTROL,
    V4_B_FIRST_PASS_CANDIDATES,
    assert_first_pass_candidate_set,
    assert_historical_boundary,
    assert_spec_identity,
    candidate_feature_columns,
    candidate_model,
    candidate_raw_score,
    feature_order_sha256,
)
from .ranking_v4_price_path_prepare import V4_B_CACHE_STATUS
from .research_stage5 import assign_within_date_buckets
from .research_v2_validation import RANKING_V2_FOLDS, evaluate_v2_scores, split_v2_model_table
from .stage5_ranking_holdout import _assert_environment


FOLD_NAMES = tuple(fold.name for fold in RANKING_V2_FOLDS)
CONTROL_SCORE_ATOL = 1e-12
METRIC_ATOL = 1e-12

V3_F1_F4_METRICS_SHA256 = "0a6919a22669c14db272cc12ff70081d50ea53139f591c7faf2be2c43d321357"
V3_F1_F4_PREDICTIONS_SHA256 = "c7761dd0bd93340381b28234537bf7a42e829eae0f214ec8173d8bc1f6f2e4e1"
V3_F5_F6_METRICS_SHA256 = "5e758e468cf883212fdb11c64d63f8ab3cf86c20a04a60edbc651205bc8f6d25"
V3_F5_F6_PREDICTIONS_SHA256 = "64cf1c04640740c5906db03e1ba86290790904daca2971e61c00212de893715b"

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


def _assert_cache(
    cache_path: Path,
    manifest_path: Path,
    spec_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, str]]:
    spec_blob = assert_spec_identity(spec_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != V4_B_CACHE_STATUS:
        raise RuntimeError("V4-B cache manifest is not frozen pre-outcome")
    if bool(manifest.get("outcome_metrics_computed", True)):
        raise RuntimeError("V4-B cache manifest unexpectedly contains outcome metrics")
    if bool(manifest.get("post_1224_materialized", True)):
        raise RuntimeError("V4-B cache manifest claims session 1225+ materialization")
    if bool(manifest.get("fresh_forward_accessed", True)):
        raise RuntimeError("V4-B cache manifest claims fresh-forward access")
    if bool(manifest.get("integration_candidate_materialized", True)):
        raise RuntimeError("V4-B first-pass cache claims integration candidate materialization")
    if manifest.get("spec_git_blob") != spec_blob:
        raise RuntimeError("V4-B cache manifest spec identity mismatch")

    actual_cache_sha = sha256_file(cache_path)
    if actual_cache_sha != manifest.get("cache_sha256"):
        raise RuntimeError("V4-B cache SHA mismatch")
    table = pd.read_parquet(cache_path)
    assert_historical_boundary(table)
    required = {
        "ticker",
        "date",
        "signal_session_index",
        "binary_target",
        *candidate_feature_columns(V4_B1_CANDIDATE),
        *candidate_feature_columns(V4_B2_CANDIDATE),
    }
    missing = required - set(table.columns)
    if missing:
        raise RuntimeError(f"V4-B cache missing required columns: {sorted(missing)}")
    if table.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V4-B cache contains duplicate ticker/date rows")
    return table, manifest, {
        "cache": actual_cache_sha,
        "manifest": sha256_file(manifest_path),
        "spec_git_blob": spec_blob,
    }


def _read_reference(
    *,
    f1_f4_metrics_path: Path,
    f1_f4_predictions_path: Path,
    f5_f6_metrics_path: Path,
    f5_f6_predictions_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    hashes = {
        "f1_f4_metrics": sha256_file(f1_f4_metrics_path),
        "f1_f4_predictions": sha256_file(f1_f4_predictions_path),
        "f5_f6_metrics": sha256_file(f5_f6_metrics_path),
        "f5_f6_predictions": sha256_file(f5_f6_predictions_path),
    }
    expected = {
        "f1_f4_metrics": V3_F1_F4_METRICS_SHA256,
        "f1_f4_predictions": V3_F1_F4_PREDICTIONS_SHA256,
        "f5_f6_metrics": V3_F5_F6_METRICS_SHA256,
        "f5_f6_predictions": V3_F5_F6_PREDICTIONS_SHA256,
    }
    if hashes != expected:
        raise RuntimeError(
            f"V4-B frozen V3-B reference hash mismatch: expected={expected} actual={hashes}"
        )

    early_metrics = pd.read_csv(f1_f4_metrics_path)
    late_metrics = pd.read_csv(f5_f6_metrics_path)
    early_predictions = pd.read_parquet(f1_f4_predictions_path)
    late_predictions = pd.read_parquet(f5_f6_predictions_path)

    def select(frame: pd.DataFrame, *, artifact: str) -> pd.DataFrame:
        if "candidate" not in frame.columns:
            raise RuntimeError(f"V3-B reference {artifact} missing candidate column")
        selected = frame[frame["candidate"].astype(str).eq(V3_B_CANDIDATE)].copy()
        if selected.empty:
            raise RuntimeError(f"V3-B reference {artifact} missing final Structure-Lite candidate")
        return selected

    metrics = pd.concat(
        [select(early_metrics, artifact="F1-F4 metrics"), select(late_metrics, artifact="F5-F6 metrics")],
        ignore_index=True,
    )
    predictions = pd.concat(
        [
            select(early_predictions, artifact="F1-F4 predictions"),
            select(late_predictions, artifact="F5-F6 predictions"),
        ],
        ignore_index=True,
    )
    metrics["fold"] = metrics["fold"].astype(str)
    predictions["fold"] = predictions["fold"].astype(str)
    metrics = pd.concat([metrics[metrics["fold"].eq(name)] for name in FOLD_NAMES], ignore_index=True)
    predictions = pd.concat(
        [predictions[predictions["fold"].eq(name)] for name in FOLD_NAMES], ignore_index=True
    )
    if tuple(metrics["fold"].tolist()) != FOLD_NAMES:
        raise RuntimeError("V3-B reference metrics do not contain exactly one row per F1-F6 fold")
    if tuple(dict.fromkeys(predictions["fold"].tolist())) != FOLD_NAMES:
        raise RuntimeError("V3-B reference predictions fold order is not F1-F6")
    return metrics.reset_index(drop=True), predictions.reset_index(drop=True), hashes


def _score_candidate(
    table: pd.DataFrame,
    candidate: str,
    *,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    if candidate not in V4_B_FIRST_PASS_CANDIDATES:
        raise ValueError(f"unknown V4-B first-pass candidate: {candidate}")
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}

    for fold in RANKING_V2_FOLDS:
        train, validation = split_v2_model_table(table, fold)
        model = candidate_model(candidate)
        model.fit(train, train["binary_target"].to_numpy(dtype=int))
        score = candidate_raw_score(model, validation)
        if not np.isfinite(score).all():
            raise RuntimeError(f"{candidate} {fold.name} produced non-finite scores")
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

        model_path = output_dir / f"{candidate.lower()}_{fold.name.lower()}.joblib"
        joblib.dump(model, model_path)
        model_hashes[model_path.name] = sha256_file(model_path)

    return pd.DataFrame(metrics_rows), pd.concat(prediction_rows, ignore_index=True), model_hashes


def _normalize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["fold", "ticker", "date", "signal_session_index", "binary_target"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise RuntimeError(f"V4-B prediction identity missing columns: {sorted(missing)}")
    out = frame[required].copy()
    out["fold"] = out["fold"].astype(str)
    out["ticker"] = out["ticker"].astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    out["signal_session_index"] = pd.to_numeric(out["signal_session_index"], errors="raise").astype(int)
    out["binary_target"] = pd.to_numeric(out["binary_target"], errors="raise").astype(int)
    return out.reset_index(drop=True)


def prove_v3_b_control_equivalence(
    *,
    control_metrics: pd.DataFrame,
    control_predictions: pd.DataFrame,
    reference_metrics: pd.DataFrame,
    reference_predictions: pd.DataFrame,
    reference_hashes: dict[str, str],
) -> dict[str, Any]:
    if len(control_predictions) != len(reference_predictions):
        raise RuntimeError("V4-B control row count differs from frozen V3-B reference")
    if not _normalize_identity(control_predictions).equals(_normalize_identity(reference_predictions)):
        raise RuntimeError("V4-B control row identity/order differs from frozen V3-B reference")
    new_score = pd.to_numeric(control_predictions["score"], errors="raise").to_numpy(dtype=float)
    ref_score = pd.to_numeric(reference_predictions["score"], errors="raise").to_numpy(dtype=float)
    if not np.allclose(new_score, ref_score, rtol=0.0, atol=CONTROL_SCORE_ATOL, equal_nan=False):
        raise RuntimeError(
            "V4-B exact V3-B score equivalence failed: "
            f"max={float(np.max(np.abs(new_score - ref_score)))}"
        )

    left = control_metrics.set_index("fold").loc[list(FOLD_NAMES)]
    right = reference_metrics.set_index("fold").loc[list(FOLD_NAMES)]
    metric_diff: dict[str, float] = {}
    for column in METRIC_COLUMNS:
        a = pd.to_numeric(left[column], errors="raise").to_numpy(dtype=float)
        b = pd.to_numeric(right[column], errors="raise").to_numpy(dtype=float)
        maximum = float(np.max(np.abs(a - b)))
        metric_diff[column] = maximum
        if not np.allclose(a, b, rtol=0.0, atol=METRIC_ATOL, equal_nan=False):
            raise RuntimeError(f"V4-B V3-B metric equivalence failed {column}: max={maximum}")
    return {
        "status": "V4_B_V3_B_CONTROL_EQUIVALENCE_PASS",
        "folds": list(FOLD_NAMES),
        "row_count": int(len(control_predictions)),
        "max_score_abs_diff": float(np.max(np.abs(new_score - ref_score))),
        "max_metric_abs_diff": metric_diff,
        "reference_artifact_sha256": reference_hashes,
    }


def _paired_frame(candidate_metrics: pd.DataFrame, control_metrics: pd.DataFrame) -> pd.DataFrame:
    candidate = candidate_metrics.set_index("fold").loc[list(FOLD_NAMES)]
    control = control_metrics.set_index("fold").loc[list(FOLD_NAMES)]
    paired = pd.DataFrame(index=FOLD_NAMES)
    paired.index.name = "fold"
    paired["pr_auc_improvement"] = (
        pd.to_numeric(candidate["pr_auc"], errors="raise")
        - pd.to_numeric(control["pr_auc"], errors="raise")
    )
    paired["roc_auc_change"] = (
        pd.to_numeric(candidate["roc_auc"], errors="raise")
        - pd.to_numeric(control["roc_auc"], errors="raise")
    )
    paired["q5_minus_q1_change"] = (
        pd.to_numeric(candidate["q5_minus_q1"], errors="raise")
        - pd.to_numeric(control["q5_minus_q1"], errors="raise")
    )
    paired["top_decile_lift_change"] = (
        pd.to_numeric(candidate["top_decile_lift"], errors="raise")
        - pd.to_numeric(control["top_decile_lift"], errors="raise")
    )
    return paired.reset_index()


def _gate(
    candidate_metrics: pd.DataFrame,
    control_metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any], bool]:
    candidate = candidate_metrics.set_index("fold").loc[list(FOLD_NAMES)]
    finite = bool(
        np.isfinite(
            candidate[list(METRIC_COLUMNS)].apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
        ).all()
    )
    pr_delta = pd.to_numeric(candidate["pr_auc_delta_vs_base"], errors="raise").to_numpy(dtype=float)
    spread_abs = pd.to_numeric(candidate["q5_minus_q1"], errors="raise").to_numpy(dtype=float)

    paired = _paired_frame(candidate_metrics, control_metrics)
    pr = pd.to_numeric(paired["pr_auc_improvement"], errors="raise").to_numpy(dtype=float)
    roc = pd.to_numeric(paired["roc_auc_change"], errors="raise").to_numpy(dtype=float)
    spread = pd.to_numeric(paired["q5_minus_q1_change"], errors="raise").to_numpy(dtype=float)
    late_pr = paired[paired["fold"].isin(("V2F5", "V2F6"))]["pr_auc_improvement"].to_numpy(dtype=float)

    detail = {
        "absolute_all_metrics_finite": finite,
        "absolute_pr_delta_positive_6_of_6": bool(np.all(pr_delta > 0.0)),
        "absolute_q5_q1_positive_6_of_6": bool(np.all(spread_abs > 0.0)),
        "paired_pr_nonnegative_folds": int((pr >= 0.0).sum()),
        "paired_pr_nonnegative_at_least_5_of_6": bool((pr >= 0.0).sum() >= 5),
        "median_pr_auc_improvement": float(np.median(pr)),
        "q25_pr_auc_improvement": float(np.quantile(pr, 0.25)),
        "worst_pr_auc_improvement": float(np.min(pr)),
        "median_roc_auc_change": float(np.median(roc)),
        "median_q5_minus_q1_change": float(np.median(spread)),
        "q5_q1_nonnegative_folds": int((spread >= 0.0).sum()),
        "q5_q1_nonnegative_at_least_4_of_6": bool((spread >= 0.0).sum() >= 4),
        "late_pr_each_at_least_minus_003": bool(np.all(late_pr >= -0.0030)),
        "late_median_pr_nonnegative": bool(np.median(late_pr) >= 0.0),
        "median_top_decile_lift_change": float(
            np.median(pd.to_numeric(paired["top_decile_lift_change"], errors="raise").to_numpy(dtype=float))
        ),
    }
    passed = bool(
        detail["absolute_all_metrics_finite"]
        and detail["absolute_pr_delta_positive_6_of_6"]
        and detail["absolute_q5_q1_positive_6_of_6"]
        and detail["paired_pr_nonnegative_at_least_5_of_6"]
        and detail["median_pr_auc_improvement"] >= 0.0015
        and detail["q25_pr_auc_improvement"] >= 0.0
        and detail["worst_pr_auc_improvement"] >= -0.0030
        and detail["median_roc_auc_change"] >= -0.0020
        and detail["median_q5_minus_q1_change"] >= 0.0
        and detail["q5_q1_nonnegative_at_least_4_of_6"]
        and detail["late_pr_each_at_least_minus_003"]
        and detail["late_median_pr_nonnegative"]
    )
    return paired, detail, passed


def _top_decile_overlap(control_predictions: pd.DataFrame, candidate_predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for fold in FOLD_NAMES:
        control = control_predictions[control_predictions["fold"].eq(fold)].copy().reset_index(drop=True)
        candidate = candidate_predictions[candidate_predictions["fold"].eq(fold)].copy().reset_index(drop=True)
        identity = ["ticker", "date", "signal_session_index", "binary_target"]
        if not control[identity].equals(candidate[identity]):
            raise RuntimeError(f"V4-B top-decile identity mismatch for {fold}")
        left = assign_within_date_buckets(control, score_column="score", buckets=10, output_column="decile")
        right = assign_within_date_buckets(candidate, score_column="score", buckets=10, output_column="decile")
        left_keys = set(
            zip(
                left.loc[left["decile"].eq(10), "date"],
                left.loc[left["decile"].eq(10), "ticker"],
                strict=False,
            )
        )
        right_keys = set(
            zip(
                right.loc[right["decile"].eq(10), "date"],
                right.loc[right["decile"].eq(10), "ticker"],
                strict=False,
            )
        )
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


def run_v4b_first_pass(
    *,
    cache_path: Path,
    cache_manifest_path: Path,
    spec_path: Path,
    v3_f1_f4_metrics_path: Path,
    v3_f1_f4_predictions_path: Path,
    v3_f5_f6_metrics_path: Path,
    v3_f5_f6_predictions_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    """Atomic first-pass V4-B run: exact V3-B control + B1 + B2, no integration."""

    started = time.perf_counter()
    environment = _assert_environment()
    _assert_clean_output_dir(output_dir)
    assert_first_pass_candidate_set(V4_B_FIRST_PASS_CANDIDATES)
    table, cache_manifest, contract = _assert_cache(cache_path, cache_manifest_path, spec_path)
    reference_metrics, reference_predictions, reference_hashes = _read_reference(
        f1_f4_metrics_path=v3_f1_f4_metrics_path,
        f1_f4_predictions_path=v3_f1_f4_predictions_path,
        f5_f6_metrics_path=v3_f5_f6_metrics_path,
        f5_f6_predictions_path=v3_f5_f6_predictions_path,
    )

    all_metrics: list[pd.DataFrame] = []
    all_predictions: list[pd.DataFrame] = []
    all_model_hashes: dict[str, str] = {}
    elapsed: dict[str, float] = {}

    control_dir = output_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=False)
    t0 = time.perf_counter()
    control_metrics, control_predictions, model_hashes = _score_candidate(table, V4_B_CONTROL, output_dir=control_dir)
    elapsed[V4_B_CONTROL] = time.perf_counter() - t0
    all_metrics.append(control_metrics)
    all_predictions.append(control_predictions)
    all_model_hashes.update({f"control/{k}": v for k, v in model_hashes.items()})

    equivalence = prove_v3_b_control_equivalence(
        control_metrics=control_metrics,
        control_predictions=control_predictions,
        reference_metrics=reference_metrics,
        reference_predictions=reference_predictions,
        reference_hashes=reference_hashes,
    )
    equivalence_path = output_dir / "ranking_v4_b_v3_b_control_equivalence.json"
    equivalence_path.write_text(json.dumps(equivalence, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    challenger_outputs: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for candidate, dirname in (
        (V4_B1_CANDIDATE, "b1_coherence"),
        (V4_B2_CANDIDATE, "b2_range_acceptance"),
    ):
        candidate_dir = output_dir / dirname
        candidate_dir.mkdir(parents=True, exist_ok=False)
        t0 = time.perf_counter()
        metrics, predictions, model_hashes = _score_candidate(table, candidate, output_dir=candidate_dir)
        elapsed[candidate] = time.perf_counter() - t0
        challenger_outputs[candidate] = (metrics, predictions)
        all_metrics.append(metrics)
        all_predictions.append(predictions)
        all_model_hashes.update({f"{dirname}/{k}": v for k, v in model_hashes.items()})

    results: dict[str, Any] = {}
    paired_frames: list[pd.DataFrame] = []
    overlap_frames: list[pd.DataFrame] = []
    for candidate in (V4_B1_CANDIDATE, V4_B2_CANDIDATE):
        metrics, predictions = challenger_outputs[candidate]
        paired, gate_detail, passed = _gate(metrics, control_metrics)
        paired.insert(0, "candidate", candidate)
        overlap = _top_decile_overlap(control_predictions, predictions)
        overlap.insert(0, "candidate", candidate)
        paired_frames.append(paired)
        overlap_frames.append(overlap)
        results[candidate] = {
            "verdict": "PASS" if passed else "FAIL",
            "gate_pass": bool(passed),
            "gate_detail": gate_detail,
            "feature_columns": list(candidate_feature_columns(candidate)),
            "feature_order_sha256": feature_order_sha256(candidate_feature_columns(candidate)),
        }

    metrics_path = output_dir / "ranking_v4_b_f1_f6_metrics.csv"
    predictions_path = output_dir / "ranking_v4_b_f1_f6_predictions.parquet"
    paired_path = output_dir / "ranking_v4_b_f1_f6_paired.csv"
    overlap_path = output_dir / "ranking_v4_b_f1_f6_top_decile_overlap.csv"
    verdict_path = output_dir / "ranking_v4_b_f1_f6_verdict.json"
    runtime_path = output_dir / "ranking_v4_b_f1_f6_runtime.json"

    pd.concat(all_metrics, ignore_index=True).to_csv(metrics_path, index=False)
    pd.concat(all_predictions, ignore_index=True).to_parquet(predictions_path, index=False)
    pd.concat(paired_frames, ignore_index=True).to_csv(paired_path, index=False)
    pd.concat(overlap_frames, ignore_index=True).to_csv(overlap_path, index=False)

    survivors = [candidate for candidate, item in results.items() if item["gate_pass"]]
    verdict = {
        "status": "V4_B_FIRST_PASS_COMPLETE",
        "hypothesis_id": "V4-B-PRICE-PATH-V1",
        "control": V4_B_CONTROL,
        "challengers": results,
        "survivors": survivors,
        "integration_authorized_by_result": bool(len(survivors) == 2),
        "integration_executed": False,
        "candidate_ordinals_viewed": [15, 16, 17],
        "cumulative_historical_candidate_count_after_run": 15,
        "post_1224_materialized": False,
        "fresh_forward_accessed": False,
        "forward_marker_written": False,
        "independent_validation_claim": False,
        "probability_claim": False,
    }
    verdict_path.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    runtime = {
        "mode": "atomic_first_pass_sequential_compute_no_midrun_adaptation",
        "candidate_seconds": elapsed,
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
        verdict_path,
        runtime_path,
    ]
    artifacts = {path.name: sha256_file(path) for path in artifact_paths}
    artifacts.update(all_model_hashes)
    summary = {
        "status": verdict["status"],
        "code_commit": code_commit,
        "hypothesis_id": "V4-B-PRICE-PATH-V1",
        "candidate_ids": list(V4_B_FIRST_PASS_CANDIDATES),
        "folds": list(FOLD_NAMES),
        "cache_sha256": contract["cache"],
        "cache_manifest_sha256": contract["manifest"],
        "spec_git_blob": contract["spec_git_blob"],
        "reference_sha256": reference_hashes,
        "control_equivalence_status": equivalence["status"],
        "results": results,
        "survivors": survivors,
        "integration_candidate_materialized": False,
        "coverage": cache_manifest.get("coverage", {}),
        "artifact_sha256": artifacts,
        "post_1224_materialized": False,
        "fresh_forward_accessed": False,
        "forward_marker_written": False,
        "independent_validation_claim": False,
        "probability_claim": False,
    }
    summary_path = output_dir / "ranking_v4_b_f1_f6_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen V4-B B1/B2 first-pass historical-development comparison")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--v3-f1-f4-metrics", type=Path, required=True)
    parser.add_argument("--v3-f1-f4-predictions", type=Path, required=True)
    parser.add_argument("--v3-f5-f6-metrics", type=Path, required=True)
    parser.add_argument("--v3-f5-f6-predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_v4b_first_pass(
        cache_path=args.cache,
        cache_manifest_path=args.cache_manifest,
        spec_path=args.spec,
        v3_f1_f4_metrics_path=args.v3_f1_f4_metrics,
        v3_f1_f4_predictions_path=args.v3_f1_f4_predictions,
        v3_f5_f6_metrics_path=args.v3_f5_f6_metrics,
        v3_f5_f6_predictions_path=args.v3_f5_f6_predictions,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
