from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


SHORT_WINDOW = 5
MEDIUM_WINDOW = 20
MIN_MEDIUM_CLV_OBSERVATIONS = 10
EXTREME_CLV_THRESHOLD = 0.5

V4_B1_FEATURE_COLUMNS = (
    "v4b_path_efficiency_5",
    "v4b_path_efficiency_20",
    "v4b_largest_move_share_20",
)

V4_B2_FEATURE_COLUMNS = (
    "v4b_range_acceptance_mean_5",
    "v4b_range_acceptance_mean_20",
    "v4b_extreme_close_balance_5",
)

V4_B_FEATURE_COLUMNS = (*V4_B1_FEATURE_COLUMNS, *V4_B2_FEATURE_COLUMNS)

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


def _finite_positive(value: float) -> bool:
    return bool(np.isfinite(value) and value > 0.0)


def _exact_positions(by_session: dict[int, int], sessions: range) -> np.ndarray | None:
    positions = [by_session.get(int(value)) for value in sessions]
    if any(value is None for value in positions):
        return None
    return np.asarray([int(value) for value in positions], dtype=int)


def _positions_in_window(session_index: np.ndarray, start: int, end: int) -> np.ndarray:
    return np.flatnonzero((session_index >= int(start)) & (session_index <= int(end)))


def _path_metrics(close_values: np.ndarray) -> tuple[float, float]:
    if len(close_values) < 2:
        return np.nan, np.nan
    if not np.isfinite(close_values).all() or not (close_values > 0.0).all():
        return np.nan, np.nan
    log_returns = np.diff(np.log(close_values.astype(float)))
    if not np.isfinite(log_returns).all():
        return np.nan, np.nan
    gross = float(np.abs(log_returns).sum())
    if gross == 0.0:
        return 0.0, 0.0
    efficiency = float(abs(float(log_returns.sum())) / gross)
    largest_share = float(np.abs(log_returns).max() / gross)
    return efficiency, largest_share


