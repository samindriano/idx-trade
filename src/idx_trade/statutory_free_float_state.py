"""PIT knowledge-state resolution for official statutory free-float observations.

This module intentionally resolves one ticker/session query at a time.  It does
not create a synthetic calendar-day or ticker-month panel and it never chooses
between conflicting official share counts.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from math import isfinite
from typing import Iterable
from zoneinfo import ZoneInfo

from .historical_statutory_free_float import (
    FreeFloatSourceFamily,
    HistoricalFreeFloatObservation,
    replay_historical_free_float,
)


JAKARTA = ZoneInfo("Asia/Jakarta")
DEFAULT_PERCENTAGE_TOLERANCE = 0.01


class StatutoryFreeFloatKnowledgeStatus(str, Enum):
    USABLE_OFFICIAL_LBRE_STATE = "USABLE_OFFICIAL_LBRE_STATE"
    USABLE_MARKET_ANCHOR_ONLY_STATE = "USABLE_MARKET_ANCHOR_ONLY_STATE"
    CROSS_SOURCE_SHARE_VALIDATED = "CROSS_SOURCE_SHARE_VALIDATED"
    PERCENTAGE_ONLY_DISAGREEMENT = "PERCENTAGE_ONLY_DISAGREEMENT"
    GENUINE_SHARE_COUNT_CONFLICT = "GENUINE_SHARE_COUNT_CONFLICT"
    NO_KNOWN_STATE = "NO_KNOWN_STATE"
    INVALID_DENOMINATOR = "INVALID_DENOMINATOR"


@dataclass(frozen=True)
class StatutoryFreeFloatKnowledgeState:
    """State that was knowable for one ticker on one official session.

    ``free_float_shares`` is populated only when the surfaced state has one
    unambiguous positive denominator.  The source-specific fields remain
    populated for diagnostics even when the state is invalid or conflicting.
    """

    ticker: str
    session_date: date
    status: StatutoryFreeFloatKnowledgeStatus
    denominator_eligible: bool
    free_float_shares: int | None
    free_float_pct: float | None
    source_as_of_date: date | None
    first_known_source_families: tuple[FreeFloatSourceFamily, ...]
    first_known_record_ids: tuple[str, ...]
    first_known_published_at: datetime | None
    first_known_eligible_from_session: date | None
    status_effective_published_at: datetime | None
    status_effective_eligible_from_session: date | None
    status_age_sessions: int | None
    status_age_days: int | None
    # Backward-compatible aliases: these now mean first-known time, not LBRE time.
    source_published_at: datetime | None
    eligible_from_session: date | None
    knowledge_age_sessions: int | None
    knowledge_age_days: int | None
    economic_position_age_sessions: int | None
    economic_position_age_days: int | None
    lbre_record_id: str | None
    lbre_source_sha256: str | None
    lbre_metadata_source_sha256: str | None
    lbre_as_of_date: date | None
    lbre_published_at: datetime | None
    lbre_eligible_from_session: date | None
    lbre_free_float_shares: int | None
    lbre_free_float_pct: float | None
    market_record_id: str | None
    market_source_sha256: str | None
    market_metadata_source_sha256: str | None
    market_as_of_date: date | None
    market_published_at: datetime | None
    market_eligible_from_session: date | None
    market_free_float_shares: int | None
    market_free_float_pct: float | None
    validation_published_at: datetime | None
    share_delta_lbre_minus_market: int | None
    percentage_delta_pp_lbre_minus_market: float | None


def _local_publication_date(published_at: datetime) -> date:
    if published_at.tzinfo is None or published_at.utcoffset() is None:
        raise ValueError("published_at must be timezone-aware")
    return published_at.astimezone(JAKARTA).date()


def normalize_official_sessions(
    official_sessions: Iterable[date | datetime],
) -> tuple[date, ...]:
    """Normalize an explicit official IDX session set and reject ambiguity."""

    normalized: list[date] = []
    for session in official_sessions:
        if isinstance(session, datetime):
            if session.tzinfo is None or session.utcoffset() is None:
                raise ValueError("official session datetime must be timezone-aware")
            normalized.append(session.astimezone(JAKARTA).date())
        elif isinstance(session, date):
            normalized.append(session)
        else:
            raise TypeError("official sessions must contain date or datetime values")

    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate official session date")
    return tuple(sorted(normalized))


def eligible_from_session(
    published_at: datetime,
    official_sessions: Iterable[date | datetime],
) -> date | None:
    """Return the first supplied official session strictly after local publication date."""

    sessions = normalize_official_sessions(official_sessions)
    publication_date = _local_publication_date(published_at)
    index = bisect_left(sessions, publication_date)
    while index < len(sessions) and sessions[index] <= publication_date:
        index += 1
    return sessions[index] if index < len(sessions) else None


def _age_sessions(sessions: tuple[date, ...], start: date, current: date) -> int:
    start_index = bisect_left(sessions, start)
    current_index = bisect_left(sessions, current)
    if start_index >= len(sessions) or current_index >= len(sessions):
        raise ValueError("state age date is outside official session set")
    if sessions[start_index] != start or sessions[current_index] != current:
        raise ValueError("state age date is not an official session")
    return current_index - start_index


def _economic_age_sessions(
    sessions: tuple[date, ...],
    as_of_date: date,
    current: date,
) -> int:
    anchor_index = bisect_left(sessions, as_of_date)
    current_index = bisect_left(sessions, current)
    if current_index >= len(sessions) or current_index < anchor_index:
        raise ValueError("economic position is after queried session")
    return current_index - anchor_index


def _eligible_observations(
    observations: tuple[HistoricalFreeFloatObservation, ...],
    sessions: tuple[date, ...],
    session_date: date,
) -> tuple[HistoricalFreeFloatObservation, ...]:
    eligible: list[HistoricalFreeFloatObservation] = []
    for observation in observations:
        first_session = eligible_from_session(observation.published_at, sessions)
        if first_session is not None and first_session <= session_date:
            eligible.append(observation)
    return tuple(eligible)


def _pick_source_rows(
    observations: tuple[HistoricalFreeFloatObservation, ...],
) -> dict[FreeFloatSourceFamily, HistoricalFreeFloatObservation]:
    replay = replay_historical_free_float(observations)
    return {
        family: observation
        for (ticker, _as_of_date, family), observation in replay.current.items()
        if ticker == observation.ticker
    }


def _row_eligible_from(
    observation: HistoricalFreeFloatObservation | None,
    sessions: tuple[date, ...],
) -> date | None:
    return None if observation is None else eligible_from_session(observation.published_at, sessions)


def _state_from_rows(
    *,
    ticker: str,
    session_date: date,
    sessions: tuple[date, ...],
    lbre: HistoricalFreeFloatObservation | None,
    market: HistoricalFreeFloatObservation | None,
    percentage_tolerance: float,
) -> StatutoryFreeFloatKnowledgeState:
    lbre_eligible = _row_eligible_from(lbre, sessions)
    market_eligible = _row_eligible_from(market, sessions)
    candidates = tuple(row for row in (lbre, market) if row is not None)
    source_as_of = max((row.as_of_date for row in candidates), default=None)
    if source_as_of is None:
        return StatutoryFreeFloatKnowledgeState(
            ticker=ticker,
            session_date=session_date,
            status=StatutoryFreeFloatKnowledgeStatus.NO_KNOWN_STATE,
            denominator_eligible=False,
            free_float_shares=None,
            free_float_pct=None,
            source_as_of_date=None,
            first_known_source_families=(),
            first_known_record_ids=(),
            first_known_published_at=None,
            first_known_eligible_from_session=None,
            status_effective_published_at=None,
            status_effective_eligible_from_session=None,
            status_age_sessions=None,
            status_age_days=None,
            source_published_at=None,
            eligible_from_session=None,
            knowledge_age_sessions=None,
            knowledge_age_days=None,
            economic_position_age_sessions=None,
            economic_position_age_days=None,
            lbre_record_id=None,
            lbre_source_sha256=None,
            lbre_metadata_source_sha256=None,
            lbre_as_of_date=None,
            lbre_published_at=None,
            lbre_eligible_from_session=None,
            lbre_free_float_shares=None,
            lbre_free_float_pct=None,
            market_record_id=None,
            market_source_sha256=None,
            market_metadata_source_sha256=None,
            market_as_of_date=None,
            market_published_at=None,
            market_eligible_from_session=None,
            market_free_float_shares=None,
            market_free_float_pct=None,
            validation_published_at=None,
            share_delta_lbre_minus_market=None,
            percentage_delta_pp_lbre_minus_market=None,
        )

    if lbre is not None and lbre.as_of_date != source_as_of:
        lbre = None
        lbre_eligible = None
    if market is not None and market.as_of_date != source_as_of:
        market = None
        market_eligible = None

    selected_rows = tuple(row for row in (lbre, market) if row is not None)
    selected_eligibility = tuple(
        eligible
        for eligible in (lbre_eligible, market_eligible)
        if eligible is not None
    )
    first_known_published_at = min(row.published_at for row in selected_rows)
    first_known_eligible = min(selected_eligibility)
    first_known_rows = tuple(
        sorted(
            (row for row in selected_rows if row.published_at == first_known_published_at),
            key=lambda row: (row.source_family.value, row.record_id),
        )
    )
    if first_known_eligible is None or first_known_published_at is None:
        raise ValueError("selected observation has no eligible session")

    age_sessions = _age_sessions(sessions, first_known_eligible, session_date)
    age_days = (session_date - _local_publication_date(first_known_published_at)).days
    economic_age_sessions = _economic_age_sessions(sessions, source_as_of, session_date)
    economic_age_days = (session_date - source_as_of).days

    share_delta = None
    pct_delta = None
    validation_published_at = None
    if lbre is not None and market is not None:
        share_delta = lbre.free_float_shares - market.free_float_shares
        pct_delta = lbre.free_float_pct - market.free_float_pct
        if share_delta != 0:
            status = StatutoryFreeFloatKnowledgeStatus.GENUINE_SHARE_COUNT_CONFLICT
            denominator_eligible = False
            selected_shares = None
            selected_pct = None
        elif pct_delta == 0.0:
            status = StatutoryFreeFloatKnowledgeStatus.CROSS_SOURCE_SHARE_VALIDATED
            denominator_eligible = lbre.free_float_shares > 0
            selected_shares = lbre.free_float_shares if denominator_eligible else None
            selected_pct = lbre.free_float_pct if denominator_eligible else None
        elif abs(pct_delta) > percentage_tolerance:
            status = StatutoryFreeFloatKnowledgeStatus.PERCENTAGE_ONLY_DISAGREEMENT
            denominator_eligible = lbre.free_float_shares > 0
            selected_shares = lbre.free_float_shares if denominator_eligible else None
            selected_pct = None
        else:
            # Diagnostic share validation can pass within tolerance, but a
            # non-identical official percentage is never canonicalized.
            status = StatutoryFreeFloatKnowledgeStatus.CROSS_SOURCE_SHARE_VALIDATED
            denominator_eligible = lbre.free_float_shares > 0
            selected_shares = lbre.free_float_shares if denominator_eligible else None
            selected_pct = None
    elif lbre is not None:
        status = StatutoryFreeFloatKnowledgeStatus.USABLE_OFFICIAL_LBRE_STATE
        denominator_eligible = lbre.free_float_shares > 0
        selected_shares = lbre.free_float_shares if denominator_eligible else None
        selected_pct = lbre.free_float_pct if denominator_eligible else None
    else:
        status = StatutoryFreeFloatKnowledgeStatus.USABLE_MARKET_ANCHOR_ONLY_STATE
        denominator_eligible = market.free_float_shares > 0
        selected_shares = market.free_float_shares if denominator_eligible else None
        selected_pct = market.free_float_pct if denominator_eligible else None

    if (
        status
        in {
            StatutoryFreeFloatKnowledgeStatus.USABLE_OFFICIAL_LBRE_STATE,
            StatutoryFreeFloatKnowledgeStatus.USABLE_MARKET_ANCHOR_ONLY_STATE,
            StatutoryFreeFloatKnowledgeStatus.CROSS_SOURCE_SHARE_VALIDATED,
            StatutoryFreeFloatKnowledgeStatus.PERCENTAGE_ONLY_DISAGREEMENT,
        }
        and not denominator_eligible
    ):
        status = StatutoryFreeFloatKnowledgeStatus.INVALID_DENOMINATOR

    status_effective_published_at = max(row.published_at for row in selected_rows) if len(selected_rows) > 1 else first_known_published_at
    status_effective_eligible = max(selected_eligibility) if len(selected_rows) > 1 else first_known_eligible
    status_age_sessions = _age_sessions(sessions, status_effective_eligible, session_date)
    status_age_days = (session_date - _local_publication_date(status_effective_published_at)).days
    validation_published_at = status_effective_published_at if len(selected_rows) > 1 else None

    return StatutoryFreeFloatKnowledgeState(
        ticker=ticker,
        session_date=session_date,
        status=status,
        denominator_eligible=denominator_eligible,
        free_float_shares=selected_shares,
        free_float_pct=selected_pct,
        source_as_of_date=source_as_of,
        first_known_source_families=tuple(row.source_family for row in first_known_rows),
        first_known_record_ids=tuple(row.record_id for row in first_known_rows),
        first_known_published_at=first_known_published_at,
        first_known_eligible_from_session=first_known_eligible,
        status_effective_published_at=status_effective_published_at,
        status_effective_eligible_from_session=status_effective_eligible,
        status_age_sessions=status_age_sessions,
        status_age_days=status_age_days,
        source_published_at=first_known_published_at,
        eligible_from_session=first_known_eligible,
        knowledge_age_sessions=age_sessions,
        knowledge_age_days=age_days,
        economic_position_age_sessions=economic_age_sessions,
        economic_position_age_days=economic_age_days,
        lbre_record_id=None if lbre is None else lbre.record_id,
        lbre_source_sha256=None if lbre is None else lbre.source_sha256,
        lbre_metadata_source_sha256=None if lbre is None else lbre.metadata_source_sha256,
        lbre_as_of_date=None if lbre is None else lbre.as_of_date,
        lbre_published_at=None if lbre is None else lbre.published_at,
        lbre_eligible_from_session=lbre_eligible,
        lbre_free_float_shares=None if lbre is None else lbre.free_float_shares,
        lbre_free_float_pct=None if lbre is None else lbre.free_float_pct,
        market_record_id=None if market is None else market.record_id,
        market_source_sha256=None if market is None else market.source_sha256,
        market_metadata_source_sha256=None if market is None else market.metadata_source_sha256,
        market_as_of_date=None if market is None else market.as_of_date,
        market_published_at=None if market is None else market.published_at,
        market_eligible_from_session=market_eligible,
        market_free_float_shares=None if market is None else market.free_float_shares,
        market_free_float_pct=None if market is None else market.free_float_pct,
        validation_published_at=validation_published_at,
        share_delta_lbre_minus_market=share_delta,
        percentage_delta_pp_lbre_minus_market=pct_delta,
    )


def resolve_statutory_free_float_state(
    ticker: str,
    session_date: date | datetime,
    official_sessions: Iterable[date | datetime],
    observations: Iterable[HistoricalFreeFloatObservation],
    *,
    percentage_tolerance: float = DEFAULT_PERCENTAGE_TOLERANCE,
) -> StatutoryFreeFloatKnowledgeState:
    """Resolve the official knowledge state for one ticker and session.

    Only observations eligible by ``session_date`` participate. Economic
    position selection is then the maximum available ``as_of_date``; this is
    what prevents a late correction to an older position from regressing a
    newer state.
    """

    if isinstance(session_date, datetime):
        if session_date.tzinfo is None or session_date.utcoffset() is None:
            raise ValueError("session datetime must be timezone-aware")
        query_date = session_date.astimezone(JAKARTA).date()
    elif isinstance(session_date, date):
        query_date = session_date
    else:
        raise TypeError("session_date must be a date or datetime")

    if not isfinite(percentage_tolerance) or percentage_tolerance < 0:
        raise ValueError("percentage_tolerance must be finite and non-negative")

    sessions = normalize_official_sessions(official_sessions)
    if query_date not in sessions:
        raise ValueError("session_date must be an official session")

    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker is empty")
    materialized = tuple(observations)
    for observation in materialized:
        if observation.ticker != normalized_ticker:
            raise ValueError("all observations must match ticker")

    eligible = _eligible_observations(materialized, sessions, query_date)
    if not eligible:
        return _state_from_rows(
            ticker=normalized_ticker,
            session_date=query_date,
            sessions=sessions,
            lbre=None,
            market=None,
            percentage_tolerance=percentage_tolerance,
        )

    current_by_source = _pick_source_rows(eligible)
    current_rows = tuple(current_by_source.values())
    max_as_of = max(row.as_of_date for row in current_rows)
    selected = tuple(row for row in current_rows if row.as_of_date == max_as_of)
    lbre = next(
        (row for row in selected if row.source_family is FreeFloatSourceFamily.ISSUER_LBRE),
        None,
    )
    market = next(
        (row for row in selected if row.source_family is FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS),
        None,
    )
    return _state_from_rows(
        ticker=normalized_ticker,
        session_date=query_date,
        sessions=sessions,
        lbre=lbre,
        market=market,
        percentage_tolerance=percentage_tolerance,
    )


__all__ = [
    "DEFAULT_PERCENTAGE_TOLERANCE",
    "StatutoryFreeFloatKnowledgeState",
    "StatutoryFreeFloatKnowledgeStatus",
    "eligible_from_session",
    "normalize_official_sessions",
    "resolve_statutory_free_float_state",
]
