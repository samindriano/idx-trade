from idx_trade.v4_ca_targeted_schedule_linkage_remediation import (
    explicit_date_set,
    frozen_source_dates_contained,
    two_line_stock_split_transition,
)


def test_two_line_cuan_stock_split_transition():
    text = """
di Pasar Reguler dan Pasar Negosiasi 14 Juli 2025
2. Mulai perdagangan saham dengan Nilai Nominal Baru (Nominal Rp 20,- per saham) 15 Juli 2025
di Pasar Reguler dan Pasar Negosiasi
Tanggal Pencatatan (Recording Date) 16 Juli 2025
Tanggal distribusi saham dengan Nilai Nominal Baru Rp 20,- 17 Juli 2025
"""
    transition, diagnostics = two_line_stock_split_transition(text)
    assert transition == "2025-07-15"
    assert diagnostics == ()
    dates = explicit_date_set(text)
    assert frozen_source_dates_contained(
        ["2025-07-14", "2025-07-16", "2025-07-17"], dates
    )


def test_two_line_isat_stock_split_transition():
    text = """
di Pasar Reguler dan Pasar Negosiasi 11 Oktober 2024
2. Mulai perdagangan saham dengan Nilai Nominal Baru (Nominal Rp 25,- per saham) 14 Oktober 2024
di Pasar Reguler dan Pasar Negosiasi
Tanggal Pencatatan (Recording Date) 15 Oktober 2024
Tanggal distribusi saham dengan Nilai Nominal Baru Rp 25,- 16 Oktober 2024
"""
    transition, diagnostics = two_line_stock_split_transition(text)
    assert transition == "2024-10-14"
    assert diagnostics == ()
    assert frozen_source_dates_contained(
        ["2024-10-11", "2024-10-15", "2024-10-16"], explicit_date_set(text)
    )


def test_two_line_ptro_and_raja_wrapped_di_transition():
    ptro = """
2. Mulai perdagangan saham dengan Nilai Nominal Baru (Nominal Rp 5,- per saham) di 3 Januari 2025
Pasar Reguler dan Pasar Negosiasi
"""
    raja = """
2. Mulai perdagangan saham dengan Nilai Nominal Baru (Nominal Rp 5,- per saham) di 16 Juli 2026
Pasar Reguler dan Pasar Negosiasi
"""
    assert two_line_stock_split_transition(ptro) == ("2025-01-03", ())
    assert two_line_stock_split_transition(raja) == ("2026-07-16", ())


def test_detached_flat_date_list_stays_unresolved():
    text = """
2. Mulai perdagangan saham dengan Nilai Nominal Baru (Nominal Rp 25,- per saham)
di Pasar Reguler dan Pasar Negosiasi
11 Oktober 2024 14 Oktober 2024 15 Oktober 2024 16 Oktober 2024
"""
    transition, diagnostics = two_line_stock_split_transition(text)
    assert transition is None
    assert diagnostics == ("NO_EXACT_TWO_LINE_STOCK_SPLIT_TRANSITION",)


def test_full_source_date_set_is_required():
    dates = {"2025-07-14", "2025-07-15", "2025-07-16"}
    assert not frozen_source_dates_contained(
        ["2025-07-14", "2025-07-16", "2025-07-17"], dates
    )
