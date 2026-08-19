from __future__ import annotations

import pandas as pd

from idx_trade.v4_3_ca_residual47_idx_digital_split import (
    listing_date_linked,
    month_scope,
    normalize_split_row,
    source_type_compatible,
)


def test_month_scope_is_symmetric_and_frozen() -> None:
    scope = month_scope([pd.Timestamp("2024-06-15")], radius=2)
    assert scope == ((2024, 4), (2024, 5), (2024, 6), (2024, 7), (2024, 8))


def test_normalize_split_row_accepts_idx_field_names() -> None:
    row = normalize_split_row({
        "code": "ABCD",
        "issuerName": "Issuer",
        "Type": "Stock Split",
        "Ratio": "1:5",
        "OldNominal": 100,
        "NewNominal": 20,
        "ListedShares": 500,
        "NumOfShares": 400,
        "ListingDate": "2024-06-20",
    })
    assert row["ticker"] == "ABCD"
    assert row["listing_date"] == "2024-06-20"
    assert len(row["row_identity_sha256"]) == 64


def test_family_compatibility_is_fail_closed() -> None:
    assert source_type_compatible("stock split", "Stock Split")
    assert not source_type_compatible("stock split", "Reverse Stock")
    assert source_type_compatible("reverse split", "Reverse Stock Split")
    assert not source_type_compatible("merger", "Stock Split")


def test_listing_date_is_linkage_only_with_bounded_distance() -> None:
    dates = [pd.Timestamp("2024-06-15")]
    assert listing_date_linked("2024-06-20", dates, max_distance_days=180)
    assert not listing_date_linked("2025-06-20", dates, max_distance_days=180)
