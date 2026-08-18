from __future__ import annotations

import pandas as pd
import pytest

import idx_trade.v4_ca_fren_ksei_schedule_semantics as fren


def _schedule_text() -> str:
    return (
        "PT Smartfren Telecom Tbk FREN HMETD. KSEI-7000/JKU/0424. "
        "Setiap 178 saham memperoleh 75 HMETD. "
        "Tanggal Cum di Pasar Regular dan Pasar Negosiasi 16 April 2024. "
        "Tanggal Ex di Pasar Regular dan Pasar Negosiasi 17 April 2024. "
        "Tanggal Pencatatan 18 April 2024. Tanggal Distribusi 19 April 2024. "
        "Perdagangan HMETD dimulai 22 April 2024 dan berakhir 6 Mei 2024."
    )


def test_ksei_schedule_accepts_only_explicit_regular_negotiated_ex_date(monkeypatch) -> None:
    monkeypatch.setattr(fren, "sha256_bytes", lambda payload: fren.EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256)
    monkeypatch.setattr(fren, "pdf_text", lambda payload: _schedule_text())
    result = fren.verify_ksei_fren_rights_schedule_pdf(b"fake")
    assert result["transition_date"] == "2024-04-17"
    assert result["transition_semantic"] == "OFFICIAL_KSEI_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE"
    assert result["cum_regular_negotiated"] == "2024-04-16"
    assert result["record_date"] == "2024-04-18"
    assert result["ratio"] == "178_OLD_TO_75_HMETD"
    assert result["reference_no"] == "KSEI-7000/JKU/0424"


def test_ksei_schedule_record_date_without_explicit_ex_label_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(fren, "sha256_bytes", lambda payload: fren.EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256)
    monkeypatch.setattr(
        fren,
        "pdf_text",
        lambda payload: _schedule_text().replace(
            "Tanggal Ex di Pasar Regular dan Pasar Negosiasi 17 April 2024.",
            "Tanggal 17 April 2024.",
        ),
    )
    with pytest.raises(RuntimeError, match="EX_RIGHT_LABEL_MISSING"):
        fren.verify_ksei_fren_rights_schedule_pdf(b"fake")


def test_ksei_schedule_sha_is_pinned(monkeypatch) -> None:
    monkeypatch.setattr(fren, "sha256_bytes", lambda payload: "0" * 64)
    with pytest.raises(RuntimeError, match="SHA_CHANGED"):
        fren.verify_ksei_fren_rights_schedule_pdf(b"fake")


def test_synthetic_ksei_right_event_is_truthful_and_exact() -> None:
    event = fren.synthetic_fren_rights_event_ksei(fren.EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256)
    assert event.ticker == "FREN"
    assert event.source_type == "OFFICIAL_KSEI_RIGHTS_SCHEDULE"
    assert event.semantic_class == "EXACT_TRANSITION"
    assert event.transition_date == pd.Timestamp("2024-04-17")
    assert event.transition_source == "OFFICIAL_KSEI_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE"
    assert "NO_RECORD_DATE_INFERENCE" in event.reason
    assert pd.Timestamp("2024-04-18") in event.source_dates
