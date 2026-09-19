"""Frozen-window structural robustness audit for corrected Stage A features."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


CANDIDATES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C3_financial_quality_growth_v1",
    "C4_path_efficiency_reversal_20_v1",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe(value):
    if isinstance(value, dict):
        return {key: safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe(item) for item in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    if isinstance(value, np.integer):
        return int(value)
    return value


def stats(frame: pd.DataFrame) -> dict[str, object]:
    eligible = frame["eligible_decision_universe"].fillna(False).astype(bool)
    result: dict[str, object] = {
        "date_min": str(frame["date"].min().date()) if len(frame) else None,
        "date_max": str(frame["date"].max().date()) if len(frame) else None,
        "date_count": int(frame["date"].nunique()),
        "row_count": int(len(frame)),
        "eligible_rows": int(eligible.sum()),
        "candidate_stats": {},
    }
    for column in CANDIDATES:
        finite = np.isfinite(pd.to_numeric(frame[column], errors="coerce"))
        finite_eligible = finite & eligible
        per_date = frame.loc[finite_eligible].groupby("date", sort=True).size()
        per_ticker = frame.loc[finite_eligible].groupby("ticker", sort=True).size()
        result["candidate_stats"][column] = {
            "finite_eligible_rows": int(finite_eligible.sum()),
            "coverage_of_eligible_rows": float(finite_eligible.sum() / eligible.sum()) if eligible.sum() else None,
            "date_count": int(frame.loc[finite_eligible, "date"].nunique()),
            "ticker_count": int(frame.loc[finite_eligible, "ticker"].nunique()),
            "median_finite_names_per_date": float(per_date.median()) if len(per_date) else None,
            "q10_finite_names_per_date": float(per_date.quantile(0.10)) if len(per_date) else None,
            "min_finite_names_per_date": int(per_date.min()) if len(per_date) else None,
            "top_10_ticker_share": float(per_ticker.nlargest(10).sum() / finite_eligible.sum())
            if finite_eligible.sum()
            else None,
        }
    result["spearman"] = frame.loc[eligible, CANDIDATES].corr(method="spearman", min_periods=100).round(8).to_dict()
    return safe(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    features = pd.read_parquet(args.features)
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions["date"].drop_duplicates().sort_values().reset_index(drop=True)
    if len(sessions) < 600:
        raise ValueError("frozen six-fold audit requires at least 600 official sessions")
    frozen_dates = sessions.iloc[-600:]
    features = features[features["date"].isin(frozen_dates)].sort_values(
        ["date", "ticker"], kind="mergesort"
    )
    folds = {}
    for index in range(6):
        fold_dates = frozen_dates.iloc[index * 100 : (index + 1) * 100]
        folds[f"fold_{index + 1}"] = stats(features[features["date"].isin(fold_dates)])
    first_dates = frozen_dates.iloc[:300]
    last_dates = frozen_dates.iloc[300:]
    result = safe(
        {
            "status": "PASS_STRUCTURAL_ONLY",
            "protocol": "2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1",
            "implementation": "alpha_stage_a_robustness_v2",
            "outcome_accessed": False,
            "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "features_sha256": sha256_file(args.features),
            "sessions_sha256": sha256_file(args.sessions),
            "frozen_session_count": int(len(frozen_dates)),
            "frozen_date_min": str(frozen_dates.min().date()),
            "frozen_date_max": str(frozen_dates.max().date()),
            "folds": folds,
            "first_half": stats(features[features["date"].isin(first_dates)]),
            "last_half": stats(features[features["date"].isin(last_dates)]),
        }
    )
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    print(json.dumps({**result, "output_sha256": sha256_file(args.out)}, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
