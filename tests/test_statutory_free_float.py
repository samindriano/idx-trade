from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from idx_trade.statutory_free_float import (
    FreeFloatRuleVersion,
    FreeFloatSnapshotStatus,
    FreeFloatSource,
    StatutoryFreeFloatSnapshot,
    official_reported_free_float,
    reconstruct_statutory_free_float,
)


TZ = timezone(timedelta(hours=7))


def _source(digit: str = "a") -> FreeFloatSource:
    return FreeFloatSource(
        source_type="IDX_FREE_FLOAT_STATUS_ANNOUNCEMENT",
        source_url="https://www.idx.id/StaticData/free-float.pdf",
        source_sha256=digit * 64,
        announcement_no="Peng-S-00011/BEI.PLP/04-2026",
    )


def test_official_reported_is_preserved_without_reconstructing_holder_buckets() -> None:
    snapshot = official_reported_free_float(
        ticker="BBCA",
        as_of_date=date(2026, 3, 31),
        published_at=datetime(2026, 4, 30, 18, 0, tzinfo=TZ),
        rule_version=FreeFloatRuleVersion.IDX_I_A_2026,
        free_float_shares=10_000_000,
        free_float_pct=42.4,
        sources=(_source(),),
    )
    assert snapshot.status is FreeFloatSnapshotStatus.OFFICIAL_REPORTED
    assert snapshot.free_float_shares == 10_000_000
    assert snapshot.free_float_pct == 42.4
    assert snapshot.unresolved_shares is None
    assert snapshot.lower_bound_shares is None


def test_bounded_reconstruction_forbids_point_estimate_when_any_shares_unresolved() -> None:
    snapshot = reconstruct_statutory_free_float(
        ticker="DCII",
        as_of_date=date(2026, 6, 30),
        published_at=datetime(2026, 7, 10, 18, 0, tzinfo=TZ),
        rule_version=FreeFloatRuleVersion.IDX_I_A_2026,
        total_listed_shares=1_000,
        confirmed_eligible_shares=15,
        confirmed_excluded_shares=975,
        unresolved_shares=10,
        sources=(_source(),),
    )
    assert snapshot.status is FreeFloatSnapshotStatus.BOUNDED_ONLY
    assert snapshot.free_float_shares is None
    assert snapshot.free_float_pct is None
    assert snapshot.lower_bound_shares == 15
    assert snapshot.upper_bound_shares == 25


def test_verified_reconstruction_requires_every_share_to_be_classified() -> None:
    snapshot = reconstruct_statutory_free_float(
        ticker="BBCA",
        as_of_date=date(2026, 6, 30),
        published_at=datetime(2026, 7, 10, 18, 0, tzinfo=TZ),
        rule_version=FreeFloatRuleVersion.IDX_I_A_2026,
        total_listed_shares=1_000,
        confirmed_eligible_shares=424,
        confirmed_excluded_shares=576,
        unresolved_shares=0,
        sources=(_source(),),
    )
    assert snapshot.status is FreeFloatSnapshotStatus.RECONSTRUCTED_VERIFIED
    assert snapshot.free_float_shares == 424
    assert snapshot.free_float_pct == pytest.approx(42.4)
    assert snapshot.lower_bound_shares == 424
    assert snapshot.upper_bound_shares == 424


def test_bucket_arithmetic_must_reconcile_exactly_to_total_listed_shares() -> None:
    with pytest.raises(ValueError, match="exactly reconcile"):
        reconstruct_statutory_free_float(
            ticker="BBCA",
            as_of_date=date(2026, 6, 30),
            published_at=datetime(2026, 7, 10, 18, 0, tzinfo=TZ),
            rule_version=FreeFloatRuleVersion.IDX_I_A_2026,
            total_listed_shares=1_000,
            confirmed_eligible_shares=400,
            confirmed_excluded_shares=500,
            unresolved_shares=50,
            sources=(_source(),),
        )


def test_rule_version_boundary_is_explicit() -> None:
    with pytest.raises(ValueError, match="cannot apply before"):
        official_reported_free_float(
            ticker="BBCA",
            as_of_date=date(2026, 3, 30),
            published_at=datetime(2026, 4, 1, 18, 0, tzinfo=TZ),
            rule_version=FreeFloatRuleVersion.IDX_I_A_2026,
            free_float_shares=100,
            free_float_pct=10.0,
            sources=(_source(),),
        )

    with pytest.raises(ValueError, match="cannot apply on/after"):
        official_reported_free_float(
            ticker="BBCA",
            as_of_date=date(2026, 3, 31),
            published_at=datetime(2026, 4, 1, 18, 0, tzinfo=TZ),
            rule_version=FreeFloatRuleVersion.IDX_I_A_2021,
            free_float_shares=100,
            free_float_pct=10.0,
            sources=(_source(),),
        )


def test_knowledge_time_must_be_causal_and_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        official_reported_free_float(
            ticker="BBCA",
            as_of_date=date(2026, 3, 31),
            published_at=datetime(2026, 4, 30, 18, 0),
            rule_version=FreeFloatRuleVersion.IDX_I_A_2026,
            free_float_shares=100,
            free_float_pct=10.0,
            sources=(_source(),),
        )

    with pytest.raises(ValueError, match="as_of_date cannot be after"):
        official_reported_free_float(
            ticker="BBCA",
            as_of_date=date(2026, 5, 1),
            published_at=datetime(2026, 4, 30, 18, 0, tzinfo=TZ),
            rule_version=FreeFloatRuleVersion.IDX_I_A_2026,
            free_float_shares=100,
            free_float_pct=10.0,
            sources=(_source(),),
        )


def test_unresolved_status_cannot_leak_numeric_estimates() -> None:
    with pytest.raises(ValueError, match="UNRESOLVED must not expose"):
        StatutoryFreeFloatSnapshot(
            ticker="DCII",
            as_of_date=date(2026, 6, 30),
            published_at=datetime(2026, 7, 10, 18, 0, tzinfo=TZ),
            rule_version=FreeFloatRuleVersion.IDX_I_A_2026,
            status=FreeFloatSnapshotStatus.UNRESOLVED,
            free_float_shares=None,
            free_float_pct=None,
            total_listed_shares=1_000,
            confirmed_eligible_shares=None,
            confirmed_excluded_shares=None,
            unresolved_shares=None,
            lower_bound_shares=None,
            upper_bound_shares=None,
            sources=(_source(),),
        )


def test_non_official_source_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="official IDX/KSEI URL"):
        FreeFloatSource(
            source_type="MIRROR",
            source_url="https://example.com/free-float.csv",
            source_sha256="a" * 64,
        )
