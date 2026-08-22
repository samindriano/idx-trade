from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any

import numpy as np
import pandas as pd

from .decision_economic_comparison import (
    REFERENCE_NAV_RP,
    SEAT_WEIGHT,
    STAMP_DUTY_GROSS_TURNOVER_THRESHOLD_RP,
    STAMP_DUTY_RP,
    HistoricalSource,
    load_historical_source,
)
from .decision_v2_1_conservative_severe_replacement import (
    RULE_ID as V2_1_RULE_ID,
    V2_1_PROFILE,
    plan_decision_v2_1_conservative_severe_replacement,
)
from .decision_v2_minimal import (
    DecisionV2Plan,
    DecisionV2Profile,
    DecisionV2ShadowState,
    RankObservation,
    RankSession,
    plan_decision_v2_minimal,
)
from .v4_x1_decision_v2_minimal import V4_X1_DECISION_V2_MINIMAL_PROFILE_V1


EXPECTED_V2_STRUCTURAL_REPLACEMENTS = 1435
PRIMARY_BUY_BPS = 25.0  # 15 fee + 10 slippage
PRIMARY_SELL_BPS = 35.0  # 25 fee + 10 slippage


class DecisionV21EvaluationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PolicyTrace:
    policy: str
    profile: DecisionV2Profile | None
    plans: tuple[DecisionV2Plan | None, ...]
    dates: tuple[pd.Timestamp, ...]
    targets: tuple[tuple[str, ...], ...]
    rank_maps: tuple[dict[str, int], ...]


def _rank_sessions(source: HistoricalSource) -> tuple[tuple[RankSession, ...], tuple[dict[str, int], ...]]:
    sessions: list[RankSession] = []
    rank_maps: list[dict[str, int]] = []
    for date in source.dates:
        block = source.scores.loc[source.scores["date"].eq(date), ["ticker", "alpha_consensus"]].copy()
        block = block.sort_values(
            ["alpha_consensus", "ticker"],
            ascending=[False, True],
            kind="mergesort",
        ).reset_index(drop=True)
        block["rank"] = np.arange(1, len(block) + 1, dtype=int)
        rows = tuple(
            RankObservation(ticker=str(row.ticker), rank=int(row.rank))
            for row in block[["ticker", "rank"]].itertuples(index=False)
        )
        sessions.append(RankSession(session_date=pd.Timestamp(date).date().isoformat(), rows=rows))
        rank_maps.append(dict(zip(block["ticker"].astype(str), block["rank"].astype(int), strict=False)))
    return tuple(sessions), tuple(rank_maps)


def _run_decision_policy(
    *,
    name: str,
    source: HistoricalSource,
    sessions: tuple[RankSession, ...],
    rank_maps: tuple[dict[str, int], ...],
    profile: DecisionV2Profile,
    planner: Callable[[RankSession, RankSession | None, DecisionV2ShadowState, DecisionV2Profile], DecisionV2Plan],
) -> PolicyTrace:
    state = DecisionV2ShadowState.empty()
    plans: list[DecisionV2Plan] = []
    targets: list[tuple[str, ...]] = []
    for index, current in enumerate(sessions):
        previous = None if index == 0 else sessions[index - 1]
        plan = planner(current, previous, state, profile)
        plans.append(plan)
        targets.append(tuple(plan.target_positions))
        state = DecisionV2ShadowState.from_plan(plan)
    return PolicyTrace(
        policy=name,
        profile=profile,
        plans=tuple(plans),
        dates=source.dates,
        targets=tuple(targets),
        rank_maps=rank_maps,
    )


def _run_naive(
    source: HistoricalSource,
    rank_maps: tuple[dict[str, int], ...],
) -> PolicyTrace:
    targets: list[tuple[str, ...]] = []
    for ranks in rank_maps:
        targets.append(
            tuple(
                ticker
                for ticker, _ in sorted(ranks.items(), key=lambda item: (item[1], item[0]))[:10]
            )
        )
    return PolicyTrace(
        policy="NAIVE_TOP10",
        profile=None,
        plans=tuple(None for _ in source.dates),
        dates=source.dates,
        targets=tuple(targets),
        rank_maps=rank_maps,
    )


