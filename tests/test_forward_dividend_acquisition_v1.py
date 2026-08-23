from __future__ import annotations

import pytest

import idx_trade.forward_dividend_acquisition_v1 as acquisition


def _reply(
    *,
    ticker: str = "BBCA",
    title: str,
    announcement_id: str = "A1",
    number: str = "N1",
    attachments: bool = True,
):
    return {
        "pengumuman": {
            "Kode_Emiten": ticker,
            "JudulPengumuman": title,
            "Id2": announcement_id,
            "NoPengumuman": number,
            "CreatedDate": "2026-08-19T18:31:03",
            "Form_Id": "11000",
        },
        "attachments": (
            [
                {
                    "PDFFilename": "one.pdf",
                    "FullSavePath": (
                        "https://www.idx.co.id/StaticData/"
                        "NewsAndAnnouncement/one.pdf"
                    ),
                    "OriginalFilename": "one.pdf",
                    "IsAttachment": True,
                }
            ]
            if attachments
            else []
        ),
    }


def test_cash_dividend_candidate_is_discovered() -> None:
    payload = {
        "Replies": [
            _reply(title="Jadwal Dividen Tunai Interim")
        ],
        "ResultCount": 1,
    }

    rows = acquisition.extract_dividend_candidates(
        payload,
        expected_ticker="BBCA",
    )

    assert len(rows) == 1
    assert rows[0].ticker == "BBCA"
    assert (
        rows[0].classification
        == acquisition.CASH_DIVIDEND_CANDIDATE
    )
    assert len(rows[0].attachments) == 1


def test_generic_dividend_is_conservatively_ambiguous() -> None:
    payload = {
        "Replies": [
            _reply(title="Pengumuman Dividen")
        ]
    }

    rows = acquisition.extract_dividend_candidates(
        payload,
        expected_ticker="BBCA",
    )

    assert len(rows) == 1
    assert (
        rows[0].classification
        == acquisition.AMBIGUOUS_DIVIDEND_CANDIDATE
    )


def test_stock_dividend_is_not_promoted_to_cash() -> None:
    payload = {
        "Replies": [
            _reply(title="Pembagian Dividen Saham")
        ]
    }

    rows = acquisition.extract_dividend_candidates(
        payload,
        expected_ticker="BBCA",
    )

    assert len(rows) == 1
    assert (
        rows[0].classification
        == acquisition.UNSUPPORTED_NON_CASH_DIVIDEND
    )


def test_unrelated_announcement_is_ignored() -> None:
    payload = {
        "Replies": [
            _reply(title="Laporan Informasi Material")
        ]
    }

    rows = acquisition.extract_dividend_candidates(
        payload,
        expected_ticker="BBCA",
    )

    assert rows == ()


def test_response_ticker_mismatch_fails_closed() -> None:
    payload = {
        "Replies": [
            _reply(
                ticker="BBRI",
                title="Jadwal Dividen Tunai",
            )
        ]
    }

    with pytest.raises(
        acquisition.ForwardDividendAcquisitionError,
        match="RESPONSE_TICKER_MISMATCH",
    ):
        acquisition.extract_dividend_candidates(
            payload,
            expected_ticker="BBCA",
        )


def test_security_class_suffix_is_excluded_from_common_share_candidates() -> None:
    for ticker in ("BBCA-R", "BBCA PENGUMUMAN HT STOCK SPLIT", "C-BBCA"):
        payload = {
            "Replies": [
                _reply(
                    ticker=ticker,
                    title="Jadwal Dividen Tunai",
                )
            ],
            "ResultCount": 1,
        }

        assert (
            acquisition.extract_dividend_candidates(
                payload,
                expected_ticker="BBCA",
            )
            == ()
        )


def test_duplicate_identity_conflict_fails_closed() -> None:
    payload = {
        "Replies": [
            _reply(
                title="Jadwal Dividen Tunai",
                announcement_id="A1",
            ),
            _reply(
                title="Jadwal Dividen Tunai Interim",
                announcement_id="A1",
            ),
        ]
    }

    with pytest.raises(
        acquisition.ForwardDividendAcquisitionError,
        match="DUPLICATE_ANNOUNCEMENT_CONFLICT",
    ):
        acquisition.extract_dividend_candidates(
            payload,
            expected_ticker="BBCA",
        )


def test_invalid_schema_fails_closed() -> None:
    with pytest.raises(
        acquisition.ForwardDividendAcquisitionError,
        match="REPLIES_NOT_LIST",
    ):
        acquisition.extract_dividend_candidates(
            {},
            expected_ticker="BBCA",
        )

def test_tgl_pengumuman_precedes_created_date() -> None:
    payload = {
        "Replies": [
            {
                "pengumuman": {
                    "Kode_Emiten": "BBCA",
                    "JudulPengumuman": "Jadwal Dividen Tunai Interim",
                    "Id2": "A1",
                    "NoPengumuman": "N1",
                    "TglPengumuman": "2026-08-19T18:31:03",
                    "CreatedDate": "2026-08-19T19:00:02",
                    "Form_Id": "11000",
                },
                "attachments": [],
            }
        ]
    }

    rows = acquisition.extract_dividend_candidates(
        payload,
        expected_ticker="BBCA",
    )

    assert len(rows) == 1
    assert (
        rows[0].announcement_timestamp
        == "2026-08-19T18:31:03"
    )
