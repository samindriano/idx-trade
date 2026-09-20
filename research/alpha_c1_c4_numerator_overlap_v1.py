"""Outcome-blind numerator-versus-score overlap for C1 and C4."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from alpha_candidate_component_anatomy_v1 import (
        CANDIDATES,
        FEATURE_COLUMNS,
        build_components,
        prepare_surface,
        quantile_summary,
        sha256_file,
    )
except ModuleNotFoundError:
    from research.alpha_candidate_component_anatomy_v1 import (
        CANDIDATES,
        FEATURE_COLUMNS,
        build_components,
        prepare_surface,
        quantile_summary,
        sha256_file,
    )


TOP_K = 30
PANEL_COLUMNS = ["ticker", "date", "close", "volume"]
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def select_sets(frame: pd.DataFrame, candidate: str, proxy_column: str) -> tuple[dict[pd.Timestamp, set[str]], dict[pd.Timestamp, set[str]]]:
    score_column = CANDIDATES[candidate]
    rank_column = f"rank_{score_column}"
    valid = frame.loc[
        frame["eligible_decision_universe"]
        & frame[rank_column].notna()
        & frame[proxy_column].notna(),
        ["ticker", "date", rank_column, proxy_column],
    ]
    score_sets: dict[pd.Timestamp, set[str]] = {}
    proxy_sets: dict[pd.Timestamp, set[str]] = {}
    for date, group in valid.groupby("date", sort=True):
        if len(group) < TOP_K:
            continue
        score_sets[pd.Timestamp(date)] = set(
            group.sort_values([rank_column, "ticker"], ascending=[False, True], kind="mergesort").head(TOP_K)["ticker"].astype(str)
        )
        proxy_sets[pd.Timestamp(date)] = set(
            group.sort_values([proxy_column, "ticker"], ascending=[False, True], kind="mergesort").head(TOP_K)["ticker"].astype(str)
        )
    return score_sets, proxy_sets


def pair_summary(left: dict[pd.Timestamp, set[str]], right: dict[pd.Timestamp, set[str]]) -> dict[str, Any]:
    dates = sorted(set(left).intersection(right))
    overlaps: list[float] = []
    jaccards: list[float] = []
    for date in dates:
        intersection = len(left[date] & right[date])
        union = len(left[date] | right[date])
        overlaps.append(intersection / TOP_K)
        jaccards.append(intersection / union if union else 0.0)
    return {
        "common_dates": int(len(dates)),
        "overlap_fraction": quantile_summary(overlaps),
        "jaccard": quantile_summary(jaccards),
    }


def summarize_pair_by_year(left: dict[pd.Timestamp, set[str]], right: dict[pd.Timestamp, set[str]]) -> dict[str, Any]:
    years = sorted(set(date.year for date in left).intersection(date.year for date in right))
    output: dict[str, Any] = {}
    for year in years:
        l = {date: value for date, value in left.items() if date.year == year}
        r = {date: value for date, value in right.items() if date.year == year}
        output[str(year)] = pair_summary(l, r)
    return output


def summarize(features: pd.DataFrame, panel: pd.DataFrame, official_dates: pd.Series | pd.Index) -> dict[str, Any]:
    surface, official = prepare_surface(features, panel, official_dates)
    surface = build_components(surface, official)
    # The proxy is higher-is-better negative residual, so create an explicit column.
    surface["c1_numerator_reversal"] = -surface["c1_residual"]
    c1_score, c1_num = select_sets(surface, "C1", "c1_numerator_reversal")
    surface["c4_numerator_reversal"] = -surface["ret_20"]
    c4_score, c4_num = select_sets(surface, "C4", "c4_numerator_reversal")
    return {
        "status": "PASS_STRUCTURAL_C1_C4_NUMERATOR_OVERLAP",
        "scope": "Outcome-blind fixed Top-30 overlap between stored C1/C4 scores and numerator-only reversal proxies, plus cross-candidate score/numerator overlap.",
        "proxy_definitions": {
            "C1_numerator_reversal": "-(ret_5 - beta_60_prior * market_ret_5)",
            "C4_numerator_reversal": "-ret_20",
            "selection": "fixed Top-30 descending value with ascending ticker tie-break",
        },
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official.min().date()) if len(official) else None,
            "official_max": str(official.max().date()) if len(official) else None,
        },
        "within_candidate": {
            "C1_score_vs_numerator": {"overall": pair_summary(c1_score, c1_num), "by_year": summarize_pair_by_year(c1_score, c1_num)},
            "C4_score_vs_numerator": {"overall": pair_summary(c4_score, c4_num), "by_year": summarize_pair_by_year(c4_score, c4_num)},
        },
        "cross_candidate": {
            "score_vs_score": {"overall": pair_summary(c1_score, c4_score), "by_year": summarize_pair_by_year(c1_score, c4_score)},
            "numerator_vs_numerator": {"overall": pair_summary(c1_num, c4_num), "by_year": summarize_pair_by_year(c1_num, c4_num)},
        },
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
        "features": {"path": str(args.features), "sha256": sha256_file(args.features), "rows": int(len(features))},
        "panel": {"path": str(args.panel), "sha256": sha256_file(args.panel), "rows": int(len(panel))},
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