def _transition_counts(trace: PolicyTrace) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    previous: set[str] = set()
    for index, (date, target) in enumerate(zip(trace.dates, trace.targets, strict=True)):
        current = set(target)
        buys = current - previous
        sells = previous - current
        gross_turnover_rp = REFERENCE_NAV_RP * SEAT_WEIGHT * (len(buys) + len(sells))
        variable = SEAT_WEIGHT * (
            len(buys) * PRIMARY_BUY_BPS + len(sells) * PRIMARY_SELL_BPS
        ) / 10_000.0
        stamp = 0.0
        if gross_turnover_rp > STAMP_DUTY_GROSS_TURNOVER_THRESHOLD_RP:
            stamp = STAMP_DUTY_RP / REFERENCE_NAV_RP
        rows.append(
            {
                "policy": trace.policy,
                "session_index": index,
                "date": pd.Timestamp(date),
                "target_size": len(current),
                "buy_count": len(buys),
                "sell_count": len(sells),
                "replacement_count": 0 if index == 0 else max(len(buys), len(sells)),
                "primary_cost_fraction": variable + stamp,
            }
        )
        previous = current
    return pd.DataFrame(rows)


def _holding_durations(trace: PolicyTrace) -> list[int]:
    active: dict[str, int] = {}
    completed: list[int] = []
    for index, target in enumerate(trace.targets):
        current = set(target)
        previous = set(active)
        for ticker in previous - current:
            completed.append(index - active.pop(ticker))
        for ticker in current - previous:
            active[ticker] = index
    return completed


def _structural_summary(trace: PolicyTrace, transitions: pd.DataFrame) -> dict[str, Any]:
    occupied_ranks: list[int] = []
    top10_overlap: list[int] = []
    top20_overlap: list[int] = []
    full_top10_overlap: list[int] = []
    pending_gt50_name_days = 0
    severe_permission_count = 0

    for index, (target, ranks) in enumerate(zip(trace.targets, trace.rank_maps, strict=True)):
        target_ranks = [int(ranks[ticker]) for ticker in target]
        occupied_ranks.extend(target_ranks)
        t10 = sum(rank <= 10 for rank in target_ranks)
        t20 = sum(rank <= 20 for rank in target_ranks)
        top10_overlap.append(t10)
        top20_overlap.append(t20)
        if len(target) == 10:
            full_top10_overlap.append(t10)
        pending_gt50_name_days += sum(rank > 50 for rank in target_ranks)
        plan = trace.plans[index]
        if plan is not None:
            severe_permission_count += sum(
                intent.side == "SELL_INTENT"
                and intent.reason == "ESTABLISHED_SEVERE_PENDING_REPLACEMENT"
                for intent in plan.sell_intents
            )

    nonbootstrap = transitions.loc[transitions["session_index"].gt(0)]
    durations = _holding_durations(trace)
    sizes = transitions["target_size"].astype(int)
    return {
        "total_replacements_excluding_bootstrap": int(nonbootstrap["replacement_count"].sum()),
        "mean_replacements_per_transition": float(nonbootstrap["replacement_count"].mean()),
        "share_transitions_ge3_replacements": float(nonbootstrap["replacement_count"].ge(3).mean()),
        "median_completed_holding_sessions": float(np.median(durations)) if durations else None,
        "one_session_completed_holding_share": float(np.mean(np.asarray(durations) == 1)) if durations else None,
        "mean_target_rank": float(np.mean(occupied_ranks)),
        "mean_top10_overlap_all_sessions": float(np.mean(top10_overlap)),
        "mean_top20_overlap_all_sessions": float(np.mean(top20_overlap)),
        "mean_full_target_top10_overlap": float(np.mean(full_top10_overlap)),
        "mean_target_size": float(sizes.mean()),
        "share_target_size_10": float(sizes.eq(10).mean()),
        "share_target_size_le8": float(sizes.le(8).mean()),
        "underfilled_sessions": int(sizes.lt(10).sum()),
        "vacancy_days": int((10 - sizes).sum()),
        "target_rank_gt50_name_days": int(pending_gt50_name_days),
        "v2_1_established_severe_replacements": int(severe_permission_count),
    }


