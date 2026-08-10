from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.ranking_v3_structure_lite import V3_B_FEATURE_COLUMNS
from idx_trade.ranking_v4_participation import (
    MAX_V4_A_HISTORICAL_SIGNAL_INDEX,
    V4_A1_CANDIDATE,
    V4_A1_MODEL_FEATURE_COLUMNS,
    V4_A2_CANDIDATE,
    V4_A2_MODEL_FEATURE_COLUMNS,
    V4_A_CONTROL,
    V4_A_CONTROL_FEATURE_COLUMNS,
    V4_A_FIRST_PASS_CANDIDATES,
    assert_first_pass_candidate_set,
    assert_historical_boundary,
    candidate_feature_columns,
    candidate_model,
)
from idx_trade.research_v4_participation import (
    V4_A1_FEATURE_COLUMNS,
    V4_A2_FEATURE_COLUMNS,
    V4_A_FEATURE_COLUMNS,
    _centered_log_ratio,
    build_participation_quality_features,
)


def _panel(periods: int = 40, *, value: float = 100_000_000.0) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    dates = pd.bdate_range("2026-01-02", periods=periods)
    close = 100.0 * np.power(1.01, np.arange(periods, dtype=float))
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"] * periods,
            "date": dates,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(periods, 1_000_000.0),
            "regular_market_value": np.full(periods, value),
            "tradability_state": ["ACTIVE"] * periods,
        }
    )
    return frame, dates


def test_v4_a_feature_order_preserves_exact_v3_b_prefix() -> None:
    assert tuple(V4_A_CONTROL_FEATURE_COLUMNS) == tuple(V3_B_FEATURE_COLUMNS)
    assert tuple(V4_A1_MODEL_FEATURE_COLUMNS[: len(V3_B_FEATURE_COLUMNS)]) == tuple(
        V3_B_FEATURE_COLUMNS
    )
    assert tuple(V4_A2_MODEL_FEATURE_COLUMNS[: len(V3_B_FEATURE_COLUMNS)]) == tuple(
        V3_B_FEATURE_COLUMNS
    )
    assert tuple(V4_A1_MODEL_FEATURE_COLUMNS[len(V3_B_FEATURE_COLUMNS) :]) == tuple(
        V4_A1_FEATURE_COLUMNS
    )
    assert tuple(V4_A2_MODEL_FEATURE_COLUMNS[len(V3_B_FEATURE_COLUMNS) :]) == tuple(
        V4_A2_FEATURE_COLUMNS
    )
    assert len(V4_A_CONTROL_FEATURE_COLUMNS) == 33
    assert len(V4_A1_MODEL_FEATURE_COLUMNS) == 36
    assert len(V4_A2_MODEL_FEATURE_COLUMNS) == 37


def test_v4_a_first_pass_has_only_control_a1_a2() -> None:
    assert V4_A_FIRST_PASS_CANDIDATES == (
        V4_A_CONTROL,
        V4_A1_CANDIDATE,
        V4_A2_CANDIDATE,
    )
    assert_first_pass_candidate_set(V4_A_FIRST_PASS_CANDIDATES)
    with pytest.raises(RuntimeError):
        assert_first_pass_candidate_set((*V4_A_FIRST_PASS_CANDIDATES, "A1_A2_INTEGRATION"))


def test_v4_a_models_keep_frozen_hgb_parameters_and_feature_sets() -> None:
    for candidate, expected_columns in (
        (V4_A_CONTROL, V4_A_CONTROL_FEATURE_COLUMNS),
        (V4_A1_CANDIDATE, V4_A1_MODEL_FEATURE_COLUMNS),
        (V4_A2_CANDIDATE, V4_A2_MODEL_FEATURE_COLUMNS),
    ):
        assert candidate_feature_columns(candidate) == tuple(expected_columns)
        model = candidate_model(candidate)
        estimator = model.named_steps["model"]
        assert estimator.learning_rate == 0.05
        assert estimator.max_iter == 200
        assert estimator.max_leaf_nodes == 31
        assert estimator.l2_regularization == 1.0
        assert estimator.random_state == 42
        columns = tuple(model.named_steps["preprocess"].transformers[0][2])
        assert columns == tuple(expected_columns)


