from __future__ import annotations

from idx_trade.corporate_action_pit_linkage import (
    EventFamily,
    LinkageStatus,
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