def _economic_rows(
    source: HistoricalSource,
    trace: PolicyTrace,
    transitions: pd.DataFrame,
) -> pd.DataFrame:
    target = source.targets.set_index(["date", "ticker"], drop=False)
    cost_by_date = transitions.set_index("date")["primary_cost_fraction"].to_dict()
    rows: list[dict[str, Any]] = []
    for date, tickers in zip(trace.dates, trace.targets, strict=True):
        row: dict[str, Any] = {
            "policy": trace.policy,
            "date": pd.Timestamp(date),
            "target_size": len(tickers),
            "cash_weight": (10 - len(tickers)) * SEAT_WEIGHT,
            "primary_cost_fraction": float(cost_by_date[pd.Timestamp(date)]),
        }
        for horizon in (5, 10):
            returns: list[float] = []
            complete = True
            for ticker in tickers:
                item = target.loc[(pd.Timestamp(date), ticker)]
                if isinstance(item, pd.DataFrame):
                    raise DecisionV21EvaluationError("TARGET_DUPLICATE_IDENTITY")
                state = str(item[f"target_state_h{horizon}"])
                value = item[f"r{horizon}"]
                if state != f"TARGET_H{horizon}_AVAILABLE" or pd.isna(value) or not np.isfinite(float(value)):
                    complete = False
                    break
                returns.append(float(value))
            gross = float(SEAT_WEIGHT * np.sum(returns)) if complete else np.nan
            row[f"h{horizon}_complete_support"] = bool(complete)
            row[f"h{horizon}_gross"] = gross
            row[f"h{horizon}_primary"] = (
                gross - row["primary_cost_fraction"] if complete else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def _pairwise(a: pd.DataFrame, b: pd.DataFrame, horizon: int) -> dict[str, Any]:
    left = a.set_index("date")
    right = b.set_index("date")
    common = left[f"h{horizon}_complete_support"].astype(bool) & right[f"h{horizon}_complete_support"].astype(bool)
    dates = left.index[common]
    gross_delta = left.loc[dates, f"h{horizon}_gross"] - right.loc[dates, f"h{horizon}_gross"]
    primary_delta = left.loc[dates, f"h{horizon}_primary"] - right.loc[dates, f"h{horizon}_primary"]
    return {
        "common_support_dates": int(len(dates)),
        "left_gross_mean": float(left.loc[dates, f"h{horizon}_gross"].mean()) if len(dates) else None,
        "right_gross_mean": float(right.loc[dates, f"h{horizon}_gross"].mean()) if len(dates) else None,
        "gross_delta_mean": float(gross_delta.mean()) if len(dates) else None,
        "gross_delta_median": float(gross_delta.median()) if len(dates) else None,
        "gross_win_share": float(gross_delta.gt(0).mean()) if len(dates) else None,
        "left_primary_mean": float(left.loc[dates, f"h{horizon}_primary"].mean()) if len(dates) else None,
        "right_primary_mean": float(right.loc[dates, f"h{horizon}_primary"].mean()) if len(dates) else None,
        "primary_delta_mean": float(primary_delta.mean()) if len(dates) else None,
        "primary_delta_median": float(primary_delta.median()) if len(dates) else None,
        "primary_win_share": float(primary_delta.gt(0).mean()) if len(dates) else None,
    }


def run_v2_1_evaluation(historical_root: str) -> tuple[dict[str, Any], pd.DataFrame]:
    source = load_historical_source(historical_root)
    sessions, rank_maps = _rank_sessions(source)

    v2 = _run_decision_policy(
        name="DECISION_V2",
        source=source,
        sessions=sessions,
        rank_maps=rank_maps,
        profile=V4_X1_DECISION_V2_MINIMAL_PROFILE_V1,
        planner=plan_decision_v2_minimal,
    )
    v21 = _run_decision_policy(
        name="DECISION_V2_1",
        source=source,
        sessions=sessions,
        rank_maps=rank_maps,
        profile=V2_1_PROFILE,
        planner=plan_decision_v2_1_conservative_severe_replacement,
    )
    naive = _run_naive(source, rank_maps)

    transition_frames = {
        trace.policy: _transition_counts(trace) for trace in (v2, v21, naive)
    }
    v2_struct = _structural_summary(v2, transition_frames["DECISION_V2"])
    if v2_struct["total_replacements_excluding_bootstrap"] != EXPECTED_V2_STRUCTURAL_REPLACEMENTS:
        raise DecisionV21EvaluationError(
            "V2_REPRODUCTION_MISMATCH:"
            f"{v2_struct['total_replacements_excluding_bootstrap']}!={EXPECTED_V2_STRUCTURAL_REPLACEMENTS}"
        )
    v21_struct = _structural_summary(v21, transition_frames["DECISION_V2_1"])

    economic_frames = {
        trace.policy: _economic_rows(source, trace, transition_frames[trace.policy])
        for trace in (v2, v21, naive)
    }

    structural_delta = {
        key: (
            None
            if v21_struct[key] is None or v2_struct[key] is None
            else float(v21_struct[key]) - float(v2_struct[key])
        )
        for key in v2_struct
        if key != "v2_1_established_severe_replacements"
    }

    summary: dict[str, Any] = {
        "schema_version": "decision_v2_1_conservative_severe_replacement_evaluation_v1",
        "status": "COMPLETE_DEVELOPMENT_V2_1_SINGLE_CALIBRATION_EVALUATION",
        "rule": {
            "rule_id": V2_1_RULE_ID,
            "only_change": "FIRST_DAY_RANK_GT50_PENDING_MAY_BE_REPLACED_ONE_FOR_ONE_BY_UNUSED_CURRENT_TOP10_PREVIOUS_TOP10_CHALLENGER_AFTER_V2_VACANCY_FILL_BEFORE_ORDINARY_SOFT_REPLACE",
            "severe_pending_min_rank": 51,
            "established_challenger_previous_rank_max": 10,
            "v2_vacancy_rule_changed": False,
            "v2_underfill_permission_changed": False,
            "v2_confirmed_exit_rule_changed": False,
            "v2_ordinary_soft_gap_changed": False,
        },
        "interpretation_boundary": {
            "development_window_only": True,
            "single_candidate_only": True,
            "threshold_sweep": False,
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
            "DECISION_V2_1": v21_struct,
            "V2_1_MINUS_V2": structural_delta,
        },
        "economic": {},
    }
    for horizon in (5, 10):
        summary["economic"][f"H{horizon}"] = {
            "V2_1_MINUS_V2": _pairwise(
                economic_frames["DECISION_V2_1"], economic_frames["DECISION_V2"], horizon
            ),
            "V2_1_MINUS_NAIVE": _pairwise(
                economic_frames["DECISION_V2_1"], economic_frames["NAIVE_TOP10"], horizon
            ),
            "V2_MINUS_NAIVE": _pairwise(
                economic_frames["DECISION_V2"], economic_frames["NAIVE_TOP10"], horizon
            ),
        }

    daily = pd.concat(
        [economic_frames["DECISION_V2"], economic_frames["DECISION_V2_1"], economic_frames["NAIVE_TOP10"]],
        ignore_index=True,
    )
    return summary, daily
