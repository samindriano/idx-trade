from __future__ import annotations

import base64
import io
import json
import re
from collections.abc import Callable
from urllib.parse import urlencode

import pandas as pd
import requests


IDX_DAILY_INVESTOR_TABLE_URL = (
    "https://www.idx.id/en/market-data/statistical-reports/digital-statistic/"
    "monthly/equity-trading-by-investor/table-daily-trading-by-type-of-investor"
)
IDX_DAILY_INVESTOR_DATA_URL = "https://www.idx.id/primary/DigitalStatistic/GetApiData"


HtmlFetcher = Callable[[str], str]
JsonFetcher = Callable[[str], dict[str, object]]
DATE_CELL = re.compile(r"^\s*\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\s*$")


def _fetch_html(url: str) -> str:
    response = requests.get(
        url,
        headers={
            "Referer": "https://www.idx.id/",
            "User-Agent": "idx-trade-research/2.0",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def _fetch_json(url: str) -> dict[str, object]:
    response = requests.get(
        url,
        headers={
            "Referer": "https://www.idx.id/",
            "User-Agent": "idx-trade-research/2.0",
            "Accept": "application/json, text/plain, */*",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("IDX session API response is not an object")
    return payload


def _monthly_filter(year: int, month: int) -> str:
    if month < 1 or month > 12:
        raise ValueError(f"Invalid month: {month}")
    payload = {
        "year": str(year),
        "month": str(month),
        "quarter": 0,
        "type": "monthly",
    }
    encoded = base64.b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return encoded


def monthly_session_page_url(year: int, month: int) -> str:
    return f"{IDX_DAILY_INVESTOR_TABLE_URL}?filter={_monthly_filter(year, month)}"


def monthly_session_data_url(year: int, month: int) -> str:
    query = urlencode(
        {
            "urlName": "LINK_TABLE_DAILY_TRADING_INVESTOR_FOREIGN",
            "query": _monthly_filter(year, month),
            "isPrint": "False",
            "cumulative": "false",
        }
    )
    return f"{IDX_DAILY_INVESTOR_DATA_URL}?{query}"


def _validate_exchange_sessions(
    found: set[pd.Timestamp], *, year: int, month: int
) -> pd.DatetimeIndex:
    if not found:
        raise ValueError(f"No IDX exchange sessions found for {year:04d}-{month:02d}")

    sessions = pd.DatetimeIndex(sorted(found))
    if sessions.weekday.max() > 4:
        raise ValueError("Official IDX session extraction produced a weekend date")
    return sessions


def parse_exchange_sessions_from_html(html: str, *, year: int, month: int) -> pd.DatetimeIndex:
    """Extract Exchange Days from an official IDX daily-trading table.

    The page contains several investor-flow tables that repeat the same trading
    dates. We intentionally use only date-shaped values found inside parsed HTML
    tables and require every resulting date to belong to the requested month.
    Page-level timestamps, numeric trade values and unrelated dates are never
    accepted as exchange sessions.
    """

    if not html.strip():
        raise ValueError("IDX session page is empty")

    try:
        tables = pd.read_html(io.StringIO(html))
    except ValueError as error:
        raise ValueError("IDX session page contains no parseable HTML tables") from error

    found: set[pd.Timestamp] = set()
    for table in tables:
        for column in table.columns:
            values = table[column].astype(str)
            date_values = values[values.str.match(DATE_CELL, na=False)]
            parsed = pd.to_datetime(date_values, errors="coerce", dayfirst=True)
            for value in parsed.dropna():
                session = pd.Timestamp(value).tz_localize(None).normalize()
                if session.year == year and session.month == month:
                    found.add(session)

    return _validate_exchange_sessions(found, year=year, month=month)


def parse_exchange_sessions_from_json(
    payload: dict[str, object], *, year: int, month: int
) -> pd.DatetimeIndex:
    """Extract exchange sessions from the current official IDX data endpoint."""

    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError("IDX session API response has no list-valued data field")

    found: set[pd.Timestamp] = set()
    for row in rows:
        if not isinstance(row, dict) or "date" not in row:
            continue
        value = pd.to_datetime(row["date"], errors="coerce")
        if pd.isna(value):
            continue
        session = pd.Timestamp(value).tz_localize(None).normalize()
        if session.year == year and session.month == month:
            found.add(session)

    return _validate_exchange_sessions(found, year=year, month=month)


def fetch_exchange_sessions_month(
    year: int,
    month: int,
    *,
    fetch_json: JsonFetcher = _fetch_json,
    fetch_html: HtmlFetcher | None = None,
) -> pd.DatetimeIndex:
    if fetch_html is not None:
        url = monthly_session_page_url(year, month)
        return parse_exchange_sessions_from_html(fetch_html(url), year=year, month=month)
    return parse_exchange_sessions_from_json(
        fetch_json(monthly_session_data_url(year, month)), year=year, month=month
    )


def fetch_exchange_sessions(
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    *,
    fetch_json: JsonFetcher = _fetch_json,
    fetch_html: HtmlFetcher | None = None,
) -> pd.DatetimeIndex:
    """Fetch an auditable official IDX Exchange-Day calendar for a date range."""

    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    if end_ts < start_ts:
        raise ValueError("end precedes start")

    months = pd.period_range(start_ts.to_period("M"), end_ts.to_period("M"), freq="M")
    sessions: set[pd.Timestamp] = set()
    for period in months:
        for session in fetch_exchange_sessions_month(
            period.year,
            period.month,
            fetch_json=fetch_json,
            fetch_html=fetch_html,
        ):
            if start_ts <= session <= end_ts:
                sessions.add(pd.Timestamp(session))

    if not sessions:
        raise ValueError("No IDX exchange sessions found in requested range")
    return pd.DatetimeIndex(sorted(sessions))
