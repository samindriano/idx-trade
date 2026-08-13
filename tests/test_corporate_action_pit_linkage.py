from __future__ import annotations

import pytest

from idx_trade.corporate_action_pit_linkage import (
    EventFamily,
    LinkageStatus,
    link_event,
    normalize_event_family,
    revision_relation,
    safe_availability_date,
    validate_schedule_locator,
)


def _sini_rights() -> dict[str, str]:
    return {
        "ticker": "SINI",
        "event_family": "RIGHTS_ISSUE",
        "rights_code": "SINI-R",
        "rights_isin": "ID3000069608",
        "record_date": "2026-07-10",
        "distribution_date": "2026-07-13",
        "listing_date": "2026-07-14",
        "ratio_left_value": "2",
        "ratio_left_security": "SINI",
        "ratio_right_value": "3",
        "ratio_right_security": "SINI-R",
    }


def test_rights_identifier_keeps_event_identity_across_explicit_schedule_revision():
    base = _sini_rights()
    revised = dict(base, record_date="2026-07-11", subject="Perubahan Jadwal HMETD SINI")
    decision = link_event(base, [revised])
    assert decision.status == LinkageStatus.EXACT
    assert "RIGHTS_CODE_EXACT" in decision.reasons
    assert "RECORD_DATE_VERSION_DIFF" in decision.reasons
    revision = revision_relation(base, revised)
    assert revision.status == LinkageStatus.EXACT
    assert revision.reasons[0] == "EXPLICIT_REVISION"


def test_title_or_date_proximity_alone_never_creates_exact_linkage():
    event = _sini_rights()
    candidate = {
        "ticker": "SINI",
        "event_family": "RIGHTS_ISSUE",
        "subject": "HMETD SINI",
        "record_date": "2026-07-09",
    }
    assert link_event(event, [candidate]).status != LinkageStatus.EXACT


def test_mandatory_conversion_requires_schedule_document_to_classify_split_direction():
    assert normalize_event_family(source_family="Mandatory Conversion") == EventFamily.MANDATORY_CONVERSION_UNCLASSIFIED
    assert normalize_event_family(
        source_family="Mandatory Conversion",
        schedule_subject="Jadwal Pelaksanaan Pemecahan Saham (Stock Split) atas MULTIPOLAR TECHNOLOGY Tbk (MLPT)",
    ) == EventFamily.STOCK_SPLIT
    assert normalize_event_family(
        source_family="Mandatory Conversion",
        schedule_subject="Jadwal Reverse Stock Split ABCD",
    ) == EventFamily.REVERSE_SPLIT
    assert normalize_event_family(
        source_family="Mandatory Conversion",
        schedule_subject="Jadwal Pelaksanaan Pemecahan Saham (Stock Split) atas MLPT",
    ) == EventFamily.STOCK_SPLIT
    assert normalize_event_family(source_family="Tanpa HMETD") == EventFamily.NON_PREEMPTIVE_ISSUANCE


def test_ksei_schedule_index_reference_mismatch_is_not_silently_repaired():
    locator = {"reference": "KSEI-17016/JKU/0726", "ticker": "COCO"}
    document = {"ksei_reference": "KSEI-17977/JKU/0726", "ticker": "COCO"}
    decision = validate_schedule_locator(locator, document)
    assert decision.status == LinkageStatus.CONFLICT
    assert decision.conflicts == ("KSEI_REFERENCE_MISMATCH",)
    assert dict(decision.evidence)["locator_reference"] == "KSEI-17016/JKU/0726"
    assert dict(decision.evidence)["document_reference"] == "KSEI-17977/JKU/0726"


def test_locator_conflict_dominates_incomplete_second_identity():
    decision = validate_schedule_locator(
        {"reference": "KSEI-17016/JKU/0726", "ticker": "COCO"},
        {"ksei_reference": "KSEI-17977/JKU/0726", "ticker": ""},
    )
    assert decision.status == LinkageStatus.CONFLICT
    assert decision.conflicts == ("KSEI_REFERENCE_MISMATCH",)


def test_ksei_schedule_index_missing_identity_fails_closed():
    decision = validate_schedule_locator(
        {"reference": "KSEI-17016/JKU/0726", "ticker": "COCO"},
        {"ksei_reference": "", "ticker": "COCO"},
    )
    assert decision.status == LinkageStatus.UNRESOLVED
    assert decision.reasons == ("KSEI_REFERENCE_INCOMPLETE",)


def test_distribution_event_requires_exact_ratio_record_and_distribution_dates():
    event = {
        "ticker": "CCSI",
        "event_family": "STOCK_DIVIDEND",
        "record_date": "2021-11-02",
        "distribution_date": "2021-11-24",
        "ratio_left_value": "5",
        "ratio_left_security": "CCSI",
        "ratio_right_value": "1",
        "ratio_right_security": "CCSI",
    }
    assert link_event(event, [dict(event)]).status == LinkageStatus.EXACT
    wrong_distribution = dict(event, distribution_date="2021-11-25")
    assert link_event(event, [wrong_distribution]).status != LinkageStatus.EXACT


def test_multiple_exact_candidates_fail_closed_as_ambiguous():
    event = _sini_rights()
    assert link_event(event, [dict(event), dict(event)]).status == LinkageStatus.AMBIGUOUS


def test_availability_precision_never_fabricates_ksei_intraday_timestamp():
    assert safe_availability_date(ksei_document_date="2026-07-03") == {
        "knowledge_at_utc": None,
        "knowledge_date": "2026-07-03",
        "precision": "DATE_ONLY",
    }
    assert safe_availability_date(
        idx_published_at_utc="2026-07-03T03:00:00Z",
        linkage_status=LinkageStatus.EXACT,
    ) == {
        "knowledge_at_utc": "2026-07-03T03:00:00Z",
        "knowledge_date": "2026-07-03",
        "precision": "IDX_TIMESTAMP_CONFIRMED",
    }
    with pytest.raises(ValueError, match="EXACT linkage"):
        safe_availability_date(idx_published_at_utc="2026-07-03T03:00:00Z")
    with pytest.raises(ValueError, match="timezone"):
        safe_availability_date(idx_published_at_utc="2026-07-03T10:00:00")
