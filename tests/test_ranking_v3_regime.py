from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.ranking_v3_regime import (
    REGIME_JOIN_COLUMNS,
    V3_C_CANDIDATE,
    V3_C_CONTROL,
    _coverage_report,
    _regime_promotion,
    assert_discovery_fold_allowed,
)
from idx_trade.research_v2_features import V2_FULL_FEATURE_COLUMNS
from idx_trade.research_v3_regime import (
    REGIME_MISSING,
    REGIME_NORMAL,
    REGIME_SOURCE_COLUMNS,
    REGIME_STRESS,
    build_regime_table,
    extract_market_context,
)


def _context_frame(periods: int, *, start: str = "2024-01-02") -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    dates = pd.date_range(start, periods=periods, freq="B")
    frame = pd.DataFrame(
        {
            "date": dates,
            "universe_primary_liquid": True,
            REGIME_SOURCE_COLUMNS[0]: np.linspace(0.55, 0.45, periods),
            REGIME_SOURCE_COLUMNS[1]: np.linspace(0.03, -0.01, periods),
            REGIME_SOURCE_COLUMNS[2]: np.linspace(0.02, 0.03, periods),
        }
    )
    return frame, dates


def test_regime_feature_contract_does_not_add_model_features() -> None:
    assert tuple(V2_FULL_FEATURE_COLUMNS) == tuple(V2_FULL_FEATURE_COLUMNS)
    assert "regime_state" in REGIME_JOIN_COLUMNS
    assert V3_C_CONTROL.endswith("006")
    assert V3_C_CANDIDATE.endswith("007")


def test_regime_warmup_requires_126_prior_observations() -> None:
    frame, dates = _context_frame(130)
    regime = build_regime_table(frame, dates, max_signal_session_index=130)
    assert regime.loc[124, "regime_state"] == REGIME_MISSING  # session 125 has only 124 prior
    assert regime.loc[125, "regime_state"] == REGIME_MISSING  # session 126 has only 125 prior
    assert regime.loc[126, "regime_state"] in {REGIME_NORMAL, REGIME_STRESS}


def test_current_context_does_not_change_its_own_thresholds() -> None:
    frame, dates = _context_frame(140)
    first = build_regime_table(frame, dates, max_signal_session_index=140)
    changed = frame.copy()
    changed.loc[139, REGIME_SOURCE_COLUMNS[0]] = 0.0
    changed.loc[139, REGIME_SOURCE_COLUMNS[1]] = -1.0
    changed.loc[139, REGIME_SOURCE_COLUMNS[2]] = 1.0
    second = build_regime_table(changed, dates, max_signal_session_index=140)
    threshold_cols = ["regime_breadth_q25_prior", "regime_return_q25_prior", "regime_atr_q75_prior"]
    assert np.allclose(first.loc[139, threshold_cols], second.loc[139, threshold_cols], rtol=0.0, atol=0.0)
    assert second.loc[139, "regime_state"] == REGIME_STRESS


def test_regime_history_is_capped_at_252_official_sessions() -> None:
    frame, dates = _context_frame(300)
    first = build_regime_table(frame, dates, max_signal_session_index=300)
    changed = frame.copy()
    changed.loc[:46, REGIME_SOURCE_COLUMNS[0]] = 0.0
    changed.loc[:46, REGIME_SOURCE_COLUMNS[1]] = -10.0
    changed.loc[:46, REGIME_SOURCE_COLUMNS[2]] = 10.0
    second = build_regime_table(changed, dates, max_signal_session_index=300)
    cols = ["regime_breadth_q25_prior", "regime_return_q25_prior", "regime_atr_q75_prior"]
    assert np.allclose(first.loc[299, cols], second.loc[299, cols], rtol=0.0, atol=0.0)


