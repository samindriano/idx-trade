from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.pit_security_identity_audit import (
    compare_representation_tables,
    derive_right_only_identity_overlay,
    merge_identity_overlay,
)


def master(*rows: tuple[str, str, str, str, str | None, str]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["security_id", "ticker", "company_name", "listed_from", "listed_to", "source"],
    )


def test_missing_identities_are_restored_generically_without_ticker_allowlist() -> None:
    frozen = master(("IDX:AAA:20200101", "AAA", "A", "2020-01-01", None, "FROZEN"))
    historical = master(
        ("IDX:AAA:20200101", "AAA", "A", "2020-01-01", None, "FROZEN"),
        ("IDX:BBB:20100101", "BBB", "B", "2010-01-01", "2021-01-01", "HIST"),
        ("IDX:CCC:20150101", "CCC", "C", "2015-01-01", None, "HIST"),
    )
    overlay, diagnostics = derive_right_only_identity_overlay(frozen, historical)
    assert overlay["ticker"].tolist() == ["BBB", "CCC"]
    assert diagnostics.overlay_rows == 2
    assert set(merge_identity_overlay(frozen, overlay)["ticker"]) == {"AAA", "BBB", "CCC"}


def test_pre_listing_row_remains_excluded_by_frozen_listing_filter() -> None:
    from idx_trade.ranking_v4_3_features import filter_pit_listing_rows

    panel = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "date": ["2019-12-31", "2020-01-02"],
            "high": [10.0, 10.0],
            "low": [9.0, 9.0],
            "close": [9.5, 9.5],
            "volume": [100.0, 100.0],
            "regular_market_value": [1e9, 1e9],
        }
    )
    admitted, diagnostics = filter_pit_listing_rows(
        panel, master(("IDX:AAA:20200101", "AAA", "A", "2020-01-01", None, "HIST"))
    )
    assert admitted["date"].astype(str).tolist() == ["2020-01-02"]
    assert diagnostics.excluded_pre_listing_rows == 1


def test_duplicate_or_overlapping_restored_identities_fail_closed() -> None:
    frozen = master(("IDX:AAA:20200101", "AAA", "A", "2020-01-01", None, "FROZEN"))
    duplicate = master(
        ("IDX:BBB:20100101", "BBB", "B", "2010-01-01", "2021-01-01", "HIST"),
        ("IDX:BBB:20150101", "BBB", "B2", "2015-01-01", None, "HIST"),
    )
    with pytest.raises(ValueError, match="unique"):
        derive_right_only_identity_overlay(frozen, duplicate)


def test_existing_ticker_overlap_is_not_a_ticker_specific_repair() -> None:
    frozen = master(("IDX:AAA:20200101", "AAA", "A", "2020-01-01", None, "FROZEN"))
    historical = master(
        ("IDX:AAA:20100101", "AAA", "A-old", "2010-01-01", "2019-01-01", "HIST"),
    )
    with pytest.raises(ValueError, match="overlaps frozen ticker"):
        derive_right_only_identity_overlay(frozen, historical)


def test_representation_diff_separates_direct_and_spillover() -> None:
    base = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": ["2020-01-02", "2020-01-02"],
            "xs_rank_close_return_5": [0.5, 0.5],
            "market_primary_liquid_count": [2.0, 2.0],
            "universe_primary_liquid": [True, True],
        }
    )
    counter = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "FREN"],
            "date": ["2020-01-02", "2020-01-02", "2020-01-02"],
            "xs_rank_close_return_5": [0.5, 0.6, 0.4],
            "market_primary_liquid_count": [3.0, 3.0, 3.0],
            "universe_primary_liquid": [True, True, False],
        }
    )
    diff = compare_representation_tables(base, counter)
    assert diff.direct_new_rows == 1
    assert diff.direct_new_tickers == ("FREN",)
    assert diff.spillover_changed_rows == 2
    assert diff.spillover_changed_tickers == ("AAA", "BBB")
    assert diff.primary_membership_changes == 1


def test_diff_rejects_duplicate_identity_keys() -> None:
    base = pd.DataFrame({"ticker": ["AAA", "AAA"], "date": ["2020-01-01", "2020-01-01"]})
    with pytest.raises(ValueError, match="duplicate"):
        compare_representation_tables(base, base)
