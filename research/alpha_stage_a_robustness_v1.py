"""Outcome-blind temporal robustness audit for Stage A features."""

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


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def candidate_slice_stats(frame: pd.DataFrame) -> dict[str, object]:
    output: dict[str, object] = {}
    date_counts = frame.groupby("date", sort=True).size()
    for column in CANDIDATES:
        finite = np.isfinite(pd.to_numeric(frame[column], errors="coerce"))
        finite_frame = frame.loc[finite]
        per_date = finite_frame.groupby("date", sort=True).size()
        per_ticker = finite_frame.groupby("ticker", sort=True).size()
        output[column] = {
            "finite_rows": int(finite.sum()),
            "coverage": float(finite.mean()) if len(frame) else None,
            "date_count": int(finite_frame["date"].nunique()),
            "ticker_count": int(finite_frame["ticker"].nunique()),
            "median_finite_names_per_date": float(per_date.median()) if len(per_date) else None,
            "q10_finite_names_per_date": float(per_date.quantile(0.10)) if len(per_date) else None,
            "min_finite_names_per_date": int(per_date.min()) if len(per_date) else None,
            "top_10_ticker_share": float(per_ticker.nlargest(10).sum() / finite.sum()) if finite.sum() else None,
            "finite_dates_over_all_dates": float(len(per_date) / len(date_counts)) if len(date_counts) else None,
        }
    corr = frame[CANDIDATES].corr(method="spearman", min_periods=100).round(8)
    return {
        "date_min": str(frame["date"].min().date()) if len(frame) else None,
        "date_max": str(frame["date"].max().date()) if len(frame) else None,
        "row_count": int(len(frame)),
        "date_count": int(frame["date"].nunique()),
        "candidate_stats": output,
        "spearman": corr.to_dict(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    frame = pd.read_parquet(args.features)
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    frame = frame.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    dates = pd.Index(frame["date"].drop_duplicates().sort_values())
    chunks = np.array_split(dates.to_numpy(), 6)
    slices = {}
    for index, chunk in enumerate(chunks, start=1):
        slices[f"slice_{index}"] = candidate_slice_stats(frame[frame["date"].isin(chunk)])

    midpoint = dates[len(dates) // 2]
    first = frame[frame["date"] < midpoint]
    second = frame[frame["date"] >= midpoint]
    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "source_features_sha256": sha256_file(args.features),
        "row_count": int(len(frame)),
        "date_count": int(len(dates)),
        "date_min": str(dates.min().date()),
        "date_max": str(dates.max().date()),
        "six_equal_date_slices": slices,
        "first_half": candidate_slice_stats(first),
        "second_half": candidate_slice_stats(second),
        "midpoint": str(midpoint.date()),
        "outcome_accessed": False,
    }
    safe_result = json_safe(result)
    args.out.write_text(json.dumps(safe_result, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    result["output_sha256"] = sha256_file(args.out)
    print(json.dumps({**safe_result, "output_sha256": result["output_sha256"]}, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
