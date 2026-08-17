from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.ranking_v4_3_features import (
    V4_CONTROL_FEATURE_COLUMNS,
    build_v4_control_feature_table,
    v4_primary_control_view,
)


ROOT = Path(__file__).resolve().parents[1]


def make_panel(ticker: str, dates: pd.DatetimeIndex, value: float) -> pd.DataFrame:
    n = len(dates)
    close = 100.0 + np.arange(n, dtype=float)
    return pd.DataFrame(
        {
            "ticker": ticker,
            "date": dates,
            "high": close + 2.0,
            "low": close - 2.0,
            "close": close,
            "volume": np.full(n, 1_000_000.0),
            "regular_market_value": np.full(n, value),
        }
    )


def test_control_feature_order_matches_locked_v4_3_config() -> None:
    config = json.loads(
        (ROOT / "config" / "ranking_v4_3_preregistration.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(V4_CONTROL_FEATURE_COLUMNS) == config["control"]["features"]
    assert len(V4_CONTROL_FEATURE_COLUMNS) == 25


def test_prelisting_row_is_removed_before_liquidity_and_market_context() -> None:
    sessions = pd.date_range("2024-01-02", periods=25, freq="B")
    aaa = make_panel("AAA", sessions[:21], 2_000_000_000.0)
    bbb = make_panel("BBB", sessions[:21], 3_000_000_000.0)
    panel = pd.concat([aaa, bbb], ignore_index=True)
    master = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "listed_from": [sessions[1], sessions[0]],
            "listed_to": [None, None],
        }
    )

    features, diagnostics = build_v4_control_feature_table(panel, sessions, master)
    assert diagnostics.excluded_pre_listing_rows == 1
    assert diagnostics.excluded_missing_security_master_rows == 0
    assert not ((features["ticker"] == "AAA") & (features["date"] == sessions[0])).any()

    aaa_day19 = features[
        (features["ticker"] == "AAA") & (features["date"] == sessions[19])
    ].iloc[0]
    aaa_day20 = features[
        (features["ticker"] == "AAA") & (features["date"] == sessions[20])
    ].iloc[0]
    bbb_day19 = features[
        (features["ticker"] == "BBB") & (features["date"] == sessions[19])
    ].iloc[0]

    # AAA has only sessions 1..19 at day 19: 19 valid PIT observations, not 20.
    assert aaa_day19["liquidity_active_observations_60"] == 19
    assert not bool(aaa_day19["universe_primary_liquid"])
    assert aaa_day20["liquidity_active_observations_60"] == 20
    assert bool(aaa_day20["universe_primary_liquid"])

    assert bool(bbb_day19["universe_primary_liquid"])
    assert bbb_day19["market_primary_liquid_count"] == 1.0
    assert aaa_day19["market_primary_liquid_count"] == 1.0
    assert aaa_day20["market_primary_liquid_count"] == 2.0


def test_panel_listing_columns_cannot_override_authoritative_security_master() -> None:
    sessions = pd.date_range("2024-01-02", periods=21, freq="B")
    panel = make_panel("AAA", sessions, 2_000_000_000.0)
    # Deliberately wrong fail-open panel metadata. It must be discarded.
    panel["listed_from"] = sessions[0]
    panel["listed_to"] = None
    master = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "listed_from": [sessions[1]],
            "listed_to": [None],
        }
    )
    features, diagnostics = build_v4_control_feature_table(panel, sessions, master)
    assert diagnostics.excluded_pre_listing_rows == 1
    assert not (features["date"] == sessions[0]).any()
    assert features["listed_from"].eq(sessions[1]).all()


def test_missing_security_master_row_fails_closed_before_feature_history() -> None:
    sessions = pd.date_range("2024-01-02", periods=21, freq="B")
    panel = pd.concat(
        [
            make_panel("AAA", sessions, 2_000_000_000.0),
            make_panel("MISSING", sessions, 2_000_000_000.0),
        ],
        ignore_index=True,
    )
    master = pd.DataFrame(
        {"ticker": ["AAA"], "listed_from": [sessions[0]], "listed_to": [None]}
    )
    features, diagnostics = build_v4_control_feature_table(panel, sessions, master)
    assert diagnostics.excluded_missing_security_master_rows == len(sessions)
    assert set(features["ticker"]) == {"AAA"}


def test_primary_control_view_contains_only_frozen_25_columns_plus_identity_context() -> None:
    sessions = pd.date_range("2024-01-02", periods=25, freq="B")
    panel = make_panel("AAA", sessions, 2_000_000_000.0)
    master = pd.DataFrame(
        {"ticker": ["AAA"], "listed_from": [sessions[0]], "listed_to": [None]}
    )
    features, _ = build_v4_control_feature_table(panel, sessions, master)
    primary = v4_primary_control_view(features)
    assert len(primary) == 6  # sessions 19..24 once 20 PIT observations exist
    assert set(V4_CONTROL_FEATURE_COLUMNS).issubset(primary.columns)
    assert primary["universe_primary_liquid"].all()
