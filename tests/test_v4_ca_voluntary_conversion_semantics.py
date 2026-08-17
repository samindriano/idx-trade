from __future__ import annotations

import pandas as pd

from idx_trade.v4_ca_event_windows import RESOLVED, UNRESOLVED_EVENT, window_continuity
from idx_trade.v4_ca_voluntary_conversion_semantics import (
    POLICY_ID,
    classify_event,
    is_exact_security_to_currency_voluntary_conversion,
)


def sessions() -> list[pd.Timestamp]:
    return [
        pd.Timestamp("2026-04-13"),
        pd.Timestamp("2026-04-14"),
        pd.Timestamp("2026-04-15"),
        pd.Timestamp("2026-04-16"),
        pd.Timestamp("2026-04-17"),
        pd.Timestamp("2026-04-20"),
        pd.Timestamp("2026-04-21"),
        pd.Timestamp("2026-04-22"),
    ]


def row(**updates):
    base = {
        "ticker": "TEST",
        "row_index": 1,
        "event_family_source": "Voluntary Conversion",
        "cum_date": None,
        "record_date": None,
        "distribution_date": "2026-04-17",
        "status": "Active",
        "ratio_raw": "(1 TEST : 63 IDR)",
        "ratio_parse_status": "PARSED_SOURCE_TEXT_ONLY",
        "ratio_left_value": "1",
        "ratio_left_security": "TEST",
        "ratio_right_value": "63",
        "ratio_right_security": "IDR",
        "source_sha256": "a" * 64,
    }
    base.update(updates)
    return base


def test_policy_identity_is_explicit():
    assert POLICY_ID == "V4_CA_VOLUNTARY_CONVERSION_SEMANTICS_REMEDIATION_V1"


def test_active_exact_security_to_currency_is_non_blocking():
    source = row()
    assert is_exact_security_to_currency_voluntary_conversion(source)
    event = classify_event(source, official_sessions=sessions())
    assert event.semantic_class == "NON_BLOCKING"
    assert event.family == "VOLUNTARY_CASH_SETTLEMENT"
    assert event.transition_date is None
    assert event.transition_source is None

    result = window_continuity(
        coverage_certified=True,
        cross_source_conflict=False,
        events=[event],
        entry_date="2026-04-13",
        terminal_date="2026-04-20",
    )
    assert result.status == RESOLVED


def test_security_to_security_voluntary_conversion_remains_fail_closed():
    source = row(
        ratio_raw="(1 TEST : 2 NEXT)",
        ratio_right_value="2",
        ratio_right_security="NEXT",
    )
    assert not is_exact_security_to_currency_voluntary_conversion(source)
    event = classify_event(source, official_sessions=sessions())
    assert event.semantic_class == "SCHEDULE_REQUIRED"

    result = window_continuity(
        coverage_certified=True,
        cross_source_conflict=False,
        events=[event],
        entry_date="2026-04-13",
        terminal_date="2026-04-14",
    )
    assert result.status == UNRESOLVED_EVENT


def test_unparsed_ratio_remains_fail_closed_even_if_currency_text_is_present():
    source = row(ratio_parse_status="UNRESOLVED_SOURCE_TEXT")
    assert not is_exact_security_to_currency_voluntary_conversion(source)
    event = classify_event(source, official_sessions=sessions())
    assert event.semantic_class == "SCHEDULE_REQUIRED"


def test_left_security_identity_mismatch_remains_fail_closed():
    source = row(ratio_left_security="OTHER")
    assert not is_exact_security_to_currency_voluntary_conversion(source)
    event = classify_event(source, official_sessions=sessions())
    assert event.semantic_class == "SCHEDULE_REQUIRED"


def test_unknown_right_token_remains_fail_closed():
    source = row(ratio_right_security="CASH")
    assert not is_exact_security_to_currency_voluntary_conversion(source)
    event = classify_event(source, official_sessions=sessions())
    assert event.semantic_class == "SCHEDULE_REQUIRED"


def test_mandatory_conversion_is_unchanged_and_still_requires_schedule():
    source = row(
        event_family_source="Mandatory Conversion",
        ratio_raw="(1 TEST : .052401 NEXT)",
        ratio_right_value=".052401",
        ratio_right_security="NEXT",
    )
    event = classify_event(source, official_sessions=sessions())
    assert event.semantic_class == "SCHEDULE_REQUIRED"


def test_cancelled_voluntary_conversion_uses_parent_non_blocking_semantics():
    source = row(status="Cancelled")
    assert not is_exact_security_to_currency_voluntary_conversion(source)
    event = classify_event(source, official_sessions=sessions())
    assert event.semantic_class == "NON_BLOCKING"
    assert event.family == "CANCELLED_OR_INACTIVE"
