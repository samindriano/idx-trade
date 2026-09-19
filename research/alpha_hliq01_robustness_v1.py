"""Adversarial, outcome-blind robustness audit for H-LIQ-01."""

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
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, np.integer):
        return int(value)
    return value


def stable_hash(text: str) -> int:
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "little")


def hliq_scores(surface: pd.DataFrame, horizon: int) -> pd.Series:
    return rolling(surface, "log_dollar_turnover", horizon, "std")


def score_summary(frame: pd.DataFrame, column: str, dates: pd.Series) -> dict[str, object]:
    eligible = frame["eligible_decision_universe"] & frame["source_panel_row_present"]
    finite = eligible & frame["date"].isin(dates) & np.isfinite(frame[column])
    values = pd.to_numeric(frame.loc[finite, column], errors="coerce")
    values = values[np.isfinite(values)]
    sets = top_sets(frame, column, dates)
    return {
        "finite_rows": int(finite.sum()),
        "date_count": int(frame.loc[finite, "date"].nunique()),
        "ticker_count": int(frame.loc[finite, "ticker"].nunique()),
        "skew": float(values.skew()) if len(values) > 2 else None,
        "excess_kurtosis": float(values.kurt()) if len(values) > 3 else None,
        "top30": set_metrics(sets, k=TOP_K),
    }


def daily_spearman(frame: pd.DataFrame, left: str, right: str, dates: pd.Series, mask: pd.Series | None = None) -> dict[str, object]:
    base = (
        frame["date"].isin(dates)
        & frame["eligible_decision_universe"]
        & frame["source_panel_row_present"]
        & np.isfinite(frame[left])
        & np.isfinite(frame[right])
    )
    if mask is not None:
        base &= mask
    values = []
    for _, group in frame.loc[base].groupby("date", sort=True):
        if len(group) >= 10:
            values.append(group[left].rank().corr(group[right].rank(), method="spearman"))
    return {
        "date_count": len(values),
        "mean": float(np.nanmean(values)) if values else None,
        "q10": float(np.nanquantile(values, 0.10)) if values else None,
        "q90": float(np.nanquantile(values, 0.90)) if values else None,
    }


def conditional_liquidity(frame: pd.DataFrame, dates: pd.Series) -> dict[str, object]:
    eligible = frame["date"].isin(dates) & frame["eligible_decision_universe"] & frame["source_panel_row_present"]
    frame = frame.copy()
    frame["value_pct"] = np.nan
    rows = frame.loc[eligible]
    frame.loc[rows.index, "value_pct"] = rows.groupby("date")["regular_market_value"].rank(pct=True)
    buckets = {}
    for bucket, mask in {
        "Q1_bottom_value": frame["value_pct"].le(0.25),
        "Q2": frame["value_pct"].gt(0.25) & frame["value_pct"].le(0.50),
        "Q3": frame["value_pct"].gt(0.50) & frame["value_pct"].le(0.75),
        "Q4_top_value": frame["value_pct"].gt(0.75),
    }.items():
        buckets[bucket] = {
            "hliq_vs_c2_daily_spearman": daily_spearman(frame, HLIQ, CANDIDATES["C2"], dates, mask),
            "hliq_vs_c1_daily_spearman": daily_spearman(frame, HLIQ, CANDIDATES["C1"], dates, mask),
            "hliq_vs_c4_daily_spearman": daily_spearman(frame, HLIQ, CANDIDATES["C4"], dates, mask),
            "eligible_rows": int((eligible & mask).sum()),
        }
    return buckets


def missingness_stress(frame: pd.DataFrame, dates: pd.Series) -> dict[str, object]:
    base_sets = top_sets(frame, HLIQ, dates)
    finite = frame["date"].isin(dates) & frame["eligible_decision_universe"] & frame["source_panel_row_present"] & np.isfinite(frame[HLIQ])
    row_hash = pd.util.hash_pandas_object(frame[["ticker", "date"]], index=False).astype("uint64")
    result = {}
    for rate in [0.005, 0.01, 0.05]:
        salt = np.uint64(stable_hash(f"H-LIQ-01|missingness|{rate}"))
        masked = finite & (((row_hash ^ salt) % np.uint64(1_000_000)) < np.uint64(int(rate * 1_000_000)))
        stressed = frame[["ticker", "date", "eligible_decision_universe", "source_panel_row_present", HLIQ]].copy()
        stressed["stress_score"] = stressed[HLIQ].where(~masked)
        stressed_sets = top_sets(stressed, "stress_score", dates)
        result[str(rate)] = {
            "masked_rows": int(masked.sum()),
            "finite_row_loss_rate": float(masked.sum() / finite.sum()) if finite.sum() else None,
            "top30": set_metrics(stressed_sets, base_sets, k=TOP_K),
        }
    return result


