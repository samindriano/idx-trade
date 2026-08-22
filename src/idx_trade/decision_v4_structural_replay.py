from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .decision_v3_graded_evidence import (
    DecisionV3Plan,
    DecisionV3ShadowState,
)
from .decision_v3_structural_replay import (
    ReplayTrace,
    StructuralReplayResult,
    _build_holding_spells,
    _iso_day,
    _plan_digest,
    _rank_map,
    _replacement_count,
    _verified_session,
    _verified_session_reversed,
    summarize_replay as _summarize_v3_replay,
)
from .decision_v3_structural_source import (
    DecisionV3StructuralReplayError,
    EXPECTED_SCORE_ROWS,
    EXPECTED_SCORE_SESSIONS,
    PinnedReplaySource,
)
from .v4_x1_decision_v1_contract import VerifiedScoreSession
from .v4_x1_decision_v4_refill_decoupling import (
    V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1,
    plan_v4_x1_decision_v4_refill_decoupling,
)
from .decision_v4_structural_contract import (
    EXPECTED_ACCEPT_VERDICT,
    EXPECTED_PREREG_CANONICAL_SHA256,
    EXPECTED_REJECT_VERDICT,
)


def _empty_correctness_v4() -> dict[str, Any]:
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
        "severe_session_noncore_refill_violation_count": 0,
        "severe_session_flag_mismatch_count": 0,
    }


def _independent_incumbent_state(
    ticker: str,
    current_ranks: dict[str, int],
    previous_ranks: dict[str, int],
) -> str:
    profile = V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1
    previous_rank = previous_ranks[ticker]
    current_rank = current_ranks.get(ticker)
    if current_rank is None:
        return "UNIVERSE_EXIT"
    if current_rank <= profile.strong_zone_max_rank:
        return "STRONG_HOLD"
    if current_rank <= profile.retention_zone_max_rank:
        return "ACCEPTABLE_HOLD"
    if current_rank <= profile.mild_deterioration_max_rank:
        return (
            "MILD_DETERIORATION_PENDING_1"
            if previous_rank <= profile.retention_zone_max_rank
            else "CONFIRMED_MILD_DETERIORATION_EXIT"
        )
    return "SEVERE_DETERIORATION_EXIT"


def _independent_challenger_tiers(
    current_ranks: dict[str, int],
    previous_ranks: dict[str, int],
    held_at_start: set[str],
) -> dict[str, list[str]]:
    profile = V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1
    tiers = {"A_CORE": [], "B_NEAR": [], "C_DISTANT": [], "D_NO_HISTORY": []}
    ordered = sorted(current_ranks.items(), key=lambda item: (item[1], item[0]))
    for ticker, current_rank in ordered:
        if current_rank > profile.strong_zone_max_rank or ticker in held_at_start:
            continue
        previous_rank = previous_ranks.get(ticker)
        if previous_rank is None:
            tier = "D_NO_HISTORY"
        elif previous_rank <= profile.retention_zone_max_rank:
            tier = "A_CORE"
        elif previous_rank <= profile.mild_deterioration_max_rank:
            tier = "B_NEAR"
        else:
            tier = "C_DISTANT"
        tiers[tier].append(ticker)
    return tiers


