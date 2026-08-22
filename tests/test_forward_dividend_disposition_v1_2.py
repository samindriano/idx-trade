from __future__ import annotations

import pytest

from idx_trade.forward_dividend_disposition_v1_2 import (
    BLOCKED_LIVE_UNRESOLVED,
    CERTIFIED_LIVE,
    CORROBORATING_ONLY,
    HISTORICAL_OBSERVED,
    SUPERSEDED,
    DividendDispositionCandidate,
    DividendDispositionError,
    apply_temporal_disposition,
)


def _candidate(
    *,
    identity: str,
    ticker: str = "BBCA",
    timestamp: str = "2026-08-19T18:31:03",
    title: str = "Jadwal Dividen Tunai Interim",
    event_id: str | None = "E1",
    event_sha: str | None = "a" * 64,
    amount: str | None = "25",
    docs: tuple[str, ...] = ("d" * 64,),
    payment: str | None = "2026-09-16",
) -> DividendDispositionCandidate:
    return DividendDispositionCandidate(
        announcement_identity=identity,
        ticker=ticker,
        announcement_timestamp=timestamp,
        title=title,
        event_id=event_id,
        event_sha256=event_sha,
        gross_dividend_per_share_idr=amount,
        cum_date="2026-08-28" if event_id else None,
        ex_date="2026-08-31" if event_id else None,
        record_date="2026-09-01" if event_id else None,
        payment_date=payment if event_id else None,
        document_sha256=docs,
    )


def test_completed_event_is_historical_and_future_event_is_live():
    result = apply_temporal_disposition(
        [
            _candidate(
                identity="BBCA|NUMBER|OLD",
                timestamp="2026-06-05T16:48:01",
                amount="20",
                payment="2026-06-26",
            ),
            _candidate(identity="BBCA|NUMBER|LIVE"),
        ],
        as_of_date="2026-08-22",
    )

    categories = {
        row.announcement_identity: row.category
        for row in result.dispositions
    }
    assert categories == {
        "BBCA|NUMBER|OLD": HISTORICAL_OBSERVED,
        "BBCA|NUMBER|LIVE": CERTIFIED_LIVE,
    }
    assert tuple(row.announcement_identity for row in result.live_events) == (
        "BBCA|NUMBER|LIVE",
    )


def test_advertisement_and_post_event_report_do_not_duplicate_payable_event():
    result = apply_temporal_disposition(
        [
            _candidate(
                identity="BBRI|NUMBER|ECONOMIC",
                ticker="BBRI",
                timestamp="2025-12-17T08:51:06",
                payment="2025-12-29",
            ),
            _candidate(
                identity="BBRI|NUMBER|ADVERTISEMENT",
                ticker="BBRI",
                timestamp="2025-12-18T10:00:00",
                title="Bukti Iklan Jadwal Pembagian Dividen Interim",
            ),
            _candidate(
                identity="BBRI|NUMBER|REPORT",
                ticker="BBRI",
                timestamp="2026-01-19T10:00:00",
                title="Laporan Pasca Pembayaran Dividen Interim",
                event_id=None,
                event_sha=None,
                amount=None,
                docs=(),
                payment=None,
            ),
        ],
        as_of_date="2026-08-22",
    )

    categories = {
        row.announcement_identity: row.category
        for row in result.dispositions
    }
    assert categories["BBRI|NUMBER|ECONOMIC"] == HISTORICAL_OBSERVED
    assert categories["BBRI|NUMBER|ADVERTISEMENT"] == CORROBORATING_ONLY
    assert categories["BBRI|NUMBER|REPORT"] == CORROBORATING_ONLY
    assert len(result.live_events) == 0


def test_unresolved_correction_predecessor_is_superseded_by_shared_document():
    shared = "f" * 64
    result = apply_temporal_disposition(
        [
            _candidate(
                identity="TLKM|NUMBER|PREDECESSOR",
                ticker="TLKM",
                timestamp="2026-06-10T23:49:47",
                title="Jadwal Dividen Tunai",
                event_id=None,
                event_sha=None,
                amount=None,
                docs=(shared,),
                payment=None,
            ),
            _candidate(
                identity="TLKM|NUMBER|CORRECTION",
                ticker="TLKM",
                timestamp="2026-06-19T13:51:49",
                title="Jadwal Dividen Tunai (KOREKSI)",
                event_id="TLKM-FINAL",
                event_sha="b" * 64,
                amount="223.1658777",
                docs=(shared, "e" * 64),
                payment="2026-07-10",
            ),
        ],
        as_of_date="2026-08-22",
    )

    categories = {
        row.announcement_identity: row
        for row in result.dispositions
    }
    assert categories["TLKM|NUMBER|PREDECESSOR"].category == SUPERSEDED
    assert categories["TLKM|NUMBER|PREDECESSOR"].superseded_by == (
        "TLKM|NUMBER|CORRECTION"
    )
    assert categories["TLKM|NUMBER|CORRECTION"].category == HISTORICAL_OBSERVED
    assert result.blockers == ()


def test_unresolved_live_candidate_is_an_execution_blocker():
    result = apply_temporal_disposition(
        [
            _candidate(
                identity="BBCA|NUMBER|UNRESOLVED",
                event_id=None,
                event_sha=None,
                amount=None,
                docs=(),
                payment=None,
            )
        ],
        as_of_date="2026-08-22",
    )

    assert result.dispositions[0].category == BLOCKED_LIVE_UNRESOLVED
    assert result.blockers[0].announcement_identity == (
        "BBCA|NUMBER|UNRESOLVED"
    )


def test_conflicting_live_correction_fails_closed():
    with pytest.raises(
        DividendDispositionError,
        match="CONFLICTING_LIVE_CORRECTION",
    ):
        apply_temporal_disposition(
            [
                _candidate(
                    identity="BBCA|NUMBER|ORIGINAL",
                    timestamp="2026-08-18T10:00:00",
                    amount="25",
                    docs=("a" * 64,),
                ),
                _candidate(
                    identity="BBCA|NUMBER|CORRECTION",
                    timestamp="2026-08-19T10:00:00",
                    title="Jadwal Dividen Tunai (KOREKSI)",
                    event_id="E2",
                    event_sha="b" * 64,
                    amount="30",
                    docs=("b" * 64,),
                ),
            ],
            as_of_date="2026-08-22",
        )


def test_same_economic_live_correction_replaces_original():
    result = apply_temporal_disposition(
        [
            _candidate(
                identity="BBCA|NUMBER|ORIGINAL",
                timestamp="2026-08-18T10:00:00",
                docs=("shared".ljust(64, "0"),),
            ),
            _candidate(
                identity="BBCA|NUMBER|CORRECTION",
                timestamp="2026-08-19T10:00:00",
                title="Jadwal Dividen Tunai (KOREKSI)",
                event_id="E2",
                event_sha="b" * 64,
                docs=("shared".ljust(64, "0"), "e" * 64),
            ),
        ],
        as_of_date="2026-08-22",
    )

    categories = {
        row.announcement_identity: row
        for row in result.dispositions
    }
    assert categories["BBCA|NUMBER|ORIGINAL"].category == SUPERSEDED
    assert categories["BBCA|NUMBER|CORRECTION"].category == CERTIFIED_LIVE
    assert tuple(row.event_id for row in result.live_events) == ("E2",)
