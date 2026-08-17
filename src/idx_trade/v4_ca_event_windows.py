"""Outcome-blind V4 corporate-action event-window semantics.

This module narrows price-basis continuity from ticker-period quarantine to the
actual target interval.  It never infers a transition from prices.  A market
basis transition is admitted only from either:

1. a source-native KSEI Cum Date for an entitlement family whose regular-market
   Ex Date is the next official exchange session; or
2. exact official KSEI schedule evidence naming the regular-market Ex Date or
   first trading date on the new basis.

Everything else fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

import pandas as pd


RESOLVED = "RESOLVED_NO_MECHANICAL_DISCONTINUITY"
UNRESOLVED_COVERAGE = "PRICE_CONTINUITY_UNRESOLVED_COVERAGE"
UNRESOLVED_EVENT = "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE"

STATIC_CUM_EXACT_TYPES = {
    "right distribution",
    "stock dividend",
    "share bonus",
    "bonus shares",
    "bonus share",
    "bonus distribution",
}
NON_BLOCKING_TYPES = {"cash dividend", "proxy voting"}
SCHEDULE_REQUIRED_TYPES = {
    "mandatory conversion",
    "voluntary conversion",
    "stock split",
    "reverse stock",
    "reverse stock split",
    "reverse split",
    "merger",
    "capital restructuring",
    "capital reduction",
}
CURRENCY_TOKENS = {
    "IDR",
    "USD",
    "SGD",
    "EUR",
    "JPY",
    "AUD",
    "GBP",
    "CNY",
    "HKD",
}
ACCEPTED_SCHEDULE_SEMANTICS = {
    "REGULAR_MARKET_EX_DATE",
    "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
}


@dataclass(frozen=True)
class EventSemantic:
    event_id: str
    ticker: str
    source_type: str
    family: str
    semantic_class: str
    transition_date: pd.Timestamp | None
    transition_source: str | None
    reason: str
    source_dates: tuple[pd.Timestamp, ...]


@dataclass(frozen=True)
class WindowContinuity:
    status: str
    reason: str
    blocking_event_ids: tuple[str, ...]
    blocking_transition_dates: tuple[str, ...]


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _ticker(value: Any) -> str:
    return _text(value).upper().replace(".JK", "")


def _timestamp(value: Any) -> pd.Timestamp | None:
    if value is None or _text(value) in {"", "-", "NaT", "None", "nan"}:
        return None
    candidate = pd.to_datetime(value, errors="coerce")
    if pd.isna(candidate):
        return None
    result = pd.Timestamp(candidate)
    if result.tz is not None:
        result = result.tz_localize(None)
    return result.normalize()


def source_dates(row: Mapping[str, Any]) -> tuple[pd.Timestamp, ...]:
    result: list[pd.Timestamp] = []
    for key in ("cum_date", "record_date", "distribution_date"):
        value = _timestamp(row.get(key))
        if value is not None:
            result.append(value)
    return tuple(sorted(set(result)))


def event_identity(row: Mapping[str, Any]) -> str:
    """Stable identity over immutable KSEI-history row semantics."""

    payload = {
        "ticker": _ticker(row.get("ticker")),
        "row_index": int(row.get("row_index") or 0),
        "event_family_source": _text(row.get("event_family_source")),
        "cum_date": _text(row.get("cum_date")),
        "record_date": _text(row.get("record_date")),
        "distribution_date": _text(row.get("distribution_date")),
        "status": _text(row.get("status")),
        "ratio_raw": _text(row.get("ratio_raw")),
        "source_sha256": _text(row.get("source_sha256")),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def is_active(row: Mapping[str, Any]) -> bool:
    return _text(row.get("status")).casefold() == "active"


def _ratio_right_security(row: Mapping[str, Any]) -> str:
    return _text(row.get("ratio_right_security")).upper()


def _mixed_dividend_class(row: Mapping[str, Any]) -> tuple[str, str]:
    """Decompose KSEI Mixed Dividend using source-native ratio denomination."""

    ticker = _ticker(row.get("ticker"))
    right = _ratio_right_security(row)
    if right == ticker:
        return "MIXED_STOCK_DIVIDEND", "STATIC_CUM_IF_AVAILABLE"
    if right in CURRENCY_TOKENS:
        return "MIXED_CASH_DIVIDEND", "NON_BLOCKING"
    return "MIXED_DIVIDEND_UNKNOWN", "SCHEDULE_REQUIRED"


def next_official_session(
    cum_date: pd.Timestamp,
    official_sessions: Iterable[Any],
) -> pd.Timestamp | None:
    sessions = sorted(
        {
            value
            for raw in official_sessions
            if (value := _timestamp(raw)) is not None
        }
    )
    if cum_date not in set(sessions):
        return None
    for session in sessions:
        if session > cum_date:
            return session
    return None


def _schedule_rows_for_event(
    event_id: str,
    schedule_evidence: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for row in schedule_evidence:
        if _text(row.get("event_id")) != event_id:
            continue
        if _text(row.get("linkage_status")) != "EXACT":
            continue
        if _text(row.get("transition_semantic")) not in ACCEPTED_SCHEDULE_SEMANTICS:
            continue
        transition = _timestamp(row.get("transition_date"))
        if transition is None:
            continue
        if not _text(row.get("ksei_reference")):
            continue
        if not _text(row.get("source_sha256")):
            continue
        rows.append(row)
    return rows


def exact_schedule_transition(
    event_id: str,
    schedule_evidence: Iterable[Mapping[str, Any]],
) -> tuple[pd.Timestamp | None, str]:
    rows = _schedule_rows_for_event(event_id, schedule_evidence)
    if not rows:
        return None, "NO_EXACT_OFFICIAL_SCHEDULE_TRANSITION"
    dates = {
        value
        for row in rows
        if (value := _timestamp(row.get("transition_date"))) is not None
    }
    if len(dates) != 1:
        return None, "CONFLICTING_EXACT_OFFICIAL_SCHEDULE_TRANSITIONS"
    return next(iter(dates)), "OFFICIAL_KSEI_SCHEDULE"


def classify_event(
    row: Mapping[str, Any],
    *,
    official_sessions: Iterable[Any],
    schedule_evidence: Iterable[Mapping[str, Any]] = (),
) -> EventSemantic:
    event_id = event_identity(row)
    ticker = _ticker(row.get("ticker"))
    source_type = _text(row.get("event_family_source"))
    source_key = source_type.casefold()
    dates = source_dates(row)

    if not is_active(row):
        return EventSemantic(
            event_id,
            ticker,
            source_type,
            "CANCELLED_OR_INACTIVE",
            "NON_BLOCKING",
            None,
            None,
            "KSEI_EVENT_NOT_ACTIVE",
            dates,
        )

    if source_key in NON_BLOCKING_TYPES:
        return EventSemantic(
            event_id,
            ticker,
            source_type,
            source_type.upper().replace(" ", "_"),
            "NON_BLOCKING",
            None,
            None,
            "NON_MECHANICAL_FOR_V4_PRICE_RETURN_CONTINUITY",
            dates,
        )

    if source_key == "mixed dividend":
        family, policy = _mixed_dividend_class(row)
        if policy == "NON_BLOCKING":
            return EventSemantic(
                event_id,
                ticker,
                source_type,
                family,
                "NON_BLOCKING",
                None,
                None,
                "MIXED_DIVIDEND_CASH_COMPONENT",
                dates,
            )
        if policy == "STATIC_CUM_IF_AVAILABLE":
            cum = _timestamp(row.get("cum_date"))
            if cum is not None:
                transition = next_official_session(cum, official_sessions)
                if transition is not None:
                    return EventSemantic(
                        event_id,
                        ticker,
                        source_type,
                        family,
                        "EXACT_TRANSITION",
                        transition,
                        "KSEI_STATIC_CUM_NEXT_OFFICIAL_SESSION",
                        "MIXED_STOCK_COMPONENT_REGULAR_MARKET_EX_BOUNDARY",
                        dates,
                    )
        transition, transition_source = exact_schedule_transition(
            event_id, schedule_evidence
        )
        if transition is not None:
            return EventSemantic(
                event_id,
                ticker,
                source_type,
                family,
                "EXACT_TRANSITION",
                transition,
                transition_source,
                "EXACT_OFFICIAL_SCHEDULE_TRANSITION",
                dates,
            )
        return EventSemantic(
            event_id,
            ticker,
            source_type,
            family,
            "SCHEDULE_REQUIRED",
            None,
            None,
            "MIXED_STOCK_OR_UNKNOWN_COMPONENT_NEEDS_EXACT_SCHEDULE",
            dates,
        )

    if source_key in STATIC_CUM_EXACT_TYPES:
        cum = _timestamp(row.get("cum_date"))
        if cum is not None:
            transition = next_official_session(cum, official_sessions)
            if transition is not None:
                return EventSemantic(
                    event_id,
                    ticker,
                    source_type,
                    source_type.upper().replace(" ", "_"),
                    "EXACT_TRANSITION",
                    transition,
                    "KSEI_STATIC_CUM_NEXT_OFFICIAL_SESSION",
                    "REGULAR_MARKET_EX_BOUNDARY_FROM_SOURCE_NATIVE_CUM",
                    dates,
                )
        transition, transition_source = exact_schedule_transition(
            event_id, schedule_evidence
        )
        if transition is not None:
            return EventSemantic(
                event_id,
                ticker,
                source_type,
                source_type.upper().replace(" ", "_"),
                "EXACT_TRANSITION",
                transition,
                transition_source,
                "EXACT_OFFICIAL_SCHEDULE_TRANSITION",
                dates,
            )
        return EventSemantic(
            event_id,
            ticker,
            source_type,
            source_type.upper().replace(" ", "_"),
            "SCHEDULE_REQUIRED",
            None,
            None,
            "SOURCE_NATIVE_CUM_MISSING_OR_NOT_OFFICIAL_SESSION",
            dates,
        )

    # Mandatory/voluntary conversions, split/reverse/merger labels, and all
    # unrecognized active source types require an explicit KSEI schedule.
    transition, transition_source = exact_schedule_transition(event_id, schedule_evidence)
    if transition is not None:
        return EventSemantic(
            event_id,
            ticker,
            source_type,
            source_type.upper().replace(" ", "_") or "UNKNOWN",
            "EXACT_TRANSITION",
            transition,
            transition_source,
            "EXACT_OFFICIAL_SCHEDULE_TRANSITION",
            dates,
        )

    family = (
        source_type.upper().replace(" ", "_")
        if source_key in SCHEDULE_REQUIRED_TYPES
        else "UNKNOWN"
    )
    return EventSemantic(
        event_id,
        ticker,
        source_type,
        family,
        "SCHEDULE_REQUIRED",
        None,
        None,
        "ACTIVE_EVENT_REQUIRES_EXACT_OFFICIAL_SCHEDULE",
        dates,
    )


def event_relevant_to_study_period(
    event: EventSemantic,
    *,
    period_start: Any,
    period_end: Any,
    selection_halo_calendar_days: int = 60,
) -> bool:
    """Select events for evidence work without using the halo as a transition."""

    start = _timestamp(period_start)
    end = _timestamp(period_end)
    if start is None or end is None:
        raise ValueError("period bounds must be valid dates")
    start -= pd.Timedelta(days=selection_halo_calendar_days)
    end += pd.Timedelta(days=selection_halo_calendar_days)

    if event.semantic_class == "NON_BLOCKING":
        return False
    if event.transition_date is not None:
        return start <= event.transition_date <= end
    if not event.source_dates:
        return True
    return any(start <= value <= end for value in event.source_dates)


def window_continuity(
    *,
    coverage_certified: bool,
    cross_source_conflict: bool,
    events: Iterable[EventSemantic],
    entry_date: Any,
    terminal_date: Any,
) -> WindowContinuity:
    entry = _timestamp(entry_date)
    terminal = _timestamp(terminal_date)
    if entry is None or terminal is None or terminal < entry:
        raise ValueError("invalid target interval")

    if not coverage_certified:
        return WindowContinuity(
            UNRESOLVED_COVERAGE,
            "KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED",
            (),
            (),
        )
    if cross_source_conflict:
        return WindowContinuity(
            UNRESOLVED_COVERAGE,
            "CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY",
            (),
            (),
        )

    missing_schedule: list[str] = []
    crossing: list[EventSemantic] = []
    for event in events:
        if event.semantic_class == "NON_BLOCKING":
            continue
        if event.semantic_class == "SCHEDULE_REQUIRED":
            missing_schedule.append(event.event_id)
            continue
        if event.semantic_class != "EXACT_TRANSITION" or event.transition_date is None:
            missing_schedule.append(event.event_id)
            continue
        # Entry on the transition date already uses the post-event basis.
        if entry < event.transition_date <= terminal:
            crossing.append(event)

    if missing_schedule:
        return WindowContinuity(
            UNRESOLVED_EVENT,
            "EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED",
            tuple(sorted(set(missing_schedule))),
            (),
        )
    if crossing:
        return WindowContinuity(
            UNRESOLVED_EVENT,
            "TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION",
            tuple(sorted(event.event_id for event in crossing)),
            tuple(
                sorted(
                    {
                        event.transition_date.date().isoformat()
                        for event in crossing
                        if event.transition_date is not None
                    }
                )
            ),
        )
    return WindowContinuity(
        RESOLVED,
        "NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL",
        (),
        (),
    )
