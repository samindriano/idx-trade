import numpy as np
import pandas as pd

from idx_trade.ohlcv_o1_research import (
    EXPECTED_V3_B_FEATURE_ORDER_SHA256,
    HGB_PARAMS,
    MODEL_FEATURES,
    RANKING_V2_FOLDS,
    V3_B_FEATURE_COLUMNS,
    _survivor_decision,
    evaluate_scores,
    feature_order_hash,
    hgb_pipeline,
    verify_fold_contract,
)


def test_v3_b_feature_order_is_frozen_and_open_free() -> None:
    assert len(V3_B_FEATURE_COLUMNS) == 33
    assert feature_order_hash(V3_B_FEATURE_COLUMNS) == EXPECTED_V3_B_FEATURE_ORDER_SHA256
    assert not any("open" in name.lower() for name in V3_B_FEATURE_COLUMNS)
    assert MODEL_FEATURES["O1A_OVERNIGHT"][-1] == "overnight_gap"
    assert MODEL_FEATURES["O1B_INTRADAY"][-1] == "intraday_return"
    assert MODEL_FEATURES["O1C_DECOMPOSITION"][-2:] == ("overnight_gap", "intraday_return")


def test_six_frozen_v2_folds_have_h20_and_h100_contract() -> None:
    assert [fold.name for fold in RANKING_V2_FOLDS] == [f"V2F{i}" for i in range(1, 7)]
    assert all(fold.gap_end - fold.gap_start + 1 == 20 for fold in RANKING_V2_FOLDS)
    assert all(fold.validation_end - fold.validation_start + 1 == 100 for fold in RANKING_V2_FOLDS)
    assert len(verify_fold_contract()) == 6


def test_hgb_pipeline_matches_frozen_parameters() -> None:
    model = hgb_pipeline(V3_B_FEATURE_COLUMNS)
    estimator = model.named_steps["model"]
    assert estimator.get_params()["learning_rate"] == HGB_PARAMS["learning_rate"]
    assert estimator.get_params()["max_iter"] == HGB_PARAMS["max_iter"]
    assert estimator.get_params()["max_leaf_nodes"] == HGB_PARAMS["max_leaf_nodes"]
    assert estimator.get_params()["l2_regularization"] == HGB_PARAMS["l2_regularization"]
    assert estimator.get_params()["random_state"] == HGB_PARAMS["random_state"]
    imputer = model.named_steps["preprocess"].transformers[0][1].named_steps["impute"]
    assert imputer.keep_empty_features is True


def test_evaluator_uses_frozen_within_date_buckets() -> None:
    frame = pd.DataFrame({"ticker": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"], "date": pd.Timestamp("2024-01-02"), "binary_target": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]})
    metrics = evaluate_scores(frame, np.arange(10, dtype=float))
    assert metrics["rows"] == 10
    assert metrics["q5_tp_rate"] == 1.0
    assert metrics["q1_tp_rate"] == 0.0


def test_survivor_requires_non_isolated_paired_improvement_and_guardrails() -> None:
    folds = [f"V2F{i}" for i in range(1, 7)]
    rows = []
    for model in ("V3B_COMMON_SUPPORT_BASELINE", "O1A_OVERNIGHT", "O1B_INTRADAY", "O1C_DECOMPOSITION"):
        for fold in folds:
            rows.append({"model": model, "fold": fold, "pr_auc": 0.2, "pr_auc_minus_prevalence": 0.05, "roc_auc": 0.6, "q5_minus_q1": 0.1, "top_decile_lift": 0.1, "paired_pr_auc_vs_baseline": np.nan if model.startswith("V3B") else 0.01})
    metrics = pd.DataFrame(rows)
    aggregate = pd.DataFrame([
        {"model": "V3B_COMMON_SUPPORT_BASELINE", "median_roc_auc": 0.6, "median_q5_minus_q1": 0.1},
        {"model": "O1A_OVERNIGHT", "median_roc_auc": 0.6, "median_q5_minus_q1": 0.1},
        {"model": "O1B_INTRADAY", "median_roc_auc": 0.6, "median_q5_minus_q1": 0.1},
        {"model": "O1C_DECOMPOSITION", "median_roc_auc": 0.6, "median_q5_minus_q1": 0.1},
    ])
    decision, table = _survivor_decision(metrics, aggregate)
    assert decision == "O1_SURVIVOR"
    assert bool(table.loc[0, "survivor"])
