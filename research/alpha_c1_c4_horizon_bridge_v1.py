"""Outcome-blind bridge between C1 short-horizon and C4 medium-horizon reversal."""

from __future__ import annotations

import argparse
import itertools
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
SIGNALS = {
    "C1_STORED": "C1_residual_reversal_5_v1",
    "C1_RAW_REVERSAL_5": "c1_raw_reversal_5",
    "C1_RESIDUAL_NUMERATOR": "c1_residual_numerator",
    "C4_STORED": "C4_path_efficiency_reversal_20_v1",
    "C4_RAW_REVERSAL_20": "c4_raw_reversal_20",
}
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def finite_float(value: object) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if np.isfinite(converted) else None


def build_signal_surface(features: pd.DataFrame, panel: pd.DataFrame, official_dates: pd.Series | pd.Index) -> tuple[pd.DataFrame, pd.Index]:
    surface, official = prepare_surface(features, panel, official_dates)
    surface = build_components(surface, official)
    surface["c1_raw_reversal_5"] = -surface["ret_5"]
    surface["c1_residual_numerator"] = -surface["c1_residual"]
    surface["c4_raw_reversal_20"] = -surface["ret_20"]
    return surface, official


def signal_sets(surface: pd.DataFrame, signal: str) -> dict[pd.Timestamp, set[str]]:
    column = SIGNALS[signal]
    valid = surface.loc[
        surface["eligible_decision_universe"] & surface[column].notna(),
        ["ticker", "date", column],
    ].copy()
    selections: dict[pd.Timestamp, set[str]] = {}
    for date, group in valid.groupby("date", sort=True):
        ordered = group.sort_values([column, "ticker"], ascending=[False, True], kind="mergesort")
        if len(ordered) >= TOP_K:
            selections[pd.Timestamp(date)] = set(ordered.head(TOP_K)["ticker"].astype(str))
    return selections


def compare_pair(surface: pd.DataFrame, left: str, right: str) -> dict[str, Any]:
    left_sets = signal_sets(surface, left)
    right_sets = signal_sets(surface, right)
    common_dates = sorted(set(left_sets) & set(right_sets))
    overlap: list[float] = []
    jaccard: list[float] = []
    exact: list[bool] = []
    rank_corr: list[float] = []
    year_rows: dict[int, list[tuple[float, float, bool]]] = {}
    rank_left = surface["eligible_decision_universe"] & surface[SIGNALS[left]].notna()
    rank_right = surface["eligible_decision_universe"] & surface[SIGNALS[right]].notna()
    rank_frame = surface.loc[rank_left & rank_right, ["date", SIGNALS[left], SIGNALS[right]]]
    for date, group in rank_frame.groupby("date", sort=True):
        if len(group) >= 3 and group[SIGNALS[left]].nunique() > 1 and group[SIGNALS[right]].nunique() > 1:
            corr = group[SIGNALS[left]].corr(group[SIGNALS[right]], method="spearman")
            if np.isfinite(corr):
                rank_corr.append(float(corr))
    for date in common_dates:
        left_set = left_sets[date]
        right_set = right_sets[date]
        intersection = len(left_set & right_set)
        union = len(left_set | right_set)
        overlap_value = float(intersection / TOP_K)
        jaccard_value = float(intersection / union) if union else 0.0
        exact_value = left_set == right_set
        overlap.append(overlap_value)
        jaccard.append(jaccard_value)
        exact.append(exact_value)
        year_rows.setdefault(pd.Timestamp(date).year, []).append((overlap_value, jaccard_value, exact_value))
    by_year: dict[str, Any] = {}
    for year, rows in sorted(year_rows.items()):
        by_year[str(year)] = {
            "dates": len(rows),
            "mean_overlap_fraction": finite_float(np.mean([row[0] for row in rows])),
            "mean_jaccard": finite_float(np.mean([row[1] for row in rows])),
            "exact_match_fraction": finite_float(np.mean([row[2] for row in rows])),
        }
    return {
        "left": left,
        "right": right,
        "left_selection_dates": len(left_sets),
        "right_selection_dates": len(right_sets),
        "common_selection_dates": len(common_dates),
        "mean_overlap_fraction": finite_float(np.mean(overlap)) if overlap else None,
        "median_overlap_fraction": finite_float(np.median(overlap)) if overlap else None,
        "mean_jaccard": finite_float(np.mean(jaccard)) if jaccard else None,
        "exact_match_fraction": finite_float(np.mean(exact)) if exact else None,
        "mean_daily_rank_spearman": finite_float(np.mean(rank_corr)) if rank_corr else None,
        "rank_spearman_dates": len(rank_corr),
        "by_year": by_year,
    }


def summarize(features: pd.DataFrame, panel: pd.DataFrame, official_dates: pd.Series | pd.Index) -> dict[str, Any]:
    surface, official = build_signal_surface(features, panel, official_dates)
    pairs = [compare_pair(surface, left, right) for left, right in itertools.combinations(SIGNALS, 2)]
    return {
        "status": "PASS_STRUCTURAL_C1_C4_HORIZON_BRIDGE",
        "scope": "Outcome-blind fixed Top-30 overlap and daily rank association across C1 raw/residual/normalized and C4 raw/normalized reversal representations.",
        "top_k": TOP_K,
        "signal_definitions": {
            "C1_STORED": "stored C1 residual-reversal score = -c1_residual / vol_20",
            "C1_RAW_REVERSAL_5": "-ret_5",
            "C1_RESIDUAL_NUMERATOR": "-c1_residual = -(ret_5 - beta_60_prior * market_ret_5)",
            "C4_STORED": "stored C4 path-efficiency score = -ret_20 / abs_ret_sum_20",
            "C4_RAW_REVERSAL_20": "-ret_20",
        },
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official.min().date()) if len(official) else None,
            "official_max": str(official.max().date()) if len(official) else None,
        },
        "pairwise": pairs,
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
