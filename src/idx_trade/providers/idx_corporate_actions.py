from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from math import isclose
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import requests

from ..security_master import normalise_ticker


IDX_ISSUED_HISTORY_URL = (
    "https://www.idx.id/primary/ListingActivity/GetIssuedHistory"
)
IDX_CORPORATE_ACTION_SOURCE_ID = "IDX_LISTING_ACTIVITY_ISSUED_HISTORY"
IDX_CORPORATE_ACTIONS = frozenset({"stockSplit", "reverseStock"})

CORPORATE_ACTION_COLUMNS = (
    "ticker",
    "action",
    "effective_date",
    "listing_date",
    "old_shares",
    "new_shares",
    "ratio",
    "source",
    "source_identity",
    "source_ref",
)

CorporateActionPayload = dict[str, object] | list[object]
JsonFetcher = Callable[[str], CorporateActionPayload]


def _fetch_json(url: str) -> CorporateActionPayload:
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
        raise ValueError("IDX corporate-action response is not an object or list")
    return payload


def _date_param(value: str | pd.Timestamp | None) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""
    parsed = pd.Timestamp(value).normalize()
    return parsed.strftime("%Y%m%d")


def issued_history_url(
    *,
    start: int = 0,
    length: int = 9999,
    ca_type: str = "",
    date_from: str | pd.Timestamp | None = None,
    date_to: str | pd.Timestamp | None = None,
) -> str:
    """Build the official issued-history request URL."""

    if start < 0 or length <= 0:
        raise ValueError("start must be non-negative and length must be positive")
    if ca_type and ca_type not in IDX_CORPORATE_ACTIONS:
        raise ValueError(f"Unsupported IDX corporate-action type: {ca_type}")
    query = urlencode(
        {
            "caType": ca_type,
            "dateFrom": _date_param(date_from),
            "dateTo": _date_param(date_to),
            "start": start,
            "length": length,
        }
    )
    return f"{IDX_ISSUED_HISTORY_URL}?{query}"


def corporate_action_data_url(
    *,
    start: int = 0,
    length: int = 9999,
    ca_type: str = "",
    date_from: str | pd.Timestamp | None = None,
    date_to: str | pd.Timestamp | None = None,
) -> str:
    """Compatibility alias for the official issued-history URL."""

    return issued_history_url(
        start=start,
        length=length,
        ca_type=ca_type,
        date_from=date_from,
        date_to=date_to,
    )


def _response_rows(payload: CorporateActionPayload) -> list[object]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
        rows = payload["data"]
    elif isinstance(payload, dict) and isinstance(payload.get("value"), list):
        rows = payload["value"]
    else:
        raise ValueError("IDX corporate-action response has no list-valued data field")
    return rows


_MISSING = object()


def _first_present(row: Mapping[str, object], *names: str) -> object:
    for name in names:
        if name in row:
            return row[name]
    return _MISSING


def _parse_share_count(value: object, *, field: str, ticker: str) -> int | float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"Invalid {field} for IDX corporate action {ticker}") from error
    if not number.is_finite():
        raise ValueError(f"Invalid {field} for IDX corporate action {ticker}")
    if number == number.to_integral_value():
        return int(number)
    return float(number)


def derive_split_ratio(
    old_shares: object, new_shares: object
) -> float | None:
    """Return new shares / old shares only when both counts are positive."""

    old = _parse_share_count(old_shares, field="old_shares", ticker="")
    new = _parse_share_count(new_shares, field="new_shares", ticker="")
    if old is None or new is None or old <= 0 or new <= 0:
        return None
    return float(Decimal(str(new)) / Decimal(str(old)))


