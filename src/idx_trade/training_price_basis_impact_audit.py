"""Offline helpers for frozen-panel price-basis training impact audits.

This module is deliberately provider-free and outcome-free. It can compare the
frozen research panel with an official daily witness, isolate stable
multiplicative H/L/C basis regimes, create a counterfactual H/L/C-only panel,
and compare downstream feature tables without fitting or scoring models.

The V2 feature reconstruction below mirrors the frozen Clean-V2
HGB_XS_MARKET representation used by Ranking V2. It is kept local to this
forensic lane because the V4-X1 scientific branch does not contain the legacy
V2 feature module. Runtime parity against the immutable V2 prepared cache is a
mandatory guard before any V2 impact verdict is emitted.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd


HLC_FIELDS = ("high", "low", "close")
MIN_STABLE_SCALE_RUN = 3
SCALE_RTOL = 1e-9
FEATURE_ATOL = 1e-12

PRIMARY_LIQUIDITY_LOOKBACK = 60
PRIMARY_MIN_ACTIVE_OBSERVATIONS = 20
PRIMARY_VALUE_THRESHOLD_IDR = 1_000_000_000.0

V2_XS_SOURCE_FEATURES = (
    "close_return_5",
    "close_return_20",
    "atr14_over_close",
    "close_position_20",
    "distance_high_20_atr",
    "distance_low_20_atr",
    "distance_high_60_atr",
    "distance_low_60_atr",
    "relative_volume_20",
    "log_regular_value_relative_20",
)
V2_XS_FEATURE_COLUMNS = tuple(f"xs_rank_{name}" for name in V2_XS_SOURCE_FEATURES)
V2_MARKET_CONTEXT_COLUMNS = (
    "market_primary_liquid_count",
    "market_breadth_return_5_positive",
    "market_breadth_return_20_positive",
    "market_median_close_return_5",
    "market_median_close_return_20",
    "market_median_atr14_over_close",
    "market_median_close_position_20",
    "market_median_relative_volume_20",
    "market_median_log_regular_value_relative_20",
)
V2_MARKET_RELATIVE_COLUMNS = (
    "market_relative_close_return_5",
    "market_relative_close_return_20",
    "market_relative_atr14_over_close",
    "market_relative_close_position_20",
    "market_relative_relative_volume_20",
    "market_relative_log_regular_value_relative_20",
)
V2_FULL_FEATURE_COLUMNS = (
    *V2_XS_FEATURE_COLUMNS,
    *V2_MARKET_CONTEXT_COLUMNS,
    *V2_MARKET_RELATIVE_COLUMNS,
)
_V2_RELATIVE_SOURCE_TO_MARKET = {
    "close_return_5": ("market_median_close_return_5", "market_relative_close_return_5"),
    "close_return_20": ("market_median_close_return_20", "market_relative_close_return_20"),
    "atr14_over_close": ("market_median_atr14_over_close", "market_relative_atr14_over_close"),
    "close_position_20": ("market_median_close_position_20", "market_relative_close_position_20"),
    "relative_volume_20": ("market_median_relative_volume_20", "market_relative_relative_volume_20"),
    "log_regular_value_relative_20": (
        "market_median_log_regular_value_relative_20",
        "market_relative_log_regular_value_relative_20",
    ),
}


def normalize_ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def normalize_date(series: pd.Series, *, label: str) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if values.isna().any():
        raise ValueError(f"{label} contains invalid dates")
    return values


def normalize_panel(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", "high", "low", "close", "volume", "regular_market_value"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")
    out = frame.copy()
    out["ticker"] = normalize_ticker(out["ticker"])
    out["date"] = normalize_date(out["date"], label="panel")
    if out["ticker"].eq("").any() or out.duplicated(["ticker", "date"]).any():
        raise ValueError("panel ticker/date identity must be non-empty and unique")
    for column in ("high", "low", "close", "volume", "regular_market_value"):
        out[column] = pd.to_numeric(out[column], errors="coerce").astype(float)
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def add_hlc_basis_comparison(
    frame: pd.DataFrame,
    *,
    left_prefix: str,
    right_prefix: str,
    result_prefix: str,
    rtol: float = SCALE_RTOL,
) -> pd.DataFrame:
    """Add exact-HLC flags and a stable row-level multiplicative factor.

    A row-level scale factor is present only when H/L/C are positive and the
    three right/left ratios agree within the frozen relative tolerance. A factor
    approximately equal to 1 is treated as exact/same-basis, not a scale event.
    """
    out = frame.copy()
    ratio_columns: list[str] = []
    exact_flags: list[str] = []
    for field in HLC_FIELDS:
        left = pd.to_numeric(out[f"{left_prefix}{field}"], errors="coerce").astype(float)
        right = pd.to_numeric(out[f"{right_prefix}{field}"], errors="coerce").astype(float)
        exact = left.notna() & right.notna() & left.eq(right)
        exact_name = f"{result_prefix}_{field}_exact"
        out[exact_name] = exact
        exact_flags.append(exact_name)
        ratio = pd.Series(np.nan, index=out.index, dtype=float)
        valid = np.isfinite(left) & np.isfinite(right) & left.gt(0.0) & right.gt(0.0)
        ratio.loc[valid] = right.loc[valid] / left.loc[valid]
        ratio_name = f"{result_prefix}_{field}_ratio"
        out[ratio_name] = ratio
        ratio_columns.append(ratio_name)
    out[f"{result_prefix}_hlc_exact"] = out[exact_flags].all(axis=1)

    ratios = out[ratio_columns].to_numpy(dtype=float)
    factors = np.full(len(out), np.nan, dtype=float)
    for idx, row in enumerate(ratios):
        if not np.isfinite(row).all():
            continue
        median = float(np.median(row))
        if median <= 0.0 or np.isclose(median, 1.0, rtol=rtol, atol=rtol):
            continue
        if np.all(np.isclose(row, median, rtol=rtol, atol=rtol)):
            factors[idx] = median
    out[f"{result_prefix}_scale_factor"] = factors
    out[f"{result_prefix}_row_scale_consistent"] = np.isfinite(factors)
    return out


def mark_stable_scale_runs(
    frame: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    factor_column: str,
    prefix: str,
    min_run: int = MIN_STABLE_SCALE_RUN,
) -> pd.DataFrame:
    """Mark same-factor runs across consecutive official exchange sessions."""
    if min_run < 2:
        raise ValueError("min_run must be at least 2")
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(list(official_sessions), errors="coerce"))
        .tz_localize(None)
        .normalize()
        .dropna()
        .unique()
        .sort_values()
    )
    if not len(sessions):
        raise ValueError("official_sessions must not be empty")
    index_by_date = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}

    out = frame.copy()
    out["ticker"] = normalize_ticker(out["ticker"])
    out["date"] = normalize_date(out["date"], label="scale-run frame")
    out["_session_index"] = out["date"].map(index_by_date)
    factor = pd.to_numeric(out[factor_column], errors="coerce").astype(float)
    out[f"{prefix}_factor_key"] = factor.round(10)
    out[f"{prefix}_run_id"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
    out[f"{prefix}_run_length"] = 0
    out[f"{prefix}_stable_run_member"] = False

    next_run_id = 0
    for _, positions in out.groupby("ticker", sort=True).groups.items():
        block = out.loc[list(positions)].sort_values("date", kind="mergesort")
        valid = block[f"{prefix}_factor_key"].notna() & block["_session_index"].notna()
        block = block.loc[valid]
        if block.empty:
            continue
        current_indices: list[int] = []
        previous_session: int | None = None
        previous_factor: float | None = None

        def flush() -> None:
            nonlocal next_run_id, current_indices
            if not current_indices:
                return
            next_run_id += 1
            run_len = len(current_indices)
            out.loc[current_indices, f"{prefix}_run_id"] = next_run_id
            out.loc[current_indices, f"{prefix}_run_length"] = run_len
            if run_len >= min_run:
                out.loc[current_indices, f"{prefix}_stable_run_member"] = True
            current_indices = []

        for idx, row in block.iterrows():
            session = int(row["_session_index"])
            factor_key = float(row[f"{prefix}_factor_key"])
            starts_new = (
                previous_session is None
                or previous_factor is None
                or session != previous_session + 1
                or factor_key != previous_factor
            )
            if starts_new:
                flush()
            current_indices.append(int(idx))
            previous_session = session
            previous_factor = factor_key
        flush()

    return out.drop(columns=["_session_index"])


def apply_hlc_counterfactual(
    panel: pd.DataFrame,
    comparison: pd.DataFrame,
    *,
    member_column: str,
    official_prefix: str = "idx_",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replace H/L/C only on pre-classified stable-scale rows."""
    base = normalize_panel(panel)
    required = {"ticker", "date", member_column, *(f"{official_prefix}{f}" for f in HLC_FIELDS)}
    missing = required - set(comparison.columns)
    if missing:
        raise ValueError(f"comparison missing columns: {sorted(missing)}")
    evidence = comparison[["ticker", "date", member_column, *(f"{official_prefix}{f}" for f in HLC_FIELDS)]].copy()
    evidence["ticker"] = normalize_ticker(evidence["ticker"])
    evidence["date"] = normalize_date(evidence["date"], label="comparison")
    evidence = evidence[evidence[member_column].fillna(False).astype(bool)].copy()
    if evidence.duplicated(["ticker", "date"]).any():
        raise ValueError("counterfactual evidence has duplicate ticker/date")

    out = base.merge(evidence, on=["ticker", "date"], how="left", validate="one_to_one")
    changed = out[member_column].fillna(False).astype(bool)
    for field in HLC_FIELDS:
        replacement = pd.to_numeric(out[f"{official_prefix}{field}"], errors="coerce").astype(float)
        if replacement[changed].isna().any():
            raise ValueError(f"counterfactual {field} replacement is missing")
        out.loc[changed, field] = replacement.loc[changed]
    evidence_out = out.loc[changed, ["ticker", "date", *HLC_FIELDS]].copy()
    drop = [member_column, *(f"{official_prefix}{f}" for f in HLC_FIELDS)]
    out = out.drop(columns=drop)
    return out, evidence_out


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.astype(float) / denominator.astype(float)
    return result.where(np.isfinite(result) & denominator.ne(0))


