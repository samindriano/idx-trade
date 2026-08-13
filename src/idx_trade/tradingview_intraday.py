"""Timestamp-safe normalization used only by the TradingView audits."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
import math
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

import pandas as pd


WIB = ZoneInfo("Asia/Jakarta")
UTC = timezone.utc
EMPTY_COLUMNS = [
    "ticker", "symbol", "server", "phase", "era", "timeframe", "adjustment", "raw_epoch",
    "raw_timestamp_utc", "timestamp_wib", "session_date", "in_requested_window",
    "official_session_known", "within_time_band", "session_admissible", "open", "high", "low", "close", "volume",
]


def request_epochs(start: date, end: date) -> tuple[int, int]:
    start_dt = datetime(start.year, start.month, start.day, tzinfo=WIB)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=WIB)
    return int(start_dt.timestamp()), int(end_dt.timestamp())


def normalize_periods(
    periods: Iterable[Mapping[str, Any]],
    *,
    ticker: str,
    symbol: str,
    server: str,
    phase: str,
    era: str,
    timeframe: str,
    adjustment: str,
    requested_start: date,
    requested_end: date,
    official_sessions: set[date] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Preserve valid returned periods and expose, rather than hide, boundary flags."""
    daily = str(timeframe).upper() in {"D", "1D"}
    diag: dict[str, Any] = {
        "raw_rows": 0, "valid_rows": 0, "malformed_rows": 0, "duplicate_rows": 0,
        "invalid_ohlcv_rows": 0, "outside_requested_rows": 0, "off_session_rows": 0,
        "session_dates": [], "timezone_hours": [], "first_epoch": None, "last_epoch": None,
    }
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for period in periods:
        diag["raw_rows"] += 1
        try:
            epoch = int(period["time"])
            values = {field: float(period[field]) for field in ("open", "high", "low", "close", "volume")}
            if not math.isfinite(epoch) or any(not math.isfinite(value) for value in values.values()):
                raise ValueError("non-finite period")
        except (KeyError, TypeError, ValueError, OverflowError):
            diag["malformed_rows"] += 1
            continue
        if epoch in seen:
            diag["duplicate_rows"] += 1
            continue
        seen.add(epoch)
        timestamp_utc = datetime.fromtimestamp(epoch, tz=UTC)
        timestamp_wib = timestamp_utc.astimezone(WIB)
        in_requested = requested_start <= timestamp_wib.date() <= requested_end
        official_known = official_sessions is not None
        official_date = official_sessions is None or timestamp_wib.date() in official_sessions
        within_time_band = daily or (time(8, 0) <= timestamp_wib.time() <= time(16, 0))
        session_admissible = bool(official_date and within_time_band)
        if not in_requested:
            diag["outside_requested_rows"] += 1
        if not session_admissible:
            diag["off_session_rows"] += 1
        if (
            values["open"] <= 0 or values["high"] <= 0 or values["low"] <= 0 or values["close"] <= 0
            or values["volume"] < 0 or values["high"] < values["low"]
            or not values["low"] <= values["open"] <= values["high"]
            or not values["low"] <= values["close"] <= values["high"]
        ):
            diag["invalid_ohlcv_rows"] += 1
            continue
        rows.append({
            "ticker": ticker, "symbol": symbol, "server": server, "phase": phase, "era": era,
            "timeframe": str(timeframe), "adjustment": adjustment, "raw_epoch": epoch,
            "raw_timestamp_utc": timestamp_utc.isoformat(), "timestamp_wib": timestamp_wib.isoformat(),
            "session_date": timestamp_wib.date().isoformat(), "in_requested_window": in_requested,
            "official_session_known": official_known, "within_time_band": within_time_band,
            "session_admissible": session_admissible, **values,
        })
    frame = pd.DataFrame(rows, columns=EMPTY_COLUMNS)
    if not frame.empty:
        diag["valid_rows"] = len(frame)
        diag["session_dates"] = sorted(frame.loc[frame["in_requested_window"], "session_date"].unique().tolist())
        diag["timezone_hours"] = sorted(pd.to_datetime(frame["timestamp_wib"]).dt.hour.unique().tolist())
        diag["first_epoch"] = int(frame["raw_epoch"].min())
        diag["last_epoch"] = int(frame["raw_epoch"].max())
    return frame, diag


def aggregate_daily(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["ticker", "server", "phase", "era", "timeframe", "adjustment", "session_date", "open", "high", "low", "close", "volume", "bar_count"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    usable = frame[frame["in_requested_window"] & frame["session_admissible"]].copy()
    if usable.empty:
        return pd.DataFrame(columns=columns)
    ordered = usable.sort_values(["ticker", "server", "phase", "era", "timeframe", "adjustment", "session_date", "raw_epoch"])
    grouped = ordered.groupby(["ticker", "server", "phase", "era", "timeframe", "adjustment", "session_date"], sort=True)
    return grouped.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), volume=("volume", "sum"), bar_count=("raw_epoch", "size")).reset_index()


def compare_daily(provider: pd.DataFrame, canonical: pd.DataFrame, *, tolerance: float = 0.05) -> pd.DataFrame:
    if provider.empty or canonical.empty:
        return pd.DataFrame()
    left = provider.copy()
    right = canonical.copy()
    left["session_date"] = left["session_date"].astype(str)
    right["session_date"] = pd.to_datetime(right["date"]).dt.date.astype(str)
    right = right.rename(columns={"open": "open_canonical", "high": "high_canonical", "low": "low_canonical", "close": "close_canonical", "volume": "volume_canonical"})
    keys = ["ticker", "session_date"]
    merged = left.merge(right[keys + ["open_canonical", "high_canonical", "low_canonical", "close_canonical", "volume_canonical"]], on=keys, how="inner")
    for field in ("open", "high", "low", "close", "volume"):
        provider_value = pd.to_numeric(merged[field], errors="coerce")
        canonical_value = pd.to_numeric(merged[f"{field}_canonical"], errors="coerce")
        merged[f"{field}_exact"] = provider_value.eq(canonical_value)
        merged[f"{field}_near"] = (provider_value - canonical_value).abs() <= tolerance * canonical_value.abs().clip(lower=1.0)
    merged["open_canonical_present"] = merged["open_canonical"].notna()
    merged["hlc_exact"] = merged[["high_exact", "low_exact", "close_exact"]].all(axis=1)
    merged["volume_ratio"] = merged["volume"] / merged["volume_canonical"].replace(0, pd.NA)
    return merged
