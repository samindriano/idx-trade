"""Offline reconciliation helpers for TradingView Open/session remediation.

The functions here read preserved raw artifacts only. Network execution remains
in the bounded runner and is never performed by this module.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd


UTC = timezone.utc
WIB = ZoneInfo("Asia/Jakarta")
PREOPEN_START = time(8, 45)
REGULAR_START = time(9, 0)
REGULAR_END = time(16, 30)


def _float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if pd.notna(result) else None


def bps_difference(value: Any, reference: Any) -> float | None:
    """Return value/reference difference in basis points, without repair."""

    observed = _float(value)
    baseline = _float(reference)
    if observed is None or baseline is None or baseline == 0:
        return None
    return (observed / baseline - 1.0) * 10_000.0


def _timestamp_wib(period: dict[str, Any]) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(period["time"]), tz=UTC).astimezone(WIB)
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return None


def _period_record(ticker: str, requested_date: str, timeframe: str, session: str, period: dict[str, Any], timestamp: datetime) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "date": requested_date,
        "timeframe": str(timeframe),
        "provider_session": session,
        "timestamp_wib": timestamp.isoformat(),
        "timestamp_utc": timestamp.astimezone(UTC).isoformat(),
        "raw_epoch": int(period["time"]),
        "open": _float(period.get("open")),
        "high": _float(period.get("high")),
        "low": _float(period.get("low")),
        "close": _float(period.get("close")),
        "volume": _float(period.get("volume")),
    }


def _load_references(admission_root: Path, panel: Path, tickers: Iterable[str], requested_date: str) -> dict[str, dict[str, Any]]:
    requested = date.fromisoformat(requested_date)
    wanted = {str(ticker).upper() for ticker in tickers}
    panel_frame = pd.read_parquet(panel, columns=["ticker", "date", "open", "close"])
    panel_frame["ticker"] = panel_frame["ticker"].astype(str).str.upper()
    panel_frame["date"] = pd.to_datetime(panel_frame["date"]).dt.date
    panel_frame = panel_frame[panel_frame["ticker"].isin(wanted)].sort_values(["ticker", "date"])
    panel_frame["previous_canonical_close"] = panel_frame.groupby("ticker", sort=False)["close"].shift(1)
    target = panel_frame[panel_frame["date"] == requested]

    tv1d_path = admission_root / "normalized" / "tv1d_comparison.csv"
    tv1d = pd.read_csv(tv1d_path, low_memory=False)
    tv1d["ticker"] = tv1d["ticker"].astype(str).str.upper()
    tv1d["session_date"] = pd.to_datetime(tv1d["session_date"]).dt.date
    tv1d = tv1d[(tv1d["ticker"].isin(wanted)) & (tv1d["session_date"] == requested)]
    tv1d_by_ticker = tv1d.groupby("ticker", sort=False).first()

    references: dict[str, dict[str, Any]] = {}
    for ticker in sorted(wanted):
        row = target[target["ticker"] == ticker]
        if row.empty:
            continue
        panel_row = row.iloc[0]
        tv1d_row = tv1d_by_ticker.loc[ticker] if ticker in tv1d_by_ticker.index else None
        references[ticker] = {
            "official_open": _float(panel_row["open"]),
            "previous_canonical_close": _float(panel_row["previous_canonical_close"]),
            "tv1d_open": _float(tv1d_row.get("open")) if tv1d_row is not None else None,
        }
    return references


def _load_live_payloads(session_artifact_root: Path, tickers: set[str], requested_date: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for path in sorted((session_artifact_root / "raw" / "live").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        request = payload.get("request") or {}
        if str(request.get("ticker", "")).upper() not in tickers:
            continue
        if str(request.get("date")) != requested_date:
            continue
        if str(request.get("timeframe")) not in {"1", "5", "60"}:
            continue
        payloads.append(payload)
    return payloads


def extract_preopen_reconciliation(
    session_artifact_root: Path,
    admission_root: Path,
    panel: Path,
    tickers: Iterable[str] = ("BBCA", "BBRI", "BMRI", "TLKM", "ASII"),
    requested_date: str = "2026-07-01",
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Extract preserved pre-open bars and exact regular/extended comparisons."""

    wanted = {str(ticker).upper() for ticker in tickers}
    references = _load_references(admission_root, panel, wanted, requested_date)
    records: dict[tuple[str, str, str], dict[str, Any]] = {}
    preopen_rows: list[dict[str, Any]] = []
    for payload in _load_live_payloads(session_artifact_root, wanted, requested_date):
        request = payload.get("request") or {}
        response = payload.get("response") or {}
        ticker = str(request.get("ticker")).upper()
        timeframe = str(request.get("timeframe"))
        session = str(request.get("session"))
        if response.get("status") != "AVAILABLE" or ticker not in references:
            continue
        key = (ticker, requested_date, timeframe)
        state = records.setdefault(key, {"ticker": ticker, "date": requested_date, "timeframe": timeframe})
        periods: list[tuple[datetime, dict[str, Any]]] = []
        for period in response.get("periods") or []:
            timestamp = _timestamp_wib(period)
            if timestamp is not None and timestamp.date() == date.fromisoformat(requested_date):
                periods.append((timestamp, period))
        periods.sort(key=lambda item: item[0])
        if session == "extended":
            preopen = [(timestamp, period) for timestamp, period in periods if PREOPEN_START <= timestamp.time() < REGULAR_START]
            for rank, (timestamp, period) in enumerate(preopen, start=1):
                row = _period_record(ticker, requested_date, timeframe, session, period, timestamp)
                row["preopen_rank"] = rank
                preopen_rows.append(row)
            state["preopen"] = preopen
        elif session == "regular":
            regular = [(timestamp, period) for timestamp, period in periods if REGULAR_START <= timestamp.time() <= REGULAR_END]
            state["regular_first"] = regular[0] if regular else None

    reconciliation_rows: list[dict[str, Any]] = []
    for key in sorted(records):
        state = records[key]
        ticker, requested_date, timeframe = key
        reference = references[ticker]
        regular_first = state.get("regular_first")
        regular = _period_record(ticker, requested_date, timeframe, "regular", regular_first[1], regular_first[0]) if regular_first else {}
        for rank, (timestamp, period) in enumerate(state.get("preopen") or [], start=1):
            preopen = _period_record(ticker, requested_date, timeframe, "extended", period, timestamp)
            official_open = reference["official_open"]
            tv1d_open = reference["tv1d_open"]
            row = {
                "ticker": ticker,
                "date": requested_date,
                "timeframe": timeframe,
                "preopen_rank": rank,
                "preopen_timestamp_wib": preopen["timestamp_wib"],
                "preopen_open": preopen["open"],
                "preopen_high": preopen["high"],
                "preopen_low": preopen["low"],
                "preopen_close": preopen["close"],
                "preopen_volume": preopen["volume"],
                "regular_first_timestamp_wib": regular.get("timestamp_wib"),
                "regular_first_open": regular.get("open"),
                "regular_first_high": regular.get("high"),
                "regular_first_low": regular.get("low"),
                "regular_first_close": regular.get("close"),
                "regular_first_volume": regular.get("volume"),
                "official_open": official_open,
                "tv1d_open": tv1d_open,
                "previous_canonical_close": reference["previous_canonical_close"],
                "preopen_open_equals_official_open": official_open is not None and preopen["open"] == official_open,
                "preopen_high_equals_official_open": official_open is not None and preopen["high"] == official_open,
                "preopen_low_equals_official_open": official_open is not None and preopen["low"] == official_open,
                "preopen_close_equals_official_open": official_open is not None and preopen["close"] == official_open,
                "preopen_hlc_all_equal_official_open": official_open is not None and all(preopen[field] == official_open for field in ("high", "low", "close")),
                "official_open_inside_preopen_hl": official_open is not None and preopen["low"] <= official_open <= preopen["high"],
                "preopen_open_equals_tv1d_open": tv1d_open is not None and preopen["open"] == tv1d_open,
                "official_open_inside_preopen_hl_vs_tv1d": tv1d_open is not None and preopen["low"] <= tv1d_open <= preopen["high"],
                "preopen_open_diff_bps_official": bps_difference(preopen["open"], official_open),
                "preopen_open_diff_bps_tv1d": bps_difference(preopen["open"], tv1d_open),
                "preopen_open_diff_bps_previous_close": bps_difference(preopen["open"], reference["previous_canonical_close"]),
                "regular_open_diff_bps_official": bps_difference(regular.get("open"), official_open),
                "regular_open_diff_bps_tv1d": bps_difference(regular.get("open"), tv1d_open),
            }
            reconciliation_rows.append(row)

    bars = pd.DataFrame(preopen_rows).sort_values(["ticker", "timeframe", "preopen_rank"]).reset_index(drop=True) if preopen_rows else pd.DataFrame()
    reconciliation = pd.DataFrame(reconciliation_rows).sort_values(["ticker", "timeframe", "preopen_rank"]).reset_index(drop=True) if reconciliation_rows else pd.DataFrame()
    summary = {
        "requested_date": requested_date,
        "tickers": sorted(wanted),
        "preopen_bar_rows": int(len(bars)),
        "paired_reconciliation_rows": int(len(reconciliation)),
        "preopen_open_equals_official_open": int(reconciliation["preopen_open_equals_official_open"].sum()) if not reconciliation.empty else 0,
        "regular_open_equals_official_open": int((reconciliation["regular_open_diff_bps_official"] == 0).sum()) if not reconciliation.empty else 0,
        "official_open_inside_preopen_hl": int(reconciliation["official_open_inside_preopen_hl"].sum()) if not reconciliation.empty else 0,
        "preopen_open_equals_tv1d_open": int(reconciliation["preopen_open_equals_tv1d_open"].sum()) if not reconciliation.empty else 0,
        "official_open_inside_preopen_hl_vs_tv1d": int(reconciliation["official_open_inside_preopen_hl_vs_tv1d"].sum()) if not reconciliation.empty else 0,
        "interpretation": "forensic comparison only; no OHLC selection or repair",
    }
    return bars, reconciliation, summary


