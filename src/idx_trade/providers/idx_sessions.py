from __future__ import annotations

import base64
import io
import json
from collections.abc import Callable

import pandas as pd
import requests


IDX_DAILY_INVESTOR_TABLE_URL = (
    "https://www.idx.id/en/market-data/statistical-reports/digital-statistic/"
    "monthly/equity-trading-by-investor/table-daily-trading-by-type-of-investor"
)


HtmlFetcher = Callable[[str], str]


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


def parse_exchange_sessions_from_html(html: str, *, year: int, month: int) -> pd.DatetimeIndex:
    """Extract Exchange Days from an official IDX daily-trading table.

    The page contains several investor-flow tables that repeat the same trading
    dates. We intentionally use only values found inside parsed HTML tables and
    require every resulting date to belong to the requested month. Page-level
    timestamps or unrelated dates are never accepted as exchange sessions.
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
            parsed = pd.to_datetime(values, errors="coerce", dayfirst=True)
            for value in parsed.dropna():
                session = pd.Timestamp(value).tz_localize(None).normalize()
                if session.year == year and session.month == month:
                    found.add(session)

    if not found:
        raise ValueError(f"No IDX exchange sessions found for {year:04d}-{month:02d}")

    sessions = pd.DatetimeIndex(sorted(found))
    if sessions.weekday.max() > 4:
        raise ValueError("Official IDX session extraction produced a weekend date")
    return sessions


def fetch_exchange_sessions_month(
    year: int,
    month: int,
    *,
    fetch_html: HtmlFetcher = _fetch_html,
) -> pd.DatetimeIndex:
    url = monthly_session_page_url(year, month)
    html = fetch_html(url)
    return parse_exchange_sessions_from_html(html, year=year, month=month)


def fetch_exchange_sessions(
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    *,
    fetch_html: HtmlFetcher = _fetch_html,
) -> pd.DatetimeIndex:
    """Fetch an auditable official IDX Exchange-Day calendar for a date range."""

    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    if end_ts < start_ts:
        raise ValueError("end precedes start")

    months = pd.period_range(start_ts.to_period("M"), end_ts.to_period("M"), freq="M")
    sessions: set[pd.Timestamp] = set()
    for period in months:
        for session in fetch_exchange_sessions_month(period.year, period.month, fetch_html=fetch_html):
            if start_ts <= session <= end_ts:
                sessions.add(pd.Timestamp(session))

    if not sessions:
        raise ValueError("No IDX exchange sessions found in requested range")
    return pd.DatetimeIndex(sorted(sessions))
