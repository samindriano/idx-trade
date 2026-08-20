from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

WINDOW_SPECS = {
    "lag5": ("lag", 5),
    "lag20": ("lag", 20),
    "atr14": ("rolling", 14),
    "rolling20": ("rolling", 20),
    "rolling60": ("rolling", 60),
}


def normalize_ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def normalize_date(series: pd.Series, label: str) -> pd.Series:
    out = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if out.isna().any():
        raise ValueError(f"{label} contains invalid dates")
    return out


def build_session_span_state(panel: pd.DataFrame, official_sessions: Iterable[object]) -> pd.DataFrame:
    required = {"ticker", "date"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")

    sessions = pd.DatetimeIndex(pd.to_datetime(list(official_sessions), errors="coerce"))
    sessions = sessions.tz_localize(None).normalize().dropna().unique().sort_values()
    if not len(sessions):
        raise ValueError("official_sessions must not be empty")
    index_by_date = {pd.Timestamp(day): i for i, day in enumerate(sessions)}

    data = panel[["ticker", "date"]].copy()
    data["ticker"] = normalize_ticker(data["ticker"])
    data["date"] = normalize_date(data["date"], "panel.date")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("panel contains duplicate ticker/date")
    data["session_index"] = data["date"].map(index_by_date)
    if data["session_index"].isna().any():
        raise ValueError("panel contains dates outside official calendar")
    data["session_index"] = data["session_index"].astype(int)
    data = data.sort_values(["ticker", "session_index"], kind="mergesort").reset_index(drop=True)

    pieces: list[pd.DataFrame] = []
    for _, group in data.groupby("ticker", sort=False):
        frame = group.copy()
        idx = frame["session_index"].astype(float)
        for name, (kind, nominal) in WINDOW_SPECS.items():
            shift_n = nominal if kind == "lag" else nominal - 1
            oldest = idx.shift(shift_n)
            if kind == "lag":
                effective = idx - oldest
            else:
                effective = idx - oldest + 1.0
            frame[f"{name}_effective_sessions"] = effective
        pieces.append(frame)
    return pd.concat(pieces, ignore_index=True).sort_values(
        ["date", "ticker"], kind="mergesort"
    ).reset_index(drop=True)


def summarize_window(frame: pd.DataFrame, name: str) -> dict[str, object]:
    if name not in WINDOW_SPECS:
        raise ValueError(f"unknown window: {name}")
    nominal = WINDOW_SPECS[name][1]
    column = f"{name}_effective_sessions"
    if column not in frame.columns:
        raise ValueError(f"missing span column: {column}")
    values = pd.to_numeric(frame[column], errors="coerce").astype(float)
    finite = values[np.isfinite(values)]
    extended = finite > float(nominal)
    exact = finite == float(nominal)
    return {
        "nominal_sessions": nominal,
        "support_rows": int(len(frame)),
        "observable_rows": int(len(finite)),
        "unavailable_rows": int(len(frame) - len(finite)),
        "exact_nominal_rows": int(exact.sum()),
        "extended_rows": int(extended.sum()),
        "extended_rate_observable": float(extended.mean()) if len(finite) else 0.0,
        "extended_tickers": int(frame.loc[values.gt(float(nominal)), "ticker"].nunique()),
        "extended_dates": int(frame.loc[values.gt(float(nominal)), "date"].nunique()),
        "p50_effective_sessions": float(finite.quantile(0.50)) if len(finite) else None,
        "p90_effective_sessions": float(finite.quantile(0.90)) if len(finite) else None,
        "p99_effective_sessions": float(finite.quantile(0.99)) if len(finite) else None,
        "max_effective_sessions": float(finite.max()) if len(finite) else None,
        "max_excess_sessions": float((finite - nominal).max()) if len(finite) else None,
    }


def summarize_support(frame: pd.DataFrame) -> dict[str, object]:
    return {
        "rows": int(len(frame)),
        "tickers": int(frame["ticker"].nunique()),
        "dates": int(frame["date"].nunique()),
        "windows": {name: summarize_window(frame, name) for name in WINDOW_SPECS},
    }


def subset_state(state: pd.DataFrame, keys: pd.DataFrame, label: str) -> pd.DataFrame:
    right = keys[["ticker", "date"]].copy()
    right["ticker"] = normalize_ticker(right["ticker"])
    right["date"] = normalize_date(right["date"], f"{label}.date")
    right = right.drop_duplicates(["ticker", "date"])
    out = right.merge(state, on=["ticker", "date"], how="left", validate="one_to_one")
    if out["session_index"].isna().any():
        missing = int(out["session_index"].isna().sum())
        raise RuntimeError(f"{label}_KEYS_NOT_IN_PANEL:{missing}")
    return out
