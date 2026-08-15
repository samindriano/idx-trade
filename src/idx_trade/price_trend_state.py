"""Deterministic, outcome-blind price/trend/confirmation state for IDX daily bars.

V1 is deliberately descriptive.  It does not fit a model, estimate expected
return, emit a trade recommendation, or inspect future outcomes.  Every source
session ``t`` is assigned to the next official feature session ``t+1``.

The contract intentionally uses H/L/C/Volume only.  ``Open`` is excluded so
this state layer does not depend on the still-separate historical OPEN recovery
lineage.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


STATE_CONTRACT_VERSION = "PRICE_TREND_CONFIRMATION_STATE_V1"

REQUIRED_INPUT_COLUMNS = (
    "ticker",
    "session_date",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
)

EVIDENCE_COLUMNS = (
    "source_close",
    "ma_10",
    "ma_20",
    "ma_50",
    "ma_200",
    "ma20_slope_5",
    "ma50_slope_10",
    "ma200_slope_20",
    "distance_to_ma20",
    "distance_to_ma50",
    "distance_to_ma200",
    "prior_high_20",
    "prior_low_20",
    "distance_to_prior_high_20",
    "range_position_20",
    "range_width_20",
    "recent_low_5",
    "prior_low_5",
    "recent_high_5",
    "prior_high_5",
    "volume_ratio_20",
    "range_median_5",
    "range_median_prior_20",
    "volatility_ratio_5_20",
    "recent_breakout_level_5",
)

STATE_COLUMNS = (
    "trend_state",
    "ma_structure_state",
    "long_term_state",
    "swing_structure_state",
    "volume_state",
    "volatility_state",
    "confirmation_state",
)

_FORBIDDEN_TOKENS = (
    "binary_target",
    "label_status",
    "outcome",
    "tp_first",
    "sl_first",
    "realized",
    "forward_return",
    "future_return",
    "target_return",
)

# Engineering/descriptive defaults only.  These are not estimated or tuned
# against historical outcomes and must not be changed post-hoc from a result.
VOLUME_EXPANSION_RATIO = 1.50
VOLUME_CONTRACTION_RATIO = 2.0 / 3.0
VOLATILITY_CONTRACTION_RATIO = 0.75
VOLATILITY_EXPANSION_RATIO = 1.25
NEAR_BREAKOUT_DISTANCE = -0.03
BASING_MAX_ABS_MA20_SLOPE_5 = 0.015
BASING_MAX_RANGE_WIDTH_20 = 0.20
BASING_MAX_ABS_DISTANCE_TO_MA20 = 0.08


def _date(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"invalid date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


def _official_index(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = pd.DatetimeIndex([_date(value) for value in values]).sort_values()
    if len(sessions) < 2 or sessions.has_duplicates:
        raise ValueError("official session calendar must contain unique ordered sessions")
    return sessions


def _normalise_input(frame: pd.DataFrame) -> pd.DataFrame:
    forbidden = [
        str(column)
        for column in frame.columns
        if any(token in str(column).lower() for token in _FORBIDDEN_TOKENS)
    ]
    if forbidden:
        raise ValueError(f"price state input contains outcome-like columns: {sorted(forbidden)}")

    data = frame.copy()
    if "date" in data.columns and "session_date" not in data.columns:
        data = data.rename(columns={"date": "session_date"})

    missing = set(REQUIRED_INPUT_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"price state input missing columns: {sorted(missing)}")

    data = data[list(REQUIRED_INPUT_COLUMNS)].copy()
    data["ticker"] = (
        data["ticker"]
        .astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )
    if data["ticker"].eq("").any():
        raise ValueError("price state input contains empty ticker")

    parsed = pd.to_datetime(data["session_date"], errors="coerce")
    if parsed.isna().any():
        raise ValueError("price state input contains malformed session_date")
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        parsed = parsed.dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)
    data["session_date"] = parsed.dt.normalize()

    for column in ("raw_high", "raw_low", "raw_close", "raw_volume"):
        values = pd.to_numeric(data[column], errors="coerce")
        if values.isna().any() or (~np.isfinite(values.to_numpy(dtype=float))).any():
            raise ValueError(f"price state input contains invalid {column}")
        data[column] = values.astype(float)

    if (data[["raw_high", "raw_low", "raw_close"]] <= 0).any().any():
        raise ValueError("price state input contains non-positive HLC")
    if (data["raw_volume"] < 0).any():
        raise ValueError("price state input contains negative volume")
    if (data["raw_low"] > data["raw_high"]).any():
        raise ValueError("price state input contains low above high")
    if ((data["raw_close"] < data["raw_low"]) | (data["raw_close"] > data["raw_high"])).any():
        raise ValueError("price state input contains close outside high/low")
    if data.duplicated(["ticker", "session_date"]).any():
        raise ValueError("price state input contains duplicate ticker/session identity")

    return data.sort_values(["ticker", "session_date"], kind="mergesort").reset_index(drop=True)


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.astype(float).div(denominator.astype(float))
    return result.where(np.isfinite(result) & denominator.ne(0))


def _state_from_row(row: pd.Series) -> dict[str, str]:
    required = [
        "ma_20",
        "ma_50",
        "ma20_slope_5",
        "ma50_slope_10",
        "distance_to_ma20",
        "prior_high_20",
        "prior_low_20",
        "range_width_20",
        "recent_low_5",
        "prior_low_5",
        "recent_high_5",
        "prior_high_5",
        "volume_ratio_20",
        "range_median_5",
        "range_median_prior_20",
        "volatility_ratio_5_20",
    ]
    if any(pd.isna(row[column]) or not np.isfinite(float(row[column])) for column in required):
        return {column: "INDETERMINATE" for column in STATE_COLUMNS}

    close = float(row["source_close"])
    ma20 = float(row["ma_20"])
    ma50 = float(row["ma_50"])
    slope20 = float(row["ma20_slope_5"])
    slope50 = float(row["ma50_slope_10"])

    if close > ma20 > ma50 and slope20 > 0 and slope50 > 0:
        ma_state = "BULLISH_STACK"
    elif close < ma20 < ma50 and slope20 < 0 and slope50 < 0:
        ma_state = "BEARISH_STACK"
    elif close > ma20 and slope20 > 0:
        ma_state = "RECOVERING"
    elif close < ma20 and slope20 < 0:
        ma_state = "WEAKENING"
    else:
        ma_state = "MIXED"

    ma200 = row["ma_200"]
    ma200_slope = row["ma200_slope_20"]
    if pd.isna(ma200) or pd.isna(ma200_slope):
        long_term_state = "UNAVAILABLE"
    elif close > float(ma200) and float(ma200_slope) > 0:
        long_term_state = "ABOVE_RISING_MA200"
    elif close < float(ma200) and float(ma200_slope) < 0:
        long_term_state = "BELOW_FALLING_MA200"
    else:
        long_term_state = "MIXED"

    higher_low = float(row["recent_low_5"]) > float(row["prior_low_5"])
    higher_high = float(row["recent_high_5"]) > float(row["prior_high_5"])
    lower_low = float(row["recent_low_5"]) < float(row["prior_low_5"])
    lower_high = float(row["recent_high_5"]) < float(row["prior_high_5"])
    if higher_low and higher_high:
        swing_state = "HIGHER_LOW_HIGHER_HIGH"
    elif higher_low:
        swing_state = "HIGHER_LOW_ONLY"
    elif lower_low and lower_high:
        swing_state = "LOWER_LOW_LOWER_HIGH"
    elif lower_low:
        swing_state = "LOWER_LOW_ONLY"
    else:
        swing_state = "MIXED"

    volume_ratio = float(row["volume_ratio_20"])
    if volume_ratio >= VOLUME_EXPANSION_RATIO:
        volume_state = "EXPANDING"
    elif volume_ratio <= VOLUME_CONTRACTION_RATIO:
        volume_state = "CONTRACTING"
    else:
        volume_state = "NORMAL"

    volatility_ratio = float(row["volatility_ratio_5_20"])
    if volatility_ratio <= VOLATILITY_CONTRACTION_RATIO:
        volatility_state = "CONTRACTING"
    elif volatility_ratio >= VOLATILITY_EXPANSION_RATIO:
        volatility_state = "EXPANDING"
    else:
        volatility_state = "NORMAL"

    breakout = close > float(row["prior_high_20"])
    recent_breakout_level = row["recent_breakout_level_5"]
    failed_recent = (
        not pd.isna(recent_breakout_level)
        and np.isfinite(float(recent_breakout_level))
        and close < float(recent_breakout_level)
    )
    distance_to_high = float(row["distance_to_prior_high_20"])
    if breakout and volume_ratio >= VOLUME_EXPANSION_RATIO:
        confirmation_state = "BREAKOUT_CONFIRMED"
    elif breakout:
        confirmation_state = "BREAKOUT_WEAK_VOLUME"
    elif failed_recent:
        confirmation_state = "FAILED_BREAKOUT_RECENT"
    elif distance_to_high >= NEAR_BREAKOUT_DISTANCE:
        confirmation_state = "NEAR_BREAKOUT"
    else:
        confirmation_state = "NO_BREAKOUT"

    basing = (
        abs(slope20) <= BASING_MAX_ABS_MA20_SLOPE_5
        and float(row["range_width_20"]) <= BASING_MAX_RANGE_WIDTH_20
        and abs(float(row["distance_to_ma20"])) <= BASING_MAX_ABS_DISTANCE_TO_MA20
        and volatility_state != "EXPANDING"
    )
    if ma_state == "BULLISH_STACK":
        trend_state = "UPTREND"
    elif ma_state == "BEARISH_STACK":
        trend_state = "DOWNTREND"
    elif ma_state == "RECOVERING" and higher_low:
        trend_state = "EARLY_REVERSAL"
    elif basing:
        trend_state = "BASING"
    else:
        trend_state = "TRANSITION"

    return {
        "trend_state": trend_state,
        "ma_structure_state": ma_state,
        "long_term_state": long_term_state,
        "swing_structure_state": swing_state,
        "volume_state": volume_state,
        "volatility_state": volatility_state,
        "confirmation_state": confirmation_state,
    }


def _ticker_evidence(group: pd.DataFrame) -> pd.DataFrame:
    out = group.copy()
    high = out["raw_high"]
    low = out["raw_low"]
    close = out["raw_close"]
    volume = out["raw_volume"]

    out["source_close"] = close
    out["ma_10"] = close.rolling(10, min_periods=10).mean()
    out["ma_20"] = close.rolling(20, min_periods=20).mean()
    out["ma_50"] = close.rolling(50, min_periods=50).mean()
    out["ma_200"] = close.rolling(200, min_periods=200).mean()
    out["ma20_slope_5"] = _safe_div(out["ma_20"], out["ma_20"].shift(5)) - 1.0
    out["ma50_slope_10"] = _safe_div(out["ma_50"], out["ma_50"].shift(10)) - 1.0
    out["ma200_slope_20"] = _safe_div(out["ma_200"], out["ma_200"].shift(20)) - 1.0

    out["distance_to_ma20"] = _safe_div(close, out["ma_20"]) - 1.0
    out["distance_to_ma50"] = _safe_div(close, out["ma_50"]) - 1.0
    out["distance_to_ma200"] = _safe_div(close, out["ma_200"]) - 1.0

    out["prior_high_20"] = high.rolling(20, min_periods=20).max().shift(1)
    out["prior_low_20"] = low.rolling(20, min_periods=20).min().shift(1)
    out["distance_to_prior_high_20"] = _safe_div(close, out["prior_high_20"]) - 1.0
    prior_range = out["prior_high_20"] - out["prior_low_20"]
    out["range_position_20"] = _safe_div(close - out["prior_low_20"], prior_range)

    current_high_20 = high.rolling(20, min_periods=20).max()
    current_low_20 = low.rolling(20, min_periods=20).min()
    out["range_width_20"] = _safe_div(current_high_20 - current_low_20, close)

    out["recent_low_5"] = low.rolling(5, min_periods=5).min()
    out["prior_low_5"] = low.shift(5).rolling(5, min_periods=5).min()
    out["recent_high_5"] = high.rolling(5, min_periods=5).max()
    out["prior_high_5"] = high.shift(5).rolling(5, min_periods=5).max()

    prior_volume_median_20 = volume.shift(1).rolling(20, min_periods=20).median()
    out["volume_ratio_20"] = _safe_div(volume, prior_volume_median_20)

    range_pct = _safe_div(high - low, close)
    out["range_median_5"] = range_pct.rolling(5, min_periods=5).median()
    out["range_median_prior_20"] = range_pct.shift(5).rolling(20, min_periods=20).median()
    out["volatility_ratio_5_20"] = _safe_div(
        out["range_median_5"], out["range_median_prior_20"]
    )

    breakout_event = close > out["prior_high_20"]
    breakout_level = out["prior_high_20"].where(breakout_event)
    out["recent_breakout_level_5"] = breakout_level.shift(1).rolling(5, min_periods=1).max()

    states = out.apply(_state_from_row, axis=1, result_type="expand")
    for column in STATE_COLUMNS:
        out[column] = states[column]
    return out


def build_price_trend_confirmation_state_v1(
    frame: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Build deterministic price state from source session ``t`` for ``t+1``.

    The source panel may contain many historical sessions.  All evidence for a
    row is computed only from that ticker's observations through its own source
    session.  ``feature_session`` is the next date from the supplied official
    calendar; target-session OHLCV is never required for that row.
    """

    data = _normalise_input(frame)
    sessions = _official_index(official_sessions)
    official_set = set(sessions)
    if not data["session_date"].isin(official_set).all():
        raise ValueError("price state input contains dates outside official sessions")

    next_session = {sessions[index]: sessions[index + 1] for index in range(len(sessions) - 1)}
    pieces: list[pd.DataFrame] = []
    for _, group in data.groupby("ticker", sort=False):
        pieces.append(_ticker_evidence(group.sort_values("session_date", kind="mergesort")))
    result = pd.concat(pieces, ignore_index=True, sort=False)
    result["feature_session"] = result["session_date"].map(next_session)
    result = result.loc[result["feature_session"].notna()].copy()
    result = result.rename(columns={"session_date": "source_session"})
    result["state_contract_version"] = STATE_CONTRACT_VERSION
    result["outcome_blind"] = True
    result["model_fitted"] = False
    result["trade_recommendation"] = False

    columns = [
        "ticker",
        "source_session",
        "feature_session",
        *EVIDENCE_COLUMNS,
        *STATE_COLUMNS,
        "state_contract_version",
        "outcome_blind",
        "model_fitted",
        "trade_recommendation",
    ]
    result = result[columns].sort_values(["feature_session", "ticker"], kind="mergesort")
    if result.duplicated(["ticker", "feature_session"]).any():
        raise RuntimeError("price state output contains duplicate ticker/feature_session")
    return result.reset_index(drop=True)


def build_price_state_for_source_session(
    frame: pd.DataFrame,
    official_sessions: Iterable[object],
    source_session: object,
) -> pd.DataFrame:
    """Return exactly one prospective feature-session slice for completed ``t``."""

    source = _date(source_session)
    data = _normalise_input(frame)
    if source not in set(data["session_date"]):
        raise ValueError("requested source session is absent from price input")
    if (data["session_date"] > source).any():
        data = data.loc[data["session_date"] <= source].copy()
    built = build_price_trend_confirmation_state_v1(data, official_sessions)
    selected = built.loc[built["source_session"].eq(source)].copy()
    if selected.empty:
        raise RuntimeError("requested source has no next official feature session")
    return selected.reset_index(drop=True)
