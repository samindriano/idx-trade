from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.ranking_v3_structure_lite import V3_B_FEATURE_COLUMNS
from idx_trade.ranking_v4_price_path import (
    V4_B1_CANDIDATE,
    V4_B1_MODEL_FEATURE_COLUMNS,
    V4_B2_CANDIDATE,
    V4_B2_MODEL_FEATURE_COLUMNS,
    V4_B_CONTROL,
    V4_B_FIRST_PASS_CANDIDATES,
    assert_first_pass_candidate_set,
    assert_historical_boundary,
    candidate_model,
)
from idx_trade.ranking_v4_price_path_run import FOLD_NAMES, METRIC_COLUMNS, _gate
from idx_trade.research_baselines import (
    RANDOM_SEED,
    TREE_L2,
    TREE_LEARNING_RATE,
    TREE_MAX_ITER,
    TREE_MAX_LEAF_NODES,
)
from idx_trade.research_v4_price_path import (
    V4_B1_FEATURE_COLUMNS,
    V4_B2_FEATURE_COLUMNS,
    build_price_path_features,
)


def _calendar(n: int = 40) -> pd.DatetimeIndex:
    return pd.bdate_range("2025-01-02", periods=n)


def _panel(n: int = 40, *, flat: bool = False) -> pd.DataFrame:
    dates = _calendar(n)
    if flat:
        close = np.full(n, 100.0)
    else:
        close = 100.0 + np.arange(n, dtype=float)
    return pd.DataFrame(
        {
            "ticker": "AAA",
            "date": dates,
            "high": close + 1.0,
            "low": close - 3.0,
            "close": close,
        }
    )


def test_v4b_feature_names_and_exact_v3_prefix() -> None:
    assert len(V3_B_FEATURE_COLUMNS) == 33
    assert len(V4_B1_FEATURE_COLUMNS) == 3
    assert len(V4_B2_FEATURE_COLUMNS) == 3
    assert len(V4_B1_MODEL_FEATURE_COLUMNS) == 36
    assert len(V4_B2_MODEL_FEATURE_COLUMNS) == 36
    assert tuple(V4_B1_MODEL_FEATURE_COLUMNS[:33]) == tuple(V3_B_FEATURE_COLUMNS)
    assert tuple(V4_B2_MODEL_FEATURE_COLUMNS[:33]) == tuple(V3_B_FEATURE_COLUMNS)


def test_v4b_model_reuses_frozen_hgb_parameters() -> None:
    for candidate in (V4_B_CONTROL, V4_B1_CANDIDATE, V4_B2_CANDIDATE):
        pipe = candidate_model(candidate)
        model = pipe.named_steps["model"]
        assert model.learning_rate == TREE_LEARNING_RATE
        assert model.max_iter == TREE_MAX_ITER
        assert model.max_leaf_nodes == TREE_MAX_LEAF_NODES
        assert model.l2_regularization == TREE_L2
        assert model.random_state == RANDOM_SEED


def test_monotonic_path_is_efficient_and_acceptance_is_positive() -> None:
    features = build_price_path_features(_panel(), _calendar(), max_signal_session_index=40)
    row = features[features["signal_session_index"].eq(30)].iloc[0]
    assert row["v4b_path_efficiency_5"] == pytest.approx(1.0)
    assert row["v4b_path_efficiency_20"] == pytest.approx(1.0)
    assert 0.0 < row["v4b_largest_move_share_20"] < 1.0
    assert row["v4b_range_acceptance_mean_5"] == pytest.approx(0.5)
    assert row["v4b_range_acceptance_mean_20"] == pytest.approx(0.5)
    assert row["v4b_extreme_close_balance_5"] == pytest.approx(1.0)


def test_flat_path_has_zero_efficiency_and_zero_largest_share() -> None:
    features = build_price_path_features(_panel(flat=True), _calendar(), max_signal_session_index=40)
    row = features[features["signal_session_index"].eq(30)].iloc[0]
    assert row["v4b_path_efficiency_5"] == pytest.approx(0.0)
    assert row["v4b_path_efficiency_20"] == pytest.approx(0.0)
    assert row["v4b_largest_move_share_20"] == pytest.approx(0.0)


def test_missing_official_session_breaks_exact_path_and_exact_five_acceptance() -> None:
    panel = _panel()
    missing_date = _calendar()[24]
    panel = panel[~panel["date"].eq(missing_date)].copy()
    features = build_price_path_features(panel, _calendar(), max_signal_session_index=40)
    row = features[features["signal_session_index"].eq(27)].iloc[0]
    assert np.isnan(row["v4b_path_efficiency_5"])
    assert np.isnan(row["v4b_range_acceptance_mean_5"])
    assert np.isnan(row["v4b_extreme_close_balance_5"])


