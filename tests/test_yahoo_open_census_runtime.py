import pandas as pd

from idx_trade.yahoo_open_census import apply_verified_split_reconstruction, build_full_direct_audit
from idx_trade.yahoo_open_census_runtime import build_full_panel_derivative


def test_full_panel_derivative_preserves_all_columns_and_existing_open():
    panel = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "date": "2022-01-03",
                "open": 100.0,
                "high": 110.0,
                "low": 90.0,
                "close": 105.0,
                "volume": 1000,
                "state": "ACTIVE",
                "custom_flag": "keep-me",
            },
            {
                "ticker": "AAA",
                "date": "2022-01-04",
                "open": None,
                "high": 120.0,
                "low": 100.0,
                "close": 115.0,
                "volume": 1100,
                "state": "ACTIVE",
                "custom_flag": "also-keep",
            },
        ]
    )
    provider = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "date": pd.Timestamp("2022-01-03"),
                "raw_open": 100.0,
                "raw_high": 110.0,
                "raw_low": 90.0,
                "raw_close": 105.0,
                "raw_volume": 1000.0,
            },
            {
                "ticker": "AAA",
                "date": pd.Timestamp("2022-01-04"),
                "raw_open": 110.0,
                "raw_high": 120.0,
                "raw_low": 100.0,
                "raw_close": 115.0,
                "raw_volume": 1100.0,
            },
        ]
    )
    actions = pd.DataFrame(columns=["ticker", "effective_date", "ratio"])
    direct, _ = build_full_direct_audit(panel, provider)
    audit, _ = apply_verified_split_reconstruction(direct, actions)
    derivative, provenance, summary = build_full_panel_derivative(panel, audit)

    assert list(derivative.columns) == list(panel.columns)
    assert derivative.loc[0, "open"] == 100.0
    assert derivative.loc[1, "open"] == 110.0
    assert derivative.loc[0, "custom_flag"] == "keep-me"
    assert derivative.loc[1, "custom_flag"] == "also-keep"
    assert summary["all_original_columns_preserved"] is True
    assert summary["direct_fills"] == 1
    assert provenance.loc[1, "open_evidence_class"] == "DIRECT_RAW_HLC_EXACT"
