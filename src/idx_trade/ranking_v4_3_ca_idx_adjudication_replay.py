"""Fail-closed replay overlay for frozen official IDX schedule-59 evidence.

This module never performs provider access or document discovery.  It applies
only exact event_id+ticker evidence rows that were already adjudicated by the
frozen IDX attachment parser.  Unresolved rows remain SCHEDULE_REQUIRED and
conflicts fail closed.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from idx_trade.v4_ca_event_windows import ACCEPTED_SCHEDULE_SEMANTICS, EventSemantic

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


def apply_idx_adjudication(
    parent_events: dict[tuple[str, str], EventSemantic],
    evidence: pd.DataFrame,
    *,
    expected_schedule_events: int = 59,
) -> tuple[dict[tuple[str, str], EventSemantic], pd.DataFrame]:
    required = {
        "event_id",
        "ticker",
        "event_source_type",
        "linkage_status",
        "transition_date",
        "transition_semantic",
        "official_reference",
        "source_sha256",
        "linkage_basis",
    }
    missing = required - set(evidence.columns)
    if missing:
        raise RuntimeError(f"IDX_ADJUDICATION_EVIDENCE_COLUMNS_MISSING:{sorted(missing)}")
    if len(evidence) != expected_schedule_events:
        raise RuntimeError(
            f"IDX_ADJUDICATION_EVENT_COUNT_CHANGED:{len(evidence)}!={expected_schedule_events}"
        )

    work = evidence.copy()
    work["event_id"] = work["event_id"].map(clean)
    work["ticker"] = work["ticker"].map(ticker)
    if work[["event_id", "ticker"]].eq("").any().any():
        raise RuntimeError("IDX_ADJUDICATION_EVENT_IDENTITY_EMPTY")
    if work.duplicated(["event_id", "ticker"]).any():
        raise RuntimeError("IDX_ADJUDICATION_EVENT_IDENTITY_DUPLICATED")

    updated = dict(parent_events)
    overlay_rows: list[dict[str, Any]] = []
    for row in work.to_dict("records"):
        key = (clean(row["event_id"]), ticker(row["ticker"]))
        parent = parent_events.get(key)
        if parent is None:
            raise RuntimeError(f"IDX_ADJUDICATION_EVENT_NOT_IN_PARENT:{key[0]}:{key[1]}")
        if parent.semantic_class != "SCHEDULE_REQUIRED":
            raise RuntimeError(
                f"IDX_ADJUDICATION_PARENT_NOT_SCHEDULE_REQUIRED:{key[0]}:{key[1]}:{parent.semantic_class}"
            )
        if clean(row.get("event_source_type")).casefold() != parent.source_type.casefold():
            raise RuntimeError(f"IDX_ADJUDICATION_SOURCE_TYPE_CHANGED:{key[0]}:{key[1]}")

        status = clean(row.get("linkage_status"))
        new_event = parent
        action = "KEEP_UNRESOLVED"
        if status == EXACT:
            transition = timestamp(row.get("transition_date"))
            semantic = clean(row.get("transition_semantic"))
            if transition is None or semantic not in ACCEPTED_SCHEDULE_SEMANTICS:
                raise RuntimeError(f"IDX_ADJUDICATION_EXACT_TRANSITION_INVALID:{key[0]}:{key[1]}")
            if not clean(row.get("official_reference")) or not clean(row.get("source_sha256")):
                raise RuntimeError(f"IDX_ADJUDICATION_EXACT_PROVENANCE_MISSING:{key[0]}:{key[1]}")
            new_event = EventSemantic(
                event_id=parent.event_id,
                ticker=parent.ticker,
                source_type=parent.source_type,
                family=parent.family,
                semantic_class="EXACT_TRANSITION",
                transition_date=transition,
                transition_source="OFFICIAL_IDX_ANNOUNCEMENT_ATTACHMENT_SCHEDULE59_ADJUDICATION_V1",
                reason="EXACT_OFFICIAL_IDX_ANNOUNCEMENT_TRANSITION",
                source_dates=parent.source_dates,
            )
            action = "ADMIT_EXACT_TRANSITION"
        elif status == EXACT_NON_BLOCKING:
            if parent.source_type.casefold() != "voluntary conversion":
                raise RuntimeError(
                    f"IDX_ADJUDICATION_NONBLOCKING_NOT_VOLUNTARY:{key[0]}:{key[1]}"
                )
            if not clean(row.get("official_reference")) or not clean(row.get("source_sha256")):
                raise RuntimeError(
                    f"IDX_ADJUDICATION_NONBLOCKING_PROVENANCE_MISSING:{key[0]}:{key[1]}"
                )
            new_event = EventSemantic(
                event_id=parent.event_id,
                ticker=parent.ticker,
                source_type=parent.source_type,
                family="VOLUNTARY_CASH_DOCUMENT_SETTLEMENT",
                semantic_class="NON_BLOCKING",
                transition_date=None,
                transition_source=None,
                reason="EXACT_OFFICIAL_IDX_CASH_DOCUMENT_NOT_MARKET_WIDE_PRICE_BASIS_REBASE",
                source_dates=parent.source_dates,
            )
            action = "ADMIT_EXACT_NON_BLOCKING"
        elif status == UNRESOLVED:
            pass
        elif status == CONFLICT:
            raise RuntimeError(f"IDX_ADJUDICATION_CONFLICT_FAIL_CLOSED:{key[0]}:{key[1]}")
        else:
            raise RuntimeError(
                f"IDX_ADJUDICATION_LINKAGE_STATUS_UNKNOWN:{key[0]}:{key[1]}:{status}"
            )

        updated[key] = new_event
        overlay_rows.append(
            {
                "event_id": parent.event_id,
                "ticker": parent.ticker,
                "parent_semantic_class": parent.semantic_class,
                "idx_linkage_status": status,
                "replay_action": action,
                "replayed_semantic_class": new_event.semantic_class,
                "replayed_transition_date": (
                    new_event.transition_date.date().isoformat()
                    if new_event.transition_date is not None
                    else ""
                ),
                "replayed_transition_source": new_event.transition_source or "",
                "official_reference": clean(row.get("official_reference")),
                "source_sha256": clean(row.get("source_sha256")),
                "linkage_basis": clean(row.get("linkage_basis")),
            }
        )

    overlay = pd.DataFrame(overlay_rows).sort_values(
        ["ticker", "event_id"], kind="mergesort"
    ).reset_index(drop=True)
    return updated, overlay
