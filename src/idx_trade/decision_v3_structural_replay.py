from __future__ import annotations

from dataclasses import asdict, dataclass
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
from .decision_v3_structural_source import (
    DecisionV3StructuralReplayError,
    EXPECTED_NAIVE_TOP10_REPLACEMENTS,
    EXPECTED_SCORE_ROWS,
    EXPECTED_SCORE_SESSIONS,
    EXPECTED_SOURCE_MANIFEST_SHA256,
    EXPECTED_SOURCE_SCORE_SHA256,
    PinnedReplaySource,
    canonical_json_sha256,
    sha256_file,
)
from .v4_x1_decision_v1_contract import (
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    VerifiedScoreSession,
    _VERIFIED_TOKEN,
)
from .v4_x1_decision_v3_graded_evidence import (
    V4_X1_DECISION_V3_GRADED_EVIDENCE_PROFILE_V2,
    plan_v4_x1_decision_v3_graded_evidence,
)


EXPECTED_DECISION_V1_REPLACEMENTS = 2686
EXPECTED_DECISION_V2_REPLACEMENTS = 1435
EXPECTED_DECISION_V2_RESULT_MANIFEST_SHA256 = (
    "a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba"
)
EXPECTED_DECISION_V2_PLAN_DIGEST = (
    "51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4"
)
VERDICT_ACCEPT = "DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_ACCEPT"
VERDICT_REJECT = "DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_REJECT"

GATE_MEAN_REPLACEMENTS_MAX = 2.25
GATE_TURNOVER_VS_NAIVE_MAX = 0.50
GATE_SHARE_GE3_MAX = 0.35
GATE_MEDIAN_HOLDING_MIN = 3.0
GATE_ONE_SESSION_HOLDING_SHARE_MAX = 0.35
GATE_MEAN_FULL_TARGET_TOP10_OVERLAP_MIN = 6.0
GATE_MEAN_TARGET_RANK_MAX = 12.0
GATE_MEAN_TARGET_SIZE_MIN = 9.0
GATE_SHARE_TARGET_SIZE_10_MIN = 0.70
GATE_SHARE_TARGET_SIZE_LE8_MAX = 0.10


@dataclass(frozen=True)
class ReplayTrace:
    session_ledger: pd.DataFrame
    membership_ledger: pd.DataFrame
    intent_ledger: pd.DataFrame
    state_ledger: pd.DataFrame
    holding_spells: pd.DataFrame
    fold_boundaries: pd.DataFrame
    plan_digest: str
    correctness: dict[str, Any]


@dataclass(frozen=True)
class StructuralReplayResult:
    primary: ReplayTrace
    summary: dict[str, Any]


def _iso_day(value: object) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _verified_session(
    block: pd.DataFrame,
    source: PinnedReplaySource,
) -> VerifiedScoreSession:
    if block.empty:
        raise DecisionV3StructuralReplayError("DECISION_V3_REPLAY_EMPTY_SCORE_SESSION")
    dates = pd.to_datetime(block["date"]).dt.normalize().unique()
    if len(dates) != 1:
        raise DecisionV3StructuralReplayError("DECISION_V3_REPLAY_BLOCK_MULTIPLE_DATES")
    scores = block.loc[:, ["ticker", "rank_consensus"]].copy()
    scores = scores.sort_values(["rank_consensus", "ticker"], kind="mergesort")
    return VerifiedScoreSession(
        session_date=_iso_day(dates[0]),
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=source.score_path,
        artifact_sha256=EXPECTED_SOURCE_SCORE_SHA256,
        manifest_path=source.manifest_path,
        manifest_sha256=EXPECTED_SOURCE_MANIFEST_SHA256,
        scores=scores,
        alpha_tie_rows=0,
        _verification_token=_VERIFIED_TOKEN,
    )


def _verified_session_reversed(
    block: pd.DataFrame,
    source: PinnedReplaySource,
) -> VerifiedScoreSession:
    verified = _verified_session(block, source)
    return VerifiedScoreSession(
        session_date=verified.session_date,
        model_id=verified.model_id,
        model_fingerprint=verified.model_fingerprint,
        artifact_path=verified.artifact_path,
        artifact_sha256=verified.artifact_sha256,
        manifest_path=verified.manifest_path,
        manifest_sha256=verified.manifest_sha256,
        scores=verified.scores.iloc[::-1].reset_index(drop=True),
        alpha_tie_rows=verified.alpha_tie_rows,
        _verification_token=_VERIFIED_TOKEN,
    )


def _plan_payload(plan: DecisionV3Plan) -> dict[str, Any]:
    return asdict(plan)


def _plan_digest(plans: list[DecisionV3Plan]) -> str:
    payload = [_plan_payload(plan) for plan in plans]
    return canonical_json_sha256(payload)


