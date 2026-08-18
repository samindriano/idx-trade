"""Outcome-blind replay helpers for adjudicated V4-3 CA schedule evidence.

The helpers consume an already-built parent event audit and an immutable
schedule-80 adjudication result.  Only exact event_id+ticker identities may be
changed.  Unresolved events remain fail-closed, while exact transitions retain
normal event-window crossing semantics.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

import pandas as pd

from idx_trade.v4_ca_event_windows import (
    ACCEPTED_SCHEDULE_SEMANTICS,
    EventSemantic,
    window_continuity,
)


EXACT = "EXACT"
EXACT_NON_BLOCKING = "EXACT_NON_BLOCKING"
UNRESOLVED = "UNRESOLVED"
CONFLICT = "CONFLICT"


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def ticker(value: object) -> str:
    return clean(value).upper().replace(".JK", "")


def timestamp(value: object) -> pd.Timestamp | None:
    text = clean(value)
    if text in {"", "-", "None", "nan", "NaT"}:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    result = pd.Timestamp(parsed)
    if result.tz is not None:
        result = result.tz_localize(None)
    return result.normalize()


def source_date_tuple(value: object) -> tuple[pd.Timestamp, ...]:
    dates: set[pd.Timestamp] = set()
    for token in clean(value).split("|"):
        parsed = timestamp(token)
        if parsed is not None:
            dates.add(parsed)
    return tuple(sorted(dates))


def event_from_audit_row(row: dict[str, Any]) -> EventSemantic:
    event_id = clean(row.get("event_id"))
    event_ticker = ticker(row.get("ticker"))
    semantic_class = clean(row.get("semantic_class"))
    if not event_id or not event_ticker or not semantic_class:
        raise RuntimeError("PARENT_EVENT_AUDIT_IDENTITY_INCOMPLETE")
    transition = timestamp(row.get("transition_date"))
    if semantic_class == "EXACT_TRANSITION" and transition is None:
        raise RuntimeError(f"PARENT_EXACT_TRANSITION_DATE_MISSING:{event_id}:{event_ticker}")
    if semantic_class != "EXACT_TRANSITION":
        transition = None
    return EventSemantic(
        event_id=event_id,
        ticker=event_ticker,
        source_type=clean(row.get("source_type")),
        family=clean(row.get("family")),
        semantic_class=semantic_class,
        transition_date=transition,
        transition_source=clean(row.get("transition_source")) or None,
        reason=clean(row.get("reason")),
        source_dates=source_date_tuple(row.get("source_dates")),
    )


def build_parent_events(audit: pd.DataFrame) -> dict[tuple[str, str], EventSemantic]:
    required = {
        "event_id",
        "ticker",
        "source_type",
        "family",
        "semantic_class",
        "transition_date",
        "transition_source",
        "reason",
        "source_dates",
    }
    missing = required - set(audit.columns)
    if missing:
        raise RuntimeError(f"PARENT_EVENT_AUDIT_COLUMNS_MISSING:{sorted(missing)}")
    result: dict[tuple[str, str], EventSemantic] = {}
    for row in audit.to_dict("records"):
        event = event_from_audit_row(row)
        key = (event.event_id, event.ticker)
        if key in result:
            raise RuntimeError(f"PARENT_EVENT_IDENTITY_DUPLICATED:{event.event_id}:{event.ticker}")
        result[key] = event
    return result


def apply_adjudication(
    parent_events: dict[tuple[str, str], EventSemantic],
    evidence: pd.DataFrame,
    *,
    expected_schedule_events: int = 80,
) -> tuple[dict[tuple[str, str], EventSemantic], pd.DataFrame]:
    required = {
        "event_id",
        "ticker",
        "event_source_type",
        "linkage_status",
        "evidence_kind",
        "transition_date",
        "transition_semantic",
        "ksei_reference",
        "source_sha256",
        "linkage_basis",
    }
    missing = required - set(evidence.columns)
    if missing:
        raise RuntimeError(f"ADJUDICATION_EVIDENCE_COLUMNS_MISSING:{sorted(missing)}")
    if len(evidence) != expected_schedule_events:
        raise RuntimeError(f"ADJUDICATION_EVENT_COUNT_CHANGED:{len(evidence)}!={expected_schedule_events}")

    work = evidence.copy()
    work["event_id"] = work["event_id"].map(clean)
    work["ticker"] = work["ticker"].map(ticker)
    if work[["event_id", "ticker"]].eq("").any().any():
        raise RuntimeError("ADJUDICATION_EVENT_IDENTITY_EMPTY")
    if work.duplicated(["event_id", "ticker"]).any():
        raise RuntimeError("ADJUDICATION_EVENT_IDENTITY_DUPLICATED")

    updated = dict(parent_events)
    overlay_rows: list[dict[str, Any]] = []
    for row in work.to_dict("records"):
        key = (clean(row["event_id"]), ticker(row["ticker"]))
        parent = parent_events.get(key)
        if parent is None:
            raise RuntimeError(f"ADJUDICATION_EVENT_NOT_IN_PARENT:{key[0]}:{key[1]}")
        if parent.semantic_class != "SCHEDULE_REQUIRED":
            raise RuntimeError(
                f"ADJUDICATION_PARENT_NOT_SCHEDULE_REQUIRED:{key[0]}:{key[1]}:{parent.semantic_class}"
            )
        if clean(row.get("event_source_type")).casefold() != parent.source_type.casefold():
            raise RuntimeError(f"ADJUDICATION_SOURCE_TYPE_CHANGED:{key[0]}:{key[1]}")

        status = clean(row.get("linkage_status"))
        new_event = parent
        action = "KEEP_UNRESOLVED"
        if status == EXACT:
            transition = timestamp(row.get("transition_date"))
            semantic = clean(row.get("transition_semantic"))
            if transition is None or semantic not in ACCEPTED_SCHEDULE_SEMANTICS:
                raise RuntimeError(f"ADJUDICATION_EXACT_TRANSITION_INVALID:{key[0]}:{key[1]}")
            if not clean(row.get("ksei_reference")) or not clean(row.get("source_sha256")):
                raise RuntimeError(f"ADJUDICATION_EXACT_PROVENANCE_MISSING:{key[0]}:{key[1]}")
            new_event = EventSemantic(
                event_id=parent.event_id,
                ticker=parent.ticker,
                source_type=parent.source_type,
                family=parent.family,
                semantic_class="EXACT_TRANSITION",
                transition_date=transition,
                transition_source="OFFICIAL_KSEI_SCHEDULE_80_ADJUDICATION_V1",
                reason="EXACT_OFFICIAL_KSEI_SCHEDULE_80_TRANSITION",
                source_dates=parent.source_dates,
            )
            action = "ADMIT_EXACT_TRANSITION"
        elif status == EXACT_NON_BLOCKING:
            if parent.source_type.casefold() != "voluntary conversion":
                raise RuntimeError(f"ADJUDICATION_NONBLOCKING_NOT_VOLUNTARY:{key[0]}:{key[1]}")
            if not clean(row.get("ksei_reference")) or not clean(row.get("source_sha256")):
                raise RuntimeError(f"ADJUDICATION_NONBLOCKING_PROVENANCE_MISSING:{key[0]}:{key[1]}")
            new_event = EventSemantic(
                event_id=parent.event_id,
                ticker=parent.ticker,
                source_type=parent.source_type,
                family="VOLUNTARY_CASH_DOCUMENT_SETTLEMENT",
                semantic_class="NON_BLOCKING",
                transition_date=None,
                transition_source=None,
                reason="EXACT_OFFICIAL_KSEI_CASH_DOCUMENT_NOT_MARKET_WIDE_PRICE_BASIS_REBASE",
                source_dates=parent.source_dates,
            )
            action = "ADMIT_EXACT_NON_BLOCKING"
        elif status == UNRESOLVED:
            pass
        elif status == CONFLICT:
            raise RuntimeError(f"ADJUDICATION_CONFLICT_FAIL_CLOSED:{key[0]}:{key[1]}")
        else:
            raise RuntimeError(f"ADJUDICATION_LINKAGE_STATUS_UNKNOWN:{key[0]}:{key[1]}:{status}")

        updated[key] = new_event
        overlay_rows.append(
            {
                "event_id": parent.event_id,
                "ticker": parent.ticker,
                "parent_semantic_class": parent.semantic_class,
                "adjudication_linkage_status": status,
                "replay_action": action,
                "replayed_semantic_class": new_event.semantic_class,
                "replayed_transition_date": (
                    new_event.transition_date.date().isoformat()
                    if new_event.transition_date is not None
                    else ""
                ),
                "replayed_transition_source": new_event.transition_source or "",
                "ksei_reference": clean(row.get("ksei_reference")),
                "source_sha256": clean(row.get("source_sha256")),
                "linkage_basis": clean(row.get("linkage_basis")),
            }
        )

    overlay = pd.DataFrame(overlay_rows).sort_values(
        ["ticker", "event_id"], kind="mergesort"
    ).reset_index(drop=True)
    return updated, overlay


def events_by_ticker(events: Iterable[EventSemantic]) -> dict[str, list[EventSemantic]]:
    result: dict[str, list[EventSemantic]] = {}
    for event in events:
        result.setdefault(event.ticker, []).append(event)
    for value in result.values():
        value.sort(key=lambda event: (event.event_id, event.semantic_class))
    return result


def replay_continuity(
    windows: pd.DataFrame,
    events: dict[tuple[str, str], EventSemantic],
    *,
    unresolved_coverage_tickers: set[str],
    missing_coverage_tickers: set[str],
    cross_source_conflict_tickers: set[str],
) -> pd.DataFrame:
    required = {
        "ticker",
        "signal_date",
        "signal_session_index",
        "horizon",
        "entry_date",
        "terminal_date",
    }
    missing = required - set(windows.columns)
    if missing:
        raise RuntimeError(f"PARENT_CONTINUITY_WINDOW_COLUMNS_MISSING:{sorted(missing)}")
    grouped = events_by_ticker(events.values())
    rows: list[dict[str, Any]] = []
    for row in windows.itertuples(index=False):
        row_ticker = ticker(row.ticker)
        coverage_certified = (
            row_ticker not in unresolved_coverage_tickers
            and row_ticker not in missing_coverage_tickers
        )
        result = window_continuity(
            coverage_certified=coverage_certified,
            cross_source_conflict=row_ticker in cross_source_conflict_tickers,
            events=grouped.get(row_ticker, []),
            entry_date=row.entry_date,
            terminal_date=row.terminal_date,
        )
        rows.append(
            {
                "ticker": row_ticker,
                "signal_date": pd.Timestamp(row.signal_date).normalize(),
                "signal_session_index": int(row.signal_session_index),
                "horizon": int(row.horizon),
                "entry_date": pd.Timestamp(row.entry_date).normalize(),
                "terminal_date": pd.Timestamp(row.terminal_date).normalize(),
                "continuity_status": result.status,
                "continuity_reason": result.reason,
                "blocking_event_ids": "|".join(result.blocking_event_ids),
                "blocking_transition_dates": "|".join(result.blocking_transition_dates),
                "policy_id": "V4_CA_EVENT_WINDOW_SEMANTICS_V1",
            }
        )
    frame = pd.DataFrame(rows)
    if frame.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise RuntimeError("REPLAY_CONTINUITY_IDENTITY_DUPLICATED")
    return frame.sort_values(
        ["signal_session_index", "ticker", "horizon"], kind="mergesort"
    ).reset_index(drop=True)


def event_audit_frame(events: dict[tuple[str, str], EventSemantic]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for event in events.values():
        value = asdict(event)
        rows.append(
            {
                **{key: field for key, field in value.items() if key not in {"transition_date", "source_dates"}},
                "transition_date": (
                    event.transition_date.date().isoformat()
                    if event.transition_date is not None
                    else ""
                ),
                "source_dates": "|".join(value.date().isoformat() for value in event.source_dates),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["ticker", "source_dates", "source_type", "event_id"], kind="mergesort"
    ).reset_index(drop=True)
