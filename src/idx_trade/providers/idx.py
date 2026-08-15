from __future__ import annotations

from datetime import date
from typing import Any, Callable

import pandas as pd
import requests

from ..security_master import normalise_ticker


IDX_STOCK_LIST_URL = "https://www.idx.id/primary/StockData/GetSecuritiesStock"
IDX_DELISTING_URL = "https://www.idx.id/primary/DigitalStatistic/GetApiDataPaginated"


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(
        url,
        params=params,
        headers={"Referer": "https://www.idx.id/", "User-Agent": "idx-trade-research/2.0"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _inclusive_listed_to_from_delisting_effective_date(values: pd.Series) -> pd.Series:
    """Convert IDX ``DeListingDate`` into the security-master inclusive end date.

    IDX reports the date on which delisting becomes effective.  The canonical
    security-master contract stores ``listed_to`` as the last calendar date on
    which the security is still considered listed, and ``existence_state``
    treats that boundary inclusively.  Therefore the effective delisting date
    itself must already resolve to ``DELISTED``.

    Universe decisions are made only on official exchange sessions, so using
    the preceding calendar date is sufficient even when the immediately prior
    calendar day is a weekend or exchange holiday.
    """

    effective = pd.to_datetime(values, errors="coerce").dt.normalize()
    return effective - pd.Timedelta(days=1)


def fetch_active_listings(
    get_json: Callable[[str, dict[str, Any]], dict[str, Any]] = _get_json,
) -> pd.DataFrame:
    """Fetch the current IDX listing reference.

    This source is identity/reference data only. It must never be used by itself
    to define a historical backtest universe.
    """

    payload = get_json(
        IDX_STOCK_LIST_URL,
        {"start": 0, "length": 9999, "code": "", "sector": "", "board": "", "language": "en-us"},
    )
    rows = pd.DataFrame(payload.get("data", []))
    required = {"Code", "Name", "ListingDate"}
    if rows.empty or not required.issubset(rows.columns):
        raise ValueError("IDX active-listing response is empty or schema changed")
    result = pd.DataFrame(
        {
            "ticker": rows["Code"].map(normalise_ticker),
            "company_name": rows["Name"].astype(str).str.strip(),
            "listed_from": pd.to_datetime(rows["ListingDate"], errors="coerce").dt.normalize(),
            "listed_to": pd.NaT,
            "source": "IDX_STOCK_LIST",
        }
    )
    return result[result["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)].dropna(subset=["listed_from"]).reset_index(drop=True)


def fetch_delisted_listings(
    start_year: int,
    end: date | None = None,
    get_json: Callable[[str, dict[str, Any]], dict[str, Any]] = _get_json,
) -> pd.DataFrame:
    """Fetch historical delisting rows from IDX Digital Statistics month by month.

    ``DeListingDate`` is treated as an exclusive effective date.  The returned
    ``listed_to`` therefore represents the inclusive last-listed boundary used
    by the canonical security-master contract.
    """

    end = end or pd.Timestamp.today().date()
    records: list[dict[str, Any]] = []
    for year in range(start_year, end.year + 1):
        last_month = end.month if year == end.year else 12
        for month in range(1, last_month + 1):
            payload = get_json(
                IDX_DELISTING_URL,
                {
                    "urlName": "LINK_DELISTING",
                    "periodYear": year,
                    "periodMonth": month,
                    "periodType": "monthly",
                    "isPrint": "False",
                    "cumulative": "false",
                    "pageSize": 9999,
                    "pageNumber": 1,
                    "orderBy": "",
                },
            )
            records.extend(payload.get("data", []))
    if not records:
        return pd.DataFrame(columns=["ticker", "company_name", "listed_from", "listed_to", "source"])

    rows = pd.DataFrame(records)
    required = {"code", "issuerName", "ListingDate", "DeListingDate"}
    if not required.issubset(rows.columns):
        raise ValueError("IDX delisting response schema changed")
    result = pd.DataFrame(
        {
            "ticker": rows["code"].map(normalise_ticker),
            "company_name": rows["issuerName"].astype(str).str.strip(),
            "listed_from": pd.to_datetime(rows["ListingDate"], errors="coerce").dt.normalize(),
            "listed_to": _inclusive_listed_to_from_delisting_effective_date(rows["DeListingDate"]),
            "source": "IDX_DIGITAL_STATISTIC_DELISTING",
        }
    )
    result = result[result["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)]
    return result.dropna(subset=["listed_from", "listed_to"]).drop_duplicates(["ticker", "listed_from", "listed_to"]).reset_index(drop=True)
