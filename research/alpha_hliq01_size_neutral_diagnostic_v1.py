"""One preregistered, target-free size-neutral H-LIQ-01 diagnostic.

This is a representation diagnostic only.  It does not create a candidate ID,
read outcomes, or choose a representation using predictive evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import rolling, sha256_file
from alpha_structural_robustness_v1 import prepare_surface


BASE = "H_LIQ_01_baseline_h20"
NEUTRAL = "H_LIQ_01_size_neutral_h20"
HORIZON = 20
TOP_K = 30
FROZEN_SESSIONS = 600
CANDIDATES = {
    "C1": "C1_residual_reversal_5_v1",
    "C2": "C2_participation_confirmation_5_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}


def safe(value):
    if isinstance(value, dict):
        return {str(key): safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    return value


def top_sets(frame: pd.DataFrame, score: str, dates: pd.Series) -> dict[pd.Timestamp, set[str]]:
    usable = frame.loc[
        frame["date"].isin(dates)
        & frame["eligible_decision_universe"]
        & frame["source_panel_row_present"]
        & np.isfinite(frame[score]),
        ["date", "ticker", score],
    ]
    result: dict[pd.Timestamp, set[str]] = {}
    for date, group in usable.groupby("date", sort=True):
        if len(group) >= TOP_K:
            selected = group.sort_values([score, "ticker"], ascending=[False, True], kind="mergesort").head(TOP_K)
            result[pd.Timestamp(date)] = set(selected["ticker"].astype(str))
    return result


def turnover_metrics(sets: dict[pd.Timestamp, set[str]]) -> dict[str, object]:
    dates = sorted(sets)
    turnovers = [
        1.0 - len(sets[left] & sets[right]) / TOP_K
        for left, right in zip(dates[:-1], dates[1:], strict=True)
    ]
    return {
        "usable_top30_dates": len(dates),
        "turnover_observations": len(turnovers),
        "mean_turnover": float(np.mean(turnovers)) if turnovers else None,
        "q10_turnover": float(np.quantile(turnovers, 0.10)) if turnovers else None,
        "median_turnover": float(np.median(turnovers)) if turnovers else None,
        "q90_turnover": float(np.quantile(turnovers, 0.90)) if turnovers else None,
    }


def persistence_summary(sets: dict[pd.Timestamp, set[str]], session_index: dict[pd.Timestamp, int]) -> dict[str, object]:
    observations: dict[str, list[int]] = {}
    for date, tickers in sets.items():
        for ticker in tickers:
            observations.setdefault(ticker, []).append(session_index[date])
    lengths: list[int] = []
    for indices in observations.values():
        ordered = sorted(set(indices))
        start = previous = ordered[0]
        for current in ordered[1:]:
            if current != previous + 1:
                lengths.append(previous - start + 1)
                start = current
            previous = current
        lengths.append(previous - start + 1)
    return {
        "count": len(lengths),
        "median": float(np.median(lengths)) if lengths else None,
        "q90": float(np.quantile(lengths, 0.90)) if lengths else None,
        "max": int(max(lengths)) if lengths else None,
    }


def exposure(frame: pd.DataFrame, sets: dict[pd.Timestamp, set[str]]) -> dict[str, object]:
    selected_rows: list[pd.DataFrame] = []
    for date, tickers in sets.items():
        selected_rows.append(frame.loc[(frame["date"] == date) & frame["ticker"].astype(str).isin(tickers)])
    selected = pd.concat(selected_rows, ignore_index=True) if selected_rows else pd.DataFrame()
    if selected.empty:
        return {"selected_slots": 0, "bottom_value_q25_share": None, "bottom_volume_q25_share": None}
    return {
        "selected_slots": int(len(selected)),
        "bottom_value_q25_share": float((selected["value_pct"] <= 0.25).mean()),
        "bottom_volume_q25_share": float((selected["volume_pct"] <= 0.25).mean()),
        "median_value_pct": float(selected["value_pct"].median()),
        "median_volume_pct": float(selected["volume_pct"].median()),
    }


def dependence(frame: pd.DataFrame, left: str, right: str, dates: pd.Series) -> dict[str, object]:
    correlations: list[float] = []
    overlaps: list[float] = []
    left_sets = top_sets(frame, left, dates)
    right_sets = top_sets(frame, right, dates)
    common = frame.loc[
        frame["date"].isin(dates)
        & frame["eligible_decision_universe"]
        & frame["source_panel_row_present"]
        & np.isfinite(frame[left])
        & np.isfinite(frame[right]),
    ]
    for _, group in common.groupby("date", sort=True):
        if len(group) >= TOP_K:
            corr = group[left].rank(method="average").corr(group[right].rank(method="average"), method="spearman")
            if np.isfinite(corr):
                correlations.append(float(corr))
    for date in sorted(set(left_sets) & set(right_sets)):
        overlaps.append(len(left_sets[date] & right_sets[date]) / TOP_K)
    return {
        "common_rows": int(len(common)),
        "daily_spearman_mean": float(np.mean(correlations)) if correlations else None,
        "daily_spearman_q10": float(np.quantile(correlations, 0.10)) if correlations else None,
        "daily_spearman_q90": float(np.quantile(correlations, 0.90)) if correlations else None,
        "top30_overlap_mean": float(np.mean(overlaps)) if overlaps else None,
        "common_top30_dates": len(overlaps),
    }


def score_summary(frame: pd.DataFrame, score: str, dates: pd.Series, session_index: dict[pd.Timestamp, int]) -> dict[str, object]:
    finite = (
        frame["date"].isin(dates)
        & frame["eligible_decision_universe"]
        & frame["source_panel_row_present"]
        & np.isfinite(frame[score])
    )
    values = pd.to_numeric(frame.loc[finite, score], errors="coerce")
    sets = top_sets(frame, score, dates)
    return {
        "finite_rows": int(finite.sum()),
        "finite_dates": int(frame.loc[finite, "date"].nunique()),
        "finite_tickers": int(frame.loc[finite, "ticker"].nunique()),
        "score_skew": float(values.skew()) if len(values) > 2 else None,
        "score_excess_kurtosis": float(values.kurt()) if len(values) > 3 else None,
        "top30": turnover_metrics(sets),
        "persistence": persistence_summary(sets, session_index),
        "exposure": exposure(frame, sets),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    surface, official_dates, universe_stats = prepare_surface(args.panel, args.sessions, args.anchors)
    frozen_dates = official_dates.iloc[-FROZEN_SESSIONS:].reset_index(drop=True)
    if len(frozen_dates) != FROZEN_SESSIONS:
        raise ValueError("expected at least 600 official sessions")
    session_index = dict(zip(frozen_dates, range(len(frozen_dates)), strict=True))

    feature_columns = ["ticker", "date", "eligible_decision_universe", *CANDIDATES.values()]
    features = pd.read_parquet(args.features, columns=feature_columns)
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    features = features[features["date"].isin(frozen_dates)].copy()

    surface["log_dollar_turnover"] = np.log(surface["turnover"].where(surface["turnover"].gt(0)))
    surface[BASE] = rolling(surface, "log_dollar_turnover", HORIZON, "std")
    surface.loc[
        ~surface["eligible_decision_universe"] | ~surface["source_panel_row_present"], BASE
    ] = np.nan
    surface = surface[surface["date"].isin(frozen_dates)].copy()
    surface = surface.merge(features, on=["ticker", "date"], how="left", validate="one_to_one", suffixes=("", "_feature"))

    eligible = surface["eligible_decision_universe"] & surface["source_panel_row_present"] & np.isfinite(surface[BASE])
    surface["value_pct"] = np.nan
    surface["volume_pct"] = np.nan
    surface.loc[eligible, "value_pct"] = surface.loc[eligible].groupby("date")["regular_market_value"].rank(pct=True, method="average")
    surface.loc[eligible, "volume_pct"] = surface.loc[eligible].groupby("date")["volume"].rank(pct=True, method="average")

    residuals = pd.Series(np.nan, index=surface.index, dtype="float64")
    for _, group in surface.loc[eligible].groupby("date", sort=True):
        x = group["value_pct"].to_numpy(dtype="float64")
        y = group[BASE].rank(method="average", pct=True).to_numpy(dtype="float64")
        valid = np.isfinite(x) & np.isfinite(y)
        if valid.sum() >= 3:
            design = np.column_stack([np.ones(valid.sum()), x[valid]])
            coefficients, *_ = np.linalg.lstsq(design, y[valid], rcond=None)
            residuals.loc[group.index[valid]] = y[valid] - design @ coefficients
    surface[NEUTRAL] = residuals

    summaries = {score: score_summary(surface, score, frozen_dates, session_index) for score in [BASE, NEUTRAL]}
    comparisons: dict[str, object] = {}
    for left, right in itertools.combinations([BASE, NEUTRAL, *CANDIDATES.values()], 2):
        comparisons[f"{left}__{right}"] = dependence(surface, left, right, frozen_dates)

    result = safe(
        {
            "status": "PASS_STRUCTURAL_ONLY",
            "hypothesis_id": "H-LIQ-01",
            "diagnostic_id": "H-LIQ-01-SIZE-NEUTRAL-V1",
            "baseline": BASE,
            "variant": NEUTRAL,
            "formula": "daily OLS residual of H-LIQ h20 percentile rank on regular_market_value percentile rank",
            "direction": "higher baseline or residual rank first",
            "frozen_session_count": int(len(frozen_dates)),
            "frozen_date_min": str(frozen_dates.min().date()),
            "frozen_date_max": str(frozen_dates.max().date()),
            "universe_stats": universe_stats,
            "summaries": summaries,
            "comparisons": comparisons,
            "interpretation": {
                "target_free": True,
                "single_preregistered_neutralization": True,
                "candidate_id_created": False,
                "novelty_status": "NOVELTY_PENDING",
                "economic_status": "ECONOMIC_CAUTION",
                "predictive_claim": False,
            },
            "source_hashes": {
                "features": sha256_file(args.features),
                "panel": sha256_file(args.panel),
                "official_sessions": sha256_file(args.sessions),
                "tradability_anchors": sha256_file(args.anchors),
            },
            "manifest_sha256": sha256_file(args.manifest),
            "code_sha256": sha256_file(Path(__file__)),
            "repo_head": args.repo_head,
            "access": {
                "target": False,
                "outcome": False,
                "incumbent_score": False,
                "provider": False,
            },
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(args.output), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
