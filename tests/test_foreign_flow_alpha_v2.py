import numpy as np
import pandas as pd
import pytest

from idx_trade.foreign_flow_alpha_v2 import (
    FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS,
    CHALLENGER_FEATURE_COLUMNS,
    V2_FEATURE_COLUMNS,
    _gate,
    _hash_columns,
    verify_flow_temporal_contract,
)


def test_frozen_v2_core_block_is_exactly_eight_features_after_clean_v2_prefix():
    assert len(FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS) == 8
    assert tuple(CHALLENGER_FEATURE_COLUMNS[:25]) == V2_FEATURE_COLUMNS
    assert tuple(CHALLENGER_FEATURE_COLUMNS[25:]) == FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS
    assert _hash_columns(V2_FEATURE_COLUMNS) == "1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72"


def _flow_fixture():
    return pd.DataFrame({"ticker": ["AAA", "AAA"], "feature_session": pd.to_datetime(["2021-01-05", "2021-01-06"]), "flow_through_session": pd.to_datetime(["2021-01-04", "2021-01-05"]), **{column: [0.1, np.nan] for column in FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS}})


def test_flow_core_requires_previous_official_session():
    flow = _flow_fixture()
    calendar = {pd.Timestamp(day): index for index, day in enumerate(pd.date_range("2021-01-01", periods=6, freq="D"), 1)}
    assert verify_flow_temporal_contract(flow, calendar) == {"rows": 2, "tickers": 1, "feature_sessions": 2}
    future = flow.copy(); future.loc[0, "flow_through_session"] = pd.Timestamp("2021-01-05")
    with pytest.raises(RuntimeError, match="t\\+1"):
        verify_flow_temporal_contract(future, calendar)


def test_gate_is_preregistered_and_has_no_rescue_path():
    base = pd.DataFrame({"fold": [f"V2F{i}" for i in range(1, 7)], "roc_auc": [0.51] * 6, "q5_minus_q1": [0.02] * 6})
    paired = pd.DataFrame({"fold": [f"V2F{i}" for i in range(1, 7)], "paired_pr_auc_delta": [0.001, 0.002, 0.003, 0.004, -0.001, 0.005], "roc_auc_delta": [0.0] * 6, "q5_minus_q1_delta": [0.0] * 6, "challenger_roc_auc": [0.51] * 6, "challenger_q5_minus_q1": [0.02] * 6})
    result = _gate(base, paired)
    assert result["verdict"] == "FOREIGN_FLOW_V2_CORE_SURVIVOR"
    assert result["aggregate"]["positive_paired_pr_auc_folds"] == 5


def test_gate_rejects_nonpositive_q25():
    base = pd.DataFrame({"fold": [f"V2F{i}" for i in range(1, 7)], "roc_auc": [0.51] * 6, "q5_minus_q1": [0.02] * 6})
    paired = pd.DataFrame({"fold": [f"V2F{i}" for i in range(1, 7)], "paired_pr_auc_delta": [0.01, 0.01, 0.01, -0.02, -0.02, -0.02], "roc_auc_delta": [0.0] * 6, "q5_minus_q1_delta": [0.0] * 6, "challenger_roc_auc": [0.51] * 6, "challenger_q5_minus_q1": [0.02] * 6})
    result = _gate(base, paired)
    assert result["verdict"] == "FOREIGN_FLOW_V2_CORE_NO_SURVIVOR"
    assert result["checks"]["q25_paired_pr_auc_gt_0"] is False
