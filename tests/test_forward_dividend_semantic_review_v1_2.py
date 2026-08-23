from __future__ import annotations

from decimal import Decimal

import pytest

from idx_trade.forward_dividend_semantic_review_v1 import (
    DividendSemanticReviewError,
)
from idx_trade.forward_dividend_semantic_review_v1_2 import (
    _amount_mode_and_values,
    _material_non_cash_subject,
    _parse_per_share_number,
    analyze_cash_dividend_documents_v1_2,
    extract_cash_dividend_schedule_v1_2,
    normalize_text,
)


SCHEDULE = """
BBCA
Dividen Tunai
Tanggal Cum Dividen Pasar Reguler dan Pasar Negosiasi
20 April 2026
Tanggal Ex Dividen Pasar Reguler dan Pasar Negosiasi
21 April 2026
Record Date 22 April 2026
Tanggal Pembayaran Dividen 8 Mei 2026
"""


def amount(text: str) -> tuple[str, set[str]]:
    return _amount_mode_and_values(
        [normalize_text(text)]
    )


def test_bbca_parenthetical_amount() -> None:
    mode, values = amount(
        "dividen interim tunai sebesar "
        "Rp 55,00 (lima puluh lima rupiah) "
        "per saham"
    )

    assert mode == "GENERIC_PER_SHARE"
    assert values == {"55"}


def test_bbri_dash_amount() -> None:
    mode, values = amount(
        "Dividen Interim sebesar "
        "Rp137,- (Seratus Tiga Puluh Tujuh Rupiah) "
        "per lembar saham"
    )

    assert mode == "GENERIC_PER_SHARE"
    assert values == {"137"}


def test_zero_leading_three_digit_separator_is_decimal_not_thousands():
    assert _parse_per_share_number("0,125") == Decimal("0.125")
    assert _parse_per_share_number("0.125") == Decimal("0.125")


def test_nonzero_single_three_digit_separator_is_ambiguous():
    with pytest.raises(
        DividendSemanticReviewError,
        match="AMBIGUOUS_THREE_DIGIT_SEPARATOR",
    ):
        _parse_per_share_number("123,456")


def test_multi_separator_grouping_remains_supported():
    assert _parse_per_share_number("1.234.567") == Decimal("1234567")


def test_bbca_final_prefers_remaining_payable() -> None:
    mode, values = amount(
        "cash dividends of Rp336.00 per share, "
        "including interim cash dividends "
        "at Rp55.00 per share already paid, "
        "therefore the remaining cash dividends "
        "will be paid at Rp281.00 per share"
    )

    assert mode == "REMAINING_PAYABLE"
    assert values == {"281"}


def test_bbri_final_prefers_remaining_payable() -> None:
    mode, values = amount(
        "Dividen Tunai sebesar Rp346,00 per saham. "
        "Termasuk Dividen Interim sebesar "
        "Rp137,00 per saham. "
        "Dengan demikian, sisa jumlah Dividen Tunai "
        "yang akan dibayarkan sebesar "
        "Rp209,00 per saham."
    )

    assert mode == "REMAINING_PAYABLE"
    assert values == {"209"}


def test_tlkm_high_precision_idx_field() -> None:
    mode, values = amount(
        "Dividen Per Saham "
        "(Jika sudah ada kepastian jumlah saham "
        "yang akan dibagi) IDR 223,1658777 "
        "Jadwal pembagian dividen"
    )

    assert mode == "IDX_PER_SHARE_FIELD"
    assert values == {"223.1658777"}


def test_regulatory_stock_dividend_reference_is_ignored() -> None:
    text = normalize_text(
        "Peraturan Bursa dan Surat Keputusan Direksi "
        "tentang Perubahan Ketentuan Pelaksanaan "
        "Pembagian Dividen Saham, Pembagian Saham Bonus "
        "dan Pembagian Dividen Interim."
    )

    assert (
        _material_non_cash_subject(text)
        is False
    )


