"""Strict semantics for the seven-event V4 CA targeted evidence lane.

The lane is intentionally narrow. Six selected mechanical events can be
resolved only by the already accepted official-KSEI schedule transition path.
The selected NISP Voluntary Conversion may additionally be classified as
non-blocking when a freshly captured official KSEI registered-security row
strictly proves a security-to-currency conversion for the exact historical
source date.

This is ex-post price-basis continuity evidence. It is not a decision-time
feature and it never uses price behavior, Record/Distribution as a transition,
or a generic ticker-wide exemption.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from idx_trade.v4_ca_event_windows import EventSemantic, event_identity, source_dates
from idx_trade.v4_ca_residual_document_semantics import (
    classify_event_with_residual_document_evidence,
)
from idx_trade.v4_ksei_ca_history import row_dates


NISP_EVENT_ID = "10e24d3621e0f5e65833655b2e11938fc53d64e68c03e6c87658eb74bb2ae26b"
NISP_TICKER = "NISP"
CURRENCY_TOKENS = {
    "IDR", "USD", "SGD", "EUR", "JPY", "AUD", "GBP", "CNY", "HKD"
}
STATIC_LINKAGE_STATUS = "EXACT_NON_BLOCKING_STATIC_SECURITY_TO_CURRENCY"
STATIC_EVIDENCE_KIND = "VOLUNTARY_CASH_STATIC_SECURITY_TO_CURRENCY"


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _ticker(value: Any) -> str:
    return _text(value).upper().replace(".JK", "")


def selected_source_dates(event_row: Mapping[str, Any]) -> set[str]:
    raw = _text(event_row.get("source_dates"))
    if raw:
        return {token.strip() for token in raw.split("|") if token.strip()}
    return {value.date().isoformat() for value in source_dates(event_row)}


def resolve_nisp_static_cash_evidence(
    selected_event: Mapping[str, Any],
    parsed_history_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind exactly one current official KSEI static row to the frozen NISP event.

    The static row must itself expose a parseable security-to-currency ratio.
    Record/Distribution are used only to establish exact event identity against
    the frozen historical source-date set; they are not interpreted as a market
    basis transition.
    """

    event_id = _text(selected_event.get("event_id"))
    ticker = _ticker(selected_event.get("ticker"))
    source_type = _text(selected_event.get("source_type"))
    source_date_set = selected_source_dates(selected_event)
    if event_id != NISP_EVENT_ID or ticker != NISP_TICKER:
        raise RuntimeError("NISP_STATIC_EVIDENCE_WRONG_SELECTED_EVENT")
    if source_type.casefold() != "voluntary conversion":
        raise RuntimeError("NISP_STATIC_EVIDENCE_WRONG_SOURCE_TYPE")
    if source_date_set != {"2024-09-06"}:
        raise RuntimeError("NISP_STATIC_EVIDENCE_SOURCE_DATE_IDENTITY_CHANGED")

    candidates: list[Mapping[str, Any]] = []
    for row in parsed_history_rows:
        if _ticker(row.get("ticker")) != NISP_TICKER:
            continue
        if _text(row.get("event_family_source")).casefold() != "voluntary conversion":
            continue
        if _text(row.get("status")).casefold() != "active":
            continue
        if _text(row.get("ratio_parse_status")) != "PARSED_SOURCE_TEXT_ONLY":
            continue
        if _ticker(row.get("ratio_left_security")) != NISP_TICKER:
            continue
        right = _text(row.get("ratio_right_security")).upper()
        if right not in CURRENCY_TOKENS:
            continue
        if not (source_date_set & set(row_dates(dict(row)))):
            continue
        if not _text(row.get("source_url")) or not _text(row.get("source_sha256")):
            continue
        candidates.append(row)

    if len(candidates) != 1:
        return {
            "event_id": event_id,
            "ticker": ticker,
            "event_source_type": source_type,
            "linkage_status": "UNRESOLVED",
            "evidence_kind": STATIC_EVIDENCE_KIND,
            "transition_semantic": "",
            "transition_date": "",
            "ksei_reference": "STATIC_REGISTERED_SECURITY_PAGE",
            "document_date": "",
            "source_url": "",
            "source_sha256": "",
            "linkage_basis": "NISP_STATIC_SECURITY_TO_CURRENCY_EXACT_CANDIDATE_COUNT_NOT_ONE",
            "ratio_raw": "",
            "ratio_left_security": "",
            "ratio_right_security": "",
            "identity_date": "2024-09-06",
            "diagnostics": f"EXACT_CANDIDATE_COUNT:{len(candidates)}",
        }

    row = candidates[0]
    return {
        "event_id": event_id,
        "ticker": ticker,
        "event_source_type": source_type,
        "linkage_status": STATIC_LINKAGE_STATUS,
        "evidence_kind": STATIC_EVIDENCE_KIND,
        "transition_semantic": "",
        "transition_date": "",
        # The static page has no schedule reference number. This literal is a
        # source-class marker, not an invented KSEI document reference.
        "ksei_reference": "STATIC_REGISTERED_SECURITY_PAGE",
        "document_date": "",
        "source_url": _text(row.get("source_url")),
        "source_sha256": _text(row.get("source_sha256")),
        "linkage_basis": "EXACT_TICKER_VOLUNTARY_CONVERSION_SECURITY_TO_CURRENCY_AND_SOURCE_DATE_OVERLAP",
        "ratio_raw": _text(row.get("ratio_raw")),
        "ratio_left_security": _ticker(row.get("ratio_left_security")),
        "ratio_right_security": _text(row.get("ratio_right_security")).upper(),
        "identity_date": "2024-09-06",
        "diagnostics": "",
    }