def extract_first_60m_pair_reconciliation(
    session_artifact_root: Path,
    admission_root: Path,
    panel: Path,
    tickers: Iterable[str],
    requested_dates: Iterable[str],
) -> pd.DataFrame:
    """Compare first raw extended and regular 60m bars for frozen dates."""

    wanted = {str(ticker).upper() for ticker in tickers}
    dates = {str(value) for value in requested_dates}
    rows: list[dict[str, Any]] = []
    for requested_date in sorted(dates):
        references = _load_references(admission_root, panel, wanted, requested_date)
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for payload in _load_live_payloads(session_artifact_root, wanted, requested_date):
            request = payload.get("request") or {}
            response = payload.get("response") or {}
            if str(request.get("timeframe")) != "60" or response.get("status") != "AVAILABLE":
                continue
            ticker = str(request.get("ticker", "")).upper()
            if ticker not in references:
                continue
            periods: list[tuple[datetime, dict[str, Any]]] = []
            for period in response.get("periods") or []:
                timestamp = _timestamp_wib(period)
                if timestamp is not None and timestamp.date() == date.fromisoformat(requested_date):
                    periods.append((timestamp, period))
            periods.sort(key=lambda item: item[0])
            if not periods:
                continue
            state = grouped.setdefault((ticker, requested_date), {})
            if str(request.get("session")) == "extended":
                state["extended"] = periods[0]
            elif str(request.get("session")) == "regular":
                regular = [item for item in periods if REGULAR_START <= item[0].time() <= REGULAR_END]
                if regular:
                    state["regular"] = regular[0]
        for (ticker, requested_date), state in sorted(grouped.items()):
            extended = state.get("extended")
            regular = state.get("regular")
            reference = references[ticker]
            extended_row = _period_record(ticker, requested_date, "60", "extended", extended[1], extended[0]) if extended else {}
            regular_row = _period_record(ticker, requested_date, "60", "regular", regular[1], regular[0]) if regular else {}
            official_open = reference["official_open"]
            tv1d_open = reference["tv1d_open"]
            rows.append({
                "ticker": ticker,
                "date": requested_date,
                "extended60_first_timestamp_wib": extended_row.get("timestamp_wib"),
                "extended60_open": extended_row.get("open"),
                "extended60_high": extended_row.get("high"),
                "extended60_low": extended_row.get("low"),
                "extended60_close": extended_row.get("close"),
                "extended60_volume": extended_row.get("volume"),
                "regular60_first_timestamp_wib": regular_row.get("timestamp_wib"),
                "regular60_open": regular_row.get("open"),
                "regular60_high": regular_row.get("high"),
                "regular60_low": regular_row.get("low"),
                "regular60_close": regular_row.get("close"),
                "regular60_volume": regular_row.get("volume"),
                "official_open": official_open,
                "tv1d_open": tv1d_open,
                "previous_canonical_close": reference["previous_canonical_close"],
                "extended60_open_equals_official_open": extended_row.get("open") == official_open if extended_row else False,
                "regular60_open_equals_official_open": regular_row.get("open") == official_open if regular_row else False,
                "extended60_open_equals_tv1d_open": extended_row.get("open") == tv1d_open if extended_row and tv1d_open is not None else False,
                "regular60_open_equals_tv1d_open": regular_row.get("open") == tv1d_open if regular_row and tv1d_open is not None else False,
                "official_open_inside_extended60_hl": extended_row.get("low") <= official_open <= extended_row.get("high") if extended_row and official_open is not None else False,
                "tv1d_open_inside_extended60_hl": extended_row.get("low") <= tv1d_open <= extended_row.get("high") if extended_row and tv1d_open is not None else False,
                "extended60_open_diff_bps_official": bps_difference(extended_row.get("open"), official_open),
                "regular60_open_diff_bps_official": bps_difference(regular_row.get("open"), official_open),
                "extended60_open_diff_bps_tv1d": bps_difference(extended_row.get("open"), tv1d_open),
                "regular60_open_diff_bps_tv1d": bps_difference(regular_row.get("open"), tv1d_open),
                "extended60_open_diff_bps_previous_close": bps_difference(extended_row.get("open"), reference["previous_canonical_close"]),
                "regular60_open_diff_bps_previous_close": bps_difference(regular_row.get("open"), reference["previous_canonical_close"]),
            })
    return pd.DataFrame(rows).sort_values(["ticker", "date"]).reset_index(drop=True) if rows else pd.DataFrame()
