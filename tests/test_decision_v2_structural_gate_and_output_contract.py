from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v2_structural_replay import (
    DecisionV2StructuralReplayError,
    GATE_LIMITS,
    ReplayPass,
    StructuralReplayResult,
    evaluate_gates,
    write_structural_replay_artifacts,
)


def _boundary_metrics() -> dict[str, object]:
    return {
        "turnover_churn": {
            "replacement_distribution": {
                "mean": GATE_LIMITS["mean_replacements_per_transition_max"]
            },
            "transition_distribution": {
                "share_ge3": GATE_LIMITS[
                    "share_transitions_ge3_replacements_max"
                ]
            },
            "turnover_ratio_vs_naive_exact_daily_top10": GATE_LIMITS[
                "turnover_ratio_vs_naive_max"
            ],
        },
        "holding_persistence": {
            "completed_duration_sessions": {
                "median": GATE_LIMITS["median_completed_holding_spell_min"]
            },
            "one_session_holding_share": GATE_LIMITS[
                "one_session_completed_holding_share_max"
            ],
        },
        "rank_quality": {
            "mean_current_top10_overlap_full_target": GATE_LIMITS[
                "mean_full_target_top10_overlap_min"
            ],
            "mean_target_rank": GATE_LIMITS["mean_target_rank_max"],
        },
        "capacity": {
            "mean_target_size": GATE_LIMITS["mean_target_size_min"],
            "share_target_size_10": GATE_LIMITS["share_target_size_10_min"],
            "share_target_size_le8": GATE_LIMITS["share_target_size_le8_max"],
        },
        "correctness": {
            "no_target_size_gt10": True,
            "no_duplicate_target_ticker": True,
            "unqualified_nonbootstrap_entrant_violations": 0,
            "one_observation_gt20_exit_violations": 0,
            "confirmed_gt20_incumbent_retained_violations": 0,
            "soft_replacement_gap_violations": 0,
            "stale_state_violations": 0,
            "deterministic_second_pass_match": True,
        },
    }


def test_every_numeric_gate_constant_matches_machine_contract() -> None:
    payload = json.loads(
        Path(
            "docs/specs/decision_v2_minimal_structural_replay_contract_v1.json"
        ).read_text(encoding="utf-8")
    )
    hard = payload["hard_gates"]

    assert (
        hard["B_churn_reduction"]["mean_replacements_per_transition_max"]
        == GATE_LIMITS["mean_replacements_per_transition_max"]
    )
    assert (
        hard["B_churn_reduction"]["turnover_ratio_vs_naive_max"]
        == GATE_LIMITS["turnover_ratio_vs_naive_max"]
    )
    assert (
        hard["B_churn_reduction"]["share_transitions_ge3_replacements_max"]
        == GATE_LIMITS["share_transitions_ge3_replacements_max"]
    )
    assert (
        hard["C_holding_persistence"]["median_completed_holding_spell_min_sessions"]
        == GATE_LIMITS["median_completed_holding_spell_min"]
    )
    assert (
        hard["C_holding_persistence"]["one_session_completed_holding_share_max"]
        == GATE_LIMITS["one_session_completed_holding_share_max"]
    )
    assert (
        hard["D_rank_quality_preservation"]["mean_current_top10_overlap_full_target_min"]
        == GATE_LIMITS["mean_full_target_top10_overlap_min"]
    )
    assert (
        hard["D_rank_quality_preservation"]["mean_target_rank_max"]
        == GATE_LIMITS["mean_target_rank_max"]
    )
    assert (
        hard["E_capacity"]["mean_target_size_min"]
        == GATE_LIMITS["mean_target_size_min"]
    )
    assert (
        hard["E_capacity"]["share_target_size_10_min"]
        == GATE_LIMITS["share_target_size_10_min"]
    )
    assert (
        hard["E_capacity"]["share_target_size_le8_max"]
        == GATE_LIMITS["share_target_size_le8_max"]
    )


def test_all_numeric_gate_boundaries_are_inclusive() -> None:
    gates = evaluate_gates(_boundary_metrics())
    assert all(group["pass"] for group in gates.values())


def _dummy_result() -> StructuralReplayResult:
    empty = pd.DataFrame()
    replay = ReplayPass(
        session_ledger=empty,
        membership_ledger=empty,
        intent_ledger=empty,
        state_ledger=empty,
        holding_spells=empty,
        fold_boundaries=empty,
        plan_digest="dummy",
    )
    return StructuralReplayResult(
        primary=replay,
        summary={
            "status": "DECISION_V2_MINIMAL_STRUCTURAL_REJECT",
            "source": {},
            "guards": {},
        },
    )


def test_output_writer_refuses_existing_destination(tmp_path: Path) -> None:
    destination = tmp_path / "result"
    destination.mkdir()

    with pytest.raises(
        DecisionV2StructuralReplayError,
        match="OUTPUT_ALREADY_EXISTS",
    ):
        write_structural_replay_artifacts(_dummy_result(), destination)


def test_output_writer_refuses_existing_staging_directory(tmp_path: Path) -> None:
    destination = tmp_path / "result"
    staging = tmp_path / "result.staging"
    staging.mkdir()

    with pytest.raises(
        DecisionV2StructuralReplayError,
        match="STAGING_ALREADY_EXISTS",
    ):
        write_structural_replay_artifacts(_dummy_result(), destination)
