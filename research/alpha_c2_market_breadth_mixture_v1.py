"""Outcome-blind C2 quadrant mixture versus daily market breadth."""

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
RANK_COLUMN = "rank_C2_participation_confirmation_5_v1"
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def finite_float(value: object) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if np.isfinite(converted) else None


def quantile_summary(values: list[float]) -> dict[str, float | int | None]:
    series = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return {"count": 0, "mean": None, "median": None, "q10": None, "q90": None}
    return {
        "count": int(len(series)),
        "mean": finite_float(series.mean()),
        "median": finite_float(series.median()),
        "q10": finite_float(series.quantile(0.10)),
        "q90": finite_float(series.quantile(0.90)),
    }


def correlation_summary(left: pd.Series, right: pd.Series) -> dict[str, float | int | None]:
    frame = pd.DataFrame({"left": left, "right": right}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 3:
        return {"pairs": int(len(frame)), "spearman": None}
    return {"pairs": int(len(frame)), "spearman": finite_float(frame["left"].corr(frame["right"], method="spearman"))}


def add_quadrants(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["ret_pos"] = result["ret_5"] >= 0.0
    result["activity_pos"] = result["c2_log_abnormal_turnover"] >= 0.0
    result["quadrant"] = np.select(
        [result["ret_pos"] & result["activity_pos"], ~result["ret_pos"] & ~result["activity_pos"]],
        ["pp", "nn"],
        default="cross",
    )
    return result


def build_daily_breadth(frame: pd.DataFrame) -> pd.DataFrame:
    valid = frame.loc[
        frame["eligible_decision_universe"]
        & frame["ret_5"].notna()
        & frame["c2_log_abnormal_turnover"].notna(),
        ["ticker", "date", "ret_pos", "activity_pos", "quadrant"],
    ]
    if valid.empty:
        return pd.DataFrame()
    return valid.groupby("date", sort=True).agg(
        ret_pos_share=("ret_pos", "mean"),
        activity_pos_share=("activity_pos", "mean"),
        pp_eligible_share=("quadrant", lambda values: float((values == "pp").mean())),
        nn_eligible_share=("quadrant", lambda values: float((values == "nn").mean())),
        finite_count=("ticker", "size"),
    )


def build_selected_mixture(frame: pd.DataFrame) -> pd.DataFrame:
    valid = frame.loc[
        frame["eligible_decision_universe"]
        & frame[RANK_COLUMN].notna()
        & frame["quadrant"].notna(),
        ["ticker", "date", RANK_COLUMN, "quadrant"],
    ]
    rows: list[dict[str, Any]] = []
    for date, group in valid.groupby("date", sort=True):
        ordered = group.sort_values([RANK_COLUMN, "ticker"], ascending=[False, True], kind="mergesort")
        if len(ordered) < TOP_K:
            continue
        selected = ordered.head(TOP_K)
        counts = selected["quadrant"].value_counts()
        rows.append(
            {
                "date": pd.Timestamp(date),
                "selected_pp_share": float(counts.get("pp", 0) / TOP_K),
                "selected_nn_share": float(counts.get("nn", 0) / TOP_K),
                "selected_cross_share": float(counts.get("cross", 0) / TOP_K),
                "selected_positive_score_quadrant_share": float((selected["quadrant"] == "pp").mean()),
            }
        )
    return pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame()


def merge_breadth_and_selection(frame: pd.DataFrame) -> pd.DataFrame:
    breadth = build_daily_breadth(frame)
    selection = build_selected_mixture(frame)
    if breadth.empty or selection.empty:
        return pd.DataFrame()
    return breadth.join(selection, how="inner")


def summarize_table(table: pd.DataFrame) -> dict[str, Any]:
    if table.empty:
        return {"dates": 0, "selected_mixture": {}, "correlations": {}}
    return {
        "dates": int(len(table)),
        "selected_mixture": {
            "pp": quantile_summary(table["selected_pp_share"].tolist()),
            "nn": quantile_summary(table["selected_nn_share"].tolist()),
            "cross": quantile_summary(table["selected_cross_share"].tolist()),
        },
        "eligible_mixture": {
            "pp": quantile_summary(table["pp_eligible_share"].tolist()),
            "nn": quantile_summary(table["nn_eligible_share"].tolist()),
        },
        "correlations": {
            "selected_pp_vs_ret_pos_share": correlation_summary(table["selected_pp_share"], table["ret_pos_share"]),
            "selected_pp_vs_activity_pos_share": correlation_summary(table["selected_pp_share"], table["activity_pos_share"]),
            "selected_pp_vs_pp_eligible_share": correlation_summary(table["selected_pp_share"], table["pp_eligible_share"]),
            "selected_pp_vs_nn_eligible_share": correlation_summary(table["selected_pp_share"], table["nn_eligible_share"]),
            "selected_nn_vs_ret_pos_share": correlation_summary(table["selected_nn_share"], table["ret_pos_share"]),
        },
    }


def summarize(features: pd.DataFrame, panel: pd.DataFrame, official_dates: pd.Series | pd.Index) -> dict[str, Any]:
    surface, official = prepare_surface(features, panel, official_dates)
    surface = build_components(surface, official)
    surface = add_quadrants(surface)
    table = merge_breadth_and_selection(surface)
    by_year = {
        str(year): summarize_table(group.copy())
        for year, group in table.groupby(table.index.year, sort=True)
    }
    return {
        "status": "PASS_STRUCTURAL_C2_MARKET_BREADTH_MIXTURE",
        "scope": "Outcome-blind daily eligible-market breadth versus fixed C2 Top-30 sign-quadrant mixture; no candidate split or outcome access.",
        "top_k": TOP_K,
        "quadrants": {
            "pp": "ret_5 >= 0 and log abnormal turnover >= 0",
            "nn": "ret_5 < 0 and log abnormal turnover < 0",
            "cross": "the two cross-sign quadrants combined",
        },
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official.min().date()) if len(official) else None,
            "official_max": str(official.max().date()) if len(official) else None,
        },
        "overall": summarize_table(table),
        "by_year": by_year,
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
