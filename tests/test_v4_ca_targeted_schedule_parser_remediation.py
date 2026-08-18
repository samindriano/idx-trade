from idx_trade.v4_ca_schedule_semantics import parse_ksei_schedule_transition
from idx_trade.v4_ca_targeted_schedule_parser_remediation import (
    repair_layout_parse,
    strict_layout_transition,
    strict_ticker_from_layout,
)


def test_layout_ticker_never_admits_kode_header_token():
    text = """
Emiten Kode dan Nama Saham Kode ISIN : INDOSAT Tbk, PT : ISAT - INDOSAT Tbk : ID1000097405
"""
    assert strict_ticker_from_layout(text) == "ISAT"


def test_layout_stock_split_repairs_exact_transition_without_subject_line():
    text = """
Bahwa Emiten diatas bermaksud untuk melakukan Pemecahan Nilai Nominal Saham (Stock Split).
Akhir perdagangan saham dengan Nilai Nominal Lama di Pasar Reguler dan Pasar Negosiasi 14 Oktober 2024
Mulai perdagangan saham dengan Nilai Nominal Baru di Pasar Reguler dan Pasar Negosiasi 15 Oktober 2024
Tanggal Pencatatan (Recording Date) 16 Oktober 2024
Tanggal distribusi saham dengan Nilai Nominal Baru 16 Oktober 2024
No : KSEI-23920/JKU/1024 Jakarta, 8 Oktober 2024
Emiten Kode dan Nama Saham Kode ISIN : INDOSAT Tbk, PT : ISAT - INDOSAT Tbk : ID1000097405
"""
    original = parse_ksei_schedule_transition(text)
    repaired = repair_layout_parse(text, original)

    assert repaired.parse_status == "PARSED_EXACT_TRANSITION"
    assert repaired.ticker == "ISAT"
    assert repaired.event_family == "STOCK_SPLIT"
    assert repaired.record_date == "2024-10-16"
    assert repaired.distribution_date == "2024-10-16"
    assert repaired.transition_date == "2024-10-15"
    assert repaired.transition_semantic == "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"


def test_layout_rights_ex_date_is_admitted_only_from_same_row_date():
    text = """
No : KSEI-11111/JKU/1225 Jakarta, 1 Desember 2025
Jadwal HMETD PT Test Tbk
Tanggal perdagangan bursa memuat HMETD (Cum HMETD) di Pasar Reguler dan Pasar Negosiasi 8 Desember 2025
Tanggal perdagangan bursa tidak memuat HMETD (Ex HMETD) di Pasar Reguler dan Pasar Negosiasi 9 Desember 2025
Tanggal Pencatatan (Recording Date) 10 Desember 2025
Tanggal Distribusi 10 Desember 2025
Emiten Kode dan Nama Saham Kode ISIN : TEST Tbk, PT : TEST - TEST Tbk : ID1000000000
"""
    original = parse_ksei_schedule_transition(text)
    repaired = repair_layout_parse(text, original)

    assert repaired.parse_status == "PARSED_EXACT_TRANSITION"
    assert repaired.ticker == "TEST"
    assert repaired.event_family == "RIGHTS_HMETD"
    assert repaired.transition_date == "2025-12-09"
    assert repaired.transition_semantic == "REGULAR_MARKET_EX_DATE"
    assert repaired.record_date == "2025-12-10"
    assert repaired.distribution_date == "2025-12-10"


def test_layout_generic_tanggal_ex_regular_market_row_is_admitted():
    text = """
No : KSEI-22222/JKU/1225 Jakarta, 1 Desember 2025
Jadwal HMETD PT Test Tbk
Tanggal Cum di Pasar Reguler dan Pasar Negosiasi 8 Desember 2025
Tanggal Ex di Pasar Reguler dan Pasar Negosiasi 9 Desember 2025
Tanggal Cum di Pasar Tunai 10 Desember 2025
Tanggal Pencatatan (Recording Date) 10 Desember 2025
Tanggal Distribusi 10 Desember 2025
Emiten Kode dan Nama Saham Kode ISIN : TEST Tbk, PT : TEST - TEST Tbk : ID1000000000
"""
    original = parse_ksei_schedule_transition(text)
    repaired = repair_layout_parse(text, original)

    assert repaired.parse_status == "PARSED_EXACT_TRANSITION"
    assert repaired.transition_date == "2025-12-09"
    assert repaired.transition_semantic == "REGULAR_MARKET_EX_DATE"


def test_flattened_stock_split_date_list_is_not_inferred():
    text = """
Pemecahan Nilai Nominal Saham (Stock Split)
Akhir perdagangan saham dengan Nilai Nominal Lama di Pasar Reguler dan Pasar Negosiasi
Mulai perdagangan saham dengan Nilai Nominal Baru di Pasar Reguler dan Pasar Negosiasi
Tanggal Pencatatan (Recording Date)
Tanggal distribusi saham dengan Nilai Nominal Baru
16 Oktober 2024 15 Oktober 2024 11 Oktober 2024 14 Oktober 2024
"""
    date_value, semantic, diagnostics = strict_layout_transition(text)
    assert date_value is None
    assert semantic is None
    assert diagnostics == ("NO_EXPLICIT_LAYOUT_REGULAR_MARKET_TRANSITION",)
