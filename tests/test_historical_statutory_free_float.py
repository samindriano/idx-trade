from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from idx_trade.historical_statutory_free_float import (
    FreeFloatCrossSourceStatus,
    FreeFloatRevisionKind,
    FreeFloatSourceFamily,
    HistoricalFreeFloatObservation,
    arithmetic_percentage_difference,
    census_historical_free_float,
    reconcile_cross_source,
    replay_historical_free_float,
)


TZ = timezone(timedelta(hours=7))


def _row(
    record_id: str,
    *,
    ticker: str = "BBCA",
    as_of: date = date(2026, 3, 31),
    published_at: datetime = datetime(2026, 5, 7, 12, 0, tzinfo=TZ),
    shares: int = 424,
    pct: float = 42.4,
    total: int | None = 1_000,
    family: FreeFloatSourceFamily = FreeFloatSourceFamily.ISSUER_LBRE,
    revision: FreeFloatRevisionKind = FreeFloatRevisionKind.ORIGINAL,
    supersedes: str | None = None,
    source_digit: str = "a",
) -> HistoricalFreeFloatObservation:
    return HistoricalFreeFloatObservation(
        record_id=record_id,
        ticker=ticker,
        as_of_date=as_of,
        published_at=published_at,
        free_float_shares=shares,
        free_float_pct=pct,
        total_listed_shares=total,
        source_family=family,
        revision_kind=revision,
        supersedes_record_id=supersedes,
        announcement_no=f"ANN-{record_id}",
        source_url=f"https://www.idx.id/StaticData/{record_id}.pdf",
        source_sha256=source_digit * 64,
        metadata_source_sha256="f" * 64,
        source_row_key=(ticker if family is FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS else None),
    )


def test_original_and_correction_are_pit_replayed() -> None:
    original = _row(
        "maya-original",
        ticker="MAYA",
        shares=100,
        pct=10.0,
        published_at=datetime(2026, 5, 7, 9, 0, tzinfo=TZ),
    )
    correction = _row(
        "maya-correction",
        ticker="MAYA",
        shares=110,
        pct=11.0,
        published_at=datetime(2026, 5, 8, 9, 0, tzinfo=TZ),
        revision=FreeFloatRevisionKind.CORRECTION,
        supersedes="maya-original",
        source_digit="b",
    )

    before = replay_historical_free_float(
        [correction, original],
        cutoff=datetime(2026, 5, 7, 23, 59, tzinfo=TZ),
    )
    assert next(iter(before.current.values())).record_id == "maya-original"

    after = replay_historical_free_float([correction, original])
    assert next(iter(after.current.values())).record_id == "maya-correction"


def test_stale_or_cross_identity_correction_fails_closed() -> None:
    original = _row("original")
    correction = _row(
        "correction",
        published_at=datetime(2026, 5, 8, 12, 0, tzinfo=TZ),
        revision=FreeFloatRevisionKind.CORRECTION,
        supersedes="original",
        source_digit="b",
    )
    stale = _row(
        "stale",
        published_at=datetime(2026, 5, 9, 12, 0, tzinfo=TZ),
        revision=FreeFloatRevisionKind.CORRECTION,
        supersedes="original",
        source_digit="c",
    )
    with pytest.raises(ValueError, match="ambiguous or stale"):
        replay_historical_free_float([original, correction, stale])

    wrong_ticker = _row(
        "wrong-ticker",
        ticker="BREN",
        published_at=datetime(2026, 5, 8, 12, 0, tzinfo=TZ),
        revision=FreeFloatRevisionKind.CORRECTION,
        supersedes="original",
        source_digit="d",
    )
    with pytest.raises(ValueError, match="identity differs"):
        replay_historical_free_float([original, wrong_ticker])


