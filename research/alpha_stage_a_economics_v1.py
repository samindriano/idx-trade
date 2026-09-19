"""Outcome-blind structural economics audit for the frozen Stage A candidates.

This computes only portfolio-construction diagnostics from the already frozen
candidate ranks and frozen-only OHLCV market-value field. It does not read a
target, forward label, incumbent score, provider, or protected artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


CANDIDATES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C3_financial_quality_growth_v1",
    "C4_path_efficiency_reversal_20_v1",
]
TOP_N = 30
FROZEN_SESSION_COUNT = 600
BASE_COST_BPS_PER_MATCHED_TURNOVER = 60.0
SENSITIVITY_COST_BPS_PER_MATCHED_TURNOVER = 110.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def q(series: pd.Series, quantile: float) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.quantile(quantile))


def finite_float(value: float | int | np.floating | None) -> float | None:
    if value is None or not np.isfinite(value):
        return None
    return float(value)


def summarize_candidate(
    candidate: str,
    frame: pd.DataFrame,
    sessions: pd.DataFrame,
) -> dict[str, object]:
    rank_column = f"rank_{candidate}"
    eligible = frame["eligible_decision_universe"].astype(bool)
    finite = pd.to_numeric(frame[rank_column], errors="coerce").notna() & eligible
    candidate_frame = frame.loc[finite, ["ticker", "date", rank_column, "regular_market_value"]].copy()
    candidate_frame[rank_column] = pd.to_numeric(candidate_frame[rank_column], errors="coerce")
    candidate_frame["regular_market_value"] = pd.to_numeric(
        candidate_frame["regular_market_value"], errors="coerce"
    )

    top_rows: list[tuple[pd.Timestamp, list[str], float, float | None, float | None]] = []
    for date, group in candidate_frame.groupby("date", sort=True):
        selected = group.sort_values([rank_column, "ticker"], ascending=[False, True], kind="mergesort").head(TOP_N)
        if len(selected) < TOP_N:
            continue
        values = selected["regular_market_value"]
        finite_value = values[np.isfinite(values) & (values > 0)]
        top_rows.append(
            (
                pd.Timestamp(date),
                selected["ticker"].astype(str).tolist(),
                float(len(finite_value) / TOP_N),
                finite_float(finite_value.median()) if not finite_value.empty else None,
                finite_float((finite_value * 0.01).median()) if not finite_value.empty else None,
            )
        )

    top_rows.sort(key=lambda row: row[0])
    top_dates = [row[0] for row in top_rows]
    top_sets = {row[0]: set(row[1]) for row in top_rows}
    session_index = dict(zip(sessions["date"], sessions.index, strict=True))
    turnovers: list[float] = []
    for previous, current in zip(top_dates, top_dates[1:]):
        if session_index.get(current) != session_index.get(previous, -2) + 1:
            continue
        overlap = len(top_sets[previous] & top_sets[current])
        turnovers.append(float(1.0 - overlap / TOP_N))

    selected = candidate_frame[candidate_frame["date"].isin(top_dates)].copy()
    selected = selected.sort_values(["date", rank_column, "ticker"], ascending=[True, False, True], kind="mergesort")
    selected = selected.groupby("date", sort=False, group_keys=False).head(TOP_N)
    slot_counts = selected["ticker"].astype(str).value_counts()
    total_slots = int(len(selected))
    top10_slots = int(slot_counts.head(10).sum()) if total_slots else 0
    selected_values = selected["regular_market_value"]
    positive_values = selected_values[np.isfinite(selected_values) & (selected_values > 0)]
    top30_counts = pd.Series([len(top_sets[date]) for date in top_dates], dtype="float64")
    turnover_series = pd.Series(turnovers, dtype="float64")

    return {
        "candidate": candidate,
        "candidate_finite_rows": int(len(candidate_frame)),
        "candidate_finite_dates": int(candidate_frame["date"].nunique()),
        "candidate_finite_tickers": int(candidate_frame["ticker"].nunique()),
        "top30_dates": int(len(top_dates)),
        "top30_tickers": int(slot_counts.size),
        "top30_selection_slots": total_slots,
        "top30_market_value_coverage": finite_float(float(selected_values.notna().mean())) if total_slots else None,
        "top30_positive_market_value_coverage": finite_float(float(len(positive_values) / total_slots)) if total_slots else None,
        "top30_median_regular_market_value_idr": finite_float(float(positive_values.median())) if not positive_values.empty else None,
        "top30_q10_regular_market_value_idr": q(positive_values, 0.10),
        "top30_median_one_percent_capacity_idr": finite_float(float((positive_values * 0.01).median())) if not positive_values.empty else None,
        "top30_q10_one_percent_capacity_idr": q(positive_values * 0.01, 0.10),
        "turnover_observations_consecutive_sessions": int(len(turnovers)),
        "one_way_turnover_mean": finite_float(turnover_series.mean()),
        "one_way_turnover_median": finite_float(turnover_series.median()),
        "one_way_turnover_q95": q(turnover_series, 0.95),
        "one_way_turnover_max": finite_float(turnover_series.max()),
        "base_friction_bps_mean_of_nav": finite_float(turnover_series.mean() * BASE_COST_BPS_PER_MATCHED_TURNOVER),
        "sensitivity_friction_bps_mean_of_nav": finite_float(turnover_series.mean() * SENSITIVITY_COST_BPS_PER_MATCHED_TURNOVER),
        "top10_ticker_slot_share": finite_float(top10_slots / total_slots) if total_slots else None,
        "largest_single_ticker_slot_share": finite_float(slot_counts.iloc[0] / total_slots) if total_slots else None,
        "mean_daily_unique_top30": finite_float(top30_counts.mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    feature_columns = [
        "ticker",
        "date",
        "eligible_decision_universe",
        *(f"rank_{candidate}" for candidate in CANDIDATES),
    ]
    features = pd.read_parquet(args.features, columns=feature_columns)
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    panel = pd.read_parquet(args.panel, columns=["ticker", "date", "regular_market_value"])
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel contains duplicate ticker/date keys")
    if features.duplicated(["ticker", "date"]).any():
        raise ValueError("features contain duplicate ticker/date keys")

    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.drop_duplicates("date").sort_values("date", kind="mergesort").reset_index(drop=True)
    if len(sessions) < FROZEN_SESSION_COUNT:
        raise ValueError("official session source is shorter than frozen window")
    frozen_sessions = sessions.tail(FROZEN_SESSION_COUNT).copy().reset_index(drop=True)
    frozen_dates = set(frozen_sessions["date"])
    features = features[features["date"].isin(frozen_dates)].copy()
    features = features.merge(panel, on=["ticker", "date"], how="left", validate="one_to_one", indicator=True)
    if not features["_merge"].eq("both").all():
        raise ValueError("feature/panel key closure failed")
    features = features.drop(columns=["_merge"])

    candidates = {
        candidate: summarize_candidate(candidate, features, frozen_sessions)
        for candidate in CANDIDATES
    }
    slice_metrics: dict[str, dict[str, object]] = {}
    for slice_name, slice_sessions in {
        "first_300": frozen_sessions.head(300).copy().reset_index(drop=True),
        "last_300": frozen_sessions.tail(300).copy().reset_index(drop=True),
    }.items():
        slice_dates = set(slice_sessions["date"])
        slice_frame = features[features["date"].isin(slice_dates)].copy()
        slice_metrics[slice_name] = {
            "session_count": int(len(slice_sessions)),
            "window_start": slice_sessions["date"].min().strftime("%Y-%m-%d"),
            "window_end": slice_sessions["date"].max().strftime("%Y-%m-%d"),
            "candidate_metrics": {
                candidate: summarize_candidate(candidate, slice_frame, slice_sessions)
                for candidate in CANDIDATES
            },
        }
    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "protocol": "2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1",
        "stage": "A_OUTCOME_BLIND_ECONOMICS",
        "outcome_accessed": False,
        "provider_accessed": False,
        "target_accessed": False,
        "incumbent_score_accessed": False,
        "top_n": TOP_N,
        "frozen_session_count": FROZEN_SESSION_COUNT,
        "frozen_window_start": frozen_sessions["date"].min().strftime("%Y-%m-%d"),
        "frozen_window_end": frozen_sessions["date"].max().strftime("%Y-%m-%d"),
        "friction_contract": {
            "buy_fee_bps": 15.0,
            "sell_fee_bps": 25.0,
            "slippage_bps_per_side": 10.0,
            "base_matched_turnover_bps": BASE_COST_BPS_PER_MATCHED_TURNOVER,
            "sensitivity_matched_turnover_bps": SENSITIVITY_COST_BPS_PER_MATCHED_TURNOVER,
            "interpretation": "structural cost burden only; not realized net alpha",
        },
        "source_classification": "PARTIAL_FROZEN_ONLY_CAPABILITY_DIAGNOSTIC",
        "source_hashes": {
            "features": sha256_file(args.features),
            "panel": sha256_file(args.panel),
            "official_sessions": sha256_file(args.sessions),
        },
        "code_sha256": sha256_file(Path(__file__)),
        "candidate_metrics": candidates,
        "candidate_metrics_by_slice": slice_metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