def _expected_vacancy_refills(
    *,
    current_ranks: dict[str, int],
    previous_ranks: dict[str, int],
    start_positions: tuple[str, ...],
) -> tuple[bool, dict[str, list[str]], dict[str, int]]:
    profile = V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1
    held_at_start = set(start_positions)
    states = {
        ticker: _independent_incumbent_state(ticker, current_ranks, previous_ranks)
        for ticker in start_positions
    }
    mandatory = {
        "CONFIRMED_MILD_DETERIORATION_EXIT",
        "SEVERE_DETERIORATION_EXIT",
        "UNIVERSE_EXIT",
    }
    retained_before_fill = sum(state not in mandatory for state in states.values())
    vacancies = max(0, profile.target_count_max - retained_before_fill)
    severe_exit_session = any(
        state == "SEVERE_DETERIORATION_EXIT" for state in states.values()
    )
    tiers = _independent_challenger_tiers(
        current_ranks,
        previous_ranks,
        held_at_start,
    )

    expected = {
        "TIER_A_VACANCY_FILL": [],
        "TIER_B_VACANCY_FILL": [],
        "TIER_C_RESIDUAL_VACANCY_FILL": [],
    }
    residual = vacancies
    a_selected = tiers["A_CORE"][:residual]
    expected["TIER_A_VACANCY_FILL"] = a_selected
    residual -= len(a_selected)

    blocked_b = 0
    blocked_c = 0
    if severe_exit_session:
        blocked_b = min(residual, len(tiers["B_NEAR"]))
        residual_after_hypothetical_b = residual - blocked_b
        blocked_c = min(residual_after_hypothetical_b, len(tiers["C_DISTANT"]))
    else:
        b_selected = tiers["B_NEAR"][:residual]
        expected["TIER_B_VACANCY_FILL"] = b_selected
        residual -= len(b_selected)
        c_selected = tiers["C_DISTANT"][:residual]
        expected["TIER_C_RESIDUAL_VACANCY_FILL"] = c_selected
        residual -= len(c_selected)

    diagnostics = {
        "vacancies_before_refill": vacancies,
        "tier_b_candidates_blocked": blocked_b,
        "tier_c_candidates_blocked": blocked_c,
    }
    return severe_exit_session, expected, diagnostics


