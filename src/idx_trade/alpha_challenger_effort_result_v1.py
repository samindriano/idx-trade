"""Outcome-blind causal features for the Effort-vs-Result challenger.

This module intentionally stops before universe ranking, target joins, model
fitting, or score generation.  It is a research-side feature constructor for
the isolated challenger lane only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = frozenset({"ticker", "date", "open", "high", "low", "close", "volume"})
FORBIDDEN_TOKENS = (
    "target",
    "label",
    "outcome",
    "realized",
    "tp_first",
    "sl_first",
    "return_forward",
)

FEATURE_COLUMNS = (
    "effort_signed_body",
    "effort_close_location",
    "range_per_effort",
    "failed_breakout_signed",
    "confirmed_breakout_signed",
    "effort_absorption",
)


def _validate_input(frame: pd.DataFrame) -> pd.DataFrame:
    columns = {str(column).strip().lower() for column in frame.columns}
    forbidden = sorted(
        str(column)
        for column in frame.columns
        if any(token in str(column).strip().lower() for token in FORBIDDEN_TOKENS)
    )
    if forbidden:
        raise ValueError(f"outcome-like columns are forbidden: {forbidden}")
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"effort-result input missing columns: {sorted(missing)}")

    out = frame.copy()
    out.columns = [str(column).strip().lower() for column in out.columns]
    out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    for column in ("open", "high", "low", "close", "volume"):
        out[column] = pd.to_numeric(out[column], errors="coerce")

    if out[["ticker", "date"]].isna().any().any():
        raise ValueError("ticker/date contains null or invalid values")
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError("duplicate ticker/date rows")

    finite_hlcv = np.isfinite(out[["high", "low", "close", "volume"]].to_numpy(dtype=float)).all(axis=1)
    open_present = out["open"].notna()
    finite_open_when_present = np.isfinite(out["open"].fillna(0).to_numpy(dtype=float)) | ~open_present.to_numpy()
    finite = finite_hlcv & finite_open_when_present
    positive_open_when_present = out["open"].gt(0).to_numpy() | ~open_present.to_numpy()
    open_for_order = out["open"].where(open_present)
    high_floor = pd.concat([out["close"], out["low"], open_for_order], axis=1).max(axis=1)
    low_ceiling = pd.concat([out["close"], out["high"], open_for_order], axis=1).min(axis=1)
    valid_ohlc = (
        finite
        & out[["high", "low", "close"]].gt(0).all(axis=1).to_numpy()
        & positive_open_when_present
        & out["high"].ge(high_floor).to_numpy()
        & out["low"].le(low_ceiling).to_numpy()
        & out["volume"].ge(0).to_numpy()
    )
    if not bool(valid_ohlc.all()):
        raise ValueError("invalid OHLCV row; feature construction fails closed")
    if "corporate_action_integrity_verified" in out.columns:
        verified = out["corporate_action_integrity_verified"]
        if not verified.astype(bool).all():
            raise ValueError("corporate-action integrity is not verified for every row")

    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def build_effort_result_features(frame: pd.DataFrame, *, window: int = 20, min_periods: int = 10) -> pd.DataFrame:
    """Build one causal effort/result row per input row.

    The rolling reference window is explicitly shifted by one row.  Therefore
    the completed session `t` can use its own OHLCV and only sessions before
    `t` for the volume and breakout baselines.  Missing early history remains
    missing; no forward fill or target access is performed.
    """

    if window < 2 or min_periods < 1 or min_periods > window:
        raise ValueError("window/min_periods combination is invalid")
    data = _validate_input(frame)
    grouped = data.groupby("ticker", sort=False, group_keys=False)

    prior_volume_median = grouped["volume"].transform(
        lambda series: series.shift(1).rolling(window, min_periods=min_periods).median()
    )
    prior_high = grouped["high"].transform(
        lambda series: series.shift(1).rolling(window, min_periods=min_periods).max()
    )
    prior_low = grouped["low"].transform(
        lambda series: series.shift(1).rolling(window, min_periods=min_periods).min()
    )

    intraday_range = data["high"] - data["low"]
    valid_range = intraday_range.gt(0)
    body_signed_range = (data["close"] - data["open"]).where(valid_range).div(intraday_range.where(valid_range))
    close_location = (2.0 * data["close"] - data["high"] - data["low"]).where(valid_range).div(
        intraday_range.where(valid_range)
    )
    relative_volume = data["volume"].div(prior_volume_median.where(prior_volume_median.gt(0)))
    log_relative_volume = np.log(relative_volume.where(relative_volume.gt(0)))
    prior_ready = prior_high.notna() & prior_low.notna() & prior_volume_median.gt(0)

    failed_high = prior_ready & data["high"].gt(prior_high) & data["close"].lt(prior_high)
    failed_low = prior_ready & data["low"].lt(prior_low) & data["close"].gt(prior_low)
    confirmed_high = prior_ready & data["close"].gt(prior_high)
    confirmed_low = prior_ready & data["close"].lt(prior_low)

    result = data[["ticker", "date"]].copy()
    result["prior_volume_median"] = prior_volume_median
    result["prior_high"] = prior_high
    result["prior_low"] = prior_low
    result["history_ready"] = prior_ready
    result["open_usable"] = data["open"].notna()
    if "open_available" in data.columns:
        result["open_metadata_mismatch"] = data["open_available"].astype(bool).ne(data["open"].notna())
    else:
        result["open_metadata_mismatch"] = False
    result["effort_signed_body"] = log_relative_volume * body_signed_range
    result["effort_close_location"] = log_relative_volume * close_location
    result["range_per_effort"] = np.log(data["high"].div(data["low"])) - log_relative_volume
    result["failed_breakout_signed"] = failed_low.astype(float) - failed_high.astype(float)
    result["confirmed_breakout_signed"] = confirmed_high.astype(float) - confirmed_low.astype(float)
    result["effort_absorption"] = log_relative_volume * (1.0 - body_signed_range.abs())

    for column in FEATURE_COLUMNS:
        values = pd.to_numeric(result[column], errors="coerce")
        if np.isinf(values.to_numpy(dtype=float)).any():
            raise RuntimeError(f"feature contains infinity: {column}")
        result[column] = values
    return result


__all__ = ["FEATURE_COLUMNS", "build_effort_result_features"]
