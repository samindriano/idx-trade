from __future__ import annotations

import pandas as pd

from idx_trade.v4_ca_event_windows import (
    RESOLVED,
    UNRESOLVED_EVENT,
    classify_event,
    event_identity,
    event_relevant_to_study_period,
    window_continuity,
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
        "event_family_source": "Right Distribution",
        "cum_date": "2026-04-16",
        "record_date": "2026-04-20",
        "distribution_date": "2026-04-21",
        "status": "Active",
        "ratio_raw": "(10 TEST : 1 TEST)",
        "ratio_right_security": "TEST",
        "source_sha256": "a" * 64,
    }
    base.update(updates)
    return base


def test_rights_static_cum_maps_to_next_official_regular_ex_boundary():
    event = classify_event(row(), official_sessions=sessions())
    assert event.semantic_class == "EXACT_TRANSITION"
    assert event.transition_date == pd.Timestamp("2026-04-17")
    assert event.transition_source == "KSEI_STATIC_CUM_NEXT_OFFICIAL_SESSION"


def test_crossing_rule_and_entry_on_transition_are_distinct():
    event = classify_event(row(), official_sessions=sessions())
    crossing = window_continuity(
        coverage_certified=True,
        cross_source_conflict=False,
        events=[event],
        entry_date="2026-04-16",
        terminal_date="2026-04-20",
    )
    assert crossing.status == UNRESOLVED_EVENT
    assert crossing.reason == "TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION"

    already_post = window_continuity(
        coverage_certified=True,
        cross_source_conflict=False,
        events=[event],
        entry_date="2026-04-17",
        terminal_date="2026-04-20",
    )
    assert already_post.status == RESOLVED


def test_mixed_dividend_stock_and_cash_components_are_not_conflated():
    stock = classify_event(
        row(
            event_family_source="Mixed Dividend",
            ratio_raw="(50 TEST : 1 TEST)",
            ratio_right_security="TEST",
        ),
        official_sessions=sessions(),
    )
    cash = classify_event(
        row(
            row_index=2,
            event_family_source="Mixed Dividend",
            ratio_raw="(50 TEST : 7 IDR)",
            ratio_right_security="IDR",
        ),
        official_sessions=sessions(),
    )
    assert stock.semantic_class == "EXACT_TRANSITION"
    assert stock.family == "MIXED_STOCK_DIVIDEND"
    assert cash.semantic_class == "NON_BLOCKING"
    assert cash.family == "MIXED_CASH_DIVIDEND"


def test_missing_cum_does_not_use_record_or_distribution_as_effective_date():
    event = classify_event(
        row(cum_date=None, event_family_source="Stock Dividend"),
        official_sessions=sessions(),
    )
    assert event.semantic_class == "SCHEDULE_REQUIRED"
    assert event.transition_date is None


def test_mandatory_conversion_requires_exact_official_schedule():
    source = row(
        event_family_source="Mandatory Conversion",
        cum_date=None,
        record_date="2026-04-20",
        distribution_date="2026-04-21",
    )
    event = classify_event(source, official_sessions=sessions())
    assert event.semantic_class == "SCHEDULE_REQUIRED"

    evidence = [
        {
            "event_id": event_identity(source),
            "linkage_status": "EXACT",
            "transition_semantic": "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
            "transition_date": "2026-04-17",
            "ksei_reference": "KSEI-1/JKU/0426",
            "source_sha256": "b" * 64,
        }
    ]
    resolved = classify_event(
        source,
        official_sessions=sessions(),
        schedule_evidence=evidence,
    )
    assert resolved.semantic_class == "EXACT_TRANSITION"
    assert resolved.transition_date == pd.Timestamp("2026-04-17")
    assert resolved.transition_source == "OFFICIAL_KSEI_SCHEDULE"


def test_conflicting_schedule_dates_fail_closed():
    source = row(
        event_family_source="Mandatory Conversion",
        cum_date=None,
    )
    event_id = event_identity(source)
    evidence = [
        {
            "event_id": event_id,
            "linkage_status": "EXACT",
            "transition_semantic": "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
            "transition_date": date,
            "ksei_reference": ref,
            "source_sha256": "c" * 64,
        }
        for date, ref in [
            ("2026-04-17", "KSEI-A"),
            ("2026-04-20", "KSEI-B"),
        ]
    ]
    event = classify_event(
        source,
        official_sessions=sessions(),
        schedule_evidence=evidence,
    )
    assert event.semantic_class == "SCHEDULE_REQUIRED"
    assert event.transition_date is None


def test_schedule_required_event_keeps_window_fail_closed_until_resolved():
    event = classify_event(
        row(event_family_source="Voluntary Conversion", cum_date=None),
        official_sessions=sessions(),
    )
    result = window_continuity(
        coverage_certified=True,
        cross_source_conflict=False,
        events=[event],
        entry_date="2026-04-13",
        terminal_date="2026-04-14",
    )
    assert result.status == UNRESOLVED_EVENT
    assert result.reason == "EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED"


def test_cancelled_event_is_non_blocking():
    event = classify_event(row(status="Cancelled"), official_sessions=sessions())
    result = window_continuity(
        coverage_certified=True,
        cross_source_conflict=False,
        events=[event],
        entry_date="2026-04-16",
        terminal_date="2026-04-20",
    )
    assert event.semantic_class == "NON_BLOCKING"
    assert result.status == RESOLVED


def test_event_selection_halo_is_not_used_as_transition_inference():
    event = classify_event(
        row(
            event_family_source="Mandatory Conversion",
            cum_date=None,
            record_date="2026-04-20",
            distribution_date="2026-04-21",
        ),
        official_sessions=sessions(),
    )
    assert event_relevant_to_study_period(
        event,
        period_start="2026-04-13",
        period_end="2026-04-22",
        selection_halo_calendar_days=60,
    )
    assert event.transition_date is None
