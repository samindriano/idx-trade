from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

import idx_trade.v4_ca_targeted_schedule_evidence as targeted
from idx_trade.v4_ca_event_windows import EventSemantic
from scripts.run_v4_ca_targeted_schedule_evidence import (
    EXPECTED_SELECTED,
    exact_source_date_link,
    query_months,
    validate_selected,
)


def _selected_nisp() -> dict[str, str]:
    return {
        "event_id": targeted.NISP_EVENT_ID,
        "ticker": "NISP",
        "source_type": "Voluntary Conversion",
        "source_dates": "2024-09-06",
    }


def _static_row(**overrides):
    row = {
        "ticker": "NISP",
        "event_family_source": "Voluntary Conversion",
        "status": "Active",
        "ratio_parse_status": "PARSED_SOURCE_TEXT_ONLY",
        "ratio_raw": "(1 NISP : 1230 IDR)",
        "ratio_left_security": "NISP",
        "ratio_right_security": "IDR",
        "cum_date": None,
        "record_date": None,
        "distribution_date": "2024-09-06",
        "source_url": "https://web.ksei.co.id/example/NISP",
        "source_sha256": "a" * 64,
    }
    row.update(overrides)
    return row


def _base_event(*, semantic_class: str = "SCHEDULE_REQUIRED") -> EventSemantic:
    transition = pd.Timestamp("2024-09-05") if semantic_class == "EXACT_TRANSITION" else None
    return EventSemantic(
        event_id=targeted.NISP_EVENT_ID,
        ticker="NISP",
        source_type="Voluntary Conversion",
        family="VOLUNTARY_CONVERSION",
        semantic_class=semantic_class,
        transition_date=transition,
        transition_source="TEST" if transition is not None else None,
        reason="TEST",
        source_dates=(pd.Timestamp("2024-09-06"),),
    )


def test_selected_subset_artifact_is_exactly_frozen_seven():
    path = Path("docs/artifacts/v4_ca_schedule_event_impact_attribution_20260818_v1/selected_schedule_event_subset.csv")
    frame = validate_selected(path)
    assert len(frame) == 7
    assert set(frame["event_id"]) == set(EXPECTED_SELECTED)


def test_query_months_is_exact_plus_minus_two_months():
    assert query_months("2025-01-06") == [
        (2024, 11), (2024, 12), (2025, 1), (2025, 2), (2025, 3)
    ]


def test_exact_source_date_link_uses_record_or_distribution_only():
    event = {"source_dates": "2024-10-11|2024-10-15|2024-10-16"}
    assert exact_source_date_link(event, {"record_date": "2024-10-15", "distribution_date": ""})
    assert not exact_source_date_link(event, {"record_date": "", "distribution_date": "2024-10-17"})


def test_nisp_static_cash_exact_security_to_currency_resolves():
    evidence = targeted.resolve_nisp_static_cash_evidence(_selected_nisp(), [_static_row()])
    assert evidence["linkage_status"] == targeted.STATIC_LINKAGE_STATUS
    assert evidence["ratio_left_security"] == "NISP"
    assert evidence["ratio_right_security"] == "IDR"
    assert evidence["identity_date"] == "2024-09-06"


def test_nisp_static_cash_rejects_wrong_currency_or_security():
    wrong_currency = targeted.resolve_nisp_static_cash_evidence(
        _selected_nisp(), [_static_row(ratio_right_security="NISP")]
    )
    assert wrong_currency["linkage_status"] == "UNRESOLVED"
    wrong_left = targeted.resolve_nisp_static_cash_evidence(
        _selected_nisp(), [_static_row(ratio_left_security="XXXX")]
    )
    assert wrong_left["linkage_status"] == "UNRESOLVED"


def test_nisp_static_cash_requires_exact_source_date_overlap():
    evidence = targeted.resolve_nisp_static_cash_evidence(
        _selected_nisp(), [_static_row(distribution_date="2024-09-07")]
    )
    assert evidence["linkage_status"] == "UNRESOLVED"


def test_nisp_static_cash_multiple_candidates_fail_closed():
    evidence = targeted.resolve_nisp_static_cash_evidence(
        _selected_nisp(), [_static_row(), _static_row(source_sha256="b" * 64)]
    )
    assert evidence["linkage_status"] == "UNRESOLVED"
    assert evidence["diagnostics"] == "EXACT_CANDIDATE_COUNT:2"


def test_targeted_classifier_turns_exact_nisp_static_cash_nonblocking(monkeypatch):
    base = _base_event()
    monkeypatch.setattr(targeted, "event_identity", lambda row: targeted.NISP_EVENT_ID)
    monkeypatch.setattr(
        targeted,
        "classify_event_with_residual_document_evidence",
        lambda row, official_sessions, schedule_evidence: base,
    )
    evidence = targeted.resolve_nisp_static_cash_evidence(_selected_nisp(), [_static_row()])
    result = targeted.classify_event_with_targeted_evidence(
        {"event_family_source": "Voluntary Conversion"},
        official_sessions=[],
        schedule_evidence=[evidence],
    )
    assert result.semantic_class == "NON_BLOCKING"
    assert result.family == "VOLUNTARY_CASH_STATIC_SECURITY_TO_CURRENCY"


def test_targeted_classifier_conflicting_duplicate_static_rows_fail_closed(monkeypatch):
    base = _base_event()
    monkeypatch.setattr(targeted, "event_identity", lambda row: targeted.NISP_EVENT_ID)
    monkeypatch.setattr(
        targeted,
        "classify_event_with_residual_document_evidence",
        lambda row, official_sessions, schedule_evidence: base,
    )
    evidence = targeted.resolve_nisp_static_cash_evidence(_selected_nisp(), [_static_row()])
    second = dict(evidence)
    second["source_sha256"] = "b" * 64
    result = targeted.classify_event_with_targeted_evidence(
        {"event_family_source": "Voluntary Conversion"},
        official_sessions=[],
        schedule_evidence=[evidence, second],
    )
    assert result.semantic_class == "SCHEDULE_REQUIRED"
    assert "CONFLICT" in result.reason


def test_targeted_classifier_cash_and_exact_transition_conflict_fails_closed(monkeypatch):
    base = _base_event(semantic_class="EXACT_TRANSITION")
    monkeypatch.setattr(targeted, "event_identity", lambda row: targeted.NISP_EVENT_ID)
    monkeypatch.setattr(
        targeted,
        "classify_event_with_residual_document_evidence",
        lambda row, official_sessions, schedule_evidence: base,
    )
    evidence = targeted.resolve_nisp_static_cash_evidence(_selected_nisp(), [_static_row()])
    result = targeted.classify_event_with_targeted_evidence(
        {"event_family_source": "Voluntary Conversion"},
        official_sessions=[],
        schedule_evidence=[evidence],
    )
    assert result.semantic_class == "SCHEDULE_REQUIRED"
    assert result.reason == "TARGETED_STATIC_CASH_AND_TRANSITION_CONFLICT_FAIL_CLOSED"


def test_non_nisp_event_is_never_changed_by_static_overlay(monkeypatch):
    other = replace(_base_event(), event_id="OTHER", ticker="ISAT")
    monkeypatch.setattr(targeted, "event_identity", lambda row: "OTHER")
    monkeypatch.setattr(
        targeted,
        "classify_event_with_residual_document_evidence",
        lambda row, official_sessions, schedule_evidence: other,
    )
    result = targeted.classify_event_with_targeted_evidence(
        {"event_family_source": "Mandatory Conversion"},
        official_sessions=[],
        schedule_evidence=[],
    )
    assert result == other