def _validate_plan_permissions_v4(
    *,
    plan: DecisionV3Plan,
    index: int,
    current_block: pd.DataFrame,
    previous_block: pd.DataFrame | None,
    start_positions: tuple[str, ...],
    shuffled_plan: DecisionV3Plan,
    correctness: dict[str, Any],
) -> tuple[bool, dict[str, int]]:
    profile = V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1
    current_ranks = _rank_map(current_block)
    previous_ranks = {} if previous_block is None else _rank_map(previous_block)
    target = tuple(plan.target_positions)
    target_set = set(target)

    if len(target) > profile.target_count_max:
        correctness["target_size_over_10_count"] += 1
    if len(target_set) != len(target):
        correctness["duplicate_target_count"] += 1
    if plan.bootstrap != (index == 0):
        correctness["bootstrap_wrong_index_count"] += 1
    if plan.rule_id != profile.rule_id:
        correctness["rule_id_mismatch_count"] += 1
    if plan != shuffled_plan:
        correctness["row_order_nondeterministic_count"] += 1

    if index == 0:
        expected = tuple(
            ticker
            for ticker, _ in sorted(
                current_ranks.items(), key=lambda item: (item[1], item[0])
            )[: profile.target_count_max]
        )
        if target != expected:
            correctness["bootstrap_wrong_index_count"] += 1
        return False, {
            "vacancies_before_refill": 0,
            "tier_b_candidates_blocked": 0,
            "tier_c_candidates_blocked": 0,
        }

    severe_exit_session, expected_fills, diagnostic = _expected_vacancy_refills(
        current_ranks=current_ranks,
        previous_ranks=previous_ranks,
        start_positions=start_positions,
    )

    observed_severe = any(
        obs.state == "SEVERE_DETERIORATION_EXIT"
        for obs in plan.incumbent_observations
    )
    if observed_severe != severe_exit_session:
        correctness["severe_session_flag_mismatch_count"] += 1

    challenger_by_ticker = {obs.ticker: obs for obs in plan.challenger_observations}
    for buy in plan.buy_intents:
        current_rank = current_ranks.get(buy.ticker)
        if current_rank is None or current_rank > profile.strong_zone_max_rank:
            correctness["nonbootstrap_entrant_not_top10_count"] += 1
        previous_rank = previous_ranks.get(buy.ticker)
        if previous_rank is None:
            correctness["postbootstrap_previous_absent_entrant_count"] += 1

        challenger = challenger_by_ticker.get(buy.ticker)
        if buy.reason == "TIER_A_VACANCY_FILL":
            if challenger is None or challenger.state != "A_CORE":
                correctness["tier_a_vacancy_priority_violation_count"] += 1
        elif buy.reason == "TIER_B_VACANCY_FILL":
            if challenger is None or challenger.state != "B_NEAR":
                correctness["tier_b_priority_or_permission_violation_count"] += 1
            if severe_exit_session:
                correctness["severe_session_noncore_refill_violation_count"] += 1
        elif buy.reason == "TIER_C_RESIDUAL_VACANCY_FILL":
            if challenger is None or challenger.state != "C_DISTANT":
                correctness["tier_c_priority_or_permission_violation_count"] += 1
            if severe_exit_session:
                correctness["severe_session_noncore_refill_violation_count"] += 1
        elif buy.reason == "SOFT_RANK_GAP_REPLACEMENT":
            if challenger is None or challenger.state != "A_CORE":
                correctness[
                    "soft_replacement_non_tier_a_or_gap_violation_count"
                ] += 1
                if challenger is not None and challenger.state in {
                    "B_NEAR",
                    "C_DISTANT",
                }:
                    correctness["tier_b_c_soft_replacement_violation_count"] += 1
            if buy.replacement_peer is None:
                correctness[
                    "soft_replacement_non_tier_a_or_gap_violation_count"
                ] += 1
            else:
                incumbent_rank = current_ranks.get(buy.replacement_peer)
                if (
                    incumbent_rank is None
                    or current_rank is None
                    or incumbent_rank - current_rank
                    < profile.soft_replacement_min_rank_advantage
                ):
                    correctness[
                        "soft_replacement_non_tier_a_or_gap_violation_count"
                    ] += 1

    actual = {
        reason: [
            intent.ticker for intent in plan.buy_intents if intent.reason == reason
        ]
        for reason in expected_fills
    }
    if actual["TIER_A_VACANCY_FILL"] != expected_fills["TIER_A_VACANCY_FILL"]:
        correctness["tier_a_vacancy_priority_violation_count"] += 1
    if actual["TIER_B_VACANCY_FILL"] != expected_fills["TIER_B_VACANCY_FILL"]:
        correctness["tier_b_priority_or_permission_violation_count"] += 1
    if (
        actual["TIER_C_RESIDUAL_VACANCY_FILL"]
        != expected_fills["TIER_C_RESIDUAL_VACANCY_FILL"]
    ):
        correctness["tier_c_priority_or_permission_violation_count"] += 1

    mandatory_states = {
        "CONFIRMED_MILD_DETERIORATION_EXIT",
        "SEVERE_DETERIORATION_EXIT",
        "UNIVERSE_EXIT",
    }
    for obs in plan.incumbent_observations:
        independent = _independent_incumbent_state(
            obs.ticker, current_ranks, previous_ranks
        )
        if obs.state != independent:
            correctness["severe_session_flag_mismatch_count"] += 1
        if obs.state == "MILD_DETERIORATION_PENDING_1" and obs.ticker not in target_set:
            correctness["first_mild_observation_retention_violation_count"] += 1
        if (
            obs.current_rank is not None
            and obs.current_rank > profile.mild_deterioration_max_rank
            and obs.ticker in target_set
        ):
            correctness["target_rank_gt50_after_processing_count"] += 1
        if (
            obs.current_rank is not None
            and profile.retention_zone_max_rank
            < obs.current_rank
            <= profile.mild_deterioration_max_rank
            and obs.previous_rank > profile.retention_zone_max_rank
            and obs.ticker in target_set
        ):
            correctness["second_consecutive_rank21_50_retained_count"] += 1
        if obs.state == "UNIVERSE_EXIT" and obs.ticker in target_set:
            correctness["universe_exit_retention_violation_count"] += 1
        if obs.state in mandatory_states and obs.ticker in target_set:
            correctness["mandatory_exit_retained_count"] += 1

    return severe_exit_session, diagnostic


