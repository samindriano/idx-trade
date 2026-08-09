from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


TP_FIRST = "TP_FIRST"
SL_FIRST = "SL_FIRST"
AMBIGUOUS_SAME_BAR = "AMBIGUOUS_SAME_BAR"
NO_BARRIER_HIT = "NO_BARRIER_HIT"
UNRESOLVED_PATH = "UNRESOLVED_PATH"
UNRESOLVED_HORIZON_END = "UNRESOLVED_HORIZON_END"
INVALID_BARRIER = "INVALID_BARRIER"


@dataclass(frozen=True)
class BarrierLabelConfig:
    horizon: int = 10
    atr_window: int = 14
    sl_atr_multiple: float = 1.0
    reward_risk: float = 1.5

    def validate(self) -> None:
        if self.horizon <= 0:
            raise ValueError("horizon must be positive")
        if self.atr_window <= 1:
            raise ValueError("atr_window must exceed one observation")
        if self.sl_atr_multiple <= 0:
            raise ValueError("sl_atr_multiple must be positive")
        if self.reward_risk <= 0:
            raise ValueError("reward_risk must be positive")


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


def _prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", "high", "low", "close", "volume"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"signal panel missing columns: {sorted(missing)}")
    data = panel.copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if data["date"].isna().any():
        raise ValueError("signal panel contains invalid dates")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("signal panel contains duplicate ticker/date rows")
    numeric = data[["high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or not (numeric > 0).all().all():
        raise ValueError("signal panel contains invalid HLCV")
    if not (
        (numeric["high"] >= numeric[["low", "close"]].max(axis=1))
        & (numeric["low"] <= numeric[["high", "close"]].min(axis=1))
    ).all():
        raise ValueError("signal panel contains invalid HLC envelope")
    for column in numeric:
        data[column] = numeric[column]
    return data.sort_values(["ticker", "date"]).reset_index(drop=True)


def add_causal_atr(panel: pd.DataFrame, *, window: int = 14) -> pd.DataFrame:
    """Add right-aligned ATR using only observed ACTIVE bars through each row."""

    if window <= 1:
        raise ValueError("window must exceed one")
    data = _prepare_panel(panel)
    pieces: list[pd.DataFrame] = []
    for _, group in data.groupby("ticker", sort=False):
        frame = group.copy()
        previous_close = frame["close"].shift(1)
        true_range = pd.concat(
            [
                frame["high"] - frame["low"],
                (frame["high"] - previous_close).abs(),
                (frame["low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1, skipna=True)
        frame["true_range"] = true_range
        frame[f"atr{window}"] = true_range.rolling(window=window, min_periods=window).mean()
        pieces.append(frame)
    return pd.concat(pieces, ignore_index=True, sort=False).sort_values(["ticker", "date"]).reset_index(drop=True)


def build_first_touch_labels(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    config: BarrierLabelConfig | None = None,
    max_signal_session_index: int | None = None,
    max_future_session_index: int | None = None,
) -> pd.DataFrame:
    """Build the frozen first-touch research label in official-session space.

    The function never uses Open. A resolved barrier/no-touch label requires the
    full future official-session path through H to be present as ACTIVE signal
    rows. Any missing future official session fails closed as UNRESOLVED_PATH.

    `max_signal_session_index` and `max_future_session_index` are one-based hard
    access bounds. Stage-3 development uses them to make accidental locked-
    holdout outcome inspection impossible even when the immutable 1260 panel is
    supplied as the source table.
    """

    cfg = config or BarrierLabelConfig()
    cfg.validate()
    sessions = _sessions(official_sessions)
    if max_signal_session_index is not None and not 1 <= max_signal_session_index <= len(sessions):
        raise ValueError("max_signal_session_index is outside the official calendar")
    if max_future_session_index is not None and not 1 <= max_future_session_index <= len(sessions):
        raise ValueError("max_future_session_index is outside the official calendar")
    session_index = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    data = add_causal_atr(panel, window=cfg.atr_window)
    unknown_dates = sorted(set(data["date"]) - set(sessions))
    if unknown_dates:
        raise ValueError(f"panel dates absent from official calendar: {unknown_dates[:3]}")

    rows: list[dict[str, object]] = []
    atr_column = f"atr{cfg.atr_window}"
    for ticker, group in data.groupby("ticker", sort=False):
        lookup = group.set_index("date", drop=False)
        for record in group.itertuples(index=False):
            day = pd.Timestamp(record.date)
            signal_idx = session_index[day]
            signal_one_based = signal_idx + 1
            if max_signal_session_index is not None and signal_one_based > max_signal_session_index:
                continue
            reference = float(record.close)
            atr = getattr(record, atr_column)
            base = {
                "ticker": ticker,
                "signal_date": day,
                "signal_session_index": signal_one_based,
                "signal_reference_close": reference,
                "atr": float(atr) if pd.notna(atr) else np.nan,
                "horizon": cfg.horizon,
                "sl_atr_multiple": cfg.sl_atr_multiple,
                "reward_risk": cfg.reward_risk,
                "tp_level": np.nan,
                "sl_level": np.nan,
                "label_status": INVALID_BARRIER,
                "binary_target": np.nan,
                "first_barrier_date": pd.NaT,
                "path_complete": False,
                "mfe_h": np.nan,
                "mae_h": np.nan,
                "normalized_close_return_h": np.nan,
                "research_r_h": np.nan,
                "unresolved_date": pd.NaT,
            }
            if pd.isna(atr) or float(atr) <= 0:
                rows.append(base)
                continue
            sl_distance = cfg.sl_atr_multiple * float(atr)
            sl_level = reference - sl_distance
            tp_level = reference + cfg.reward_risk * sl_distance
            base["sl_level"] = sl_level
            base["tp_level"] = tp_level
            if sl_level <= 0 or tp_level <= reference:
                rows.append(base)
                continue
            future_end_one_based = signal_one_based + cfg.horizon
            if max_future_session_index is not None and future_end_one_based > max_future_session_index:
                raise RuntimeError(
                    "label request crosses the configured future-session access boundary: "
                    f"signal={signal_one_based}, horizon={cfg.horizon}, max_future={max_future_session_index}"
                )
            if signal_idx + cfg.horizon >= len(sessions):
                base["label_status"] = UNRESOLVED_HORIZON_END
                rows.append(base)
                continue

            future_dates = sessions[signal_idx + 1 : signal_idx + cfg.horizon + 1]
            if any(pd.Timestamp(future) not in lookup.index for future in future_dates):
                missing = next(pd.Timestamp(future) for future in future_dates if pd.Timestamp(future) not in lookup.index)
                base["label_status"] = UNRESOLVED_PATH
                base["unresolved_date"] = missing
                rows.append(base)
                continue

            path = lookup.loc[list(future_dates)].copy()
            base["path_complete"] = True
            first_status = NO_BARRIER_HIT
            first_date = pd.NaT
            for future in path.itertuples(index=False):
                tp_hit = float(future.high) >= tp_level
                sl_hit = float(future.low) <= sl_level
                if tp_hit and sl_hit:
                    first_status = AMBIGUOUS_SAME_BAR
                    first_date = pd.Timestamp(future.date)
                    break
                if tp_hit:
                    first_status = TP_FIRST
                    first_date = pd.Timestamp(future.date)
                    break
                if sl_hit:
                    first_status = SL_FIRST
                    first_date = pd.Timestamp(future.date)
                    break

            base["label_status"] = first_status
            base["first_barrier_date"] = first_date
            if first_status == TP_FIRST:
                base["binary_target"] = 1.0
            elif first_status == SL_FIRST:
                base["binary_target"] = 0.0

            base["mfe_h"] = float((path["high"].max() / reference) - 1.0)
            base["mae_h"] = float((path["low"].min() / reference) - 1.0)
            terminal_close = float(path.iloc[-1]["close"])
            base["normalized_close_return_h"] = float((terminal_close / reference) - 1.0)
            base["research_r_h"] = float((terminal_close - reference) / sl_distance)
            rows.append(base)

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    if result.duplicated(["ticker", "signal_date"]).any():
        raise RuntimeError("label pipeline produced duplicate ticker/signal_date rows")
    return result.sort_values(["signal_date", "ticker"]).reset_index(drop=True)


def binary_label_view(labels: pd.DataFrame) -> pd.DataFrame:
    """Return only pre-registered TP_FIRST/SL_FIRST observations."""

    required = {"label_status", "binary_target", "ticker", "signal_date"}
    if not required.issubset(labels.columns):
        raise ValueError("label table is missing required columns")
    resolved = labels[labels["label_status"].isin([TP_FIRST, SL_FIRST])].copy()
    if resolved["binary_target"].isna().any():
        raise RuntimeError("resolved binary labels contain null targets")
    return resolved.reset_index(drop=True)
