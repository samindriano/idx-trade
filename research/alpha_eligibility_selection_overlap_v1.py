"""Outcome-blind Top-30 membership overlap under the 20-vs-60 policy fork."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from alpha_eligibility_policy_scenario_v1 import (
        CANDIDATES,
        POLICIES,
        TOP_K,
        add_ranks,
        build_c3_score,
        build_market_scores,
        build_universe,
        sha256_file,
    )
except ModuleNotFoundError:
    from research.alpha_eligibility_policy_scenario_v1 import (
        CANDIDATES,
        POLICIES,
        TOP_K,
        add_ranks,
        build_c3_score,
        build_market_scores,
        build_universe,
        sha256_file,
    )


FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def finite_float(value: object) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if np.isfinite(converted) else None


def top_k_sets(frame: pd.DataFrame, candidate: str) -> dict[pd.Timestamp, set[str]]:
    rank = f"rank_{candidate}"
    valid = frame.loc[
        frame["eligible_decision_universe"] & frame[rank].notna(),
        ["ticker", "date", rank],
    ].copy()
    selections: dict[pd.Timestamp, set[str]] = {}
    for date, group in valid.groupby("date", sort=True):
        ordered = group.sort_values([rank, "ticker"], ascending=[False, True], kind="mergesort")
        if len(ordered) >= TOP_K:
            selections[pd.Timestamp(date)] = set(ordered.head(TOP_K)["ticker"].astype(str))
    return selections


def compare_sets(left: dict[pd.Timestamp, set[str]], right: dict[pd.Timestamp, set[str]]) -> pd.DataFrame:
    common_dates = sorted(set(left) & set(right))
    rows: list[dict[str, Any]] = []
    for date in common_dates:
        left_set = left[date]
        right_set = right[date]
        intersection = len(left_set & right_set)
        union = len(left_set | right_set)
        rows.append(
            {
                "date": date,
                "overlap_fraction": float(intersection / TOP_K),
                "jaccard": float(intersection / union) if union else 0.0,
                "twenty_only": int(len(left_set - right_set)),
                "sixty_only": int(len(right_set - left_set)),
                "symmetric_difference": int(len(left_set ^ right_set)),
                "exact_match": bool(left_set == right_set),
            }
        )
    return pd.DataFrame(rows)


def summarize_comparison(rows: pd.DataFrame) -> dict[str, Any]:
    if rows.empty:
        return {"common_selection_dates": 0, "by_year": {}}
    by_year: dict[str, Any] = {}
    rows = rows.copy()
    rows["year"] = pd.to_datetime(rows["date"]).dt.year
    for year, group in rows.groupby("year", sort=True):
        by_year[str(int(year))] = {
            "dates": int(len(group)),
            "mean_overlap_fraction": finite_float(group["overlap_fraction"].mean()),
            "median_overlap_fraction": finite_float(group["overlap_fraction"].median()),
            "mean_jaccard": finite_float(group["jaccard"].mean()),
            "mean_symmetric_difference": finite_float(group["symmetric_difference"].mean()),
            "exact_match_fraction": finite_float(group["exact_match"].mean()),
        }
    return {
        "common_selection_dates": int(len(rows)),
        "mean_overlap_fraction": finite_float(rows["overlap_fraction"].mean()),
        "median_overlap_fraction": finite_float(rows["overlap_fraction"].median()),
        "mean_jaccard": finite_float(rows["jaccard"].mean()),
        "mean_symmetric_difference": finite_float(rows["symmetric_difference"].mean()),
        "exact_match_dates": int(rows["exact_match"].sum()),
        "exact_match_fraction": finite_float(rows["exact_match"].mean()),
        "by_year": by_year,
    }


def build_policy_frames(
    panel_path: Path,
    financial_path: Path,
    sessions: pd.DataFrame,
    anchors: pd.DataFrame,
    panel: pd.DataFrame,
) -> dict[int, pd.DataFrame]:
    frames: dict[int, pd.DataFrame] = {}
    for minimum in POLICIES:
        universe, _ = build_universe(panel, sessions, anchors, minimum)
        market = build_market_scores(panel_path, universe)
        financial = build_c3_score(financial_path, universe)
        frame = market.merge(financial, on=["ticker", "date"], how="left", validate="one_to_one")
        frames[minimum] = add_ranks(frame)
    return frames


def summarize(
    panel_path: Path,
    financial_path: Path,
    sessions_path: Path,
    anchors_path: Path,
) -> dict[str, Any]:
    panel = pd.read_parquet(panel_path, columns=["ticker", "date", "regular_market_value", "close", "volume"])
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    sessions = pd.read_csv(sessions_path, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    anchors = pd.read_csv(anchors_path)
    frames = build_policy_frames(panel_path, financial_path, sessions, anchors, panel)

    candidates: dict[str, Any] = {}
    for candidate in CANDIDATES:
        selections = {minimum: top_k_sets(frames[minimum], candidate) for minimum in POLICIES}
        comparison = compare_sets(selections[20], selections[60])
        candidates[candidate] = {
            "minimum_20_selection_dates": int(len(selections[20])),
            "minimum_60_selection_dates": int(len(selections[60])),
            "comparison": summarize_comparison(comparison),
        }

    return {
        "status": "PASS_STRUCTURAL_POLICY_SELECTION_OVERLAP",
        "scope": "Outcome-blind cross-policy fixed Top-30 membership overlap; policy remains unresolved.",
        "policy_pair": {"left": 20, "right": 60, "top_k": TOP_K},
        "candidates": candidates,
        "admission": {
            "policy_selected": False,
            "population_selected": False,
            "candidate_status_changed": False,
            "protected_boundary": "CLOSED",
        },
        "inputs": {
            "panel": {"path": str(panel_path), "rows": int(len(panel)), "sha256": sha256_file(panel_path)},
            "financial": {"path": str(financial_path), "sha256": sha256_file(financial_path)},
            "official_sessions": {"path": str(sessions_path), "sha256": sha256_file(sessions_path)},
            "tradability_anchors": {"path": str(anchors_path), "sha256": sha256_file(anchors_path)},
        },
        "limitations": [
            "The 20-policy branch is a counterfactual, not an admitted population.",
            "Top-30 membership overlap is structural and cannot establish predictive robustness or policy correctness.",
            "Population completeness, identity continuity, corporate-action basis, financial PIT, and execution capacity remain unresolved.",
            "No forward outcomes, IC, Rank-IC, PnL, incumbent result, or protected array was read.",
        ],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    for path in (args.panel, args.financial, args.sessions, args.anchors):
        if any(marker in str(path).lower() for marker in FORBIDDEN_INPUT_MARKERS):
            raise ValueError(f"refusing input path with protected-data marker: {path}")
    result = summarize(args.panel, args.financial, args.sessions, args.anchors)
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--financial", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
