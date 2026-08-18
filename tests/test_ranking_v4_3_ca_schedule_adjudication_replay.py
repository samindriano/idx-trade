from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ranking_v4_3_ca_schedule_adjudication_replay import (
    apply_adjudication,
    replay_continuity,
)
from idx_trade.v4_ca_event_windows import EventSemantic


def _event(event_id: str, ticker: str, source_type: str) -> EventSemantic:
    return EventSemantic(
        event_id=event_id,
        ticker=ticker,
        source_type=source_type,
        family=source_type.upper().replace(" ", "_"),
        semantic_class="SCHEDULE_REQUIRED",
        transition_date=None,
        transition_source=None,
        reason="NEEDS_SCHEDULE",
        source_dates=(pd.Timestamp("2024-01-10"),),
    )


def _evidence(rows: list[dict[str, str]]) -> pd.DataFrame:
    defaults = {
        "event_source_type": "stock split",
        "linkage_status": "UNRESOLVED",
        "evidence_kind": "UNRESOLVED",
        "transition_date": "",
        "transition_semantic": "",
        "ksei_reference": "",
        "source_sha256": "",
        "linkage_basis": "NO_EXACT_ADMISSIBLE_DOCUMENT_LINK",
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def test_apply_exact_transition_and_keep_unresolved() -> None:
    parents = {
        ("e1", "AAA"): _event("e1", "AAA", "stock split"),
        ("e2", "BBB"): _event("e2", "BBB", "stock split"),
    }
    evidence = _evidence(
        [
            {
                "event_id": "e1",
                "ticker": "AAA",
                "linkage_status": "EXACT",
                "transition_date": "2024-01-15",
                "transition_semantic": "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
                "ksei_reference": "KSEI-1/ABC/0124",
                "source_sha256": "a" * 64,
                "linkage_basis": "EXACT_TEST",
            },
            {"event_id": "e2", "ticker": "BBB"},
        ]
    )
    updated, overlay = apply_adjudication(parents, evidence, expected_schedule_events=2)
    assert updated[("e1", "AAA")].semantic_class == "EXACT_TRANSITION"
    assert updated[("e1", "AAA")].transition_date == pd.Timestamp("2024-01-15")
    assert updated[("e2", "BBB")].semantic_class == "SCHEDULE_REQUIRED"
    assert set(overlay["replay_action"]) == {"ADMIT_EXACT_TRANSITION", "KEEP_UNRESOLVED"}


def test_exact_transition_still_blocks_crossing_window_only() -> None:
    parents = {("e1", "AAA"): _event("e1", "AAA", "stock split")}
    evidence = _evidence(
        [
            {
                "event_id": "e1",
                "ticker": "AAA",
                "linkage_status": "EXACT",
                "transition_date": "2024-01-15",
                "transition_semantic": "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
                "ksei_reference": "KSEI-1/ABC/0124",
                "source_sha256": "a" * 64,
            }
        ]
    )
    updated, _ = apply_adjudication(parents, evidence, expected_schedule_events=1)
    windows = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "signal_date": "2024-01-10",
                "signal_session_index": 1,
                "horizon": 5,
                "entry_date": "2024-01-11",
                "terminal_date": "2024-01-16",
            },
            {
                "ticker": "AAA",
                "signal_date": "2024-01-16",
                "signal_session_index": 2,
                "horizon": 5,
                "entry_date": "2024-01-17",
                "terminal_date": "2024-01-22",
            },
        ]
    )
    continuity = replay_continuity(
        windows,
        updated,
        unresolved_coverage_tickers=set(),
        missing_coverage_tickers=set(),
        cross_source_conflict_tickers=set(),
    )
    assert continuity.iloc[0]["continuity_reason"] == "TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION"
    assert continuity.iloc[1]["continuity_status"] == "RESOLVED_NO_MECHANICAL_DISCONTINUITY"


def test_nonblocking_requires_voluntary_conversion() -> None:
    parents = {("e1", "AAA"): _event("e1", "AAA", "stock split")}
    evidence = _evidence(
        [
            {
                "event_id": "e1",
                "ticker": "AAA",
                "linkage_status": "EXACT_NON_BLOCKING",
                "ksei_reference": "KSEI-1/ABC/0124",
                "source_sha256": "b" * 64,
            }
        ]
    )
    with pytest.raises(RuntimeError, match="ADJUDICATION_NONBLOCKING_NOT_VOLUNTARY"):
        apply_adjudication(parents, evidence, expected_schedule_events=1)


def test_voluntary_exact_nonblocking_is_admitted() -> None:
    parents = {("e1", "AAA"): _event("e1", "AAA", "voluntary conversion")}
    evidence = _evidence(
        [
            {
                "event_id": "e1",
                "ticker": "AAA",
                "event_source_type": "voluntary conversion",
                "linkage_status": "EXACT_NON_BLOCKING",
                "ksei_reference": "KSEI-1/ABC/0124",
                "source_sha256": "c" * 64,
            }
        ]
    )
    updated, _ = apply_adjudication(parents, evidence, expected_schedule_events=1)
    assert updated[("e1", "AAA")].semantic_class == "NON_BLOCKING"
    assert updated[("e1", "AAA")].transition_date is None
