from __future__ import annotations

import re
from collections.abc import Callable

import pandas as pd
import requests
from lxml import html

from ..security_master import normalise_ticker


KSEI_SECURITY_URL = "https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}?setLocale=en-US"
KSEI_IDENTITY_SOURCE = "KSEI_REGISTERED_SECURITIES"
SCOPE_EXCLUSION_REASON_NON_COMMON = "NON_COMMON_SHARE"

_INDONESIAN_MONTHS = {
    "januari": "January",
    "februari": "February",
    "maret": "March",
    "april": "April",
    "mei": "May",
    "juni": "June",
    "juli": "July",
    "agustus": "August",
    "september": "September",
    "oktober": "October",
    "november": "November",
    "desember": "December",
}


def _get_text(url: str) -> str:
    for attempt in range(3):
        response = requests.get(
            url,
            headers={
                "Referer": "https://web.ksei.co.id/",
                "User-Agent": "idx-trade-research/2.0",
            },
            timeout=30,
        )
        if response.status_code < 500 or attempt == 2:
            response.raise_for_status()
            return response.text
    raise RuntimeError(f"KSEI request did not return a response: {url}")


def _page_text(document: str) -> str:
    root = html.fromstring(document)
    values = [str(value).strip() for value in root.xpath("//text()")]
    return re.sub(r"\s+", " ", " ".join(value for value in values if value)).strip()


def _between(text: str, start: str, end: str) -> str:
    pattern = rf"{re.escape(start)}\s+(.*?)\s+{re.escape(end)}"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _definition_fields(document: str) -> dict[str, str]:
    """Read label/value pairs from the structured KSEI security page."""

    root = html.fromstring(document)
    fields: dict[str, str] = {}
    for label_node in root.xpath("//dt"):
        value_nodes = label_node.xpath("following-sibling::dd[1]")
        if not value_nodes:
            continue
        label = " ".join(label_node.text_content().split())
        value = " ".join(value_nodes[0].text_content().split())
        if label and value:
            fields.setdefault(label, value)
    return fields


