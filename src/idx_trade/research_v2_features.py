from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from .research_features import assert_no_open_dependency


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

V2_TIME_PROXY_EXCLUSIONS = (
    "observed_session_count",
    "security_age_sessions_exact",
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


def _normalize_dates(values: pd.Series) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce")
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_localize(None)
    return dates.dt.normalize()


def _finite_numeric(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    return values.where(np.isfinite(values))


def _positive_breadth(series: pd.Series) -> float:
    values = _finite_numeric(series).dropna()
    if values.empty:
        return np.nan
    return float((values > 0.0).mean())


def _finite_median(series: pd.Series) -> float:
    values = _finite_numeric(series).dropna()
    if values.empty:
        return np.nan
    return float(values.median())


def build_v2_feature_table(features: pd.DataFrame) -> pd.DataFrame:
    """Add frozen Ranking-V2 cross-sectional and market-context features.

    Cross-sectional ranks and market context are computed from the full causal
    primary-liquid universe on each signal date. Resolved labels are never used
    here. The transformation is therefore outcome-independent and causal at the
    after-close signal timestamp.
    """

    required = {"ticker", "date", "universe_primary_liquid", *V2_XS_SOURCE_FEATURES}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"V2 feature input missing columns: {sorted(missing)}")
    assert_no_open_dependency(V2_XS_SOURCE_FEATURES)
    assert_no_open_dependency(V2_FULL_FEATURE_COLUMNS)

    data = features.copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["date"] = _normalize_dates(data["date"])
    if data["date"].isna().any():
        raise ValueError("V2 feature input contains invalid dates")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("V2 feature input contains duplicate ticker/date rows")

    for feature in V2_XS_SOURCE_FEATURES:
        data[feature] = _finite_numeric(data[feature])

    primary_mask = data["universe_primary_liquid"].astype(bool)
    primary = data.loc[primary_mask].copy()
    if primary.empty:
        raise ValueError("V2 feature input has no primary-liquid rows")

    # Frozen within-date percentile ranks. Missing raw values remain missing.
    for source, output in zip(V2_XS_SOURCE_FEATURES, V2_XS_FEATURE_COLUMNS, strict=True):
        data[output] = np.nan
        ranks = primary.groupby("date", sort=True)[source].rank(method="average", pct=True)
        data.loc[ranks.index, output] = ranks.astype(float)

    # Market context is computed from every primary-liquid row on the date,
    # independent of whether a future H10 label later resolves.
    context_rows: list[dict[str, object]] = []
    for date, block in primary.groupby("date", sort=True):
        context_rows.append(
            {
                "date": pd.Timestamp(date),
                "market_primary_liquid_count": float(len(block)),
                "market_breadth_return_5_positive": _positive_breadth(block["close_return_5"]),
                "market_breadth_return_20_positive": _positive_breadth(block["close_return_20"]),
                "market_median_close_return_5": _finite_median(block["close_return_5"]),
                "market_median_close_return_20": _finite_median(block["close_return_20"]),
                "market_median_atr14_over_close": _finite_median(block["atr14_over_close"]),
                "market_median_close_position_20": _finite_median(block["close_position_20"]),
                "market_median_relative_volume_20": _finite_median(block["relative_volume_20"]),
                "market_median_log_regular_value_relative_20": _finite_median(
                    block["log_regular_value_relative_20"]
                ),
            }
        )
    context = pd.DataFrame(context_rows)
    if context["date"].duplicated().any():
        raise RuntimeError("V2 market context produced duplicate dates")

    data = data.merge(context, on="date", how="left", validate="many_to_one")

    # Stock-minus-market relative features. They are meaningful for the primary
    # universe used by the model; non-primary rows remain available in the table
    # but are not candidate model rows.
    primary_mask = data["universe_primary_liquid"].astype(bool)
    for source, (market_column, output) in _RELATIVE_SOURCE_TO_MARKET.items():
        data[output] = np.nan
        stock = _finite_numeric(data.loc[primary_mask, source])
        market = _finite_numeric(data.loc[primary_mask, market_column])
        data.loc[primary_mask, output] = stock - market

    return data.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def v2_primary_feature_view(features: pd.DataFrame, *, columns: Iterable[str] = V2_FULL_FEATURE_COLUMNS) -> pd.DataFrame:
    requested = tuple(columns)
    required = {"ticker", "date", "universe_primary_liquid", *requested}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"V2 primary feature view missing columns: {sorted(missing)}")
    assert_no_open_dependency(requested)
    return features[features["universe_primary_liquid"].astype(bool)].copy().reset_index(drop=True)
