from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.ca_feature_basis_gate_v1 import BASIS_SAFE, BASIS_UNSAFE
from idx_trade.ca_feature_basis_v1 import NOT_APPLICABLE
from idx_trade.ca_feature_basis_v4_contract_v1 import V4_CA_BASIS_DIRECT_SOURCE_FEATURES
from idx_trade.ca_feature_basis_v4_recompute_v1 import (
    FROZEN_V4_FEATURE_BUILDER_BLOB_SHA1,
    V4_CONTROL_FEATURE_COLUMNS,
    assert_frozen_v4_feature_builder_blob,
    recompute_v4_control_after_basis_admission,
)


def direct_frame() -> pd.DataFrame:
    rows = []
    for ticker, r5, relvol in (
        ("AAA", 1.0, 1.0),
        ("BBB", 2.0, 2.0),
        ("CCC", 3.0, 3.0),
    ):
        row = {
            "ticker": ticker,
            "date": pd.Timestamp("2021-10-13"),
            "universe_primary_liquid": True,
            "close_return_5": r5,
            "close_return_20": r5 + 10.0,
            "atr14_over_close": r5 + 20.0,
            "close_position_20": r5 + 30.0,
            "distance_high_20_atr": r5 + 40.0,
            "distance_low_20_atr": r5 + 50.0,
            "distance_high_60_atr": r5 + 60.0,
            "distance_low_60_atr": r5 + 70.0,
            "relative_volume_20": relvol,
            "log_regular_value_relative_20": r5 + 80.0,
        }
        # Deliberately poison every derived column. Recompute must overwrite it.
        for column in V4_CONTROL_FEATURE_COLUMNS:
            row[column] = 999.0
        rows.append(row)
    return pd.DataFrame(rows)


def admission() -> pd.DataFrame:
    rows = []
    for ticker in ("AAA", "BBB", "CCC"):
        for feature in V4_CA_BASIS_DIRECT_SOURCE_FEATURES:
            state = BASIS_SAFE
            if ticker == "CCC" and feature in {"close_return_5", "relative_volume_20"}:
                state = BASIS_UNSAFE
            rows.append(
                {
                    "ticker": ticker,
                    "date": pd.Timestamp("2021-10-13"),
                    "feature": feature,
                    "basis_integrity_state": state,
                }
            )
    return pd.DataFrame(rows)


def all_safe_admission(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker, date in frame[["ticker", "date"]].itertuples(index=False):
        for feature in V4_CA_BASIS_DIRECT_SOURCE_FEATURES:
            rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "feature": feature,
                    "basis_integrity_state": BASIS_SAFE,
                }
            )
    return pd.DataFrame(rows)


def test_invalid_direct_value_is_excluded_before_rank_and_market_context() -> None:
    result = recompute_v4_control_after_basis_admission(direct_frame(), admission()).set_index("ticker")

    assert np.isnan(result.loc["CCC", "close_return_5"])
    assert np.isnan(result.loc["CCC", "relative_volume_20"])

    # CCC must not retain its stale rank or participate in the recomputed rank.
    assert np.isnan(result.loc["CCC", "xs_rank_close_return_5"])
    assert result.loc["AAA", "xs_rank_close_return_5"] == 0.5
    assert result.loc["BBB", "xs_rank_close_return_5"] == 1.0

    # Context uses finite admitted direct values but universe count itself is not
    # changed merely because one price-derived feature is invalid.
    assert set(result["market_primary_liquid_count"]) == {3.0}
    assert set(result["market_median_close_return_5"]) == {1.5}
    assert set(result["market_breadth_return_5_positive"]) == {1.0}
    assert set(result["market_median_relative_volume_20"]) == {1.5}

    assert result.loc["AAA", "market_relative_close_return_5"] == -0.5
    assert result.loc["BBB", "market_relative_close_return_5"] == 0.5
    assert np.isnan(result.loc["CCC", "market_relative_close_return_5"])


def test_stale_derived_columns_are_rebuilt_not_reused() -> None:
    result = recompute_v4_control_after_basis_admission(direct_frame(), admission())
    for column in V4_CONTROL_FEATURE_COLUMNS:
        finite = pd.to_numeric(result[column], errors="coerce").dropna()
        assert not finite.eq(999.0).any(), column


