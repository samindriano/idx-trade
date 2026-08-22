"""Outcome-blind current IDX common-stock identity refresh primitives.

The active roster is constructed from two agreeing current IDX reference views
(`securities` and stock-enabled `companies`) and a validated listing-event
overlay. Trading data, model outputs, returns, labels, Stockbit activity, and
forward counters are intentionally absent from this API.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

from idx_trade.stockbit_stream_archive import TICKER_RE


class IdentityRefreshError(RuntimeError):
    """Fail-closed identity refresh integrity error."""


@dataclass(frozen=True)
class IdentityRefreshResult:
    tickers: tuple[str, ...]
    rows: tuple[dict[str, str], ...]
    snapshot_sha256: str
    additions: tuple[str, ...]
    removals: tuple[str, ...]
    explained_additions: tuple[str, ...]
    unexplained_additions: tuple[str, ...]
    explained_removals: tuple[str, ...]
    unexplained_removals: tuple[str, ...]
    effective_delistings: tuple[str, ...]
    effective_positive_listings: tuple[str, ...]
    activation_safe: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _ticker(value: Any, *, field_name: str) -> str:
    ticker = str(value or "").strip().upper()
    if not TICKER_RE.fullmatch(ticker):
        raise IdentityRefreshError(f"invalid {field_name}: {ticker!r}")
    return ticker


def _required_text(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise IdentityRefreshError(f"blank {field_name}")
    return text


def _date(value: Any, *, field_name: str) -> date:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text[:10])
    except Exception as exc:
        raise IdentityRefreshError(f"invalid {field_name}: {value!r}") from exc


def _positive_number(value: Any, *, field_name: str) -> float:
    try:
        number = float(value)
    except Exception as exc:
        raise IdentityRefreshError(f"invalid {field_name}: {value!r}") from exc
    if not math.isfinite(number) or number <= 0:
        raise IdentityRefreshError(f"invalid {field_name}: {value!r}")
    return number


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _normalize_securities(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        ticker = _ticker(row.get("Code"), field_name="security Code")
        if ticker in result:
            raise IdentityRefreshError(f"duplicate security ticker: {ticker}")
        name = _required_text(row.get("Name"), field_name=f"security Name {ticker}")
        listing_date = _date(row.get("ListingDate"), field_name=f"security ListingDate {ticker}")
        _positive_number(row.get("Shares"), field_name=f"security Shares {ticker}")
        _required_text(row.get("ListingBoard"), field_name=f"security ListingBoard {ticker}")
        result[ticker] = {
            "ticker": ticker,
            "company_name": name,
            "listed_from": listing_date.isoformat(),
            "listed_to": "",
            "universe_source": "ZAPI_IDX_SECURITIES_COMPANIES_MINUS_LISTING_EVENTS_V1",
        }
    if not result:
        raise IdentityRefreshError("empty securities base")
    return result


def _normalize_stock_companies(rows: Iterable[Mapping[str, Any]]) -> dict[str, date]:
    result: dict[str, date] = {}
    for row in rows:
        stock_flag = row.get("EfekEmiten_Saham")
        if stock_flag not in {True, False}:
            raise IdentityRefreshError("non-boolean EfekEmiten_Saham")
        if stock_flag is False:
            continue
        ticker = _ticker(row.get("KodeEmiten"), field_name="company KodeEmiten")
        if ticker in result:
            raise IdentityRefreshError(f"duplicate stock-enabled company ticker: {ticker}")
        _required_text(row.get("NamaEmiten"), field_name=f"company NamaEmiten {ticker}")
        result[ticker] = _date(row.get("TanggalPencatatan"), field_name=f"company TanggalPencatatan {ticker}")
    if not result:
        raise IdentityRefreshError("empty stock-enabled companies base")
    return result


def _monthly_pages(
    pages: Sequence[Mapping[str, Any]],
    *,
    dataset: str,
    event_date_field: str,
) -> list[dict[str, Any]]:
    if not pages:
        return []

    groups: dict[tuple[int, int], list[Mapping[str, Any]]] = {}
    for payload in pages:
        if payload.get("provider") != "idx" or payload.get("dataset") != dataset:
            raise IdentityRefreshError(f"{dataset} provider/dataset mismatch")
        try:
            year = int(payload.get("year"))
            month = int(payload.get("month"))
            page = int(payload.get("page"))
        except Exception as exc:
            raise IdentityRefreshError(f"invalid {dataset} page metadata") from exc
        if month < 1 or month > 12 or page < 1:
            raise IdentityRefreshError(f"invalid {dataset} page metadata")
        groups.setdefault((year, month), []).append(payload)

    events: list[dict[str, Any]] = []
    seen_tickers: set[str] = set()
    for (year, month), group in sorted(groups.items()):
        ordered = sorted(group, key=lambda payload: int(payload["page"]))
        expected_page = 1
        month_count = 0
        declared_total: int | None = None
        for index, payload in enumerate(ordered):
            page_number = int(payload["page"])
            if page_number != expected_page:
                raise IdentityRefreshError(f"incomplete {dataset} pagination for {year:04d}-{month:02d}")
            expected_page += 1
            items = payload.get("items")
            if not isinstance(items, list):
                raise IdentityRefreshError(f"{dataset} items is not a list")
            try:
                count = int(payload.get("count"))
                total = int(payload.get("total"))
            except Exception as exc:
                raise IdentityRefreshError(f"invalid {dataset} count metadata") from exc
            if count != len(items) or total < count:
                raise IdentityRefreshError(f"{dataset} count metadata mismatch")
            if declared_total is None:
                declared_total = total
            elif declared_total != total:
                raise IdentityRefreshError(f"{dataset} total changed across pages")
            month_count += count

            has_more = payload.get("hasMore")
            if not isinstance(has_more, bool):
                raise IdentityRefreshError(f"invalid {dataset} hasMore")
            if index < len(ordered) - 1 and not has_more:
                raise IdentityRefreshError(f"unexpected terminal {dataset} page")
            if index == len(ordered) - 1 and has_more:
                raise IdentityRefreshError(f"incomplete {dataset} pagination for {year:04d}-{month:02d}")

            for raw in items:
                if not isinstance(raw, Mapping):
                    raise IdentityRefreshError(f"invalid {dataset} item")
                ticker = _ticker(raw.get("code"), field_name=f"{dataset} code")
                if ticker in seen_tickers:
                    label = "delisting" if dataset == "delistings" else "new listing"
                    raise IdentityRefreshError(f"duplicate {label} ticker: {ticker}")
                seen_tickers.add(ticker)
                event_date = _date(raw.get(event_date_field), field_name=f"{dataset} {event_date_field} {ticker}")
                if event_date.year != year or event_date.month != month:
                    raise IdentityRefreshError(f"{dataset} event outside declared month: {ticker}")
                events.append({"ticker": ticker, "date": event_date, "raw": dict(raw)})

        if declared_total is None or month_count != declared_total:
            raise IdentityRefreshError(f"incomplete {dataset} month total for {year:04d}-{month:02d}")
    return events


def _ipo_events(payloads: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen_tickers: set[str] = set()
    for payload in payloads:
        if payload.get("provider") != "idx" or payload.get("dataset") != "ipo":
            raise IdentityRefreshError("ipo provider/dataset mismatch")
        items = payload.get("items")
        if not isinstance(items, list):
            raise IdentityRefreshError("ipo items is not a list")
        try:
            start = int(payload.get("start"))
            length = int(payload.get("length"))
            total = int(payload.get("total"))
            declared_year = int(payload.get("year"))
        except Exception as exc:
            raise IdentityRefreshError("invalid ipo pagination metadata") from exc
        if start != 0 or length < total or len(items) != total:
            raise IdentityRefreshError("incomplete ipo payload")
        for raw in items:
            if not isinstance(raw, Mapping):
                raise IdentityRefreshError("invalid ipo item")
            ticker = _ticker(raw.get("code"), field_name="ipo code")
            if ticker in seen_tickers:
                raise IdentityRefreshError(f"duplicate ipo ticker: {ticker}")
            seen_tickers.add(ticker)
            listing_date = _date(raw.get("listingDate"), field_name=f"ipo listingDate {ticker}")
            if listing_date.year != declared_year:
                raise IdentityRefreshError(f"ipo event outside declared year: {ticker}")
            security_type = _required_text(raw.get("securityType"), field_name=f"ipo securityType {ticker}").casefold()
            listing_type = _required_text(raw.get("listingType"), field_name=f"ipo listingType {ticker}")
            events.append(
                {
                    "ticker": ticker,
                    "date": listing_date,
                    "security_type": security_type,
                    "listing_type": listing_type,
                    "raw": dict(raw),
                }
            )
    return events


def reconstruct_active_roster(
    *,
    securities_rows: Sequence[Mapping[str, Any]],
    companies_rows: Sequence[Mapping[str, Any]],
    delisting_pages: Sequence[Mapping[str, Any]],
    new_listing_pages: Sequence[Mapping[str, Any]],
    ipo_payloads: Sequence[Mapping[str, Any]],
    previous_tickers: set[str] | frozenset[str],
    previous_as_of: date,
    as_of: date,
) -> IdentityRefreshResult:
    """Build a deterministic candidate roster without mutating the pinned roster.

    The current base must agree exactly between `securities` and stock-enabled
    `companies`. Event-only tickers are never injected into the base. Listing
    events are used to explain changes, while effective delistings can remove a
    stale ticker that remains in the current reference endpoints.
    """

    if as_of < previous_as_of:
        raise IdentityRefreshError("as_of precedes previous_as_of")

    securities = _normalize_securities(securities_rows)
    companies = _normalize_stock_companies(companies_rows)
    security_set = set(securities)
    company_set = set(companies)
    if security_set != company_set:
        only_securities = sorted(security_set - company_set)
        only_companies = sorted(company_set - security_set)
        raise IdentityRefreshError(
            f"base ticker mismatch: securities_only={only_securities[:10]} companies_only={only_companies[:10]}"
        )

    previous: set[str] = set()
    for raw in previous_tickers:
        previous.add(_ticker(raw, field_name="previous ticker"))

    delistings = _monthly_pages(delisting_pages, dataset="delistings", event_date_field="delistingDate")
    new_listings = _monthly_pages(new_listing_pages, dataset="new-listings", event_date_field="listingDate")
    ipos = _ipo_events(ipo_payloads)

    effective_delisting_dates = {
        event["ticker"]: event["date"] for event in delistings if event["date"] <= as_of
    }
    positive_dates: dict[str, date] = {}
    for event in new_listings:
        if event["date"] <= as_of:
            positive_dates[event["ticker"]] = max(positive_dates.get(event["ticker"], date.min), event["date"])
    for event in ipos:
        if event["security_type"] == "saham" and event["date"] <= as_of:
            positive_dates[event["ticker"]] = max(positive_dates.get(event["ticker"], date.min), event["date"])

    # A validated later stock listing/relisting supersedes an older delisting.
    # Equal-date positive/negative events are ambiguous and fail closed.
    effective_delisted: set[str] = set()
    for ticker, delisting_date in effective_delisting_dates.items():
        positive_date = positive_dates.get(ticker)
        if positive_date == delisting_date:
            raise IdentityRefreshError(f"same-day contradictory listing status: {ticker}")
        if positive_date is None or positive_date < delisting_date:
            effective_delisted.add(ticker)

    candidate_set = security_set - effective_delisted
    additions = candidate_set - previous
    removals = previous - candidate_set

    explained_additions = {ticker for ticker in additions if ticker in positive_dates}
    explained_removals = {ticker for ticker in removals if ticker in effective_delisting_dates}
    unexplained_additions = additions - explained_additions
    unexplained_removals = removals - explained_removals

    rows = tuple(securities[ticker] for ticker in sorted(candidate_set))
    snapshot_sha256 = _canonical_sha(rows)
    activation_safe = not unexplained_additions and not unexplained_removals

    listing_date_mismatches = sorted(
        ticker
        for ticker in candidate_set
        if _date(securities[ticker]["listed_from"], field_name=f"normalized listed_from {ticker}") != companies[ticker]
    )

    return IdentityRefreshResult(
        tickers=tuple(sorted(candidate_set)),
        rows=rows,
        snapshot_sha256=snapshot_sha256,
        additions=tuple(sorted(additions)),
        removals=tuple(sorted(removals)),
        explained_additions=tuple(sorted(explained_additions)),
        unexplained_additions=tuple(sorted(unexplained_additions)),
        explained_removals=tuple(sorted(explained_removals)),
        unexplained_removals=tuple(sorted(unexplained_removals)),
        effective_delistings=tuple(sorted(effective_delisted)),
        effective_positive_listings=tuple(sorted(positive_dates)),
        activation_safe=activation_safe,
        diagnostics={
            "previous_as_of": previous_as_of.isoformat(),
            "as_of": as_of.isoformat(),
            "base_count": len(security_set),
            "candidate_count": len(candidate_set),
            "delisting_event_count": len(delistings),
            "new_listing_event_count": len(new_listings),
            "ipo_event_count": len(ipos),
            "listing_date_mismatches": listing_date_mismatches,
            "event_only_positive_tickers": sorted(set(positive_dates) - security_set),
        },
    )
