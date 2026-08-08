from __future__ import annotations

import base64
import io
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlencode

import pandas as pd
import requests


IDX_DAILY_INVESTOR_TABLE_URL = (
    "https://www.idx.id/en/market-data/statistical-reports/digital-statistic/"
    "monthly/equity-trading-by-investor/table-daily-trading-by-type-of-investor"
)
IDX_DAILY_INVESTOR_DATA_URL = "https://www.idx.id/primary/DigitalStatistic/GetApiData"
IDX_DAILY_STATISTICS_URL = "https://www.idx.id/primary/Statistic/GetStatistic"

IDX_DIGITAL_STATISTICS_SOURCE_ID = "IDX_DIGITAL_STATISTICS_DAILY_TRADING_TABLE"
IDX_DAILY_STATISTICS_SOURCE_ID = "IDX_DAILY_STATISTICS_PUBLICATION_LISTING"


HtmlFetcher = Callable[[str], str]
JsonPayload = dict[str, object] | list[object]
JsonFetcher = Callable[[str], JsonPayload]
DATE_CELL = re.compile(r"^\s*\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\s*$")


@dataclass(frozen=True)
class ExchangeSessionSourceResult:
    """Parsed sessions plus the source evidence used to obtain them."""

    sessions: pd.DatetimeIndex
    source_identity: str
    source_ref: str
    fallback_reason: str = ""
    attempted_source_identities: tuple[str, ...] = ()
    attempted_source_refs: tuple[str, ...] = ()


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


def _fetch_json(url: str) -> JsonPayload:
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
    if not isinstance(payload, (dict, list)):
        raise ValueError("IDX session API response is not an object or list")
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


def daily_statistics_url(
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    *,
    lang: str = "en-us",
    keyword: str = "",
) -> str:
    """Build the official IDX Daily Statistics publication-listing URL."""

    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    if end_ts < start_ts:
        raise ValueError("end precedes start")
    query = urlencode(
        {
            "type": "daily",
            "lang": lang,
            "StartDate": start_ts.date().isoformat(),
            "EndDate": end_ts.date().isoformat(),
            "keyword": keyword,
        }
    )
    return f"{IDX_DAILY_STATISTICS_URL}?{query}"


def daily_statistics_data_url(
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    *,
    lang: str = "en-us",
    keyword: str = "",
) -> str:
    """Compatibility alias for the Daily Statistics listing URL."""

    return daily_statistics_url(start, end, lang=lang, keyword=keyword)


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


def _daily_statistics_rows(payload: JsonPayload) -> list[object]:
    """Return rows from both observed official response envelopes."""

    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("value"), list):
        rows = payload["value"]
    else:
        raise ValueError("IDX Daily Statistics response has no list-valued value field")
    if not rows:
        raise ValueError("IDX Daily Statistics response contains no source dates")
    return rows


