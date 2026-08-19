"""Outcome-blind helpers for post-remediation Open price-basis forensics.

No field repair is performed here.  The helpers compare an existing accepted
Open against corrected raw H/L and an independently certified multiplicative
factor, plus official IDX OpenPrice when available.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series.dtype):
        return pd.to_numeric(series, errors="coerce").astype(float)
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    ).astype(float)


def within_hlc(open_value: pd.Series, low: pd.Series, high: pd.Series) -> pd.Series:
    o = numeric(open_value)
    l = numeric(low)
    h = numeric(high)
    valid = np.isfinite(o) & np.isfinite(l) & np.isfinite(h) & o.gt(0.0) & l.gt(0.0) & h.gt(0.0) & h.ge(l)
    return valid & o.ge(l) & o.le(h)


def exact_numeric(left: pd.Series, right: pd.Series, *, atol: float = 1e-9) -> pd.Series:
    a = numeric(left).to_numpy(dtype=float)
    b = numeric(right).to_numpy(dtype=float)
    finite = np.isfinite(a) & np.isfinite(b)
    result = np.zeros(len(a), dtype=bool)
    result[finite] = np.isclose(a[finite], b[finite], rtol=0.0, atol=atol)
    return pd.Series(result, index=left.index)


def classify_open_basis(rows: pd.DataFrame) -> pd.DataFrame:
    required = {"accepted_open", "low", "high", "expected_factor", "official_open"}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"open forensic missing columns: {sorted(missing)}")
    out = rows.copy()
    accepted = numeric(out["accepted_open"])
    factor = numeric(out["expected_factor"])
    official = numeric(out["official_open"])
    out["accepted_open"] = accepted
    out["official_open"] = official
    out["factor_up_open"] = accepted * factor
    out["factor_down_open"] = accepted / factor
    out["accepted_within_corrected_hlc"] = within_hlc(accepted, out["low"], out["high"])
    out["factor_up_within_corrected_hlc"] = within_hlc(out["factor_up_open"], out["low"], out["high"])
    out["factor_down_within_corrected_hlc"] = within_hlc(out["factor_down_open"], out["low"], out["high"])
    out["official_open_positive"] = np.isfinite(official) & official.gt(0.0)
    out["official_open_within_corrected_hlc"] = within_hlc(official, out["low"], out["high"])
    out["accepted_equals_official"] = exact_numeric(accepted, official)
    out["factor_up_equals_official"] = exact_numeric(out["factor_up_open"], official)
    out["factor_down_equals_official"] = exact_numeric(out["factor_down_open"], official)
    return out


def summary(rows: pd.DataFrame) -> dict[str, Any]:
    if rows.empty:
        raise ValueError("open forensic rows empty")
    bool_columns = (
        "accepted_within_corrected_hlc",
        "factor_up_within_corrected_hlc",
        "factor_down_within_corrected_hlc",
        "official_open_positive",
        "official_open_within_corrected_hlc",
        "accepted_equals_official",
        "factor_up_equals_official",
        "factor_down_equals_official",
    )
    return {
        "rows": int(len(rows)),
        **{column: int(rows[column].astype(bool).sum()) for column in bool_columns},
    }
