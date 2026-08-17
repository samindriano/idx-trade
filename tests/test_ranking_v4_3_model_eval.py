from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.ranking_v4_3_features import V4_CONTROL_FEATURE_COLUMNS
from idx_trade.ranking_v4_3_model_eval import (
    CHALLENGER,
    CONTROL,
    attach_folds,
    build_v4_regressor,
    evaluate_absolute_viability_gates,
    evaluate_head_by_date,
    evaluate_incremental_promotion_gates,
    fit_v4_head,
    fold_stratified_block_bootstrap_mean,
    model_feature_columns,
    paired_date_delta,
    percentile_ci,
    score_v4_head,
    summarize_fold_metrics,
    summarize_paired_deltas,
)
from idx_trade.ranking_v4_3_preregistration import SESSION_GEOMETRY_FEATURE_COLUMNS
from idx_trade.ranking_v4_3_target_execution import TARGET_H5_AVAILABLE


ROOT = Path(__file__).resolve().parents[1]


def synthetic_training(rows_per_date: int = 40, dates: int = 3) -> pd.DataFrame:
    records = []
    for day_index, day in enumerate(pd.date_range("2024-01-02", periods=dates, freq="B")):
        for i in range(rows_per_date):
            row = {"ticker": f"T{i:03d}", "date": day}
            for j, column in enumerate(V4_CONTROL_FEATURE_COLUMNS):
                row[column] = float((i + 1) * (j + 1) + day_index) / 1000.0
            for j, column in enumerate(SESSION_GEOMETRY_FEATURE_COLUMNS):
                row[column] = np.nan if (i + j) % 11 == 0 else float(i - j) / 50.0
            row["target_rank_h5"] = i / float(rows_per_date - 1)
            records.append(row)
    return pd.DataFrame(records)


def test_model_modes_and_effective_params_match_frozen_contract() -> None:
    assert model_feature_columns(CONTROL) == tuple(V4_CONTROL_FEATURE_COLUMNS)
    assert model_feature_columns(CHALLENGER) == (
        *V4_CONTROL_FEATURE_COLUMNS,
        *SESSION_GEOMETRY_FEATURE_COLUMNS,
    )
    control = build_v4_regressor(CONTROL)
    challenger = build_v4_regressor(CHALLENGER)
    for pipeline in (control, challenger):
        params = pipeline.named_steps["model"].get_params(deep=False)
        assert params["loss"] == "squared_error"
        assert params["learning_rate"] == 0.05
        assert params["max_iter"] == 200
        assert params["max_leaf_nodes"] == 31
        assert params["min_samples_leaf"] == 20
        assert params["l2_regularization"] == 1.0
        assert params["early_stopping"] is False
        assert params["random_state"] == 42

    control_transformer = control.named_steps["preprocess"].transformers[0][1]
    assert control_transformer.get_params()["strategy"] == "median"
    assert control_transformer.get_params()["add_indicator"] is True
    geometry_transformer = challenger.named_steps["preprocess"].transformers[1][1]
    assert geometry_transformer.get_params()["strategy"] == "median"
    assert geometry_transformer.get_params()["add_indicator"] is False


def test_synthetic_fit_and_scoring_preserve_full_population_and_rank_each_date() -> None:
    frame = synthetic_training()
    model = fit_v4_head(frame, target_column="target_rank_h5", mode=CHALLENGER)
    scored = score_v4_head(
        model,
        frame,
        mode=CHALLENGER,
        raw_score_column="raw_h5",
        alpha_column="alpha_h5",
    )
    assert len(scored) == len(frame)
    assert scored["alpha_h5"].between(0.0, 1.0).all()
    assert np.isfinite(scored["raw_h5"]).all()
    assert scored.groupby("date").size().tolist() == [40, 40, 40]


def make_scored_and_targets(observable_top: int = 30, observable_total: int = 60) -> tuple[pd.DataFrame, pd.DataFrame]:
    day = pd.Timestamp("2025-01-02")
    tickers = [f"T{i:02d}" for i in range(60)]
    scored = pd.DataFrame(
        {
            "ticker": tickers,
            "date": day,
            "alpha_h5": np.linspace(0.0, 1.0, 60),
        }
    )
    top = set(tickers[-observable_top:]) if observable_top else set()
    available = set(tickers[: max(0, observable_total - observable_top)]) | top
    ranks = np.linspace(0.0, 1.0, 60)
    targets = pd.DataFrame(
        {
            "ticker": tickers,
            "date": day,
            "target_state_h5": [TARGET_H5_AVAILABLE if ticker in available else "TARGET_DATA_UNOBSERVABLE" for ticker in tickers],
            "target_rank_h5": [rank if ticker in available else np.nan for ticker, rank in zip(tickers, ranks)],
            "r5": [rank - 0.5 if ticker in available else np.nan for ticker, rank in zip(tickers, ranks)],
        }
    )
    return scored, targets


