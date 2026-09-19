import pandas as pd
import pytest

from idx_trade.alpha_challenger_price_trend_v1 import (
    build_price_trend_alpha_overlay,
    fixed_quality_blend,
)


def test_maps_frozen_states_and_neutral_indeterminate():
    frame = pd.DataFrame(
        {
            "ticker": ["aaa", "BBB", "ccc"],
            "feature_session": ["2026-09-17"] * 3,
            "trend_state": ["UPTREND", "DOWNTREND", "INDETERMINATE"],
            "state_contract_version": ["PRICE_TREND_CONFIRMATION_STATE_V1"] * 3,
            "outcome_blind": [True] * 3,
            "model_fitted": [False] * 3,
            "trade_recommendation": [False] * 3,
        }
    )

    result = build_price_trend_alpha_overlay(frame)

    assert result["ticker"].tolist() == ["AAA", "BBB", "CCC"]
    assert result["price_trend_quality"].tolist() == pytest.approx([1.0, 0.0, 0.5])
    assert result["price_trend_available"].tolist() == [True, True, False]


def test_fixed_blend_is_higher_is_better():
    result = fixed_quality_blend(pd.Series([1.0, 0.0]), pd.Series([0.0, 1.0]))
    assert result.tolist() == pytest.approx([0.9, 0.1])


def test_rejects_non_blind_or_unknown_state():
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "feature_session": ["2026-09-17"],
            "trend_state": ["UPTREND"],
            "outcome_blind": [False],
        }
    )
    with pytest.raises(ValueError, match="outcome-blind"):
        build_price_trend_alpha_overlay(frame)
