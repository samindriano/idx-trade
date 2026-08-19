"""Outcome-blind helpers for Regular-Market Value basis audits.

The audit compares the frozen research-panel ``regular_market_value`` field
against the official IDX Stock Summary ``Value`` field on exact ticker/date
overlap.  It does not modify canonical artifacts, fit/score models, or access
protected outcomes.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


VALUE_RTOL = 1e-9
VALUE_ATOL_IDR = 0.5
FEATURE_ATOL = 1e-12


def normalize_ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def normalize_date(series: pd.Series, *, label: str) -> pd.Series:
    out = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if out.isna().any():
        raise ValueError(f"{label} contains invalid dates")
    return out


def normalize_panel(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker",
        "date",
        "close",
        "volume",
        "regular_market_value",
        "price_provenance",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")
    out = frame.copy()
    out["ticker"] = normalize_ticker(out["ticker"])
    out["date"] = normalize_date(out["date"], label="panel")
    if out["ticker"].eq("").any() or out.duplicated(["ticker", "date"]).any():
        raise ValueError("panel ticker/date identity invalid")
    for column in ("close", "volume", "regular_market_value"):
        out[column] = pd.to_numeric(out[column], errors="coerce").astype(float)
    out["price_provenance"] = out["price_provenance"].astype(str).str.strip()
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def normalize_idx_value(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", "idx_close", "idx_volume", "idx_regular_market_value"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"IDX value witness missing columns: {sorted(missing)}")
    out = frame.copy()
    out["ticker"] = normalize_ticker(out["ticker"])
    out["date"] = normalize_date(out["date"], label="IDX value witness")
    if out["ticker"].eq("").any() or out.duplicated(["ticker", "date"]).any():
        raise ValueError("IDX value witness ticker/date identity invalid")
    for column in ("idx_close", "idx_volume", "idx_regular_market_value"):
        out[column] = pd.to_numeric(out[column], errors="coerce").astype(float)
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def build_value_comparison(panel: pd.DataFrame, idx: pd.DataFrame) -> pd.DataFrame:
    p = normalize_panel(panel)
    i = normalize_idx_value(idx)
    merged = p[[
        "ticker", "date", "close", "volume", "regular_market_value", "price_provenance"
    ]].merge(i, on=["ticker", "date"], how="inner", validate="one_to_one")
    if merged.empty:
        return merged

    valid = (
        np.isfinite(merged["regular_market_value"])
        & np.isfinite(merged["idx_regular_market_value"])
        & merged["regular_market_value"].gt(0.0)
        & merged["idx_regular_market_value"].gt(0.0)
    )
    merged["value_comparable"] = valid
    merged["panel_idx_value_exact"] = False
    merged.loc[valid, "panel_idx_value_exact"] = np.isclose(
        merged.loc[valid, "regular_market_value"].to_numpy(float),
        merged.loc[valid, "idx_regular_market_value"].to_numpy(float),
        rtol=VALUE_RTOL,
        atol=VALUE_ATOL_IDR,
    )
    merged["panel_idx_value_ratio"] = np.nan
    merged.loc[valid, "panel_idx_value_ratio"] = (
        merged.loc[valid, "regular_market_value"]
        / merged.loc[valid, "idx_regular_market_value"]
    )
    for pct in (0.01, 0.05, 0.10):
        name = f"panel_idx_value_within_{int(pct * 100)}pct"
        ratio = merged["panel_idx_value_ratio"]
        merged[name] = valid & ratio.between(1.0 - pct, 1.0 + pct, inclusive="both")

    panel_notional = merged["close"] * merged["volume"]
    idx_notional = merged["idx_close"] * merged["idx_volume"]
    merged["panel_value_over_close_volume"] = np.where(
        np.isfinite(panel_notional) & panel_notional.gt(0.0),
        merged["regular_market_value"] / panel_notional,
        np.nan,
    )
    merged["idx_value_over_close_volume"] = np.where(
        np.isfinite(idx_notional) & idx_notional.gt(0.0),
        merged["idx_regular_market_value"] / idx_notional,
        np.nan,
    )
    merged["panel_value_close_volume_like_1pct"] = (
        pd.to_numeric(merged["panel_value_over_close_volume"], errors="coerce")
        .between(0.99, 1.01, inclusive="both")
    )
    return merged.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def ratio_summary(frame: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    data = frame[frame.get("value_comparable", False)].copy()
    if data.empty:
        columns = ["rows", "exact_rate", "within_1pct_rate", "within_5pct_rate", "median_ratio", "p01_ratio", "p99_ratio", "close_volume_like_1pct_rate"]
        return pd.DataFrame(columns=([by] if by else []) + columns)

    def summarize(block: pd.DataFrame) -> pd.Series:
        ratio = pd.to_numeric(block["panel_idx_value_ratio"], errors="coerce").dropna()
        return pd.Series({
            "rows": int(len(block)),
            "exact_rate": float(block["panel_idx_value_exact"].mean()),
            "within_1pct_rate": float(block["panel_idx_value_within_1pct"].mean()),
            "within_5pct_rate": float(block["panel_idx_value_within_5pct"].mean()),
            "median_ratio": float(ratio.median()) if len(ratio) else np.nan,
            "p01_ratio": float(ratio.quantile(0.01)) if len(ratio) else np.nan,
            "p99_ratio": float(ratio.quantile(0.99)) if len(ratio) else np.nan,
            "close_volume_like_1pct_rate": float(block["panel_value_close_volume_like_1pct"].mean()),
        })

    if by is None:
        return summarize(data).to_frame().T
    if by not in data.columns:
        raise ValueError(f"summary grouping column missing: {by}")
    return (
        data.groupby(by, dropna=False, sort=True)
        .apply(summarize, include_groups=False)
        .reset_index()
    )


def detect_ratio_seams(frame: pd.DataFrame, *, jump_factor: float = 1.20) -> pd.DataFrame:
    if jump_factor <= 1.0:
        raise ValueError("jump_factor must exceed 1")
    data = frame[frame.get("value_comparable", False)].copy()
    if data.empty:
        return pd.DataFrame()
    data = data.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    data["prev_date"] = data.groupby("ticker", sort=False)["date"].shift(1)
    data["prev_ratio"] = data.groupby("ticker", sort=False)["panel_idx_value_ratio"].shift(1)
    data["prev_price_provenance"] = data.groupby("ticker", sort=False)["price_provenance"].shift(1)
    ratio = pd.to_numeric(data["panel_idx_value_ratio"], errors="coerce")
    prev = pd.to_numeric(data["prev_ratio"], errors="coerce")
    both = ratio.gt(0.0) & prev.gt(0.0)
    symmetric = pd.Series(np.nan, index=data.index, dtype=float)
    symmetric.loc[both] = np.maximum(
        ratio.loc[both] / prev.loc[both],
        prev.loc[both] / ratio.loc[both],
    )
    data["ratio_jump_factor"] = symmetric
    data["provenance_changed"] = (
        data["prev_price_provenance"].notna()
        & data["price_provenance"].ne(data["prev_price_provenance"])
    )
    seams = data[both & symmetric.ge(jump_factor)].copy()
    keep = [
        "ticker", "prev_date", "date", "prev_ratio", "panel_idx_value_ratio",
        "ratio_jump_factor", "prev_price_provenance", "price_provenance",
        "provenance_changed", "regular_market_value", "idx_regular_market_value",
    ]
    return seams[keep].sort_values(["ratio_jump_factor", "ticker", "date"], ascending=[False, True, True], kind="mergesort").reset_index(drop=True)


def apply_official_value_counterfactual(panel: pd.DataFrame, idx: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = normalize_panel(panel)
    i = normalize_idx_value(idx)[["ticker", "date", "idx_regular_market_value"]]
    merged = p.merge(i, on=["ticker", "date"], how="left", validate="one_to_one")
    eligible = (
        np.isfinite(merged["idx_regular_market_value"])
        & merged["idx_regular_market_value"].gt(0.0)
        & np.isfinite(merged["regular_market_value"])
        & merged["regular_market_value"].gt(0.0)
    )
    changed = eligible & ~np.isclose(
        merged["regular_market_value"].fillna(0.0).to_numpy(float),
        merged["idx_regular_market_value"].fillna(0.0).to_numpy(float),
        rtol=VALUE_RTOL,
        atol=VALUE_ATOL_IDR,
    )
    evidence = merged.loc[changed, [
        "ticker", "date", "regular_market_value", "idx_regular_market_value", "price_provenance"
    ]].rename(columns={"regular_market_value": "original_regular_market_value"}).copy()
    merged.loc[eligible, "regular_market_value"] = merged.loc[eligible, "idx_regular_market_value"]
    merged = merged.drop(columns=["idx_regular_market_value"])
    return merged[p.columns].copy(), evidence.reset_index(drop=True)


def _value_feature_state(panel: pd.DataFrame, primary_state: pd.DataFrame) -> pd.DataFrame:
    p = normalize_panel(panel)
    state = primary_state[["ticker", "date", "universe_primary_liquid"]].copy()
    state["ticker"] = normalize_ticker(state["ticker"])
    state["date"] = normalize_date(state["date"], label="primary state")
    data = p.merge(state, on=["ticker", "date"], how="left", validate="one_to_one")
    if data["universe_primary_liquid"].isna().any():
        raise ValueError("primary-state identity mismatch")
    pieces: list[pd.DataFrame] = []
    for _, block in data.groupby("ticker", sort=False):
        block = block.sort_values("date", kind="mergesort").copy()
        value = block["regular_market_value"]
        median20 = value.rolling(20, min_periods=20).median()
        ratio = value / median20
        block["log_regular_value_relative_20"] = np.log(ratio.where(np.isfinite(ratio) & ratio.gt(0.0)))
        pieces.append(block)
    result = pd.concat(pieces, ignore_index=True, sort=False).sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    primary = result["universe_primary_liquid"].astype(bool)
    result["xs_rank_log_regular_value_relative_20"] = np.nan
    ranks = result.loc[primary].groupby("date", sort=True)["log_regular_value_relative_20"].rank(method="average", pct=True)
    result.loc[ranks.index, "xs_rank_log_regular_value_relative_20"] = ranks.astype(float)
    market = (
        result.loc[primary]
        .groupby("date", sort=True)["log_regular_value_relative_20"]
        .median()
        .rename("market_median_log_regular_value_relative_20")
        .reset_index()
    )
    result = result.merge(market, on="date", how="left", validate="many_to_one")
    result["market_relative_log_regular_value_relative_20"] = np.nan
    result.loc[primary, "market_relative_log_regular_value_relative_20"] = (
        result.loc[primary, "log_regular_value_relative_20"]
        - result.loc[primary, "market_median_log_regular_value_relative_20"]
    )
    return result[[
        "ticker", "date", "universe_primary_liquid", "log_regular_value_relative_20",
        "xs_rank_log_regular_value_relative_20", "market_median_log_regular_value_relative_20",
        "market_relative_log_regular_value_relative_20",
    ]].copy()


def compare_value_feature_states(before: pd.DataFrame, after: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    keys = ["ticker", "date"]
    merged = before.merge(after, on=keys, how="outer", suffixes=("_before", "_after"), validate="one_to_one", indicator=True)
    if not merged["_merge"].eq("both").all():
        raise ValueError("value-feature identity mismatch")
    summary: dict[str, Any] = {"rows": int(len(merged))}
    eligibility_changed = merged["universe_primary_liquid_before"].astype(bool).ne(merged["universe_primary_liquid_after"].astype(bool))
    summary["primary_liquid_changed_rows"] = int(eligibility_changed.sum())
    summary["primary_liquid_changed_tickers"] = int(merged.loc[eligibility_changed, "ticker"].nunique())

    changed_any = eligibility_changed.copy()
    for name in (
        "log_regular_value_relative_20",
        "xs_rank_log_regular_value_relative_20",
        "market_median_log_regular_value_relative_20",
        "market_relative_log_regular_value_relative_20",
    ):
        left = pd.to_numeric(merged[f"{name}_before"], errors="coerce").astype(float)
        right = pd.to_numeric(merged[f"{name}_after"], errors="coerce").astype(float)
        both_nan = left.isna() & right.isna()
        equal = both_nan | np.isclose(left.fillna(0.0), right.fillna(0.0), rtol=0.0, atol=FEATURE_ATOL)
        changed = ~equal
        merged[f"{name}_changed"] = changed
        summary[f"{name}_changed_rows"] = int(changed.sum())
        summary[f"{name}_changed_tickers"] = int(merged.loc[changed, "ticker"].nunique())
        changed_any |= changed
    merged["any_value_representation_changed"] = changed_any
    summary["any_value_representation_changed_rows"] = int(changed_any.sum())
    summary["any_value_representation_changed_tickers"] = int(merged.loc[changed_any, "ticker"].nunique())
    return merged, summary


def build_value_feature_state(panel: pd.DataFrame, primary_state: pd.DataFrame) -> pd.DataFrame:
    return _value_feature_state(panel, primary_state)
