from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v3_structural_replay import (
    GATE_MEAN_FULL_TARGET_TOP10_OVERLAP_MIN,
    GATE_MEAN_REPLACEMENTS_MAX,
    GATE_MEAN_TARGET_RANK_MAX,
    GATE_MEAN_TARGET_SIZE_MIN,
    GATE_MEDIAN_HOLDING_MIN,
    GATE_ONE_SESSION_HOLDING_SHARE_MAX,
    GATE_SHARE_GE3_MAX,
    GATE_SHARE_TARGET_SIZE_10_MIN,
    GATE_SHARE_TARGET_SIZE_LE8_MAX,
    GATE_TURNOVER_VS_NAIVE_MAX,
    ReplayTrace,
    StructuralReplayResult,
    evaluate_gates,
    write_structural_replay_artifacts,
)
from idx_trade.decision_v3_structural_source import (
    DecisionV3StructuralReplayError,
    REPLAY_CONTRACT_RELATIVE_PATH,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _zero_correctness() -> dict[str, int]:
    return {
        "target_size_over_10_count": 0,
        "duplicate_target_count": 0,
        "nonbootstrap_entrant_not_top10_count": 0,
        "postbootstrap_previous_absent_entrant_count": 0,
        "tier_a_vacancy_priority_violation_count": 0,
        "tier_b_priority_or_permission_violation_count": 0,
        "tier_c_priority_or_permission_violation_count": 0,
        "tier_b_c_soft_replacement_violation_count": 0,
        "target_rank_gt50_after_processing_count": 0,
        "second_consecutive_rank21_50_retained_count": 0,
        "first_mild_observation_retention_violation_count": 0,
        "soft_replacement_non_tier_a_or_gap_violation_count": 0,
        "universe_exit_retention_violation_count": 0,
        "mandatory_exit_retained_count": 0,
        "row_order_nondeterministic_count": 0,
        "bootstrap_wrong_index_count": 0,
        "rule_id_mismatch_count": 0,
        "second_pass_nondeterministic_count": 0,
    }


def _threshold_metrics() -> dict:
    return {
        "correctness": _zero_correctness(),
        "determinism": {"second_pass_exact_match": True},
        "churn": {
            "replacement_distribution": {"mean": GATE_MEAN_REPLACEMENTS_MAX},
            "turnover_ratio_vs_naive": GATE_TURNOVER_VS_NAIVE_MAX,
            "share_replacements_ge3": GATE_SHARE_GE3_MAX,
        },
        "holding_persistence": {
            "completed_holding_spell_distribution": {
                "median": GATE_MEDIAN_HOLDING_MIN
            },
            "one_session_holding_share": GATE_ONE_SESSION_HOLDING_SHARE_MAX,
        },
        "rank_quality": {
            "mean_current_top10_overlap_full_target": (
                GATE_MEAN_FULL_TARGET_TOP10_OVERLAP_MIN
            ),
            "mean_target_rank": GATE_MEAN_TARGET_RANK_MAX,
        },
        "capacity": {
            "mean_target_size": GATE_MEAN_TARGET_SIZE_MIN,
            "share_target_size_10": GATE_SHARE_TARGET_SIZE_10_MIN,
            "share_target_size_le8": GATE_SHARE_TARGET_SIZE_LE8_MAX,
        },
    }


def test_numeric_gate_constants_map_one_to_one_to_frozen_contract() -> None:
    payload = json.loads(
        (REPO_ROOT / REPLAY_CONTRACT_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    gates = payload["gates"]
    assert gates["B_churn"]["mean_replacements_max"] == GATE_MEAN_REPLACEMENTS_MAX
    assert gates["B_churn"]["turnover_vs_naive_max"] == GATE_TURNOVER_VS_NAIVE_MAX
    assert gates["B_churn"]["share_ge3_replacements_max"] == GATE_SHARE_GE3_MAX
    assert gates["C_holding_persistence"]["median_holding_min"] == GATE_MEDIAN_HOLDING_MIN
    assert gates["C_holding_persistence"]["one_session_holding_share_max"] == (
        GATE_ONE_SESSION_HOLDING_SHARE_MAX
    )
    assert gates["D_rank_quality"]["mean_full_target_top10_overlap_min"] == (
        GATE_MEAN_FULL_TARGET_TOP10_OVERLAP_MIN
    )
    assert gates["D_rank_quality"]["mean_target_rank_max"] == GATE_MEAN_TARGET_RANK_MAX
    assert gates["E_capacity"]["mean_target_size_min"] == GATE_MEAN_TARGET_SIZE_MIN
    assert gates["E_capacity"]["share_target_size_10_min"] == (
        GATE_SHARE_TARGET_SIZE_10_MIN
    )
    assert gates["E_capacity"]["share_target_size_le8_max"] == (
        GATE_SHARE_TARGET_SIZE_LE8_MAX
    )


def test_exact_gate_threshold_boundaries_are_inclusive_passes() -> None:
    gates = evaluate_gates(_threshold_metrics())
    assert all(group["pass"] for group in gates.values())


def _dummy_result() -> StructuralReplayResult:
    empty = pd.DataFrame()
    trace = ReplayTrace(
        session_ledger=empty,
        membership_ledger=empty,
        intent_ledger=empty,
        state_ledger=empty,
        holding_spells=empty,
        fold_boundaries=empty,
        plan_digest="dummy",
        correctness={},
    )
    summary = {
        "status": "DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_REJECT",
        "source": {},
        "guards": {},
    }
    return StructuralReplayResult(primary=trace, summary=summary)


def test_existing_output_destination_is_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "already-exists"
    destination.mkdir()
    with pytest.raises(DecisionV3StructuralReplayError, match="OUTPUT_ALREADY_EXISTS"):
        write_structural_replay_artifacts(_dummy_result(), destination)


def test_existing_staging_directory_is_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "new-output"
    staging = tmp_path / "new-output.staging"
    staging.mkdir()
    with pytest.raises(DecisionV3StructuralReplayError, match="STAGING_ALREADY_EXISTS"):
        write_structural_replay_artifacts(_dummy_result(), destination)
