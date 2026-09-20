from __future__ import annotations

import pandas as pd

from research.alpha_panel_anchor_state_census_v1 import summarize


def test_panel_is_active_subset_and_no_trade_is_absent() -> None:
    anchor = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "CCC"],
            "as_of_date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-01", "2025-01-01"]),
            "state": ["ACTIVE", "NO_TRADE", "ACTIVE", "NO_TRADE"],
        }
    )
    panel = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": pd.to_datetime(["2025-01-01", "2025-01-01"]),
        }
    )

    result = summarize(anchor, panel)

    assert result["status"] == "PASS_PANEL_ANCHOR_STATE_CENSUS"
    assert result["panel_keys_subset_of_active_anchor"] is True
    assert result["no_trade_keys_in_panel"] == 0
    assert result["no_trade_only_ticker_count"] == 1


def test_panel_key_outside_active_anchor_is_not_silently_accepted() -> None:
    anchor = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "as_of_date": pd.to_datetime(["2025-01-01"]),
            "state": ["ACTIVE"],
        }
    )
    panel = pd.DataFrame(
        {
            "ticker": ["ZZZ"],
            "date": pd.to_datetime(["2025-01-01"]),
        }
    )

    result = summarize(anchor, panel)

    assert result["panel_keys_subset_of_active_anchor"] is False
