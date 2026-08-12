import numpy as np
import pandas as pd
import pytest

from idx_trade.o2_v2_common_support_comparator import (
    O2_FEATURE_COLUMNS,
    O2_MODEL,
    V2_FEATURE_COLUMNS,
    V2_MODEL,
    comparator_hgb_pipeline,
    comparator_verdict,
)
from idx_trade.ohlcv_o1_research import HGB_PARAMS, V3_B_FEATURE_COLUMNS, feature_order_hash


def _aggregate():
    return pd.DataFrame(
        [
            {"model": V2_MODEL, "median_roc_auc": 0.60, "median_q5_minus_q1": 0.10},
            {"model": O2_MODEL, "median_roc_auc": 0.61, "median_q5_minus_q1": 0.11},
        ]
    )


def test_frozen_comparator_feature_orders_and_parameters():
    assert V2_FEATURE_COLUMNS == V3_B_FEATURE_COLUMNS[:25]
    assert len(V2_FEATURE_COLUMNS) == 25
    assert O2_FEATURE_COLUMNS == (*V3_B_FEATURE_COLUMNS, "open_position", "open_to_high", "open_to_low")
    assert feature_order_hash(V2_FEATURE_COLUMNS) == "1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72"
    assert feature_order_hash(O2_FEATURE_COLUMNS) == "a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f"
    for columns in (V2_FEATURE_COLUMNS, O2_FEATURE_COLUMNS):
        pipeline = comparator_hgb_pipeline(columns)
        estimator = pipeline.named_steps["model"]
        for name, value in HGB_PARAMS.items():
            assert estimator.get_params()[name] == value
        imputer = pipeline.named_steps["preprocess"].transformers[0][1].named_steps["impute"]
        assert imputer.strategy == "median"
        assert imputer.add_indicator is True
        assert imputer.keep_empty_features is True


def test_comparator_rejects_unfrozen_feature_order():
    with pytest.raises(ValueError):
        comparator_hgb_pipeline((*V2_FEATURE_COLUMNS, "open_position"))


def test_frozen_verdict_requires_four_positive_folds_and_no_double_guardrail_reversal():
    rows = []
    for fold, delta in zip([f"V2F{i}" for i in range(1, 7)], [0.01, 0.02, 0.03, 0.04, -0.01, -0.02]):
        rows.append({"level": "fold", "fold": fold, "pr_auc_delta_o2_minus_v2": delta})
    verdict, diagnostics = comparator_verdict(pd.DataFrame(rows), _aggregate())
    assert verdict == "O2_DIRECT_V2_COMMON_SUPPORT_NOT_ESTABLISHED"
    assert diagnostics["positive_paired_pr_auc_folds"] == 4
    assert diagnostics["lower_quartile_paired_pr_auc_delta"] < 0.0


def test_frozen_verdict_can_establish_direct_o2_better():
    rows = [
        {"level": "fold", "fold": f"V2F{i}", "pr_auc_delta_o2_minus_v2": value}
        for i, value in enumerate([0.01, 0.02, 0.03, 0.04, 0.05, 0.06], start=1)
    ]
    verdict, diagnostics = comparator_verdict(pd.DataFrame(rows), _aggregate())
    assert verdict == "O2_DIRECT_V2_COMMON_SUPPORT_BETTER"
    assert diagnostics["positive_paired_pr_auc_folds"] == 6
