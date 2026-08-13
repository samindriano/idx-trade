from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from .research_features import build_baseline_features


MIN_CROSS_SECTION = 50

V4_C_FEATURE_COLUMNS = (
    "v4c_market_return_iqr_5",
    "v4c_market_return_iqr_20",
    "v4c_market_atr_iqr",
    "v4c_market_close_position_iqr_20",
)

_SOURCE_FEATURES = (
    "close_return_5",
    "close_return_20",
    "atr14_over_close",
    "close_position_20",
)

_FORBIDDEN_TOKENS = (
    "binary_target",
    "label_status",
    "actual_up",
    "realized_return",
    "outcome",
    "tp_first",
    "sl_first",
)


def normalize_official_sessions(values: Iterable[object]) -> pd.DatetimeIndex:
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


def _iqr(values: pd.Series, *, minimum: int = MIN_CROSS_SECTION) -> float:
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    finite = numeric[np.isfinite(numeric)]
    if len(finite) < int(minimum):
        return np.nan
    q25, q75 = np.quantile(finite, [0.25, 0.75], method="linear")
    result = float(q75 - q25)
    if not np.isfinite(result) or result < 0.0:
        raise RuntimeError("V4-C IQR construction produced invalid dispersion")
    return result


def build_cross_sectional_context_features(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    max_signal_session_index: int,
) -> pd.DataFrame:
    """Build frozen V4-C date-level dispersion context without outcomes.

    The full causal primary-liquid universe is reconstructed using the exact
    existing V2 baseline-feature semantics before any model-row filtering.
    Returned V4-C features are one row per signal date and are therefore
    constant across all stocks sharing that date after the later join.
    """

    required = {
        "ticker",
        "date",
        "high",
        "low",
        "close",
        "volume",
        "regular_market_value",
    }
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"V4-C panel missing columns: {sorted(missing)}")

    present_forbidden = [
        column
        for column in panel.columns
        if any(token in str(column).lower() for token in _FORBIDDEN_TOKENS)
    ]
    if present_forbidden:
        raise ValueError(
            "V4-C context builder must not receive label/outcome columns: "
            f"{sorted(present_forbidden)}"
        )

    if max_signal_session_index <= 0:
        raise ValueError("max_signal_session_index must be positive")

    sessions = normalize_official_sessions(official_sessions)
    if max_signal_session_index > len(sessions):
        raise ValueError("V4-C boundary exceeds official calendar")
    max_date = pd.Timestamp(sessions[max_signal_session_index - 1])

    data = panel.copy()
    data["ticker"] = (
        data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    data["date"] = (
        pd.to_datetime(data["date"], errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    if data["date"].isna().any():
        raise ValueError("V4-C panel contains invalid dates")
    data = data[data["date"] <= max_date].copy()
    if data.empty:
        raise ValueError("V4-C bounded panel is empty")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("V4-C panel contains duplicate ticker/date rows")
    if "tradability_state" in data.columns:
        state = data["tradability_state"].astype(str).str.upper()
        if not state.eq("ACTIVE").all():
            raise ValueError("V4-C signal-research panel must contain ACTIVE rows only")

    baseline = build_baseline_features(data, sessions)
    baseline = baseline[baseline["date"] <= max_date].copy()
    if baseline.empty:
        raise RuntimeError("V4-C baseline reconstruction is empty")

    primary = baseline[baseline["universe_primary_liquid"].astype(bool)].copy()
    if primary.empty:
        raise RuntimeError("V4-C baseline reconstruction has no primary-liquid rows")

    index_by_date = {pd.Timestamp(day): idx + 1 for idx, day in enumerate(sessions)}
    rows: list[dict[str, object]] = []
    for date, block in primary.groupby("date", sort=True):
        date = pd.Timestamp(date)
        signal_session_index = index_by_date.get(date)
        if signal_session_index is None or signal_session_index > max_signal_session_index:
            continue
        rows.append(
            {
                "date": date,
                "signal_session_index": int(signal_session_index),
                "v4c_primary_liquid_count": int(len(block)),
                V4_C_FEATURE_COLUMNS[0]: _iqr(block[_SOURCE_FEATURES[0]]),
                V4_C_FEATURE_COLUMNS[1]: _iqr(block[_SOURCE_FEATURES[1]]),
                V4_C_FEATURE_COLUMNS[2]: _iqr(block[_SOURCE_FEATURES[2]]),
                V4_C_FEATURE_COLUMNS[3]: _iqr(block[_SOURCE_FEATURES[3]]),
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        raise RuntimeError("V4-C context builder produced no dates")
    if result["date"].duplicated().any():
        raise RuntimeError("V4-C context builder produced duplicate dates")
    if int(result["signal_session_index"].max()) > int(max_signal_session_index):
        raise RuntimeError("V4-C context builder escaped frozen historical boundary")

    for column in V4_C_FEATURE_COLUMNS:
        values = pd.to_numeric(result[column], errors="coerce").astype(float)
        if np.isinf(values.to_numpy(dtype=float)).any():
            raise RuntimeError(f"V4-C context feature contains infinity: {column}")
        observed = values.dropna()
        if (observed < 0.0).any():
            raise RuntimeError(f"V4-C IQR feature became negative: {column}")
        result[column] = values

    return result.sort_values("signal_session_index", kind="mergesort").reset_index(drop=True)