def test_actual_stock_dividend_subject_still_fails_closed() -> None:
    text = normalize_text(
        "Perseroan akan melakukan pembagian "
        "dividen saham kepada pemegang saham."
    )

    assert (
        _material_non_cash_subject(text)
        is True
    )


def test_partial_schedule_can_exist_without_amount() -> None:
    schedule = (
        extract_cash_dividend_schedule_v1_2(
            [SCHEDULE]
        )
    )

    assert schedule == (
        "2026-04-20",
        "2026-04-21",
        "2026-04-22",
        "2026-05-08",
    )


def test_full_analysis_uses_remaining_amount() -> None:
    text = (
        SCHEDULE
        + """
        Perseroan akan membagikan Dividen Tunai
        sebesar Rp346,00 per saham.
        Jumlah tersebut termasuk Dividen Interim
        sebesar Rp137,00 per saham.
        Dengan demikian, sisa jumlah Dividen Tunai
        yang akan dibayarkan sebesar
        Rp209,00 per saham.
        """
    )

    result = (
        analyze_cash_dividend_documents_v1_2(
            [text],
            ticker="BBCA",
        )
    )

    assert (
        result.gross_dividend_per_share_idr
        == "209"
    )
    assert result.cum_regular_negotiated == "2026-04-20"
    assert result.payment_date == "2026-05-08"


def test_structured_and_direct_attachments_can_contribute_same_event():
    structured = """
    BBRI Dividen Tunai Interim
    Dividen per saham
    20.633.761.718.348 IDR Tidak 137 IDR
    Jadwal pembagian dividen:
    Tanggal Daftar Pemegang Saham (DPS) yang berhak atas dividen tunai
    Tanggal Cum Dividen di Pasar Reguler dan Pasar Negosiasi
    Tanggal Ex Dividen di Pasar Reguler dan Pasar Negosiasi
    Tanggal Cum Dividen di Pasar Tunai
    Tanggal Ex Dividen di Pasar Tunai
    Tanggal Pembayaran Dividen
    02 Januari 2026 Waktu 16:00
    29 Desember 2025
    30 Desember 2025
    02 Januari 2026
    05 Januari 2026
    15 Januari 2026
    """
    english = """
    BBRI Interim Dividend Rp137 per share.
    """

    result = analyze_cash_dividend_documents_v1_2(
        [structured, english],
        ticker="BBRI",
    )

    assert result.gross_dividend_per_share_idr == "137"
    assert result.contributing_document_count == 1
    assert result.cum_regular_negotiated == "2025-12-29"
    assert result.payment_date == "2026-01-15"


def test_no_per_share_amount_remains_unresolved() -> None:
    text = (
        SCHEDULE
        + """
        Total Nilai Dividen IDR
        21.999.902.180.685
        Dividen Per Saham
        Jadwal pembagian dividen
        """
    )

    with pytest.raises(
        DividendSemanticReviewError,
        match="AMOUNT_NOT_UNIQUE",
    ):
        analyze_cash_dividend_documents_v1_2(
            [text],
            ticker="BBCA",
        )

# --- STEP 4D2B R2 REAL-EVIDENCE REGRESSIONS ---


# --- STEP 4D2B R2 REAL-EVIDENCE REGRESSIONS ---


def test_r2_local_per_share_syntax_beats_aggregate_payout():
    from idx_trade.forward_dividend_semantic_review_v1_2 import (
        _amount_mode_and_values,
        normalize_text,
    )

    text = normalize_text(
        """
        Perseroan akan melaksanakan pembagian dividen interim
        sebesar Rp25,00 per lembar saham.

        Total Nilai Dividen
        Dividen per saham
        3.071.043.782.500
        IDR
        Tidak
        25
        IDR
        """
    )

    mode, values = _amount_mode_and_values(
        [text]
    )

    assert mode == "GENERIC_PER_SHARE"
    assert values == {"25"}