def test_unaffected_source_feature_keeps_all_three_members_in_its_rank() -> None:
    result = recompute_v4_control_after_basis_admission(direct_frame(), admission()).set_index("ticker")
    assert result.loc["AAA", "xs_rank_log_regular_value_relative_20"] == 1.0 / 3.0
    assert result.loc["BBB", "xs_rank_log_regular_value_relative_20"] == 2.0 / 3.0
    assert result.loc["CCC", "xs_rank_log_regular_value_relative_20"] == 1.0


def test_frozen_builder_blob_pin_is_executable_not_documentary() -> None:
    assert assert_frozen_v4_feature_builder_blob(FROZEN_V4_FEATURE_BUILDER_BLOB_SHA1) == (
        FROZEN_V4_FEATURE_BUILDER_BLOB_SHA1
    )
    with pytest.raises(ValueError, match="blob mismatch"):
        assert_frozen_v4_feature_builder_blob("0" * 40)
    with pytest.raises(ValueError, match="blob mismatch"):
        assert_frozen_v4_feature_builder_blob("")


def test_not_applicable_must_already_be_natural_missingness() -> None:
    frame = direct_frame()
    states = all_safe_admission(frame)
    mask = (
        states["ticker"].eq("AAA")
        & states["feature"].eq("close_return_5")
    )
    states.loc[mask, "basis_integrity_state"] = NOT_APPLICABLE

    # A finite frozen source value cannot be erased under a warm-up state.
    with pytest.raises(ValueError, match="cannot erase finite frozen source feature"):
        recompute_v4_control_after_basis_admission(frame, states)

    # When the frozen direct formula is already naturally missing, the same
    # NOT_APPLICABLE state is a semantic annotation only and is allowed.
    frame.loc[frame["ticker"].eq("AAA"), "close_return_5"] = np.nan
    result = recompute_v4_control_after_basis_admission(frame, states).set_index("ticker")
    assert np.isnan(result.loc["AAA", "close_return_5"])
    assert np.isnan(result.loc["AAA", "xs_rank_close_return_5"])


def test_noop_recompute_preserves_frozen_tie_nonprimary_and_context_semantics() -> None:
    rows = []
    for date, values in (
        (pd.Timestamp("2021-10-13"), (("AAA", 1.0, True), ("BBB", 1.0, True), ("ZZZ", 99.0, False))),
        (pd.Timestamp("2021-10-14"), (("AAA", -1.0, True), ("BBB", 3.0, True), ("ZZZ", -99.0, False))),
    ):
        for ticker, r5, primary in values:
            row = {
                "ticker": ticker,
                "date": date,
                "universe_primary_liquid": primary,
                "close_return_5": r5,
                "close_return_20": r5 * 2.0,
                "atr14_over_close": abs(r5) + 0.1,
                "close_position_20": 0.5,
                "distance_high_20_atr": abs(r5) + 1.0,
                "distance_low_20_atr": abs(r5) + 2.0,
                "distance_high_60_atr": abs(r5) + 3.0,
                "distance_low_60_atr": abs(r5) + 4.0,
                "relative_volume_20": abs(r5) + 1.0,
                "log_regular_value_relative_20": 0.0 if ticker != "ZZZ" else 50.0,
            }
            rows.append(row)
    frame = pd.DataFrame(rows)
    result = recompute_v4_control_after_basis_admission(
        frame, all_safe_admission(frame)
    ).set_index(["date", "ticker"])

    day1 = pd.Timestamp("2021-10-13")
    day2 = pd.Timestamp("2021-10-14")

    # Frozen pandas rank(method='average', pct=True): tied two-member primary
    # cross-section receives average rank 1.5 / 2 = 0.75.
    assert result.loc[(day1, "AAA"), "xs_rank_close_return_5"] == 0.75
    assert result.loc[(day1, "BBB"), "xs_rank_close_return_5"] == 0.75
    assert np.isnan(result.loc[(day1, "ZZZ"), "xs_rank_close_return_5"])

    # Market context is attached to non-primary rows too, while the count and
    # statistics use the primary-liquid block only.
    assert result.loc[(day1, "ZZZ"), "market_primary_liquid_count"] == 2.0
    assert result.loc[(day1, "ZZZ"), "market_median_close_return_5"] == 1.0
    assert np.isnan(result.loc[(day1, "ZZZ"), "market_relative_close_return_5"])

    assert result.loc[(day2, "AAA"), "market_median_close_return_5"] == 1.0
    assert result.loc[(day2, "AAA"), "market_breadth_return_5_positive"] == 0.5
    assert result.loc[(day2, "AAA"), "market_relative_close_return_5"] == -2.0
    assert result.loc[(day2, "BBB"), "market_relative_close_return_5"] == 2.0
