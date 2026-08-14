from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.foreign_flow_features_v2 import build_foreign_flow_representation_v2


def _frames(days: int = 150) -> tuple[pd.DatetimeIndex, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sessions = pd.date_range("2025-01-02", periods=days, freq="B")
    flow_rows: list[dict[str, object]] = []
    volume_rows: list[dict[str, object]] = []
    context_rows: list[dict[str, object]] = []
    for ticker_index, ticker in enumerate(("AAA", "BBB")):
        for index, day in enumerate(sessions):
            net = index + 1 if ticker == "AAA" else -(index + 1)
            flow_rows.append(
                {
                    "ticker": ticker,
                    "session_date": day,
                    "foreign_buy": max(net, 0) + 1_000,
                    "foreign_sell": max(-net, 0) + 1_000,
                    "foreign_net": net,
                    "unit": "SHARES",
                }
            )
            volume_rows.append({"ticker": ticker, "date": day, "raw_volume": 1_000.0})
            context_rows.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "universe_primary_liquid": True,
                    "close_return_5": 0.01 * (ticker_index + 1),
                    "close_return_20": 0.02 * (ticker_index + 1),
                }
            )
    return sessions, pd.DataFrame(flow_rows), pd.DataFrame(volume_rows), pd.DataFrame(context_rows)


def _row(frame: pd.DataFrame, ticker: str, through: pd.Timestamp) -> pd.Series:
    return frame.loc[
        frame["ticker"].eq(ticker) & frame["flow_through_session"].eq(through)
    ].iloc[0]


def test_current_volume_changes_participation_but_not_historical_flow_shock() -> None:
    sessions, flow, volume, context = _frames()
    base = build_foreign_flow_representation_v2(flow, volume, context, sessions)
    before = _row(base, "AAA", sessions[30])
    assert before["feature_session"] == sessions[31]

    changed = volume.copy()
    changed.loc[
        changed["ticker"].eq("AAA") & changed["date"].eq(sessions[30]), "raw_volume"
    ] = 100_000.0
    revised = build_foreign_flow_representation_v2(flow, changed, context, sessions)
    after = _row(revised, "AAA", sessions[30])

    assert after["foreign_participation_1"] < before["foreign_participation_1"]
    assert np.isclose(after["foreign_flow_shock_1"], before["foreign_flow_shock_1"])


def test_historical_percentile_excludes_current_observation() -> None:
    sessions, flow, volume, context = _frames()
    result = build_foreign_flow_representation_v2(flow, volume, context, sessions)
    row = _row(result, "AAA", sessions[140])
    # AAA shock is monotonically increasing, so the current observation exceeds
    # every prior value in the frozen 120-session reference history.
    assert np.isclose(row["foreign_flow_shock_percentile_120"], 1.0)


def test_cross_sectional_rank_uses_average_percentile_semantics() -> None:
    sessions, flow, volume, context = _frames()
    result = build_foreign_flow_representation_v2(flow, volume, context, sessions)
    aaa = _row(result, "AAA", sessions[100])
    bbb = _row(result, "BBB", sessions[100])
    assert aaa["xs_rank_foreign_flow_shock_1"] == 1.0
    assert bbb["xs_rank_foreign_flow_shock_1"] == 0.5


def test_non_primary_row_is_not_used_in_cross_sectional_preference_rank() -> None:
    sessions, flow, volume, context = _frames()
    context.loc[context["ticker"].eq("BBB"), "universe_primary_liquid"] = False
    result = build_foreign_flow_representation_v2(flow, volume, context, sessions)
    aaa = _row(result, "AAA", sessions[100])
    bbb = _row(result, "BBB", sessions[100])
    assert aaa["xs_rank_foreign_flow_shock_1"] == 1.0
    assert np.isnan(bbb["xs_rank_foreign_flow_shock_1"])


def test_accumulation_dynamics_preserve_direction_and_magnitude_weighting() -> None:
    sessions, flow, volume, context = _frames()
    result = build_foreign_flow_representation_v2(flow, volume, context, sessions)
    aaa = _row(result, "AAA", sessions[100])
    bbb = _row(result, "BBB", sessions[100])
    assert np.isclose(aaa["foreign_weighted_persistence_5"], 1.0)
    assert np.isclose(bbb["foreign_weighted_persistence_5"], -1.0)
    assert np.isclose(aaa["foreign_signed_streak_10"], 1.0)
    assert np.isclose(bbb["foreign_signed_streak_10"], -1.0)


def test_flow_price_divergence_uses_source_session_cross_section() -> None:
    sessions, flow, volume, context = _frames()
    result = build_foreign_flow_representation_v2(flow, volume, context, sessions)
    aaa = _row(result, "AAA", sessions[100])
    # AAA has the stronger positive flow but the weaker return rank, so the
    # source-session divergence must be positive.
    assert aaa["foreign_flow_price_divergence_5"] > 0.0
    assert aaa["foreign_flow_price_divergence_20"] > 0.0


def test_market_context_rejects_outcome_columns() -> None:
    sessions, flow, volume, context = _frames()
    context["binary_target"] = 1
    with pytest.raises(ValueError, match="outcome-blind"):
        build_foreign_flow_representation_v2(flow, volume, context, sessions)
