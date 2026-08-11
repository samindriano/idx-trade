import numpy as np
import pandas as pd

from idx_trade.ohlcv_o1_research import HGB_PARAMS, V3_B_FEATURE_COLUMNS, feature_order_hash
from idx_trade.ohlcv_o2_minimality import (
    BASELINE_MODEL,
    MODEL_FEATURES,
    MODEL_ORDER,
    O2_FULL_3,
    O2_GEOMETRY_FEATURES,
    REDUCED_MODELS,
    _minimality_diagnostics,
    minimality_hgb_pipeline,
)


def test_minimality_model_order_and_feature_sets_are_exact() -> None:
    assert MODEL_ORDER == (
        BASELINE_MODEL,
        O2_FULL_3,
        "O2_SINGLE_POSITION",
        "O2_SINGLE_TO_HIGH",
        "O2_SINGLE_TO_LOW",
        "O2_PAIR_POSITION_HIGH",
        "O2_PAIR_POSITION_LOW",
        "O2_PAIR_HIGH_LOW",
    )
    assert REDUCED_MODELS == MODEL_ORDER[2:]
    assert O2_GEOMETRY_FEATURES == ("open_position", "open_to_high", "open_to_low")
    assert MODEL_FEATURES[BASELINE_MODEL] == V3_B_FEATURE_COLUMNS
    assert MODEL_FEATURES[O2_FULL_3][-3:] == O2_GEOMETRY_FEATURES
    assert MODEL_FEATURES["O2_SINGLE_POSITION"][-1] == "open_position"
    assert MODEL_FEATURES["O2_SINGLE_TO_HIGH"][-1] == "open_to_high"
    assert MODEL_FEATURES["O2_SINGLE_TO_LOW"][-1] == "open_to_low"
    assert MODEL_FEATURES["O2_PAIR_POSITION_HIGH"][-2:] == ("open_position", "open_to_high")
    assert MODEL_FEATURES["O2_PAIR_POSITION_LOW"][-2:] == ("open_position", "open_to_low")
    assert MODEL_FEATURES["O2_PAIR_HIGH_LOW"][-2:] == ("open_to_high", "open_to_low")
    assert feature_order_hash(MODEL_FEATURES[BASELINE_MODEL]) == "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"


def test_all_minimality_models_use_the_same_frozen_hgb_contract() -> None:
    for columns in MODEL_FEATURES.values():
        pipeline = minimality_hgb_pipeline(columns)
        estimator = pipeline.named_steps["model"]
        assert estimator.get_params()["learning_rate"] == HGB_PARAMS["learning_rate"]
        assert estimator.get_params()["max_iter"] == HGB_PARAMS["max_iter"]
        assert estimator.get_params()["max_leaf_nodes"] == HGB_PARAMS["max_leaf_nodes"]
        assert estimator.get_params()["l2_regularization"] == HGB_PARAMS["l2_regularization"]
        assert estimator.get_params()["random_state"] == HGB_PARAMS["random_state"]
        assert pipeline.named_steps["preprocess"].transformers[0][1].named_steps["impute"].keep_empty_features is True


def test_minimality_diagnostics_keep_final_choice_undecided() -> None:
    models = list(MODEL_ORDER)
    metrics = pd.DataFrame(
        [
            {"model": model, "fold": f"V2F{i}", "pr_auc": 0.40 + (0.01 if model != BASELINE_MODEL else 0.0), "roc_auc": 0.53, "q5_minus_q1": 0.05, "paired_pr_auc_vs_baseline": np.nan if model == BASELINE_MODEL else 0.01, "paired_pr_auc_vs_o2_full_3": np.nan}
            for model in models
            for i in range(1, 7)
        ]
    )
    aggregate = pd.DataFrame(
        [{"model": model, "mean_pr_auc": 0.40 + (0.01 if model != BASELINE_MODEL else 0.0), "median_roc_auc": 0.53, "median_q5_minus_q1": 0.05} for model in models]
    )
    diagnostics = _minimality_diagnostics(metrics, aggregate)
    assert len(diagnostics) == 7
    assert "final_representation" not in diagnostics.columns
