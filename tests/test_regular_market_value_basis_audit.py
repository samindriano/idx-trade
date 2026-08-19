from __future__ import annotations

import numpy as np
import pandas as pd

from idx_trade.regular_market_value_basis_audit import (
    apply_official_value_counterfactual,
    build_value_comparison,
    build_value_feature_state,
    compare_value_feature_states,
    detect_ratio_seams,
    ratio_summary,
)


def _panel(dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for ticker, base in (("AAAA", 2_000_000_000.0), ("BBBB", 3_000_000_000.0)):
        for i, day in enumerate(dates):
            rows.append({
                "ticker": ticker,
                "date": day,
                "close": 100.0 + i,
                "volume": 20_000_000.0,
                "regular_market_value": base + i * 10_000_000.0,
                "price_provenance": "YAHOO_RAW",
            })
    return pd.DataFrame(rows)


def _primary(panel: pd.DataFrame) -> pd.DataFrame:
    return panel[["ticker", "date"]].assign(universe_primary_liquid=True)


def test_value_comparison_distinguishes_official_parity_and_mismatch() -> None:
    dates = pd.date_range("2026-01-01", periods=3, freq="D")
    panel = _panel(dates)
    idx = panel[["ticker", "date", "close", "volume", "regular_market_value"]].rename(columns={
        "close": "idx_close",
        "volume": "idx_volume",
        "regular_market_value": "idx_regular_market_value",
    })
    mask = (idx["ticker"] == "AAAA") & (idx["date"] == dates[1])
    idx.loc[mask, "idx_regular_market_value"] *= 2.0

    comparison = build_value_comparison(panel, idx)
    summary = ratio_summary(comparison).iloc[0]
    assert int(summary["rows"]) == 6
    assert int(comparison["panel_idx_value_exact"].sum()) == 5
    mismatch = comparison.loc[~comparison["panel_idx_value_exact"]]
    assert len(mismatch) == 1
    assert np.isclose(float(mismatch["panel_idx_value_ratio"].iloc[0]), 0.5)


def test_ratio_seam_detects_large_basis_jump_and_provenance_change() -> None:
    dates = pd.date_range("2026-01-01", periods=3, freq="D")
    panel = _panel(dates)
    panel = panel[panel["ticker"] == "AAAA"].copy()
    panel.loc[panel["date"] == dates[2], "price_provenance"] = "IDX_PUBLIC_STOCK_SUMMARY"
    idx = panel[["ticker", "date", "close", "volume", "regular_market_value"]].rename(columns={
        "close": "idx_close",
        "volume": "idx_volume",
        "regular_market_value": "idx_regular_market_value",
    })
    idx.loc[idx["date"] < dates[2], "idx_regular_market_value"] *= 2.0

    comparison = build_value_comparison(panel, idx)
    seams = detect_ratio_seams(comparison, jump_factor=1.20)
    assert len(seams) == 1
    assert bool(seams["provenance_changed"].iloc[0])
    assert np.isclose(float(seams["ratio_jump_factor"].iloc[0]), 2.0)


def test_official_counterfactual_propagates_into_value_representation() -> None:
    dates = pd.date_range("2026-01-01", periods=25, freq="D")
    panel = _panel(dates)
    idx = panel[["ticker", "date", "close", "volume", "regular_market_value"]].rename(columns={
        "close": "idx_close",
        "volume": "idx_volume",
        "regular_market_value": "idx_regular_market_value",
    })
    # BBBB starts with a lower own-history value ratio than AAAA at day 20.
    # Increasing BBBB's official value by 1.5x therefore exercises both the
    # own-history representation change and an actual cross-sectional rank flip.
    mask = (idx["ticker"] == "BBBB") & (idx["date"] == dates[19])
    idx.loc[mask, "idx_regular_market_value"] *= 1.5

    corrected, evidence = apply_official_value_counterfactual(panel, idx)
    assert len(evidence) == 1
    before = build_value_feature_state(panel, _primary(panel))
    after = build_value_feature_state(corrected, _primary(corrected))
    diff, summary = compare_value_feature_states(before, after)
    assert summary["log_regular_value_relative_20_changed_rows"] > 0
    assert summary["xs_rank_log_regular_value_relative_20_changed_rows"] > 0
    assert summary["any_value_representation_changed_rows"] > 0
    assert diff["any_value_representation_changed"].any()
