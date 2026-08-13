from __future__ import annotations

from idx_trade.corporate_action_pit_documents import parse_ksei_schedule_text


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
