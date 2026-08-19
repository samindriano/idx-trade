"""Outcome-blind post-remediation guards before any clean model refit."""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

PRIMARY_LIQUIDITY_LOOKBACK = 60
PRIMARY_MIN_ACTIVE_OBSERVATIONS = 20
PRIMARY_VALUE_THRESHOLD_IDR = 1_000_000_000.0


def normalize_ticker(series: pd.Series) -> pd.Series:
    return series.astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()


def normalize_date(series: pd.Series, *, label: str) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if values.isna().any():
        raise ValueError(f"{label} contains invalid dates")
    return values


def open_hlc_audit(frame: pd.DataFrame, *, open_column: str) -> tuple[pd.DataFrame, dict[str, int]]:
    required = {"ticker", "date", "low", "high", open_column}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"open/HLC audit missing columns: {sorted(missing)}")
    out = frame.copy()
    out["ticker"] = normalize_ticker(out["ticker"])
    out["date"] = normalize_date(out["date"], label="open/HLC audit")
    for column in ("low", "high", open_column):
        out[column] = pd.to_numeric(out[column], errors="coerce").astype(float)
    valid_hlc = np.isfinite(out[["low", "high"]]).all(axis=1) & out["low"].gt(0.0) & out["high"].ge(out["low"])
    open_available = np.isfinite(out[open_column]) & out[open_column].gt(0.0)
    within = valid_hlc & open_available & out[open_column].ge(out["low"]) & out[open_column].le(out["high"])
    out["hlc_valid"] = valid_hlc
    out["open_available"] = open_available
    out["open_within_corrected_hlc"] = within.where(open_available, pd.NA)
    return out, {
        "rows": int(len(out)),
        "valid_hlc_rows": int(valid_hlc.sum()),
        "open_available_rows": int(open_available.sum()),
        "open_within_rows": int(within.sum()),
        "open_range_violation_rows": int((open_available & ~within).sum()),
        "invalid_hlc_rows": int((~valid_hlc).sum()),
    }


def volume_value_exact_comparison(panel: pd.DataFrame, official: pd.DataFrame) -> pd.DataFrame:
    required_panel = {"ticker", "date", "volume", "regular_market_value"}
    required_official = {"ticker", "date", "idx_volume", "idx_value"}
    if not required_panel.issubset(panel.columns):
        raise ValueError(f"panel missing: {sorted(required_panel - set(panel.columns))}")
    if not required_official.issubset(official.columns):
        raise ValueError(f"official missing: {sorted(required_official - set(official.columns))}")
    pcols = ["ticker", "date", "volume", "regular_market_value"]
    if "price_provenance" in panel.columns:
        pcols.append("price_provenance")
    p = panel[pcols].copy()
    p["ticker"] = normalize_ticker(p["ticker"])
    p["date"] = normalize_date(p["date"], label="panel")
    p = p.rename(columns={"volume": "panel_volume", "regular_market_value": "panel_value"})
    o = official[list(required_official)].copy()
    o["ticker"] = normalize_ticker(o["ticker"])
    o["date"] = normalize_date(o["date"], label="official")
    merged = p.merge(o, on=["ticker", "date"], how="left", validate="one_to_one", indicator="official_support")
    for column in ("panel_volume", "panel_value", "idx_volume", "idx_value"):
        merged[column] = pd.to_numeric(merged[column], errors="coerce").astype(float)
    merged["volume_same_basis"] = merged["panel_volume"].eq(merged["idx_volume"])
    merged["value_same_basis"] = merged["panel_value"].eq(merged["idx_value"])
    merged["volume_ratio"] = merged["panel_volume"] / merged["idx_volume"]
    merged["value_ratio"] = merged["panel_value"] / merged["idx_value"]
    merged["year"] = merged["date"].dt.year.astype(int)
    return merged


def denominator_summary(rows: pd.DataFrame) -> dict[str, Any]:
    support = rows["official_support"].eq("both")
    volume_valid = support & np.isfinite(rows["idx_volume"])
    value_valid = support & np.isfinite(rows["idx_value"])
    return {
        "panel_rows": int(len(rows)),
        "official_identity_overlap_rows": int(support.sum()),
        "official_identity_overlap_rate": float(support.mean()) if len(rows) else 0.0,
        "official_volume_supported_rows": int(volume_valid.sum()),
        "official_value_supported_rows": int(value_valid.sum()),
        "volume_same_basis_rows": int((volume_valid & rows["volume_same_basis"]).sum()),
        "value_same_basis_rows": int((value_valid & rows["value_same_basis"]).sum()),
        "volume_mismatch_rows": int((volume_valid & ~rows["volume_same_basis"]).sum()),
        "value_mismatch_rows": int((value_valid & ~rows["value_same_basis"]).sum()),
    }


