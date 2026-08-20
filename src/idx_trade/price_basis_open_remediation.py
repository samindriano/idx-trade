"""Immutable Open price-basis remediation helpers.

Policy is frozen from the accepted residual adjudication before remediation:
1) official IDX OpenPrice is primary whenever positive and inside corrected H/L;
2) otherwise use accepted Open multiplied by the independently certified CA factor
   only when that transformed Open is inside corrected H/L;
3) otherwise fail closed with Open unavailable.

This module never fits/scores models or accesses outcomes.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

OFFICIAL_CLASS = "OFFICIAL_IDX_OPEN_PRIMARY_CANDIDATE"
FALLBACK_CLASS = "CA_FACTOR_FALLBACK_CANDIDATE"
DISAGREEMENT_CLASS = "OFFICIAL_PRIMARY_FACTOR_DISAGREEMENT"
UNRESOLVED_CLASS = "UNRESOLVED_NO_OFFICIAL_FACTOR_OUT_OF_RANGE"


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype(float)


def _within(value: pd.Series, low: pd.Series, high: pd.Series) -> pd.Series:
    v = _numeric(value)
    l = _numeric(low)
    h = _numeric(high)
    valid = np.isfinite(v) & np.isfinite(l) & np.isfinite(h) & v.gt(0.0) & l.gt(0.0) & h.gt(0.0) & h.ge(l)
    return valid & v.ge(l) & v.le(h)


def materialize_open_candidate(rows: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = {
        "ticker", "date", "adjudication_class", "official_open", "factor_up_open",
        "low", "high", "accepted_open", "accepted_open_source", "expected_factor",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"open remediation rows missing columns: {sorted(missing)}")
    out = rows.copy()
    labels = out["adjudication_class"].astype(str)
    official_mask = labels.isin([OFFICIAL_CLASS, DISAGREEMENT_CLASS])
    fallback_mask = labels.eq(FALLBACK_CLASS)
    unresolved_mask = labels.eq(UNRESOLVED_CLASS)
    if not (official_mask | fallback_mask | unresolved_mask).all():
        unknown = sorted(set(labels[~(official_mask | fallback_mask | unresolved_mask)]))
        raise ValueError(f"unrecognized adjudication classes: {unknown}")

    out["remediated_open"] = np.nan
    out.loc[official_mask, "remediated_open"] = _numeric(out.loc[official_mask, "official_open"])
    out.loc[fallback_mask, "remediated_open"] = _numeric(out.loc[fallback_mask, "factor_up_open"])
    out["open_admitted_after"] = ~unresolved_mask
    out["open_remediation_source"] = np.select(
        [official_mask, fallback_mask, unresolved_mask],
        ["IDX_OFFICIAL_OPENPRICE", "CA_FACTOR_RECONSTRUCTION", "FAIL_CLOSED_UNAVAILABLE"],
        default="UNCLASSIFIED",
    )
    out["open_remediation_policy"] = "IDX_OPENPRICE_PRIMARY_CA_FACTOR_FALLBACK_FAIL_CLOSED_V1"

    admitted = out["open_admitted_after"].astype(bool)
    if out.loc[admitted, "remediated_open"].isna().any():
        raise ValueError("admitted remediation row missing Open")
    if out.loc[~admitted, "remediated_open"].notna().any():
        raise ValueError("fail-closed remediation row unexpectedly has Open")
    within = _within(out["remediated_open"], out["low"], out["high"])
    if not within.loc[admitted].all():
        raise ValueError("remediated Open outside corrected H/L")
    out["remediated_open_within_corrected_hlc"] = within

    diagnostics = {
        "rows": int(len(out)),
        "official_primary_rows": int(official_mask.sum()),
        "factor_fallback_rows": int(fallback_mask.sum()),
        "unresolved_fail_closed_rows": int(unresolved_mask.sum()),
        "admitted_rows": int(admitted.sum()),
        "admitted_within_corrected_hlc_rows": int(within.loc[admitted].sum()),
        "official_factor_disagreement_rows": int(labels.eq(DISAGREEMENT_CLASS).sum()),
    }
    return out, diagnostics


def overlay_view(rows: pd.DataFrame) -> pd.DataFrame:
    admitted = rows[rows["open_admitted_after"].astype(bool)].copy()
    cols = [
        "ticker", "date", "remediated_open", "open_remediation_source",
        "open_remediation_policy", "adjudication_class", "accepted_open",
        "accepted_open_source", "expected_factor", "low", "high",
    ]
    return admitted[cols].sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def fail_closed_view(rows: pd.DataFrame) -> pd.DataFrame:
    unresolved = rows[~rows["open_admitted_after"].astype(bool)].copy()
    cols = [
        "ticker", "date", "adjudication_class", "accepted_open",
        "accepted_open_source", "expected_factor", "factor_up_open", "low", "high",
        "open_remediation_source", "open_remediation_policy",
    ]
    return unresolved[cols].sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
