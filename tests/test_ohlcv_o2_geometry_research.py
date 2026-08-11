import numpy as np
import pandas as pd

from idx_trade.ohlcv_o1_research import HGB_PARAMS, V3_B_FEATURE_COLUMNS, feature_order_hash
from idx_trade.ohlcv_o2_geometry_research import (
    BASELINE_MODEL,
    O2_FEATURE_COLUMNS,
    O2_GEOMETRY_FEATURES,
    O2_MODEL,
    _o2_survivor,
    o2_hgb_pipeline,
)


def test_o2_geometry_order_is_exactly_the_frozen_three_features() -> None:
    assert O2_GEOMETRY_FEATURES == ("open_position", "open_to_high", "open_to_low")
    assert O2_FEATURE_COLUMNS[: len(V3_B_FEATURE_COLUMNS)] == V3_B_FEATURE_COLUMNS
    assert O2_FEATURE_COLUMNS[-3:] == O2_GEOMETRY_FEATURES
    assert feature_order_hash(O2_FEATURE_COLUMNS) == "a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f"


def test_o2_baseline_and_challenger_use_identical_frozen_hgb_contract() -> None:
    baseline = o2_hgb_pipeline(V3_B_FEATURE_COLUMNS)
    challenger = o2_hgb_pipeline(O2_FEATURE_COLUMNS)
    for model in (baseline, challenger):
        estimator = model.named_steps["model"]
        assert estimator.get_params()["learning_rate"] == HGB_PARAMS["learning_rate"]
        assert estimator.get_params()["max_iter"] == HGB_PARAMS["max_iter"]
        assert estimator.get_params()["max_leaf_nodes"] == HGB_PARAMS["max_leaf_nodes"]
        assert estimator.get_params()["l2_regularization"] == HGB_PARAMS["l2_regularization"]
        assert estimator.get_params()["random_state"] == HGB_PARAMS["random_state"]
        assert model.named_steps["preprocess"].transformers[0][1].named_steps["impute"].keep_empty_features is True


def test_o2_survivor_requires_positive_lower_quartile() -> None:
    metrics = pd.DataFrame(
        [
            {"model": BASELINE_MODEL, "fold": f"V2F{i}", "pr_auc": 0.40, "pr_auc_minus_prevalence": 0.02, "roc_auc": 0.53, "q5_minus_q1": 0.05, "top_decile_lift": 0.02, "paired_pr_auc_vs_baseline": np.nan}
            for i in range(1, 7)
        ]
        + [
            {"model": O2_MODEL, "fold": f"V2F{i}", "pr_auc": 0.40 + delta, "pr_auc_minus_prevalence": 0.02, "roc_auc": 0.53, "q5_minus_q1": 0.05, "top_decile_lift": 0.02, "paired_pr_auc_vs_baseline": delta}
                for i, delta in enumerate((0.01, 0.01, 0.01, -0.01, -0.01, 0.02), start=1)
        ]
    )
    aggregate = pd.DataFrame(
        [
            {"model": BASELINE_MODEL, "median_roc_auc": 0.53, "median_q5_minus_q1": 0.05},
            {"model": O2_MODEL, "median_roc_auc": 0.53, "median_q5_minus_q1": 0.05},
        ]
    )
    decision, table = _o2_survivor(metrics, aggregate)
    assert decision == "O2_NO_SURVIVOR"
    assert float(table.loc[0, "q25_paired_pr_auc"]) <= 0.0
