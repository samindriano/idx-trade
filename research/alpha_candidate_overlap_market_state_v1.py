"""Outcome-blind candidate Top-30 overlap conditional on market-breadth state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from alpha_candidate_component_anatomy_v1 import (
        FEATURE_COLUMNS,
        PANEL_COLUMNS,
        build_components,
        prepare_surface,
        sha256_file,
    )
except ModuleNotFoundError:
    from research.alpha_candidate_component_anatomy_v1 import (
        FEATURE_COLUMNS,
        PANEL_COLUMNS,
        build_components,
        prepare_surface,
        sha256_file,
    )


TOP_K = 30
CANDIDATE_RANKS = {
    "C1": "rank_C1_residual_reversal_5_v1",
    "C2": "rank_C2_participation_confirmation_5_v1",
    "C4": "rank_C4_path_efficiency_reversal_20_v1",
}
PAIR_NAMES = ("C1_C2", "C1_C4", "C2_C4")
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def finite_float(value: object) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if np.isfinite(converted) else None


def classify_market_state(ret_pos_share: float, activity_pos_share: float) -> str:
    if ret_pos_share >= 0.5 and activity_pos_share >= 0.5:
        return "HIGH_HIGH"
    if ret_pos_share >= 0.5 and activity_pos_share < 0.5:
        return "RET_HIGH_ACT_LOW"
    if ret_pos_share < 0.5 and activity_pos_share >= 0.5:
        return "RET_LOW_ACT_HIGH"
    return "LOW_LOW"


def market_state_table(surface: pd.DataFrame) -> pd.DataFrame:
    valid = surface.loc[
        surface["eligible_decision_universe"]
        & surface["ret_5"].notna()
        & surface["c2_log_abnormal_turnover"].notna(),
        ["ticker", "date", "ret_5", "c2_log_abnormal_turnover"],
    ].copy()
    if valid.empty:
        return pd.DataFrame()
    valid["ret_pos"] = valid["ret_5"] >= 0.0
    valid["activity_pos"] = valid["c2_log_abnormal_turnover"] >= 0.0
    state = valid.groupby("date", sort=True).agg(
        ret_pos_share=("ret_pos", "mean"),
        activity_pos_share=("activity_pos", "mean"),
        finite_count=("ticker", "size"),
    )
    state["market_state"] = [classify_market_state(r, a) for r, a in zip(state["ret_pos_share"], state["activity_pos_share"])]
    return state


def candidate_selections(surface: pd.DataFrame) -> dict[str, dict[pd.Timestamp, set[str]]]:
    output: dict[str, dict[pd.Timestamp, set[str]]] = {}
    for candidate, rank_column in CANDIDATE_RANKS.items():
        valid = surface.loc[surface["eligible_decision_universe"] & surface[rank_column].notna(), ["ticker", "date", rank_column]].copy()
        selections: dict[pd.Timestamp, set[str]] = {}
        for date, group in valid.groupby("date", sort=True):
            ordered = group.sort_values([rank_column, "ticker"], ascending=[False, True], kind="mergesort")
            if len(ordered) >= TOP_K:
                selections[pd.Timestamp(date)] = set(ordered.head(TOP_K)["ticker"].astype(str))
        output[candidate] = selections
    return output


def overlap_rows(surface: pd.DataFrame) -> pd.DataFrame:
    states = market_state_table(surface)
    selections = candidate_selections(surface)
    common_dates = sorted(set(states.index) & set(selections["C1"]) & set(selections["C2"]) & set(selections["C4"]))
    rows: list[dict[str, Any]] = []
    for date in common_dates:
        row: dict[str, Any] = {
            "date": date,
            "market_state": states.loc[date, "market_state"],
            "ret_pos_share": float(states.loc[date, "ret_pos_share"]),
            "activity_pos_share": float(states.loc[date, "activity_pos_share"]),
        }
        for name, left, right in (("C1_C2", "C1", "C2"), ("C1_C4", "C1", "C4"), ("C2_C4", "C2", "C4")):
            intersection = len(selections[left][date] & selections[right][date])
            union = len(selections[left][date] | selections[right][date])
            row[f"{name}_overlap_fraction"] = float(intersection / TOP_K)
            row[f"{name}_jaccard"] = float(intersection / union) if union else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_rows(rows: pd.DataFrame) -> dict[str, Any]:
    if rows.empty:
        return {"dates": 0, "by_state": {}}
    by_state: dict[str, Any] = {}
    for state, group in rows.groupby("market_state", sort=True):
        metrics: dict[str, Any] = {"dates": int(len(group))}
        for pair in PAIR_NAMES:
            metrics[pair] = {
                "mean_overlap_fraction": finite_float(group[f"{pair}_overlap_fraction"].mean()),
                "median_overlap_fraction": finite_float(group[f"{pair}_overlap_fraction"].median()),
                "mean_jaccard": finite_float(group[f"{pair}_jaccard"].mean()),
                "median_jaccard": finite_float(group[f"{pair}_jaccard"].median()),
            }
        by_state[state] = metrics
    return {"dates": int(len(rows)), "by_state": by_state}


def summarize(features: pd.DataFrame, panel: pd.DataFrame, official_dates: pd.Series | pd.Index) -> dict[str, Any]:
    surface, official = prepare_surface(features, panel, official_dates)
    surface = build_components(surface, official)
    rows = overlap_rows(surface)
    return {
        "status": "PASS_STRUCTURAL_CANDIDATE_OVERLAP_MARKET_STATE",
        "scope": "Outcome-blind same-day Top-30 C1/C2/C4 overlap conditional on deterministic 2x2 market-breadth states.",
        "top_k": TOP_K,
        "state_rule": "return-positive breadth and activity-positive breadth each thresholded at 0.5; no tuning or outcome conditioning",
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official.min().date()) if len(official) else None,
            "official_max": str(official.max().date()) if len(official) else None,
        },
        "summary": summarize_rows(rows),
        "admission": {
            "policy_selected": False,
            "era_admitted": False,
            "candidate_status_changed": False,
            "protected_boundary": "CLOSED",
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    for path in (args.features, args.panel, args.sessions):
        if any(marker in str(path).lower() for marker in FORBIDDEN_INPUT_MARKERS):
            raise ValueError(f"refusing input path with protected-data marker: {path}")
    features = pd.read_parquet(args.features, columns=FEATURE_COLUMNS)
    panel = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    result = summarize(features, panel, sessions["date"])
    result["inputs"] = {
        "features": {"path": str(args.features), "rows": int(len(features)), "sha256": sha256_file(args.features)},
        "panel": {"path": str(args.panel), "rows": int(len(panel)), "sha256": sha256_file(args.panel)},
        "official_sessions": {"path": str(args.sessions), "sha256": sha256_file(args.sessions)},
        "component_helper_sha256": sha256_file(Path(__file__).with_name("alpha_candidate_component_anatomy_v1.py")),
    }
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
