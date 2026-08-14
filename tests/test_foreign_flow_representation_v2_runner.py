from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.foreign_flow_representation_v2_runner import (
    _hash_pin,
    _restrict_flow_to_official_sessions,
    _verify_rank_scope,
    build_causal_market_context,
)


def _panel(days: int = 25) -> tuple[pd.DatetimeIndex, pd.DataFrame, pd.DataFrame]:
    sessions = pd.date_range("2025-01-02", periods=days, freq="B")
    rows = []
    for ticker, value in (("AAA", 2_000_000_000.0), ("BBB", 3_000_000_000.0)):
        for index, day in enumerate(sessions):
            rows.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "close": 100.0 + index,
                    "volume": 100_000.0,
                    "regular_market_value": value,
                }
            )
    panel = pd.DataFrame(rows)
    master = pd.DataFrame(
        [
            {"ticker": "AAA", "listed_from": sessions[0], "listed_to": pd.NaT},
            {"ticker": "BBB", "listed_from": sessions[0], "listed_to": pd.NaT},
        ]
    )
    return sessions, panel, master


def test_primary_liquid_context_uses_full_panel_and_clean_v2_threshold() -> None:
    sessions, panel, master = _panel()
    context, removed = build_causal_market_context(panel, master, sessions)

    assert removed.empty
    assert len(context) == 50
    assert context["universe_primary_liquid"].sum() == 12
    assert context.loc[context["date"] == sessions[18], "universe_primary_liquid"].sum() == 0
    assert context.loc[context["date"] == sessions[19], "universe_primary_liquid"].sum() == 2


def test_listing_filter_prevents_prelisting_rows_from_liquidity_history() -> None:
    sessions, panel, master = _panel()
    master.loc[master["ticker"].eq("AAA"), "listed_from"] = sessions[5]
    context, removed = build_causal_market_context(panel, master, sessions)

    assert len(removed) == 5
    assert not context.loc[context["ticker"].eq("AAA"), "date"].lt(sessions[5]).any()
    assert context.loc[
        context["ticker"].eq("AAA") & context["date"].eq(sessions[24]),
        "universe_primary_liquid",
    ].item()


def test_hash_pin_fails_closed(tmp_path) -> None:
    path = tmp_path / "input.txt"
    path.write_text("immutable", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        _hash_pin(path, "0" * 64, label="test input")


def test_flow_boundary_rows_are_excluded_explicitly(tmp_path) -> None:
    sessions = pd.date_range("2025-01-02", periods=2, freq="B")
    flow = pd.DataFrame(
        {
            "session_date": [sessions[0], sessions[1], pd.Timestamp("2025-01-01")],
            "ticker": ["AAA", "AAA", "AAA"],
            "foreign_buy": [1, 1, 1],
            "foreign_sell": [0, 0, 0],
            "foreign_net": [1, 1, 1],
        }
    )

    kept, audit = _restrict_flow_to_official_sessions(flow, pd.DatetimeIndex(sessions))

    assert len(kept) == 2
    assert audit["flow_rows_outside_official_calendar"] == 1
    assert audit["flow_sessions_outside_official_calendar"] == 1
    assert audit["flow_sessions_outside_official_calendar_range"] == ["2025-01-01", "2025-01-01"]


def test_rank_scope_allows_negative_derived_divergence() -> None:
    day = pd.Timestamp("2025-01-03")
    features = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "flow_through_session": [day],
            "xs_rank_foreign_flow_shock_1": [0.25],
            "xs_rank_foreign_flow_shock_mean_5": [0.50],
            "xs_rank_foreign_flow_shock_mean_20": [0.75],
            "foreign_flow_price_divergence_5": [-0.25],
            "foreign_flow_price_divergence_20": [-0.10],
        }
    )
    context = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": [day],
            "universe_primary_liquid": [True],
        }
    )

    valid, bad_rows = _verify_rank_scope(features, context)

    assert valid
    assert bad_rows == {
        "xs_rank_foreign_flow_shock_1": 0,
        "xs_rank_foreign_flow_shock_mean_5": 0,
        "xs_rank_foreign_flow_shock_mean_20": 0,
        "foreign_flow_price_divergence_5": 0,
        "foreign_flow_price_divergence_20": 0,
    }
