from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.historical_universe import (
    audit_price_lifecycle_consistency,
    canonicalize_lifecycle_records,
    canonicalize_universe_coverage,
    compare_current_universe,
    historical_universe_as_of,
    lifecycle_to_security_master,
    universe_coverage_complete_on,
)
from idx_trade.security_master import existence_state
from idx_trade.states import ExistenceState


def _lifecycle() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AAAA.JK",
                "company_name": "Alpha",
                "listed_from": "2020-01-02",
                "listed_to": None,
                "source": "IDX",
                "source_ref": "alpha",
            },
            {
                "ticker": "BBBB",
                "company_name": "Beta",
                "listed_from": "2021-02-01",
                "listed_to": "2022-06-30",
                "source": "IDX",
                "source_ref": "beta-1",
            },
            {
                "ticker": "BBBB",
                "company_name": "Beta",
                "listed_from": "2023-01-10",
                "listed_to": None,
                "source": "IDX",
                "source_ref": "beta-2",
            },
        ]
    )


def test_canonicalize_lifecycle_normalizes_tickers_and_dates() -> None:
    result = canonicalize_lifecycle_records(_lifecycle())

    assert result["ticker"].tolist() == ["AAAA", "BBBB", "BBBB"]
    assert result.iloc[0]["listed_from"] == pd.Timestamp("2020-01-02")
    assert pd.isna(result.iloc[0]["listed_to"])


def test_canonicalize_lifecycle_rejects_overlapping_intervals() -> None:
    frame = pd.DataFrame(
        [
            {
                "ticker": "AAAA",
                "listed_from": "2020-01-01",
                "listed_to": "2021-01-31",
                "source": "IDX",
            },
            {
                "ticker": "AAAA",
                "listed_from": "2021-01-31",
                "listed_to": None,
                "source": "IDX",
            },
        ]
    )

    with pytest.raises(ValueError, match="Overlapping lifecycle intervals"):
        canonicalize_lifecycle_records(frame)


def test_canonicalize_lifecycle_rejects_duplicate_unreconciled_evidence() -> None:
    frame = pd.DataFrame(
        [
            {
                "ticker": "AAAA",
                "listed_from": "2020-01-01",
                "listed_to": None,
                "source": "IDX-A",
            },
            {
                "ticker": "AAAA",
                "listed_from": "2020-01-01",
                "listed_to": None,
                "source": "IDX-B",
            },
        ]
    )

    with pytest.raises(ValueError, match="explicit upstream reconciliation"):
        canonicalize_lifecycle_records(frame)


def test_historical_universe_excludes_future_ipo_and_handles_relisting() -> None:
    lifecycle = _lifecycle()

    before_beta = historical_universe_as_of(lifecycle, pd.Timestamp("2020-06-01"))
    beta_first = historical_universe_as_of(lifecycle, pd.Timestamp("2022-06-30"))
    beta_gap = historical_universe_as_of(lifecycle, pd.Timestamp("2022-07-01"))
    beta_relisted = historical_universe_as_of(lifecycle, pd.Timestamp("2023-01-10"))

    assert set(before_beta["ticker"]) == {"AAAA"}
    assert set(beta_first["ticker"]) == {"AAAA", "BBBB"}
    assert set(beta_gap["ticker"]) == {"AAAA"}
    assert set(beta_relisted["ticker"]) == {"AAAA", "BBBB"}


def test_lifecycle_bridge_matches_existing_existence_semantics() -> None:
    master = lifecycle_to_security_master(_lifecycle())

    assert existence_state(master, "BBBB", pd.Timestamp("2020-12-31")) is ExistenceState.NOT_LISTED
    assert existence_state(master, "BBBB", pd.Timestamp("2022-06-30")) is ExistenceState.LISTED
    assert existence_state(master, "BBBB", pd.Timestamp("2022-07-01")) is ExistenceState.DELISTED
    assert existence_state(master, "BBBB", pd.Timestamp("2023-01-10")) is ExistenceState.LISTED


def test_price_lifecycle_audit_finds_unknown_and_outside_interval_rows() -> None:
    observations = pd.DataFrame(
        [
            {"ticker": "AAAA", "date": "2020-01-02"},
            {"ticker": "BBBB", "date": "2022-06-30"},
            {"ticker": "BBBB", "date": "2022-08-01"},
            {"ticker": "CCCC", "date": "2024-01-02"},
        ]
    )

    issues = audit_price_lifecycle_consistency(_lifecycle(), observations)

    assert issues.to_dict("records") == [
        {
            "ticker": "BBBB",
            "date": pd.Timestamp("2022-08-01"),
            "issue": "OBSERVED_OUTSIDE_LISTING_INTERVAL",
        },
        {
            "ticker": "CCCC",
            "date": pd.Timestamp("2024-01-02"),
            "issue": "NO_LIFECYCLE_RECORD",
        },
    ]


def test_current_snapshot_comparison_is_fail_visible() -> None:
    mismatches = compare_current_universe(
        _lifecycle(),
        ["AAAA.JK", "CCCC"],
        pd.Timestamp("2024-01-02"),
    )

    assert mismatches.to_dict("records") == [
        {"ticker": "CCCC", "issue": "MISSING_FROM_LIFECYCLE_SNAPSHOT"},
        {"ticker": "BBBB", "issue": "STALE_LISTED_IN_LIFECYCLE_SNAPSHOT"},
    ]


def test_universe_coverage_requires_bounded_window_and_basis() -> None:
    raw = pd.DataFrame(
        [
            {
                "effective_from": "2020-01-01",
                "effective_to": "2023-12-31",
                "source": "IDX_ARCHIVE",
                "is_complete": True,
                "discovery_basis": "complete listing/delisting census",
            },
            {
                "effective_from": "2024-01-01",
                "effective_to": None,
                "source": "IDX_CURRENT",
                "is_complete": True,
                "discovery_basis": "",
            },
        ]
    )

    coverage = canonicalize_universe_coverage(raw)

    assert coverage["is_complete"].tolist() == [True, False]
    assert universe_coverage_complete_on(coverage, pd.Timestamp("2022-06-01"))
    assert not universe_coverage_complete_on(coverage, pd.Timestamp("2024-06-01"))
