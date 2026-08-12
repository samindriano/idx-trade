from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib

import pandas as pd
import requests

from ..security_master import canonicalize_tradability_anchors, normalise_ticker
from ..states import TradabilityState


IDX_HOME_URL = "https://www.idx.id/id"
IDX_SESSION_VALIDATION_URL = "https://www.idx.id/primary/home/GetIndexList"
IDX_STOCK_SUMMARY_URL = "https://www.idx.id/primary/TradingSummary/GetStockSummary"


@dataclass(frozen=True)
class StockSummaryFetchMeta:
    requested_date: str
    source_ref: str
    records_total: int | None
    rows: int
    explicit_security_status_rows: int
    regular_trade_evidence_rows: int
    records_filtered: int | None = None
    retrieval_started_at_utc: str | None = None
    observed_available_at_utc: str | None = None
    raw_sha256: str | None = None
    completeness_status: str = "UNVERIFIED"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def stock_summary_url(date: str | pd.Timestamp) -> str:
    day = pd.Timestamp(date).normalize()
    return f"{IDX_STOCK_SUMMARY_URL}?date={day.strftime('%Y%m%d')}"


def _browser_headers() -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Referer": "https://www.idx.id/",
        "User-Agent": "Mozilla/5.0 idx-trade-research/2.0",
        "X-Requested-With": "XMLHttpRequest",
    }


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _integer_metadata(payload: Mapping[str, object], name: str) -> int | None:
    value = payload.get(name)
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"IDX Stock Summary {name} is not an integer") from error
    if parsed < 0:
        raise ValueError(f"IDX Stock Summary {name} cannot be negative")
    return parsed


def _validate_complete_payload(
    payload: Mapping[str, object],
    *,
    requested_date: str | pd.Timestamp,
) -> tuple[int, int | None]:
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise ValueError("IDX Stock Summary is empty; capture is not complete")
    records_total = _integer_metadata(payload, "recordsTotal")
    if records_total is None:
        raise ValueError("IDX Stock Summary recordsTotal is missing; completeness is unverified")
    records_filtered = _integer_metadata(payload, "recordsFiltered")
    if records_total == 0:
        raise ValueError("IDX Stock Summary recordsTotal is zero; capture is not complete")
    if len(rows) != records_total:
        raise ValueError(
            "IDX Stock Summary response is partial: "
            f"rows={len(rows)} recordsTotal={records_total}"
        )
    if records_filtered is not None and records_filtered != records_total:
        raise ValueError(
            "IDX Stock Summary response is filtered/partial: "
            f"recordsFiltered={records_filtered} recordsTotal={records_total}"
        )

    requested = pd.Timestamp(requested_date).normalize()
    for position, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"IDX Stock Summary row {position} is not an object")
        parsed = pd.to_datetime(row.get("Date"), errors="coerce")
        if pd.isna(parsed) or pd.Timestamp(parsed).normalize() != requested:
            raise ValueError(
                "IDX Stock Summary row date mismatch: "
                f"requested={requested.date().isoformat()} row={row.get('Date')!r}"
            )
        ticker = normalise_ticker(row.get("StockCode", ""))
        if not ticker or not pd.Series([ticker]).str.fullmatch(r"[A-Z0-9]{4}").iloc[0]:
            raise ValueError(f"IDX Stock Summary row {position} has an invalid StockCode")

    tickers = [normalise_ticker(row.get("StockCode", "")) for row in rows]
    if len(set(tickers)) != len(tickers):
        raise ValueError("IDX Stock Summary contains duplicate StockCode rows")
    return records_total, records_filtered


@dataclass(frozen=True)
class StockSummaryPayloadCapture:
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


