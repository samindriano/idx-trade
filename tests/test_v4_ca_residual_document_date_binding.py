from __future__ import annotations

from idx_trade.v4_ca_residual_document_semantics_hardened import (
    layout_bound_dates,
    parse_residual_document_hardened,
)


def test_payment_row_binds_same_line_date():
    parsed = parse_residual_document_hardened(
        "Penawaran Tender Sukarela saham ABCD",
        expected_ticker="ABCD",
        layout_text="Tanggal Pembayaran hasil Penawaran Tender 15 April 2026",
    )
    assert parsed.payment_dates == ("2026-04-15",)


def test_payment_row_binds_safe_continuation_date():
    parsed = parse_residual_document_hardened(
        "Penawaran Tender Wajib saham ABCD",
        expected_ticker="ABCD",
        layout_text="Tanggal Pembayaran\n15 April 2026",
    )
    assert parsed.payment_dates == ("2026-04-15",)


def test_payment_row_cannot_steal_record_date():
    parsed = parse_residual_document_hardened(
        "Penawaran Tender Sukarela saham ABCD",
        expected_ticker="ABCD",
        layout_text="Tanggal Pembayaran\nTanggal Pencatatan 15 April 2026",
    )
    assert parsed.payment_dates == ()
    assert parsed.record_date == "2026-04-15"


def test_record_row_cannot_steal_distribution_date():
    parsed = parse_residual_document_hardened(
        "Stock Split saham ABCD",
        expected_ticker="ABCD",
        layout_text="Tanggal Pencatatan\nTanggal Distribusi 8 Juli 2024",
    )
    assert parsed.record_date is None
    assert parsed.distribution_date == "2024-07-08"


def test_first_new_basis_cannot_steal_record_date():
    parsed = parse_residual_document_hardened(
        "Stock Split saham ABCD",
        expected_ticker="ABCD",
        layout_text=(
            "Mulai perdagangan saham dengan Nilai Nominal Baru di Pasar Reguler\n"
            "Tanggal Pencatatan 8 Juli 2024"
        ),
    )
    assert parsed.transition_date is None
    assert parsed.record_date == "2024-07-08"


def test_first_new_basis_same_line_is_admitted():
    parsed = parse_residual_document_hardened(
        "Stock Split saham ABCD",
        expected_ticker="ABCD",
        layout_text=(
            "Mulai perdagangan saham dengan Nilai Nominal Baru di Pasar Reguler 4 Juli 2024\n"
            "Tanggal Pencatatan 5 Juli 2024\n"
            "Tanggal Distribusi 8 Juli 2024"
        ),
    )
    assert parsed.transition_date == "2024-07-04"
    assert parsed.transition_semantic == "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"
    assert parsed.record_date == "2024-07-05"
    assert parsed.distribution_date == "2024-07-08"


def test_multiple_payment_dates_in_one_document_fail_closed():
    bound, diagnostics = layout_bound_dates(
        "Tanggal Pembayaran 15 April 2026\nTanggal Pembayaran 16 April 2026"
    )
    assert bound["PAYMENT_DATE"] == ()
    assert "CONFLICTING_LAYOUT_DATES:PAYMENT_DATE" in diagnostics


def test_plain_text_proximity_date_is_not_used_when_layout_unbound():
    parsed = parse_residual_document_hardened(
        "Penawaran Tender Sukarela saham ABCD Tanggal Pembayaran xxxxxxxxx 15 April 2026",
        expected_ticker="ABCD",
        layout_text="Tanggal Pembayaran\nTanggal Pencatatan 15 April 2026",
    )
    assert parsed.payment_dates == ()
