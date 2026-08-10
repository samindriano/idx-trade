from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.ranking_v3_structure_lite import V3_B_FEATURE_COLUMNS
from idx_trade.ranking_v4_cross_sectional_context import (
    MAX_V4_C_HISTORICAL_SIGNAL_INDEX,
    V4_C_CHALLENGER,
    V4_C_CONTROL,
    V4_C_FIRST_PASS_CANDIDATES,
    V4_C_MODEL_FEATURE_COLUMNS,
    assert_first_pass_candidate_set,
    assert_historical_boundary,
    candidate_feature_columns,
    candidate_model,
)
from idx_trade.ranking_v4_cross_sectional_context_run import _gate as v4c_gate
from idx_trade.ranking_v4_participation_run import _gate as v4a_gate
from idx_trade.research_v2_validation import RANKING_V2_FOLDS
from idx_trade.research_v4_cross_sectional_context import (
    MIN_CROSS_SECTION,
    V4_C_FEATURE_COLUMNS,
    _iqr,
    build_cross_sectional_context_features,
)


def _panel(*, tickers: int = 55, sessions_count: int = 35) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    sessions = pd.bdate_range("2024-01-02", periods=sessions_count)
    rows: list[dict[str, object]] = []
    for ticker_index in range(tickers):
        ticker = f"T{ticker_index:03d}"
        for day, date in enumerate(sessions):
            drift = 0.04 + ticker_index * 0.0015
            oscillation = np.sin(day / 3.0 + ticker_index * 0.17) * (
                0.25 + ticker_index * 0.004
            )
            close = 100.0 + ticker_index * 0.2 + day * drift + oscillation
            high = close * (1.010 + ticker_index * 0.00002)
            low = close * (0.991 - ticker_index * 0.00001)
            regular_value = 2_000_000_000.0 + ticker_index * 15_000_000.0 + day * 1_000_000.0
            volume = regular_value / close
            rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "regular_market_value": regular_value,
                }
            )
    return pd.DataFrame(rows), sessions


def test_iqr_uses_frozen_linear_quantiles_and_minimum_cross_section() -> None:
    values = pd.Series(np.arange(100, dtype=float))
    expected = float(
        np.quantile(values.to_numpy(), 0.75, method="linear")
        - np.quantile(values.to_numpy(), 0.25, method="linear")
    )
    assert _iqr(values) == pytest.approx(expected)
    assert np.isnan(_iqr(pd.Series(np.arange(MIN_CROSS_SECTION - 1, dtype=float))))


def test_context_builder_produces_one_full_primary_universe_row_per_date() -> None:
    panel, sessions = _panel()
    context = build_cross_sectional_context_features(
        panel,
        sessions,
        max_signal_session_index=len(sessions),
    )
    assert not context["date"].duplicated().any()
    last = context.iloc[-1]
    assert int(last["v4c_primary_liquid_count"]) == 55
    for column in V4_C_FEATURE_COLUMNS:
        assert np.isfinite(float(last[column]))
        assert float(last[column]) >= 0.0


def test_context_builder_returns_missing_dispersion_below_frozen_cross_section_minimum() -> None:
    panel, sessions = _panel(tickers=MIN_CROSS_SECTION - 1)
    context = build_cross_sectional_context_features(
        panel,
        sessions,
        max_signal_session_index=len(sessions),
    )
    last = context.iloc[-1]
    assert int(last["v4c_primary_liquid_count"]) == MIN_CROSS_SECTION - 1
    assert last[list(V4_C_FEATURE_COLUMNS)].isna().all()


def test_context_builder_is_causal_under_appended_future_rows() -> None:
    panel, sessions = _panel(sessions_count=35)
    earlier = build_cross_sectional_context_features(
        panel,
        sessions,
        max_signal_session_index=30,
    )
    later = build_cross_sectional_context_features(
        panel,
        sessions,
        max_signal_session_index=35,
    )
    left = earlier[earlier["signal_session_index"] <= 30].reset_index(drop=True)
    right = later[later["signal_session_index"] <= 30].reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right, check_exact=False, rtol=0.0, atol=1e-12)


