from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .decision_economic_comparison import (
    PolicyMembership,
    build_signal_outcomes,
    build_turnover_table,
    derive_naive_top10,
    load_historical_source,
    validate_membership_against_source,
)
from .decision_v2_2_coherent_vacancy_admission import (
    HEAD_ACCEPTABLE_MAX_RANK,
    RULE_ID as V2_2_RULE_ID,
    V2_2_PROFILE,
    plan_decision_v2_2_coherent_vacancy_admission,
)
from .decision_v2_minimal import (
    DecisionV2Plan,
    DecisionV2ShadowState,
    RankObservation,
    RankSession,
    plan_decision_v2_minimal,
)
from .v4_x1_decision_v2_minimal import V4_X1_DECISION_V2_MINIMAL_PROFILE_V1


EXPECTED_V2_STRUCTURAL_REPLACEMENTS = 1435


class DecisionV22EvaluationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Trace:
    policy: str
    dates: tuple[pd.Timestamp, ...]
    targets: tuple[tuple[str, ...], ...]
    plans: tuple[DecisionV2Plan, ...]
    consensus_ranks: tuple[dict[str, int], ...]
    head_ranks: tuple[dict[str, tuple[int, int]], ...]


def _session_inputs(source) -> tuple[
    tuple[RankSession, ...],
    tuple[dict[str, int], ...],
    tuple[dict[str, tuple[int, int]], ...],
]:
    required = {"ticker", "date", "alpha_consensus", "alpha_h5", "alpha_h10"}
    missing = required - set(source.scores.columns)
    if missing:
        raise DecisionV22EvaluationError(f"V2_2_SCORE_COLUMNS_MISSING:{sorted(missing)}")

    sessions: list[RankSession] = []
    consensus_maps: list[dict[str, int]] = []
    head_maps: list[dict[str, tuple[int, int]]] = []
    for date in source.dates:
        block = source.scores.loc[
            source.scores["date"].eq(date),
            ["ticker", "alpha_consensus", "alpha_h5", "alpha_h10"],
        ].copy()
        for col in ("alpha_consensus", "alpha_h5", "alpha_h10"):
            values = pd.to_numeric(block[col], errors="coerce")
            if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
                raise DecisionV22EvaluationError(f"V2_2_SCORE_NONFINITE:{col}:{pd.Timestamp(date).date()}")
            block[col] = values.astype(float)

        consensus = block.sort_values(
            ["alpha_consensus", "ticker"], ascending=[False, True], kind="mergesort"
        ).reset_index(drop=True)
        consensus["rank_consensus"] = np.arange(1, len(consensus) + 1, dtype=int)
        consensus_map = dict(
            zip(consensus["ticker"].astype(str), consensus["rank_consensus"].astype(int), strict=False)
        )

        h5 = block.sort_values(
            ["alpha_h5", "ticker"], ascending=[False, True], kind="mergesort"
        ).reset_index(drop=True)
        h5["rank_h5"] = np.arange(1, len(h5) + 1, dtype=int)
        h5_map = dict(zip(h5["ticker"].astype(str), h5["rank_h5"].astype(int), strict=False))

        h10 = block.sort_values(
            ["alpha_h10", "ticker"], ascending=[False, True], kind="mergesort"
        ).reset_index(drop=True)
        h10["rank_h10"] = np.arange(1, len(h10) + 1, dtype=int)
        h10_map = dict(zip(h10["ticker"].astype(str), h10["rank_h10"].astype(int), strict=False))

        if set(consensus_map) != set(h5_map) or set(consensus_map) != set(h10_map):
            raise DecisionV22EvaluationError("V2_2_HEAD_IDENTITY_CHANGED")

        rows = tuple(
            RankObservation(ticker=ticker, rank=int(rank))
            for ticker, rank in sorted(consensus_map.items(), key=lambda item: (item[1], item[0]))
        )
        sessions.append(
            RankSession(session_date=pd.Timestamp(date).date().isoformat(), rows=rows)
        )
        consensus_maps.append(consensus_map)
        head_maps.append(
            {ticker: (int(h5_map[ticker]), int(h10_map[ticker])) for ticker in consensus_map}
        )

    return tuple(sessions), tuple(consensus_maps), tuple(head_maps)


def _run_v2(
    source,
    sessions: tuple[RankSession, ...],
    consensus_maps: tuple[dict[str, int], ...],
    head_maps: tuple[dict[str, tuple[int, int]], ...],
) -> Trace:
    state = DecisionV2ShadowState.empty()
    targets: list[tuple[str, ...]] = []
    plans: list[DecisionV2Plan] = []
    for index, current in enumerate(sessions):
        previous = None if index == 0 else sessions[index - 1]
        plan = plan_decision_v2_minimal(
            current,
            previous,
            state,
            V4_X1_DECISION_V2_MINIMAL_PROFILE_V1,
        )
        plans.append(plan)
        targets.append(tuple(plan.target_positions))
        state = DecisionV2ShadowState.from_plan(plan)
    return Trace("DECISION_V2", source.dates, tuple(targets), tuple(plans), consensus_maps, head_maps)


