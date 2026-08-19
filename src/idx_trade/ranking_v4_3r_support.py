"""Outcome-blind support re-admission helpers for V4-3R CA80.

V4-3R is a new preregistered generation.  It does not mutate row-level target
observability or corporate-action semantics inherited from V4-3.  It only
recomputes date-level admission booleans from already frozen supported-row
counts/rates using the new round 80% threshold.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


GATE_RATE = 0.80
REFERENCE_V4_3_GATE_RATE = 0.90


def rethreshold_per_date_support(frame: pd.DataFrame, *, gate_rate: float = GATE_RATE) -> pd.DataFrame:
    required = {
        "session_index",
        "date",
        "decision_rows",
        "h5_supported_rows",
        "h10_supported_rows",
        "consensus_supported_rows",
        "h5_rate",
        "h10_rate",
        "consensus_rate",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"per-date support missing columns: {sorted(missing)}")
    if not (0.0 < float(gate_rate) <= 1.0):
        raise ValueError("gate_rate must be in (0, 1]")

    out = frame.copy()
    out["session_index"] = pd.to_numeric(out["session_index"], errors="raise").astype(int)
    out["date"] = pd.to_datetime(out["date"], errors="raise").dt.normalize()
    out["decision_rows"] = pd.to_numeric(out["decision_rows"], errors="raise").astype(int)
    if out["decision_rows"].le(0).any():
        raise RuntimeError("V4_3R_DECISION_ROWS_NON_POSITIVE")

    for prefix in ("h5", "h10", "consensus"):
        supported_col = f"{prefix}_supported_rows"
        rate_col = f"{prefix}_rate"
        eligible_col = f"{prefix}_eligible"
        out[supported_col] = pd.to_numeric(out[supported_col], errors="raise").astype(int)
        out[rate_col] = pd.to_numeric(out[rate_col], errors="raise").astype(float)
        if out[supported_col].lt(0).any() or (out[supported_col] > out["decision_rows"]).any():
            raise RuntimeError(f"V4_3R_SUPPORTED_ROW_COUNT_INVALID:{prefix}")
        recomputed = out[supported_col] / out["decision_rows"]
        if not np.allclose(out[rate_col].to_numpy(), recomputed.to_numpy(), rtol=0.0, atol=1e-12):
            raise RuntimeError(f"V4_3R_STORED_RATE_MISMATCH:{prefix}")
        out[eligible_col] = out[rate_col].ge(float(gate_rate))

    if out.duplicated(["session_index", "date"]).any():
        raise RuntimeError("V4_3R_PER_DATE_IDENTITY_DUPLICATED")
    return out.sort_values("session_index", kind="mergesort").reset_index(drop=True)


def support_bucket(rate: float) -> str:
    value = float(rate)
    if value < GATE_RATE:
        return "below_0.80"
    if value < REFERENCE_V4_3_GATE_RATE:
        return "0.80_to_below_0.90"
    return "at_least_0.90"


def frozen_support_bucket_counts(per_date: pd.DataFrame, validation_folds: pd.DataFrame) -> dict[str, int]:
    required = {"session_index", "date", "consensus_rate"}
    missing = required - set(per_date.columns)
    if missing:
        raise ValueError(f"per-date support missing bucket columns: {sorted(missing)}")
    folds = validation_folds[["session_index", "date"]].copy()
    folds["session_index"] = pd.to_numeric(folds["session_index"], errors="raise").astype(int)
    folds["date"] = pd.to_datetime(folds["date"], errors="raise").dt.normalize()
    if len(folds) != 600 or folds.duplicated(["session_index", "date"]).any():
        raise RuntimeError("V4_3R_FROZEN_VALIDATION_IDENTITY_INVALID")
    source = per_date[["session_index", "date", "consensus_rate"]].copy()
    source["date"] = pd.to_datetime(source["date"], errors="raise").dt.normalize()
    merged = folds.merge(source, on=["session_index", "date"], how="left", validate="one_to_one")
    if merged["consensus_rate"].isna().any():
        raise RuntimeError("V4_3R_FROZEN_SUPPORT_MISSING")
    buckets = merged["consensus_rate"].map(support_bucket).value_counts().to_dict()
    return {
        "below_0.80": int(buckets.get("below_0.80", 0)),
        "0.80_to_below_0.90": int(buckets.get("0.80_to_below_0.90", 0)),
        "at_least_0.90": int(buckets.get("at_least_0.90", 0)),
    }