def listing_age_audit(frame: pd.DataFrame, dates: pd.Series, security_master_path: Path) -> dict[str, object]:
    master = pd.read_csv(security_master_path, usecols=["ticker", "listed_from", "listed_to"])
    master["ticker"] = master["ticker"].astype("string")
    master["listed_from"] = pd.to_datetime(master["listed_from"], errors="coerce").dt.normalize()
    master["listed_to"] = pd.to_datetime(master["listed_to"], errors="coerce").dt.normalize()
    work = frame.merge(master, on="ticker", how="left", validate="many_to_one")
    work["listing_age_days"] = (work["date"] - work["listed_from"]).dt.days
    eligible = work["date"].isin(dates) & work["eligible_decision_universe"] & work["source_panel_row_present"]
    selected = top_sets(work, HLIQ, dates)
    selected_rows = []
    for date, tickers in selected.items():
        selected_rows.append(work.loc[(work["date"] == date) & work["ticker"].astype(str).isin(tickers)])
    selected_frame = pd.concat(selected_rows, ignore_index=True) if selected_rows else pd.DataFrame()
    def share(frame: pd.DataFrame, threshold: int) -> float | None:
        if frame.empty:
            return None
        return float(frame["listing_age_days"].le(threshold).mean())
    return {
        "eligible_rows_with_master": int((eligible & work["listed_from"].notna()).sum()),
        "eligible_rows_missing_listed_from": int((eligible & work["listed_from"].isna()).sum()),
        "selected_slots": int(len(selected_frame)),
        "selected_slots_age_le_60_days": share(selected_frame, 60),
        "selected_slots_age_le_365_days": share(selected_frame, 365),
        "eligible_rows_age_le_60_days": float((work.loc[eligible, "listing_age_days"] <= 60).mean()) if eligible.any() else None,
        "eligible_rows_age_le_365_days": float((work.loc[eligible, "listing_age_days"] <= 365).mean()) if eligible.any() else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    baseline = pd.read_parquet(args.features)
    baseline["ticker"] = baseline["ticker"].astype("string")
    baseline["date"] = pd.to_datetime(baseline["date"], errors="raise").dt.normalize()
    surface_all, official_dates, universe_stats = prepare_surface(args.panel, args.sessions, args.anchors)
    frozen_dates = official_dates.iloc[-FROZEN_SESSIONS:]
    surface_all["log_dollar_turnover"] = np.log(surface_all["turnover"].where(surface_all["turnover"].gt(0)))
    for horizon in [10, 20, 40]:
        surface_all[f"hliq_h{horizon}"] = hliq_scores(surface_all, horizon)
        surface_all.loc[
            ~surface_all["eligible_decision_universe"] | ~surface_all["source_panel_row_present"],
            f"hliq_h{horizon}",
        ] = np.nan
    surface = surface_all[surface_all["date"].isin(frozen_dates)].copy()
    baseline = baseline[baseline["date"].isin(frozen_dates)]
    surface = surface.merge(
        baseline[["ticker", "date", *CANDIDATES.values()]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    surface[HLIQ] = surface["hliq_h20"]
    result = safe(
        {
            "status": "PASS_STRUCTURAL_ONLY",
            "stage": "Q_HLIQ01_ADVERSARIAL_ROBUSTNESS",
            "hypothesis_id": "H-LIQ-01",
            "outcome_accessed": False,
            "provider_accessed": False,
            "incumbent_score_accessed": False,
            "candidate_id_created": False,
            "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "frozen_session_count": int(len(frozen_dates)),
            "frozen_date_min": str(frozen_dates.min().date()),
            "frozen_date_max": str(frozen_dates.max().date()),
            "universe_stats": universe_stats,
            "horizon_sensitivity": {
                f"h{horizon}": {
                    "summary": score_summary(surface, f"hliq_h{horizon}", frozen_dates),
                    "overlap_vs_h20": set_metrics(
                        top_sets(surface, f"hliq_h{horizon}", frozen_dates),
                        top_sets(surface, "hliq_h20", frozen_dates),
                        k=TOP_K,
                    ),
                }
                for horizon in [10, 20, 40]
            },
            "conditional_liquidity_dependence": conditional_liquidity(surface, frozen_dates),
            "missingness_stress": missingness_stress(surface, frozen_dates),
            "listing_age_audit": listing_age_audit(surface, frozen_dates, args.security_master),
            "sector_data_available": False,
            "interpretation": {
                "single_bounded_robustness_audit": True,
                "literature_is_not_idx_evidence": True,
                "no_parameter_selection": True,
                "novelty_status": "NOVELTY_PENDING",
                "economic_status": "ECONOMIC_CAUTION",
                "predictive_claim": False,
            },
            "inputs": {
                "features_sha256": sha256_file(args.features),
                "panel_sha256": sha256_file(args.panel),
                "sessions_sha256": sha256_file(args.sessions),
                "anchors_sha256": sha256_file(args.anchors),
                "security_master_sha256": sha256_file(args.security_master),
            },
            "code_sha256": sha256_file(Path(__file__)),
        }
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(args.out), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