def _price_path_for_ticker(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.sort_values("signal_session_index", kind="mergesort").reset_index(drop=True).copy()
    session_index = pd.to_numeric(work["signal_session_index"], errors="raise").to_numpy(dtype=int)
    if len(session_index) > 1 and np.any(np.diff(session_index) <= 0):
        raise ValueError("V4-B ticker sessions must be strictly increasing")

    high = pd.to_numeric(work["high"], errors="coerce").to_numpy(dtype=float)
    low = pd.to_numeric(work["low"], errors="coerce").to_numpy(dtype=float)
    close = pd.to_numeric(work["close"], errors="coerce").to_numpy(dtype=float)
    by_session = {int(value): pos for pos, value in enumerate(session_index)}
    n = len(work)

    clv = np.full(n, np.nan, dtype=float)
    valid_bar = (
        np.isfinite(high)
        & np.isfinite(low)
        & np.isfinite(close)
        & (high > 0.0)
        & (low > 0.0)
        & (close > 0.0)
        & (high >= low)
        & (close >= low)
        & (close <= high)
    )
    nonzero_range = valid_bar & (high > low)
    clv[nonzero_range] = (
        2.0 * close[nonzero_range] - high[nonzero_range] - low[nonzero_range]
    ) / (high[nonzero_range] - low[nonzero_range])
    finite_clv = np.isfinite(clv)
    clv[finite_clv] = np.clip(clv[finite_clv], -1.0, 1.0)

    path_efficiency_5 = np.full(n, np.nan, dtype=float)
    path_efficiency_20 = np.full(n, np.nan, dtype=float)
    largest_move_share_20 = np.full(n, np.nan, dtype=float)
    range_acceptance_mean_5 = np.full(n, np.nan, dtype=float)
    range_acceptance_mean_20 = np.full(n, np.nan, dtype=float)
    extreme_close_balance_5 = np.full(n, np.nan, dtype=float)

    for pos, current_session in enumerate(session_index):
        s = int(current_session)

        exact6 = _exact_positions(by_session, range(s - SHORT_WINDOW, s + 1))
        if exact6 is not None:
            efficiency, _ = _path_metrics(close[exact6])
            path_efficiency_5[pos] = efficiency

        exact21 = _exact_positions(by_session, range(s - MEDIUM_WINDOW, s + 1))
        if exact21 is not None:
            efficiency, largest_share = _path_metrics(close[exact21])
            path_efficiency_20[pos] = efficiency
            largest_move_share_20[pos] = largest_share

        exact5 = _exact_positions(by_session, range(s - SHORT_WINDOW + 1, s + 1))
        if exact5 is not None:
            five_clv = clv[exact5]
            if np.isfinite(five_clv).all():
                range_acceptance_mean_5[pos] = float(np.mean(five_clv))
                mapped = np.where(
                    five_clv >= EXTREME_CLV_THRESHOLD,
                    1.0,
                    np.where(five_clv <= -EXTREME_CLV_THRESHOLD, -1.0, 0.0),
                )
                extreme_close_balance_5[pos] = float(np.mean(mapped))

        medium = _positions_in_window(session_index, s - MEDIUM_WINDOW + 1, s)
        valid_medium = clv[medium][np.isfinite(clv[medium])]
        if len(valid_medium) >= MIN_MEDIUM_CLV_OBSERVATIONS:
            range_acceptance_mean_20[pos] = float(np.mean(valid_medium))

    result = work[["ticker", "date", "signal_session_index"]].copy()
    result[V4_B1_FEATURE_COLUMNS[0]] = path_efficiency_5
    result[V4_B1_FEATURE_COLUMNS[1]] = path_efficiency_20
    result[V4_B1_FEATURE_COLUMNS[2]] = largest_move_share_20
    result[V4_B2_FEATURE_COLUMNS[0]] = range_acceptance_mean_5
    result[V4_B2_FEATURE_COLUMNS[1]] = range_acceptance_mean_20
    result[V4_B2_FEATURE_COLUMNS[2]] = extreme_close_balance_5
    return result


def build_price_path_features(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    max_signal_session_index: int,
) -> pd.DataFrame:
    """Build the frozen causal V4-B1/B2 price-path feature families."""

    required = {"ticker", "date", "high", "low", "close"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"V4-B panel missing columns: {sorted(missing)}")
    present_forbidden = [
        column
        for column in panel.columns
        if any(token in str(column).lower() for token in _FORBIDDEN_TOKENS)
    ]
    if present_forbidden:
        raise ValueError(
            "V4-B feature builder must not receive label/outcome columns: "
            f"{sorted(present_forbidden)}"
        )
    if max_signal_session_index <= 0:
        raise ValueError("max_signal_session_index must be positive")

    sessions = normalize_official_sessions(official_sessions)
    if max_signal_session_index > len(sessions):
        raise ValueError("V4-B boundary exceeds official calendar")
    index_by_date = {pd.Timestamp(day): idx + 1 for idx, day in enumerate(sessions)}

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
        raise ValueError("V4-B panel contains invalid dates")
    data["signal_session_index"] = data["date"].map(index_by_date)
    if data["signal_session_index"].isna().any():
        raise ValueError("V4-B panel has dates outside official calendar")
    data["signal_session_index"] = data["signal_session_index"].astype(int)
    data = data[data["signal_session_index"] <= int(max_signal_session_index)].copy()
    if data.empty:
        raise ValueError("V4-B panel is empty inside boundary")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("V4-B panel contains duplicate ticker/date rows")
    if "tradability_state" in data.columns:
        state = data["tradability_state"].astype(str).str.upper()
        if not state.eq("ACTIVE").all():
            raise ValueError("V4-B signal-research panel must contain ACTIVE rows only")

    for column in ("high", "low", "close"):
        values = pd.to_numeric(data[column], errors="coerce")
        if (values.dropna() <= 0.0).any():
            raise ValueError(f"V4-B panel contains non-positive {column}")
    high = pd.to_numeric(data["high"], errors="coerce")
    low = pd.to_numeric(data["low"], errors="coerce")
    close = pd.to_numeric(data["close"], errors="coerce")
    if (high.notna() & low.notna() & (high < low)).any():
        raise ValueError("V4-B panel contains high below low")
    invalid_close = high.notna() & low.notna() & close.notna() & ((close < low) | (close > high))
    if invalid_close.any():
        raise ValueError("V4-B panel contains close outside high-low range")

    pieces = [_price_path_for_ticker(group) for _, group in data.groupby("ticker", sort=True)]
    result = pd.concat(pieces, ignore_index=True, sort=False)
    if result.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V4-B builder produced duplicate ticker/date rows")
    if int(result["signal_session_index"].max()) > int(max_signal_session_index):
        raise RuntimeError("V4-B builder escaped frozen boundary")

    for column in V4_B_FEATURE_COLUMNS:
        values = pd.to_numeric(result[column], errors="coerce").astype(float)
        if np.isinf(values.to_numpy(dtype=float)).any():
            raise RuntimeError(f"V4-B feature contains infinity: {column}")
        result[column] = values

    for column in V4_B1_FEATURE_COLUMNS:
        observed = result[column].dropna()
        if ((observed < -1e-12) | (observed > 1.0 + 1e-12)).any():
            raise RuntimeError(f"V4-B B1 feature escaped [0,1]: {column}")
    for column in V4_B2_FEATURE_COLUMNS:
        observed = result[column].dropna()
        if ((observed < -1.0 - 1e-12) | (observed > 1.0 + 1e-12)).any():
            raise RuntimeError(f"V4-B B2 feature escaped [-1,1]: {column}")

    return result.sort_values(
        ["signal_session_index", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