def test_v4_a_has_no_open_dependency() -> None:
    assert all("open" not in column.lower() for column in V4_A_FEATURE_COLUMNS)
    assert all("open" not in column.lower() for column in V4_A1_MODEL_FEATURE_COLUMNS)
    assert all("open" not in column.lower() for column in V4_A2_MODEL_FEATURE_COLUMNS)


def test_centered_log_ratio_is_zero_at_own_baseline_and_finite_at_zero() -> None:
    assert _centered_log_ratio(5.0, 5.0) == pytest.approx(0.0)
    assert _centered_log_ratio(0.0, 5.0) == pytest.approx(-np.log(2.0))
    assert np.isnan(_centered_log_ratio(1.0, 0.0))


def test_constant_participation_path_has_expected_neutral_features() -> None:
    panel, sessions = _panel(40)
    result = build_participation_quality_features(
        panel, sessions, max_signal_session_index=40
    )
    row = result.loc[result["signal_session_index"].eq(30)].iloc[0]
    assert row["v4a_range_impact_logrel20"] == pytest.approx(0.0, abs=1e-12)
    assert row["v4a_close_impact_logrel20"] == pytest.approx(0.0, abs=1e-12)
    assert row["v4a_high_range_impact_fraction_5"] == pytest.approx(0.0)
    assert row["v4a_value_persistence_fraction_5"] == pytest.approx(0.0)
    assert row["v4a_value_acceleration_log_5v20"] == pytest.approx(0.0)
    assert row["v4a_signed_value_5"] == pytest.approx(1.0)
    assert row["v4a_signed_value_20"] == pytest.approx(1.0)


def test_value_acceleration_detects_exact_five_session_build() -> None:
    panel, sessions = _panel(30)
    panel.loc[:24, "regular_market_value"] = 100.0
    panel.loc[25:29, "regular_market_value"] = 200.0
    result = build_participation_quality_features(
        panel, sessions, max_signal_session_index=30
    )
    row = result.loc[result["signal_session_index"].eq(30)].iloc[0]
    assert row["v4a_value_acceleration_log_5v20"] == pytest.approx(np.log(2.0))
    assert row["v4a_value_persistence_fraction_5"] == pytest.approx(1.0)


def test_exact_five_session_features_fail_closed_across_missing_official_row() -> None:
    panel, sessions = _panel(30)
    missing_date = sessions[27]
    panel = panel.loc[panel["date"].ne(missing_date)].copy()
    result = build_participation_quality_features(
        panel, sessions, max_signal_session_index=30
    )
    row = result.loc[result["signal_session_index"].eq(30)].iloc[0]
    assert np.isnan(row["v4a_high_range_impact_fraction_5"])
    assert np.isnan(row["v4a_value_persistence_fraction_5"])
    assert np.isnan(row["v4a_value_acceleration_log_5v20"])
    assert np.isnan(row["v4a_signed_value_5"])


def test_v4_a_builder_rejects_outcome_columns() -> None:
    panel, sessions = _panel(30)
    panel["binary_target"] = 1
    with pytest.raises(ValueError, match="label/outcome"):
        build_participation_quality_features(
            panel, sessions, max_signal_session_index=30
        )


def test_appending_future_rows_does_not_change_prior_v4_a_features() -> None:
    panel, sessions = _panel(40)
    prefix = build_participation_quality_features(
        panel.iloc[:30].copy(), sessions, max_signal_session_index=30
    )
    full = build_participation_quality_features(
        panel, sessions, max_signal_session_index=40
    )
    full_prefix = full.loc[full["signal_session_index"].le(30)].reset_index(drop=True)
    pd.testing.assert_frame_equal(prefix.reset_index(drop=True), full_prefix)


def test_builder_respects_requested_historical_boundary() -> None:
    panel, sessions = _panel(40)
    result = build_participation_quality_features(
        panel, sessions, max_signal_session_index=30
    )
    assert result["signal_session_index"].max() == 30
    assert result["signal_session_index"].min() == 1


def test_v4_a_historical_boundary_hard_blocks_1225_plus() -> None:
    assert_historical_boundary(
        pd.DataFrame({"signal_session_index": [1, MAX_V4_A_HISTORICAL_SIGNAL_INDEX]})
    )
    with pytest.raises(PermissionError):
        assert_historical_boundary(
            pd.DataFrame({"signal_session_index": [MAX_V4_A_HISTORICAL_SIGNAL_INDEX + 1]})
        )