def test_r2_structured_field_rejects_aggregate_and_selects_dps():
    from idx_trade.forward_dividend_semantic_review_v1_2 import (
        _amount_mode_and_values,
        normalize_text,
    )

    text = normalize_text(
        """
        BBRI Dividen Tunai Interim.

        Total Nilai Dividen sekurang-kurangnya
        Dividen per saham
        20.633.761.718.348
        IDR
        Tidak
        137
        IDR
        IDR
        20.632.254.718.348
        """
    )

    mode, values = _amount_mode_and_values([text])

    assert mode == "IDX_PER_SHARE_FIELD"
    assert values == {"137"}


def test_r2_ordered_idx_schedule_form_maps_regular_market_dates():
    from idx_trade.forward_dividend_semantic_review_v1_2 import (
        _r2_schedule_from_ordered_idx_form,
        normalize_text,
    )

    text = normalize_text(
        """
        Jadwal pembagian dividen:

        Tanggal Daftar Pemegang Saham (DPS) yang berhak
        atas dividen tunai

        Tanggal Cum Dividen di Pasar Reguler dan
        Pasar Negosiasi

        Tanggal Ex Dividen di Pasar Reguler dan
        Pasar Negosiasi

        Tanggal Cum Dividen di Pasar Tunai

        Tanggal Ex Dividen di Pasar Tunai

        Tanggal Pembayaran Dividen

        02 Januari 2026 Waktu 16:00
        29 Desember 2025
        30 Desember 2025
        02 Januari 2026
        05 Januari 2026
        15 Januari 2026
        """
    )

    assert _r2_schedule_from_ordered_idx_form(
        text
    ) == (
        "2025-12-29",
        "2025-12-30",
        "2026-01-02",
        "2026-01-15",
    )


def test_r2_remaining_payable_still_has_priority():
    from idx_trade.forward_dividend_semantic_review_v1_2 import (
        _amount_mode_and_values,
        normalize_text,
    )

    text = normalize_text(
        """
        BBRI akan membagikan dividen tunai sebesar
        Rp52.102.414.608.484,00 atau sebesar
        Rp346,00 per saham.

        Termasuk dividen interim sebesar
        Rp137,00 per saham yang telah dibayarkan.

        Dengan demikian, sisa jumlah Dividen Tunai yang
        akan dibayarkan kepada Pemegang Saham sebesar
        Rp31.470.159.890.136,00 atau sebesar
        Rp209,00 per saham.
        """
    )

    mode, values = _amount_mode_and_values([text])

    assert mode == "REMAINING_PAYABLE"
    assert values == {"209"}


def test_r2_high_precision_structured_dps():
    from idx_trade.forward_dividend_semantic_review_v1_2 import (
        _amount_mode_and_values,
        normalize_text,
    )

    text = normalize_text(
        """
        TLKM Dividen Tunai

        Total Value of Dividend IDR
        21.999.902.180.685

        Dividend per share
        (if the receiving number of shares has been determined)
        IDR 223,1658777

        Dividend distribution schedule
        """
    )

    mode, values = _amount_mode_and_values([text])

    assert mode == "IDX_PER_SHARE_FIELD"
    assert values == {
        "223.1658777"
    }


def test_r2_ordered_form_tlkm_schedule():
    from idx_trade.forward_dividend_semantic_review_v1_2 import (
        _r2_schedule_from_ordered_idx_form,
        normalize_text,
    )

    text = normalize_text(
        """
        Tanggal Daftar Pemegang Saham (DPS) yang berhak
        atas dividen tunai
        Tanggal Cum Dividen di Pasar Reguler dan Pasar Negosiasi
        Tanggal Ex Dividen di Pasar Reguler dan Pasar Negosiasi
        Tanggal Cum Dividen di Pasar Tunai
        Tanggal Ex Dividen di Pasar Tunai
        Tanggal Pembayaran Dividen

        19 Juni 2026 Waktu 16:00
        17 Juni 2026
        18 Juni 2026
        19 Juni 2026
        22 Juni 2026
        10 Juli 2026
        """
    )

    assert _r2_schedule_from_ordered_idx_form(
        text
    ) == (
        "2026-06-17",
        "2026-06-18",
        "2026-06-19",
        "2026-07-10",
    )