def parse_exchange_sessions_from_daily_statistics(
    payload: JsonPayload,
    *,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> pd.DatetimeIndex:
    """Parse official Daily Statistics publication dates as exchange sessions.

    The endpoint has been observed both as a top-level list and as an object
    containing that list in ``value``. A row without a valid source date is
    rejected rather than silently converted into a missing session.
    """

    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    if end_ts < start_ts:
        raise ValueError("end precedes start")

    found: set[pd.Timestamp] = set()
    for row in _daily_statistics_rows(payload):
        if not isinstance(row, dict) or "date" not in row:
            raise ValueError("IDX Daily Statistics response has a malformed row")
        value = pd.to_datetime(row["date"], errors="coerce")
        if pd.isna(value):
            raise ValueError("IDX Daily Statistics response has an invalid source date")
        session = pd.Timestamp(value).tz_localize(None).normalize()
        if session.weekday() > 4:
            raise ValueError("Official IDX Daily Statistics produced a weekend date")
        if start_ts <= session <= end_ts:
            found.add(session)

    if not found:
        raise ValueError("No IDX Daily Statistics source dates found in requested range")
    return pd.DatetimeIndex(sorted(found))


def parse_daily_statistics_publication_dates(
    payload: JsonPayload,
    *,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> pd.DatetimeIndex:
    """Compatibility alias for the Daily Statistics date parser."""

    return parse_exchange_sessions_from_daily_statistics(payload, start=start, end=end)


def fetch_exchange_sessions_from_daily_statistics(
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    *,
    fetch_json: JsonFetcher = _fetch_json,
    lang: str = "en-us",
    keyword: str = "",
) -> pd.DatetimeIndex:
    """Fetch the official Daily Statistics publication-listing sessions."""

    url = daily_statistics_url(start, end, lang=lang, keyword=keyword)
    return parse_exchange_sessions_from_daily_statistics(
        fetch_json(url), start=start, end=end
    )


def _source_result(
    sessions: pd.DatetimeIndex,
    *,
    source_identity: str,
    source_ref: str,
    fallback_reason: str = "",
    attempted_source_identities: tuple[str, ...] = (),
    attempted_source_refs: tuple[str, ...] = (),
) -> ExchangeSessionSourceResult:
    return ExchangeSessionSourceResult(
        sessions=pd.DatetimeIndex(sessions),
        source_identity=source_identity,
        source_ref=source_ref,
        fallback_reason=fallback_reason,
        attempted_source_identities=attempted_source_identities,
        attempted_source_refs=attempted_source_refs,
    )


def fetch_exchange_sessions_month_with_source(
    year: int,
    month: int,
    *,
    fetch_json: JsonFetcher = _fetch_json,
    fetch_html: HtmlFetcher | None = None,
    fetch_daily_statistics_json: JsonFetcher | None = None,
) -> ExchangeSessionSourceResult:
    """Fetch a month and retain auditable source/fallback identity.

    The Digital Statistics table remains the first source. The Daily
    Statistics publication listing is consulted when the first source is
    empty, and in the default/live path it is also used to detect an
    incomplete first-source date set. Conflicting official date sets fail
    closed because neither source can safely be preferred.
    """

    month_start = pd.Timestamp(year=year, month=month, day=1)
    month_end = month_start + pd.offsets.MonthEnd(1)
    monthly_ref = (
        monthly_session_page_url(year, month)
        if fetch_html is not None
        else monthly_session_data_url(year, month)
    )
    attempted_identities = [IDX_DIGITAL_STATISTICS_SOURCE_ID]
    attempted_refs = [monthly_ref]

    monthly_error: Exception | None = None
    try:
        if fetch_html is not None:
            monthly_sessions = parse_exchange_sessions_from_html(
                fetch_html(monthly_ref), year=year, month=month
            )
        else:
            monthly_sessions = parse_exchange_sessions_from_json(
                fetch_json(monthly_ref), year=year, month=month
            )
    except Exception as error:
        monthly_error = error
        monthly_sessions = pd.DatetimeIndex([])

    # A custom HTML compatibility fetcher is intentionally not followed by a
    # live network fallback unless its Daily Statistics fetcher is injected.
    daily_fetcher = fetch_daily_statistics_json
    if daily_fetcher is None and fetch_html is None:
        daily_fetcher = fetch_json
    should_compare_sources = (
        daily_fetcher is not None
        and (monthly_error is None)
        and (fetch_daily_statistics_json is not None or fetch_json is _fetch_json)
    )

    daily_ref = daily_statistics_url(month_start, month_end)
    if should_compare_sources or monthly_error is not None:
        attempted_identities.append(IDX_DAILY_STATISTICS_SOURCE_ID)
        attempted_refs.append(daily_ref)

    if monthly_error is None and not should_compare_sources:
        return _source_result(
            monthly_sessions,
            source_identity=IDX_DIGITAL_STATISTICS_SOURCE_ID,
            source_ref=monthly_ref,
            attempted_source_identities=tuple(attempted_identities),
            attempted_source_refs=tuple(attempted_refs),
        )

    if monthly_error is None and should_compare_sources:
        try:
            daily_sessions = parse_exchange_sessions_from_daily_statistics(
                daily_fetcher(daily_ref), start=month_start, end=month_end
            )
        except Exception as error:
            raise ValueError(
                "IDX Daily Statistics fallback/coverage source is malformed: "
                f"{error}"
            ) from error

        monthly_set = set(monthly_sessions)
        daily_set = set(daily_sessions)
        if monthly_set == daily_set:
            return _source_result(
                monthly_sessions,
                source_identity=IDX_DIGITAL_STATISTICS_SOURCE_ID,
                source_ref=monthly_ref,
                attempted_source_identities=tuple(attempted_identities),
                attempted_source_refs=tuple(attempted_refs),
            )
        if monthly_set.issubset(daily_set):
            return _source_result(
                daily_sessions,
                source_identity=IDX_DAILY_STATISTICS_SOURCE_ID,
                source_ref=daily_ref,
                fallback_reason="MONTHLY_DIGITAL_STATISTICS_INCOMPLETE",
                attempted_source_identities=tuple(attempted_identities),
                attempted_source_refs=tuple(attempted_refs),
            )
        if daily_set.issubset(monthly_set):
            return _source_result(
                monthly_sessions,
                source_identity=IDX_DIGITAL_STATISTICS_SOURCE_ID,
                source_ref=monthly_ref,
                fallback_reason="DAILY_STATISTICS_LISTING_INCOMPLETE",
                attempted_source_identities=tuple(attempted_identities),
                attempted_source_refs=tuple(attempted_refs),
            )
        raise ValueError(
            "Official IDX session sources disagree on dates; refusing to infer truth"
        )

    # The primary source was empty or malformed. Use only the separately
    # injected/default official listing source; no weekday/vendor substitution.
    if daily_fetcher is None:
        raise ValueError(f"Monthly IDX session source failed: {monthly_error}")
    try:
        daily_sessions = parse_exchange_sessions_from_daily_statistics(
            daily_fetcher(daily_ref), start=month_start, end=month_end
        )
    except Exception as error:
        raise ValueError(
            "IDX session sources failed: monthly Digital Statistics: "
            f"{monthly_error}; Daily Statistics: {error}"
        ) from error
    return _source_result(
        daily_sessions,
        source_identity=IDX_DAILY_STATISTICS_SOURCE_ID,
        source_ref=daily_ref,
        fallback_reason="MONTHLY_DIGITAL_STATISTICS_EMPTY_OR_INVALID",
        attempted_source_identities=tuple(attempted_identities),
        attempted_source_refs=tuple(attempted_refs),
    )


def fetch_exchange_sessions_month(
    year: int,
    month: int,
    *,
    fetch_json: JsonFetcher = _fetch_json,
    fetch_html: HtmlFetcher | None = None,
    fetch_daily_statistics_json: JsonFetcher | None = None,
) -> pd.DatetimeIndex:
    return fetch_exchange_sessions_month_with_source(
        year,
        month,
        fetch_json=fetch_json,
        fetch_html=fetch_html,
        fetch_daily_statistics_json=fetch_daily_statistics_json,
    ).sessions


def fetch_exchange_sessions(
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    *,
    fetch_json: JsonFetcher = _fetch_json,
    fetch_html: HtmlFetcher | None = None,
    fetch_daily_statistics_json: JsonFetcher | None = None,
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
            fetch_daily_statistics_json=fetch_daily_statistics_json,
        ):
            if start_ts <= session <= end_ts:
                sessions.add(pd.Timestamp(session))

    if not sessions:
        raise ValueError("No IDX exchange sessions found in requested range")
    return pd.DatetimeIndex(sorted(sessions))
