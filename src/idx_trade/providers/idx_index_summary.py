"""Immutable official IDX Index Summary acquisition for forward sessions.

This provider is deliberately separate from model-input construction.  It
accepts a response only when the endpoint's own row-count metadata proves the
requested date is complete, and it keeps the exact response bytes available
for the session manifest.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib

import pandas as pd
import requests

from .idx_stock_summary import (
    IDX_HOME_URL,
    IDX_SESSION_VALIDATION_URL,
    _browser_headers,
)


IDX_INDEX_SUMMARY_URL = "https://www.idx.id/primary/TradingSummary/GetIndexSummary"
INDEX_FIELDS = (
    "Date",
    "IndexCode",
    "Previous",
    "Highest",
    "Lowest",
    "Close",
    "Change",
    "Volume",
    "Value",
    "Frequency",
    "MarketCapital",
    "NumberOfStock",
)


def index_summary_url(date: str | pd.Timestamp) -> str:
    day = pd.Timestamp(date).normalize()
    return f"{IDX_INDEX_SUMMARY_URL}?date={day.strftime('%Y%m%d')}"


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _integer_metadata(payload: Mapping[str, object], name: str) -> int | None:
    value = payload.get(name)
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"IDX Index Summary {name} is not an integer") from error
    if parsed < 0:
        raise ValueError(f"IDX Index Summary {name} cannot be negative")
    return parsed


def _validate_complete_payload(
    payload: Mapping[str, object],
    *,
    requested_date: str | pd.Timestamp,
) -> tuple[int, int | None]:
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise ValueError("IDX Index Summary is empty; capture is not complete")
    records_total = _integer_metadata(payload, "recordsTotal")
    if records_total is None:
        raise ValueError("IDX Index Summary recordsTotal is missing; completeness is unverified")
    records_filtered = _integer_metadata(payload, "recordsFiltered")
    if records_total == 0:
        raise ValueError("IDX Index Summary recordsTotal is zero; capture is not complete")
    if len(rows) != records_total:
        raise ValueError(
            "IDX Index Summary response is partial: "
            f"rows={len(rows)} recordsTotal={records_total}"
        )
    if records_filtered is not None and records_filtered != records_total:
        raise ValueError(
            "IDX Index Summary response is filtered/partial: "
            f"recordsFiltered={records_filtered} recordsTotal={records_total}"
        )

    requested = pd.Timestamp(requested_date).normalize()
    codes: list[str] = []
    for position, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"IDX Index Summary row {position} is not an object")
        parsed = pd.to_datetime(row.get("Date"), errors="coerce")
        if pd.isna(parsed) or pd.Timestamp(parsed).normalize() != requested:
            raise ValueError(
                "IDX Index Summary row date mismatch: "
                f"requested={requested.date().isoformat()} row={row.get('Date')!r}"
            )
        code = str(row.get("IndexCode", "")).strip().upper()
        if not code:
            raise ValueError(f"IDX Index Summary row {position} has an empty IndexCode")
        codes.append(code)
    if len(set(codes)) != len(codes):
        raise ValueError("IDX Index Summary contains duplicate IndexCode rows")
    return records_total, records_filtered


@dataclass(frozen=True)
class IndexSummaryFetchMeta:
    requested_date: str
    source_ref: str
    records_total: int | None
    rows: int
    records_filtered: int | None = None
    retrieval_started_at_utc: str | None = None
    observed_available_at_utc: str | None = None
    raw_sha256: str | None = None
    completeness_status: str = "UNVERIFIED"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IndexSummaryPayloadCapture:
    payload: dict[str, object]
    source_ref: str
    raw_bytes: bytes
    endpoint: str
    params: dict[str, str]
    retrieval_started_at_utc: str
    observed_available_at_utc: str
    records_total: int
    records_filtered: int | None
    row_count: int
    completeness_status: str

    @property
    def raw_sha256(self) -> str:
        return hashlib.sha256(self.raw_bytes).hexdigest()


def fetch_index_summary_payload_capture(
    date: str | pd.Timestamp,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> IndexSummaryPayloadCapture:
    """Fetch one complete official IDX Index Summary response with raw bytes."""

    client = session or requests.Session()
    retrieval_started_at_utc = _utc_now()
    headers = _browser_headers()
    home = client.get(IDX_HOME_URL, headers=headers, timeout=timeout)
    home.raise_for_status()
    validation = client.get(
        IDX_SESSION_VALIDATION_URL,
        headers=headers,
        timeout=timeout,
    )
    validation.raise_for_status()

    url = index_summary_url(date)
    response = client.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("IDX Index Summary response is not an object")
    records_total, records_filtered = _validate_complete_payload(
        payload,
        requested_date=date,
    )
    raw_bytes = bytes(response.content)
    observed_available_at_utc = _utc_now()
    return IndexSummaryPayloadCapture(
        payload=payload,
        source_ref=str(getattr(response, "url", "") or url),
        raw_bytes=raw_bytes,
        endpoint=IDX_INDEX_SUMMARY_URL,
        params={"date": pd.Timestamp(date).normalize().strftime("%Y%m%d")},
        retrieval_started_at_utc=retrieval_started_at_utc,
        observed_available_at_utc=observed_available_at_utc,
        records_total=records_total,
        records_filtered=records_filtered,
        row_count=len(payload["data"]),
        completeness_status="COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
    )


def parse_index_summary_payload(
    payload: Mapping[str, object],
    *,
    requested_date: str | pd.Timestamp,
    source_ref: str,
    source_sha256: str,
    retrieved_at: str | pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, IndexSummaryFetchMeta]:
    """Validate and normalize official index rows without assigning PIT time."""

    records_total, records_filtered = _validate_complete_payload(
        payload,
        requested_date=requested_date,
    )
    rows = payload["data"]
    data = pd.DataFrame(rows).copy()
    missing = set(INDEX_FIELDS) - set(data.columns)
    if missing:
        raise ValueError(f"IDX Index Summary fields missing: {sorted(missing)}")
    requested = pd.Timestamp(requested_date).normalize()
    data["session_date"] = pd.to_datetime(data["Date"], errors="coerce").dt.normalize()
    numeric = [
        "Previous", "Highest", "Lowest", "Close", "Change", "Volume", "Value",
        "Frequency", "MarketCapital", "NumberOfStock",
    ]
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].isna().any():
            raise ValueError(f"IDX Index Summary {column} contains invalid values")
    if (data[["Previous", "Highest", "Lowest", "Close"]] < 0).any().any():
        raise ValueError("IDX Index Summary prices cannot be negative")
    if (data["Highest"] < data[["Lowest", "Close"]].max(axis=1)).any():
        raise ValueError("IDX Index Summary High is below Low or Close")
    if (data["Lowest"] > data[["Highest", "Close"]].min(axis=1)).any():
        raise ValueError("IDX Index Summary Low is above High or Close")
    if (data[["Volume", "Value", "Frequency", "MarketCapital", "NumberOfStock"]] < 0).any().any():
        raise ValueError("IDX Index Summary aggregate fields cannot be negative")
    if (data["NumberOfStock"] % 1 != 0).any():
        raise ValueError("IDX Index Summary NumberOfStock must be integer-valued")
    if data["session_date"].ne(requested).any():
        raise ValueError("IDX Index Summary contains a date outside the requested session")

    result = pd.DataFrame(
        {
            "session_date": data["session_date"],
            "index_code": data["IndexCode"].astype(str).str.strip().str.upper(),
            "previous": data["Previous"].astype(float),
            "high": data["Highest"].astype(float),
            "low": data["Lowest"].astype(float),
            "close": data["Close"].astype(float),
            "change": data["Change"].astype(float),
            "volume": data["Volume"].astype(float),
            "trading_value_idr": data["Value"].astype(float),
            "frequency": data["Frequency"].astype(float),
            "market_capital_idr": data["MarketCapital"].astype(float),
            "number_of_stock": data["NumberOfStock"].astype(int),
            "source": "IDX_OFFICIAL",
            "source_ref": source_ref,
            "source_sha256": source_sha256,
            "source_retrieved_at": pd.NaT if retrieved_at is None else pd.to_datetime(retrieved_at, utc=True),
            "knowledge_at": pd.NaT,
            "pit_timing_status": "UNRESOLVED_NO_PUBLICATION_TIMESTAMP",
        }
    )
    return (
        result.sort_values(["session_date", "index_code"]).reset_index(drop=True),
        IndexSummaryFetchMeta(
            requested_date=requested.date().isoformat(),
            source_ref=source_ref,
            records_total=records_total,
            rows=len(result),
            records_filtered=records_filtered,
            completeness_status="COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
        ),
    )


def fetch_index_summary_snapshot(
    date: str | pd.Timestamp,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
    include_capture: bool = False,
) -> tuple[pd.DataFrame, IndexSummaryFetchMeta] | tuple[
    pd.DataFrame, IndexSummaryFetchMeta, IndexSummaryPayloadCapture
]:
    capture = fetch_index_summary_payload_capture(
        date,
        session=session,
        timeout=timeout,
    )
    frame, meta = parse_index_summary_payload(
        capture.payload,
        requested_date=date,
        source_ref=capture.source_ref,
        source_sha256=capture.raw_sha256,
        retrieved_at=capture.observed_available_at_utc,
    )
    meta = replace(
        meta,
        retrieval_started_at_utc=capture.retrieval_started_at_utc,
        observed_available_at_utc=capture.observed_available_at_utc,
        raw_sha256=capture.raw_sha256,
    )
    if include_capture:
        return frame, meta, capture
    return frame, meta