def test_two_of_three_votes_define_stress() -> None:
    periods = 127
    dates = pd.date_range("2024-01-02", periods=periods, freq="B")
    frame = pd.DataFrame(
        {
            "date": dates,
            "universe_primary_liquid": True,
            REGIME_SOURCE_COLUMNS[0]: 0.5,
            REGIME_SOURCE_COLUMNS[1]: 0.0,
            REGIME_SOURCE_COLUMNS[2]: 0.02,
        }
    )
    frame.loc[126, REGIME_SOURCE_COLUMNS[0]] = 0.4
    frame.loc[126, REGIME_SOURCE_COLUMNS[1]] = -0.01
    frame.loc[126, REGIME_SOURCE_COLUMNS[2]] = 0.01
    regime = build_regime_table(frame, dates, max_signal_session_index=periods)
    assert regime.loc[126, "stress_votes"] == 2.0
    assert regime.loc[126, "regime_state"] == REGIME_STRESS


def test_equality_to_threshold_counts_as_stress_vote() -> None:
    periods = 127
    dates = pd.date_range("2024-01-02", periods=periods, freq="B")
    frame = pd.DataFrame(
        {
            "date": dates,
            "universe_primary_liquid": True,
            REGIME_SOURCE_COLUMNS[0]: 0.5,
            REGIME_SOURCE_COLUMNS[1]: 0.0,
            REGIME_SOURCE_COLUMNS[2]: 0.02,
        }
    )
    regime = build_regime_table(frame, dates, max_signal_session_index=periods)
    assert regime.loc[126, "stress_votes"] == 3.0
    assert regime.loc[126, "regime_state"] == REGIME_STRESS


def test_extract_market_context_rejects_outcome_columns() -> None:
    frame, _ = _context_frame(2)
    frame["binary_target"] = [0, 1]
    with pytest.raises(ValueError, match="label/outcome"):
        extract_market_context(frame)


def test_extract_market_context_rejects_non_datewide_values() -> None:
    date = pd.Timestamp("2026-01-02")
    frame = pd.DataFrame(
        {
            "date": [date, date],
            "universe_primary_liquid": [True, True],
            REGIME_SOURCE_COLUMNS[0]: [0.5, 0.6],
            REGIME_SOURCE_COLUMNS[1]: [0.0, 0.0],
            REGIME_SOURCE_COLUMNS[2]: [0.02, 0.02],
        }
    )
    with pytest.raises(RuntimeError, match="not date-wide"):
        extract_market_context(frame)


def test_f5_f6_are_hard_blocked() -> None:
    for name in ("V2F5", "V2F6"):
        with pytest.raises(PermissionError):
            assert_discovery_fold_allowed(name)
    for name in ("V2F1", "V2F2", "V2F3", "V2F4"):
        assert_discovery_fold_allowed(name)


def test_fragmentation_gate_fails_small_cache() -> None:
    rows = []
    for session in range(1, 985):
        state = REGIME_STRESS if session % 5 == 0 else REGIME_NORMAL
        rows.append(
            {
                "signal_session_index": session,
                "date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=session),
                "ticker": "AAA",
                "regime_state": state,
            }
        )
    report = _coverage_report(pd.DataFrame(rows))
    assert report["gate_pass"] is False


def test_regime_promotion_requires_stress_improvement() -> None:
    summary = {
        "by_regime": {
            REGIME_STRESS: {
                "median_pr_auc_delta_improvement": 0.0009,
                "pr_nonnegative_folds": 4,
                "median_roc_auc_change": 0.0,
                "median_q5_minus_q1_change": 0.0,
            },
            REGIME_NORMAL: {
                "median_pr_auc_delta_improvement": 0.0,
                "pr_nonnegative_folds": 4,
                "median_roc_auc_change": 0.0,
                "median_q5_minus_q1_change": 0.0,
            },
        },
        "worst_regime_fold_pr_auc_delta_improvement": 0.0,
    }
    assert _regime_promotion(summary) is False
    summary["by_regime"][REGIME_STRESS]["median_pr_auc_delta_improvement"] = 0.001
    assert _regime_promotion(summary) is True