def fetch_stock_summary_payload(
    date: str | pd.Timestamp,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> tuple[dict[str, object], str]:
    """Fetch the official public IDX Stock Summary endpoint.

    The response is accepted only when its explicit row-count metadata proves
    that the returned date snapshot is complete.  Callers needing immutable
    raw bytes should use ``fetch_stock_summary_payload_capture``.
    """

    capture = fetch_stock_summary_payload_capture(
        date,
        session=session,
        timeout=timeout,
    )
    return capture.payload, capture.source_ref


def fetch_stock_summary_payload_capture(
    date: str | pd.Timestamp,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> StockSummaryPayloadCapture:
    """Fetch one complete official Stock Summary response with raw bytes."""

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

    url = stock_summary_url(date)
    response = client.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("IDX stock-summary response is not an object")
    records_total, records_filtered = _validate_complete_payload(
        payload,
        requested_date=date,
    )
    raw_bytes = bytes(response.content)
    observed_available_at_utc = _utc_now()
    return StockSummaryPayloadCapture(
        payload=payload,
        source_ref=str(getattr(response, "url", "") or url),
        raw_bytes=raw_bytes,
        endpoint=IDX_STOCK_SUMMARY_URL,
        params={"date": pd.Timestamp(date).normalize().strftime("%Y%m%d")},
        retrieval_started_at_utc=retrieval_started_at_utc,
        observed_available_at_utc=observed_available_at_utc,
        records_total=records_total,
        records_filtered=records_filtered,
        row_count=len(payload["data"]),
        completeness_status="COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
    )


def _number(value: object) -> float | None:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(parsed) else float(parsed)


def parse_stock_summary_payload(
    payload: Mapping[str, object],
    *,
    requested_date: str | pd.Timestamp,
    source_ref: str,
) -> tuple[pd.DataFrame, StockSummaryFetchMeta]:
    """Parse the legacy IDX Stock Summary schema without changing its semantics.

    `Volume`/`Frequency` are the regular order-book daily metrics. The
    `NonRegular*` fields are separate market metrics and are retained only as
    separate evidence; they must not be subtracted from `Volume`/`Frequency`.
    `Value` is retained as `regular_value` for market-materiality reporting.
    """

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
        day = (
            requested
            if pd.isna(raw_date)
            else pd.Timestamp(raw_date).tz_localize(None).normalize()
        )
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
                "volume": _number(row.get("Volume")),
                "frequency": _number(row.get("Frequency")),
                "regular_value": _number(row.get("Value")),
                "nonregular_volume": _number(row.get("NonRegularVolume")),
                "nonregular_frequency": _number(row.get("NonRegularFrequency")),
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
            "volume",
            "frequency",
            "regular_value",
            "nonregular_volume",
            "nonregular_frequency",
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

    regular_trade_rows = 0
    if not frame.empty:
        volume = pd.to_numeric(frame["volume"], errors="coerce")
        frequency = pd.to_numeric(frame["frequency"], errors="coerce")
        regular_trade_rows = int((volume.gt(0) & frequency.gt(0)).sum())

    meta = StockSummaryFetchMeta(
        requested_date=requested.date().isoformat(),
        source_ref=source_ref,
        records_total=records_total_value,
        rows=len(frame),
        explicit_security_status_rows=(
            int(frame["security_status_raw"].ne("").sum()) if not frame.empty else 0
        ),
        regular_trade_evidence_rows=regular_trade_rows,
    )
    return frame, meta


def fetch_stock_summary_snapshot(
    date: str | pd.Timestamp,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
    include_capture: bool = False,
) -> tuple[pd.DataFrame, StockSummaryFetchMeta] | tuple[
    pd.DataFrame, StockSummaryFetchMeta, StockSummaryPayloadCapture
]:
    capture = fetch_stock_summary_payload_capture(
        date,
        session=session,
        timeout=timeout,
    )
    frame, meta = parse_stock_summary_payload(
        capture.payload,
        requested_date=date,
        source_ref=capture.source_ref,
    )
    meta = replace(
        meta,
        records_total=capture.records_total,
        records_filtered=capture.records_filtered,
        retrieval_started_at_utc=capture.retrieval_started_at_utc,
        observed_available_at_utc=capture.observed_available_at_utc,
        raw_sha256=capture.raw_sha256,
        completeness_status=capture.completeness_status,
    )
    if include_capture:
        return frame, meta, capture
    return frame, meta


def stock_summary_regular_trade_anchors(
    frame: pd.DataFrame,
    *,
    market: str = "REGULAR",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create ACTIVE anchors from positive official regular-market metrics only."""

    required = {
        "ticker",
        "as_of_date",
        "volume",
        "frequency",
        "source",
        "source_ref",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Stock-summary columns missing: {sorted(missing)}")

    anchors: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []

    for row in frame.itertuples(index=False):
        regular_volume = pd.to_numeric(row.volume, errors="coerce")
        regular_frequency = pd.to_numeric(row.frequency, errors="coerce")

        if pd.isna(regular_volume) or pd.isna(regular_frequency):
            diagnostics.append(
                {
                    "ticker": row.ticker,
                    "as_of_date": row.as_of_date,
                    "status": "UNRESOLVED",
                    "diagnostic": "REGULAR_TRADE_METRICS_MISSING",
                }
            )
            continue

        regular_volume = float(regular_volume)
        regular_frequency = float(regular_frequency)
        if regular_volume < 0 or regular_frequency < 0:
            diagnostics.append(
                {
                    "ticker": row.ticker,
                    "as_of_date": row.as_of_date,
                    "status": "UNRESOLVED",
                    "diagnostic": "REGULAR_TRADE_METRICS_NEGATIVE",
                }
            )
            continue

        if regular_volume > 0 and regular_frequency > 0:
            anchors.append(
                {
                    "ticker": row.ticker,
                    "market": market,
                    "as_of_date": row.as_of_date,
                    "state": TradabilityState.ACTIVE.value,
                    "source": row.source,
                    "source_ref": row.source_ref,
                    "evidence_type": "IDX_STOCK_SUMMARY_REGULAR_TRADE",
                }
            )
            continue

        diagnostic = (
            "REGULAR_TRADE_METRICS_INCONSISTENT"
            if (regular_volume > 0) != (regular_frequency > 0)
            else "NO_REGULAR_TRADE_EVIDENCE"
        )
        diagnostics.append(
            {
                "ticker": row.ticker,
                "as_of_date": row.as_of_date,
                "status": "UNRESOLVED",
                "diagnostic": diagnostic,
            }
        )

    return (
        canonicalize_tradability_anchors(pd.DataFrame(anchors)),
        pd.DataFrame(
            diagnostics,
            columns=("ticker", "as_of_date", "status", "diagnostic"),
        ),
    )


def stock_summary_status_to_anchors(
    frame: pd.DataFrame,
    *,
    status_mapping: Mapping[str, str | TradabilityState],
    market: str = "REGULAR",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create anchors only from explicitly mapped IDX status values."""

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
        str(key).strip(): (
            value.value
            if isinstance(value, TradabilityState)
            else TradabilityState(str(value)).value
        )
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