def _run_v22(
    source,
    sessions: tuple[RankSession, ...],
    consensus_maps: tuple[dict[str, int], ...],
    head_maps: tuple[dict[str, tuple[int, int]], ...],
) -> Trace:
    state = DecisionV2ShadowState.empty()
    targets: list[tuple[str, ...]] = []
    plans: list[DecisionV2Plan] = []
    for index, current in enumerate(sessions):
        previous = None if index == 0 else sessions[index - 1]
        plan = plan_decision_v2_2_coherent_vacancy_admission(
            current,
            previous,
            state,
            head_maps[index],
            V2_2_PROFILE,
        )
        plans.append(plan)
        targets.append(tuple(plan.target_positions))
        state = DecisionV2ShadowState.from_plan(plan)
    return Trace("DECISION_V2_2", source.dates, tuple(targets), tuple(plans), consensus_maps, head_maps)


def _membership(trace: Trace, source_root: str, source_manifest_sha256: str) -> PolicyMembership:
    return PolicyMembership(
        policy=trace.policy,
        by_date={date: target for date, target in zip(trace.dates, trace.targets, strict=True)},
        source_root=source_root,
        source_manifest_sha256=source_manifest_sha256,
    )


def _holding_durations(targets: tuple[tuple[str, ...], ...]) -> list[int]:
    active: dict[str, int] = {}
    completed: list[int] = []
    for index, target in enumerate(targets):
        current = set(target)
        previous = set(active)
        for ticker in previous - current:
            completed.append(index - active.pop(ticker))
        for ticker in current - previous:
            active[ticker] = index
    return completed


def _structural(trace: Trace, turnover: pd.DataFrame) -> dict[str, Any]:
    occupied_ranks: list[int] = []
    top10_overlap: list[int] = []
    top20_overlap: list[int] = []
    rank_gt50 = 0
    coherent_vacancy_fills = 0
    ordinary_soft_buys = 0

    for target, ranks, plan in zip(trace.targets, trace.consensus_ranks, trace.plans, strict=True):
        values = [int(ranks[ticker]) for ticker in target]
        occupied_ranks.extend(values)
        top10_overlap.append(sum(rank <= 10 for rank in values))
        top20_overlap.append(sum(rank <= 20 for rank in values))
        rank_gt50 += sum(rank > 50 for rank in values)
        coherent_vacancy_fills += sum(
            intent.side == "BUY_INTENT" and intent.reason == "QUALIFIED_COHERENT_VACANCY_FILL"
            for intent in plan.buy_intents
        )
        ordinary_soft_buys += sum(
            intent.side == "BUY_INTENT" and intent.reason == "SOFT_RANK_GAP_REPLACEMENT"
            for intent in plan.buy_intents
        )

    block = turnover.loc[turnover["policy"].eq(trace.policy)].copy()
    nonbootstrap = block.loc[block["session_index"].gt(0)]
    sizes = block["target_size"].astype(int)
    durations = _holding_durations(trace.targets)
    return {
        "total_replacements_excluding_bootstrap": int(nonbootstrap["replacement_count_proxy"].sum()),
        "mean_replacements_per_transition": float(nonbootstrap["replacement_count_proxy"].mean()),
        "median_completed_holding_sessions": float(np.median(durations)) if durations else None,
        "mean_target_rank": float(np.mean(occupied_ranks)),
        "mean_top10_overlap": float(np.mean(top10_overlap)),
        "mean_top20_overlap": float(np.mean(top20_overlap)),
        "mean_target_size": float(sizes.mean()),
        "underfilled_sessions": int(sizes.lt(10).sum()),
        "vacancy_days": int((10 - sizes).sum()),
        "minimum_target_size": int(sizes.min()),
        "target_rank_gt50_name_days": int(rank_gt50),
        "coherent_vacancy_fills": int(coherent_vacancy_fills),
        "ordinary_soft_replacement_buys": int(ordinary_soft_buys),
    }