def _replacement_count(plan: DecisionV3Plan) -> int:
    if plan.bootstrap:
        return 0
    return max(len(plan.sell_intents), len(plan.buy_intents))


def _rank_map(block: pd.DataFrame) -> dict[str, int]:
    return {
        str(row.ticker): int(row.rank_consensus)
        for row in block.loc[:, ["ticker", "rank_consensus"]].itertuples(index=False)
    }


def _quantiles(values: pd.Series | list[float] | list[int]) -> dict[str, float | int | None]:
    series = pd.Series(values, dtype=float).dropna()
    if series.empty:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "max": None,
        }
    return {
        "count": int(series.size),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "p75": float(series.quantile(0.75)),
        "p90": float(series.quantile(0.90)),
        "p95": float(series.quantile(0.95)),
        "max": float(series.max()),
    }


def _build_holding_spells(
    memberships: pd.DataFrame,
    dates: list[pd.Timestamp],
) -> pd.DataFrame:
    columns = [
        "ticker",
        "entry_index",
        "entry_date",
        "entry_reason",
        "exit_index",
        "exit_date",
        "duration_sessions",
        "completed",
        "right_censored",
    ]
    if memberships.empty:
        return pd.DataFrame(columns=columns)

    by_index: dict[int, pd.DataFrame] = {
        int(index): block.copy()
        for index, block in memberships.groupby("session_index", sort=True)
    }
    active: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    for index, day in enumerate(dates):
        block = by_index.get(index, pd.DataFrame())
        current = set(block["ticker"].astype(str)) if not block.empty else set()
        previous = set(active)

        for ticker in sorted(previous - current):
            item = active.pop(ticker)
            rows.append(
                {
                    "ticker": ticker,
                    "entry_index": int(item["entry_index"]),
                    "entry_date": item["entry_date"],
                    "entry_reason": item["entry_reason"],
                    "exit_index": index,
                    "exit_date": _iso_day(day),
                    "duration_sessions": index - int(item["entry_index"]),
                    "completed": True,
                    "right_censored": False,
                }
            )

        if not block.empty:
            entry_reason_by_ticker = dict(
                zip(block["ticker"].astype(str), block["entry_reason"].astype(str))
            )
            for ticker in sorted(current - previous):
                active[ticker] = {
                    "entry_index": index,
                    "entry_date": _iso_day(day),
                    "entry_reason": entry_reason_by_ticker[ticker],
                }

    last_index = len(dates) - 1
    for ticker in sorted(active):
        item = active[ticker]
        rows.append(
            {
                "ticker": ticker,
                "entry_index": int(item["entry_index"]),
                "entry_date": item["entry_date"],
                "entry_reason": item["entry_reason"],
                "exit_index": None,
                "exit_date": None,
                "duration_sessions": last_index - int(item["entry_index"]) + 1,
                "completed": False,
                "right_censored": True,
            }
        )

    return pd.DataFrame(rows, columns=columns).sort_values(
        ["entry_index", "ticker"], kind="mergesort"
    ).reset_index(drop=True)


def _empty_correctness() -> dict[str, Any]:
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
    }


