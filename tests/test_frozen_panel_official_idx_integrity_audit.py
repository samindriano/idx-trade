from __future__ import annotations

import numpy as np
import pandas as pd

from idx_trade.frozen_panel_official_idx_integrity_audit import (
    apply_official_volume_counterfactual,
    build_volume_comparison,
    build_volume_feature_state,
    calendar_witness_diagnostics,
    candidate_official_active_gaps,
    compare_volume_feature_states,
    detect_volume_ratio_seams,
)


def _panel(dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for ticker, multiplier in (("AAAA", 1.0), ("BBBB", 1.4)):
        for i, day in enumerate(dates):
            rows.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "high": 110.0,
                    "low": 90.0,
                    "close": 100.0,
                    "volume": multiplier * (1_000_000.0 + i * 10_000.0),
                    "regular_market_value": 2_000_000_000.0,
                    "price_provenance": "YAHOO_RAW",
                }
            )
    return pd.DataFrame(rows)


def _witness(panel: pd.DataFrame) -> pd.DataFrame:
    return panel[["ticker", "date", "high", "low", "close", "volume", "regular_market_value"]].rename(
        columns={
            "high": "idx_high",
            "low": "idx_low",
            "close": "idx_close",
            "volume": "idx_volume",
            "regular_market_value": "idx_value",
        }
    ).assign(idx_frequency=10.0)


def _primary(panel: pd.DataFrame) -> pd.DataFrame:
    return panel[["ticker", "date"]].assign(universe_primary_liquid=True)


def test_volume_comparison_and_seam_detection() -> None:
    dates = pd.date_range("2026-01-01", periods=4, freq="D")
    panel = _panel(dates)
    witness = _witness(panel)
    mask = (witness["ticker"] == "AAAA") & witness["date"].lt(dates[2])
    witness.loc[mask, "idx_volume"] *= 2.0
    panel.loc[(panel["ticker"] == "AAAA") & (panel["date"] == dates[2]), "price_provenance"] = "IDX_PUBLIC_STOCK_SUMMARY"
    panel.loc[(panel["ticker"] == "AAAA") & (panel["date"] == dates[3]), "price_provenance"] = "IDX_PUBLIC_STOCK_SUMMARY"

    comparison = build_volume_comparison(panel, witness)
    assert int(comparison["panel_idx_volume_exact"].sum()) == 6
    seams = detect_volume_ratio_seams(comparison, jump_factor=1.20)
    assert len(seams) == 1
    assert bool(seams["provenance_changed"].iloc[0])
    assert np.isclose(float(seams["ratio_jump_factor"].iloc[0]), 2.0)


def test_candidate_gap_distinguishes_interior_from_edges() -> None:
    dates = pd.date_range("2026-01-01", periods=5, freq="D")
    panel = _panel(dates)
    panel = panel[~((panel["ticker"] == "AAAA") & (panel["date"] == dates[2]))].copy()
    witness = _witness(_panel(dates))

    gaps = candidate_official_active_gaps(panel, witness, dates)
    target = gaps[(gaps["ticker"] == "AAAA") & (gaps["date"] == dates[2])]
    assert len(target) == 1
    assert target["gap_class"].iloc[0] == "INTERIOR_OFFICIAL_ACTIVE_HLC_MISSING"


def test_calendar_diagnostic_finds_active_date_omitted_from_calendar() -> None:
    dates = pd.date_range("2026-01-01", periods=4, freq="D")
    panel = _panel(dates)
    witness = _witness(panel)
    calendar = pd.DatetimeIndex([dates[0], dates[1], dates[3]])
    result = calendar_witness_diagnostics(witness, calendar)
    assert result["active_witness_dates_missing_from_calendar"] == [dates[2].date().isoformat()]


def test_official_volume_counterfactual_changes_volume_representation() -> None:
    dates = pd.date_range("2026-01-01", periods=25, freq="D")
    panel = _panel(dates)
    witness = _witness(panel)
    # BBBB begins with the same smooth own-history ratio shape as AAAA. Shock one
    # official volume sufficiently to alter its own relative-volume state and rank.
    mask = (witness["ticker"] == "BBBB") & (witness["date"] == dates[19])
    witness.loc[mask, "idx_volume"] *= 3.0

    corrected, evidence = apply_official_volume_counterfactual(panel, witness)
    assert len(evidence) == 1
    before = build_volume_feature_state(panel, _primary(panel))
    after = build_volume_feature_state(corrected, _primary(corrected))
    diff, summary = compare_volume_feature_states(before, after)
    assert summary["relative_volume_20_changed_rows"] > 0
    assert summary["xs_rank_relative_volume_20_changed_rows"] > 0
    assert summary["any_volume_representation_changed_rows"] > 0
    assert diff["any_volume_representation_changed"].any()