def replay_once_v4(source: PinnedReplaySource) -> ReplayTrace:
    frame = source.frame.copy()
    if len(frame) != EXPECTED_SCORE_ROWS:
        raise DecisionV3StructuralReplayError(
            f"DECISION_V4_REPLAY_ROW_COUNT_CHANGED:{len(frame)}"
        )
    dates = sorted(pd.Timestamp(x).normalize() for x in frame["date"].drop_duplicates())
    if len(dates) != EXPECTED_SCORE_SESSIONS:
        raise DecisionV3StructuralReplayError(
            f"DECISION_V4_REPLAY_SESSION_COUNT_CHANGED:{len(dates)}"
        )

    blocks = {day: frame.loc[frame["date"].eq(day)].copy() for day in dates}
    state = DecisionV3ShadowState.empty()
    plans: list[DecisionV3Plan] = []
    session_rows: list[dict[str, Any]] = []
    membership_rows: list[dict[str, Any]] = []
    intent_rows: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    fold_boundary_rows: list[dict[str, Any]] = []
    correctness = _empty_correctness_v4()

    previous_verified: VerifiedScoreSession | None = None
    previous_block: pd.DataFrame | None = None
    previous_fold: str | None = None
    profile = V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1

    for index, day in enumerate(dates):
        block = blocks[day]
        fold_values = block["fold"].astype(str).unique()
        mode_values = block["mode"].astype(str).unique()
        if len(fold_values) != 1 or len(mode_values) != 1:
            raise DecisionV3StructuralReplayError(
                "DECISION_V4_REPLAY_SESSION_METADATA_NOT_UNIQUE"
            )
        fold = str(fold_values[0])
        mode = str(mode_values[0])
        current_verified = _verified_session(block, source)

        if index == 0:
            if state.as_of_session_date is not None or state.positions:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V4_REPLAY_BOOTSTRAP_STATE_NOT_EMPTY"
                )
            if previous_verified is not None:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V4_REPLAY_BOOTSTRAP_PREROLL_DETECTED"
                )
        else:
            expected_previous_day = _iso_day(dates[index - 1])
            if previous_verified is None:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V4_REPLAY_PREVIOUS_SESSION_MISSING"
                )
            if previous_verified.session_date != expected_previous_day:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V4_REPLAY_PREVIOUS_SESSION_NOT_ADJACENT"
                )
            if state.as_of_session_date != expected_previous_day:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V4_REPLAY_STATE_NOT_ADJACENT"
                )
            if state.rule_id != profile.rule_id:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V4_REPLAY_STATE_RULE_ID_MISMATCH"
                )

        start_positions = tuple(state.positions)
        plan = plan_v4_x1_decision_v4_refill_decoupling(
            current_verified, previous_verified, state
        )
        shuffled_plan = plan_v4_x1_decision_v4_refill_decoupling(
            _verified_session_reversed(block, source),
            (
                None
                if previous_block is None
                else _verified_session_reversed(previous_block, source)
            ),
            state,
        )
        severe_exit_session, severity_diagnostic = _validate_plan_permissions_v4(
            plan=plan,
            index=index,
            current_block=block,
            previous_block=previous_block,
            start_positions=start_positions,
            shuffled_plan=shuffled_plan,
            correctness=correctness,
        )
        plans.append(plan)

        ranks = _rank_map(block)
        target_ranks = [ranks[ticker] for ticker in plan.target_positions]
        target_size = len(plan.target_positions)
        top10_overlap = sum(rank <= 10 for rank in target_ranks)
        top20_overlap = sum(rank <= 20 for rank in target_ranks)
        replacement_count = _replacement_count(plan)

        buy_reason = {intent.ticker: intent.reason for intent in plan.buy_intents}
        for ticker in plan.target_positions:
            membership_rows.append(
                {
                    "session_index": index,
                    "date": _iso_day(day),
                    "fold": fold,
                    "mode": mode,
                    "ticker": ticker,
                    "rank_consensus": ranks[ticker],
                    "held_at_start": ticker in set(start_positions),
                    "entry_reason": (
                        buy_reason.get(ticker, "HELD")
                        if index > 0
                        else "BOOTSTRAP_TOP10"
                    ),
                }
            )

        for intent in plan.sell_intents + plan.buy_intents:
            intent_rows.append(
                {
                    "session_index": index,
                    "date": _iso_day(day),
                    "fold": fold,
                    "mode": mode,
                    "side": intent.side,
                    "ticker": intent.ticker,
                    "rank_consensus": intent.rank_consensus,
                    "reason": intent.reason,
                    "replacement_peer": intent.replacement_peer,
                }
            )

        for obs in plan.incumbent_observations:
            state_rows.append(
                {
                    "session_index": index,
                    "date": _iso_day(day),
                    "fold": fold,
                    "kind": "INCUMBENT",
                    "ticker": obs.ticker,
                    "current_rank": obs.current_rank,
                    "previous_rank": obs.previous_rank,
                    "state": obs.state,
                }
            )
        for obs in plan.challenger_observations:
            state_rows.append(
                {
                    "session_index": index,
                    "date": _iso_day(day),
                    "fold": fold,
                    "kind": "CHALLENGER",
                    "ticker": obs.ticker,
                    "current_rank": obs.current_rank,
                    "previous_rank": obs.previous_rank,
                    "state": obs.state,
                }
            )

        reason_counts = {
            reason: sum(intent.reason == reason for intent in plan.buy_intents)
            for reason in (
                "TIER_A_VACANCY_FILL",
                "TIER_B_VACANCY_FILL",
                "TIER_C_RESIDUAL_VACANCY_FILL",
                "SOFT_RANK_GAP_REPLACEMENT",
            )
        }
        sell_reason_counts = {
            reason: sum(intent.reason == reason for intent in plan.sell_intents)
            for reason in (
                "CONFIRMED_MILD_DETERIORATION_EXIT",
                "SEVERE_DETERIORATION_EXIT",
                "UNIVERSE_EXIT",
                "SOFT_RANK_GAP_REPLACEMENT",
            )
        }

        session_rows.append(
            {
                "session_index": index,
                "date": _iso_day(day),
                "fold": fold,
                "mode": mode,
                "bootstrap": bool(plan.bootstrap),
                "start_target_size": len(start_positions),
                "target_size": target_size,
                "unfilled_slots": int(plan.unfilled_slots),
                "capacity_state": plan.capacity_state,
                "sell_intent_count": len(plan.sell_intents),
                "buy_intent_count": len(plan.buy_intents),
                "replacement_count": replacement_count,
                "top10_overlap": top10_overlap,
                "top10_overlap_normalized": top10_overlap / 10.0,
                "top20_overlap": top20_overlap,
                "target_rank_mean": (
                    float(np.mean(target_ranks)) if target_ranks else None
                ),
                "target_rank_median": (
                    float(np.median(target_ranks)) if target_ranks else None
                ),
                "target_rank_worst": max(target_ranks) if target_ranks else None,
                "target_rank_gt20_count": sum(rank > 20 for rank in target_ranks),
                "target_rank_gt50_count": sum(rank > 50 for rank in target_ranks),
                "mild_pending_count": sum(
                    obs.state == "MILD_DETERIORATION_PENDING_1"
                    for obs in plan.incumbent_observations
                ),
                "confirmed_mild_exit_count": sell_reason_counts[
                    "CONFIRMED_MILD_DETERIORATION_EXIT"
                ],
                "severe_exit_count": sell_reason_counts["SEVERE_DETERIORATION_EXIT"],
                "universe_exit_count": sell_reason_counts["UNIVERSE_EXIT"],
                "tier_a_vacancy_fill_count": reason_counts["TIER_A_VACANCY_FILL"],
                "tier_b_vacancy_fill_count": reason_counts["TIER_B_VACANCY_FILL"],
                "tier_c_vacancy_fill_count": reason_counts[
                    "TIER_C_RESIDUAL_VACANCY_FILL"
                ],
                "tier_a_soft_replacement_count": reason_counts[
                    "SOFT_RANK_GAP_REPLACEMENT"
                ],
                "tier_d_rejection_count": sum(
                    obs.state == "D_NO_HISTORY"
                    for obs in plan.challenger_observations
                ),
                "severe_exit_session": bool(severe_exit_session),
                "vacancies_before_refill": int(
                    severity_diagnostic["vacancies_before_refill"]
                ),
                "tier_b_candidates_blocked": int(
                    severity_diagnostic["tier_b_candidates_blocked"]
                ),
                "tier_c_candidates_blocked": int(
                    severity_diagnostic["tier_c_candidates_blocked"]
                ),
            }
        )

        if previous_fold is not None and fold != previous_fold:
            fold_boundary_rows.append(
                {
                    "session_index": index,
                    "date": _iso_day(day),
                    "previous_date": _iso_day(dates[index - 1]),
                    "previous_fold": previous_fold,
                    "current_fold": fold,
                    "start_target_size": len(start_positions),
                    "target_size": target_size,
                    "replacement_count": replacement_count,
                    "target_rank_mean": (
                        float(np.mean(target_ranks)) if target_ranks else None
                    ),
                }
            )

        state = DecisionV3ShadowState.from_plan(plan)
        previous_verified = current_verified
        previous_block = block
        previous_fold = fold

    session_ledger = pd.DataFrame(session_rows)
    membership_ledger = pd.DataFrame(membership_rows)
    intent_ledger = pd.DataFrame(intent_rows)
    state_ledger = pd.DataFrame(state_rows)
    fold_boundaries = pd.DataFrame(fold_boundary_rows)
    holding_spells = _build_holding_spells(membership_ledger, dates)

    return ReplayTrace(
        session_ledger=session_ledger,
        membership_ledger=membership_ledger,
        intent_ledger=intent_ledger,
        state_ledger=state_ledger,
        holding_spells=holding_spells,
        fold_boundaries=fold_boundaries,
        plan_digest=_plan_digest(plans),
        correctness=correctness,
    )


