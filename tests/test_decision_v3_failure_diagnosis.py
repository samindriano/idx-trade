from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v3_failure_diagnosis import (
    DecisionV3FailureDiagnosisError,
    DecisionV3FailureDiagnosisResult,
    FrozenV3StructuralLedgers,
    build_block_mechanism_summary,
    build_entry_tier_lifecycle_diagnosis,
    build_severe_exit_session_diagnosis,
    write_failure_diagnosis_artifacts,
)


def _synthetic_ledgers(tmp_path: Path) -> FrozenV3StructuralLedgers:
    sessions = pd.DataFrame(
        [
            {
                "session_index": 0,
                "date": "2026-01-01",
                "bootstrap": True,
                "replacement_count": 0,
                "severe_exit_count": 0,
                "confirmed_mild_exit_count": 0,
                "universe_exit_count": 0,
                "tier_a_vacancy_fill_count": 0,
                "tier_b_vacancy_fill_count": 0,
                "tier_c_vacancy_fill_count": 0,
                "tier_a_soft_replacement_count": 0,
                "target_size": 10,
                "target_rank_mean": 5.5,
                "target_rank_gt20_count": 0,
            },
            {
                "session_index": 1,
                "date": "2026-01-02",
                "bootstrap": False,
                "replacement_count": 3,
                "severe_exit_count": 2,
                "confirmed_mild_exit_count": 0,
                "universe_exit_count": 0,
                "tier_a_vacancy_fill_count": 1,
                "tier_b_vacancy_fill_count": 0,
                "tier_c_vacancy_fill_count": 1,
                "tier_a_soft_replacement_count": 1,
                "target_size": 10,
                "target_rank_mean": 8.0,
                "target_rank_gt20_count": 1,
            },
            {
                "session_index": 2,
                "date": "2026-01-03",
                "bootstrap": False,
                "replacement_count": 1,
                "severe_exit_count": 1,
                "confirmed_mild_exit_count": 0,
                "universe_exit_count": 0,
                "tier_a_vacancy_fill_count": 1,
                "tier_b_vacancy_fill_count": 0,
                "tier_c_vacancy_fill_count": 0,
                "tier_a_soft_replacement_count": 0,
                "target_size": 10,
                "target_rank_mean": 7.0,
                "target_rank_gt20_count": 0,
            },
        ]
    )
    states = pd.DataFrame(
        [
            {
                "session_index": 1,
                "date": "2026-01-02",
                "fold": "1",
                "kind": "CHALLENGER",
                "ticker": "AAA",
                "current_rank": 2,
                "previous_rank": 8,
                "state": "A_CORE",
            },
            {
                "session_index": 1,
                "date": "2026-01-02",
                "fold": "1",
                "kind": "CHALLENGER",
                "ticker": "CCC",
                "current_rank": 5,
                "previous_rank": 90,
                "state": "C_DISTANT",
            },
            {
                "session_index": 2,
                "date": "2026-01-03",
                "fold": "1",
                "kind": "INCUMBENT",
                "ticker": "AAA",
                "current_rank": 12,
                "previous_rank": 2,
                "state": "ACCEPTABLE_HOLD",
            },
            {
                "session_index": 2,
                "date": "2026-01-03",
                "fold": "1",
                "kind": "INCUMBENT",
                "ticker": "CCC",
                "current_rank": 80,
                "previous_rank": 5,
                "state": "SEVERE_DETERIORATION_EXIT",
            },
        ]
    )
    intents = pd.DataFrame(
        [
            {
                "session_index": 2,
                "date": "2026-01-03",
                "side": "SELL_INTENT",
                "ticker": "CCC",
                "reason": "SEVERE_DETERIORATION_EXIT",
            }
        ]
    )
    spells = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "entry_index": 1,
                "entry_date": "2026-01-02",
                "entry_reason": "TIER_A_VACANCY_FILL",
                "exit_index": None,
                "exit_date": None,
                "duration_sessions": 2,
                "completed": False,
                "right_censored": True,
            },
            {
                "ticker": "CCC",
                "entry_index": 1,
                "entry_date": "2026-01-02",
                "entry_reason": "TIER_C_RESIDUAL_VACANCY_FILL",
                "exit_index": 2,
                "exit_date": "2026-01-03",
                "duration_sessions": 1,
                "completed": True,
                "right_censored": False,
            },
        ]
    )
    return FrozenV3StructuralLedgers(
        root=tmp_path,
        manifest={},
        summary={},
        sessions=sessions,
        memberships=pd.DataFrame(),
        intents=intents,
        states=states,
        holding_spells=spells,
        fold_boundaries=pd.DataFrame(),
    )


def test_severe_refill_overlap_and_tier_c_next_severe_are_measured(tmp_path: Path) -> None:
    ledgers = _synthetic_ledgers(tmp_path)
    severe = build_severe_exit_session_diagnosis(ledgers)
    first = severe.loc[severe["session_index"].eq(1)].iloc[0]
    assert bool(first["high_churn_ge3"])
    assert int(first["severe_exit_count"]) == 2
    assert int(first["vacancy_fill_count"]) == 2
    assert bool(first["severe_and_vacancy_fill_overlap"])
    assert bool(first["severe_and_soft_replacement_overlap"])

    lifecycle = build_entry_tier_lifecycle_diagnosis(ledgers)
    c = lifecycle.loc[lifecycle["entry_tier"].eq("C")].iloc[0]
    a = lifecycle.loc[lifecycle["entry_tier"].eq("A")].iloc[0]
    assert bool(c["next_session_severe_exit"])
    assert c["exit_reason"] == "SEVERE_DETERIORATION_EXIT"
    assert int(c["duration_sessions"]) == 1
    assert not bool(a["next_session_severe_exit"])
    assert a["exit_reason"] == "RIGHT_CENSORED"


def test_block_summary_preserves_observed_counts_only(tmp_path: Path) -> None:
    ledgers = _synthetic_ledgers(tmp_path)
    severe = build_severe_exit_session_diagnosis(ledgers)
    lifecycle = build_entry_tier_lifecycle_diagnosis(ledgers)
    blocks = build_block_mechanism_summary(ledgers, severe, lifecycle)
    block1 = blocks.loc[blocks["block"].eq(1)].iloc[0]
    assert int(block1["severe_exit_total"]) == 3
    assert int(block1["vacancy_fill_total"]) == 3
    assert int(block1["soft_replacement_total"]) == 1
    assert int(block1["tier_c_entries"]) == 1
    assert float(block1["tier_c_next_severe_rate"]) == 1.0


def test_output_is_fail_closed_on_existing_destination(tmp_path: Path) -> None:
    destination = tmp_path / "existing"
    destination.mkdir()
    result = DecisionV3FailureDiagnosisResult(
        summary={"status": "COMPLETE_OUTCOME_BLIND_DECISION_V3_FAILURE_MECHANISM_DIAGNOSIS"},
        severe_exit_sessions=pd.DataFrame(),
        entry_lifecycle=pd.DataFrame(),
        block_summary=pd.DataFrame(),
    )
    with pytest.raises(DecisionV3FailureDiagnosisError, match="OUTPUT_ALREADY_EXISTS"):
        write_failure_diagnosis_artifacts(result, destination)
