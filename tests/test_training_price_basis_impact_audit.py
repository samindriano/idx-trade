from __future__ import annotations

import numpy as np
import pandas as pd

from idx_trade.training_price_basis_impact_audit import (
    V2_FULL_FEATURE_COLUMNS,
    add_hlc_basis_comparison,
    apply_hlc_counterfactual,
    build_v2_hgb_xs_market_features,
    feature_difference_table,
    feature_parity_summary,
    mark_stable_scale_runs,
)


def test_stable_scale_run_requires_consecutive_sessions() -> None:
    sessions = pd.date_range("2024-01-01", periods=6, freq="D")
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"] * 5,
            "date": [sessions[0], sessions[1], sessions[2], sessions[4], sessions[5]],
            "panel_high": [10.0, 11.0, 12.0, 14.0, 15.0],
            "panel_low": [8.0, 9.0, 10.0, 12.0, 13.0],
            "panel_close": [9.0, 10.0, 11.0, 13.0, 14.0],
            "idx_high": [20.0, 22.0, 24.0, 28.0, 30.0],
            "idx_low": [16.0, 18.0, 20.0, 24.0, 26.0],
            "idx_close": [18.0, 20.0, 22.0, 26.0, 28.0],
        }
    )
    compared = add_hlc_basis_comparison(
        frame,
        left_prefix="panel_",
        right_prefix="idx_",
        result_prefix="panel_idx",
    )
    marked = mark_stable_scale_runs(
        compared,
        sessions,
        factor_column="panel_idx_scale_factor",
        prefix="panel_idx",
    )
    assert marked["panel_idx_stable_run_member"].tolist() == [True, True, True, False, False]
    assert marked["panel_idx_run_length"].tolist() == [3, 3, 3, 2, 2]


def test_row_factor_requires_hlc_common_factor() -> None:
    frame = pd.DataFrame(
        {
            "panel_high": [10.0, 10.0],
            "panel_low": [8.0, 8.0],
            "panel_close": [9.0, 9.0],
            "idx_high": [20.0, 20.0],
            "idx_low": [16.0, 15.0],
            "idx_close": [18.0, 18.0],
        }
    )
    out = add_hlc_basis_comparison(
        frame,
        left_prefix="panel_",
        right_prefix="idx_",
        result_prefix="x",
    )
    assert out.loc[0, "x_row_scale_consistent"]
    assert out.loc[0, "x_scale_factor"] == 2.0
    assert not out.loc[1, "x_row_scale_consistent"]
    assert np.isnan(out.loc[1, "x_scale_factor"])


def test_counterfactual_changes_only_hlc_on_marked_rows() -> None:
    panel = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "high": [10.0, 11.0],
            "low": [8.0, 9.0],
            "close": [9.0, 10.0],
            "volume": [100.0, 200.0],
            "regular_market_value": [1_000_000_000.0, 2_000_000_000.0],
            "price_provenance": ["A", "B"],
        }
    )
    evidence = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "stable": [True, False],
            "idx_high": [20.0, 22.0],
            "idx_low": [16.0, 18.0],
            "idx_close": [18.0, 20.0],
        }
    )
    out, changed = apply_hlc_counterfactual(panel, evidence, member_column="stable")
    first = out.iloc[0]
    second = out.iloc[1]
    assert (first["high"], first["low"], first["close"]) == (20.0, 16.0, 18.0)
    assert first["volume"] == 100.0
    assert first["regular_market_value"] == 1_000_000_000.0
    assert first["price_provenance"] == "A"
    assert (second["high"], second["low"], second["close"]) == (11.0, 9.0, 10.0)
    assert len(changed) == 1


def test_v2_features_are_invariant_to_full_history_constant_hlc_scale() -> None:
    dates = pd.date_range("2024-01-01", periods=90, freq="D")
    close = np.linspace(100.0, 190.0, len(dates))
    base = pd.DataFrame(
        {
            "ticker": ["AAA"] * len(dates),
            "date": dates,
            "high": close + 2.0,
            "low": close - 2.0,
            "close": close,
            "volume": np.linspace(1_000.0, 2_000.0, len(dates)),
            "regular_market_value": np.linspace(2_000_000_000.0, 3_000_000_000.0, len(dates)),
        }
    )
    scaled = base.copy()
    scaled[["high", "low", "close"]] *= 0.5
    original = build_v2_hgb_xs_market_features(base, dates)
    changed = build_v2_hgb_xs_market_features(scaled, dates)
    diff = feature_difference_table(
        original,
        changed,
        feature_columns=V2_FULL_FEATURE_COLUMNS,
    )
    summary = feature_parity_summary(diff)
    assert summary["changed_rows"] == 0


def test_feature_difference_localizes_transition_effect() -> None:
    dates = pd.date_range("2024-01-01", periods=90, freq="D")
    close = np.linspace(100.0, 190.0, len(dates))
    base = pd.DataFrame(
        {
            "ticker": ["AAA"] * len(dates),
            "date": dates,
            "high": close + 2.0,
            "low": close - 2.0,
            "close": close,
            "volume": np.linspace(1_000.0, 2_000.0, len(dates)),
            "regular_market_value": np.linspace(2_000_000_000.0, 3_000_000_000.0, len(dates)),
        }
    )
    broken = base.copy()
    broken.loc[:44, ["high", "low", "close"]] *= 0.5
    original = build_v2_hgb_xs_market_features(base, dates)
    contaminated = build_v2_hgb_xs_market_features(broken, dates)
    diff = feature_difference_table(
        original,
        contaminated,
        feature_columns=V2_FULL_FEATURE_COLUMNS,
    )
    summary = feature_parity_summary(diff)
    assert summary["changed_rows"] > 0
    assert summary["changed_cells"] > 0