def parse_idx_corporate_actions(
    payload: CorporateActionPayload,
    *,
    source_ref: str = IDX_ISSUED_HISTORY_URL,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Parse IDX stockSplit and reverseStock rows only.

    IDX listing activity is authoritative for these technical actions. Dividend
    and other listing-activity rows are deliberately excluded; this parser does
    not adjust OHLC or synthesize actions from a vendor field.
    """

    start_ts = pd.Timestamp(start_date).normalize() if start_date is not None else None
    end_ts = pd.Timestamp(end_date).normalize() if end_date is not None else None
    if start_ts is not None and end_ts is not None and end_ts < start_ts:
        raise ValueError("end_date precedes start_date")

    parsed: list[dict[str, object]] = []
    for raw_row in _response_rows(payload):
        if not isinstance(raw_row, Mapping):
            raise ValueError("IDX corporate-action response contains a malformed row")
        action_value = _first_present(raw_row, "JenisTindakan", "action")
        if action_value is _MISSING:
            raise ValueError("IDX corporate-action row has no action field")
        action = str(action_value).strip()
        if action not in IDX_CORPORATE_ACTIONS:
            continue

        ticker_value = _first_present(raw_row, "KodeEmiten", "ticker", "code")
        date_value = _first_present(
            raw_row,
            "TanggalPencatatan",
            "effective_date",
            "listing_date",
            "date",
        )
        old_value = _first_present(
            raw_row, "JumlahSaham", "old_shares", "old_share_count"
        )
        new_value = _first_present(
            raw_row,
            "JumlahSahamSetelahTindakan",
            "new_shares",
            "new_share_count",
        )
        if _MISSING in (ticker_value, date_value, old_value, new_value):
            raise ValueError(f"IDX {action} row is missing required fields")

        ticker = normalise_ticker(ticker_value)
        if not ticker:
            raise ValueError(f"IDX {action} row has an empty ticker")
        effective_date = pd.to_datetime(date_value, errors="coerce")
        if pd.isna(effective_date):
            raise ValueError(f"IDX {action} row has an invalid listing date")
        effective_date = pd.Timestamp(effective_date).tz_localize(None).normalize()
        if start_ts is not None and effective_date < start_ts:
            continue
        if end_ts is not None and effective_date > end_ts:
            continue

        old_shares = _parse_share_count(old_value, field="old_shares", ticker=ticker)
        new_shares = _parse_share_count(new_value, field="new_shares", ticker=ticker)
        parsed.append(
            {
                "ticker": ticker,
                "action": action,
                "effective_date": effective_date,
                "listing_date": effective_date,
                "old_shares": old_shares,
                "new_shares": new_shares,
                "ratio": derive_split_ratio(old_shares, new_shares),
                "source": IDX_CORPORATE_ACTION_SOURCE_ID,
                "source_identity": IDX_CORPORATE_ACTION_SOURCE_ID,
                "source_ref": source_ref,
            }
        )

    if not parsed:
        return pd.DataFrame(columns=list(CORPORATE_ACTION_COLUMNS))
    return (
        pd.DataFrame(parsed, columns=list(CORPORATE_ACTION_COLUMNS))
        .sort_values(["ticker", "effective_date", "action"])
        .reset_index(drop=True)
    )


def fetch_idx_corporate_actions(
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
    *,
    fetch_json: JsonFetcher = _fetch_json,
    start: int = 0,
    length: int = 9999,
) -> pd.DataFrame:
    """Fetch and parse authoritative IDX stockSplit/reverseStock history."""

    url = issued_history_url(
        start=start,
        length=length,
        date_from=start_date,
        date_to=end_date,
    )
    payload = fetch_json(url)
    rows = _response_rows(payload)
    if isinstance(payload, dict):
        expected = payload.get("recordsFiltered", payload.get("recordsTotal"))
        if isinstance(expected, (int, float)) and int(expected) > len(rows):
            raise ValueError(
                "IDX corporate-action response is incomplete for the requested page"
            )
    return parse_idx_corporate_actions(
        payload,
        source_ref=url,
        start_date=start_date,
        end_date=end_date,
    )


def fetch_corporate_actions(
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
    *,
    fetch_json: JsonFetcher = _fetch_json,
    start: int = 0,
    length: int = 9999,
) -> pd.DataFrame:
    """Compatibility alias for :func:`fetch_idx_corporate_actions`."""

    return fetch_idx_corporate_actions(
        start_date=start_date,
        end_date=end_date,
        fetch_json=fetch_json,
        start=start,
        length=length,
    )


def _as_float_ratio(value: object) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(result) or result == 0:
        return None
    return result


def _normalise_yahoo_split_events(
    yahoo_events: pd.DataFrame | Mapping[str, pd.DataFrame] | Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Convert common Yahoo daily-frame shapes into deterministic event rows."""

    frames: list[tuple[str | None, pd.DataFrame]] = []
    if isinstance(yahoo_events, Mapping):
        for ticker, frame in yahoo_events.items():
            if not isinstance(frame, pd.DataFrame):
                raise TypeError("Yahoo corporate-action frames must be pandas DataFrames")
            frames.append((normalise_ticker(ticker), frame))
    elif isinstance(yahoo_events, pd.DataFrame):
        frames.append((None, yahoo_events))
    else:
        frame = pd.DataFrame(list(yahoo_events))
        frames.append((None, frame))

    events: list[dict[str, object]] = []
    for default_ticker, frame in frames:
        work = frame.copy()
        if "date" not in work.columns:
            if isinstance(work.index, pd.DatetimeIndex):
                work = work.reset_index().rename(columns={work.index.name or "index": "date"})
            else:
                raise ValueError("Yahoo split events have no date field")
        split_column = next(
            (
                column
                for column in ("stock_splits", "Stock Splits", "ratio", "split_ratio")
                if column in work.columns
            ),
            None,
        )
        if split_column is None:
            raise ValueError("Yahoo split events have no stock-splits field")
        for _, row in work.iterrows():
            ratio = _as_float_ratio(row[split_column])
            if ratio is None:
                continue
            ticker_value = row.get("ticker", default_ticker)
            if ticker_value is None:
                raise ValueError("Yahoo split event has no ticker")
            ticker = normalise_ticker(ticker_value)
            event_date = pd.to_datetime(row["date"], errors="coerce")
            if pd.isna(event_date):
                raise ValueError("Yahoo split event has an invalid date")
            events.append(
                {
                    "ticker": ticker,
                    "effective_date": pd.Timestamp(event_date).tz_localize(None).normalize(),
                    "ratio": ratio,
                }
            )
    return sorted(events, key=lambda row: (row["ticker"], row["effective_date"], row["ratio"]))


def cross_check_yahoo_split_events(
    idx_actions: pd.DataFrame,
    yahoo_events: pd.DataFrame | Mapping[str, pd.DataFrame] | Sequence[Mapping[str, object]],
    *,
    relative_tolerance: float = 1e-9,
) -> pd.DataFrame:
    """Report Yahoo split agreement without changing authoritative IDX rows.

    Each IDX action receives ``MATCH``, ``MISMATCH``, ``ABSENT``, or
    ``IDX_RATIO_UNAVAILABLE``. Yahoo-only rows are reported separately as
    ``YAHOO_ONLY``; they never become IDX actions.
    """

    required = {"ticker", "effective_date", "ratio"}
    if not required.issubset(idx_actions.columns):
        raise ValueError(f"IDX corporate-action frame requires {sorted(required)}")
    yahoo = _normalise_yahoo_split_events(yahoo_events)
    yahoo_by_key: dict[tuple[str, pd.Timestamp], list[float]] = {}
    for event in yahoo:
        key = (str(event["ticker"]), pd.Timestamp(event["effective_date"]))
        yahoo_by_key.setdefault(key, []).append(float(event["ratio"]))

    report: list[dict[str, object]] = []
    matched_yahoo_keys: set[tuple[str, pd.Timestamp]] = set()
    for _, row in idx_actions.iterrows():
        ticker = normalise_ticker(row["ticker"])
        effective_date = pd.Timestamp(row["effective_date"]).normalize()
        idx_ratio = _as_float_ratio(row["ratio"])
        key = (ticker, effective_date)
        yahoo_ratios = yahoo_by_key.get(key, [])
        yahoo_ratio: float | None = None
        if len(set(yahoo_ratios)) == 1:
            yahoo_ratio = yahoo_ratios[0]
        if idx_ratio is None:
            status = "IDX_RATIO_UNAVAILABLE"
        elif not yahoo_ratios:
            status = "ABSENT"
        elif len(set(yahoo_ratios)) != 1:
            status = "MISMATCH"
        elif isclose(
            idx_ratio,
            yahoo_ratio,
            rel_tol=relative_tolerance,
            abs_tol=relative_tolerance,
        ):
            status = "MATCH"
        else:
            status = "MISMATCH"
        if yahoo_ratios:
            matched_yahoo_keys.add(key)
        report.append(
            {
                "ticker": ticker,
                "effective_date": effective_date,
                "action": row.get("action", ""),
                "idx_ratio": idx_ratio,
                "yahoo_ratio": yahoo_ratio,
                "status": status,
                "source_identity": IDX_CORPORATE_ACTION_SOURCE_ID,
                "source_ref": row.get("source_ref", IDX_ISSUED_HISTORY_URL),
            }
        )

    for key, ratios in yahoo_by_key.items():
        if key in matched_yahoo_keys:
            continue
        report.append(
            {
                "ticker": key[0],
                "effective_date": key[1],
                "action": "",
                "idx_ratio": None,
                "yahoo_ratio": ratios[0] if len(set(ratios)) == 1 else None,
                "status": "YAHOO_ONLY",
                "source_identity": IDX_CORPORATE_ACTION_SOURCE_ID,
                "source_ref": IDX_ISSUED_HISTORY_URL,
            }
        )

    columns = [
        "ticker",
        "effective_date",
        "action",
        "idx_ratio",
        "yahoo_ratio",
        "status",
        "source_identity",
        "source_ref",
    ]
    if not report:
        return pd.DataFrame(columns=columns)
    return (
        pd.DataFrame(report, columns=columns)
        .sort_values(["ticker", "effective_date", "action", "status"])
        .reset_index(drop=True)
    )


def report_yahoo_split_cross_check(
    idx_actions: pd.DataFrame,
    yahoo_events: pd.DataFrame | Mapping[str, pd.DataFrame] | Sequence[Mapping[str, object]],
    *,
    relative_tolerance: float = 1e-9,
) -> pd.DataFrame:
    """Compatibility alias for the deterministic Yahoo cross-check report."""

    return cross_check_yahoo_split_events(
        idx_actions, yahoo_events, relative_tolerance=relative_tolerance
    )