def _validate_plan_permissions(
    *,
    plan: DecisionV3Plan,
    index: int,
    current_block: pd.DataFrame,
    previous_block: pd.DataFrame | None,
    start_positions: tuple[str, ...],
    shuffled_plan: DecisionV3Plan,
    correctness: dict[str, Any],
) -> None:
    profile = V4_X1_DECISION_V3_GRADED_EVIDENCE_PROFILE_V2
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
        return

    challenger_by_ticker = {obs.ticker: obs for obs in plan.challenger_observations}

    for buy in plan.buy_intents:
        current_rank = current_ranks.get(buy.ticker)
        if current_rank is None or current_rank > profile.strong_zone_max_rank:
            correctness["nonbootstrap_entrant_not_top10_count"] += 1
        previous_rank = previous_ranks.get(buy.ticker)
        if previous_rank is None:
            correctness["postbootstrap_previous_absent_entrant_count"] += 1

        if buy.reason == "TIER_A_VACANCY_FILL":
            if previous_rank is None or previous_rank > profile.retention_zone_max_rank:
                correctness["tier_a_vacancy_priority_violation_count"] += 1
        elif buy.reason == "TIER_B_VACANCY_FILL":
            if not (
                previous_rank is not None
                and profile.retention_zone_max_rank
                < previous_rank
                <= profile.mild_deterioration_max_rank
            ):
                correctness["tier_b_priority_or_permission_violation_count"] += 1
        elif buy.reason == "TIER_C_RESIDUAL_VACANCY_FILL":
            if not (
                previous_rank is not None
                and previous_rank > profile.mild_deterioration_max_rank
            ):
                correctness["tier_c_priority_or_permission_violation_count"] += 1
        elif buy.reason == "SOFT_RANK_GAP_REPLACEMENT":
            challenger = challenger_by_ticker.get(buy.ticker)
            if challenger is None or challenger.state != "A_CORE":
                correctness[
                    "soft_replacement_non_tier_a_or_gap_violation_count"
                ] += 1
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

    for buy in plan.buy_intents:
        if buy.reason == "SOFT_RANK_GAP_REPLACEMENT":
            challenger = challenger_by_ticker.get(buy.ticker)
            if challenger is not None and challenger.state in {"B_NEAR", "C_DISTANT"}:
                correctness["tier_b_c_soft_replacement_violation_count"] += 1

    mandatory_states = {
        "CONFIRMED_MILD_DETERIORATION_EXIT",
        "SEVERE_DETERIORATION_EXIT",
        "UNIVERSE_EXIT",
    }
    mandatory_count = sum(
        obs.state in mandatory_states for obs in plan.incumbent_observations
    )
    retained_before_fill = len(start_positions) - mandatory_count
    vacancies = max(0, profile.target_count_max - retained_before_fill)

    tiers: dict[str, list[Any]] = {"A_CORE": [], "B_NEAR": [], "C_DISTANT": []}
    for obs in plan.challenger_observations:
        if obs.state in tiers:
            tiers[obs.state].append(obs)
    for values in tiers.values():
        values.sort(key=lambda obs: (obs.current_rank, obs.ticker))

    expected: dict[str, list[str]] = {
        "TIER_A_VACANCY_FILL": [],
        "TIER_B_VACANCY_FILL": [],
        "TIER_C_RESIDUAL_VACANCY_FILL": [],
    }
    residual = vacancies
    for state, reason in (
        ("A_CORE", "TIER_A_VACANCY_FILL"),
        ("B_NEAR", "TIER_B_VACANCY_FILL"),
        ("C_DISTANT", "TIER_C_RESIDUAL_VACANCY_FILL"),
    ):
        selected = tiers[state][:residual]
        expected[reason] = [obs.ticker for obs in selected]
        residual -= len(selected)

    actual: dict[str, list[str]] = {
        reason: [
            intent.ticker
            for intent in plan.buy_intents
            if intent.reason == reason
        ]
        for reason in expected
    }
    if actual["TIER_A_VACANCY_FILL"] != expected["TIER_A_VACANCY_FILL"]:
        correctness["tier_a_vacancy_priority_violation_count"] += 1
    if actual["TIER_B_VACANCY_FILL"] != expected["TIER_B_VACANCY_FILL"]:
        correctness["tier_b_priority_or_permission_violation_count"] += 1
    if (
        actual["TIER_C_RESIDUAL_VACANCY_FILL"]
        != expected["TIER_C_RESIDUAL_VACANCY_FILL"]
    ):
        correctness["tier_c_priority_or_permission_violation_count"] += 1

    for obs in plan.incumbent_observations:
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


