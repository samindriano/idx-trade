from idx_trade.v4_ca_schedule_semantics import parse_ksei_schedule_transition


def test_parse_rights_regular_market_ex_date_without_using_record_date():
    text = """
Nomor : KSEI-12345/JKU/0426 14 April 2026
Perihal : Jadwal Kegiatan Penawaran Umum Terbatas dalam rangka Penerbitan Hak Memesan Efek Terlebih Dahulu (HMETD) PT Test Tbk (TEST)

Kode dan Nama Saham : TEST - PT Test Tbk
1. Tanggal perdagangan bursa yang memuat HMETD (Cum HMETD) di Pasar Reguler dan Pasar Negosiasi 14 April 2026
2. Tanggal perdagangan bursa tidak memuat HMETD (Ex HMETD) di Pasar Reguler dan Pasar Negosiasi 15 April 2026
5. Tanggal Penentuan Pemegang Rekening yang berhak menerima HMETD (Recording Date) 16 April 2026
6. Periode distribusi HMETD 17 April 2026
"""
    parsed = parse_ksei_schedule_transition(text)
    assert parsed.parse_status == "PARSED_EXACT_TRANSITION"
    assert parsed.ticker == "TEST"
    assert parsed.event_family == "RIGHTS_HMETD"
    assert parsed.transition_date == "2026-04-15"
    assert parsed.transition_semantic == "REGULAR_MARKET_EX_DATE"
    assert parsed.transition_date != parsed.record_date


def test_parse_stock_split_first_new_nominal_regular_market_date():
    text = """
Nomor : KSEI-99999/JKU/0426 14 April 2026
Perihal : Jadwal Pelaksanaan Pemecahan Saham (Stock Split) atas TEST Tbk (TEST)

Kode dan Nama Saham : TEST - TEST Tbk
1. Akhir perdagangan saham dengan Nilai Nominal Lama di Pasar Reguler dan Pasar Negosiasi 14 April 2026
2. Mulai perdagangan saham dengan Nilai Nominal Baru di Pasar Reguler dan Pasar Negosiasi 15 April 2026
4. Tanggal Penentuan pemegang saham yang berhak atas hasil Stock Split (Recording Date) 17 April 2026
5. Tanggal distribusi saham dengan Nilai Nominal Baru 20 April 2026
"""
    parsed = parse_ksei_schedule_transition(text)
    assert parsed.parse_status == "PARSED_EXACT_TRANSITION"
    assert parsed.event_family == "STOCK_SPLIT"
    assert parsed.transition_date == "2026-04-15"
    assert parsed.transition_semantic == "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"


def test_record_distribution_only_never_become_transition_fallback():
    text = """
Nomor : KSEI-77777/JKU/0426 14 April 2026
Perihal : Informasi Mandatory Conversion TEST Tbk (TEST)

Kode dan Nama Saham : TEST - TEST Tbk
Tanggal Pencatatan (Recording Date) 17 April 2026
Tanggal Distribusi 20 April 2026
"""
    parsed = parse_ksei_schedule_transition(text)
    assert parsed.parse_status == "UNRESOLVED"
    assert parsed.transition_date is None
    assert "NO_EXPLICIT_REGULAR_MARKET_TRANSITION" in parsed.diagnostics


def test_bonus_share_ex_date_is_admitted():
    text = """
Number : KSEI-8070/JKU/0426 16 April 2026
Re : Distribution Schedule of HARTA DJAYA KARYA Tbk, PT (TEST) Bonus Shares

Shares Code and Name : TEST - HARTA DJAYA KARYA Tbk
1. Bonus Shares Cum-Date at the Regular Market and Negotiated Market 16 April 2026
2. Bonus Shares Ex-Date at the Regular Market and Negotiated Market 17 April 2026
5. Recording Date 20 April 2026
6. Bonus Shares Distribution Date 8 May 2026
"""
    parsed = parse_ksei_schedule_transition(text)
    assert parsed.parse_status == "PARSED_EXACT_TRANSITION"
    assert parsed.event_family == "BONUS_SHARES"
    assert parsed.transition_date == "2026-04-17"
