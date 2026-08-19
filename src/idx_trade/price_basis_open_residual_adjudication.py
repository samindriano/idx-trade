"""Outcome-blind residual adjudication helpers for Open price-basis forensics.

This module classifies evidence only. It does not repair Open, mutate panels,
fit/score models, or access targets/outcomes.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    if not set(normalized.dropna().unique()).issubset({"true", "false"}):
        raise ValueError("invalid boolean column")
    return normalized.eq("true")


def classify_residuals(rows: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker", "date", "accepted_open", "factor_up_open", "official_open",
        "low", "high", "official_open_positive", "official_open_within_corrected_hlc",
        "factor_up_within_corrected_hlc", "factor_up_equals_official",
        "accepted_open_source", "expected_factor",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"open residual rows missing columns: {sorted(missing)}")
    out = rows.copy()
    official_positive = _bool(out["official_open_positive"])
    official_within = _bool(out["official_open_within_corrected_hlc"])
    factor_within = _bool(out["factor_up_within_corrected_hlc"])
    factor_equals = _bool(out["factor_up_equals_official"])

    out["official_primary_candidate"] = official_positive & official_within
    out["factor_fallback_candidate"] = (~official_positive) & factor_within
    out["official_factor_disagreement"] = official_positive & official_within & ~factor_equals
    out["factor_range_failure"] = ~factor_within
    out["unresolved_no_official_no_factor"] = (~official_positive) & (~factor_within)

    factor_up = pd.to_numeric(out["factor_up_open"], errors="coerce").astype(float)
    official = pd.to_numeric(out["official_open"], errors="coerce").astype(float)
    low = pd.to_numeric(out["low"], errors="coerce").astype(float)
    high = pd.to_numeric(out["high"], errors="coerce").astype(float)
    out["factor_minus_official"] = factor_up - official
    out["factor_abs_minus_official"] = (factor_up - official).abs()
    out["factor_distance_below_low"] = (low - factor_up).clip(lower=0.0)
    out["factor_distance_above_high"] = (factor_up - high).clip(lower=0.0)

    labels = np.full(len(out), "UNCLASSIFIED", dtype=object)
    labels[out["official_primary_candidate"].to_numpy()] = "OFFICIAL_IDX_OPEN_PRIMARY_CANDIDATE"
    labels[out["factor_fallback_candidate"].to_numpy()] = "CA_FACTOR_FALLBACK_CANDIDATE"
    labels[out["official_factor_disagreement"].to_numpy()] = "OFFICIAL_PRIMARY_FACTOR_DISAGREEMENT"
    labels[out["unresolved_no_official_no_factor"].to_numpy()] = "UNRESOLVED_NO_OFFICIAL_FACTOR_OUT_OF_RANGE"
    out["adjudication_class"] = labels
    return out


def summarize(rows: pd.DataFrame) -> dict[str, Any]:
    if rows.empty:
        raise ValueError("open residual rows empty")
    classes = rows["adjudication_class"].astype(str).value_counts().to_dict()
    return {
        "rows": int(len(rows)),
        "tickers": int(rows["ticker"].astype(str).nunique()),
        "classes": {str(k): int(v) for k, v in classes.items()},
        "official_primary_candidates": int(rows["official_primary_candidate"].astype(bool).sum()),
        "factor_fallback_candidates": int(rows["factor_fallback_candidate"].astype(bool).sum()),
        "official_factor_disagreements": int(rows["official_factor_disagreement"].astype(bool).sum()),
        "factor_range_failures": int(rows["factor_range_failure"].astype(bool).sum()),
        "unresolved_no_official_no_factor": int(rows["unresolved_no_official_no_factor"].astype(bool).sum()),
    }


def ticker_mechanism_summary(rows: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for ticker, block in rows.groupby("ticker", sort=True):
        official = _bool(block["official_open_positive"])
        exact = _bool(block["factor_up_equals_official"])
        within = _bool(block["factor_up_within_corrected_hlc"])
        official_rows = int(official.sum())
        exact_rows = int((official & exact).sum())
        records.append({
            "ticker": str(ticker),
            "rows": int(len(block)),
            "official_positive_rows": official_rows,
            "factor_equals_official_rows": exact_rows,
            "factor_equals_official_rate_on_official": float(exact_rows / official_rows) if official_rows else np.nan,
            "factor_within_corrected_hlc_rows": int(within.sum()),
            "factor_range_failure_rows": int((~within).sum()),
            "official_factor_disagreement_rows": int((official & ~exact).sum()),
        })
    return pd.DataFrame(records).sort_values("ticker", kind="mergesort").reset_index(drop=True)