def replay_once(source: PinnedReplaySource) -> ReplayTrace:
    frame = source.frame.copy()
    if len(frame) != EXPECTED_SCORE_ROWS:
        raise DecisionV3StructuralReplayError(
            f"DECISION_V3_REPLAY_ROW_COUNT_CHANGED:{len(frame)}"
        )
    dates = sorted(pd.Timestamp(x).normalize() for x in frame["date"].drop_duplicates())
    if len(dates) != EXPECTED_SCORE_SESSIONS:
        raise DecisionV3StructuralReplayError(
            f"DECISION_V3_REPLAY_SESSION_COUNT_CHANGED:{len(dates)}"
        )

    blocks = {day: frame.loc[frame["date"].eq(day)].copy() for day in dates}
    state = DecisionV3ShadowState.empty()
    plans: list[DecisionV3Plan] = []
    session_rows: list[dict[str, Any]] = []
    membership_rows: list[dict[str, Any]] = []
    intent_rows: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    fold_boundary_rows: list[dict[str, Any]] = []
    correctness = _empty_correctness()

    previous_verified: VerifiedScoreSession | None = None
    previous_block: pd.DataFrame | None = None
    previous_fold: str | None = None

    for index, day in enumerate(dates):
        block = blocks[day]
        fold_values = block["fold"].astype(str).unique()
        mode_values = block["mode"].astype(str).unique()
        if len(fold_values) != 1 or len(mode_values) != 1:
            raise DecisionV3StructuralReplayError(
                "DECISION_V3_REPLAY_SESSION_METADATA_NOT_UNIQUE"
            )
        fold = str(fold_values[0])
        mode = str(mode_values[0])
        current_verified = _verified_session(block, source)

        if index == 0:
            if state.as_of_session_date is not None or state.positions:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V3_REPLAY_BOOTSTRAP_STATE_NOT_EMPTY"
                )
            if previous_verified is not None:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V3_REPLAY_BOOTSTRAP_PREROLL_DETECTED"
                )
        else:
            expected_previous_day = _iso_day(dates[index - 1])
            if previous_verified is None:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V3_REPLAY_PREVIOUS_SESSION_MISSING"
                )
            if previous_verified.session_date != expected_previous_day:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V3_REPLAY_PREVIOUS_SESSION_NOT_ADJACENT"
                )
            if state.as_of_session_date != expected_previous_day:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V3_REPLAY_STATE_NOT_ADJACENT"
                )
            if state.rule_id != V4_X1_DECISION_V3_GRADED_EVIDENCE_PROFILE_V2.rule_id:
                raise DecisionV3StructuralReplayError(
                    "DECISION_V3_REPLAY_STATE_RULE_ID_MISMATCH"
                )

        start_positions = tuple(state.positions)
        plan = plan_v4_x1_decision_v3_graded_evidence(
            current_verified, previous_verified, state
        )
        shuffled_plan = plan_v4_x1_decision_v3_graded_evidence(
            _verified_session_reversed(block, source),
            None if previous_block is None else _verified_session_reversed(previous_block, source),
            state,
        )
        _validate_plan_permissions(
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
                        buy_reason.get(ticker, "HELD") if index > 0 else "BOOTSTRAP_TOP10"
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
                "target_rank_mean": float(np.mean(target_ranks)) if target_ranks else None,
                "target_rank_median": float(np.median(target_ranks)) if target_ranks else None,
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
                    obs.state == "D_NO_HISTORY" for obs in plan.challenger_observations
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
                    "target_rank_mean": float(np.mean(target_ranks)) if target_ranks else None,
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


def _mild_resolution_metrics(trace: ReplayTrace) -> dict[str, Any]:
    state = trace.state_ledger
    incumbents = state.loc[state["kind"].eq("INCUMBENT")].copy()
    pending = incumbents.loc[
        incumbents["state"].eq("MILD_DETERIORATION_PENDING_1")
    ]
    if pending.empty:
        return {
            "mild_pending_count": 0,
            "mild_next_session_eligible_count": 0,
            "mild_recovery_count": 0,
            "mild_recovery_rate": None,
        }
    by_key = {
        (int(row.session_index), str(row.ticker)): str(row.state)
        for row in incumbents.itertuples(index=False)
    }
    eligible = 0
    recovered = 0
    max_index = int(trace.session_ledger["session_index"].max())
    for row in pending.itertuples(index=False):
        index = int(row.session_index)
        if index >= max_index:
            continue
        eligible += 1
        next_state = by_key.get((index + 1, str(row.ticker)))
        if next_state in {"STRONG_HOLD", "ACCEPTABLE_HOLD"}:
            recovered += 1
    return {
        "mild_pending_count": int(len(pending)),
        "mild_next_session_eligible_count": eligible,
        "mild_recovery_count": recovered,
        "mild_recovery_rate": recovered / eligible if eligible else None,
    }


def _high_churn_attribution(trace: ReplayTrace) -> dict[str, Any]:
    sessions = trace.session_ledger
    intents = trace.intent_ledger
    high = sessions.loc[
        sessions["session_index"].gt(0) & sessions["replacement_count"].ge(3)
    ]
    total = int(len(high))
    if total == 0:
        return {"high_churn_transition_count": 0, "components": {}}
    high_indices = set(high["session_index"].astype(int))
    subset = intents.loc[intents["session_index"].isin(high_indices)]
    components: dict[str, dict[str, float | int]] = {}
    for side, reason in sorted(
        set(zip(subset["side"].astype(str), subset["reason"].astype(str)))
    ):
        indexes = set(
            subset.loc[
                subset["side"].eq(side) & subset["reason"].eq(reason),
                "session_index",
            ].astype(int)
        )
        key = f"{side}:{reason}"
        components[key] = {
            "transition_count": len(indexes),
            "share_of_high_churn_transitions": len(indexes) / total,
            "intent_count": int(
                (subset["side"].eq(side) & subset["reason"].eq(reason)).sum()
            ),
        }
    return {"high_churn_transition_count": total, "components": components}


def _tier_c_diagnostics(trace: ReplayTrace) -> dict[str, Any]:
    intents = trace.intent_ledger
    state = trace.state_ledger
    sessions = trace.session_ledger
    spells = trace.holding_spells

    tier_c = intents.loc[
        intents["side"].eq("BUY_INTENT")
        & intents["reason"].eq("TIER_C_RESIDUAL_VACANCY_FILL")
    ].copy()
    completed_spells = spells.loc[
        spells["completed"].eq(True)
        & spells["entry_reason"].eq("TIER_C_RESIDUAL_VACANCY_FILL")
    ].copy()
    state_map = {
        (int(row.session_index), str(row.ticker)): str(row.state)
        for row in state.loc[state["kind"].eq("INCUMBENT")].itertuples(index=False)
    }
    max_index = int(sessions["session_index"].max())
    next_states: list[str] = []
    severe_sessions: set[int] = set()

    for row in tier_c.itertuples(index=False):
        entry_index = int(row.session_index)
        if entry_index >= max_index:
            next_states.append("RIGHT_CENSORED")
            continue
        next_index = entry_index + 1
        next_state = state_map.get((next_index, str(row.ticker)), "NOT_HELD")
        next_states.append(next_state)
        if next_state == "SEVERE_DETERIORATION_EXIT":
            severe_sessions.add(next_index)

    state_counts = pd.Series(next_states, dtype="object").value_counts().to_dict()
    replacement_sum = int(
        sessions.loc[
            sessions["session_index"].isin(severe_sessions), "replacement_count"
        ].sum()
    )
    durations = pd.to_numeric(
        completed_spells["duration_sessions"], errors="coerce"
    ).dropna()
    one_session_share = float(durations.eq(1).mean()) if not durations.empty else None
    return {
        "tier_c_entrant_count": int(len(tier_c)),
        "tier_c_completed_holding_duration_distribution": _quantiles(durations),
        "tier_c_one_session_holding_share": one_session_share,
        "tier_c_next_session_target_state_distribution": {
            str(key): int(value) for key, value in state_counts.items()
        },
        "tier_c_next_session_severe_exit_count": int(
            sum(value == "SEVERE_DETERIORATION_EXIT" for value in next_states)
        ),
        "tier_c_severe_exit_unique_sessions": len(severe_sessions),
        "replacement_seat_changes_on_tier_c_next_session_severe_exit_sessions": replacement_sum,
    }


def _segment_summary(
    sessions: pd.DataFrame,
    memberships: pd.DataFrame,
) -> dict[str, Any]:
    if sessions.empty:
        return {}
    indexes = set(sessions["session_index"].astype(int))
    member = memberships.loc[memberships["session_index"].isin(indexes)]
    transitions = sessions.loc[sessions["session_index"].gt(0), "replacement_count"]
    ranks = pd.to_numeric(member["rank_consensus"], errors="coerce").dropna()
    return {
        "sessions": int(len(sessions)),
        "mean_replacements": float(transitions.mean()) if not transitions.empty else None,
        "share_ge3_replacements": float(transitions.ge(3).mean()) if not transitions.empty else None,
        "mean_target_rank": float(ranks.mean()) if not ranks.empty else None,
        "mean_target_size": float(sessions["target_size"].mean()),
        "share_target_size_10": float(sessions["target_size"].eq(10).mean()),
        "share_target_size_le8": float(sessions["target_size"].le(8).mean()),
        "target_rank_gt20_name_days": int(ranks.gt(20).sum()),
        "target_rank_gt50_name_days": int(ranks.gt(50).sum()),
        "unfilled_sessions": int(sessions["target_size"].lt(10).sum()),
    }


def summarize_replay(
    primary: ReplayTrace,
    secondary: ReplayTrace,
    source: PinnedReplaySource,
) -> dict[str, Any]:
    sessions = primary.session_ledger
    memberships = primary.membership_ledger
    spells = primary.holding_spells

    transitions = sessions.loc[sessions["session_index"].gt(0)].copy()
    replacements = pd.to_numeric(transitions["replacement_count"], errors="raise")
    completed = spells.loc[spells["completed"].eq(True)].copy()
    completed_durations = pd.to_numeric(
        completed["duration_sessions"], errors="coerce"
    ).dropna()
    right_censored = spells.loc[spells["right_censored"].eq(True)]

    full = sessions.loc[sessions["target_size"].eq(10)]
    all_ranks = pd.to_numeric(memberships["rank_consensus"], errors="coerce").dropna()

    churn = {
        "total_replacements_excluding_bootstrap": int(replacements.sum()),
        "replacement_distribution": _quantiles(replacements),
        "share_replacements_0": float(replacements.eq(0).mean()),
        "share_replacements_1": float(replacements.eq(1).mean()),
        "share_replacements_2": float(replacements.eq(2).mean()),
        "share_replacements_ge3": float(replacements.ge(3).mean()),
        "turnover_ratio_vs_naive": float(
            replacements.sum() / EXPECTED_NAIVE_TOP10_REPLACEMENTS
        ),
        "turnover_ratio_vs_decision_v1": float(
            replacements.sum() / EXPECTED_DECISION_V1_REPLACEMENTS
        ),
        "turnover_ratio_vs_decision_v2": float(
            replacements.sum() / EXPECTED_DECISION_V2_REPLACEMENTS
        ),
    }
    holding = {
        "completed_holding_spell_distribution": _quantiles(completed_durations),
        "one_session_holding_share": (
            float(completed_durations.eq(1).mean()) if not completed_durations.empty else None
        ),
        "le3_session_holding_share": (
            float(completed_durations.le(3).mean()) if not completed_durations.empty else None
        ),
        "right_censored_spell_count": int(len(right_censored)),
    }
    rank_quality = {
        "mean_current_top10_overlap_full_target": (
            float(full["top10_overlap"].mean()) if not full.empty else None
        ),
        "mean_top10_overlap_normalized_all_sessions": float(
            sessions["top10_overlap_normalized"].mean()
        ),
        "mean_current_top20_overlap": float(sessions["top20_overlap"].mean()),
        "mean_target_rank": float(all_ranks.mean()),
        "median_target_rank": float(all_ranks.median()),
        "mean_worst_held_rank": float(
            pd.to_numeric(sessions["target_rank_worst"], errors="coerce").mean()
        ),
        "target_rank_gt20_name_days": int(all_ranks.gt(20).sum()),
        "target_rank_gt50_name_days": int(all_ranks.gt(50).sum()),
        "sessions_with_rank_gt20_holdings": int(
            sessions["target_rank_gt20_count"].gt(0).sum()
        ),
        "sessions_with_rank_gt50_holdings": int(
            sessions["target_rank_gt50_count"].gt(0).sum()
        ),
    }
    capacity = {
        "mean_target_size": float(sessions["target_size"].mean()),
        "median_target_size": float(sessions["target_size"].median()),
        "minimum_target_size": int(sessions["target_size"].min()),
        "share_target_size_10": float(sessions["target_size"].eq(10).mean()),
        "share_target_size_9": float(sessions["target_size"].eq(9).mean()),
        "share_target_size_le8": float(sessions["target_size"].le(8).mean()),
        "underfilled_sessions": int(sessions["target_size"].lt(10).sum()),
        "vacancy_days": int((10 - sessions["target_size"]).sum()),
    }

    mild = _mild_resolution_metrics(primary)
    state_attribution = {
        **mild,
        "confirmed_mild_exit_count": int(sessions["confirmed_mild_exit_count"].sum()),
        "severe_exit_count": int(sessions["severe_exit_count"].sum()),
        "universe_exit_count": int(sessions["universe_exit_count"].sum()),
        "tier_a_vacancy_fill_count": int(sessions["tier_a_vacancy_fill_count"].sum()),
        "tier_b_vacancy_fill_count": int(sessions["tier_b_vacancy_fill_count"].sum()),
        "tier_c_vacancy_fill_count": int(sessions["tier_c_vacancy_fill_count"].sum()),
        "tier_a_soft_replacement_count": int(
            sessions["tier_a_soft_replacement_count"].sum()
        ),
        "tier_d_rejection_count": int(sessions["tier_d_rejection_count"].sum()),
        "sessions_tier_b_prevented_underfill": int(
            (
                sessions["tier_b_vacancy_fill_count"].gt(0)
                & sessions["target_size"].eq(10)
            ).sum()
        ),
        "sessions_tier_c_prevented_underfill": int(
            (
                sessions["tier_c_vacancy_fill_count"].gt(0)
                & sessions["target_size"].eq(10)
            ).sum()
        ),
        "high_churn_mechanism_attribution": _high_churn_attribution(primary),
    }

    blocks: dict[str, Any] = {}
    for block_number in range(1, 7):
        start = (block_number - 1) * 100
        end = block_number * 100
        block_sessions = sessions.loc[
            sessions["session_index"].ge(start) & sessions["session_index"].lt(end)
        ]
        blocks[f"block_{block_number}"] = _segment_summary(block_sessions, memberships)

    folds: dict[str, Any] = {}
    for fold, fold_sessions in sessions.groupby("fold", sort=False):
        folds[str(fold)] = _segment_summary(fold_sessions, memberships)

    determinism = {
        "primary_plan_digest": primary.plan_digest,
        "secondary_plan_digest": secondary.plan_digest,
        "second_pass_exact_match": (
            primary.plan_digest == secondary.plan_digest
            and primary.session_ledger.equals(secondary.session_ledger)
            and primary.membership_ledger.equals(secondary.membership_ledger)
            and primary.intent_ledger.equals(secondary.intent_ledger)
            and primary.state_ledger.equals(secondary.state_ledger)
            and primary.holding_spells.equals(secondary.holding_spells)
        ),
    }

    correctness = dict(primary.correctness)
    correctness["second_pass_nondeterministic_count"] = (
        0 if determinism["second_pass_exact_match"] else 1
    )

    metrics = {
        "churn": churn,
        "holding_persistence": holding,
        "rank_quality": rank_quality,
        "capacity": capacity,
        "state_attribution": state_attribution,
        "tier_c_descriptive_only": _tier_c_diagnostics(primary),
        "stability": {
            "six_fixed_100_session_blocks": blocks,
            "fold_segments": folds,
            "fold_boundary_transition_count": int(len(primary.fold_boundaries)),
        },
        "correctness": correctness,
        "determinism": determinism,
    }
    gates = evaluate_gates(metrics)
    all_pass = all(group["pass"] for group in gates.values())
    verdict = VERDICT_ACCEPT if all_pass else VERDICT_REJECT

    return {
        "schema_version": "decision_v3_graded_evidence_structural_replay_summary_v2",
        "status": verdict,
        "source": {
            "manifest_sha256": sha256_file(source.manifest_path),
            "score_sha256": sha256_file(source.score_path),
            "sessions": int(sessions.shape[0]),
            "rows": int(len(source.frame)),
            "naive_exact_daily_top10_replacements": EXPECTED_NAIVE_TOP10_REPLACEMENTS,
            "decision_v1_replacements": EXPECTED_DECISION_V1_REPLACEMENTS,
            "decision_v2_replacements": EXPECTED_DECISION_V2_REPLACEMENTS,
            "decision_v2_result_manifest_sha256": EXPECTED_DECISION_V2_RESULT_MANIFEST_SHA256,
            "decision_v2_plan_digest": EXPECTED_DECISION_V2_PLAN_DIGEST,
        },
        "guards": {
            "outcome_blind": True,
            "returns_or_pnl_accessed": False,
            "protected_or_fresh_forward_accessed": False,
            "network_or_provider_called": False,
            "score_regenerated": False,
            "fold_reset": False,
            "preroll": False,
            "tier_c_diagnostics_are_tuning_gates": False,
        },
        "metrics": metrics,
        "gates": gates,
        "verdict": verdict,
    }


def evaluate_gates(metrics: dict[str, Any]) -> dict[str, Any]:
    correctness = metrics["correctness"]
    determinism = metrics["determinism"]
    churn = metrics["churn"]
    holding = metrics["holding_persistence"]
    rank_quality = metrics["rank_quality"]
    capacity = metrics["capacity"]

    gate_a_conditions = {
        "target_size_never_over_10": correctness["target_size_over_10_count"] == 0,
        "unique_target": correctness["duplicate_target_count"] == 0,
        "nonbootstrap_entrants_are_current_top10": (
            correctness["nonbootstrap_entrant_not_top10_count"] == 0
        ),
        "previous_absent_postbootstrap_entry_zero": (
            correctness["postbootstrap_previous_absent_entrant_count"] == 0
        ),
        "tier_a_vacancy_priority_integrity": (
            correctness["tier_a_vacancy_priority_violation_count"] == 0
        ),
        "tier_b_priority_permission_integrity": (
            correctness["tier_b_priority_or_permission_violation_count"] == 0
        ),
        "tier_c_priority_permission_integrity": (
            correctness["tier_c_priority_or_permission_violation_count"] == 0
        ),
        "tier_b_c_never_soft_replace": (
            correctness["tier_b_c_soft_replacement_violation_count"] == 0
        ),
        "no_rank_gt50_target_after_processing": (
            correctness["target_rank_gt50_after_processing_count"] == 0
        ),
        "no_second_consecutive_mild_retained": (
            correctness["second_consecutive_rank21_50_retained_count"] == 0
        ),
        "first_mild_observation_retained": (
            correctness["first_mild_observation_retention_violation_count"] == 0
        ),
        "soft_replacement_tier_a_and_gap5_only": (
            correctness["soft_replacement_non_tier_a_or_gap_violation_count"] == 0
        ),
        "universe_exit_not_retained": (
            correctness["universe_exit_retention_violation_count"] == 0
        ),
        "mandatory_exit_not_retained": correctness["mandatory_exit_retained_count"] == 0,
        "row_order_deterministic": correctness["row_order_nondeterministic_count"] == 0,
        "bootstrap_index_integrity": correctness["bootstrap_wrong_index_count"] == 0,
        "rule_id_integrity": correctness["rule_id_mismatch_count"] == 0,
        "second_pass_deterministic": determinism["second_pass_exact_match"],
    }
    gate_b_conditions = {
        "mean_replacements_le_2_25": (
            churn["replacement_distribution"]["mean"] <= GATE_MEAN_REPLACEMENTS_MAX
        ),
        "turnover_vs_naive_le_0_50": (
            churn["turnover_ratio_vs_naive"] <= GATE_TURNOVER_VS_NAIVE_MAX
        ),
        "share_ge3_le_0_35": churn["share_replacements_ge3"] <= GATE_SHARE_GE3_MAX,
    }
    gate_c_conditions = {
        "median_completed_holding_ge_3": (
            holding["completed_holding_spell_distribution"]["median"]
            >= GATE_MEDIAN_HOLDING_MIN
        ),
        "one_session_holding_share_le_0_35": (
            holding["one_session_holding_share"] <= GATE_ONE_SESSION_HOLDING_SHARE_MAX
        ),
    }
    gate_d_conditions = {
        "mean_full_target_top10_overlap_ge_6": (
            rank_quality["mean_current_top10_overlap_full_target"]
            >= GATE_MEAN_FULL_TARGET_TOP10_OVERLAP_MIN
        ),
        "mean_target_rank_le_12": rank_quality["mean_target_rank"] <= GATE_MEAN_TARGET_RANK_MAX,
    }
    gate_e_conditions = {
        "mean_target_size_ge_9": capacity["mean_target_size"] >= GATE_MEAN_TARGET_SIZE_MIN,
        "share_target_size_10_ge_0_70": (
            capacity["share_target_size_10"] >= GATE_SHARE_TARGET_SIZE_10_MIN
        ),
        "share_target_size_le8_le_0_10": (
            capacity["share_target_size_le8"] <= GATE_SHARE_TARGET_SIZE_LE8_MAX
        ),
    }
    gate_f_conditions = {
        "no_rank_gt50_target_after_processing": (
            correctness["target_rank_gt50_after_processing_count"] == 0
        ),
        "no_second_consecutive_mild_retained": (
            correctness["second_consecutive_rank21_50_retained_count"] == 0
        ),
        "universe_disappearance_exits_immediately": (
            correctness["universe_exit_retention_violation_count"] == 0
        ),
    }
    groups = {
        "A_correctness_permission_integrity": gate_a_conditions,
        "B_churn": gate_b_conditions,
        "C_holding_persistence": gate_c_conditions,
        "D_rank_quality": gate_d_conditions,
        "E_capacity": gate_e_conditions,
        "F_no_hidden_stale_state": gate_f_conditions,
    }
    return {
        name: {"pass": all(conditions.values()), "conditions": conditions}
        for name, conditions in groups.items()
    }


def run_structural_replay(source: PinnedReplaySource) -> StructuralReplayResult:
    # Both passes use the same already-loaded pinned rank path and exact same
    # frozen policy. The second pass exists only for the preregistered
    # determinism gate; it is not a second policy evaluation.
    primary = replay_once(source)
    secondary = replay_once(source)
    summary = summarize_replay(primary, secondary, source)
    return StructuralReplayResult(primary=primary, summary=summary)


def _frame_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def write_structural_replay_artifacts(
    result: StructuralReplayResult,
    output_dir: str | Path,
) -> Path:
    destination = Path(output_dir).expanduser().resolve()
    if destination.exists():
        raise DecisionV3StructuralReplayError(
            f"DECISION_V3_REPLAY_OUTPUT_ALREADY_EXISTS:{destination}"
        )
    staging = destination.with_name(destination.name + ".staging")
    if staging.exists():
        raise DecisionV3StructuralReplayError(
            f"DECISION_V3_REPLAY_STAGING_ALREADY_EXISTS:{staging}"
        )
    staging.mkdir(parents=True, exist_ok=False)

    outputs: dict[str, bytes] = {
        "summary.json": (json.dumps(result.summary, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        "decision_session_ledger.csv": _frame_to_csv_bytes(result.primary.session_ledger),
        "decision_membership_ledger.csv": _frame_to_csv_bytes(result.primary.membership_ledger),
        "decision_intent_ledger.csv": _frame_to_csv_bytes(result.primary.intent_ledger),
        "decision_state_ledger.csv": _frame_to_csv_bytes(result.primary.state_ledger),
        "holding_spells.csv": _frame_to_csv_bytes(result.primary.holding_spells),
        "fold_boundary_transitions.csv": _frame_to_csv_bytes(result.primary.fold_boundaries),
    }

    artifact_hashes: dict[str, str] = {}
    for name, content in outputs.items():
        path = staging / name
        path.write_bytes(content)
        artifact_hashes[name] = hashlib.sha256(content).hexdigest()

    manifest = {
        "schema_version": "decision_v3_graded_evidence_structural_replay_manifest_v2",
        "status": result.summary["status"],
        "source": result.summary["source"],
        "guards": result.summary["guards"],
        "plan_digest": result.primary.plan_digest,
        "artifacts": artifact_hashes,
    }
    manifest_content = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (staging / "MANIFEST.json").write_bytes(manifest_content)

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging.rename(destination)
    return destination / "MANIFEST.json"
