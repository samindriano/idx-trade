"""Bounded, outcome-blind context bridge for Foreign Flow prospective V2.

This module does not create a second forward monitor, scheduler, model counter,
or canonical-session repair path.  It exists only to bridge the small gap
between the accepted historical market panel and the existing canonical EOD
runtime.  Bridge artifacts are immutable, live under their own namespace, and
reuse the exact IDX Stock Summary and Yahoo price semantics already used by the
canonical EOD capture engine.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

import numpy as np
import pandas as pd

from .forward_foreign_flow import (
    _write_bytes_exclusive,
    _write_parquet_exclusive,
    parse_stock_summary_foreign_flow,
)
from .forward_monitoring import _price_payload, _raw_row, runtime_paths
from .price_backfill import _download_in_batches
from .provenance import sha256_file
from .providers.idx_stock_summary import fetch_stock_summary_snapshot
from .providers.yahoo import download_daily
from .session_backfill import run_exchange_session_backfill


SCHEMA_VERSION = "idx-trade/foreign-flow-forward-context-bridge-v1"
MARKET_FILENAME = "market_context.parquet"
FLOW_FILENAME = "foreign_flow.parquet"
RAW_FILENAME = "idx_stock_summary.raw.json"
MANIFEST_FILENAME = "manifest.json"

_FORBIDDEN_TOKENS = (
    "binary_target",
    "label_status",
    "outcome",
    "tp_first",
    "sl_first",
    "realized",
)


def _date(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"invalid date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


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
    fetch_month= None,
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
    out["session_date"] = pd.to_datetime(out["session_date"], errors="coerce").dt.normalize()
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
    stock_capture: Any,
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
        if sha256_file(calendar) != calendar_sha256.lower():
            return False
        if str(manifest.get("calendar_path")) != str(calendar) or manifest.get("calendar_sha256") != calendar_sha256.lower():
            return False
        if session not in set(_read_calendar(calendar)):
            return False
        expected_hashes = (
            (raw_path, "source_raw_sha256"),
            (market_path, "market_context_sha256"),
            (flow_path, "foreign_flow_sha256"),
        )
        for path, key in expected_hashes:
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
    if sha256_file(calendar) != calendar_sha256.lower():
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
    directory.mkdir(parents=True, exist_ok=True)

    stock_result = fetch_stock_summary_snapshot(session, include_capture=True)
    if len(stock_result) != 3:
        raise RuntimeError("official Stock Summary raw capture metadata is missing")
    stock_summary, _stock_meta, stock_capture = stock_result
    raw_path = directory / RAW_FILENAME
    if not _write_bytes_exclusive(raw_path, stock_capture.raw_bytes):
        raise RuntimeError("unexpected bridge raw Stock Summary preexistence")

    flow, flow_meta = parse_stock_summary_foreign_flow(
        stock_capture.payload,
        session_date=session,
        knowledge_at_utc=stock_capture.observed_available_at_utc,
        source_ref=stock_capture.source_ref,
        source_sha256=sha256_file(raw_path),
    )
    flow = _normalise_flow(flow, session)

    summary = stock_summary.copy()
    summary["ticker"] = summary["ticker"].astype(str).str.upper().str.strip()
    summary["as_of_date"] = pd.to_datetime(summary["as_of_date"], errors="coerce").dt.normalize()
    if summary["as_of_date"].isna().any() or not summary["as_of_date"].eq(session).all():
        raise RuntimeError("Stock Summary normalized session mismatch")
    volume = pd.to_numeric(summary["volume"], errors="coerce")
    frequency = pd.to_numeric(summary["frequency"], errors="coerce")
    regular_value = pd.to_numeric(summary["regular_value"], errors="coerce")
    active_mask = volume.gt(0) & frequency.gt(0) & regular_value.notna() & regular_value.ge(0)
    active = sorted(summary.loc[active_mask, "ticker"].dropna().astype(str).unique().tolist())
    if not active:
        raise RuntimeError("bridge Stock Summary has no ACTIVE regular-market rows")
    regular_values = {
        str(row.ticker): float(row.regular_value)
        for row in summary.loc[active_mask, ["ticker", "regular_value"]].itertuples(index=False)
    }

    paths = runtime_paths(runtime_root)
    price_rows: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    local_hits = 0
    for ticker in active:
        raw_price = paths.raw_price_root / f"{ticker}.parquet"
        row = _raw_row(raw_price, session)
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
        payload, download_errors = _download_in_batches(
            missing,
            session.date().isoformat(),
            (session + pd.Timedelta(days=1)).date().isoformat(),
            downloader=download_daily,
            batch_size=batch_size,
        )
        for ticker in missing:
            frame = payload.get(ticker, pd.DataFrame())
            if frame.empty or "date" not in frame.columns:
                continue
            dates = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
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

    market = pd.DataFrame(price_rows.values()).rename(columns={"date": "session_date"})
    market = _normalise_market(market, session)
    market_path = directory / MARKET_FILENAME
    flow_path = directory / FLOW_FILENAME
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
    manifest_path = directory / MANIFEST_FILENAME
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
