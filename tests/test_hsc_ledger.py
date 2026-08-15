from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from idx_trade.hsc_ledger import (
    HSCActiveState,
    HSCEvent,
    HSCMethodologyVersion,
    HSCRevisionKind,
    HSCStatus,
    replay_hsc_events,
    validate_active_reconciliation,
)


TZ = timezone(timedelta(hours=7))


def _sha(digit: int) -> str:
    return str(digit % 10) * 64


def _event(
    index: int,
    *,
    ticker: str = "BREN",
    kind: HSCRevisionKind = HSCRevisionKind.ORIGINAL,
    status: HSCStatus = HSCStatus.ACTIVE,
    supersedes: str | None = None,
    concentration_pct: float | None = 97.3,
    day: int = 2,
    methodology: HSCMethodologyVersion = HSCMethodologyVersion.INITIAL_2026,
) -> HSCEvent:
    return HSCEvent(
        event_id=f"event-{index}",
        ticker=ticker,
        status=status,
        ownership_as_of_date=date(2026, 3, 31),
        published_at=datetime(2026, 4, day, 18, 0, tzinfo=TZ),
        concentration_pct=concentration_pct,
        methodology_version=methodology,
        idx_announcement_no=f"Peng-{index:05d}-HSC/BEI.WAS/04-2026",
        ksei_announcement_no=f"KSEI-{index:04d}/DIR/0426",
        revision_kind=kind,
        supersedes_event_id=supersedes,
        source_url=f"https://www.idx.id/StaticData/{index}.pdf",
        source_sha256=_sha(index),
        metadata_source_sha256=_sha(index + 4),
    )


def test_original_correction_and_removal_preserve_pit_state() -> None:
    original = _event(1)
    correction = _event(
        2,
        kind=HSCRevisionKind.CORRECTION,
        supersedes="event-1",
        concentration_pct=98.0,
        day=3,
    )
    removal = _event(
        3,
        kind=HSCRevisionKind.REMOVAL,
        status=HSCStatus.REMOVED,
        concentration_pct=None,
        day=4,
    )

    final = replay_hsc_events([removal, correction, original])
    assert final.active_tickers == frozenset()

    before_removal = replay_hsc_events(
        [removal, correction, original],
        cutoff=datetime(2026, 4, 3, 23, 0, tzinfo=TZ),
    )
    state = before_removal.active["BREN"]
    assert state.concentration_pct == 98.0
    assert state.active_since == original.published_at
    assert state.last_event_id == correction.event_id


def test_duplicate_active_addition_fails_closed() -> None:
    with pytest.raises(ValueError, match="duplicate active addition"):
        replay_hsc_events([_event(1), _event(2, day=3)])


def test_removal_of_inactive_ticker_fails_closed() -> None:
    with pytest.raises(ValueError, match="removal of inactive ticker"):
        replay_hsc_events(
            [
                _event(
                    1,
                    kind=HSCRevisionKind.REMOVAL,
                    status=HSCStatus.REMOVED,
                    concentration_pct=None,
                )
            ]
        )


def test_unknown_or_ambiguous_correction_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown/not-yet-published"):
        replay_hsc_events(
            [
                _event(
                    2,
                    kind=HSCRevisionKind.CORRECTION,
                    supersedes="event-1",
                )
            ]
        )

    first = _event(1)
    corrected = _event(
        2,
        kind=HSCRevisionKind.CORRECTION,
        supersedes="event-1",
        day=3,
    )
    stale_second_correction = _event(
        3,
        kind=HSCRevisionKind.CORRECTION,
        supersedes="event-1",
        day=4,
    )
    with pytest.raises(ValueError, match="lineage is ambiguous"):
        replay_hsc_events([first, corrected, stale_second_correction])


def test_active_reconciliation_requires_exact_ticker_set() -> None:
    replay = replay_hsc_events(
        [
            _event(1, ticker="BREN"),
            _event(2, ticker="AGII", day=3),
        ]
    )
    validate_active_reconciliation(replay, ["AGII", "BREN"])

    with pytest.raises(ValueError, match="missing=.*DCII"):
        validate_active_reconciliation(replay, ["AGII", "BREN", "DCII"])


def test_naive_knowledge_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        HSCEvent(
            event_id="event-naive",
            ticker="BREN",
            status=HSCStatus.ACTIVE,
            ownership_as_of_date=date(2026, 3, 31),
            published_at=datetime(2026, 4, 2, 18, 0),
            concentration_pct=97.0,
            methodology_version=HSCMethodologyVersion.INITIAL_2026,
            idx_announcement_no="Peng-00001-HSC/BEI.WAS/04-2026",
            ksei_announcement_no="KSEI-2148/DIR/0426",
            revision_kind=HSCRevisionKind.ORIGINAL,
            supersedes_event_id=None,
            source_url="https://www.idx.id/StaticData/x.pdf",
            source_sha256="a" * 64,
            metadata_source_sha256="b" * 64,
        )


def test_contract_does_not_infer_free_float_or_effective_supply() -> None:
    fields = set(HSCActiveState.__dataclass_fields__)
    assert "free_float_pct" not in fields
    assert "effective_free_float_pct" not in fields
    assert "effective_supply" not in fields