def year_provenance_summary(rows: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["year"] + (["price_provenance"] if "price_provenance" in rows.columns else [])
    records: list[dict[str, Any]] = []
    for keys, block in rows.groupby(group_cols, sort=True, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = {column: value for column, value in zip(group_cols, keys, strict=True)}
        record.update(denominator_summary(block))
        records.append(record)
    return pd.DataFrame(records)


def provenance_seams(rows: pd.DataFrame) -> pd.DataFrame:
    if "price_provenance" not in rows.columns:
        return pd.DataFrame(columns=["ticker", "date", "previous_date", "previous_provenance", "price_provenance", "volume_same_basis", "value_same_basis"])
    records: list[dict[str, Any]] = []
    for ticker, block in rows.sort_values(["ticker", "date"], kind="mergesort").groupby("ticker", sort=True):
        block = block.reset_index(drop=True)
        previous = block["price_provenance"].shift(1)
        seam = previous.notna() & block["price_provenance"].ne(previous)
        for idx in block.index[seam]:
            records.append({
                "ticker": ticker,
                "date": block.loc[idx, "date"],
                "previous_date": block.loc[idx - 1, "date"],
                "previous_provenance": previous.loc[idx],
                "price_provenance": block.loc[idx, "price_provenance"],
                "volume_same_basis": bool(block.loc[idx, "volume_same_basis"]),
                "value_same_basis": bool(block.loc[idx, "value_same_basis"]),
            })
    return pd.DataFrame(records)


def liquidity_source_features(panel: pd.DataFrame, official_sessions: Iterable[object]) -> pd.DataFrame:
    required = {"ticker", "date", "volume", "regular_market_value"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"liquidity feature panel missing columns: {sorted(missing)}")
    sessions = pd.DatetimeIndex(pd.to_datetime(list(official_sessions), errors="coerce")).tz_localize(None).normalize().dropna().unique().sort_values()
    index_by_date = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    data = panel[list(required)].copy()
    data["ticker"] = normalize_ticker(data["ticker"])
    data["date"] = normalize_date(data["date"], label="liquidity feature panel")
    data["volume"] = pd.to_numeric(data["volume"], errors="coerce").astype(float)
    data["regular_market_value"] = pd.to_numeric(data["regular_market_value"], errors="coerce").astype(float)
    data["session_index_zero"] = data["date"].map(index_by_date)
    if data["session_index_zero"].isna().any():
        raise ValueError("panel contains dates outside official sessions")
    pieces: list[pd.DataFrame] = []
    for ticker, block in data.groupby("ticker", sort=False):
        frame = block.sort_values("date", kind="mergesort").copy()
        med_vol = frame["volume"].rolling(20, min_periods=20).median()
        frame["relative_volume_20"] = frame["volume"] / med_vol
        med_val = frame["regular_market_value"].rolling(20, min_periods=20).median()
        ratio = frame["regular_market_value"] / med_val
        frame["log_regular_value_relative_20"] = np.log(ratio.where(ratio > 0.0))
        idx = frame["session_index_zero"].to_numpy(dtype=int)
        values = frame["regular_market_value"].to_numpy(dtype=float)
        active_counts: list[int] = []
        medians: list[float] = []
        left = 0
        for right, current in enumerate(idx):
            minimum = current - (PRIMARY_LIQUIDITY_LOOKBACK - 1)
            while left <= right and idx[left] < minimum:
                left += 1
            finite = values[left : right + 1]
            finite = finite[np.isfinite(finite)]
            active_counts.append(int(len(finite)))
            medians.append(float(np.median(finite)) if len(finite) else np.nan)
        frame["universe_primary_liquid"] = (np.asarray(active_counts) >= PRIMARY_MIN_ACTIVE_OBSERVATIONS) & (np.asarray(medians) >= PRIMARY_VALUE_THRESHOLD_IDR)
        pieces.append(frame[["ticker", "date", "relative_volume_20", "log_regular_value_relative_20", "universe_primary_liquid"]])
    return pd.concat(pieces, ignore_index=True).sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def apply_official_volume_value(panel: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    out["ticker"] = normalize_ticker(out["ticker"])
    out["date"] = normalize_date(out["date"], label="counterfactual panel")
    repl = comparison.loc[comparison["official_support"].eq("both"), ["ticker", "date", "idx_volume", "idx_value"]].copy()
    merged = out.merge(repl, on=["ticker", "date"], how="left", validate="one_to_one")
    supported = merged["idx_volume"].notna() & merged["idx_value"].notna()
    merged.loc[supported, "volume"] = merged.loc[supported, "idx_volume"]
    merged.loc[supported, "regular_market_value"] = merged.loc[supported, "idx_value"]
    return merged.drop(columns=["idx_volume", "idx_value"])[out.columns]


def liquidity_feature_delta(original: pd.DataFrame, counterfactual: pd.DataFrame) -> dict[str, int]:
    merged = original.merge(counterfactual, on=["ticker", "date"], suffixes=("_original", "_counterfactual"), validate="one_to_one")
    result: dict[str, int] = {}
    for column in ("relative_volume_20", "log_regular_value_relative_20"):
        a = pd.to_numeric(merged[f"{column}_original"], errors="coerce").to_numpy(float)
        b = pd.to_numeric(merged[f"{column}_counterfactual"], errors="coerce").to_numpy(float)
        result[f"{column}_changed_rows"] = int((~np.isclose(a, b, rtol=0.0, atol=1e-12, equal_nan=True)).sum())
    result["universe_primary_liquid_changed_rows"] = int((merged["universe_primary_liquid_original"].astype(bool) != merged["universe_primary_liquid_counterfactual"].astype(bool)).sum())
    return result