def test_top30_is_fixed_before_observability_and_never_refilled() -> None:
    scored, targets = make_scored_and_targets(observable_top=26, observable_total=56)
    metrics = evaluate_head_by_date(scored, targets, head="H5").iloc[0]
    assert metrics["target_coverage_rate"] >= 0.90
    assert bool(metrics["date_metric_admitted"])
    assert metrics["top30_observable"] == 26
    assert not bool(metrics["top30_metric_admitted"])
    assert np.isnan(metrics["top30_mean_realized_percentile"])
    assert bool(metrics["ic_admitted"])
    assert np.isfinite(metrics["daily_ic"])


def test_date_coverage_below_90_percent_blocks_primary_metrics() -> None:
    scored, targets = make_scored_and_targets(observable_top=26, observable_total=53)
    metrics = evaluate_head_by_date(scored, targets, head="H5").iloc[0]
    assert metrics["target_coverage_rate"] < 0.90
    assert not bool(metrics["date_metric_admitted"])
    assert np.isnan(metrics["daily_ic"])
    assert np.isnan(metrics["top30_mean_realized_percentile"])
    assert np.isnan(metrics["top30_bottom30_spread"])


def validation_folds() -> pd.DataFrame:
    dates = pd.date_range("2023-01-02", periods=600, freq="B")
    return pd.DataFrame(
        {
            "fold": np.repeat(np.arange(1, 7), 100),
            "date": dates,
        }
    )


def test_fold_metric_requires_90_dates_for_each_primary_metric() -> None:
    folds = validation_folds()
    metrics = folds.copy()
    metrics["head"] = "H5"
    metrics["ic_admitted"] = True
    metrics["top30_metric_admitted"] = True
    metrics["spread_metric_admitted"] = True
    metrics["daily_ic"] = 0.05
    metrics["top30_mean_realized_percentile"] = 0.55
    metrics["top30_bottom30_spread"] = 0.06
    fold1 = metrics.index[metrics["fold"].eq(1)]
    metrics.loc[fold1[89:], "top30_metric_admitted"] = False
    metrics.loc[fold1[89:], "top30_mean_realized_percentile"] = np.nan

    attached = attach_folds(metrics.drop(columns="fold"), folds)
    fold_summary, aggregate = summarize_fold_metrics(attached)
    first = fold_summary.iloc[0]
    assert first["top30_admitted_dates"] == 89
    assert not bool(first["fold_top30_valid"])
    assert not bool(first["fold_all_primary_valid"])
    assert not bool(aggregate["all_six_primary_metric_folds_valid"])


def test_block_bootstrap_is_seeded_fold_stratified_and_finite() -> None:
    folds = validation_folds()
    folds["daily_ic"] = np.repeat(np.linspace(0.01, 0.06, 6), 100)
    first = fold_stratified_block_bootstrap_mean(folds)
    second = fold_stratified_block_bootstrap_mean(folds)
    assert len(first) == 2000
    assert np.allclose(first, second)
    low, high = percentile_ci(first)
    assert np.isfinite(low) and np.isfinite(high)
    assert low <= high


def test_paired_delta_requires_exact_dates_and_summarizes_six_folds() -> None:
    control = validation_folds()
    challenger = validation_folds()
    for frame, shift in ((control, 0.0), (challenger, 0.01)):
        frame["daily_ic"] = 0.03 + shift
        frame["top30_mean_realized_percentile"] = 0.53 + shift
        frame["top30_bottom30_spread"] = 0.04 + shift
    paired = paired_date_delta(challenger, control)
    _, aggregate = summarize_paired_deltas(paired)
    assert aggregate["all_six_paired_metric_folds_valid"] is True
    assert np.isclose(aggregate["median_fold_mean_ic_delta"], 0.01)
    assert aggregate["positive_fold_ic_delta_count"] == 6


def test_absolute_and_incremental_gate_mapping_uses_locked_thresholds() -> None:
    config = json.loads(
        (ROOT / "config" / "ranking_v4_3_preregistration.json").read_text(
            encoding="utf-8"
        )
    )
    absolute = {
        "all_six_primary_metric_folds_valid": True,
        "positive_fold_count": 6,
        "median_fold_mean_daily_ic": 0.04,
        "q25_fold_mean_daily_ic": 0.02,
        "median_fold_top30_mean_realized_percentile": 0.55,
        "median_fold_top30_bottom30_spread": 0.06,
        "q25_fold_top30_bottom30_spread": 0.02,
    }
    result = evaluate_absolute_viability_gates(
        head="CONSENSUS",
        aggregate=absolute,
        preregistration=config,
        bootstrap_ci=(0.01, 0.07),
    )
    assert result["pass"] is True

    delta = {
        "all_six_paired_metric_folds_valid": True,
        "positive_fold_ic_delta_count": 6,
        "median_fold_mean_ic_delta": 0.01,
        "q25_fold_mean_ic_delta": 0.005,
        "median_fold_top30_percentile_delta": 0.01,
        "median_fold_top30_bottom30_spread_delta": 0.02,
    }
    promotion = evaluate_incremental_promotion_gates(
        h5_delta=delta,
        h10_delta=delta,
        consensus_delta=delta,
        consensus_bootstrap_delta_ci=(0.001, 0.02),
        challenger_absolute_pass=True,
        preregistration=config,
    )
    assert promotion["pass"] is True
