import numpy as np
import pandas as pd

from idx_trade.price_basis_post_remediation_guard import (
    apply_official_volume_value,
    denominator_summary,
    liquidity_feature_delta,
    liquidity_source_features,
    open_hlc_audit,
    provenance_seams,
    volume_value_exact_comparison,
)


def test_open_hlc_audit_counts_available_and_violation():
    frame = pd.DataFrame({
        "ticker": ["AAA", "AAA", "AAA"],
        "date": ["2025-01-02", "2025-01-03", "2025-01-06"],
        "low": [90, 90, 90],
        "high": [110, 110, 110],
        "accepted_open": [100, 120, np.nan],
    })
    rows, summary = open_hlc_audit(frame, open_column="accepted_open")
    assert summary == {
        "rows": 3,
        "valid_hlc_rows": 3,
        "open_available_rows": 2,
        "open_within_rows": 1,
        "open_range_violation_rows": 1,
        "invalid_hlc_rows": 0,
    }
    assert rows.loc[0, "open_within_corrected_hlc"] == True  # noqa: E712
    assert rows.loc[1, "open_within_corrected_hlc"] == False  # noqa: E712
    assert pd.isna(rows.loc[2, "open_within_corrected_hlc"])


def test_exact_volume_value_comparison_and_seam():
    panel = pd.DataFrame({
        "ticker": ["AAA", "AAA", "AAA"],
        "date": ["2025-01-02", "2025-01-03", "2025-01-06"],
        "volume": [100, 120, 140],
        "regular_market_value": [1_000, 1_200, 1_400],
        "price_provenance": ["IDX", "YAHOO_RAW", "YAHOO_RAW"],
    })
    official = pd.DataFrame({
        "ticker": ["AAA", "AAA", "AAA"],
        "date": ["2025-01-02", "2025-01-03", "2025-01-06"],
        "idx_volume": [100, 120, 140],
        "idx_value": [1_000, 1_200, 1_400],
    })
    rows = volume_value_exact_comparison(panel, official)
    summary = denominator_summary(rows)
    assert summary["official_identity_overlap_rows"] == 3
    assert summary["volume_mismatch_rows"] == 0
    assert summary["value_mismatch_rows"] == 0
    seams = provenance_seams(rows)
    assert len(seams) == 1
    assert seams.iloc[0]["volume_same_basis"]
    assert seams.iloc[0]["value_same_basis"]


def test_volume_value_counterfactual_changes_liquidity_sources_when_mismatch_exists():
    dates = pd.bdate_range("2025-01-02", periods=25)
    panel = pd.DataFrame({
        "ticker": ["AAA"] * 25,
        "date": dates,
        "volume": [100.0] * 25,
        "regular_market_value": [2_000_000_000.0] * 25,
    })
    official = pd.DataFrame({
        "ticker": ["AAA"] * 25,
        "date": dates,
        "idx_volume": [100.0] * 24 + [200.0],
        "idx_value": [2_000_000_000.0] * 24 + [500_000_000.0],
    })
    comparison = volume_value_exact_comparison(panel, official)
    counter = apply_official_volume_value(panel, comparison)
    original_features = liquidity_source_features(panel, dates)
    counter_features = liquidity_source_features(counter, dates)
    delta = liquidity_feature_delta(original_features, counter_features)
    assert delta["relative_volume_20_changed_rows"] > 0
    assert delta["log_regular_value_relative_20_changed_rows"] > 0


def test_exact_volume_value_counterfactual_has_zero_liquidity_delta():
    dates = pd.bdate_range("2025-01-02", periods=25)
    panel = pd.DataFrame({
        "ticker": ["AAA"] * 25,
        "date": dates,
        "volume": np.arange(100.0, 125.0),
        "regular_market_value": np.arange(2_000_000_000.0, 2_000_000_025.0),
    })
    official = pd.DataFrame({
        "ticker": ["AAA"] * 25,
        "date": dates,
        "idx_volume": panel["volume"],
        "idx_value": panel["regular_market_value"],
    })
    comparison = volume_value_exact_comparison(panel, official)
    counter = apply_official_volume_value(panel, comparison)
    original_features = liquidity_source_features(panel, dates)
    counter_features = liquidity_source_features(counter, dates)
    assert liquidity_feature_delta(original_features, counter_features) == {
        "relative_volume_20_changed_rows": 0,
        "log_regular_value_relative_20_changed_rows": 0,
        "universe_primary_liquid_changed_rows": 0,
    }
