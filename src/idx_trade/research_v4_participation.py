from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


PRIOR_BASELINE_LOOKBACK = 20
MIN_BASELINE_OBSERVATIONS = 10
SHORT_WINDOW = 5
MEDIUM_WINDOW = 20
MIN_MEDIUM_SIGNED_OBSERVATIONS = 10
_LOG2 = float(np.log(2.0))

V4_A1_FEATURE_COLUMNS = (
    "v4a_range_impact_logrel20",
    "v4a_close_impact_logrel20",
    "v4a_high_range_impact_fraction_5",
)

V4_A2_FEATURE_COLUMNS = (
    "v4a_value_persistence_fraction_5",
    "v4a_value_acceleration_log_5v20",
    "v4a_signed_value_5",
    "v4a_signed_value_20",
)

V4_A_FEATURE_COLUMNS = (*V4_A1_FEATURE_COLUMNS, *V4_A2_FEATURE_COLUMNS)

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


def _centered_log_ratio(current: float, baseline: float) -> float:
    if not (np.isfinite(current) and current >= 0.0 and _finite_positive(baseline)):
        return np.nan
    return float(np.log1p(float(current) / float(baseline)) - _LOG2)


def _positions_in_window(session_index: np.ndarray, start: int, end: int) -> np.ndarray:
    return np.flatnonzero((session_index >= int(start)) & (session_index <= int(end)))


def _positive_median(values: np.ndarray, *, minimum: int) -> float:
    valid = values[np.isfinite(values) & (values > 0.0)]
    if len(valid) < int(minimum):
        return np.nan
    result = float(np.median(valid))
    return result if _finite_positive(result) else np.nan


def _exact_positions(by_session: dict[int, int], sessions: range) -> np.ndarray | None:
    positions = [by_session.get(int(value)) for value in sessions]
    if any(value is None for value in positions):
        return None
    return np.asarray([int(value) for value in positions], dtype=int)


