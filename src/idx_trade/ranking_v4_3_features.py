from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


PRIMARY_LIQUIDITY_LOOKBACK = 60
PRIMARY_MIN_ACTIVE_OBSERVATIONS = 20
PRIMARY_VALUE_THRESHOLD_IDR = 1_000_000_000.0

V4_XS_SOURCE_FEATURES = (
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

V4_XS_FEATURE_COLUMNS = tuple(f"xs_rank_{name}" for name in V4_XS_SOURCE_FEATURES)

V4_MARKET_CONTEXT_COLUMNS = (
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

V4_MARKET_RELATIVE_COLUMNS = (
    "market_relative_close_return_5",
    "market_relative_close_return_20",
    "market_relative_atr14_over_close",
    "market_relative_close_position_20",
    "market_relative_relative_volume_20",
    "market_relative_log_regular_value_relative_20",
)

V4_CONTROL_FEATURE_COLUMNS = (
    *V4_XS_FEATURE_COLUMNS,
    *V4_MARKET_CONTEXT_COLUMNS,
    *V4_MARKET_RELATIVE_COLUMNS,
)

_RELATIVE_SOURCE_TO_MARKET = {
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


@dataclass(frozen=True)
class PitFeatureDiagnostics:
    input_rows: int
    admitted_listing_rows: int
    excluded_pre_listing_rows: int
    excluded_post_listing_rows: int
    excluded_missing_security_master_rows: int
    tickers_input: int
    tickers_admitted: int


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


def _ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _date(series: pd.Series, *, label: str) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if values.isna().any():
        raise ValueError(f"{label} contains invalid date")
    return values


def _finite(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").astype(float)
    return numeric.where(np.isfinite(numeric))


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.astype(float) / denominator.astype(float)
    return result.where(np.isfinite(result) & denominator.ne(0))


def _prepare_security_master(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "listed_from", "listed_to"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"security master missing columns: {sorted(missing)}")
    master = frame[["ticker", "listed_from", "listed_to"]].copy()
    master["ticker"] = _ticker(master["ticker"])
    if master["ticker"].eq("").any() or master["ticker"].duplicated().any():
        raise ValueError("security master ticker identity must be non-empty and unique")
    master["listed_from"] = pd.to_datetime(master["listed_from"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if master["listed_from"].isna().any():
        raise ValueError("security master contains invalid listed_from")
    listed_to_raw = master["listed_to"]
    parsed_to = pd.to_datetime(listed_to_raw, errors="coerce").dt.tz_localize(None).dt.normalize()
    finite_to = listed_to_raw.notna() & listed_to_raw.astype(str).str.strip().ne("")
    if (finite_to & parsed_to.isna()).any():
        raise ValueError("security master contains malformed non-empty listed_to")
    master["listed_to"] = parsed_to
    invalid_interval = master["listed_to"].notna() & master["listed_to"].lt(master["listed_from"])
    if invalid_interval.any():
        raise ValueError("security master contains listed_to before listed_from")
    return master


def filter_pit_listing_rows(
    panel: pd.DataFrame,
    security_master: pd.DataFrame,
) -> tuple[pd.DataFrame, PitFeatureDiagnostics]:
    """Remove invalid listing-domain rows before any sequential feature build."""

    required = {"ticker", "date", "high", "low", "close", "volume", "regular_market_value"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"signal panel missing columns: {sorted(missing)}")

    data = panel.copy()
    data["ticker"] = _ticker(data["ticker"])
    data["date"] = _date(data["date"], label="signal panel")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("signal panel contains duplicate ticker/date identity")

    master = _prepare_security_master(security_master)
    data = data.merge(master, on="ticker", how="left", validate="many_to_one", indicator="_master_join")
    missing_master = data["_master_join"].ne("both")
    pre_listing = (~missing_master) & data["date"].lt(data["listed_from"])
    post_listing = (~missing_master) & data["listed_to"].notna() & data["date"].gt(data["listed_to"])
    admitted = ~(missing_master | pre_listing | post_listing)

    diagnostics = PitFeatureDiagnostics(
        input_rows=int(len(data)),
        admitted_listing_rows=int(admitted.sum()),
        excluded_pre_listing_rows=int(pre_listing.sum()),
        excluded_post_listing_rows=int(post_listing.sum()),
        excluded_missing_security_master_rows=int(missing_master.sum()),
        tickers_input=int(data["ticker"].nunique()),
        tickers_admitted=int(data.loc[admitted, "ticker"].nunique()),
    )
    out = data.loc[admitted].drop(columns=["_master_join"]).copy()
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True), diagnostics


def _add_causal_atr(data: pd.DataFrame) -> pd.DataFrame:
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
        frame["atr14"] = true_range.rolling(14, min_periods=14).mean()
        pieces.append(frame)
    return pd.concat(pieces, ignore_index=True, sort=False)


def build_v4_control_feature_table(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    security_master: pd.DataFrame,
) -> tuple[pd.DataFrame, PitFeatureDiagnostics]:
    """Build the frozen 25-column V4 control representation PIT-safely.

    Information formulas match the clean V2 contextual representation. The
    intentional V4 remediation is ordering: listing-domain invalid rows are
    removed before ATR, rolling features, causal liquidity, cross-sectional
    ranks, breadth, medians, and stock-minus-market context are computed.
    """

    sessions = _sessions(official_sessions)
    index_by_date = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    data, diagnostics = filter_pit_listing_rows(panel, security_master)

    for column in ("high", "low", "close", "volume", "regular_market_value"):
        data[column] = pd.to_numeric(data[column], errors="coerce").astype(float)
    valid_hlc = (
        np.isfinite(data["high"])
        & np.isfinite(data["low"])
        & np.isfinite(data["close"])
        & data["high"].gt(0.0)
        & data["low"].gt(0.0)
        & data["close"].gt(0.0)
        & data["high"].ge(data[["low", "close"]].max(axis=1))
        & data["low"].le(data[["high", "close"]].min(axis=1))
    )
    valid_volume = np.isfinite(data["volume"]) & data["volume"].ge(0.0)
    if not (valid_hlc & valid_volume).all():
        raise ValueError("PIT-admitted panel contains invalid HLCV")

    data["session_index"] = data["date"].map(index_by_date)
    if data["session_index"].isna().any():
        raise ValueError("PIT-admitted panel contains dates outside official calendar")
    data["session_index"] = data["session_index"].astype(int)
    data = _add_causal_atr(data)

    pieces: list[pd.DataFrame] = []
    for _, group in data.groupby("ticker", sort=False):
        frame = group.sort_values("session_index", kind="mergesort").copy()
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

        indices = frame["session_index"].to_numpy(dtype=int)
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
            frame["liquidity_active_observations_60"].ge(PRIMARY_MIN_ACTIVE_OBSERVATIONS)
            & frame["median_regular_value_60"].notna()
        )
        frame["universe_primary_liquid"] = (
            frame["universe_history_qualified"]
            & frame["median_regular_value_60"].ge(PRIMARY_VALUE_THRESHOLD_IDR)
        )
        pieces.append(frame)

    result = pd.concat(pieces, ignore_index=True, sort=False).sort_values(
        ["date", "ticker"], kind="mergesort"
    ).reset_index(drop=True)

    primary_mask = result["universe_primary_liquid"].astype(bool)
    primary = result.loc[primary_mask].copy()
    if primary.empty:
        raise ValueError("PIT-safe feature build has no primary-liquid rows")

    for source, output in zip(V4_XS_SOURCE_FEATURES, V4_XS_FEATURE_COLUMNS, strict=True):
        result[output] = np.nan
        source_values = _finite(primary[source])
        ranks = source_values.groupby(primary["date"]).rank(method="average", pct=True)
        result.loc[ranks.index, output] = ranks.astype(float)

    context_rows: list[dict[str, object]] = []
    for day, block in primary.groupby("date", sort=True):
        def finite_values(name: str) -> pd.Series:
            return _finite(block[name]).dropna()

        r5 = finite_values("close_return_5")
        r20 = finite_values("close_return_20")
        context_rows.append(
            {
                "date": pd.Timestamp(day),
                "market_primary_liquid_count": float(len(block)),
                "market_breadth_return_5_positive": float((r5 > 0.0).mean()) if len(r5) else np.nan,
                "market_breadth_return_20_positive": float((r20 > 0.0).mean()) if len(r20) else np.nan,
                "market_median_close_return_5": float(r5.median()) if len(r5) else np.nan,
                "market_median_close_return_20": float(r20.median()) if len(r20) else np.nan,
                "market_median_atr14_over_close": float(finite_values("atr14_over_close").median()) if len(finite_values("atr14_over_close")) else np.nan,
                "market_median_close_position_20": float(finite_values("close_position_20").median()) if len(finite_values("close_position_20")) else np.nan,
                "market_median_relative_volume_20": float(finite_values("relative_volume_20").median()) if len(finite_values("relative_volume_20")) else np.nan,
                "market_median_log_regular_value_relative_20": float(finite_values("log_regular_value_relative_20").median()) if len(finite_values("log_regular_value_relative_20")) else np.nan,
            }
        )
    context = pd.DataFrame(context_rows)
    result = result.merge(context, on="date", how="left", validate="many_to_one")

    primary_mask = result["universe_primary_liquid"].astype(bool)
    for source, (market_column, output) in _RELATIVE_SOURCE_TO_MARKET.items():
        result[output] = np.nan
        result.loc[primary_mask, output] = (
            _finite(result.loc[primary_mask, source])
            - _finite(result.loc[primary_mask, market_column])
        )

    return result.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True), diagnostics


def v4_primary_control_view(features: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", "universe_primary_liquid", *V4_CONTROL_FEATURE_COLUMNS}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"V4 control feature table missing columns: {sorted(missing)}")
    return features[features["universe_primary_liquid"].astype(bool)].copy().reset_index(drop=True)
