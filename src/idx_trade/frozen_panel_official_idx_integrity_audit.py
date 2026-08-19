"""Outcome-blind helpers for a frozen-panel vs official-IDX integrity audit."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


VOLUME_ATOL = 0.5
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
        "high",
        "low",
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
    for name in ("high", "low", "close", "volume", "regular_market_value"):
        out[name] = pd.to_numeric(out[name], errors="coerce").astype(float)
    out["price_provenance"] = out["price_provenance"].astype(str).str.strip()
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def normalize_idx_witness(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker",
        "date",
        "idx_high",
        "idx_low",
        "idx_close",
        "idx_volume",
        "idx_frequency",
        "idx_value",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"IDX witness missing columns: {sorted(missing)}")
    out = frame.copy()
    out["ticker"] = normalize_ticker(out["ticker"])
    out["date"] = normalize_date(out["date"], label="IDX witness")
    if out["ticker"].eq("").any() or out.duplicated(["ticker", "date"]).any():
        raise ValueError("IDX witness ticker/date identity invalid")
    for name in (
        "idx_high",
        "idx_low",
        "idx_close",
        "idx_volume",
        "idx_frequency",
        "idx_value",
    ):
        out[name] = pd.to_numeric(out[name], errors="coerce").astype(float)
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def official_active_valid_hlc_mask(frame: pd.DataFrame) -> pd.Series:
    hi = pd.to_numeric(frame["idx_high"], errors="coerce").astype(float)
    lo = pd.to_numeric(frame["idx_low"], errors="coerce").astype(float)
    cl = pd.to_numeric(frame["idx_close"], errors="coerce").astype(float)
    vol = pd.to_numeric(frame["idx_volume"], errors="coerce").astype(float)
    freq = pd.to_numeric(frame["idx_frequency"], errors="coerce").astype(float)
    finite = np.isfinite(hi) & np.isfinite(lo) & np.isfinite(cl) & np.isfinite(vol) & np.isfinite(freq)
    return (
        finite
        & hi.gt(0.0)
        & lo.gt(0.0)
        & cl.gt(0.0)
        & vol.gt(0.0)
        & freq.gt(0.0)
        & hi.ge(pd.concat([lo, cl], axis=1).max(axis=1))
        & lo.le(pd.concat([hi, cl], axis=1).min(axis=1))
    )


def build_volume_comparison(panel: pd.DataFrame, witness: pd.DataFrame) -> pd.DataFrame:
    p = normalize_panel(panel)
    w = normalize_idx_witness(witness)
    merged = p[["ticker", "date", "volume", "price_provenance"]].merge(
        w[[
            "ticker",
            "date",
            "idx_high",
            "idx_low",
            "idx_close",
            "idx_volume",
            "idx_frequency",
            "idx_value",
        ]],
        on=["ticker", "date"],
        how="inner",
        validate="one_to_one",
    )
    if merged.empty:
        return merged
    panel_volume = pd.to_numeric(merged["volume"], errors="coerce").astype(float)
    idx_volume = pd.to_numeric(merged["idx_volume"], errors="coerce").astype(float)
    comparable = np.isfinite(panel_volume) & np.isfinite(idx_volume) & panel_volume.ge(0.0) & idx_volume.ge(0.0)
    merged["volume_comparable"] = comparable
    merged["panel_idx_volume_exact"] = False
    merged.loc[comparable, "panel_idx_volume_exact"] = np.isclose(
        panel_volume.loc[comparable].to_numpy(float),
        idx_volume.loc[comparable].to_numpy(float),
        rtol=0.0,
        atol=VOLUME_ATOL,
    )
    ratio_ok = comparable & panel_volume.gt(0.0) & idx_volume.gt(0.0)
    merged["panel_idx_volume_ratio"] = np.nan
    merged.loc[ratio_ok, "panel_idx_volume_ratio"] = panel_volume.loc[ratio_ok] / idx_volume.loc[ratio_ok]
    ratio = pd.to_numeric(merged["panel_idx_volume_ratio"], errors="coerce")
    for pct in (0.01, 0.05, 0.10):
        merged[f"panel_idx_volume_within_{int(pct * 100)}pct"] = ratio.between(
            1.0 - pct, 1.0 + pct, inclusive="both"
        )
    merged["official_active_valid_hlc"] = official_active_valid_hlc_mask(merged)
    return merged.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def detect_volume_ratio_seams(frame: pd.DataFrame, *, jump_factor: float = 1.20) -> pd.DataFrame:
    if jump_factor <= 1.0:
        raise ValueError("jump_factor must exceed 1")
    data = frame.copy().sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    if data.empty or "panel_idx_volume_ratio" not in data.columns:
        return pd.DataFrame()
    data["prev_date"] = data.groupby("ticker", sort=False)["date"].shift(1)
    data["prev_ratio"] = data.groupby("ticker", sort=False)["panel_idx_volume_ratio"].shift(1)
    data["prev_price_provenance"] = data.groupby("ticker", sort=False)["price_provenance"].shift(1)
    ratio = pd.to_numeric(data["panel_idx_volume_ratio"], errors="coerce")
    prev = pd.to_numeric(data["prev_ratio"], errors="coerce")
    valid = ratio.gt(0.0) & prev.gt(0.0)
    symmetric = pd.Series(np.nan, index=data.index, dtype=float)
    symmetric.loc[valid] = np.maximum(ratio.loc[valid] / prev.loc[valid], prev.loc[valid] / ratio.loc[valid])
    data["ratio_jump_factor"] = symmetric
    data["provenance_changed"] = (
        data["prev_price_provenance"].notna()
        & data["price_provenance"].ne(data["prev_price_provenance"])
    )
    keep = data[valid & symmetric.ge(jump_factor)].copy()
    cols = [
        "ticker",
        "prev_date",
        "date",
        "prev_ratio",
        "panel_idx_volume_ratio",
        "ratio_jump_factor",
        "prev_price_provenance",
        "price_provenance",
        "provenance_changed",
        "volume",
        "idx_volume",
    ]
    return keep[cols].sort_values(
        ["ratio_jump_factor", "ticker", "date"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def apply_official_volume_counterfactual(
    panel: pd.DataFrame, witness: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = normalize_panel(panel)
    w = normalize_idx_witness(witness)[["ticker", "date", "idx_volume"]]
    merged = p.merge(w, on=["ticker", "date"], how="left", validate="one_to_one")
    idx_volume = pd.to_numeric(merged["idx_volume"], errors="coerce").astype(float)
    panel_volume = pd.to_numeric(merged["volume"], errors="coerce").astype(float)
    eligible = np.isfinite(idx_volume) & idx_volume.ge(0.0) & np.isfinite(panel_volume) & panel_volume.ge(0.0)
    changed = eligible & ~np.isclose(panel_volume.to_numpy(float), idx_volume.fillna(-1.0).to_numpy(float), rtol=0.0, atol=VOLUME_ATOL)
    evidence = merged.loc[changed, [
        "ticker", "date", "volume", "idx_volume", "price_provenance"
    ]].rename(columns={"volume": "original_volume"}).copy()
    merged.loc[eligible, "volume"] = idx_volume.loc[eligible]
    merged = merged.drop(columns=["idx_volume"])
    return merged[p.columns].copy(), evidence.reset_index(drop=True)


def build_volume_feature_state(panel: pd.DataFrame, primary_state: pd.DataFrame) -> pd.DataFrame:
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
        volume = pd.to_numeric(block["volume"], errors="coerce").astype(float)
        median20 = volume.rolling(20, min_periods=20).median()
        rel = volume / median20
        block["relative_volume_20"] = rel.where(np.isfinite(rel) & median20.ne(0.0))
        pieces.append(block)
    result = pd.concat(pieces, ignore_index=True, sort=False).sort_values(
        ["date", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
    primary = result["universe_primary_liquid"].astype(bool)
    result["xs_rank_relative_volume_20"] = np.nan
    ranks = result.loc[primary].groupby("date", sort=True)["relative_volume_20"].rank(
        method="average", pct=True
    )
    result.loc[ranks.index, "xs_rank_relative_volume_20"] = ranks.astype(float)
    market = (
        result.loc[primary]
        .groupby("date", sort=True)["relative_volume_20"]
        .median()
        .rename("market_median_relative_volume_20")
        .reset_index()
    )
    result = result.merge(market, on="date", how="left", validate="many_to_one")
    result["market_relative_relative_volume_20"] = np.nan
    result.loc[primary, "market_relative_relative_volume_20"] = (
        result.loc[primary, "relative_volume_20"]
        - result.loc[primary, "market_median_relative_volume_20"]
    )
    return result[[
        "ticker",
        "date",
        "universe_primary_liquid",
        "relative_volume_20",
        "xs_rank_relative_volume_20",
        "market_median_relative_volume_20",
        "market_relative_relative_volume_20",
    ]].copy()


def compare_volume_feature_states(before: pd.DataFrame, after: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    merged = before.merge(
        after,
        on=["ticker", "date"],
        how="outer",
        suffixes=("_before", "_after"),
        validate="one_to_one",
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise ValueError("volume-feature identity mismatch")
    summary: dict[str, Any] = {"rows": int(len(merged))}
    changed_any = pd.Series(False, index=merged.index, dtype=bool)
    for name in (
        "relative_volume_20",
        "xs_rank_relative_volume_20",
        "market_median_relative_volume_20",
        "market_relative_relative_volume_20",
    ):
        left = pd.to_numeric(merged[f"{name}_before"], errors="coerce").astype(float)
        right = pd.to_numeric(merged[f"{name}_after"], errors="coerce").astype(float)
        equal = (left.isna() & right.isna()) | np.isclose(
            left.fillna(0.0), right.fillna(0.0), rtol=0.0, atol=FEATURE_ATOL
        )
        changed = ~equal
        merged[f"{name}_changed"] = changed
        summary[f"{name}_changed_rows"] = int(changed.sum())
        summary[f"{name}_changed_tickers"] = int(merged.loc[changed, "ticker"].nunique())
        changed_any |= changed
    merged["any_volume_representation_changed"] = changed_any
    summary["any_volume_representation_changed_rows"] = int(changed_any.sum())
    summary["any_volume_representation_changed_tickers"] = int(
        merged.loc[changed_any, "ticker"].nunique()
    )
    return merged, summary


def candidate_official_active_gaps(
    panel: pd.DataFrame,
    witness: pd.DataFrame,
    official_sessions: pd.DatetimeIndex,
) -> pd.DataFrame:
    p = normalize_panel(panel)
    w = normalize_idx_witness(witness)
    sessions = pd.DatetimeIndex(pd.to_datetime(official_sessions, errors="coerce")).tz_localize(None).normalize().dropna().unique().sort_values()
    session_set = set(pd.Timestamp(value) for value in sessions)
    tickers = set(p["ticker"].unique())
    active = w[
        w["ticker"].isin(tickers)
        & w["date"].isin(session_set)
        & official_active_valid_hlc_mask(w)
    ].copy()
    if active.empty:
        return pd.DataFrame()
    bounds = p.groupby("ticker", sort=True)["date"].agg(panel_first_date="min", panel_last_date="max").reset_index()
    keys = p[["ticker", "date"]].assign(panel_present=True)
    active = active.merge(bounds, on="ticker", how="inner", validate="many_to_one")
    active = active.merge(keys, on=["ticker", "date"], how="left", validate="one_to_one")
    missing = active[active["panel_present"].isna()].copy()
    if missing.empty:
        return missing
    missing["gap_class"] = np.select(
        [
            missing["date"].lt(missing["panel_first_date"]),
            missing["date"].gt(missing["panel_last_date"]),
        ],
        ["LEADING_OFFICIAL_ACTIVE_HLC_MISSING", "TRAILING_OFFICIAL_ACTIVE_HLC_MISSING"],
        default="INTERIOR_OFFICIAL_ACTIVE_HLC_MISSING",
    )
    index_by_date = {pd.Timestamp(day): i for i, day in enumerate(sessions)}
    missing["session_index"] = missing["date"].map(index_by_date).astype("Int64")
    return missing[[
        "ticker",
        "date",
        "session_index",
        "gap_class",
        "panel_first_date",
        "panel_last_date",
        "idx_high",
        "idx_low",
        "idx_close",
        "idx_volume",
        "idx_frequency",
        "idx_value",
    ]].sort_values(["gap_class", "ticker", "date"], kind="mergesort").reset_index(drop=True)


def calendar_witness_diagnostics(
    witness: pd.DataFrame,
    official_sessions: pd.DatetimeIndex,
) -> dict[str, Any]:
    w = normalize_idx_witness(witness)
    sessions = pd.DatetimeIndex(pd.to_datetime(official_sessions, errors="coerce")).tz_localize(None).normalize().dropna().unique().sort_values()
    if not len(sessions):
        raise ValueError("official sessions empty")
    start, end = pd.Timestamp(sessions[0]), pd.Timestamp(sessions[-1])
    active = w[official_active_valid_hlc_mask(w)].copy()
    active_dates = set(pd.Timestamp(day) for day in active.loc[active["date"].between(start, end), "date"].unique())
    session_set = set(pd.Timestamp(day) for day in sessions)
    omitted = sorted(active_dates - session_set)
    no_active = sorted(session_set - active_dates)
    witness_dates = set(pd.Timestamp(day) for day in w.loc[w["date"].between(start, end), "date"].unique())
    no_witness = sorted(session_set - witness_dates)
    return {
        "active_witness_dates_inside_window": int(len(active_dates)),
        "calendar_sessions": int(len(sessions)),
        "active_witness_dates_missing_from_calendar": [d.date().isoformat() for d in omitted],
        "calendar_sessions_without_any_official_active_valid_hlc": [d.date().isoformat() for d in no_active],
        "calendar_sessions_without_any_stock_summary_witness": [d.date().isoformat() for d in no_witness],
    }