def test_zero_range_bar_is_missing_for_acceptance_not_neutral() -> None:
    panel = _panel()
    target_date = _calendar()[29]
    mask = panel["date"].eq(target_date)
    panel.loc[mask, "high"] = panel.loc[mask, "close"]
    panel.loc[mask, "low"] = panel.loc[mask, "close"]
    features = build_price_path_features(panel, _calendar(), max_signal_session_index=40)
    row = features[features["signal_session_index"].eq(30)].iloc[0]
    assert np.isnan(row["v4b_range_acceptance_mean_5"])
    assert np.isnan(row["v4b_extreme_close_balance_5"])
    assert np.isfinite(row["v4b_range_acceptance_mean_20"])


def test_future_rows_do_not_change_prior_features() -> None:
    panel = _panel()
    full = build_price_path_features(panel, _calendar(), max_signal_session_index=40)
    truncated = build_price_path_features(panel.iloc[:30].copy(), _calendar(), max_signal_session_index=40)
    left = full[full["signal_session_index"].le(30)].reset_index(drop=True)
    right = truncated.reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right)


def test_feature_builder_rejects_outcome_columns() -> None:
    panel = _panel()
    panel["binary_target"] = 1
    with pytest.raises(ValueError, match="label/outcome"):
        build_price_path_features(panel, _calendar(), max_signal_session_index=40)


def test_first_pass_contract_blocks_integration_and_session_1225() -> None:
    assert_first_pass_candidate_set(V4_B_FIRST_PASS_CANDIDATES)
    with pytest.raises(RuntimeError):
        assert_first_pass_candidate_set((*V4_B_FIRST_PASS_CANDIDATES, "V4-B-INTEGRATION"))
    with pytest.raises(PermissionError):
        assert_historical_boundary(pd.DataFrame({"signal_session_index": [1224, 1225]}))


def _metric_frame(candidate: str, *, pr_improvement: float, spread_improvement: float, roc_change: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    controls = []
    challengers = []
    for fold in FOLD_NAMES:
        control = {
            "candidate": "control",
            "fold": fold,
            "positive_rate": 0.40,
            "pr_auc": 0.43,
            "pr_auc_delta_vs_base": 0.03,
            "roc_auc": 0.53,
            "q1_tp_rate": 0.36,
            "q5_tp_rate": 0.44,
            "q5_minus_q1": 0.08,
            "top_decile_tp_rate": 0.46,
            "top_decile_lift": 0.06,
        }
        challenger = dict(control)
        challenger["candidate"] = candidate
        challenger["pr_auc"] += pr_improvement
        challenger["pr_auc_delta_vs_base"] += pr_improvement
        challenger["roc_auc"] += roc_change
        challenger["q5_tp_rate"] += spread_improvement
        challenger["q5_minus_q1"] += spread_improvement
        controls.append(control)
        challengers.append(challenger)
    return pd.DataFrame(challengers), pd.DataFrame(controls)


def test_v4b_gate_matches_frozen_v4a_thresholds() -> None:
    candidate, control = _metric_frame(
        V4_B1_CANDIDATE,
        pr_improvement=0.002,
        spread_improvement=0.005,
        roc_change=0.0,
    )
    paired, detail, passed = _gate(candidate, control)
    assert len(paired) == 6
    assert passed
    assert detail["median_pr_auc_improvement"] == pytest.approx(0.002)

    candidate_bad = candidate.copy()
    bad_mask = candidate_bad["fold"].isin(("V2F1", "V2F2"))
    candidate_bad.loc[bad_mask, "pr_auc"] = control.loc[bad_mask, "pr_auc"].to_numpy() - 0.004
    candidate_bad.loc[bad_mask, "pr_auc_delta_vs_base"] = (
        candidate_bad.loc[bad_mask, "pr_auc"] - candidate_bad.loc[bad_mask, "positive_rate"]
    )
    _, detail_bad, passed_bad = _gate(candidate_bad, control)
    assert not passed_bad
    assert detail_bad["paired_pr_nonnegative_folds"] == 4


def test_metric_contract_has_expected_fields() -> None:
    assert set(METRIC_COLUMNS) == {
        "positive_rate",
        "pr_auc",
        "pr_auc_delta_vs_base",
        "roc_auc",
        "q1_tp_rate",
        "q5_tp_rate",
        "q5_minus_q1",
        "top_decile_tp_rate",
        "top_decile_lift",
    }
