from __future__ import annotations

from idx_trade.corporate_action_pit_linkage import (
    EventFamily,
    LinkageStatus,
    link_event,
    normalize_event_family,
    revision_relation,
)


def test_schedule_document_economic_family_overrides_cbest_operation_label():
    assert normalize_event_family(
        source_family="Right Distribution",
        schedule_subject="Jadwal Pelaksanaan Pembagian Saham Bonus PT Bank Mega Tbk (MEGA)",
    ) == EventFamily.BONUS_SHARES
    assert normalize_event_family(
        source_family="Mixed Dividend",
        schedule_subject="Informasi Tambahan Pembagian Saham Bonus PT Bank Mega Tbk (MEGA)",
    ) == EventFamily.BONUS_SHARES


def test_explicit_prior_ksei_reference_establishes_append_only_revision_lineage():
    base = {
        "ticker": "MEGA",
        "event_family": "BONUS_SHARES",
        "ksei_reference": "KSEI-7347/JKU/0426",
        "record_date": "2026-04-13",
        "distribution_date": "2026-04-30",
        "ratio_left_value": "1",
        "ratio_left_security": "MEGA",
        "ratio_right_value": "1",
        "ratio_right_security": "MEGA",
    }
    later = {
        "ticker": "MEGA",
        "event_family": "BONUS_SHARES",
        "ksei_reference": "KSEI-7806/JKU/0426",
        "prior_ksei_reference": "KSEI-7347/JKU/0426",
        "subject": "Informasi Tambahan Pembagian Saham Bonus PT Bank Mega Tbk (MEGA)",
        "record_date": "2026-04-13",
        "distribution_date": "2026-04-30",
    }
    decision = revision_relation(base, later)
    assert decision.status == LinkageStatus.EXACT
    assert decision.reasons == ("EXPLICIT_REVISION", "PRIOR_KSEI_REFERENCE_EXACT")

    conflict = revision_relation(
        base,
        dict(later, prior_ksei_reference="KSEI-OTHER/JKU/0426"),
    )
    assert conflict.status == LinkageStatus.CONFLICT
    assert conflict.conflicts == ("prior_ksei_reference",)


def test_explicit_prior_reference_keeps_lineage_when_schedule_dates_change():
    base = {
        "ticker": "MEGA",
        "event_family": "BONUS_SHARES",
        "ksei_reference": "KSEI-7347/JKU/0426",
        "record_date": "2026-04-13",
        "distribution_date": "2026-04-30",
    }
    later = {
        "ticker": "MEGA",
        "event_family": "BONUS_SHARES",
        "ksei_reference": "KSEI-7806/JKU/0426",
        "prior_ksei_reference": "KSEI-7347/JKU/0426",
        "subject": "Penjadwalan Ulang Pembagian Saham Bonus",
        "record_date": "2026-04-14",
        "distribution_date": "2026-05-04",
    }
    decision = revision_relation(base, later)
    assert decision.status == LinkageStatus.EXACT
    assert decision.reasons == ("EXPLICIT_REVISION", "PRIOR_KSEI_REFERENCE_EXACT")


def test_schedule_subject_precedence_applies_through_link_event():
    event = {
        "ticker": "MEGA",
        "event_family": "MIXED_DIVIDEND",
        "schedule_subject": "Informasi Tambahan Pembagian Saham Bonus MEGA",
        "record_date": "2026-04-13",
        "distribution_date": "2026-04-30",
        "ratio_left_value": "1",
        "ratio_left_security": "MEGA",
        "ratio_right_value": "1",
        "ratio_right_security": "MEGA",
    }
    candidate = dict(event, event_family="BONUS_SHARES")
    assert link_event(event, [candidate]).status == LinkageStatus.EXACT


def test_revision_language_is_not_triggered_by_exchange_or_title_ignored():
    base = {"ticker": "MEGA", "event_family": "BONUS_SHARES", "ksei_reference": "KSEI-1"}
    later = dict(base, subject="Exchange announcement", title="Routine notice")
    assert revision_relation(base, later).status == LinkageStatus.UNRESOLVED
    title_only = dict(
        base,
        title="Additional Information for MEGA",
        prior_ksei_reference="KSEI-1",
    )
    assert revision_relation(base, title_only).status == LinkageStatus.EXACT


def test_rights_identifier_presence_mismatch_cannot_fallback_to_ratio_date():
    event = {
        "ticker": "SINI",
        "event_family": "RIGHTS_ISSUE",
        "rights_code": "SINI-R",
        "record_date": "2026-07-10",
        "listing_date": "2026-07-14",
        "ratio_left_value": "2",
        "ratio_left_security": "SINI",
        "ratio_right_value": "3",
        "ratio_right_security": "SINI-R",
    }
    candidate = dict(event)
    candidate.pop("rights_code")
    decision = link_event(event, [candidate])
    assert decision.status == LinkageStatus.CONFLICT


def test_explicit_conflicting_candidate_blocks_other_exact_candidate():
    event = {
        "ticker": "ABCD",
        "event_family": "STOCK_SPLIT",
        "record_date": "2026-07-10",
        "listing_date": "2026-07-14",
        "ratio_left_value": "1",
        "ratio_left_security": "ABCD",
        "ratio_right_value": "5",
        "ratio_right_security": "ABCD",
    }
    exact = dict(event)
    conflicting = dict(event, ratio_right_value="10")
    assert link_event(event, [exact, conflicting]).status == LinkageStatus.CONFLICT