def _parse_ksei_date(value: str) -> pd.Timestamp:
    """Parse KSEI dates even when the page returns Indonesian month names."""

    raw = " ".join(str(value).split()).strip()
    parsed = pd.to_datetime(raw, errors="coerce")
    if not pd.isna(parsed):
        return pd.Timestamp(parsed).tz_localize(None).normalize()

    translated = raw
    for indonesia, english in _INDONESIAN_MONTHS.items():
        translated = re.sub(
            rf"\b{re.escape(indonesia)}\b",
            english,
            translated,
            flags=re.IGNORECASE,
        )
    parsed = pd.to_datetime(translated, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        raise ValueError(f"KSEI date could not be parsed: {raw!r}")
    return pd.Timestamp(parsed).tz_localize(None).normalize()


def _is_common_share_type(value: object) -> bool:
    normalized = str(value).casefold().strip()
    return "saham biasa" in normalized or "common" in normalized


def parse_ksei_security_identity(
    document: str,
    *,
    requested_ticker: str,
    source_ref: str,
) -> pd.DataFrame:
    """Parse authoritative KSEI identity/type evidence for one registered share.

    This function deliberately does not decide model-universe scope. It records
    the security type so callers can distinguish common shares from preference
    shares or other registered equity series without hardcoding ticker symbols.
    KSEI registry status is identity evidence, not IDX tradability evidence.
    """

    ticker = normalise_ticker(requested_ticker)
    text = _page_text(document)
    fields = _definition_fields(document)
    short_code = normalise_ticker(
        fields.get("Short Code") or _between(text, "Short Code", "Type")
    )
    security_type = fields.get("Type") or _between(text, "Type", "Listing Date")
    listing_date_raw = fields.get("Listing Date") or _between(
        text, "Listing Date", "Stock Exchange"
    )
    stock_exchange = (
        fields.get("Stock Exchange") or _between(text, "Stock Exchange", "Status")
    ).upper()
    status = (fields.get("Status") or _between(text, "Status", "Nominal")).upper()
    security_name = fields.get("Security name") or _between(
        text, "Security name", "Issuer"
    )
    issuer = fields.get("Issuer") or _between(text, "Issuer", "ISIN Code")

    if short_code != ticker:
        raise ValueError(
            f"KSEI short code mismatch: requested={ticker}, parsed={short_code or 'EMPTY'}"
        )
    if not security_type.strip():
        raise ValueError(f"KSEI security type is missing for {ticker}")
    if not stock_exchange:
        raise ValueError(f"KSEI stock exchange is missing for {ticker}")
    if not status:
        raise ValueError(f"KSEI registry status is missing for {ticker}")

    try:
        listed_from = _parse_ksei_date(listing_date_raw)
    except ValueError as error:
        raise ValueError(
            f"KSEI listing date could not be parsed for {ticker}: {listing_date_raw!r}"
        ) from error

    return pd.DataFrame(
        {
            "ticker": [ticker],
            "company_name": [issuer or security_name],
            "security_name": [security_name],
            "security_type": [security_type],
            "listed_from": [listed_from],
            "stock_exchange": [stock_exchange],
            "registry_status": [status],
            "is_common_share": [_is_common_share_type(security_type)],
            "source": [KSEI_IDENTITY_SOURCE],
            "source_ref": [source_ref],
        }
    )


def fetch_ksei_security_identity(
    ticker: str,
    *,
    get_text: Callable[[str], str] = _get_text,
) -> pd.DataFrame:
    ticker = normalise_ticker(ticker)
    url = KSEI_SECURITY_URL.format(ticker=ticker)
    return parse_ksei_security_identity(
        get_text(url),
        requested_ticker=ticker,
        source_ref=url,
    )


def parse_ksei_active_listing(
    document: str,
    *,
    requested_ticker: str,
    source_ref: str,
) -> pd.DataFrame:
    """Parse one KSEI page into supplemental common-share listing identity.

    KSEI is an identity/reference fallback. `Status = Active` means active KSEI
    registration and must never override an official IDX delisting boundary or
    create ACTIVE tradability state.
    """

    identity = parse_ksei_security_identity(
        document,
        requested_ticker=requested_ticker,
        source_ref=source_ref,
    )
    row = identity.iloc[0]
    ticker = str(row["ticker"])
    if str(row["stock_exchange"]).upper() != "IDX":
        raise ValueError(f"KSEI security {ticker} is not explicitly listed on IDX")
    if str(row["registry_status"]).upper() != "ACTIVE":
        raise ValueError(f"KSEI security {ticker} is not explicitly ACTIVE")
    if not bool(row["is_common_share"]):
        raise ValueError(f"KSEI security {ticker} is not explicitly a common share")

    return pd.DataFrame(
        {
            "ticker": [ticker],
            "company_name": [row["company_name"]],
            "listed_from": [pd.Timestamp(row["listed_from"]).normalize()],
            "listed_to": [pd.NaT],
            "source": [KSEI_IDENTITY_SOURCE],
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
    """Fill common-share identities absent from the primary IDX current list."""

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
                    "source": KSEI_IDENTITY_SOURCE,
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


def reconcile_missing_security_scope(
    active_listings: pd.DataFrame,
    required_tickers: list[str],
    *,
    fetcher: Callable[[str], pd.DataFrame] = fetch_ksei_security_identity,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Resolve missing official-evidence tickers as common or out-of-scope.

    Common IDX shares are added to listing identity. A KSEI-registered IDX
    preference/non-common share is not treated as an identity failure: it is
    recorded as an authoritative `NON_COMMON_SHARE` scope exclusion. Anything
    else remains unresolved. No ticker-specific exclusion is hardcoded.
    """

    active = active_listings.copy()
    existing = (
        set(active["ticker"].map(normalise_ticker))
        if "ticker" in active.columns
        else set()
    )
    additions: list[pd.DataFrame] = []
    exclusions: list[dict[str, object]] = []
    diagnostics: list[dict[str, str]] = []

    for ticker in sorted({normalise_ticker(value) for value in required_tickers} - existing):
        try:
            identity = fetcher(ticker)
            if len(identity) != 1:
                raise ValueError(f"KSEI identity for {ticker} must contain exactly one row")
            row = identity.iloc[0]
            if str(row["stock_exchange"]).upper() != "IDX":
                raise ValueError(f"KSEI security {ticker} is not explicitly on IDX")
            if str(row["registry_status"]).upper() != "ACTIVE":
                raise ValueError(f"KSEI security {ticker} registry status is not ACTIVE")

            if not bool(row["is_common_share"]):
                exclusions.append(
                    {
                        "ticker": ticker,
                        "reason": SCOPE_EXCLUSION_REASON_NON_COMMON,
                        "security_type": str(row["security_type"]),
                        "source": str(row["source"]),
                        "source_ref": str(row["source_ref"]),
                    }
                )
                diagnostics.append(
                    {
                        "ticker": ticker,
                        "status": "OUT_OF_SCOPE_SECURITY_TYPE",
                        "source": str(row["source"]),
                        "error": "",
                    }
                )
                continue

            additions.append(
                pd.DataFrame(
                    {
                        "ticker": [ticker],
                        "company_name": [row["company_name"]],
                        "listed_from": [pd.Timestamp(row["listed_from"]).normalize()],
                        "listed_to": [pd.NaT],
                        "source": [str(row["source"])],
                    }
                )
            )
            diagnostics.append(
                {
                    "ticker": ticker,
                    "status": "SUPPLEMENTED",
                    "source": str(row["source"]),
                    "error": "",
                }
            )
        except Exception as error:
            diagnostics.append(
                {
                    "ticker": ticker,
                    "status": "UNRESOLVED",
                    "source": KSEI_IDENTITY_SOURCE,
                    "error": str(error),
                }
            )

    combined = pd.concat([active, *additions], ignore_index=True) if additions else active
    exclusion_frame = pd.DataFrame(
        exclusions,
        columns=("ticker", "reason", "security_type", "source", "source_ref"),
    )
    diagnostic_frame = pd.DataFrame(
        diagnostics,
        columns=("ticker", "status", "source", "error"),
    )
    return combined, exclusion_frame, diagnostic_frame
