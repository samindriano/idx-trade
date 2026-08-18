from __future__ import annotations

import pandas as pd

from idx_trade.v4_universe_740_610_audit import (
    classify_ca_absence,
    classify_presence,
    latest_regular_anchor,
    liquidity_band,
)


def test_ca_absence_flags_validation_presence_as_data_gap() -> None:
    row = pd.Series({"primary_rows_validation_600": 3, "primary_rows_2026": 3, "panel_rows_2026": 10})
    assert classify_ca_absence(row) == "POTENTIAL_CA_SUPPORT_DATA_GAP"


def test_ca_absence_distinguishes_active_non_primary_from_historical() -> None:
    active = pd.Series({"primary_rows_validation_600": 0, "primary_rows_2026": 0, "panel_rows_2026": 20})
    historical = pd.Series({"primary_rows_validation_600": 0, "primary_rows_2026": 0, "panel_rows_2026": 0})
    assert classify_ca_absence(active) == "ACTIVE_OR_PRESENT_2026_BUT_NOT_PRIMARY_LIQUID_ON_VALIDATION"
    assert classify_ca_absence(historical) == "HISTORICAL_PRIMARY_LIQUID_ONLY_BEFORE_2026"


def test_presence_prefers_delisting_over_panel_presence() -> None:
    row = pd.Series(
        {
            "security_master_delisting_date": pd.Timestamp("2025-01-01"),
            "security_master_status": "",
            "latest_anchor_state": "ACTIVE",
            "latest_anchor_date": pd.Timestamp("2026-01-02"),
            "panel_rows_2026": 5,
        }
    )
    assert classify_presence(row, pd.Timestamp("2026-07-17")) == "DELISTED_BY_FROZEN_END"


def test_presence_accepts_exact_2026_active_anchor() -> None:
    row = pd.Series(
        {
            "security_master_delisting_date": pd.NaT,
            "security_master_status": "",
            "latest_anchor_state": "ACTIVE",
            "latest_anchor_date": pd.Timestamp("2026-06-01"),
            "panel_rows_2026": 5,
        }
    )
    assert classify_presence(row, pd.Timestamp("2026-07-17")) == "ACTIVE_2026_EXACT_TRADABILITY_ANCHOR"


def test_latest_regular_anchor_fails_ambiguous_same_date_closed() -> None:
    anchors = pd.DataFrame(
        {
            "ticker": ["AAA.JK", "AAA", "BBB"],
            "market": ["REGULAR", "REGULAR", "REGULAR"],
            "as_of_date": ["2026-01-01", "2026-01-01", "2025-01-01"],
            "state": ["ACTIVE", "NO_TRADE", "ACTIVE"],
        }
    )
    result = latest_regular_anchor(anchors).set_index("ticker")
    assert result.loc["AAA", "latest_anchor_state"] == "AMBIGUOUS"
    assert result.loc["BBB", "latest_anchor_state"] == "ACTIVE"


def test_liquidity_bands_are_deterministic() -> None:
    assert liquidity_band(150_000_000_000) == "VERY_HIGH_LIQUIDITY_100B_PLUS"
    assert liquidity_band(30_000_000_000) == "HIGH_LIQUIDITY_25B_PLUS"
    assert liquidity_band(7_000_000_000) == "MATERIAL_LIQUIDITY_5B_PLUS"
    assert liquidity_band(2_000_000_000) == "PRIMARY_THRESHOLD_1B_PLUS"
    assert liquidity_band(500_000_000) == "BELOW_PRIMARY_THRESHOLD"
