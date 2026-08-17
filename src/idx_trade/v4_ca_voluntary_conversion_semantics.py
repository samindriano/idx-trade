"""Outcome-blind semantic remediation for KSEI Voluntary Conversion rows.

This module is intentionally narrow.  It does not modify the frozen V4 target,
execution, evaluation, or event-window crossing rules.  It only corrects the
price-basis interpretation of one KSEI source-native corporate-action label.

A Voluntary Conversion is treated as non-blocking for market-wide price-basis
continuity only when the immutable KSEI history row itself proves all of the
following:

1. the row is active;
2. the ratio parser succeeded on source text;
3. the left-hand security is exactly the requested ticker; and
4. the right-hand security is a recognized currency token.

That pattern is a security-to-cash voluntary settlement and is not an automatic
market-wide rebase of the listed share.  Every other Voluntary Conversion
remains fail-closed by delegating to the parent event-window classifier.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from idx_trade.v4_ca_event_windows import (
    CURRENCY_TOKENS,
    EventSemantic,
    classify_event as classify_event_parent,
)


POLICY_ID = "V4_CA_VOLUNTARY_CONVERSION_SEMANTICS_REMEDIATION_V1"


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _ticker(value: Any) -> str:
    return _text(value).upper().replace(".JK", "")


def is_exact_security_to_currency_voluntary_conversion(
    row: Mapping[str, Any],
) -> bool:
    """Return True only for exact source-parsed security -> currency rows."""

    if _text(row.get("event_family_source")).casefold() != "voluntary conversion":
        return False
    if _text(row.get("status")).casefold() != "active":
        return False
    if _text(row.get("ratio_parse_status")) != "PARSED_SOURCE_TEXT_ONLY":
        return False

    ticker = _ticker(row.get("ticker"))
    left = _text(row.get("ratio_left_security")).upper()
    right = _text(row.get("ratio_right_security")).upper()

    if not ticker or left != ticker:
        return False
    if right not in CURRENCY_TOKENS:
        return False
    return True


def classify_event(
    row: Mapping[str, Any],
    *,
    official_sessions: Iterable[Any],
    schedule_evidence: Iterable[Mapping[str, Any]] = (),
) -> EventSemantic:
    """Apply the narrow voluntary-cash remediation, else parent semantics."""

    parent = classify_event_parent(
        row,
        official_sessions=official_sessions,
        schedule_evidence=schedule_evidence,
    )

    if not is_exact_security_to_currency_voluntary_conversion(row):
        return parent

    return EventSemantic(
        event_id=parent.event_id,
        ticker=parent.ticker,
        source_type=parent.source_type,
        family="VOLUNTARY_CASH_SETTLEMENT",
        semantic_class="NON_BLOCKING",
        transition_date=None,
        transition_source=None,
        reason="VOLUNTARY_SECURITY_TO_CURRENCY_SETTLEMENT_NOT_AUTOMATIC_MARKET_PRICE_BASIS_REBASE",
        source_dates=parent.source_dates,
    )
