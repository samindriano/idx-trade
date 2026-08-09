from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

from .research_labels import (
    AMBIGUOUS_SAME_BAR,
    INVALID_BARRIER,
    NO_BARRIER_HIT,
    SL_FIRST,
    TP_FIRST,
    UNRESOLVED_HORIZON_END,
    UNRESOLVED_PATH,
    BarrierLabelConfig,
    add_causal_atr,
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


def build_first_touch_labels_multi_horizon_fast(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    horizons: Iterable[int] = (5, 10, 20),
    atr_window: int = 14,
    sl_atr_multiple: float = 1.0,
    reward_risk: float = 1.5,
    max_signal_session_index_by_horizon: Mapping[int, int] | None = None,
    max_future_session_index_by_horizon: Mapping[int, int] | None = None,
) -> dict[int, pd.DataFrame]:
    """Vectorized candidate for the frozen first-touch label semantics.

    This function is performance-engineering code, not yet the authoritative
    label engine. It computes ATR once and reuses the same future-path scan for
    multiple horizons. Each ticker is processed independently with NumPy arrays
    and only the horizon loop remains in Python (normally <=20 iterations).

    The legacy `build_first_touch_labels` remains authoritative until a full
    frozen-panel equivalence run proves that every semantic output matches.
    """

    requested = sorted({int(h) for h in horizons})
    if not requested or requested[0] <= 0:
        raise ValueError("horizons must contain positive integers")
    for horizon in requested:
        BarrierLabelConfig(
            horizon=horizon,
            atr_window=atr_window,
            sl_atr_multiple=sl_atr_multiple,
            reward_risk=reward_risk,
        ).validate()

    sessions = _sessions(official_sessions)
    session_lookup = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    max_signal = dict(max_signal_session_index_by_horizon or {})
    max_future = dict(max_future_session_index_by_horizon or {})
    for horizon in requested:
        if horizon in max_signal and not 1 <= int(max_signal[horizon]) <= len(sessions):
            raise ValueError("max_signal_session_index is outside the official calendar")
        if horizon in max_future and not 1 <= int(max_future[horizon]) <= len(sessions):
            raise ValueError("max_future_session_index is outside the official calendar")

    data = add_causal_atr(panel, window=atr_window)
    unknown_dates = sorted(set(data["date"]) - set(sessions))
    if unknown_dates:
        raise ValueError(f"panel dates absent from official calendar: {unknown_dates[:3]}")

    atr_column = f"atr{atr_window}"
    pieces: dict[int, list[pd.DataFrame]] = {h: [] for h in requested}
    max_horizon = requested[-1]

    for ticker, group in data.groupby("ticker", sort=False):
        frame = group.sort_values("date").reset_index(drop=True)
        n = len(frame)
        if n == 0:
            continue

        dates = pd.DatetimeIndex(frame["date"])
        session_idx = np.asarray([session_lookup[pd.Timestamp(day)] for day in dates], dtype=np.int64)
        signal_one_based = session_idx + 1
        reference = frame["close"].to_numpy(dtype=float)
        high = frame["high"].to_numpy(dtype=float)
        low = frame["low"].to_numpy(dtype=float)
        close = frame["close"].to_numpy(dtype=float)
        atr = frame[atr_column].to_numpy(dtype=float)

        atr_valid = np.isfinite(atr) & (atr > 0.0)
        sl_distance = sl_atr_multiple * atr
        sl_level = reference - sl_distance
        tp_level = reference + reward_risk * sl_distance
        sl_output = np.where(atr_valid, sl_level, np.nan)
        tp_output = np.where(atr_valid, tp_level, np.nan)
        valid_barrier = atr_valid & (sl_level > 0.0) & (tp_level > reference)

        first_missing_step = np.zeros(n, dtype=np.int16)
        first_hit_step = np.zeros(n, dtype=np.int16)
        first_hit_code = np.zeros(n, dtype=np.int8)  # 0 none, 1 TP, 2 SL, 3 ambiguous
        future_high_max = np.full(n, np.nan, dtype=float)
        future_low_min = np.full(n, np.nan, dtype=float)

        for step in range(1, max_horizon + 1):
            exact = np.zeros(n, dtype=bool)
            shifted_high = np.full(n, np.nan, dtype=float)
            shifted_low = np.full(n, np.nan, dtype=float)
            shifted_close = np.full(n, np.nan, dtype=float)
            remaining = n - step
            if remaining > 0:
                exact[:remaining] = session_idx[step:] == (session_idx[:remaining] + step)
                shifted_high[:remaining] = high[step:]
                shifted_low[:remaining] = low[step:]
                shifted_close[:remaining] = close[step:]

            newly_missing = (first_missing_step == 0) & (~exact)
            first_missing_step[newly_missing] = step

            future_high_max = np.fmax(future_high_max, np.where(exact, shifted_high, np.nan))
            future_low_min = np.fmin(future_low_min, np.where(exact, shifted_low, np.nan))

            untouched = (first_hit_step == 0) & exact
            tp_hit = untouched & (shifted_high >= tp_level)
            sl_hit = untouched & (shifted_low <= sl_level)
            both = tp_hit & sl_hit
            tp_only = tp_hit & (~sl_hit)
            sl_only = sl_hit & (~tp_hit)
            first_hit_step[both | tp_only | sl_only] = step
            first_hit_code[both] = 3
            first_hit_code[tp_only] = 1
            first_hit_code[sl_only] = 2

            if step not in pieces:
                continue

            horizon = step
            selected = np.ones(n, dtype=bool)
            if horizon in max_signal:
                selected &= signal_one_based <= int(max_signal[horizon])
            if not selected.any():
                continue

            # Legacy access-boundary check occurs only after a valid barrier has
            # been formed and before the calendar-end/path checks.
            if horizon in max_future:
                crossing = selected & valid_barrier & ((signal_one_based + horizon) > int(max_future[horizon]))
                if crossing.any():
                    first_signal = int(signal_one_based[np.flatnonzero(crossing)[0]])
                    raise RuntimeError(
                        "label request crosses the configured future-session access boundary: "
                        f"signal={first_signal}, horizon={horizon}, max_future={int(max_future[horizon])}"
                    )

            status = np.full(n, INVALID_BARRIER, dtype=object)
            binary = np.full(n, np.nan, dtype=float)
            first_barrier_date = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
            unresolved_date = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
            path_complete = np.zeros(n, dtype=bool)
            mfe_h = np.full(n, np.nan, dtype=float)
            mae_h = np.full(n, np.nan, dtype=float)
            normalized_close_return_h = np.full(n, np.nan, dtype=float)
            research_r_h = np.full(n, np.nan, dtype=float)

            valid = valid_barrier.copy()
            horizon_end = valid & ((session_idx + horizon) >= len(sessions))
            status[horizon_end] = UNRESOLVED_HORIZON_END

            evaluable = valid & (~horizon_end)
            unresolved = evaluable & (first_missing_step > 0) & (first_missing_step <= horizon)
            status[unresolved] = UNRESOLVED_PATH
            if unresolved.any():
                unresolved_positions = np.flatnonzero(unresolved)
                missing_official_idx = session_idx[unresolved_positions] + first_missing_step[unresolved_positions]
                unresolved_date[unresolved_positions] = sessions.values[missing_official_idx]

            complete = evaluable & (~unresolved)
            path_complete[complete] = True
            no_hit = complete & ((first_hit_step == 0) | (first_hit_step > horizon))
            status[no_hit] = NO_BARRIER_HIT

            hit = complete & (first_hit_step > 0) & (first_hit_step <= horizon)
            tp = hit & (first_hit_code == 1)
            sl = hit & (first_hit_code == 2)
            ambiguous = hit & (first_hit_code == 3)
            status[tp] = TP_FIRST
            status[sl] = SL_FIRST
            status[ambiguous] = AMBIGUOUS_SAME_BAR
            binary[tp] = 1.0
            binary[sl] = 0.0

            if hit.any():
                hit_positions = np.flatnonzero(hit)
                barrier_official_idx = session_idx[hit_positions] + first_hit_step[hit_positions]
                first_barrier_date[hit_positions] = sessions.values[barrier_official_idx]

            terminal_close = shifted_close
            if complete.any():
                mfe_h[complete] = future_high_max[complete] / reference[complete] - 1.0
                mae_h[complete] = future_low_min[complete] / reference[complete] - 1.0
                normalized_close_return_h[complete] = terminal_close[complete] / reference[complete] - 1.0
                research_r_h[complete] = (terminal_close[complete] - reference[complete]) / sl_distance[complete]

            idx = np.flatnonzero(selected)
            result = pd.DataFrame(
                {
                    "ticker": np.repeat(str(ticker), len(idx)),
                    "signal_date": dates.values[idx],
                    "signal_session_index": signal_one_based[idx],
                    "signal_reference_close": reference[idx],
                    "atr": np.where(np.isfinite(atr[idx]), atr[idx], np.nan),
                    "horizon": np.repeat(horizon, len(idx)),
                    "sl_atr_multiple": np.repeat(sl_atr_multiple, len(idx)),
                    "reward_risk": np.repeat(reward_risk, len(idx)),
                    "tp_level": tp_output[idx],
                    "sl_level": sl_output[idx],
                    "label_status": status[idx],
                    "binary_target": binary[idx],
                    "first_barrier_date": first_barrier_date[idx],
                    "path_complete": path_complete[idx],
                    "mfe_h": mfe_h[idx],
                    "mae_h": mae_h[idx],
                    "normalized_close_return_h": normalized_close_return_h[idx],
                    "research_r_h": research_r_h[idx],
                    "unresolved_date": unresolved_date[idx],
                }
            )
            pieces[horizon].append(result)

    outputs: dict[int, pd.DataFrame] = {}
    for horizon in requested:
        if not pieces[horizon]:
            outputs[horizon] = pd.DataFrame()
            continue
        result = pd.concat(pieces[horizon], ignore_index=True, sort=False)
        if result.duplicated(["ticker", "signal_date"]).any():
            raise RuntimeError("fast label pipeline produced duplicate ticker/signal_date rows")
        outputs[horizon] = result.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
    return outputs


def build_first_touch_labels_fast(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    config: BarrierLabelConfig | None = None,
    max_signal_session_index: int | None = None,
    max_future_session_index: int | None = None,
) -> pd.DataFrame:
    """Single-horizon compatibility wrapper around the vectorized candidate."""

    cfg = config or BarrierLabelConfig()
    cfg.validate()
    max_signal = None if max_signal_session_index is None else {cfg.horizon: max_signal_session_index}
    max_future = None if max_future_session_index is None else {cfg.horizon: max_future_session_index}
    return build_first_touch_labels_multi_horizon_fast(
        panel,
        official_sessions,
        horizons=(cfg.horizon,),
        atr_window=cfg.atr_window,
        sl_atr_multiple=cfg.sl_atr_multiple,
        reward_risk=cfg.reward_risk,
        max_signal_session_index_by_horizon=max_signal,
        max_future_session_index_by_horizon=max_future,
    )[cfg.horizon]
