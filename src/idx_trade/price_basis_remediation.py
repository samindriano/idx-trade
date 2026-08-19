"""Immutable H/L/C price-basis remediation helpers.

The remediation is intentionally narrow. It only replaces H/L/C on rows that
were already classified by the frozen Step-2 audit as stable multiplicative
panel-vs-official-IDX mismatches, have parent provenance YAHOO_RAW, and match an
independently certified corporate-action share-count factor before that action's
record date. No other panel field is changed.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

HLC = ("high", "low", "close")
FACTOR_RTOL = 1e-6
EXPECTED_PARENT_PROVENANCE = "YAHOO_RAW"
EXPECTED_CERT_STATUS = "CERTIFIED_PRIMARY"


def _ticker(s: pd.Series) -> pd.Series:
    return s.astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()


def _date(s: pd.Series, label: str) -> pd.Series:
    out = pd.to_datetime(s, errors="coerce").dt.tz_localize(None).dt.normalize()
    if out.isna().any():
        raise ValueError(f"{label} contains invalid dates")
    return out


def _bool(s: pd.Series, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(s.dtype):
        return s.astype(bool)
    x = s.astype(str).str.strip().str.lower()
    if not set(x.unique()).issubset({"true", "false"}):
        raise ValueError(f"{label} contains invalid booleans")
    return x.eq("true")


def validate_certification(cert: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker", "expected_factor", "ca_type", "ca_ratio", "record_date",
        "distribution_date", "source", "source_url", "certification_status",
    }
    missing = required - set(cert.columns)
    if missing:
        raise ValueError(f"certification missing columns: {sorted(missing)}")
    out = cert.copy()
    out["ticker"] = _ticker(out["ticker"])
    out["expected_factor"] = pd.to_numeric(out["expected_factor"], errors="coerce")
    out["record_date"] = _date(out["record_date"], "cert record_date")
    out["distribution_date"] = _date(out["distribution_date"], "cert distribution_date")
    if out["ticker"].eq("").any() or out["ticker"].duplicated().any():
        raise ValueError("certification ticker identity invalid")
    if out["expected_factor"].isna().any() or out["expected_factor"].le(1.0).any():
        raise ValueError("certification expected_factor must be >1")
    if not out["certification_status"].eq(EXPECTED_CERT_STATUS).all():
        raise ValueError("certification contains non-primary rows")
    if not out["source"].eq("KSEI").all():
        raise ValueError("certification source must be KSEI")
    if not out["source_url"].astype(str).str.startswith("https://web.ksei.co.id/").all():
        raise ValueError("certification source_url must be KSEI web")
    if (out["distribution_date"] < out["record_date"]).any():
        raise ValueError("distribution date precedes record date")
    return out.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def select_certified_repairs(basis: pd.DataFrame, cert: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = {
        "ticker", "date", "price_provenance", "panel_idx_stable_run_member",
        "panel_idx_scale_factor", "panel_high", "panel_low", "panel_close",
        "idx_high", "idx_low", "idx_close",
    }
    missing = required - set(basis.columns)
    if missing:
        raise ValueError(f"basis evidence missing columns: {sorted(missing)}")
    c = validate_certification(cert)
    b = basis.copy()
    b["ticker"] = _ticker(b["ticker"])
    b["date"] = _date(b["date"], "basis date")
    stable = _bool(b["panel_idx_stable_run_member"], "stable_run_member")
    b = b.loc[stable].copy()
    if b.empty:
        raise ValueError("no stable basis rows")
    b = b.merge(c, on="ticker", how="left", validate="many_to_one", indicator="_cert")
    b["observed_factor"] = pd.to_numeric(b["panel_idx_scale_factor"], errors="coerce")
    b["factor_certified"] = np.isclose(
        b["observed_factor"].to_numpy(float),
        b["expected_factor"].to_numpy(float),
        rtol=FACTOR_RTOL,
        atol=FACTOR_RTOL,
        equal_nan=False,
    )
    b["provenance_certified"] = b["price_provenance"].astype(str).eq(EXPECTED_PARENT_PROVENANCE)
    b["pre_action_certified"] = b["date"] < b["record_date"]
    b["repair_certified"] = (
        b["_cert"].eq("both")
        & b["factor_certified"]
        & b["provenance_certified"]
        & b["pre_action_certified"]
    )
    diagnostics = {
        "stable_rows": int(len(b)),
        "stable_tickers": int(b["ticker"].nunique()),
        "missing_cert_rows": int(b["_cert"].ne("both").sum()),
        "factor_fail_rows": int((~b["factor_certified"]).sum()),
        "provenance_fail_rows": int((~b["provenance_certified"]).sum()),
        "post_or_on_record_date_rows": int((~b["pre_action_certified"]).sum()),
        "certified_rows": int(b["repair_certified"].sum()),
        "certified_tickers": int(b.loc[b["repair_certified"], "ticker"].nunique()),
    }
    return b.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True), diagnostics


def build_hlc_overlay(selected: pd.DataFrame) -> pd.DataFrame:
    rows = selected.loc[selected["repair_certified"]].copy()
    if rows.empty:
        raise ValueError("no certified repair rows")
    out = rows[[
        "ticker", "date", "price_provenance", "observed_factor", "expected_factor",
        "ca_type", "ca_ratio", "record_date", "distribution_date", "source", "source_url",
        "panel_high", "panel_low", "panel_close", "idx_high", "idx_low", "idx_close",
    ]].copy()
    out = out.rename(columns={
        "price_provenance": "parent_price_provenance",
        "panel_high": "original_high", "panel_low": "original_low", "panel_close": "original_close",
        "idx_high": "remediated_high", "idx_low": "remediated_low", "idx_close": "remediated_close",
    })
    out["hlc_override_provenance"] = "IDX_PUBLIC_STOCK_SUMMARY"
    out["remediation_policy"] = "STABLE_SCALE_YAHOO_RAW_KSEI_FACTOR_PRE_RECORD_V1"
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError("overlay duplicate identity")
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def apply_hlc_overlay(panel: pd.DataFrame, overlay: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", *HLC}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")
    p = panel.copy()
    p["ticker"] = _ticker(p["ticker"])
    p["date"] = _date(p["date"], "panel date")
    if p.duplicated(["ticker", "date"]).any():
        raise ValueError("panel duplicate identity")
    o = overlay[["ticker", "date", "remediated_high", "remediated_low", "remediated_close"]].copy()
    o["ticker"] = _ticker(o["ticker"])
    o["date"] = _date(o["date"], "overlay date")
    merged = p.merge(o, on=["ticker", "date"], how="left", validate="one_to_one", indicator="_overlay")
    changed = merged["_overlay"].eq("both")
    if int(changed.sum()) != len(o):
        raise ValueError("overlay contains identities absent from panel")
    for f in HLC:
        repl = pd.to_numeric(merged[f"remediated_{f}"], errors="coerce")
        if repl.loc[changed].isna().any():
            raise ValueError(f"overlay missing remediated {f}")
        merged.loc[changed, f] = repl.loc[changed]
    merged = merged.drop(columns=["remediated_high", "remediated_low", "remediated_close", "_overlay"])
    if len(merged) != len(p):
        raise ValueError("panel row count changed")
    return merged[p.columns].sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def non_hlc_parity(parent: pd.DataFrame, corrected: pd.DataFrame) -> dict[str, Any]:
    keys = ["ticker", "date"]
    left = parent.sort_values(keys, kind="mergesort").reset_index(drop=True)
    right = corrected.sort_values(keys, kind="mergesort").reset_index(drop=True)
    if len(left) != len(right) or not left[keys].equals(right[keys]):
        return {"identity_equal": False, "non_hlc_equal": False}
    cols = [c for c in left.columns if c not in HLC]
    return {"identity_equal": True, "non_hlc_equal": left[cols].equals(right[cols]), "compared_columns": len(cols)}