def _v4_descriptive_diagnostics(
    trace: ReplayTrace,
    block_summary: dict[str, Any],
) -> dict[str, Any]:
    sessions = trace.session_ledger
    severe = sessions.loc[sessions["severe_exit_session"].eq(True)]
    return {
        "severe_exit_session_count": int(len(severe)),
        "tier_a_vacancy_fills_on_severe_sessions": int(
            severe["tier_a_vacancy_fill_count"].sum()
        ),
        "tier_b_candidates_blocked_on_severe_sessions": int(
            severe["tier_b_candidates_blocked"].sum()
        ),
        "tier_c_candidates_blocked_on_severe_sessions": int(
            severe["tier_c_candidates_blocked"].sum()
        ),
        "underfilled_sessions_after_severity_conditioned_refill": int(
            sessions["target_size"].lt(10).sum()
        ),
        "vacancy_days_after_severity_conditioned_refill": int(
            sessions["unfilled_slots"].sum()
        ),
        "block_1_to_6_churn_quality_capacity_summary": block_summary,
        "blocked_candidate_definition": (
            "seat-feasible B/C challengers that would have been consumed by "
            "the unchanged V3 A->B->C vacancy priority after available A supply, "
            "but are withheld solely because the session is severe"
        ),
    }


def summarize_replay_v4(
    primary: ReplayTrace,
    secondary: ReplayTrace,
    source: PinnedReplaySource,
) -> dict[str, Any]:
    base = _summarize_v3_replay(primary, secondary, source)
    gates = base["gates"]
    verdict = (
        EXPECTED_ACCEPT_VERDICT
        if all(group["pass"] for group in gates.values())
        else EXPECTED_REJECT_VERDICT
    )
    summary = dict(base)
    summary["schema_version"] = "decision_v4_refill_decoupling_structural_replay_summary_v1"
    summary["status"] = verdict
    summary["verdict"] = verdict
    source_summary = dict(summary["source"])
    source_summary["decision_v4_rule_id"] = (
        V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1.rule_id
    )
    summary["source"] = source_summary
    guards = dict(summary["guards"])
    guards.update(
        {
            "v4_preregistration_canonical_sha256": EXPECTED_PREREG_CANONICAL_SHA256,
            "severity_flag_frozen_from_start_of_session_incumbents": True,
            "severity_conditioned_refill_is_only_v4_mechanism": True,
            "required_v4_diagnostics_are_descriptive_only": True,
        }
    )
    summary["guards"] = guards
    metrics = dict(summary["metrics"])
    v4_diagnostics = _v4_descriptive_diagnostics(
        primary,
        metrics["stability"]["six_fixed_100_session_blocks"],
    )
    metrics["v4_refill_decoupling_descriptive_only"] = v4_diagnostics
    summary["metrics"] = metrics

    v4_integrity_conditions = {
        "severe_session_noncore_refill_zero": (
            metrics["correctness"]["severe_session_noncore_refill_violation_count"]
            == 0
        ),
        "severe_session_flag_matches_independent_classification": (
            metrics["correctness"]["severe_session_flag_mismatch_count"] == 0
        ),
    }
    gates = dict(summary["gates"])
    gates["A2_v4_refill_decoupling_integrity"] = {
        "pass": all(v4_integrity_conditions.values()),
        "conditions": v4_integrity_conditions,
    }
    summary["gates"] = gates
    verdict = (
        EXPECTED_ACCEPT_VERDICT
        if all(group["pass"] for group in gates.values())
        else EXPECTED_REJECT_VERDICT
    )
    summary["status"] = verdict
    summary["verdict"] = verdict
    return summary


