from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ranking_v4_3_ca_idx_adjudication_replay import apply_idx_adjudication
from idx_trade.v4_ca_event_windows import EventSemantic


def parent(source_type: str = "stock split") -> dict[tuple[str, str], EventSemantic]:
    event = EventSemantic(
        event_id="E1",
        ticker="ABCD",
        source_type=source_type,
        family="TEST",
        semantic_class="SCHEDULE_REQUIRED",
        transition_date=None,
        transition_source=None,
        reason="UNRESOLVED",
        source_dates=(pd.Timestamp("2024-01-10"),),
    )
    return {(event.event_id, event.ticker): event}


def evidence(status: str, *, source_type: str = "stock split") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "event_id": "E1",
            "ticker": "ABCD",
            "event_source_type": source_type,
            "linkage_status": status,
            "transition_date": "2024-01-11" if status == "EXACT" else "",
            "transition_semantic": "REGULAR_MARKET_EX_DATE" if status == "EXACT" else "",
            "official_reference": "IDX-REF-1" if status in {"EXACT", "EXACT_NON_BLOCKING"} else "",
            "source_sha256": "a" * 64 if status in {"EXACT", "EXACT_NON_BLOCKING"} else "",
            "linkage_basis": "EXACT_FROZEN_LINK",
        }
    ])


def test_exact_idx_transition_is_admitted_with_idx_provenance() -> None:
    updated, overlay = apply_idx_adjudication(parent(), evidence("EXACT"), expected_schedule_events=1)
    event = updated[("E1", "ABCD")]
    assert event.semantic_class == "EXACT_TRANSITION"
    assert event.transition_date == pd.Timestamp("2024-01-11")
    assert event.transition_source == "OFFICIAL_IDX_ANNOUNCEMENT_ATTACHMENT_SCHEDULE59_ADJUDICATION_V1"
    assert overlay.loc[0, "replay_action"] == "ADMIT_EXACT_TRANSITION"


def test_unresolved_stays_schedule_required() -> None:
    updated, overlay = apply_idx_adjudication(parent(), evidence("UNRESOLVED"), expected_schedule_events=1)
    assert updated[("E1", "ABCD")].semantic_class == "SCHEDULE_REQUIRED"
    assert overlay.loc[0, "replay_action"] == "KEEP_UNRESOLVED"


def test_nonblocking_requires_voluntary_conversion() -> None:
    with pytest.raises(RuntimeError, match="NONBLOCKING_NOT_VOLUNTARY"):
        apply_idx_adjudication(parent(), evidence("EXACT_NON_BLOCKING"), expected_schedule_events=1)

    updated, _ = apply_idx_adjudication(
        parent("voluntary conversion"),
        evidence("EXACT_NON_BLOCKING", source_type="voluntary conversion"),
        expected_schedule_events=1,
    )
    assert updated[("E1", "ABCD")].semantic_class == "NON_BLOCKING"


def test_conflict_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="CONFLICT_FAIL_CLOSED"):
        apply_idx_adjudication(parent(), evidence("CONFLICT"), expected_schedule_events=1)


def test_exact_requires_accepted_market_transition_semantic() -> None:
    frame = evidence("EXACT")
    frame.loc[0, "transition_semantic"] = "RECORD_DATE"
    with pytest.raises(RuntimeError, match="EXACT_TRANSITION_INVALID"):
        apply_idx_adjudication(parent(), frame, expected_schedule_events=1)
