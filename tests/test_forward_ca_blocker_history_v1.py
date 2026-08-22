from __future__ import annotations

import pytest

from idx_trade.forward_ca_blocker_history_v1 import (
    BLOCKED,
    RESOLVED_CERTIFIED,
    RESOLVED_SUPERSEDED,
    CABlockerHistoryEntry,
    ForwardCABlockerHistoryError,
    append_blocker_resolution_history,
    blocker_history_payload,
    blocker_history_sha256,
)
from idx_trade.forward_dividend_disposition_v1_2 import (
    BLOCKED_LIVE_UNRESOLVED,
    CERTIFIED_LIVE,
    SUPERSEDED,
    DividendDisposition,
    DividendDispositionResult,
)


def _result(*dispositions: DividendDisposition) -> DividendDispositionResult:
    return DividendDispositionResult(
        dispositions=dispositions,
        live_events=(),
        blockers=tuple(
            row for row in dispositions if row.category == BLOCKED_LIVE_UNRESOLVED
        ),
    )


def _blocked(identity: str = "BBCA|NUMBER|A") -> DividendDisposition:
    return DividendDisposition(
        announcement_identity=identity,
        ticker=identity.split("|", 1)[0],
        category=BLOCKED_LIVE_UNRESOLVED,
        reason="NO_CERTIFIED_EVENT_OR_DEFENSIBLE_LINEAGE",
        event_id=None,
        event_sha256=None,
    )


def _certified(identity: str = "BBCA|NUMBER|A") -> DividendDisposition:
    return DividendDisposition(
        announcement_identity=identity,
        ticker=identity.split("|", 1)[0],
        category=CERTIFIED_LIVE,
        reason="CERTIFIED_EVENT_RELEVANT_AT_AS_OF",
        event_id="EVENT-A",
        event_sha256="a" * 64,
    )


def test_same_identity_resolves_across_query_windows_without_rekeying():
    first = append_blocker_resolution_history(
        (),
        batch_id="2026-08-22_POST_EOD",
        as_of_date="2026-08-22",
        query_window_from="2026-08-01",
        query_window_to="2026-08-22",
        result=_result(_blocked()),
    )
    second = append_blocker_resolution_history(
        first,
        batch_id="2026-08-29_POST_EOD",
        as_of_date="2026-08-29",
        query_window_from="2026-08-15",
        query_window_to="2026-08-29",
        result=_result(_certified()),
    )

    assert [(row.announcement_identity, row.status) for row in second] == [
        ("BBCA|NUMBER|A", BLOCKED),
        ("BBCA|NUMBER|A", RESOLVED_CERTIFIED),
    ]
    assert second[0].query_window_from == "2026-08-01"
    assert second[1].query_window_from == "2026-08-15"
    assert second[1].event_id == "EVENT-A"


def test_window_omission_does_not_resolve_an_open_blocker():
    first = append_blocker_resolution_history(
        (),
        batch_id="B1",
        as_of_date="2026-08-22",
        query_window_from="2026-08-01",
        query_window_to="2026-08-22",
        result=_result(_blocked()),
    )
    second = append_blocker_resolution_history(
        first,
        batch_id="B2",
        as_of_date="2026-08-29",
        query_window_from="2026-08-23",
        query_window_to="2026-08-29",
        result=_result(),
    )

    assert second == first
    assert second[-1].status == BLOCKED


def test_different_identity_does_not_resolve_prior_blocker():
    first = append_blocker_resolution_history(
        (),
        batch_id="B1",
        as_of_date="2026-08-22",
        query_window_from="2026-08-01",
        query_window_to="2026-08-22",
        result=_result(_blocked()),
    )
    second = append_blocker_resolution_history(
        first,
        batch_id="B2",
        as_of_date="2026-08-29",
        query_window_from="2026-08-23",
        query_window_to="2026-08-29",
        result=_result(_certified("BBCA|NUMBER|B")),
    )

    assert second == first


def test_exact_batch_replay_is_idempotent_and_hash_stable():
    kwargs = {
        "batch_id": "B1",
        "as_of_date": "2026-08-22",
        "query_window_from": "2026-08-01",
        "query_window_to": "2026-08-22",
        "result": _result(_blocked()),
    }
    first = append_blocker_resolution_history((), **kwargs)
    replay = append_blocker_resolution_history(first, **kwargs)

    assert replay == first
    assert blocker_history_payload(replay) == blocker_history_payload(first)
    assert blocker_history_sha256(replay) == blocker_history_sha256(first)


def test_blocker_cannot_regress_after_certified_resolution():
    first = append_blocker_resolution_history(
        (),
        batch_id="B1",
        as_of_date="2026-08-22",
        query_window_from="2026-08-01",
        query_window_to="2026-08-22",
        result=_result(_blocked()),
    )
    resolved = append_blocker_resolution_history(
        first,
        batch_id="B2",
        as_of_date="2026-08-29",
        query_window_from="2026-08-23",
        query_window_to="2026-08-29",
        result=_result(_certified()),
    )

    with pytest.raises(
        ForwardCABlockerHistoryError,
        match="RESOLUTION_REGRESSED",
    ):
        append_blocker_resolution_history(
            resolved,
            batch_id="B3",
            as_of_date="2026-09-05",
            query_window_from="2026-08-30",
            query_window_to="2026-09-05",
            result=_result(_blocked()),
        )


def test_superseded_correction_resolves_prior_blocker():
    first = append_blocker_resolution_history(
        (),
        batch_id="B1",
        as_of_date="2026-08-22",
        query_window_from="2026-08-01",
        query_window_to="2026-08-22",
        result=_result(_blocked("TLKM|NUMBER|OLD")),
    )
    correction = DividendDisposition(
        announcement_identity="TLKM|NUMBER|OLD",
        ticker="TLKM",
        category=SUPERSEDED,
        reason="CORRECTION_CHAIN_RESOLVED_BY_LATER_CERTIFIED_EVIDENCE",
        event_id=None,
        event_sha256=None,
        superseded_by="TLKM|NUMBER|NEW",
    )
    second = append_blocker_resolution_history(
        first,
        batch_id="B2",
        as_of_date="2026-08-29",
        query_window_from="2026-08-23",
        query_window_to="2026-08-29",
        result=_result(correction),
    )

    assert second[-1].status == RESOLVED_SUPERSEDED
    assert second[-1].resolution_identity == "TLKM|NUMBER|NEW"


def test_same_identity_with_different_ticker_fails_closed():
    entry = CABlockerHistoryEntry(
        batch_id="B1",
        as_of_date="2026-08-22",
        query_window_from="2026-08-01",
        query_window_to="2026-08-22",
        announcement_identity="BBCA|NUMBER|A",
        ticker="BBCA",
        status=BLOCKED,
        disposition_category=BLOCKED_LIVE_UNRESOLVED,
        reason="blocked",
    )
    with pytest.raises(
        ForwardCABlockerHistoryError,
        match="IDENTITY_TICKER_MISMATCH",
    ):
        append_blocker_resolution_history(
            (entry, CABlockerHistoryEntry(
                batch_id="B2",
                as_of_date="2026-08-29",
                query_window_from="2026-08-23",
                query_window_to="2026-08-29",
                announcement_identity="BBCA|NUMBER|A",
                ticker="BBRI",
                status=BLOCKED,
                disposition_category=BLOCKED_LIVE_UNRESOLVED,
                reason="blocked",
            )),
            batch_id="B3",
            as_of_date="2026-09-05",
            query_window_from="2026-08-30",
            query_window_to="2026-09-05",
            result=_result(),
        )
