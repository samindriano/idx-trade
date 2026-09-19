import pandas as pd
import pytest

from idx_trade.alpha_challenger_foreign_flow_transition_v1 import (
    build_foreign_flow_transition_overlay,
)


def test_builds_date_local_rank_and_neutral_missing_value():
    frame = pd.DataFrame(
        {
            "ticker": ["aaa", "BBB", "ccc", "ddd"],
            "feature_session": [
                "2026-01-02",
                "2026-01-02",
                "2026-01-02",
                "2026-01-03",
            ],
            "foreign_weighted_persistence_5": [0.8, -0.2, None, 0.1],
            "foreign_weighted_persistence_20": [0.2, 0.1, 0.0, 0.1],
        }
    )

    result = build_foreign_flow_transition_overlay(frame)

    assert result.loc[0, "ticker"] == "AAA"
    assert result.loc[0, "foreign_flow_transition_score"] == pytest.approx(0.6)
    assert result.loc[1, "foreign_flow_transition_score"] == pytest.approx(-0.3)
    assert result.loc[0, "foreign_flow_transition_rank"] == pytest.approx(1.0)
    assert result.loc[1, "foreign_flow_transition_rank"] == pytest.approx(0.5)
    assert not result.loc[2, "foreign_flow_transition_available"]
    assert result.loc[2, "foreign_flow_transition_rank"] == pytest.approx(0.5)
    assert result.loc[3, "foreign_flow_transition_rank"] == pytest.approx(1.0)


def test_rejects_duplicate_ticker_session():
    frame = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "feature_session": ["2026-01-02", "2026-01-02"],
            "foreign_weighted_persistence_5": [0.1, 0.2],
            "foreign_weighted_persistence_20": [0.0, 0.0],
        }
    )

    with pytest.raises(ValueError, match="duplicate"):
        build_foreign_flow_transition_overlay(frame)


def test_requires_both_persistence_inputs():
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "feature_session": ["2026-01-02"],
            "foreign_weighted_persistence_5": [0.1],
        }
    )

    with pytest.raises(KeyError, match="foreign_weighted_persistence_20"):
        build_foreign_flow_transition_overlay(frame)
