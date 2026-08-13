from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

from .research_labels import add_causal_atr


PRIMARY_VALUE_THRESHOLD_IDR = 1_000_000_000.0
PRIMARY_LIQUIDITY_LOOKBACK = 60
PRIMARY_MIN_ACTIVE_OBSERVATIONS = 20

BASELINE_FEATURE_COLUMNS = (
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
    "observed_session_count",
    "security_age_sessions_exact",
)


def _sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .tz_localize(None)
        .normalize()
        .dropna()
        .unique()
        .sort_values()
    )
    if not len(sessions):
        raise ValueError("official_sessions must not be empty")
    return sessions


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.astype(float) / denominator.astype(float)
    return result.where(np.isfinite(result) & denominator.ne(0))


def _age_features(
    ticker: str,
    session_indices: pd.Series,
    sessions: pd.DatetimeIndex,
    listed_from: Mapping[str, object] | None,
) -> tuple[pd.Series, pd.Series]:
    """Return exact in-window age, otherwise explicit left-censored missingness.

    For securities listed before the certified calendar starts, the exact number
    of exchange sessions since listing is not identifiable from this snapshot.
    Returning the number of sessions since 2021-04-29 would create a calendar-
    time proxy, not security age, so the model feature remains NaN and the
    diagnostic censor flag stays explicit.
    """

    listing_value = None if listed_from is None else listed_from.get(ticker)
    listing_date = pd.to_datetime(listing_value, errors="coerce") if listing_value is not None else pd.NaT
    if pd.isna(listing_date):
        return (
            pd.Series(np.nan, index=session_indices.index, dtype=float),
            pd.Series(True, index=session_indices.index, dtype=bool),
        )
    listing_date = pd.Timestamp(listing_date).tz_localize(None).normalize()
    if listing_date < sessions[0]:
        return (
            pd.Series(np.nan, index=session_indices.index, dtype=float),
            pd.Series(True, index=session_indices.index, dtype=bool),
        )
    first_session_idx = int(sessions.searchsorted(listing_date, side="left"))
    age = (session_indices.astype(float) - float(first_session_idx) + 1.0).where(
        session_indices.astype(int) >= first_session_idx
    )
    return age, pd.Series(False, index=session_indices.index, dtype=bool)


def build_baseline_features(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    listed_from: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    """Build the frozen compact causal feature table.

    Price/volume rolling features are right-aligned over observed ACTIVE bars.
    The primary liquidity rule is different: its 60-session window is measured
    in official exchange-session space and requires at least 20 observed ACTIVE
    rows inside that exact window.

    `security_age_sessions_exact` is populated only when listing occurs inside
    the certified calendar and exact exchange-session age is therefore known.
    Older listings remain NaN with `security_age_left_censored=True`; the later
    training-only imputer/missing-indicator path handles them without inventing
    a pre-window calendar.
    """

    sessions = _sessions(official_sessions)
    index_by_date = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    data = add_causal_atr(panel, window=14)
    if "regular_market_value" not in data.columns:
        raise ValueError("panel must contain regular_market_value")
    data["regular_market_value"] = pd.to_numeric(data["regular_market_value"], errors="coerce")
    data["session_index_zero"] = data["date"].map(index_by_date)
    if data["session_index_zero"].isna().any():
        raise ValueError("panel contains dates outside the official session calendar")
    data["session_index_zero"] = data["session_index_zero"].astype(int)

    pieces: list[pd.DataFrame] = []
    for ticker, group in data.groupby("ticker", sort=False):
        frame = group.sort_values("date").copy()
        close = frame["close"].astype(float)
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        volume = frame["volume"].astype(float)
        value = frame["regular_market_value"].astype(float)
        atr = frame["atr14"].astype(float)

        frame["close_return_5"] = close / close.shift(5) - 1.0
        frame["close_return_20"] = close / close.shift(20) - 1.0
        frame["atr14_over_close"] = _safe_divide(atr, close)

        high20 = high.rolling(20, min_periods=20).max()
        low20 = low.rolling(20, min_periods=20).min()
        high60 = high.rolling(60, min_periods=60).max()
        low60 = low.rolling(60, min_periods=60).min()
        range20 = high20 - low20
        frame["close_position_20"] = _safe_divide(close - low20, range20)
        frame["distance_high_20_atr"] = _safe_divide(high20 - close, atr)
        frame["distance_low_20_atr"] = _safe_divide(close - low20, atr)
        frame["distance_high_60_atr"] = _safe_divide(high60 - close, atr)
        frame["distance_low_60_atr"] = _safe_divide(close - low60, atr)

        median_volume20 = volume.rolling(20, min_periods=20).median()
        frame["relative_volume_20"] = _safe_divide(volume, median_volume20)
        median_value20 = value.rolling(20, min_periods=20).median()
        ratio_value = _safe_divide(value, median_value20)
        frame["log_regular_value_relative_20"] = np.log(ratio_value.where(ratio_value > 0))
        frame["observed_session_count"] = np.arange(1, len(frame) + 1, dtype=int)

        age, censored = _age_features(
            ticker,
            frame["session_index_zero"],
            sessions,
            listed_from,
        )
        frame["security_age_sessions_exact"] = age.astype(float)
        frame["security_age_left_censored"] = censored.astype(bool)

        session_idx = frame["session_index_zero"].to_numpy(dtype=int)
        values = frame["regular_market_value"].to_numpy(dtype=float)
        counts: list[int] = []
        medians: list[float] = []
        left = 0
        for right, idx in enumerate(session_idx):
            min_idx = idx - (PRIMARY_LIQUIDITY_LOOKBACK - 1)
            while left <= right and session_idx[left] < min_idx:
                left += 1
            window_values = values[left : right + 1]
            finite = window_values[np.isfinite(window_values)]
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

    result = pd.concat(pieces, ignore_index=True, sort=False)
    result = result.sort_values(["date", "ticker"]).reset_index(drop=True)

    qualified = result["universe_history_qualified"]
    ranks = result.loc[qualified].groupby("date")["median_regular_value_60"].rank(
        method="first", ascending=False
    )
    result["causal_liquidity_rank"] = np.nan
    result.loc[qualified, "causal_liquidity_rank"] = ranks
    result["universe_top100"] = result["causal_liquidity_rank"].le(100).fillna(False)
    result["universe_top300"] = result["causal_liquidity_rank"].le(300).fillna(False)
    return result


def primary_feature_view(features: pd.DataFrame) -> pd.DataFrame:
    """Return rows admitted to the frozen primary broad causal liquid view."""

    required = {"ticker", "date", "universe_primary_liquid", *BASELINE_FEATURE_COLUMNS}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"feature table missing columns: {sorted(missing)}")
    return features[features["universe_primary_liquid"].astype(bool)].copy().reset_index(drop=True)


def assert_no_open_dependency(feature_columns: Iterable[str]) -> None:
    offenders = [name for name in feature_columns if "open" in str(name).lower()]
    if offenders:
        raise ValueError(f"primary features may not depend on Open: {offenders}")
