from __future__ import annotations

import pytest

from idx_trade.forward_dividend_semantic_review_v1 import (
    DividendSemanticReviewError,
    analyze_cash_dividend_documents,
)


INDONESIAN = """
PT BANK CENTRAL ASIA Tbk
BBCA
PENGUMUMAN JADWAL DAN TATA CARA PEMBAGIAN DIVIDEN INTERIM
Perseroan akan melaksanakan pembagian dividen interim sebesar
Rp25,00 per lembar saham.

2 Akhir Periode Perdagangan Saham Dengan Hak Dividen
(Cum Dividen)
Pasar Reguler dan Pasar Negosiasi
Pasar Tunai
28 Agustus 2026
1 September 2026

3 Awal Periode Perdagangan Saham Tanpa Hak Dividen
(Ex Dividen)
Pasar Reguler dan Pasar Negosiasi
Pasar Tunai
31 Agustus 2026
2 September 2026

4 Tanggal Daftar Pemegang Saham yang berhak atas Dividen
(Record Date)
1 September 2026

5 Tanggal Pembayaran Dividen Interim
16 September 2026
"""


ENGLISH = """
PT BANK CENTRAL ASIA Tbk
BBCA
ANNOUNCEMENT OF SCHEDULE AND PROCEDURE FOR INTERIM DIVIDENDS

The Company is going to distribute interim dividend of
Rp25,00 per share.

2 End of Trading Period for Shares with Dividend Rights
(Cum Dividends)
Regular Markets and Negotiated Markets
Cash Markets
August 28, 2026
September 1, 2026

3 Start of Trading Period for Shares without Dividend Rights
(Ex Dividends)
Regular Markets and Negotiated Markets
Cash Markets
August 31, 2026
September 2, 2026

4 Record Date to determine the Shareholders' Eligibility
for Dividends
September 1, 2026

5 Payment Date of Interim Dividends
September 16, 2026
"""


def test_indonesian_terms_are_extracted() -> None:
    result = analyze_cash_dividend_documents(
        [INDONESIAN],
        ticker="BBCA",
    )

    assert result.gross_dividend_per_share_idr == "25"
    assert result.cum_regular_negotiated == "2026-08-28"
    assert result.ex_regular_negotiated == "2026-08-31"
    assert result.record_date == "2026-09-01"
    assert result.payment_date == "2026-09-16"


def test_bilingual_duplicate_evidence_reaches_one_consensus() -> None:
    result = analyze_cash_dividend_documents(
        [INDONESIAN, ENGLISH],
        ticker="BBCA",
    )

    assert result.gross_dividend_per_share_idr == "25"
    assert result.cum_regular_negotiated == "2026-08-28"
    assert result.ex_regular_negotiated == "2026-08-31"
    assert result.record_date == "2026-09-01"
    assert result.payment_date == "2026-09-16"
    assert result.contributing_document_count == 2


def test_non_cash_term_fails_closed() -> None:
    with pytest.raises(
        DividendSemanticReviewError,
        match="NON_CASH_TERM_PRESENT",
    ):
        analyze_cash_dividend_documents(
            [INDONESIAN + " Pembagian dividen saham."],
            ticker="BBCA",
        )


def test_ticker_absence_fails_closed() -> None:
    with pytest.raises(
        DividendSemanticReviewError,
        match="TICKER_NOT_FOUND",
    ):
        analyze_cash_dividend_documents(
            [INDONESIAN.replace("BBCA", "")],
            ticker="BBCA",
        )


def test_conflicting_amount_fails_closed() -> None:
    conflict = ENGLISH.replace("Rp25,00", "Rp30,00")

    with pytest.raises(
        DividendSemanticReviewError,
        match="AMOUNT_NOT_UNIQUE",
    ):
        analyze_cash_dividend_documents(
            [INDONESIAN, conflict],
            ticker="BBCA",
        )


def test_conflicting_schedule_fails_closed() -> None:
    conflict = ENGLISH.replace(
        "August 28, 2026",
        "August 27, 2026",
    )

    with pytest.raises(
        DividendSemanticReviewError,
        match="SCHEDULE_NOT_UNIQUE",
    ):
        analyze_cash_dividend_documents(
            [INDONESIAN, conflict],
            ticker="BBCA",
        )


def test_missing_schedule_fails_closed() -> None:
    text = """
    BBCA
    Perseroan membagikan dividen interim sebesar
    Rp25,00 per lembar saham.
    """

    with pytest.raises(
        DividendSemanticReviewError,
        match="SCHEDULE_NOT_UNIQUE",
    ):
        analyze_cash_dividend_documents(
            [text],
            ticker="BBCA",
        )
