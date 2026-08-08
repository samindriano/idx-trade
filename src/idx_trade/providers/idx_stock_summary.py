from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass

import pandas as pd
import requests

from ..security_master import canonicalize_tradability_anchors, normalise_ticker
from ..states import TradabilityState


IDX_HOME_URL = "https://www.idx.co.id/id"
IDX_SESSION_VALIDATION_URL = "https://www.idx.co.id/primary/home/GetIndexList"
IDX_STOCK_SUMMARY_URL = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary"


@dataclass(frozen=True)
class StockSummaryFetchMeta:
    requested_date: str
    source_ref: str
    records_total: int | None
    rows: int
    explicit_security_status_rows: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def stock_summary_url(date: str | pd.Timestamp) -> str:
    day = pd.Timestamp(date).normalize()
    return f"{IDX_STOCK_SUMMARY_URL}?date={day.strftime('%Y%m%d')}"


def _browser_headers() -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Referer": "https://www.idx.co.id/",
        "User-Agent": "Mozilla/5.0 idx-trade-research/2.0",
        "X-Requested-With": "XMLHttpRequest",
    }


def fetch_stock_summary_payload(
    date: str | pd.Timestamp,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> tuple[dict[str, object], str]:
    """Fetch the official public IDX Stock Summary endpoint with a browser session.

    This adapter does not infer tradability from price/volume presence. It only
    preserves any explicit status field returned by IDX for later audited
    interpretation.
    """

    client = session or requests.Session()
    headers = _browser_headers()
    home = client.get(IDX_HOME_URL, headers=headers, timeout=timeout)
    home.raise_for_status()
    validation = client.get(
        IDX_SESSION_VALIDATION_URL, headers=headers, timeout=timeout
    )
    validation.raise_for_status()

    url = stock_summary_url(date)
    response = client.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("IDX stock-summary response is not an object")
    if not isinstance(payload.get("data"), list):
        raise ValueError("IDX stock-summary response has no list-valued data field")
    return payload, url


def parse_stock_summary_payload(
    payload: Mapping[str, object],
    *,
    requested_date: str | pd.Timestamp,
    source_ref: str,
) -> tuple[pd.DataFrame, StockSummaryFetchMeta]:
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError("IDX stock-summary response has no list-valued data field")

    requested = pd.Timestamp(requested_date).normalize()
    parsed: list[dict[str, object]] = []
    status_keys = ("SecurityStatus", "SecurityStatusCode")
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        ticker = normalise_ticker(row.get("StockCode", ""))
        if not ticker or not pd.Series([ticker]).str.fullmatch(r"[A-Z0-9]{4}").iloc[0]:
            continue
        raw_date = pd.to_datetime(row.get("Date"), errors="coerce")
        day = requested if pd.isna(raw_date) else pd.Timestamp(raw_date).tz_localize(None).normalize()
        if day != requested:
            continue

        explicit_status = ""
        explicit_status_field = ""
        for key in status_keys:
            value = row.get(key)
            if value is not None and str(value).strip():
                explicit_status = str(value).strip()
                explicit_status_field = key
                break

        parsed.append(
            {
                "ticker": ticker,
                "as_of_date": day,
                "remarks": str(row.get("Remarks", "") or "").strip(),
                "security_status_raw": explicit_status,
                "security_status_field": explicit_status_field,
                "source": "IDX_PUBLIC_STOCK_SUMMARY",
                "source_ref": source_ref,
            }
        )

    frame = pd.DataFrame(
        parsed,
        columns=(
            "ticker",
            "as_of_date",
            "remarks",
            "security_status_raw",
            "security_status_field",
            "source",
            "source_ref",
        ),
    )
    if not frame.empty:
        frame = frame.drop_duplicates(["ticker", "as_of_date"], keep="last")
        frame = frame.sort_values(["as_of_date", "ticker"]).reset_index(drop=True)

    records_total = payload.get("recordsTotal")
    try:
        records_total_value = int(records_total) if records_total is not None else None
    except (TypeError, ValueError):
        records_total_value = None
    meta = StockSummaryFetchMeta(
        requested_date=requested.date().isoformat(),
        source_ref=source_ref,
        records_total=records_total_value,
        rows=len(frame),
        explicit_security_status_rows=(
            int(frame["security_status_raw"].ne("").sum()) if not frame.empty else 0
        ),
    )
    return frame, meta


def fetch_stock_summary_snapshot(
    date: str | pd.Timestamp,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> tuple[pd.DataFrame, StockSummaryFetchMeta]:
    payload, source_ref = fetch_stock_summary_payload(
        date, session=session, timeout=timeout
    )
    return parse_stock_summary_payload(
        payload,
        requested_date=date,
        source_ref=source_ref,
    )


def stock_summary_status_to_anchors(
    frame: pd.DataFrame,
    *,
    status_mapping: Mapping[str, str | TradabilityState],
    market: str = "REGULAR",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create anchors only from explicitly mapped IDX status values.

    No default mapping is provided because the public endpoint's live status
    vocabulary must be audited first. `Remarks`, volume, price presence and row
    presence are never treated as ACTIVE evidence.
    """

    required = {
        "ticker",
        "as_of_date",
        "security_status_raw",
        "source",
        "source_ref",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Stock-summary columns missing: {sorted(missing)}")

    normalized_mapping = {
        str(key).strip(): TradabilityState(str(value)).value
        for key, value in status_mapping.items()
    }
    anchors: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    for row in frame.itertuples(index=False):
        raw = str(row.security_status_raw or "").strip()
        if not raw:
            diagnostics.append(
                {
                    "ticker": row.ticker,
                    "as_of_date": row.as_of_date,
                    "status": "UNRESOLVED",
                    "diagnostic": "EXPLICIT_SECURITY_STATUS_NOT_EXPOSED",
                    "security_status_raw": "",
                }
            )
            continue
        mapped = normalized_mapping.get(raw)
        if mapped is None:
            diagnostics.append(
                {
                    "ticker": row.ticker,
                    "as_of_date": row.as_of_date,
                    "status": "UNRESOLVED",
                    "diagnostic": "UNMAPPED_SECURITY_STATUS_VALUE",
                    "security_status_raw": raw,
                }
            )
            continue
        if mapped == TradabilityState.UNKNOWN.value:
            raise ValueError("UNKNOWN cannot be promoted into an authoritative anchor")
        anchors.append(
            {
                "ticker": row.ticker,
                "market": market,
                "as_of_date": row.as_of_date,
                "state": mapped,
                "source": row.source,
                "source_ref": row.source_ref,
                "evidence_type": "IDX_STOCK_SUMMARY_EXPLICIT_SECURITY_STATUS",
            }
        )

    anchor_frame = canonicalize_tradability_anchors(pd.DataFrame(anchors))
    diagnostic_frame = pd.DataFrame(
        diagnostics,
        columns=(
            "ticker",
            "as_of_date",
            "status",
            "diagnostic",
            "security_status_raw",
        ),
    )
    return anchor_frame, diagnostic_frame
