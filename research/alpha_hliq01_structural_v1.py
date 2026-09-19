"""Outcome-blind structural prototype for hypothesis card H-LIQ-01.

H-LIQ-01 asks whether variability of dollar trading activity is a distinct
mechanism from C2's level-of-participation confirmation.  This is one fixed
representation only: the 20-session standard deviation of log dollar turnover
(`close * volume`).  It is a hypothesis card diagnostic, not candidate C5 and
not a predictive evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import rolling, sha256_file
from alpha_structural_robustness_v1 import CANDIDATES, prepare_surface, set_metrics, top_sets


HLIQ = "H_LIQ_01_liquidity_variability_20_v1"
FROZEN_SESSIONS = 600
TOP_K = 30


def safe(value):
    if isinstance(value, dict):
        return {str(key): safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, np.integer):
        return int(value)
    return value


def daily_rank_correlations(frame: pd.DataFrame, left: str, right: str, dates: pd.Series) -> dict[str, object]:
    correlations = []
    overlaps = []
    left_sets = top_sets(frame, left, dates)
    right_sets = top_sets(frame, right, dates)
    for date, group in frame.loc[
        frame["date"].isin(dates)
        & frame["eligible_decision_universe"]
        & frame["source_panel_row_present"]
        & np.isfinite(frame[left])
        & np.isfinite(frame[right])
    ].groupby("date", sort=True):
        if len(group) >= 30:
            correlations.append(group[left].rank().corr(group[right].rank(), method="spearman"))
    common_dates = sorted(set(left_sets) & set(right_sets))
    for date in common_dates:
        overlaps.append(len(left_sets[date] & right_sets[date]) / TOP_K)
    return {
        "daily_spearman_mean": float(np.nanmean(correlations)) if correlations else None,
        "daily_spearman_q10": float(np.nanquantile(correlations, 0.10)) if correlations else None,
        "daily_spearman_q90": float(np.nanquantile(correlations, 0.90)) if correlations else None,
        "top30_overlap_mean": float(np.mean(overlaps)) if overlaps else None,
        "common_top30_dates": len(common_dates),
    }


def score_summary(frame: pd.DataFrame, column: str, dates: pd.Series) -> dict[str, object]:
    eligible = frame["eligible_decision_universe"] & frame["source_panel_row_present"]
    finite = eligible & frame["date"].isin(dates) & np.isfinite(frame[column])
    values = pd.to_numeric(frame.loc[finite, column], errors="coerce")
    sets = top_sets(frame, column, dates)
    summary = set_metrics(sets, k=TOP_K)
    return {
        "finite_rows": int(finite.sum()),
        "date_count": int(frame.loc[finite, "date"].nunique()),
        "ticker_count": int(frame.loc[finite, "ticker"].nunique()),
        "skew": float(values.skew()) if len(values) > 2 else None,
        "excess_kurtosis": float(values.kurt()) if len(values) > 3 else None,
        "top30": summary,
    }


def liquidity_exposure(frame: pd.DataFrame, dates: pd.Series) -> dict[str, object]:
    eligible = (
        frame["date"].isin(dates)
        & frame["eligible_decision_universe"]
        & frame["source_panel_row_present"]
    )
    frame = frame.copy()
    frame["value_pct"] = np.nan
    frame["volume_pct"] = np.nan
    rows = frame.loc[eligible]
    frame.loc[rows.index, "value_pct"] = rows.groupby("date")["regular_market_value"].rank(pct=True)
    frame.loc[rows.index, "volume_pct"] = rows.groupby("date")["volume"].rank(pct=True)
    correlations_value = []
    correlations_volume = []
    for _, group in frame.loc[
        eligible & np.isfinite(frame[HLIQ])
    ].groupby("date", sort=True):
        if len(group) >= 30:
            correlations_value.append(group[HLIQ].rank().corr(group["value_pct"].rank(), method="spearman"))
            correlations_volume.append(group[HLIQ].rank().corr(group["volume_pct"].rank(), method="spearman"))
    selected = top_sets(frame, HLIQ, dates)
    selected_rows = []
    for date, tickers in selected.items():
        selected_rows.append(frame.loc[(frame["date"] == date) & frame["ticker"].astype(str).isin(tickers)])
    selected_frame = pd.concat(selected_rows, ignore_index=True) if selected_rows else pd.DataFrame()
    return {
        "daily_rank_vs_market_value_spearman": float(np.nanmean(correlations_value)) if correlations_value else None,
        "daily_rank_vs_volume_spearman": float(np.nanmean(correlations_volume)) if correlations_volume else None,
        "selected_bottom_value_quartile_share": float((selected_frame["value_pct"] <= 0.25).mean()) if not selected_frame.empty else None,
        "selected_bottom_volume_quartile_share": float((selected_frame["volume_pct"] <= 0.25).mean()) if not selected_frame.empty else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    baseline = pd.read_parquet(args.features)
    baseline["ticker"] = baseline["ticker"].astype("string")
    baseline["date"] = pd.to_datetime(baseline["date"], errors="raise").dt.normalize()
    surface_all, official_dates, universe_stats = prepare_surface(args.panel, args.sessions, args.anchors)
    frozen_dates = official_dates.iloc[-FROZEN_SESSIONS:]
    if len(frozen_dates) != FROZEN_SESSIONS:
        raise ValueError("expected at least 600 official sessions")
    surface_all["log_dollar_turnover"] = np.log(surface_all["turnover"].where(surface_all["turnover"].gt(0)))
    surface_all[HLIQ] = rolling(surface_all, "log_dollar_turnover", 20, "std")
    surface_all.loc[
        ~surface_all["eligible_decision_universe"] | ~surface_all["source_panel_row_present"],
        HLIQ,
    ] = np.nan
    surface = surface_all[surface_all["date"].isin(frozen_dates)].copy()
    baseline = baseline[baseline["date"].isin(frozen_dates)].copy()
    surface = surface.merge(
        baseline[["ticker", "date", *CANDIDATES.values()]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    summary = score_summary(surface, HLIQ, frozen_dates)
    candidate_dependence = {
        candidate: daily_rank_correlations(surface, HLIQ, score, frozen_dates)
        for candidate, score in CANDIDATES.items()
    }
    result = safe(
        {
            "status": "PASS_STRUCTURAL_ONLY",
            "hypothesis_id": "H-LIQ-01",
            "implementation": HLIQ,
            "outcome_accessed": False,
            "provider_accessed": False,
            "incumbent_score_accessed": False,
            "candidate_id_created": False,
            "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "formula": "rolling 20-session standard deviation of log(close * volume)",
            "direction": "higher variability rank first",
            "frozen_session_count": int(len(frozen_dates)),
            "frozen_date_min": str(frozen_dates.min().date()),
            "frozen_date_max": str(frozen_dates.max().date()),
            "universe_stats": universe_stats,
            "summary": summary,
            "liquidity_exposure": liquidity_exposure(surface, frozen_dates),
            "dependence_vs_fixed_candidates": candidate_dependence,
            "interpretation": {
                "literature_is_not_idx_evidence": True,
                "single_representation_no_sweep": True,
                "novelty_status": "NOVELTY_UNRESOLVED",
                "predictive_claim": False,
            },
            "inputs": {
                "features_sha256": sha256_file(args.features),
                "panel_sha256": sha256_file(args.panel),
                "sessions_sha256": sha256_file(args.sessions),
                "anchors_sha256": sha256_file(args.anchors),
            },
            "code_sha256": sha256_file(Path(__file__)),
        }
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(args.out), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
