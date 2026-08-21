from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any

import pandas as pd

from .decision_v3_failure_diagnosis import (
    DecisionV3FailureDiagnosisResult,
    EXPECTED_SESSIONS,
)


def _safe_rate(series: pd.Series) -> float | None:
    return None if len(series) == 0 else float(series.astype(bool).mean())


def _numeric_summary(series: pd.Series) -> dict[str, float | int | None]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if values.empty:
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
        "count": int(len(values)),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "p75": float(values.quantile(0.75)),
        "p90": float(values.quantile(0.90)),
        "p95": float(values.quantile(0.95)),
        "max": float(values.max()),
    }


def _tier_summary(frame: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for tier in ("A", "B", "C", "A_SOFT"):
        part = frame.loc[frame["entry_tier"].eq(tier)].copy()
        if part.empty:
            result[tier] = {"entries": 0}
            continue
        completed = part.loc[part["completed"].astype(bool)].copy()
        observable_next = part.loc[part["next_session_observable"].astype(bool)].copy()
        result[tier] = {
            "entries": int(len(part)),
            "completed_spells": int(len(completed)),
            "right_censored_spells": int(part["right_censored"].astype(bool).sum()),
            "duration_sessions": _numeric_summary(part["duration_sessions"]),
            "one_session_holding_share": _safe_rate(completed["one_session_holding"]) if len(completed) else None,
            "next_session_observable_entries": int(len(observable_next)),
            "next_session_severe_exit_count": int(observable_next["next_session_severe_exit"].sum()),
            "next_session_severe_exit_rate": _safe_rate(observable_next["next_session_severe_exit"]) if len(observable_next) else None,
            "eventual_exit_observable_completed_spells": int(len(completed)),
            "eventual_severe_exit_count": int(completed["eventual_severe_exit"].sum()),
            "eventual_severe_exit_rate": _safe_rate(completed["eventual_severe_exit"]) if len(completed) else None,
            "entry_high_churn_share": _safe_rate(part["entry_session_high_churn_ge3"]),
        }
    return result


def _recompute_block_next_rates(blocks: pd.DataFrame, lifecycle: pd.DataFrame) -> pd.DataFrame:
    output = blocks.copy()
    for block in range(1, 7):
        mask = output["block"].eq(block)
        entries = lifecycle.loc[lifecycle["entry_block"].eq(block)]
        for tier in ("A", "B", "C", "A_SOFT"):
            part = entries.loc[entries["entry_tier"].eq(tier)]
            observable = part.loc[part["next_session_observable"].astype(bool)]
            completed = part.loc[part["completed"].astype(bool)]
            prefix = tier.lower()
            output.loc[mask, f"tier_{prefix}_next_severe_rate"] = (
                _safe_rate(observable["next_session_severe_exit"]) if len(observable) else None
            )
            output.loc[mask, f"tier_{prefix}_one_session_share"] = (
                _safe_rate(completed["one_session_holding"]) if len(completed) else None
            )
    return output


def _stress_lifecycle_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    part = frame.loc[frame["entry_tier"].eq("C")]
    observable = part.loc[part["next_session_observable"].astype(bool)]
    completed = part.loc[part["completed"].astype(bool)]
    return {
        "tier_c_entries": int(len(part)),
        "tier_c_next_session_observable_entries": int(len(observable)),
        "tier_c_next_severe_rate": _safe_rate(observable["next_session_severe_exit"]) if len(observable) else None,
        "tier_c_one_session_share": _safe_rate(completed["one_session_holding"]) if len(completed) else None,
    }


def apply_terminal_observation_boundary(
    result: DecisionV3FailureDiagnosisResult,
) -> DecisionV3FailureDiagnosisResult:
    lifecycle = result.entry_lifecycle.copy()
    lifecycle["next_session_observable"] = lifecycle["entry_index"].astype(int).lt(
        EXPECTED_SESSIONS - 1
    )

    summary = deepcopy(result.summary)
    summary["entry_tier_lifecycle"] = _tier_summary(lifecycle)
    summary["terminal_observation_boundary"] = {
        "next_session_unobservable_entries": int((~lifecycle["next_session_observable"]).sum()),
        "next_session_rates_exclude_terminal_entries": True,
        "eventual_exit_rates_use_completed_spells_only": True,
        "right_censored_spells_never_count_as_nonsevere_eventual_exits": True,
    }

    blocks = _recompute_block_next_rates(result.block_summary, lifecycle)
    summary["block_mechanism_summary"] = blocks.to_dict(orient="records")

    stress = result.severe_exit_sessions.loc[result.severe_exit_sessions["block"].isin([3, 6])]
    reference = result.severe_exit_sessions.loc[result.severe_exit_sessions["block"].isin([1, 2, 4, 5])]
    stress_life = lifecycle.loc[lifecycle["entry_block"].isin([3, 6])]
    reference_life = lifecycle.loc[lifecycle["entry_block"].isin([1, 2, 4, 5])]

    def transition_metrics(frame: pd.DataFrame) -> dict[str, Any]:
        if frame.empty:
            return {"transitions": 0}
        return {
            "transitions": int(len(frame)),
            "mean_replacements": float(frame["replacement_count"].mean()),
            "high_churn_share": _safe_rate(frame["high_churn_ge3"]),
            "severe_exits_per_transition": float(frame["severe_exit_count"].mean()),
            "severe_exit_session_share": _safe_rate(frame["severe_exit_session"]),
            "vacancy_fills_per_transition": float(frame["vacancy_fill_count"].mean()),
            "soft_replacements_per_transition": float(frame["soft_replacement_count"].mean()),
            "severe_refill_overlap_share": _safe_rate(frame["severe_and_vacancy_fill_overlap"]),
        }

    summary["block_3_6_vs_reference"] = {
        "stress_blocks_3_6": {**transition_metrics(stress), **_stress_lifecycle_metrics(stress_life)},
        "reference_blocks_1_2_4_5": {**transition_metrics(reference), **_stress_lifecycle_metrics(reference_life)},
        "interpretation": "Side-by-side descriptive mechanism intensity only; no regime rule or block-specific policy is authorized.",
    }

    return replace(result, summary=summary, entry_lifecycle=lifecycle, block_summary=blocks)
