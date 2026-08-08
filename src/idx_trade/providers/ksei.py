from __future__ import annotations

import re
from collections.abc import Callable

import pandas as pd
import requests
from lxml import html

from ..security_master import normalise_ticker


KSEI_SECURITY_URL = "https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}?setLocale=en-US"


def _get_text(url: str) -> str:
    response = requests.get(
        url,
        headers={
            "Referer": "https://web.ksei.co.id/",
            "User-Agent": "idx-trade-research/2.0",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def _page_text(document: str) -> str:
    root = html.fromstring(document)
    values = [str(value).strip() for value in root.xpath("//text()")]
    return re.sub(r"\s+", " ", " ".join(value for value in values if value)).strip()


def _between(text: str, start: str, end: str) -> str:
    pattern = rf"{re.escape(start)}\s+(.*?)\s+{re.escape(end)}"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_ksei_active_listing(
    document: str,
    *,
    requested_ticker: str,
    source_ref: str,
) -> pd.DataFrame:
    """Parse one KSEI registered-share page into supplemental listing identity.

    KSEI is used only as an identity/reference fallback when the IDX current
    active-list endpoint omits an otherwise registered IDX common share. The
    parser fails closed unless the page explicitly says the requested security
    is an ACTIVE share on IDX and exposes a valid listing date.
    """

    ticker = normalise_ticker(requested_ticker)
    text = _page_text(document)
    short_code = normalise_ticker(_between(text, "Short Code", "Type"))
    security_type = _between(text, "Type", "Listing Date")
    listing_date_raw = _between(text, "Listing Date", "Stock Exchange")
    stock_exchange = _between(text, "Stock Exchange", "Status").upper()
    status = _between(text, "Status", "Nominal").upper()
    security_name = _between(text, "Security name", "Issuer")

    if short_code != ticker:
        raise ValueError(
            f"KSEI short code mismatch: requested={ticker}, parsed={short_code or 'EMPTY'}"
        )
    if stock_exchange != "IDX":
        raise ValueError(f"KSEI security {ticker} is not explicitly listed on IDX")
    if status != "ACTIVE":
        raise ValueError(f"KSEI security {ticker} is not explicitly ACTIVE")
    normalized_type = security_type.casefold()
    if "saham biasa" not in normalized_type and "common" not in normalized_type:
        raise ValueError(f"KSEI security {ticker} is not explicitly a common share")

    listed_from = pd.to_datetime(listing_date_raw, errors="coerce")
    if pd.isna(listed_from):
        raise ValueError(f"KSEI listing date could not be parsed for {ticker}: {listing_date_raw!r}")

    return pd.DataFrame(
        {
            "ticker": [ticker],
            "company_name": [security_name],
            "listed_from": [pd.Timestamp(listed_from).normalize()],
            "listed_to": [pd.NaT],
            "source": ["KSEI_REGISTERED_SECURITIES"],
            "source_ref": [source_ref],
        }
    )


def fetch_ksei_active_listing(
    ticker: str,
    *,
    get_text: Callable[[str], str] = _get_text,
) -> pd.DataFrame:
    ticker = normalise_ticker(ticker)
    url = KSEI_SECURITY_URL.format(ticker=ticker)
    return parse_ksei_active_listing(
        get_text(url),
        requested_ticker=ticker,
        source_ref=url,
    )


def supplement_missing_active_listings(
    active_listings: pd.DataFrame,
    required_tickers: list[str],
    *,
    fetcher: Callable[[str], pd.DataFrame] = fetch_ksei_active_listing,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill only identities absent from the primary IDX current-list response.

    Fetch failures remain explicit diagnostics; they are never converted into a
    guessed listing row.
    """

    active = active_listings.copy()
    existing = (
        set(active["ticker"].map(normalise_ticker))
        if "ticker" in active.columns
        else set()
    )
    additions: list[pd.DataFrame] = []
    diagnostics: list[dict[str, str]] = []

    for ticker in sorted({normalise_ticker(value) for value in required_tickers} - existing):
        try:
            row = fetcher(ticker)
            additions.append(row)
            diagnostics.append(
                {
                    "ticker": ticker,
                    "status": "SUPPLEMENTED",
                    "source": str(row.iloc[0]["source"]),
                    "error": "",
                }
            )
        except Exception as error:
            diagnostics.append(
                {
                    "ticker": ticker,
                    "status": "UNRESOLVED",
                    "source": "KSEI_REGISTERED_SECURITIES",
                    "error": str(error),
                }
            )

    if additions:
        supplemental = pd.concat(additions, ignore_index=True)
        combined = pd.concat(
            [active, supplemental.drop(columns=["source_ref"], errors="ignore")],
            ignore_index=True,
        )
    else:
        combined = active

    return combined, pd.DataFrame(
        diagnostics,
        columns=("ticker", "status", "source", "error"),
    )
