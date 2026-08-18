from __future__ import annotations

import pandas as pd

import idx_trade.v4_ca_fren_archive_semantics as fren


def test_issuer_archive_census_requires_only_pmhmetd_2024_and_merger_terminal() -> None:
    result = fren.verify_smartfren_archive_pages(
        b"Aksi Korporasi 2024 Prospektus PMHMETD V PT Smartfren Telecom Tbk",
        b"Perubahan Jadwal PMHMETD V Informasi Tambahan PMHMETD V FREN Prospektus Ringkas PMHMETD V FREN",
        b"Merger Pengumuman ke-2 untuk Pemegang Waran FREN",
        b"PT Smartfren Telecom Tbk pada tanggal 16 April 2025 resmi bergabung dengan PT XL Axiata Tbk",
    )
    assert result["issuer_2024_mechanical_families"] == ["PMHMETD_V_RIGHTS_ISSUE"]
    assert result["issuer_2025_terminal_family"] == "MERGER_SECURITY_CESSATION"


def test_issuer_archive_additional_mechanical_family_fails_closed() -> None:
    try:
        fren.verify_smartfren_archive_pages(
            b"Aksi Korporasi 2024 Prospektus PMHMETD V PT Smartfren Telecom Tbk Stock Split",
            b"Perubahan Jadwal PMHMETD V Informasi Tambahan PMHMETD V FREN Prospektus Ringkas PMHMETD V FREN",
            b"Merger FREN",
            b"PT Smartfren Telecom Tbk 16 April 2025 PT XL Axiata Tbk",
        )
    except RuntimeError as exc:
        assert "ADDITIONAL_MECHANICAL_FAMILY" in str(exc)
    else:
        raise AssertionError("additional issuer mechanical family must fail closed")


def test_ksei_right_identity_is_exact() -> None:
    fren.verify_ksei_right_pages(
        b"18 April 2024 FREN SMARTFREN TELECOM Tbk, PT Distribusi Right/ Efek",
        b"19 April 2024 FREN SMARTFREN TELECOM Tbk, PT Distribusi Right/ Efek Member Entitlement",
    )


def test_ksei_merger_processing_identity_is_exact() -> None:
    fren.verify_ksei_merger_pages(
        b"16 April 2025 FREN SMARTFREN TELECOM Tbk Stock Split/ Reverse Stock/ Amortisasi",
        b"16 April 2025 FREN SMARTFREN TELECOM Tbk VOLUNTARY CONVERSION",
        b"17 April 2025 FREN SMARTFREN TELECOM Tbk Stock Split/ Reverse Stock/ Amortisasi",
    )


def test_rights_prospectus_requires_explicit_regular_market_ex_date(monkeypatch) -> None:
    monkeypatch.setattr(
        fren,
        "pdf_text",
        lambda payload: (
            "Setiap 178 saham memperoleh 75 HMETD. Recording date 18 April 2024. "
            "Cum Right Pasar Reguler dan Pasar Negosiasi 16 April 2024. "
            "Ex Right Pasar Reguler dan Pasar Negosiasi 17 April 2024. "
            "Perdagangan HMETD 22 April 2024 sampai 6 Mei 2024."
        ),
    )
    result = fren.verify_rights_prospectus(b"fake")
    assert result["transition_date"] == "2024-04-17"
    assert result["ratio"] == "178_OLD_TO_75_HMETD"


def test_rights_record_date_without_explicit_ex_date_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        fren,
        "pdf_text",
        lambda payload: (
            "Setiap 178 saham memperoleh 75 HMETD. Recording date 18 April 2024. "
            "Perdagangan HMETD 22 April 2024 sampai 6 Mei 2024."
        ),
    )
    try:
        fren.verify_rights_prospectus(b"fake")
    except RuntimeError as exc:
        assert "EX_DATE_NOT_EXPLICIT" in str(exc)
    else:
        raise AssertionError("record date alone must not produce an ex-right date")


def test_synthetic_right_event_is_exact_and_not_record_date_inferred() -> None:
    event = fren.synthetic_fren_rights_event("a" * 64)
    assert event.ticker == "FREN"
    assert event.semantic_class == "EXACT_TRANSITION"
    assert event.transition_date == pd.Timestamp("2024-04-17")
    assert event.source_dates == (
        pd.Timestamp("2024-04-18"),
        pd.Timestamp("2024-04-19"),
    )
    assert "NO_RECORD_DATE_INFERENCE" in event.reason
