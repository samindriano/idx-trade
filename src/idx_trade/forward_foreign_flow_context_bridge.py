"""Bounded, outcome-blind context bridge for Foreign Flow prospective V2.

This module does not create a second forward monitor, scheduler, model counter,
or canonical-session repair path. It exists only to bridge the small gap
between the accepted historical market panel and the existing canonical EOD
runtime. Bridge artifacts are immutable and live under their own namespace.

The implementation is deliberately self-contained relative to the accepted
Foreign Flow producer branch: it reuses the repo's official session parser,
Foreign Flow Stock Summary parser, canonical Yahoo adapter, and raw OHLCV
semantics without importing private modules from the separate operator-EOD
branch.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

import numpy as np
import pandas as pd
import requests

from .forward_foreign_flow import (
    _write_bytes_exclusive,
    _write_parquet_exclusive,
    parse_stock_summary_foreign_flow,
)
from .provenance import sha256_file
from .providers.yahoo import download_daily
from .security_master import normalise_ticker
from .session_backfill import run_exchange_session_backfill


SCHEMA_VERSION = "idx-trade/foreign-flow-forward-context-bridge-v1"
MARKET_FILENAME = "market_context.parquet"
FLOW_FILENAME = "foreign_flow.parquet"
RAW_FILENAME = "idx_stock_summary.raw.json"
MANIFEST_FILENAME = "manifest.json"

IDX_HOME_URL = "https://www.idx.id/id"
IDX_SESSION_VALIDATION_URL = "https://www.idx.id/primary/home/GetIndexList"
IDX_STOCK_SUMMARY_URL = "https://www.idx.id/primary/TradingSummary/GetStockSummary"

_FORBIDDEN_TOKENS = (
    "binary_target",
    "label_status",
    "outcome",
    "tp_first",
    "sl_first",
    "realized",
)


@dataclass(frozen=True)
class _StockSummaryCapture:
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


def _date(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"invalid date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _read_calendar(path: Path) -> pd.DatetimeIndex:
    if not path.is_file():
        raise FileNotFoundError(f"bridge official calendar is missing: {path}")
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError("bridge official calendar has no date column")
    values = pd.to_datetime(frame["date"], errors="coerce")
    if values.isna().any():
        raise RuntimeError("bridge official calendar contains malformed dates")
    dates = pd.DatetimeIndex(values).tz_localize(None).normalize().sort_values()
    if len(dates) == 0 or dates.has_duplicates:
        raise RuntimeError("bridge official calendar is empty or duplicated")
    return dates


def _write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> bool:
    data = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n").encode(
        "utf-8"
    )
    return _write_bytes_exclusive(path, data)


def _bridge_root(runtime_root: str | Path) -> Path:
    return Path(runtime_root).expanduser().resolve() / "forward_monitoring" / "context_bridge"


def bridge_calendar_dir(runtime_root: str | Path, start: object, end: object) -> Path:
    first = _date(start).date().isoformat()
    last = _date(end).date().isoformat()
    return _bridge_root(runtime_root) / "calendar" / "ranges" / f"{first}_{last}"


def bridge_session_dir(runtime_root: str | Path, session_date: object) -> Path:
    return _bridge_root(runtime_root) / "sessions" / _date(session_date).date().isoformat()


def sync_context_bridge_calendar(
    runtime_root: str | Path,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    *,
    fetch_month=None,
) -> dict[str, Any]:
    """Create one immutable official IDX session-calendar range for bridge use."""

    start_ts = _date(start)
    end_ts = _date(end)
    if end_ts < start_ts:
        raise ValueError("end precedes start")
    final_dir = bridge_calendar_dir(runtime_root, start_ts, end_ts)
    calendar = final_dir / "exchange_sessions.csv"
    summary = final_dir / "exchange_session_summary.json"
    sources = final_dir / "exchange_session_sources.csv"

    if calendar.exists() or summary.exists() or sources.exists():
        if not (calendar.is_file() and summary.is_file() and sources.is_file()):
            raise RuntimeError("immutable bridge calendar range is incomplete")
        payload = json.loads(summary.read_text(encoding="utf-8"))
        if payload.get("complete") is not True:
            raise RuntimeError("existing bridge calendar range is not complete")
        sessions = _read_calendar(calendar)
        return {
            "status": "BRIDGE_CALENDAR_READY",
            "created": False,
            "start": start_ts.date().isoformat(),
            "end": end_ts.date().isoformat(),
            "sessions": int(len(sessions)),
            "calendar_path": str(calendar),
            "calendar_sha256": sha256_file(calendar),
            "summary_path": str(summary),
            "summary_sha256": sha256_file(summary),
            "sources_path": str(sources),
            "sources_sha256": sha256_file(sources),
        }

    temporary = final_dir.with_name(f".{final_dir.name}.{uuid4().hex}.tmp")
    temporary.mkdir(parents=True, exist_ok=False)
    try:
        kwargs: dict[str, Any] = {}
        if fetch_month is not None:
            kwargs["fetch_month"] = fetch_month
        result = run_exchange_session_backfill(start_ts, end_ts, temporary, **kwargs)
        if result.get("complete") is not True:
            raise RuntimeError(f"official bridge calendar sync incomplete: {result}")
        produced_calendar = temporary / "exchange_sessions.csv"
        produced_summary = temporary / "exchange_session_summary.json"
        produced_sources = temporary / "exchange_session_sources.csv"
        sessions = _read_calendar(produced_calendar)
        final_dir.mkdir(parents=True, exist_ok=True)
        for produced, target in (
            (produced_calendar, calendar),
            (produced_summary, summary),
            (produced_sources, sources),
        ):
            if not _write_bytes_exclusive(target, produced.read_bytes()):
                if target.read_bytes() != produced.read_bytes():
                    raise RuntimeError(f"immutable bridge calendar revision conflict: {target}")
        return {
            "status": "BRIDGE_CALENDAR_READY",
            "created": True,
            "start": start_ts.date().isoformat(),
            "end": end_ts.date().isoformat(),
            "sessions": int(len(sessions)),
            "calendar_path": str(calendar),
            "calendar_sha256": sha256_file(calendar),
            "summary_path": str(summary),
            "summary_sha256": sha256_file(summary),
            "sources_path": str(sources),
            "sources_sha256": sha256_file(sources),
        }
    finally:
        if temporary.exists():
            for path in sorted(temporary.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                elif path.is_dir():
                    path.rmdir()
            temporary.rmdir()


def _metadata_integer(value: object, *, name: str, required: bool = True) -> int | None:
    if value is None:
        if required:
            raise ValueError(f"Stock Summary {name} is missing")
        return None
    if isinstance(value, bool):
        raise ValueError(f"Stock Summary {name} is invalid")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Stock Summary {name} is not an integer") from error
    if parsed < 0:
        raise ValueError(f"Stock Summary {name} is negative")
    return parsed


def _fetch_stock_summary_capture(
    session_date: str | pd.Timestamp,
    *,
    client: requests.Session | None = None,
    timeout: int = 30,
) -> _StockSummaryCapture:
    """Fetch one complete official Stock Summary snapshot with raw response bytes."""

    session = _date(session_date)
    http = client or requests.Session()
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Referer": "https://www.idx.id/",
        "User-Agent": "Mozilla/5.0 idx-trade-research/2.0",
        "X-Requested-With": "XMLHttpRequest",
    }
    started = _utc_now()
    home = http.get(IDX_HOME_URL, headers=headers, timeout=timeout)
    home.raise_for_status()
    validation = http.get(IDX_SESSION_VALIDATION_URL, headers=headers, timeout=timeout)
    validation.raise_for_status()
    params = {"date": session.strftime("%Y%m%d")}
    response = http.get(IDX_STOCK_SUMMARY_URL, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as error:
        raise ValueError("IDX Stock Summary response is not JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("IDX Stock Summary response is not an object")
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise ValueError("IDX Stock Summary is empty")
    total = _metadata_integer(payload.get("recordsTotal"), name="recordsTotal")
    filtered = _metadata_integer(payload.get("recordsFiltered"), name="recordsFiltered", required=False)
    assert total is not None
    if total <= 0 or len(rows) != total:
        raise ValueError(f"IDX Stock Summary response is partial: rows={len(rows)} recordsTotal={total}")
    if filtered is not None and filtered != total:
        raise ValueError(
            f"IDX Stock Summary response is filtered/partial: recordsFiltered={filtered} recordsTotal={total}"
        )
    seen: set[str] = set()
    for position, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise ValueError(f"IDX Stock Summary row {position} is not an object")
        day = pd.to_datetime(raw.get("Date"), errors="coerce")
        if pd.isna(day) or pd.Timestamp(day).tz_localize(None).normalize() != session:
            raise ValueError(f"IDX Stock Summary date mismatch at row {position}")
        ticker = normalise_ticker(raw.get("StockCode", ""))
        if not ticker or not pd.Series([ticker]).str.fullmatch(r"[A-Z0-9]{4,5}").iloc[0]:
            raise ValueError(f"IDX Stock Summary invalid StockCode at row {position}")
        if ticker in seen:
            raise ValueError(f"IDX Stock Summary duplicate StockCode {ticker}")
        seen.add(ticker)
    return _StockSummaryCapture(
        payload=payload,
        source_ref=str(getattr(response, "url", "") or f"{IDX_STOCK_SUMMARY_URL}?date={params['date']}"),
        raw_bytes=bytes(response.content),
        endpoint=IDX_STOCK_SUMMARY_URL,
        params=params,
        retrieval_started_at_utc=started,
        observed_available_at_utc=_utc_now(),
        records_total=total,
        records_filtered=filtered,
        row_count=len(rows),
        completeness_status="COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
    )


def _number(value: object) -> float | None:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed) or not np.isfinite(float(parsed)):
        return None
    return float(parsed)


def _active_regular_values(payload: Mapping[str, object], session: pd.Timestamp) -> dict[str, float]:
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError("Stock Summary data is not a list")
    result: dict[str, float] = {}
    unresolved: list[str] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            continue
        ticker = normalise_ticker(raw.get("StockCode", ""))
        if not ticker or len(ticker) != 4:
            continue
        day = pd.to_datetime(raw.get("Date"), errors="coerce")
        if pd.isna(day) or pd.Timestamp(day).tz_localize(None).normalize() != session:
            raise ValueError(f"Stock Summary date mismatch for {ticker}")
        volume = _number(raw.get("Volume"))
        frequency = _number(raw.get("Frequency"))
        regular_value = _number(raw.get("Value"))
        if volume is None or frequency is None or volume < 0 or frequency < 0:
            unresolved.append(ticker)
            continue
        if volume > 0 and frequency > 0:
            if regular_value is None or regular_value < 0:
                unresolved.append(ticker)
                continue
            result[ticker] = regular_value
        elif not (volume == 0 and frequency == 0):
            unresolved.append(ticker)
    if unresolved:
        raise RuntimeError(
            f"bridge Stock Summary has unresolved regular-market state for {len(unresolved)} tickers; "
            f"sample={sorted(unresolved)[:20]}"
        )
    if not result:
        raise RuntimeError("bridge Stock Summary has no ACTIVE regular-market rows")
    return result


def _raw_price_row(path: Path, session: pd.Timestamp) -> pd.Series | None:
    if not path.is_file():
        return None
    try:
        frame = pd.read_parquet(path)
    except Exception:
        return None
    if "date" not in frame.columns:
        return None
    dates = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    selected = frame.loc[dates.eq(session)]
    return None if selected.empty else selected.iloc[-1]


def _row_evidence_sha256(ticker: str, session: pd.Timestamp, row: pd.Series) -> str:
    fields = {}
    for column in ("raw_open", "raw_high", "raw_low", "raw_close", "raw_volume"):
        value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
        fields[column] = None if pd.isna(value) else float(value)
    payload = json.dumps(
        {"ticker": ticker, "session_date": session.date().isoformat(), **fields},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _price_payload(
    ticker: str,
    row: pd.Series,
    session: pd.Timestamp,
    regular_value: float,
    *,
    source: str,
    source_ref: str,
    source_sha256: str | None = None,
) -> dict[str, object]:
    required = ("raw_open", "raw_high", "raw_low", "raw_close", "raw_volume")
    values: dict[str, float] = {}
    for column in required:
        parsed = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
        if pd.isna(parsed) or not np.isfinite(float(parsed)):
            raise RuntimeError(f"price row for {ticker} missing/invalid {column}")
        values[column] = float(parsed)
    if any(values[column] <= 0 for column in required[:-1]):
        raise RuntimeError(f"price row for {ticker} has non-positive OHLC")
    if values["raw_volume"] < 0:
        raise RuntimeError(f"price row for {ticker} has negative volume")
    if values["raw_low"] > min(values["raw_open"], values["raw_close"]):
        raise RuntimeError(f"price row for {ticker} low is above open/close")
    if values["raw_high"] < max(values["raw_open"], values["raw_close"]):
        raise RuntimeError(f"price row for {ticker} high is below open/close")
    return {
        "ticker": ticker,
        "session_date": session,
        "high": values["raw_high"],
        "low": values["raw_low"],
        "close": values["raw_close"],
        "volume": values["raw_volume"],
        "regular_market_value": float(regular_value),
        "source": source,
        "source_ref": source_ref,
        "source_sha256": source_sha256 or _row_evidence_sha256(ticker, session, row),
    }


def _download_price_batches(
    tickers: list[str],
    start: str,
    end: str,
    *,
    batch_size: int,
) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    payload: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    for offset in range(0, len(tickers), batch_size):
        batch = tickers[offset : offset + batch_size]
        try:
            result = download_daily(batch, start, end)
        except Exception as error:
            for ticker in batch:
                errors[ticker] = f"{type(error).__name__}: {error}"
            continue
        for ticker in batch:
            payload[ticker] = result.get(ticker, pd.DataFrame())
    return payload, errors


def _normalise_market(frame: pd.DataFrame, session: pd.Timestamp) -> pd.DataFrame:
    required = {"ticker", "session_date", "high", "low", "close", "volume", "regular_market_value"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"bridge market context missing columns: {sorted(missing)}")
    forbidden = [
        column for column in frame.columns if any(token in str(column).lower() for token in _FORBIDDEN_TOKENS)
    ]
    if forbidden:
        raise RuntimeError(f"bridge market context contains outcome-like columns: {sorted(forbidden)}")
    out = frame.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    out["session_date"] = pd.to_datetime(out["session_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if out["session_date"].isna().any() or not out["session_date"].eq(session).all():
        raise RuntimeError("bridge market context session mismatch")
    if out["ticker"].eq("").any() or out.duplicated(["ticker", "session_date"]).any():
        raise RuntimeError("bridge market context has invalid/duplicate identity")
    for column in ("high", "low", "close", "volume", "regular_market_value"):
        values = pd.to_numeric(out[column], errors="coerce")
        if values.isna().any() or (~np.isfinite(values)).any():
            raise RuntimeError(f"bridge market context has invalid {column}")
        out[column] = values.astype(float)
    if (out[["high", "low", "close"]] <= 0).any().any():
        raise RuntimeError("bridge market context has non-positive HLC")
    if (out[["volume", "regular_market_value"]] < 0).any().any():
        raise RuntimeError("bridge market context has negative volume/value")
    if (out["low"] > out["high"]).any():
        raise RuntimeError("bridge market context low exceeds high")
    return out.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def _normalise_flow(frame: pd.DataFrame, session: pd.Timestamp) -> pd.DataFrame:
    required = {"security_code", "session_date", "unit", "foreign_buy", "foreign_sell", "foreign_net"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"bridge Foreign Flow missing columns: {sorted(missing)}")
    out = frame.copy()
    out["security_code"] = out["security_code"].astype(str).str.upper().str.strip()
    out["session_date"] = pd.to_datetime(out["session_date"], errors="coerce", utc=True).dt.tz_localize(None).dt.normalize()
    if out["session_date"].isna().any() or not out["session_date"].eq(session).all():
        raise RuntimeError("bridge Foreign Flow session mismatch")
    if out["security_code"].eq("").any() or out.duplicated(["security_code", "session_date"]).any():
        raise RuntimeError("bridge Foreign Flow has invalid/duplicate identity")
    if not out["unit"].astype(str).eq("SHARES").all():
        raise RuntimeError("bridge Foreign Flow unit is not SHARES")
    for column in ("foreign_buy", "foreign_sell", "foreign_net"):
        values = pd.to_numeric(out[column], errors="coerce")
        if values.isna().any() or (~np.isfinite(values)).any() or (~values.eq(values.round())).any():
            raise RuntimeError(f"bridge Foreign Flow has invalid {column}")
        out[column] = values.astype("int64")
    if (out[["foreign_buy", "foreign_sell"]] < 0).any().any():
        raise RuntimeError("bridge Foreign Flow has negative buy/sell")
    if not out["foreign_net"].eq(out["foreign_buy"] - out["foreign_sell"]).all():
        raise RuntimeError("bridge Foreign Flow net identity mismatch")
    return out.sort_values("security_code", kind="mergesort").reset_index(drop=True)


def _manifest(
    *,
    session: pd.Timestamp,
    calendar_path: Path,
    calendar_sha256: str,
    raw_path: Path,
    market_path: Path,
    flow_path: Path,
    stock_capture: _StockSummaryCapture,
    flow_meta: Mapping[str, Any],
    market: pd.DataFrame,
    local_price_hits: int,
    downloaded_price_hits: int,
    download_batch_upper_bound: int,
) -> dict[str, Any]:
    return {
        "status": "FOREIGN_FLOW_CONTEXT_BRIDGE_READY",
        "schema": SCHEMA_VERSION,
        "bridge_only": True,
        "canonical_session_repair": False,
        "session_date": session.date().isoformat(),
        "calendar_path": str(calendar_path),
        "calendar_sha256": calendar_sha256,
        "source_raw_path": str(raw_path),
        "source_raw_sha256": sha256_file(raw_path),
        "market_context_path": str(market_path),
        "market_context_sha256": sha256_file(market_path),
        "foreign_flow_path": str(flow_path),
        "foreign_flow_sha256": sha256_file(flow_path),
        "stock_summary_source": {
            "endpoint": stock_capture.endpoint,
            "params": dict(stock_capture.params),
            "source_ref": stock_capture.source_ref,
            "retrieval_started_at_utc": stock_capture.retrieval_started_at_utc,
            "observed_available_at_utc": stock_capture.observed_available_at_utc,
            "records_total": int(stock_capture.records_total),
            "records_filtered": stock_capture.records_filtered,
            "row_count": int(stock_capture.row_count),
            "completeness_status": stock_capture.completeness_status,
        },
        "foreign_flow_rows": int(flow_meta["rows"]),
        "foreign_flow_unit": "SHARES",
        "market_rows": int(len(market)),
        "local_price_hits": int(local_price_hits),
        "downloaded_price_hits": int(downloaded_price_hits),
        "yahoo_download_batch_upper_bound": int(download_batch_upper_bound),
        "market_source_counts": market["source"].astype(str).value_counts().sort_index().to_dict()
        if "source" in market.columns else {},
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "outcomes_or_labels_accessed": False,
        "model_fit": False,
        "model_scoring": False,
        "scheduler_created": False,
        "counter_modified": False,
        "publication_time_known": False,
    }


def verify_context_bridge_session(
    runtime_root: str | Path,
    session_date: str | pd.Timestamp,
    *,
    calendar_path: str | Path,
    calendar_sha256: str,
) -> bool:
    try:
        session = _date(session_date)
        directory = bridge_session_dir(runtime_root, session)
        manifest_path = directory / MANIFEST_FILENAME
        raw_path = directory / RAW_FILENAME
        market_path = directory / MARKET_FILENAME
        flow_path = directory / FLOW_FILENAME
        if not all(path.is_file() for path in (manifest_path, raw_path, market_path, flow_path)):
            return False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, Mapping):
            return False
        if manifest.get("status") != "FOREIGN_FLOW_CONTEXT_BRIDGE_READY" or manifest.get("schema") != SCHEMA_VERSION:
            return False
        if manifest.get("bridge_only") is not True or manifest.get("canonical_session_repair") is not False:
            return False
        if manifest.get("outcome_blind") is not True or manifest.get("forward_outcomes_accessed") is not False:
            return False
        if manifest.get("session_date") != session.date().isoformat():
            return False
        calendar = Path(calendar_path).expanduser().resolve()
        if not calendar.is_file() or sha256_file(calendar) != calendar_sha256.lower():
            return False
        if str(manifest.get("calendar_path")) != str(calendar) or manifest.get("calendar_sha256") != calendar_sha256.lower():
            return False
        if session not in set(_read_calendar(calendar)):
            return False
        for path, key in (
            (raw_path, "source_raw_sha256"),
            (market_path, "market_context_sha256"),
            (flow_path, "foreign_flow_sha256"),
        ):
            if manifest.get(key) != sha256_file(path):
                return False
        market = _normalise_market(pd.read_parquet(market_path), session)
        flow = _normalise_flow(pd.read_parquet(flow_path), session)
        if int(manifest.get("market_rows", -1)) != len(market):
            return False
        if int(manifest.get("foreign_flow_rows", -1)) != len(flow):
            return False
        source = manifest.get("stock_summary_source")
        if not isinstance(source, Mapping) or source.get("completeness_status") != "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE":
            return False
        if int(source.get("records_total", -1)) != len(flow):
            return False
        raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
        if not isinstance(raw_payload, Mapping) or int(raw_payload.get("recordsTotal", -1)) != len(flow):
            return False
        return True
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError):
        return False


def load_context_bridge_session(
    runtime_root: str | Path,
    session_date: str | pd.Timestamp,
    *,
    calendar_path: str | Path,
    calendar_sha256: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    session = _date(session_date)
    if not verify_context_bridge_session(
        runtime_root,
        session,
        calendar_path=calendar_path,
        calendar_sha256=calendar_sha256,
    ):
        raise RuntimeError(f"bridge session is not verified: {session.date().isoformat()}")
    directory = bridge_session_dir(runtime_root, session)
    market = _normalise_market(pd.read_parquet(directory / MARKET_FILENAME), session)
    flow = _normalise_flow(pd.read_parquet(directory / FLOW_FILENAME), session)
    manifest_path = directory / MANIFEST_FILENAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return market, flow, {
        "kind": "BRIDGE_ONLY",
        "session_date": session.date().isoformat(),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "source_raw_path": str(directory / RAW_FILENAME),
        "source_raw_sha256": sha256_file(directory / RAW_FILENAME),
        "market_context_path": str(directory / MARKET_FILENAME),
        "market_context_sha256": sha256_file(directory / MARKET_FILENAME),
        "foreign_flow_path": str(directory / FLOW_FILENAME),
        "foreign_flow_sha256": sha256_file(directory / FLOW_FILENAME),
        "stock_summary_source": manifest["stock_summary_source"],
        "canonical_session_repair": False,
    }


def capture_context_bridge_session(
    runtime_root: str | Path,
    session_date: str | pd.Timestamp,
    *,
    calendar_path: str | Path,
    calendar_sha256: str,
    batch_size: int = 100,
) -> dict[str, Any]:
    """Capture one immutable bridge-only market/Foreign-Flow context session."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    session = _date(session_date)
    calendar = Path(calendar_path).expanduser().resolve()
    if not calendar.is_file() or sha256_file(calendar) != calendar_sha256.lower():
        raise RuntimeError("bridge calendar hash mismatch")
    if session not in set(_read_calendar(calendar)):
        raise RuntimeError("bridge session is absent from official calendar")

    if verify_context_bridge_session(
        runtime_root,
        session,
        calendar_path=calendar,
        calendar_sha256=calendar_sha256,
    ):
        directory = bridge_session_dir(runtime_root, session)
        return {
            "status": "FOREIGN_FLOW_CONTEXT_BRIDGE_READY",
            "session_date": session.date().isoformat(),
            "created": False,
            "manifest_path": str(directory / MANIFEST_FILENAME),
            "manifest_sha256": sha256_file(directory / MANIFEST_FILENAME),
        }

    directory = bridge_session_dir(runtime_root, session)
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError("incomplete/revision-conflicting bridge session already exists")

    # Build and validate everything before creating final bridge files. A failed
    # provider/price attempt therefore cannot strand a partial final session.
    stock_capture = _fetch_stock_summary_capture(session)
    raw_sha = hashlib.sha256(stock_capture.raw_bytes).hexdigest()
    flow, flow_meta = parse_stock_summary_foreign_flow(
        stock_capture.payload,
        session_date=session,
        knowledge_at_utc=stock_capture.observed_available_at_utc,
        source_ref=stock_capture.source_ref,
        source_sha256=raw_sha,
    )
    flow = _normalise_flow(flow, session)
    regular_values = _active_regular_values(stock_capture.payload, session)
    active = sorted(regular_values)

    raw_price_root = Path(runtime_root).expanduser().resolve() / "prices" / "raw"
    price_rows: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    local_hits = 0
    for ticker in active:
        raw_price = raw_price_root / f"{ticker}.parquet"
        row = _raw_price_row(raw_price, session)
        if row is None:
            missing.append(ticker)
            continue
        price_rows[ticker] = _price_payload(
            ticker,
            row,
            session,
            regular_values[ticker],
            source="YAHOO_YFINANCE_RAW_OHLCV",
            source_ref=f"https://finance.yahoo.com/quote/{ticker}.JK/history",
            source_sha256=sha256_file(raw_price),
        )
        local_hits += 1

    downloaded_hits = 0
    download_errors: dict[str, str] = {}
    if missing:
        payload, download_errors = _download_price_batches(
            missing,
            session.date().isoformat(),
            (session + pd.Timedelta(days=1)).date().isoformat(),
            batch_size=batch_size,
        )
        for ticker in missing:
            frame = payload.get(ticker, pd.DataFrame())
            if frame.empty or "date" not in frame.columns:
                continue
            dates = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
            selected = frame.loc[dates.eq(session)]
            if selected.empty:
                continue
            price_rows[ticker] = _price_payload(
                ticker,
                selected.iloc[-1],
                session,
                regular_values[ticker],
                source="YAHOO_YFINANCE_AUTO_ADJUST_FALSE",
                source_ref=f"https://finance.yahoo.com/quote/{ticker}.JK/history",
            )
            downloaded_hits += 1

    missing_prices = sorted(set(active) - set(price_rows))
    if missing_prices:
        detail = {ticker: download_errors.get(ticker) for ticker in missing_prices if ticker in download_errors}
        raise RuntimeError(
            f"bridge ACTIVE tickers missing raw provider price: {missing_prices[:20]}; download_errors={detail}"
        )

    market = _normalise_market(pd.DataFrame(price_rows.values()), session)

    directory.mkdir(parents=True, exist_ok=False)
    raw_path = directory / RAW_FILENAME
    market_path = directory / MARKET_FILENAME
    flow_path = directory / FLOW_FILENAME
    manifest_path = directory / MANIFEST_FILENAME
    if not _write_bytes_exclusive(raw_path, stock_capture.raw_bytes):
        raise RuntimeError("unexpected bridge raw Stock Summary preexistence")
    if not _write_parquet_exclusive(market, market_path):
        raise RuntimeError("unexpected bridge market artifact preexistence")
    if not _write_parquet_exclusive(flow, flow_path):
        raise RuntimeError("unexpected bridge Foreign Flow artifact preexistence")
    manifest = _manifest(
        session=session,
        calendar_path=calendar,
        calendar_sha256=calendar_sha256.lower(),
        raw_path=raw_path,
        market_path=market_path,
        flow_path=flow_path,
        stock_capture=stock_capture,
        flow_meta=flow_meta,
        market=market,
        local_price_hits=local_hits,
        downloaded_price_hits=downloaded_hits,
        download_batch_upper_bound=math.ceil(len(missing) / batch_size) if missing else 0,
    )
    if not _write_json_exclusive(manifest_path, manifest):
        raise RuntimeError("unexpected bridge manifest preexistence")
    if not verify_context_bridge_session(
        runtime_root,
        session,
        calendar_path=calendar,
        calendar_sha256=calendar_sha256,
    ):
        raise RuntimeError("new bridge session failed verification")
    return {
        "status": "FOREIGN_FLOW_CONTEXT_BRIDGE_READY",
        "session_date": session.date().isoformat(),
        "created": True,
        "market_rows": int(len(market)),
        "foreign_flow_rows": int(len(flow)),
        "local_price_hits": int(local_hits),
        "downloaded_price_hits": int(downloaded_hits),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "canonical_session_repair": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Foreign Flow bounded forward context bridge")
    sub = parser.add_subparsers(dest="command", required=True)
    calendar = sub.add_parser("sync-calendar")
    calendar.add_argument("--runtime-root", type=Path, required=True)
    calendar.add_argument("--start", required=True)
    calendar.add_argument("--end", required=True)
    capture = sub.add_parser("capture-session")
    capture.add_argument("--runtime-root", type=Path, required=True)
    capture.add_argument("--date", required=True)
    capture.add_argument("--calendar", type=Path, required=True)
    capture.add_argument("--calendar-sha256", required=True)
    capture.add_argument("--batch-size", type=int, default=100)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "sync-calendar":
        result = sync_context_bridge_calendar(args.runtime_root, args.start, args.end)
    else:
        result = capture_context_bridge_session(
            args.runtime_root,
            args.date,
            calendar_path=args.calendar,
            calendar_sha256=args.calendar_sha256,
            batch_size=args.batch_size,
        )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
