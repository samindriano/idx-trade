import hashlib

import numpy as np
import pandas as pd

from idx_trade.open_alpha_prereg import (
    ALL_OPEN_FEATURES,
    OUTCOME_COLUMNS,
    V2_FULL_FEATURE_COLUMNS,
    V2_OUTCOME_BLIND_COLUMNS,
    compute_previous_active_features,
    feature_order_sha256,
    previous_range_open_geometry,
    same_day_open_geometry,
    stable_key_sha256,
)


def test_same_day_geometry_is_exact_and_flat_ranges_fail_closed():
    frame = pd.DataFrame(
        {
            "open": [105.0, 100.0, np.nan],
            "high": [110.0, 100.0, 100.0],
            "low": [100.0, 100.0, 90.0],
        }
    )
    result = same_day_open_geometry(frame)
    assert result.loc[0, "open_position"] == 0.5
    assert result.loc[0, "open_to_high"] == 110.0 / 105.0 - 1.0
    assert result.loc[0, "open_to_low"] == 100.0 / 105.0 - 1.0
    assert result.loc[1].isna().all()
    assert result.loc[2].isna().all()


def test_previous_range_geometry_does_not_fill_invalid_previous_range():
    frame = pd.DataFrame(
        {
            "open": [105.0, 105.0],
            "previous_high": [110.0, 100.0],
            "previous_low": [100.0, 100.0],
        }
    )
    result = previous_range_open_geometry(frame)
    assert result.loc[0, "open_position_prev_active_range"] == 0.5
    assert result.loc[0, "open_to_prev_high"] == 110.0 / 105.0 - 1.0
    assert result.loc[1].isna().all()


def test_previous_link_uses_previous_active_bar_not_calendar_shift():
    panel = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "AAA", "AAA"],
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "high": [10.0, 11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0, 12.0],
        }
    )
    anchors = pd.DataFrame(
        {
            "ticker": ["AAA"] * 4,
            "as_of_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "state": ["ACTIVE", "NO_TRADE", "ACTIVE", "ACTIVE"],
        }
    )
    calendar = pd.DataFrame({"date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"])})
    result = compute_previous_active_features(panel, anchors, calendar)
    row = result[result["date"].eq(pd.Timestamp("2024-01-03"))].iloc[0]
    assert row["previous_active_date"] == pd.Timestamp("2024-01-01")
    assert row["previous_active_session_gap"] == 2
    assert result[result["date"].eq(pd.Timestamp("2024-01-04"))].iloc[0]["previous_active_date"] == pd.Timestamp("2024-01-03")


def test_key_hash_is_order_invariant_and_feature_hash_is_stable():
    first = pd.DataFrame(
        {
            "ticker": ["BBB", "AAA"],
            "date": ["2024-01-02", "2024-01-01"],
            "signal_session_index": [2, 1],
        }
    )
    second = first.iloc[::-1].reset_index(drop=True)
    assert stable_key_sha256(first) == stable_key_sha256(second)
    expected = hashlib.sha256(("[\"a\",\"b\"]").encode()).hexdigest()
    assert feature_order_sha256(("a", "b")) == expected


def test_outcome_blind_read_columns_exclude_targets():
    assert not set(V2_OUTCOME_BLIND_COLUMNS).intersection(OUTCOME_COLUMNS)
    assert len(V2_FULL_FEATURE_COLUMNS) == 25
    assert len(ALL_OPEN_FEATURES) == 6
    assert "binary_target" not in V2_OUTCOME_BLIND_COLUMNS
    assert "label_status" not in V2_OUTCOME_BLIND_COLUMNS