def test_context_builder_rejects_outcome_columns() -> None:
    panel, sessions = _panel()
    panel["binary_target"] = 1
    with pytest.raises(ValueError, match="label/outcome"):
        build_cross_sectional_context_features(
            panel,
            sessions,
            max_signal_session_index=len(sessions),
        )


def test_v4c_candidate_preserves_exact_v3b_prefix_and_hgb_template() -> None:
    assert candidate_feature_columns(V4_C_CONTROL) == tuple(V3_B_FEATURE_COLUMNS)
    assert V4_C_MODEL_FEATURE_COLUMNS[: len(V3_B_FEATURE_COLUMNS)] == tuple(V3_B_FEATURE_COLUMNS)
    assert V4_C_MODEL_FEATURE_COLUMNS[-len(V4_C_FEATURE_COLUMNS) :] == tuple(V4_C_FEATURE_COLUMNS)
    assert len(candidate_feature_columns(V4_C_CHALLENGER)) == len(V3_B_FEATURE_COLUMNS) + 4

    model = candidate_model(V4_C_CHALLENGER).named_steps["model"]
    assert model.learning_rate == pytest.approx(0.05)
    assert model.max_iter == 200
    assert model.max_leaf_nodes == 31
    assert model.l2_regularization == pytest.approx(1.0)
    assert model.random_state == 42


def test_v4c_first_pass_has_only_control_and_one_challenger() -> None:
    assert V4_C_FIRST_PASS_CANDIDATES == (V4_C_CONTROL, V4_C_CHALLENGER)
    assert_first_pass_candidate_set(V4_C_FIRST_PASS_CANDIDATES)
    with pytest.raises(RuntimeError):
        assert_first_pass_candidate_set((*V4_C_FIRST_PASS_CANDIDATES, "V4-C-INTEGRATION"))


def test_v4c_session_1225_is_hard_blocked() -> None:
    ok = pd.DataFrame({"signal_session_index": [MAX_V4_C_HISTORICAL_SIGNAL_INDEX]})
    assert_historical_boundary(ok)
    blocked = pd.DataFrame({"signal_session_index": [MAX_V4_C_HISTORICAL_SIGNAL_INDEX + 1]})
    with pytest.raises(PermissionError):
        assert_historical_boundary(blocked)


def _metric_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    control_rows: list[dict[str, float | str]] = []
    candidate_rows: list[dict[str, float | str]] = []
    for idx, fold in enumerate(RANKING_V2_FOLDS):
        base = 0.35 + idx * 0.01
        control_rows.append(
            {
                "fold": fold.name,
                "positive_rate": base,
                "pr_auc": base + 0.02,
                "pr_auc_delta_vs_base": 0.02,
                "roc_auc": 0.52,
                "q1_tp_rate": base - 0.03,
                "q5_tp_rate": base + 0.03,
                "q5_minus_q1": 0.06,
                "top_decile_tp_rate": base + 0.04,
                "top_decile_lift": 0.04,
            }
        )
        candidate_rows.append(
            {
                "fold": fold.name,
                "positive_rate": base,
                "pr_auc": base + 0.022,
                "pr_auc_delta_vs_base": 0.022,
                "roc_auc": 0.522,
                "q1_tp_rate": base - 0.032,
                "q5_tp_rate": base + 0.034,
                "q5_minus_q1": 0.066,
                "top_decile_tp_rate": base + 0.045,
                "top_decile_lift": 0.045,
            }
        )
    return pd.DataFrame(candidate_rows), pd.DataFrame(control_rows)


def test_v4c_gate_is_semantically_identical_to_frozen_v4a_gate() -> None:
    candidate, control = _metric_frames()
    paired_c, detail_c, passed_c = v4c_gate(candidate, control)
    paired_a, detail_a, passed_a = v4a_gate(candidate, control)
    pd.testing.assert_frame_equal(paired_c, paired_a)
    assert detail_c == detail_a
    assert passed_c == passed_a