def _add_v2_causal_atr(panel: pd.DataFrame) -> pd.DataFrame:
    data = normalize_panel(panel)
    numeric = data[["high", "low", "close", "volume"]]
    valid = (
        np.isfinite(numeric).all(axis=1)
        & numeric[["high", "low", "close"]].gt(0.0).all(axis=1)
        & numeric["volume"].gt(0.0)
        & numeric["high"].ge(numeric[["low", "close"]].max(axis=1))
        & numeric["low"].le(numeric[["high", "close"]].min(axis=1))
    )
    if not valid.all():
        raise ValueError("V2 reconstruction panel contains invalid HLCV")
    pieces: list[pd.DataFrame] = []
    for _, group in data.groupby("ticker", sort=False):
        frame = group.sort_values("date", kind="mergesort").copy()
        previous_close = frame["close"].shift(1)
        true_range = pd.concat(
            [
                frame["high"] - frame["low"],
                (frame["high"] - previous_close).abs(),
                (frame["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1, skipna=True)
        frame["atr14"] = true_range.rolling(window=14, min_periods=14).mean()
        pieces.append(frame)
    return pd.concat(pieces, ignore_index=True, sort=False)


def build_v2_hgb_xs_market_features(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Reconstruct the frozen Clean-V2 HGB_XS_MARKET feature representation."""
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(list(official_sessions), errors="coerce"))
        .tz_localize(None)
        .normalize()
        .dropna()
        .unique()
        .sort_values()
    )
    if not len(sessions):
        raise ValueError("official_sessions must not be empty")
    index_by_date = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    data = _add_v2_causal_atr(panel)
    data["session_index_zero"] = data["date"].map(index_by_date)
    if data["session_index_zero"].isna().any():
        raise ValueError("V2 panel contains dates outside official calendar")
    data["session_index_zero"] = data["session_index_zero"].astype(int)

    pieces: list[pd.DataFrame] = []
    for _, group in data.groupby("ticker", sort=False):
        frame = group.sort_values("date", kind="mergesort").copy()
        close = frame["close"]
        high = frame["high"]
        low = frame["low"]
        volume = frame["volume"]
        value = frame["regular_market_value"]
        atr = frame["atr14"]

        frame["close_return_5"] = close / close.shift(5) - 1.0
        frame["close_return_20"] = close / close.shift(20) - 1.0
        frame["atr14_over_close"] = _safe_divide(atr, close)
        high20 = high.rolling(20, min_periods=20).max()
        low20 = low.rolling(20, min_periods=20).min()
        high60 = high.rolling(60, min_periods=60).max()
        low60 = low.rolling(60, min_periods=60).min()
        frame["close_position_20"] = _safe_divide(close - low20, high20 - low20)
        frame["distance_high_20_atr"] = _safe_divide(high20 - close, atr)
        frame["distance_low_20_atr"] = _safe_divide(close - low20, atr)
        frame["distance_high_60_atr"] = _safe_divide(high60 - close, atr)
        frame["distance_low_60_atr"] = _safe_divide(close - low60, atr)
        median_volume20 = volume.rolling(20, min_periods=20).median()
        frame["relative_volume_20"] = _safe_divide(volume, median_volume20)
        median_value20 = value.rolling(20, min_periods=20).median()
        value_ratio = _safe_divide(value, median_value20)
        frame["log_regular_value_relative_20"] = np.log(value_ratio.where(value_ratio > 0.0))

        indices = frame["session_index_zero"].to_numpy(dtype=int)
        values = frame["regular_market_value"].to_numpy(dtype=float)
        counts: list[int] = []
        medians: list[float] = []
        left = 0
        for right, current in enumerate(indices):
            minimum = int(current) - (PRIMARY_LIQUIDITY_LOOKBACK - 1)
            while left <= right and indices[left] < minimum:
                left += 1
            window = values[left : right + 1]
            finite = window[np.isfinite(window)]
            counts.append(int(len(finite)))
            medians.append(float(np.median(finite)) if len(finite) else np.nan)
        frame["liquidity_active_observations_60"] = counts
        frame["median_regular_value_60"] = medians
        frame["universe_history_qualified"] = (
            frame["liquidity_active_observations_60"] >= PRIMARY_MIN_ACTIVE_OBSERVATIONS
        ) & frame["median_regular_value_60"].notna()
        frame["universe_primary_liquid"] = frame["universe_history_qualified"] & (
            frame["median_regular_value_60"] >= PRIMARY_VALUE_THRESHOLD_IDR
        )
        pieces.append(frame)

    result = pd.concat(pieces, ignore_index=True, sort=False).sort_values(
        ["date", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
    primary_mask = result["universe_primary_liquid"].astype(bool)
    primary = result.loc[primary_mask].copy()
    if primary.empty:
        raise ValueError("V2 reconstruction has no primary-liquid rows")

    for source, output in zip(V2_XS_SOURCE_FEATURES, V2_XS_FEATURE_COLUMNS, strict=True):
        result[output] = np.nan
        ranks = primary.groupby("date", sort=True)[source].rank(method="average", pct=True)
        result.loc[ranks.index, output] = ranks.astype(float)

    context_rows: list[dict[str, object]] = []
    for date, block in primary.groupby("date", sort=True):
        def finite(name: str) -> pd.Series:
            values = pd.to_numeric(block[name], errors="coerce").astype(float)
            return values.where(np.isfinite(values)).dropna()

        r5 = finite("close_return_5")
        r20 = finite("close_return_20")
        atr14 = finite("atr14_over_close")
        close_pos = finite("close_position_20")
        rel_volume = finite("relative_volume_20")
        rel_value = finite("log_regular_value_relative_20")
        context_rows.append(
            {
                "date": pd.Timestamp(date),
                "market_primary_liquid_count": float(len(block)),
                "market_breadth_return_5_positive": float((r5 > 0.0).mean()) if len(r5) else np.nan,
                "market_breadth_return_20_positive": float((r20 > 0.0).mean()) if len(r20) else np.nan,
                "market_median_close_return_5": float(r5.median()) if len(r5) else np.nan,
                "market_median_close_return_20": float(r20.median()) if len(r20) else np.nan,
                "market_median_atr14_over_close": float(atr14.median()) if len(atr14) else np.nan,
                "market_median_close_position_20": float(close_pos.median()) if len(close_pos) else np.nan,
                "market_median_relative_volume_20": float(rel_volume.median()) if len(rel_volume) else np.nan,
                "market_median_log_regular_value_relative_20": float(rel_value.median()) if len(rel_value) else np.nan,
            }
        )
    context = pd.DataFrame(context_rows)
    result = result.merge(context, on="date", how="left", validate="many_to_one")

    primary_mask = result["universe_primary_liquid"].astype(bool)
    for source, (market_column, output) in _V2_RELATIVE_SOURCE_TO_MARKET.items():
        result[output] = np.nan
        stock = pd.to_numeric(result.loc[primary_mask, source], errors="coerce").astype(float)
        market = pd.to_numeric(result.loc[primary_mask, market_column], errors="coerce").astype(float)
        result.loc[primary_mask, output] = stock - market

    return result[["ticker", "date", "universe_primary_liquid", *V2_FULL_FEATURE_COLUMNS]].copy()


def feature_difference_table(
    original: pd.DataFrame,
    counterfactual: pd.DataFrame,
    *,
    feature_columns: Iterable[str],
    keys: pd.DataFrame | None = None,
    atol: float = FEATURE_ATOL,
) -> pd.DataFrame:
    """Compare two feature tables on exact ticker/date identity."""
    columns = tuple(feature_columns)
    left = original[["ticker", "date", *columns]].copy()
    right = counterfactual[["ticker", "date", *columns]].copy()
    for frame, label in ((left, "original"), (right, "counterfactual")):
        frame["ticker"] = normalize_ticker(frame["ticker"])
        frame["date"] = normalize_date(frame["date"], label=label)
        if frame.duplicated(["ticker", "date"]).any():
            raise ValueError(f"{label} feature table has duplicate identity")
    merged = left.merge(right, on=["ticker", "date"], how="inner", suffixes=("_original", "_counterfactual"), validate="one_to_one")
    if keys is not None:
        wanted = keys[["ticker", "date"]].copy()
        wanted["ticker"] = normalize_ticker(wanted["ticker"])
        wanted["date"] = normalize_date(wanted["date"], label="feature keys")
        wanted = wanted.drop_duplicates(["ticker", "date"])
        merged = merged.merge(wanted, on=["ticker", "date"], how="inner", validate="one_to_one")

    changed_names: list[str] = []
    masks: list[np.ndarray] = []
    for feature in columns:
        a = pd.to_numeric(merged[f"{feature}_original"], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(merged[f"{feature}_counterfactual"], errors="coerce").to_numpy(dtype=float)
        same = np.isclose(a, b, rtol=0.0, atol=atol, equal_nan=True)
        name = f"changed__{feature}"
        merged[name] = ~same
        masks.append(~same)
        changed_names.append(name)
    if masks:
        matrix = np.vstack(masks).T
        merged["changed_feature_count"] = matrix.sum(axis=1)
        names = np.asarray(columns, dtype=object)
        merged["changed_features"] = ["|".join(names[row].tolist()) for row in matrix]
    else:
        merged["changed_feature_count"] = 0
        merged["changed_features"] = ""
    return merged


def feature_parity_summary(diff: pd.DataFrame) -> dict[str, Any]:
    if diff.empty:
        return {
            "rows": 0,
            "changed_rows": 0,
            "changed_cells": 0,
            "changed_row_rate": 0.0,
            "changed_feature_counts": {},
        }
    change_cols = [column for column in diff.columns if column.startswith("changed__")]
    changed_rows = int(diff["changed_feature_count"].gt(0).sum())
    feature_counts = {
        column.removeprefix("changed__"): int(diff[column].sum())
        for column in change_cols
        if int(diff[column].sum()) > 0
    }
    return {
        "rows": int(len(diff)),
        "changed_rows": changed_rows,
        "changed_cells": int(sum(feature_counts.values())),
        "changed_row_rate": float(changed_rows / len(diff)),
        "changed_feature_counts": feature_counts,
    }