def _participation_for_ticker(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.sort_values("signal_session_index", kind="mergesort").reset_index(drop=True).copy()
    session_index = pd.to_numeric(work["signal_session_index"], errors="raise").to_numpy(dtype=int)
    if len(session_index) > 1 and np.any(np.diff(session_index) <= 0):
        raise ValueError("V4-A ticker sessions must be strictly increasing")

    high = pd.to_numeric(work["high"], errors="coerce").to_numpy(dtype=float)
    low = pd.to_numeric(work["low"], errors="coerce").to_numpy(dtype=float)
    close = pd.to_numeric(work["close"], errors="coerce").to_numpy(dtype=float)
    value = pd.to_numeric(work["regular_market_value"], errors="coerce").to_numpy(dtype=float)
    by_session = {int(value_): pos for pos, value_ in enumerate(session_index)}
    n = len(work)

    range_pct = np.full(n, np.nan, dtype=float)
    valid_range = (
        np.isfinite(high)
        & np.isfinite(low)
        & np.isfinite(close)
        & (high > 0.0)
        & (low > 0.0)
        & (close > 0.0)
        & (high >= low)
    )
    range_pct[valid_range] = (high[valid_range] - low[valid_range]) / close[valid_range]

    cc_return = np.full(n, np.nan, dtype=float)
    for pos, current_session in enumerate(session_index):
        prior_pos = by_session.get(int(current_session) - 1)
        if prior_pos is None:
            continue
        if _finite_positive(close[pos]) and _finite_positive(close[prior_pos]):
            cc_return[pos] = float(close[pos] / close[prior_pos] - 1.0)

    valid_value = np.isfinite(value) & (value > 0.0)
    range_impact = np.full(n, np.nan, dtype=float)
    close_impact = np.full(n, np.nan, dtype=float)
    range_mask = valid_value & np.isfinite(range_pct) & (range_pct >= 0.0)
    close_mask = valid_value & np.isfinite(cc_return)
    range_impact[range_mask] = range_pct[range_mask] / value[range_mask]
    close_impact[close_mask] = np.abs(cc_return[close_mask]) / value[close_mask]

    baseline_value = np.full(n, np.nan, dtype=float)
    baseline_range_impact = np.full(n, np.nan, dtype=float)
    baseline_close_impact = np.full(n, np.nan, dtype=float)
    value_high_flag = np.full(n, np.nan, dtype=float)
    range_impact_high_flag = np.full(n, np.nan, dtype=float)

    for pos, current_session in enumerate(session_index):
        prior = _positions_in_window(
            session_index,
            int(current_session) - PRIOR_BASELINE_LOOKBACK,
            int(current_session) - 1,
        )
        if len(prior):
            baseline_value[pos] = _positive_median(
                value[prior], minimum=MIN_BASELINE_OBSERVATIONS
            )
            baseline_range_impact[pos] = _positive_median(
                range_impact[prior], minimum=MIN_BASELINE_OBSERVATIONS
            )
            baseline_close_impact[pos] = _positive_median(
                close_impact[prior], minimum=MIN_BASELINE_OBSERVATIONS
            )
        if valid_value[pos] and _finite_positive(baseline_value[pos]):
            value_high_flag[pos] = float(value[pos] > baseline_value[pos])
        if np.isfinite(range_impact[pos]) and _finite_positive(baseline_range_impact[pos]):
            range_impact_high_flag[pos] = float(
                range_impact[pos] > baseline_range_impact[pos]
            )

    range_impact_logrel = np.asarray(
        [
            _centered_log_ratio(current, baseline)
            for current, baseline in zip(range_impact, baseline_range_impact, strict=True)
        ],
        dtype=float,
    )
    close_impact_logrel = np.asarray(
        [
            _centered_log_ratio(current, baseline)
            for current, baseline in zip(close_impact, baseline_close_impact, strict=True)
        ],
        dtype=float,
    )

    high_range_fraction_5 = np.full(n, np.nan, dtype=float)
    value_persistence_5 = np.full(n, np.nan, dtype=float)
    value_acceleration_5v20 = np.full(n, np.nan, dtype=float)
    signed_value_5 = np.full(n, np.nan, dtype=float)
    signed_value_20 = np.full(n, np.nan, dtype=float)

    signed_component = np.full(n, np.nan, dtype=float)
    signed_valid = valid_value & np.isfinite(cc_return)
    signed_component[signed_valid] = np.sign(cc_return[signed_valid]) * value[signed_valid]

    for pos, current_session in enumerate(session_index):
        s = int(current_session)
        exact5 = _exact_positions(by_session, range(s - SHORT_WINDOW + 1, s + 1))
        if exact5 is not None:
            impact_flags = range_impact_high_flag[exact5]
            if np.isfinite(impact_flags).all():
                high_range_fraction_5[pos] = float(np.mean(impact_flags))

            value_flags = value_high_flag[exact5]
            if np.isfinite(value_flags).all():
                value_persistence_5[pos] = float(np.mean(value_flags))

            short_values = value[exact5]
            if np.isfinite(short_values).all() and (short_values > 0.0).all():
                older = _positions_in_window(session_index, s - 24, s - 5)
                older_median = _positive_median(
                    value[older], minimum=MIN_BASELINE_OBSERVATIONS
                )
                short_median = float(np.median(short_values))
                if _finite_positive(short_median) and _finite_positive(older_median):
                    value_acceleration_5v20[pos] = float(
                        np.log(short_median / older_median)
                    )

            five_signed = signed_component[exact5]
            five_values = value[exact5]
            if (
                np.isfinite(five_signed).all()
                and np.isfinite(five_values).all()
                and (five_values > 0.0).all()
                and float(five_values.sum()) > 0.0
            ):
                signed_value_5[pos] = float(five_signed.sum() / five_values.sum())

        medium = _positions_in_window(session_index, s - MEDIUM_WINDOW + 1, s)
        medium_mask = (
            np.isfinite(signed_component[medium])
            & np.isfinite(value[medium])
            & (value[medium] > 0.0)
        )
        if int(medium_mask.sum()) >= MIN_MEDIUM_SIGNED_OBSERVATIONS:
            medium_signed = signed_component[medium][medium_mask]
            medium_values = value[medium][medium_mask]
            denominator = float(medium_values.sum())
            if denominator > 0.0:
                signed_value_20[pos] = float(medium_signed.sum() / denominator)

    result = work[["ticker", "date", "signal_session_index"]].copy()
    result[V4_A1_FEATURE_COLUMNS[0]] = range_impact_logrel
    result[V4_A1_FEATURE_COLUMNS[1]] = close_impact_logrel
    result[V4_A1_FEATURE_COLUMNS[2]] = high_range_fraction_5
    result[V4_A2_FEATURE_COLUMNS[0]] = value_persistence_5
    result[V4_A2_FEATURE_COLUMNS[1]] = value_acceleration_5v20
    result[V4_A2_FEATURE_COLUMNS[2]] = signed_value_5
    result[V4_A2_FEATURE_COLUMNS[3]] = signed_value_20
    return result


def build_participation_quality_features(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    max_signal_session_index: int,
) -> pd.DataFrame:
    """Build the frozen V4-A1/A2 causal participation feature families."""

    required = {
        "ticker",
        "date",
        "high",
        "low",
        "close",
        "regular_market_value",
    }
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"V4-A panel missing columns: {sorted(missing)}")
    present_forbidden = [
        column
        for column in panel.columns
        if any(token in str(column).lower() for token in _FORBIDDEN_TOKENS)
    ]
    if present_forbidden:
        raise ValueError(
            "V4-A feature builder must not receive label/outcome columns: "
            f"{sorted(present_forbidden)}"
        )
    if max_signal_session_index <= 0:
        raise ValueError("max_signal_session_index must be positive")

    sessions = normalize_official_sessions(official_sessions)
    if max_signal_session_index > len(sessions):
        raise ValueError("V4-A boundary exceeds official calendar")
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
        raise ValueError("V4-A panel contains invalid dates")
    data["signal_session_index"] = data["date"].map(index_by_date)
    if data["signal_session_index"].isna().any():
        raise ValueError("V4-A panel has dates outside official calendar")
    data["signal_session_index"] = data["signal_session_index"].astype(int)
    data = data[data["signal_session_index"] <= int(max_signal_session_index)].copy()
    if data.empty:
        raise ValueError("V4-A panel is empty inside boundary")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("V4-A panel contains duplicate ticker/date rows")
    if "tradability_state" in data.columns:
        state = data["tradability_state"].astype(str).str.upper()
        if not state.eq("ACTIVE").all():
            raise ValueError("V4-A signal-research panel must contain ACTIVE rows only")

    for column in ("high", "low", "close"):
        values = pd.to_numeric(data[column], errors="coerce")
        if (values.dropna() <= 0.0).any():
            raise ValueError(f"V4-A panel contains non-positive {column}")
    market_value = pd.to_numeric(data["regular_market_value"], errors="coerce")
    if (market_value.dropna() < 0.0).any():
        raise ValueError("V4-A panel contains negative regular_market_value")
    high = pd.to_numeric(data["high"], errors="coerce")
    low = pd.to_numeric(data["low"], errors="coerce")
    if (high.notna() & low.notna() & (high < low)).any():
        raise ValueError("V4-A panel contains high below low")

    pieces = [
        _participation_for_ticker(group)
        for _, group in data.groupby("ticker", sort=True)
    ]
    result = pd.concat(pieces, ignore_index=True, sort=False)
    if result.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V4-A builder produced duplicate ticker/date rows")
    if int(result["signal_session_index"].max()) > int(max_signal_session_index):
        raise RuntimeError("V4-A builder escaped frozen boundary")

    for column in V4_A_FEATURE_COLUMNS:
        values = pd.to_numeric(result[column], errors="coerce").astype(float)
        if np.isinf(values.to_numpy(dtype=float)).any():
            raise RuntimeError(f"V4-A feature contains infinity: {column}")
        result[column] = values

    for column in (
        "v4a_high_range_impact_fraction_5",
        "v4a_value_persistence_fraction_5",
    ):
        observed = result[column].dropna()
        if ((observed < 0.0) | (observed > 1.0)).any():
            raise RuntimeError(f"V4-A fraction escaped [0,1]: {column}")
    for column in ("v4a_signed_value_5", "v4a_signed_value_20"):
        observed = result[column].dropna()
        if ((observed < -1.0 - 1e-12) | (observed > 1.0 + 1e-12)).any():
            raise RuntimeError(f"V4-A signed value escaped [-1,1]: {column}")

    return result.sort_values(
        ["signal_session_index", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
