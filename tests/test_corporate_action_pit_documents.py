from __future__ import annotations

import pytest

from idx_trade.corporate_action_pit_documents import parse_asset_timestamp_candidate, parse_ksei_schedule_text


def test_asset_timestamp_is_strict_candidate_without_timezone_claim():
    parsed = parse_asset_timestamp_candidate(
        "https://web.ksei.co.id/Announcement/Files/196544_ksei_16506_jku_0626_202607011721.pdf"
    )
    assert parsed == {
        "candidate_raw": "202607011721",
        "candidate_local_naive": "2026-07-01 17:21:00",
        "parse_status": "PARSED_CANDIDATE_ONLY",
    }
    assert parse_asset_timestamp_candidate("YOII_RIGHT_20260626_ID.pdf")["parse_status"] == "NO_TERMINAL_TIMESTAMP"


def test_parser_preserves_source_date_and_asset_provenance_separately():
    row = parse_ksei_schedule_text(
        "No : KSEI-16506/JKU/0626 Jakarta, 26 Juni 2026\n"
        "Perihal : Jadwal Kegiatan Penawaran Umum Terbatas (YOII)\n"
        "Kode dan Nama Saham : YOII - Yeo Hup Indonesia Tbk",
        asset_url="https://web.ksei.co.id/Announcement/Files/196544_ksei_16506_jku_0626_202607011721.pdf",
        publication_table_date="2026-06-26",
    )
    assert row["document_date"] == "2026-06-26"
    assert row["publication_table_date"] == "2026-06-26"
    assert row["asset_timestamp_candidate_raw"] == "202607011721"
    assert row["asset_timestamp_candidate_parse_status"] == "PARSED_CANDIDATE_ONLY"


def test_parse_sini_rights_document_preserves_explicit_identity_and_evidence():
    row = parse_ksei_schedule_text(
        """
        No : KSEI-17438/JKU/0726 Jakarta, 3 Juli 2026
        Perihal : Jadwal Kegiatan Penawaran Umum Terbatas I Dalam Rangka Penerbitan HMETD Atas SINI
        Kode dan Nama Saham : SINI - SINGARAJA PUTRA Tbk
        Kode ISIN Saham : ID1000151905
        Kode HMETD & ISIN : SINI-R, ID3000069608
        Tanggal Pencatatan (Recording Date) 10 Juli 2026
        Tanggal Distribusi 13 Juli 2026
        Tanggal Pencatatan di Bursa 14 Juli 2026
        Periode Pelaksanaan HMETD 14 - 20 Juli 2026
        Setiap 2 (Dua) Saham akan mendapatkan 3 (Tiga) HMETD.
        Harga Pelaksanaan Exercise adalah Rp. 5000
        """
    )
    assert row["parse_status"] == "PARSED"
    assert row["economic_family"] == "RIGHTS_ISSUE"
    assert row["ksei_reference"] == "KSEI-17438/JKU/0726"
    assert row["ticker"] == "SINI"
    assert row["rights_isin"] == "ID3000069608"
    assert row["record_date"] == "2026-07-10"
    assert row["listing_date"] == "2026-07-14"
    assert row["exercise_start_date"] == "2026-07-14"
    assert row["ratio_right_security"] == "SINI-R"
    assert any(item["kind"] == "RIGHTS_IDENTITY" for item in row["evidence"])


def test_parse_stock_split_uses_document_subject_not_mandatory_conversion_label():
    row = parse_ksei_schedule_text(
        """
        No : KSEI-18691/JKU/0726 Jakarta, 15 Juli 2026
        Perihal : Jadwal Pelaksanaan Pemecahan Saham (Stock Split) MLPT
        Kode dan Nama Saham : MLPT - MULTIPOLAR TECHNOLOGY Tbk
        Rasio pemecahan unit saham 1:25
        Tanggal Pencatatan (Recording Date) 22 Juli 2026
        """
    )
    assert row["parse_status"] == "PARSED"
    assert row["economic_family"] == "STOCK_SPLIT"
    assert row["ratio_left_value"] == "1"
    assert row["ratio_right_value"] == "25"


def test_parse_additional_information_letter_uses_explicit_subject_ticker():
    row = parse_ksei_schedule_text(
        """
        Nomor : KSEI-7806/JKU/0426 14 April 2026
        Perihal : Informasi Tambahan Terkait Jadwal Pembagian Saham Bonus PT Bank Mega Tbk (MEGA)
        Sebagai tindak lanjut Pengumuman KSEI No. KSEI-7347/JKU/0426 7 April 2026.
        """
    )
    assert row["parse_status"] == "PARSED"
    assert row["ticker"] == "MEGA"
    assert row["prior_ksei_reference"] == "KSEI-7347/JKU/0426"


def test_parse_missing_identity_is_explicitly_unresolved():
    row = parse_ksei_schedule_text("Perihal : Stock Split MLPT\nRasio pemecahan unit saham 1:25")
    assert row["parse_status"] == "UNRESOLVED"
    assert set(row["diagnostics"]) == {"MISSING_KSEI_REFERENCE", "MISSING_TICKER", "MISSING_DOCUMENT_DATE"}


def test_schedule_date_is_not_misclassified_as_pdf_document_date():
    row = parse_ksei_schedule_text(
        "No : KSEI-1000/JKU/0726\n"
        "Perihal : Stock Split MLPT\n"
        "Kode dan Nama Saham : MLPT - MULTIPOLAR TECHNOLOGY Tbk\n"
        "Tanggal Pencatatan (Recording Date) 22 Juli 2026"
    )
    assert row["pdf_document_date"] is None
    assert row["document_date"] is None


def test_source_url_is_not_silently_treated_as_asset_filename():
    row = parse_ksei_schedule_text(
        "No : KSEI-1000/JKU/0726 Jakarta, 22 Juli 2026\n"
        "Perihal : Stock Split MLPT\n"
        "Kode dan Nama Saham : MLPT - MULTIPOLAR TECHNOLOGY Tbk",
        source_url="https://example.test/source-record",
    )
    assert row["asset_filename"] is None
    assert row["asset_timestamp_candidate_parse_status"] == "NO_ASSET_FILENAME"


def test_asset_url_and_filename_conflict_fails_closed():
    with pytest.raises(ValueError, match="asset_url and asset_filename disagree"):
        parse_ksei_schedule_text(
            "No : KSEI-1000/JKU/0726 Jakarta, 22 Juli 2026\n"
            "Perihal : Stock Split MLPT\n"
            "Kode dan Nama Saham : MLPT - MULTIPOLAR TECHNOLOGY Tbk",
            asset_url="https://web.ksei.co.id/Announcement/Files/a.pdf",
            asset_filename="b.pdf",
        )
