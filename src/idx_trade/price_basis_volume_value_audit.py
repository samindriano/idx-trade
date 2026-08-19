"""Helpers for bounded volume/value price-basis audit.

This audit is diagnostic only. It does not repair any field or fit/score models.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

FACTOR_RTOL = 1e-6
FACTOR_ATOL = 1e-6


def normalize_ticker(s: pd.Series) -> pd.Series:
    return s.astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()


def normalize_date(s: pd.Series, label: str) -> pd.Series:
    out = pd.to_datetime(s, errors="coerce").dt.tz_localize(None).dt.normalize()
    if out.isna().any():
        raise ValueError(f"{label} contains invalid dates")
    return out


def numeric_series(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s.dtype):
        return pd.to_numeric(s, errors="coerce").astype(float)
    return pd.to_numeric(
        s.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    ).astype(float)


def classify_basis_ratio(
    panel_value: float,
    official_value: float,
    factor: float,
    *,
    rtol: float = FACTOR_RTOL,
    atol: float = FACTOR_ATOL,
) -> tuple[str, float]:
    """Classify panel/official ratio against same basis and CA factor hypotheses."""
    values = np.asarray([panel_value, official_value, factor], dtype=float)
    if not np.isfinite(values).all() or panel_value <= 0.0 or official_value <= 0.0 or factor <= 1.0:
        return "INVALID_OR_MISSING", np.nan
    ratio = float(panel_value / official_value)
    if np.isclose(ratio, 1.0, rtol=rtol, atol=atol):
        return "SAME_BASIS", ratio
    if np.isclose(ratio, factor, rtol=rtol, atol=atol):
        return "CA_FACTOR", ratio
    inverse = 1.0 / factor
    if np.isclose(ratio, inverse, rtol=rtol, atol=atol):
        return "INVERSE_CA_FACTOR", ratio
    return "OTHER_RATIO", ratio


def classify_frame(
    frame: pd.DataFrame,
    *,
    panel_column: str,
    official_column: str,
    factor_column: str = "expected_factor",
    output_prefix: str,
) -> pd.DataFrame:
    required = {panel_column, official_column, factor_column}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"classification missing columns: {sorted(missing)}")
    out = frame.copy()
    panel = numeric_series(out[panel_column])
    official = numeric_series(out[official_column])
    factor = numeric_series(out[factor_column])
    labels: list[str] = []
    ratios: list[float] = []
    for p, o, f in zip(panel, official, factor, strict=True):
        label, ratio = classify_basis_ratio(p, o, f)
        labels.append(label)
        ratios.append(ratio)
    out[f"{output_prefix}_basis_class"] = labels
    out[f"{output_prefix}_panel_over_idx_ratio"] = ratios
    return out


def class_summary(frame: pd.DataFrame, class_column: str) -> dict[str, Any]:
    counts = frame[class_column].astype(str).value_counts(dropna=False).to_dict()
    return {
        "rows": int(len(frame)),
        "classes": {str(k): int(v) for k, v in counts.items()},
        "ca_factor_rows": int(frame[class_column].isin(["CA_FACTOR", "INVERSE_CA_FACTOR"]).sum()),
        "same_basis_rows": int(frame[class_column].eq("SAME_BASIS").sum()),
        "other_ratio_rows": int(frame[class_column].eq("OTHER_RATIO").sum()),
        "invalid_or_missing_rows": int(frame[class_column].eq("INVALID_OR_MISSING").sum()),
    }


def ticker_factor_evidence(
    frame: pd.DataFrame,
    *,
    class_column: str,
    minimum_rows: int = 3,
) -> pd.DataFrame:
    """Summarize tickers with repeated CA-factor-consistent field ratios."""
    if minimum_rows < 1:
        raise ValueError("minimum_rows must be positive")
    bad = frame[frame[class_column].isin(["CA_FACTOR", "INVERSE_CA_FACTOR"])].copy()
    if bad.empty:
        return pd.DataFrame(columns=["ticker", "factor_consistent_rows", "basis_classes", "requires_basis_remediation"])
    rows: list[dict[str, Any]] = []
    for ticker, block in bad.groupby("ticker", sort=True):
        rows.append({
            "ticker": str(ticker),
            "factor_consistent_rows": int(len(block)),
            "basis_classes": "|".join(sorted(set(block[class_column].astype(str)))),
            "requires_basis_remediation": bool(len(block) >= minimum_rows),
        })
    return pd.DataFrame(rows).sort_values("ticker", kind="mergesort").reset_index(drop=True)