def _static_rows_for_event(
    event_id: str,
    evidence_rows: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    matches: list[Mapping[str, Any]] = []
    for row in evidence_rows:
        if _text(row.get("event_id")) != event_id:
            continue
        if _text(row.get("linkage_status")) != STATIC_LINKAGE_STATUS:
            continue
        if _text(row.get("evidence_kind")) != STATIC_EVIDENCE_KIND:
            continue
        if _ticker(row.get("ticker")) != NISP_TICKER:
            continue
        if _ticker(row.get("ratio_left_security")) != NISP_TICKER:
            continue
        if _text(row.get("ratio_right_security")).upper() not in CURRENCY_TOKENS:
            continue
        if _text(row.get("identity_date")) != "2024-09-06":
            continue
        if not _text(row.get("source_url")) or not _text(row.get("source_sha256")):
            continue
        matches.append(row)
    return matches


def classify_event_with_targeted_evidence(
    row: Mapping[str, Any],
    *,
    official_sessions: Iterable[Any],
    schedule_evidence: Iterable[Mapping[str, Any]] = (),
) -> EventSemantic:
    """Apply targeted evidence on top of all previously accepted CA semantics."""

    evidence_rows = list(schedule_evidence)
    base = classify_event_with_residual_document_evidence(
        row,
        official_sessions=official_sessions,
        schedule_evidence=evidence_rows,
    )
    event_id = event_identity(row)
    if event_id != NISP_EVENT_ID:
        return base

    static_rows = _static_rows_for_event(event_id, evidence_rows)
    if not static_rows:
        return base
    if len(static_rows) != 1:
        return EventSemantic(
            event_id=base.event_id,
            ticker=base.ticker,
            source_type=base.source_type,
            family=base.family,
            semantic_class="SCHEDULE_REQUIRED",
            transition_date=None,
            transition_source=None,
            reason="TARGETED_STATIC_CASH_EVIDENCE_CONFLICT_FAIL_CLOSED",
            source_dates=base.source_dates,
        )
    if base.ticker != NISP_TICKER or base.source_type.casefold() != "voluntary conversion":
        return base
    if {value.date().isoformat() for value in base.source_dates} != {"2024-09-06"}:
        return base
    if base.semantic_class == "EXACT_TRANSITION":
        return EventSemantic(
            event_id=base.event_id,
            ticker=base.ticker,
            source_type=base.source_type,
            family=base.family,
            semantic_class="SCHEDULE_REQUIRED",
            transition_date=None,
            transition_source=None,
            reason="TARGETED_STATIC_CASH_AND_TRANSITION_CONFLICT_FAIL_CLOSED",
            source_dates=base.source_dates,
        )
    return EventSemantic(
        event_id=base.event_id,
        ticker=base.ticker,
        source_type=base.source_type,
        family="VOLUNTARY_CASH_STATIC_SECURITY_TO_CURRENCY",
        semantic_class="NON_BLOCKING",
        transition_date=None,
        transition_source=None,
        reason="EXACT_OFFICIAL_KSEI_STATIC_SECURITY_TO_CURRENCY_NOT_PRICE_BASIS_REBASE",
        source_dates=base.source_dates,
    )
