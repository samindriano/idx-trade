"""Pure semantics and deterministic sampling for the Investing admission pilot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import math
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

import pandas as pd


WIB = ZoneInfo("Asia/Jakarta")
UTC = timezone.utc


@dataclass(frozen=True)
class PilotWindow:
    label: str
    start: date
    end: date


PILOT_WINDOWS = (
    PilotWindow("old", date(2022, 4, 1), date(2022, 6, 30)),
    PilotWindow("mid", date(2024, 4, 1), date(2024, 6, 28)),
    PilotWindow("recent", date(2026, 4, 1), date(2026, 6, 30)),
)


PILOT_TICKERS = (
    "BBCA", "BBRI", "BMRI", "TLKM", "ASII", "AMRT", "ICBP", "INDF", "UNTR", "ANTM", "MDKA", "DSSA", "YUPI", "SPRE", "FREN",
    "INDS", "RIGS", "ESSA", "PTBA", "WTON", "SGRO", "KRAS", "MLBI", "NIKL", "ENRG",
    "RUNS", "PGUN", "KUAS", "TLDN", "IDEA", "NICL", "OLIV", "SFAN", "NETV", "RMKE",
    "PMUI", "AADI", "BMBL", "PJHB", "HGII", "VERN", "BOAT", "MERI",
    "GTBO", "COAL", "BIRD", "ZINC", "AUTO", "MFIN", "WSKT",
)


def epoch_bounds_for_local_window(window: PilotWindow) -> tuple[int, int]:
    """Return UTC epochs for inclusive local-date request bounds."""
    start = datetime.combine(window.start, time.min, tzinfo=WIB)
    end = datetime.combine(window.end + timedelta(days=1), time.min, tzinfo=WIB) - timedelta(seconds=1)
    return int(start.timestamp()), int(end.timestamp())


def normalize_history_payload(
    payload: Mapping[str, Any],
    *,
    ticker: str,
    pair_id: str,
    window: PilotWindow,
    session_dates: set[date],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Normalize a raw Investing history response without altering raw values."""
    status = str(payload.get("s", ""))
    result = {"provider_status": status, "raw_rows": 0, "admitted_rows": 0,
              "malformed_rows": 0, "duplicate_rows": 0, "off_session_rows": 0,
              "invalid_ohlcv_rows": 0, "session_dates": [], "bar_counts": {}}
    empty_columns = ["ticker", "pair_id", "raw_epoch", "raw_timestamp_utc", "timestamp_wib",
                     "session_date", "open", "high", "low", "close", "volume"]
    if status != "ok":
        return pd.DataFrame(columns=empty_columns), result
    fields = {key: payload.get(key) for key in ("t", "o", "h", "l", "c", "v")}
    lengths = [len(value) if isinstance(value, list) else -1 for value in fields.values()]
    if not lengths or min(lengths) < 0 or len(set(lengths)) != 1:
        result["malformed_rows"] += 1
        return pd.DataFrame(columns=empty_columns), result
    result["raw_rows"] = lengths[0]
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index in range(lengths[0]):
        try:
            epoch = int(fields["t"][index])
            values = {name: float(fields[name][index]) for name in ("o", "h", "l", "c", "v")}
            if not math.isfinite(epoch) or any(not math.isfinite(value) for value in values.values()):
                raise ValueError("non-finite field")
        except (TypeError, ValueError, OverflowError):
            result["malformed_rows"] += 1
            continue
        if epoch in seen:
            result["duplicate_rows"] += 1
            continue
        seen.add(epoch)
        timestamp_utc = datetime.fromtimestamp(epoch, tz=UTC)
        timestamp_wib = timestamp_utc.astimezone(WIB)
        if timestamp_wib.date() not in session_dates or not (time(8, 0) <= timestamp_wib.time() <= time(16, 0)):
            result["off_session_rows"] += 1
            continue
        if (values["o"] <= 0 or values["h"] <= 0 or values["l"] <= 0 or values["c"] <= 0 or
                values["v"] < 0 or values["h"] < values["l"] or
                not values["l"] <= values["o"] <= values["h"] or
                not values["l"] <= values["c"] <= values["h"]):
            result["invalid_ohlcv_rows"] += 1
            continue
        rows.append({"ticker": ticker, "pair_id": pair_id, "raw_epoch": epoch,
                     "raw_timestamp_utc": timestamp_utc.isoformat(),
                     "timestamp_wib": timestamp_wib.isoformat(),
                     "session_date": timestamp_wib.date().isoformat(),
                     "open": values["o"], "high": values["h"], "low": values["l"],
                     "close": values["c"], "volume": values["v"]})
    frame = pd.DataFrame(rows, columns=empty_columns)
    if not frame.empty:
        counts = frame.groupby("session_date").size().astype(int).to_dict()
        result["bar_counts"] = counts
        result["session_dates"] = sorted(counts)
        result["admitted_rows"] = len(frame)
    return frame, result


def aggregate_daily(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate admitted intraday rows, preserving session chronology."""
    if frame.empty:
        return pd.DataFrame(columns=["ticker", "session_date", "open", "high", "low", "close", "volume", "bar_count"])
    ordered = frame.sort_values(["ticker", "session_date", "raw_epoch"])
    grouped = ordered.groupby(["ticker", "session_date"], sort=True)
    result = grouped.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                         close=("close", "last"), volume=("volume", "sum"), bar_count=("raw_epoch", "size"))
    return result.reset_index()


def compare_daily(provider_daily: pd.DataFrame, canonical: pd.DataFrame, *, tolerance: float = 1e-6) -> pd.DataFrame:
    """Compare provider daily values to canonical rows; no values are repaired."""
    if provider_daily.empty or canonical.empty:
        return pd.DataFrame()
    left = provider_daily.copy()
    right = canonical.copy()
    left["session_date"] = left["session_date"].astype(str)
    right["session_date"] = pd.to_datetime(right["date"]).dt.date.astype(str)
    columns = ["ticker", "session_date", "open", "high", "low", "close", "volume"]
    merged = left[columns + ["bar_count"]].merge(right[columns], on=["ticker", "session_date"], suffixes=("_provider", "_canonical"))
    for field in ("open", "high", "low", "close", "volume"):
        provider = merged[f"{field}_provider"]
        canon = merged[f"{field}_canonical"]
        merged[f"{field}_exact"] = provider.eq(canon)
        merged[f"{field}_near"] = (provider - canon).abs() <= tolerance * canon.abs().clip(lower=1.0)
    merged["hlc_exact"] = merged[["high_exact", "low_exact", "close_exact"]].all(axis=1)
    merged["volume_ratio"] = merged["volume_provider"] / merged["volume_canonical"].replace(0, pd.NA)
    return merged


def deterministic_sample_manifest() -> dict[str, Any]:
    return {"seed": 20260813, "tickers": list(PILOT_TICKERS), "windows": [window.__dict__ for window in PILOT_WINDOWS]}


def expected_sessions_for_listing(calendar_dates: Iterable[date], *, listed_from: date | None, listed_to: date | None, window: PilotWindow) -> list[str]:
    return [d.isoformat() for d in sorted(calendar_dates) if window.start <= d <= window.end and
            (listed_from is None or d >= listed_from) and (listed_to is None or d <= listed_to)]
