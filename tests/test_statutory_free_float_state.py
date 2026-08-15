from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from idx_trade.historical_statutory_free_float import (
    FreeFloatRevisionKind,
    FreeFloatSourceFamily,
    HistoricalFreeFloatObservation,
)
from idx_trade.statutory_free_float_state import (
    StatutoryFreeFloatKnowledgeStatus,
    eligible_from_session,
    normalize_official_sessions,
    resolve_statutory_free_float_state,
)


TZ = timezone(timedelta(hours=7))
SESSIONS = (
    date(2026, 5, 7),
    date(2026, 5, 8),
    date(2026, 5, 11),
    date(2026, 5, 12),
    date(2026, 6, 30),
    date(2026, 7, 1),
    date(2026, 8, 3),
)


def _row(
    record_id: str,
    *,
    ticker: str = "BBCA",
    as_of: date = date(2026, 3, 31),
    published_at: datetime = datetime(2026, 5, 6, 12, 0, tzinfo=TZ),
    shares: int = 424,
    pct: float = 42.4,
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
        total_listed_shares=1_000,
        source_family=family,
        revision_kind=revision,
        supersedes_record_id=supersedes,
        announcement_no=f"ANN-{record_id}",
        source_url=f"https://www.idx.id/StaticData/{record_id}.pdf",
        source_sha256=source_digit * 64,
        metadata_source_sha256="f" * 64,
        source_row_key=(ticker if family is FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS else None),
    )


def _resolve(observations, session=date(2026, 5, 8)):
    return resolve_statutory_free_float_state("BBCA", session, SESSIONS, observations)


def test_publication_on_trading_day_is_eligible_only_on_strictly_later_session() -> None:
    published = datetime(2026, 5, 7, 18, 0, tzinfo=TZ)
    assert eligible_from_session(published, SESSIONS) == date(2026, 5, 8)
    row = _row("trading-day", published_at=published)
    before = _resolve([row], session=date(2026, 5, 7))
    after = _resolve([row], session=date(2026, 5, 8))
    assert before.status is StatutoryFreeFloatKnowledgeStatus.NO_KNOWN_STATE
    assert after.status is StatutoryFreeFloatKnowledgeStatus.USABLE_OFFICIAL_LBRE_STATE
    assert after.eligible_from_session == date(2026, 5, 8)


def test_weekend_publication_uses_first_monday_session() -> None:
    row = _row("weekend", published_at=datetime(2026, 5, 9, 10, 0, tzinfo=TZ))
    assert eligible_from_session(row.published_at, SESSIONS) == date(2026, 5, 11)
    assert _resolve([row], session=date(2026, 5, 8)).status is StatutoryFreeFloatKnowledgeStatus.NO_KNOWN_STATE
    assert _resolve([row], session=date(2026, 5, 11)).status is StatutoryFreeFloatKnowledgeStatus.USABLE_OFFICIAL_LBRE_STATE


def test_correction_becomes_current_only_after_its_own_eligibility() -> None:
    original = _row("original", published_at=datetime(2026, 5, 6, 12, 0, tzinfo=TZ), shares=100)
    correction = _row(
        "correction",
        published_at=datetime(2026, 5, 8, 12, 0, tzinfo=TZ),
        shares=110,
        revision=FreeFloatRevisionKind.CORRECTION,
        supersedes="original",
        source_digit="b",
    )
    before = _resolve([original, correction], session=date(2026, 5, 8))
    after = _resolve([original, correction], session=date(2026, 5, 11))
    assert before.free_float_shares == 100
    assert after.free_float_shares == 110
    assert after.lbre_record_id == "correction"


def test_late_correction_to_old_position_cannot_regress_newer_economic_state() -> None:
    old = _row("old", as_of=date(2025, 12, 31), published_at=datetime(2026, 5, 6, 12, 0, tzinfo=TZ), shares=100)
    newer = _row("newer", as_of=date(2026, 3, 31), published_at=datetime(2026, 5, 7, 12, 0, tzinfo=TZ), shares=200, source_digit="b")
    old_correction = _row(
        "old-correction",
        as_of=date(2025, 12, 31),
        published_at=datetime(2026, 6, 30, 12, 0, tzinfo=TZ),
        shares=150,
        revision=FreeFloatRevisionKind.CORRECTION,
        supersedes="old",
        source_digit="c",
    )
    state = _resolve([old, newer, old_correction], session=date(2026, 7, 1))
    assert state.source_as_of_date == date(2026, 3, 31)
    assert state.free_float_shares == 200
    assert state.lbre_record_id == "newer"


def test_newer_snapshot_is_not_poisoned_by_later_old_period_market_conflict() -> None:
    newer = _row("newer", as_of=date(2026, 3, 31), published_at=datetime(2026, 5, 6, 12, 0, tzinfo=TZ), shares=200)
    old_market = _row(
        "old-market",
        as_of=date(2025, 12, 31),
        published_at=datetime(2026, 6, 30, 12, 0, tzinfo=TZ),
        shares=999,
        family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
        source_digit="b",
    )
    state = _resolve([newer, old_market], session=date(2026, 7, 1))
    assert state.source_as_of_date == date(2026, 3, 31)
    assert state.status is StatutoryFreeFloatKnowledgeStatus.USABLE_OFFICIAL_LBRE_STATE
    assert state.free_float_shares == 200


