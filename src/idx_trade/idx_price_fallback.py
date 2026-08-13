from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .data import canonicalize_ohlcv
from .providers.idx_stock_summary import fetch_stock_summary_payload
from .security_master import normalise_ticker
from .storage import merge_daily_history, write_csv_atomic, write_parquet_atomic


PayloadFetcher = Callable[[pd.Timestamp], tuple[dict[str, object], str]]


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def _number(value: object) -> float | None:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return None if pd.isna(parsed) else float(parsed)


def stock_summary_price_rows(
    payload: Mapping[str, object],
    *,
    requested_date: str | pd.Timestamp,
    source_ref: str,
    tickers: list[str] | tuple[str, ...] | set[str] | None = None,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Extract execution-safe OHLCV from official IDX Stock Summary rows.

    This is a secondary price source used only when the primary Yahoo provider
    has no historical rows. A row is eligible only when the same official
    Stock Summary record proves positive Regular-Market Volume and Frequency.

    `OpenPrice` is preferred. Some official rows have no opening-auction price;
    when `OpenPrice` is zero/missing, a positive `FirstTrade` is accepted as the
    session opening execution price. Rows with no defensible positive opening
    execution price remain unresolved instead of being synthesized.

    Diagnostics deliberately distinguish an opening-only gap from missing or
    invalid H/L/C. That distinction does not relax the execution-safe OHLCV
    contract; it exists so research-feasibility audits can measure how much
    otherwise authoritative H/L/C evidence remains available when Open is not.
    """

    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError("IDX stock-summary response has no list-valued data field")

    requested = pd.Timestamp(requested_date).normalize()
    selected = (
        {normalise_ticker(value) for value in tickers}
        if tickers is not None
        else None
    )
    raw_by_ticker: dict[str, list[dict[str, object]]] = {}
    diagnostics: list[dict[str, object]] = []

    for raw in rows:
        if not isinstance(raw, Mapping):
            continue
        ticker = normalise_ticker(raw.get("StockCode", ""))
        if not ticker or not pd.Series([ticker]).str.fullmatch(r"[A-Z0-9]{4}").iloc[0]:
            continue
        if selected is not None and ticker not in selected:
            continue

        raw_date = pd.to_datetime(raw.get("Date"), errors="coerce")
        day = requested if pd.isna(raw_date) else pd.Timestamp(raw_date).tz_localize(None).normalize()
        if day != requested:
            continue

        volume = _number(raw.get("Volume"))
        frequency = _number(raw.get("Frequency"))
        if volume is None or frequency is None or volume <= 0 or frequency <= 0:
            diagnostics.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "status": "NOT_ACTIVE_PRICE_ROW",
                    "diagnostic": "REGULAR_VOLUME_FREQUENCY_NOT_POSITIVE",
                    "source_ref": source_ref,
                }
            )
            continue

        open_price = _number(raw.get("OpenPrice"))
        first_trade = _number(raw.get("FirstTrade"))
        high = _number(raw.get("High"))
        low = _number(raw.get("Low"))
        close = _number(raw.get("Close"))
        opening = (
            open_price
            if open_price is not None and open_price > 0
            else first_trade
            if first_trade is not None and first_trade > 0
            else None
        )
        hlc_valid = all(value is not None and value > 0 for value in (high, low, close))
        if opening is None or not hlc_valid:
            if opening is None and hlc_valid:
                diagnostic = "OFFICIAL_OPEN_MISSING_OR_NONPOSITIVE"
            elif opening is not None and not hlc_valid:
                diagnostic = "OFFICIAL_HLC_MISSING_OR_NONPOSITIVE"
            else:
                diagnostic = "OFFICIAL_OPEN_AND_HLC_MISSING_OR_NONPOSITIVE"
            diagnostics.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "status": "UNRESOLVED_PRICE",
                    "diagnostic": diagnostic,
                    "source_ref": source_ref,
                }
            )
            continue
        if high < max(opening, close, low) or low > min(opening, close, high):
            diagnostics.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "status": "UNRESOLVED_PRICE",
                    "diagnostic": "OFFICIAL_OHLC_ENVELOPE_INVALID",
                    "source_ref": source_ref,
                }
            )
            continue

        raw_by_ticker.setdefault(ticker, []).append(
            {
                "date": day,
                "open": opening,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )
        diagnostics.append(
            {
                "ticker": ticker,
                "date": day,
                "status": "PRICE_PARSED",
                "diagnostic": (
                    "OPENPRICE"
                    if open_price is not None and open_price > 0
                    else "FIRSTTRADE_FALLBACK"
                ),
                "source_ref": source_ref,
            }
        )

    frames: dict[str, pd.DataFrame] = {}
    for ticker, values in raw_by_ticker.items():
        canonical = canonicalize_ohlcv(pd.DataFrame(values), ticker)
        canonical["price_source"] = "IDX_PUBLIC_STOCK_SUMMARY"
        canonical["price_source_ref"] = source_ref
        frames[ticker] = canonical

    diagnostic_frame = pd.DataFrame(
        diagnostics,
        columns=("ticker", "date", "status", "diagnostic", "source_ref"),
    )
    return frames, diagnostic_frame


def backfill_missing_prices_from_idx_stock_summary(
    tickers: list[str],
    exchange_sessions: pd.DatetimeIndex,
    raw_dir: str | Path,
    report_dir: str | Path,
    *,
    fetcher: PayloadFetcher = fetch_stock_summary_payload,
) -> dict[str, object]:
    """Fill only absent raw-price dates from official IDX Stock Summary.

    Existing provider rows are immutable and are never replaced by this fallback.
    The caller should pass only the exact missing ACTIVE sessions discovered by
    the DATA GATE. Each official session is fetched once and all requested
    tickers are extracted from the same payload.
    """

    symbols = sorted({normalise_ticker(value) for value in tickers})
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(exchange_sessions))
        .dropna()
        .tz_localize(None)
        .normalize()
        .unique()
        .sort_values()
    )
    if not symbols:
        raise ValueError("At least one ticker is required for IDX price fallback")
    if len(sessions) == 0:
        raise ValueError("At least one exchange session is required for IDX price fallback")

    incoming: dict[str, list[pd.DataFrame]] = {ticker: [] for ticker in symbols}
    diagnostics: list[pd.DataFrame] = []
    fetch_errors: list[dict[str, object]] = []

    for session in sessions:
        day = pd.Timestamp(session).normalize()
        try:
            payload, source_ref = fetcher(day)
            frames, diag = stock_summary_price_rows(
                payload,
                requested_date=day,
                source_ref=source_ref,
                tickers=symbols,
            )
            diagnostics.append(diag)
            for ticker, frame in frames.items():
                incoming[ticker].append(frame)
        except Exception as error:
            fetch_errors.append(
                {
                    "date": day,
                    "status": "FETCH_ERROR",
                    "error": f"{type(error).__name__}: {error}",
                }
            )

    report_rows: list[dict[str, object]] = []
    raw_root = Path(raw_dir)
    for ticker in symbols:
        path = raw_root / f"{ticker}.parquet"
        existing = pd.read_parquet(path) if path.is_file() else pd.DataFrame()
        candidate = (
            pd.concat(incoming[ticker], ignore_index=True)
            if incoming[ticker]
            else pd.DataFrame()
        )
        if candidate.empty:
            report_rows.append(
                {
                    "ticker": ticker,
                    "status": "NO_OFFICIAL_PRICE_ROWS",
                    "existing_rows": int(len(existing)),
                    "candidate_rows": 0,
                    "filled_rows": 0,
                    "stored_rows": int(len(existing)),
                }
            )
            continue

        candidate["date"] = pd.to_datetime(candidate["date"]).dt.normalize()
        existing_dates = (
            set(pd.to_datetime(existing["date"]).dt.normalize())
            if not existing.empty and "date" in existing.columns
            else set()
        )
        fill = candidate[~candidate["date"].isin(existing_dates)].copy()
        fill = fill.sort_values("date").drop_duplicates("date", keep="last")
        merged, _ = merge_daily_history(existing, fill, ticker, allow_revisions=False)
        write_parquet_atomic(merged, path)
        report_rows.append(
            {
                "ticker": ticker,
                "status": "UPDATED" if len(fill) else "NO_MISSING_ROWS",
                "existing_rows": int(len(existing)),
                "candidate_rows": int(len(candidate)),
                "filled_rows": int(len(fill)),
                "stored_rows": int(len(merged)),
            }
        )

    report = pd.DataFrame(report_rows)
    diagnostic_frame = (
        pd.concat(diagnostics, ignore_index=True)
        if diagnostics
        else pd.DataFrame(columns=("ticker", "date", "status", "diagnostic", "source_ref"))
    )
    fetch_error_frame = pd.DataFrame(fetch_errors, columns=("date", "status", "error"))
    target = Path(report_dir)
    write_csv_atomic(report, target / "idx_price_fallback_report.csv")
    write_csv_atomic(diagnostic_frame, target / "idx_price_fallback_diagnostics.csv")
    write_csv_atomic(fetch_error_frame, target / "idx_price_fallback_fetch_errors.csv")

    summary = {
        "requested_tickers": len(symbols),
        "requested_sessions": int(len(sessions)),
        "fetch_errors": int(len(fetch_error_frame)),
        "updated_tickers": int(report["status"].eq("UPDATED").sum()) if not report.empty else 0,
        "filled_rows": int(report["filled_rows"].sum()) if not report.empty else 0,
        "unresolved_price_rows": int(
            diagnostic_frame["status"].eq("UNRESOLVED_PRICE").sum()
        ) if not diagnostic_frame.empty else 0,
        "price_source": "IDX_PUBLIC_STOCK_SUMMARY",
        "note": (
            "This fallback fills absent primary-provider dates only. Existing provider rows "
            "are never replaced, and missing/invalid official OHLC remains unresolved."
        ),
    }
    _atomic_json(summary, target / "idx_price_fallback_summary.json")
    return summary