def _pairwise(outcomes: pd.DataFrame, left: str, right: str, horizon: int) -> dict[str, Any]:
    lhs = outcomes.loc[outcomes["policy"].eq(left)].copy().set_index("date")
    rhs = outcomes.loc[outcomes["policy"].eq(right)].copy().set_index("date")
    support = lhs[f"h{horizon}_complete_support"].astype(bool) & rhs[f"h{horizon}_complete_support"].astype(bool)
    dates = lhs.index[support]
    gross_left = lhs.loc[dates, f"h{horizon}_gross_basket_return"].astype(float)
    gross_right = rhs.loc[dates, f"h{horizon}_gross_basket_return"].astype(float)
    primary_left = lhs.loc[dates, f"h{horizon}_net_proxy_primary"].astype(float)
    primary_right = rhs.loc[dates, f"h{horizon}_net_proxy_primary"].astype(float)
    gross_delta = gross_left - gross_right
    primary_delta = primary_left - primary_right
    return {
        "common_support_dates": int(len(dates)),
        "gross_delta_mean": float(gross_delta.mean()) if len(dates) else None,
        "gross_delta_median": float(gross_delta.median()) if len(dates) else None,
        "gross_win_share": float(gross_delta.gt(0).mean()) if len(dates) else None,
        "primary_delta_mean": float(primary_delta.mean()) if len(dates) else None,
        "primary_delta_median": float(primary_delta.median()) if len(dates) else None,
        "primary_win_share": float(primary_delta.gt(0).mean()) if len(dates) else None,
    }


def run_v2_2_evaluation(historical_root: str) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    source = load_historical_source(historical_root)
    sessions, consensus_maps, head_maps = _session_inputs(source)
    v2 = _run_v2(source, sessions, consensus_maps, head_maps)
    v22 = _run_v22(source, sessions, consensus_maps, head_maps)

    v2_membership = _membership(v2, str(source.root), source.manifest_sha256)
    v22_membership = _membership(v22, str(source.root), source.manifest_sha256)
    naive = derive_naive_top10(source)
    memberships = (v2_membership, v22_membership, naive)
    validate_membership_against_source(source, memberships)
    turnover = build_turnover_table(memberships, source.dates)
    outcomes = build_signal_outcomes(source, memberships, turnover)

    v2_struct = _structural(v2, turnover)
    if v2_struct["total_replacements_excluding_bootstrap"] != EXPECTED_V2_STRUCTURAL_REPLACEMENTS:
        raise DecisionV22EvaluationError(
            "V2_REPRODUCTION_MISMATCH:"
            f"{v2_struct['total_replacements_excluding_bootstrap']}!={EXPECTED_V2_STRUCTURAL_REPLACEMENTS}"
        )
    v22_struct = _structural(v22, turnover)

    structural_delta = {
        key: (
            None
            if v2_struct[key] is None or v22_struct[key] is None
            else float(v22_struct[key]) - float(v2_struct[key])
        )
        for key in v2_struct
        if key not in {"coherent_vacancy_fills", "ordinary_soft_replacement_buys"}
    }

    summary: dict[str, Any] = {
        "schema_version": "decision_v2_2_coherent_vacancy_admission_evaluation_v1",
        "status": "COMPLETE_DEVELOPMENT_V2_2_SINGLE_CALIBRATION_EVALUATION",
        "rule": {
            "rule_id": V2_2_RULE_ID,
            "only_change": "V2_QUALIFIED_CHALLENGER_MAY_FILL_REAL_VACANCY_ONLY_IF_CURRENT_H5_AND_H10_HEAD_RANKS_ARE_BOTH_LE20",
            "head_acceptable_max_rank": HEAD_ACCEPTABLE_MAX_RANK,
            "head_boundary_source": "REUSE_FROZEN_V2_RETENTION_ZONE_20_NOT_SEARCHED",
            "v2_exit_logic_changed": False,
            "v2_previous_rank_confirmation_changed": False,
            "v2_underfill_permission_changed": False,
            "v2_soft_replacement_changed": False,
            "noncoherent_challenger_still_soft_replace_eligible": True,
        },
        "interpretation_boundary": {
            "development_window_only": True,
            "single_candidate_only": True,
            "threshold_sweep": False,
            "alpha_refit_or_rescore": False,
            "economic_measure_is_target_outcome_not_executable_nav": True,
        },
        "source": {
            "manifest_sha256": source.manifest_sha256,
            "score_sha256": source.score_sha256,
            "target_sha256": source.target_sha256,
            "sessions": len(source.dates),
        },
        "structural": {
            "DECISION_V2": v2_struct,
            "DECISION_V2_2": v22_struct,
            "V2_2_MINUS_V2": structural_delta,
        },
        "economic": {},
    }
    for horizon in (5, 10):
        summary["economic"][f"H{horizon}"] = {
            "V2_2_MINUS_V2": _pairwise(outcomes, "DECISION_V2_2", "DECISION_V2", horizon),
            "V2_2_MINUS_NAIVE": _pairwise(outcomes, "DECISION_V2_2", "NAIVE_TOP10", horizon),
            "V2_MINUS_NAIVE": _pairwise(outcomes, "DECISION_V2", "NAIVE_TOP10", horizon),
        }

    return summary, outcomes, turnover