def test_lbre_then_later_market_validation_preserves_both_provenance_records() -> None:
    lbre = _row("lbre", published_at=datetime(2026, 5, 6, 12, 0, tzinfo=TZ), shares=100)
    market = _row(
        "market",
        published_at=datetime(2026, 6, 30, 12, 0, tzinfo=TZ),
        shares=100,
        family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
        source_digit="b",
    )
    before = _resolve([lbre, market], session=date(2026, 5, 8))
    after = _resolve([lbre, market], session=date(2026, 7, 1))
    assert before.status is StatutoryFreeFloatKnowledgeStatus.USABLE_OFFICIAL_LBRE_STATE
    assert after.status is StatutoryFreeFloatKnowledgeStatus.CROSS_SOURCE_SHARE_VALIDATED
    assert after.lbre_record_id == "lbre"
    assert after.market_record_id == "market"
    assert after.validation_published_at == market.published_at


def test_lbre_then_later_genuine_market_conflict_is_fail_closed() -> None:
    lbre = _row("lbre", published_at=datetime(2026, 5, 6, 12, 0, tzinfo=TZ), shares=100)
    market = _row(
        "market-conflict",
        published_at=datetime(2026, 6, 30, 12, 0, tzinfo=TZ),
        shares=101,
        family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
        source_digit="b",
    )
    state = _resolve([lbre, market], session=date(2026, 7, 1))
    assert state.status is StatutoryFreeFloatKnowledgeStatus.GENUINE_SHARE_COUNT_CONFLICT
    assert not state.denominator_eligible
    assert state.free_float_shares is None
    assert state.share_delta_lbre_minus_market == -1


def test_market_anchor_first_then_lbre_agree_or_conflict() -> None:
    market = _row(
        "market-first",
        published_at=datetime(2026, 5, 6, 12, 0, tzinfo=TZ),
        family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
        source_digit="a",
    )
    lbre = _row("lbre-later", published_at=datetime(2026, 6, 30, 12, 0, tzinfo=TZ), source_digit="b")
    agree = _resolve([market, lbre], session=date(2026, 7, 1))
    assert agree.status is StatutoryFreeFloatKnowledgeStatus.CROSS_SOURCE_SHARE_VALIDATED

    conflict = _resolve(
        [market, _row("lbre-conflict", published_at=datetime(2026, 6, 30, 12, 0, tzinfo=TZ), shares=101, source_digit="c")],
        session=date(2026, 7, 1),
    )
    assert conflict.status is StatutoryFreeFloatKnowledgeStatus.GENUINE_SHARE_COUNT_CONFLICT


def test_percentage_only_disagreement_does_not_block_denominator() -> None:
    lbre = _row("lbre", shares=100, pct=10.0, published_at=datetime(2026, 5, 6, 12, 0, tzinfo=TZ))
    market = _row(
        "market",
        shares=100,
        pct=11.0,
        published_at=datetime(2026, 6, 30, 12, 0, tzinfo=TZ),
        family=FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS,
        source_digit="b",
    )
    state = _resolve([lbre, market], session=date(2026, 7, 1))
    assert state.status is StatutoryFreeFloatKnowledgeStatus.PERCENTAGE_ONLY_DISAGREEMENT
    assert state.denominator_eligible
    assert state.free_float_shares == 100
    assert state.percentage_delta_pp_lbre_minus_market == -1.0


def test_no_observation_is_explicit() -> None:
    state = resolve_statutory_free_float_state("BBCA", date(2026, 5, 8), SESSIONS, [])
    assert state.status is StatutoryFreeFloatKnowledgeStatus.NO_KNOWN_STATE
    assert not state.denominator_eligible


def test_zero_denominator_is_preserved_but_not_eligible() -> None:
    state = _resolve([_row("zero", shares=0)])
    assert state.status is StatutoryFreeFloatKnowledgeStatus.INVALID_DENOMINATOR
    assert state.lbre_free_float_shares == 0
    assert not state.denominator_eligible
    assert state.free_float_shares is None


def test_duplicate_or_ambiguous_lineage_fails_closed() -> None:
    first = _row("first", shares=100)
    second = _row("second", shares=101, source_digit="b")
    with pytest.raises(ValueError, match="duplicate original"):
        _resolve([first, second])


def test_timezone_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _row("naive", published_at=datetime(2026, 5, 6, 12, 0))


def test_duplicate_official_session_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate official session"):
        normalize_official_sessions([date(2026, 5, 7), date(2026, 5, 7)])


def test_state_exposes_knowledge_and_economic_ages() -> None:
    row = _row("age", published_at=datetime(2026, 5, 6, 12, 0, tzinfo=TZ))
    state = _resolve([row], session=date(2026, 5, 11))
    assert state.knowledge_age_sessions == 2
    assert state.knowledge_age_days == 5
    assert state.economic_position_age_sessions == 2
    assert state.economic_position_age_days == 41
