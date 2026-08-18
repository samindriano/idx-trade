from __future__ import annotations

import pandas as pd

from idx_trade.v4_ca_adro_entitlement_semantics import (
    ADRO_EVENT_ID,
    ADRO_TRANSITION_DATE,
    AdroEntitlementEvidence,
    _norm,
    _verify_adro_normalized_texts,
    apply_adro_entitlement_evidence,
    is_exact_adro_pups_row,
)
from idx_trade.v4_ca_event_windows import EventSemantic


def _row(**overrides):
    row = {
        "ticker": "ADRO",
        "event_family_source": "Right Distribution",
        "cum_date": "",
        "record_date": "2024-11-29",
        "distribution_date": "2024-12-02",
        "status": "Active",
        "ratio_left_value": "4389",
        "ratio_left_security": "ADRO",
        "ratio_right_value": "1000",
        "ratio_right_security": "ADRO-H",
    }
    row.update(overrides)
    return row


def _base(event_id: str = ADRO_EVENT_ID) -> EventSemantic:
    return EventSemantic(
        event_id=event_id,
        ticker="ADRO",
        source_type="Right Distribution",
        family="RIGHT_DISTRIBUTION",
        semantic_class="SCHEDULE_REQUIRED",
        transition_date=None,
        transition_source=None,
        reason="SOURCE_NATIVE_CUM_MISSING_OR_NOT_OFFICIAL_SESSION",
        source_dates=(pd.Timestamp("2024-11-29"), pd.Timestamp("2024-12-02")),
    )


def _evidence() -> AdroEntitlementEvidence:
    return AdroEntitlementEvidence(
        prospectus_sha256="a" * 64,
        egms_minutes_sha256="b" * 64,
    )


def _prospectus_text(*, direct_clause: bool = False, record_date: str = "29 november 2024") -> str:
    core = (
        "penawaran umum oleh pemegang saham pt adaro andalan indonesia tbk "
        f"daftar pemegang saham {record_date} "
        "setiap pemegang saham yang memiliki 4.389 saham perseroan akan mendapatkan "
        "1.000 hak membeli saham tanggal distribusi hak membeli saham 2 desember 2024"
    )
    if direct_clause:
        core += (
            " pihak yang dapat berpartisipasi dalam pups ini pemegang saham perseroan "
            "memperoleh dividen berdasarkan keputusan rapat umum pemegang saham luar biasa "
            "perseroan tanggal 18 november 2024"
        )
    return core


def _egms_text(*, ex_date: str = "november 28th, 2024") -> str:
    return (
        "distribution schedule of the additional final cash dividend "
        "the date for recording the shareholders who are entitled to the additional final cash dividend "
        "november 29th, 2024 regular and negotiated market cum dividend ex dividend "
        f"november 26th, 2024 {ex_date}"
    )


def test_exact_adro_frozen_event_promotes_to_20241128() -> None:
    event = apply_adro_entitlement_evidence(
        _row(), base_event=_base(), evidence=_evidence()
    )
    assert event.semantic_class == "EXACT_TRANSITION"
    assert event.transition_date == ADRO_TRANSITION_DATE
    assert event.transition_source == "OFFICIAL_ISSUER_CROSS_DOCUMENT_ENTITLEMENT_EX_DATE"
    assert "DIVIDEND_ENTITLEMENT" in event.reason


def test_wrong_event_id_cannot_use_entitlement_evidence() -> None:
    base = _base("x" * 64)
    event = apply_adro_entitlement_evidence(
        _row(), base_event=base, evidence=_evidence()
    )
    assert event is base
    assert event.semantic_class == "SCHEDULE_REQUIRED"


def test_record_date_alone_is_not_enough() -> None:
    base = _base()
    event = apply_adro_entitlement_evidence(
        _row(ratio_right_security=""), base_event=base, evidence=_evidence()
    )
    assert event is base
    assert event.transition_date is None


def test_wrong_ratio_fails_closed() -> None:
    assert not is_exact_adro_pups_row(
        _row(ratio_left_value="4388"), event_id=ADRO_EVENT_ID
    )


def test_transition_evidence_date_cannot_drift() -> None:
    evidence = AdroEntitlementEvidence(
        prospectus_sha256="a" * 64,
        egms_minutes_sha256="b" * 64,
        transition_date=pd.Timestamp("2024-11-27"),
    )
    try:
        apply_adro_entitlement_evidence(_row(), base_event=_base(), evidence=evidence)
    except RuntimeError as exc:
        assert "TRANSITION_DATE_CHANGED" in str(exc)
    else:
        raise AssertionError("ADRO transition date drift must fail closed")


def test_pdf_normalization_collapses_layout_and_ordinal_artifacts() -> None:
    raw = (
        "PIHAK YANG DAPAT BERPARTISIPASI DALAM PUPS INI\n"
        "ADALAH PEMEGANG SAHAM PERSEROAN\u00a0YANG MEMPEROLEH DIVIDEN "
        "BERDASARKAN KEPUTUSAN\nRAPAT UMUM PEMEGANG SAHAM LUAR BIASA "
        "PERSEROAN TANGGAL 18 NOVEMBER 2024. November 29 th, 2024"
    )
    normalized = _norm(raw)
    assert "pihak yang dapat berpartisipasi dalam pups ini" in normalized
    assert "memperoleh dividen berdasarkan keputusan" in normalized
    assert "rapat umum pemegang saham luar biasa perseroan tanggal 18 november 2024" in normalized
    assert "november 29th, 2024" in normalized


def test_direct_clause_route_is_accepted() -> None:
    method = _verify_adro_normalized_texts(
        _prospectus_text(direct_clause=True), _egms_text()
    )
    assert method == "DIRECT_PROSPECTUS_DIVIDEND_ENTITLEMENT_CLAUSE"


def test_boxed_clause_extraction_loss_uses_exact_record_set_identity() -> None:
    method = _verify_adro_normalized_texts(
        _prospectus_text(direct_clause=False), _egms_text()
    )
    assert method == "EXACT_2024-11-29_SHAREHOLDER_RECORD_SET_IDENTITY"


def test_record_set_mismatch_fails_closed() -> None:
    try:
        _verify_adro_normalized_texts(
            _prospectus_text(record_date="28 november 2024"), _egms_text()
        )
    except RuntimeError as exc:
        assert "RECORD_SET_IDENTITY_MISSING" in str(exc)
    else:
        raise AssertionError("ADRO record-set mismatch must fail closed")


def test_egms_ex_date_mismatch_fails_closed() -> None:
    try:
        _verify_adro_normalized_texts(
            _prospectus_text(), _egms_text(ex_date="november 27th, 2024")
        )
    except RuntimeError as exc:
        assert "EGMS_EX_DIVIDEND_SCHEDULE_MISSING" in str(exc)
    else:
        raise AssertionError("ADRO explicit ex-date mismatch must fail closed")
