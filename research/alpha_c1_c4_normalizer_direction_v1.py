"""Outcome-blind direction of C1/C4 denominator-driven rank changes."""

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
CANDIDATES = {
    "C1": {"score": "C1_residual_reversal_5_v1", "numerator": "c1_residual", "denominator": "vol_20", "proxy_sign": -1.0},
    "C4": {"score": "C4_path_efficiency_reversal_20_v1", "numerator": "ret_20", "denominator": "abs_ret_sum_20", "proxy_sign": -1.0},
}
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


def daily_group_rows(frame: pd.DataFrame, candidate: str) -> pd.DataFrame:
    spec = CANDIDATES[candidate]
    score = spec["score"]
    rank = f"rank_{score}"
    valid = (
        frame["eligible_decision_universe"].astype(bool)
        & frame[score].notna()
        & frame[rank].notna()
        & frame[spec["numerator"]].notna()
        & frame[spec["denominator"]].notna()
    )
    columns = ["ticker", "date", rank, spec["numerator"], spec["denominator"]]
    rows: list[pd.DataFrame] = []
    for date, group in frame.loc[valid, columns].groupby("date", sort=True):
        group = group.copy()
        group[spec["numerator"]] = pd.to_numeric(group[spec["numerator"]], errors="coerce")
        group[spec["denominator"]] = pd.to_numeric(group[spec["denominator"]], errors="coerce")
        group["proxy"] = spec["proxy_sign"] * group[spec["numerator"]]
        group = group[np.isfinite(group["proxy"]) & np.isfinite(group[spec["denominator"]])]
        if len(group) < TOP_K:
            continue
        score_names = set(group.sort_values([rank, "ticker"], ascending=[False, True], kind="mergesort").head(TOP_K)["ticker"].astype(str))
        numerator_names = set(group.sort_values(["proxy", "ticker"], ascending=[False, True], kind="mergesort").head(TOP_K)["ticker"].astype(str))
        group["ticker"] = group["ticker"].astype(str)
        group["denominator_percentile"] = group[spec["denominator"]].rank(pct=True, method="average")
        group["selection_group"] = np.select(
            [group["ticker"].isin(score_names) & group["ticker"].isin(numerator_names), group["ticker"].isin(score_names), group["ticker"].isin(numerator_names)],
            ["both", "score_only", "numerator_only"],
            default="neither",
        )
        selected = group[group["selection_group"] != "neither"].copy()
        selected["date"] = pd.Timestamp(date)
        rows.append(selected[["date", "ticker", "selection_group", "denominator_percentile"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["date", "ticker", "selection_group", "denominator_percentile"])


def summarize_groups(rows: pd.DataFrame) -> dict[str, Any]:
    if rows.empty:
        return {"dates": 0, "groups": {}}
    daily = rows.groupby(["date", "selection_group"], sort=True).agg(
        group_count=("ticker", "size"),
        daily_median_denominator_percentile=("denominator_percentile", "median"),
        daily_mean_denominator_percentile=("denominator_percentile", "mean"),
    ).reset_index()
    groups: dict[str, Any] = {}
    for name, group in daily.groupby("selection_group", sort=True):
        groups[name] = {
            "dates": int(len(group)),
            "mean_group_count": finite_float(group["group_count"].mean()),
            "median_group_count": finite_float(group["group_count"].median()),
            "mean_daily_median_denominator_percentile": finite_float(group["daily_median_denominator_percentile"].mean()),
            "median_daily_median_denominator_percentile": finite_float(group["daily_median_denominator_percentile"].median()),
            "mean_daily_mean_denominator_percentile": finite_float(group["daily_mean_denominator_percentile"].mean()),
        }
    pivot = daily.pivot(index="date", columns="selection_group", values="daily_median_denominator_percentile")
    delta = pivot["score_only"] - pivot["numerator_only"] if {"score_only", "numerator_only"}.issubset(pivot.columns) else pd.Series(dtype="float64")
    groups["score_only_minus_numerator_only_daily_median_delta"] = {
        "dates": int(delta.notna().sum()),
        "mean": finite_float(delta.mean()),
        "median": finite_float(delta.median()),
        "quantiles": quantile_summary(delta.dropna().tolist()),
    }
    return {"dates": int(rows["date"].nunique()), "groups": groups}


def summarize(features: pd.DataFrame, panel: pd.DataFrame, official_dates: pd.Series | pd.Index) -> dict[str, Any]:
    surface, official = prepare_surface(features, panel, official_dates)
    surface = build_components(surface, official)
    candidates: dict[str, Any] = {}
    for candidate in CANDIDATES:
        rows = daily_group_rows(surface, candidate)
        candidates[candidate] = {
            "denominator": CANDIDATES[candidate]["denominator"],
            "numerator_proxy": f"{CANDIDATES[candidate]['proxy_sign']} * {CANDIDATES[candidate]['numerator']}",
            "overall": summarize_groups(rows),
            "by_year": {
                str(year): summarize_groups(group.copy())
                for year, group in rows.groupby(rows["date"].dt.year, sort=True)
            },
        }
    return {
        "status": "PASS_STRUCTURAL_C1_C4_NORMALIZER_DIRECTION",
        "scope": "Outcome-blind denominator-direction audit for C1/C4 score-versus-numerator Top-30 membership changes.",
        "top_k": TOP_K,
        "selection": "stored score rank and numerator proxy descending with ascending ticker tie-break",
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official.min().date()) if len(official) else None,
            "official_max": str(official.max().date()) if len(official) else None,
        },
        "candidates": candidates,
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