def run_structural_replay_v4(source: PinnedReplaySource) -> StructuralReplayResult:
    primary = replay_once_v4(source)
    secondary = replay_once_v4(source)
    summary = summarize_replay_v4(primary, secondary, source)
    return StructuralReplayResult(primary=primary, summary=summary)


def _frame_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def write_structural_replay_artifacts_v4(
    result: StructuralReplayResult,
    output_dir: str | Path,
) -> Path:
    destination = Path(output_dir).expanduser().resolve()
    if destination.exists():
        raise DecisionV3StructuralReplayError(
            f"DECISION_V4_REPLAY_OUTPUT_ALREADY_EXISTS:{destination}"
        )
    staging = destination.with_name(destination.name + ".staging")
    if staging.exists():
        raise DecisionV3StructuralReplayError(
            f"DECISION_V4_REPLAY_STAGING_ALREADY_EXISTS:{staging}"
        )
    staging.mkdir(parents=True, exist_ok=False)

    outputs: dict[str, bytes] = {
        "summary.json": (
            json.dumps(result.summary, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8"),
        "decision_session_ledger.csv": _frame_to_csv_bytes(
            result.primary.session_ledger
        ),
        "decision_membership_ledger.csv": _frame_to_csv_bytes(
            result.primary.membership_ledger
        ),
        "decision_intent_ledger.csv": _frame_to_csv_bytes(
            result.primary.intent_ledger
        ),
        "decision_state_ledger.csv": _frame_to_csv_bytes(
            result.primary.state_ledger
        ),
        "holding_spells.csv": _frame_to_csv_bytes(result.primary.holding_spells),
        "fold_boundary_transitions.csv": _frame_to_csv_bytes(
            result.primary.fold_boundaries
        ),
    }

    artifact_hashes: dict[str, str] = {}
    for name, content in outputs.items():
        path = staging / name
        path.write_bytes(content)
        artifact_hashes[name] = hashlib.sha256(content).hexdigest()

    manifest = {
        "schema_version": "decision_v4_refill_decoupling_structural_replay_manifest_v1",
        "status": result.summary["status"],
        "source": result.summary["source"],
        "guards": result.summary["guards"],
        "plan_digest": result.primary.plan_digest,
        "artifacts": artifact_hashes,
    }
    manifest_content = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    (staging / "MANIFEST.json").write_bytes(manifest_content)

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging.rename(destination)
    return destination / "MANIFEST.json"