def test_market_wide_rows_require_row_locator_but_may_share_attachment_hash() -> None:
    with pytest.raises(ValueError, match="source_row_key"):
        HistoricalFreeFloatObservation(
            record_id="market-bbca",
            ticker="BBCA",
            as_of_date=date(2026, 3, 31),
            published_at=datetime(2026, 5, 7, 12, 0, tzinfo=TZ),
            free_float_shares=424,
            free_float_pct=42.4,
            total_listed_shares=1_000,
            source_family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
            revision_kind=FreeFloatRevisionKind.ORIGINAL,
            supersedes_record_id=None,
            announcement_no="Peng-S-00011/BEI.PLP/04-2026",
            source_url="https://www.idx.id/StaticData/market.pdf",
            source_sha256="a" * 64,
            metadata_source_sha256="b" * 64,
            source_row_key=None,
        )

    bbca = _row(
        "market-bbca",
        family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
        source_digit="a",
    )
    bren = _row(
        "market-bren",
        ticker="BREN",
        shares=123,
        pct=12.3,
        family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
        source_digit="a",
    )
    replay = replay_historical_free_float([bbca, bren])
    assert len(replay.current) == 2


def test_matching_lbre_and_market_wide_observations_agree() -> None:
    lbre = _row("lbre")
    market = _row(
        "market",
        family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
        source_digit="b",
    )
    reconciliation = reconcile_cross_source(
        replay_historical_free_float([lbre, market])
    )
    assert len(reconciliation) == 1
    assert reconciliation[0].status is FreeFloatCrossSourceStatus.AGREE
    assert reconciliation[0].share_spread == 0


def test_cross_source_disagreement_is_never_silently_resolved() -> None:
    lbre = _row("lbre")
    market = _row(
        "market",
        shares=425,
        pct=42.5,
        family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
        source_digit="b",
    )
    reconciliation = reconcile_cross_source(
        replay_historical_free_float([lbre, market])
    )
    assert reconciliation[0].status is FreeFloatCrossSourceStatus.CONFLICT
    assert reconciliation[0].share_spread == 1
    assert reconciliation[0].percentage_point_spread == pytest.approx(0.1)


def test_single_source_is_explicit_not_treated_as_cross_source_pass() -> None:
    reconciliation = reconcile_cross_source(
        replay_historical_free_float([_row("lbre")])
    )
    assert reconciliation[0].status is FreeFloatCrossSourceStatus.SINGLE_SOURCE


def test_knowledge_time_is_causal_and_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _row("naive", published_at=datetime(2026, 5, 7, 12, 0))

    with pytest.raises(ValueError, match="as_of_date cannot be after"):
        _row(
            "future-asof",
            as_of=date(2026, 5, 8),
            published_at=datetime(2026, 5, 7, 12, 0, tzinfo=TZ),
        )


def test_free_float_shares_cannot_exceed_total_and_pct_diagnostic_is_non_authoritative() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        _row("bad-total", shares=1_001, total=1_000)

    row = _row("rounding", shares=424, pct=42.39, total=1_000)
    assert arithmetic_percentage_difference(row) == pytest.approx(-0.01)
    assert row.free_float_pct == 42.39


def test_cutoff_does_not_forward_fill_or_create_unpublished_months() -> None:
    march = _row("march", as_of=date(2026, 3, 31))
    replay = replay_historical_free_float(
        [march],
        cutoff=datetime(2026, 8, 15, 23, 59, tzinfo=TZ),
    )
    assert len(replay.current) == 1
    only = next(iter(replay.current.values()))
    assert only.as_of_date == date(2026, 3, 31)


def test_census_reports_only_observed_dates_and_sources() -> None:
    march_lbre = _row("march-lbre")
    march_market = _row(
        "march-market",
        family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
        source_digit="b",
    )
    june = _row(
        "june-lbre",
        as_of=date(2026, 6, 30),
        published_at=datetime(2026, 7, 7, 12, 0, tzinfo=TZ),
        source_digit="c",
    )
    replay = replay_historical_free_float([march_lbre, march_market, june])
    census = census_historical_free_float(replay)

    assert census.admitted_record_count == 3
    assert census.current_observation_count == 3
    assert census.unique_ticker_count == 1
    assert census.unique_as_of_dates == (date(2026, 3, 31), date(2026, 6, 30))
    assert census.issuer_count_by_as_of_date == {
        date(2026, 3, 31): 1,
        date(2026, 6, 30): 1,
    }
    assert census.current_source_family_counts == {
        "IDX_MARKET_WIDE_FF_STATUS": 1,
        "ISSUER_LBRE": 2,
    }
    assert census.cross_source_status_counts == {"AGREE": 1, "SINGLE_SOURCE": 1}
