from __future__ import annotations

import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pandas as pd

from .providers.yahoo import download_daily
from .security_master import normalise_ticker
from .storage import (
    DataRevisionConflict,
    merge_daily_history,
    write_csv_atomic,
    write_parquet_atomic,
)


Downloader = Callable[[list[str], str, str | None], dict[str, pd.DataFrame]]


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def _download_in_batches(
    symbols: list[str],
    start: str,
    end: str | None,
    *,
    downloader: Downloader,
    batch_size: int,
) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    downloaded: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    for offset in range(0, len(symbols), batch_size):
        batch = symbols[offset : offset + batch_size]
        try:
            payload = downloader(batch, start, end)
            if not isinstance(payload, dict):
                raise TypeError("Price downloader must return a ticker->DataFrame mapping")
            downloaded.update(payload)
        except Exception as error:
            message = f"{type(error).__name__}: {error}"
            for ticker in batch:
                errors[ticker] = message
    return downloaded, errors


def run_price_backfill(
    tickers: list[str],
    start: str,
    end: str | None,
    raw_dir: str | Path,
    report_dir: str | Path,
    *,
    downloader: Downloader = download_daily,
    allow_revisions: bool = False,
    batch_size: int = 100,
) -> dict[str, object]:
    """Download and persist canonical daily price histories with revision guards.

    Existing mature history is never silently rewritten. Provider revisions are
    reported as conflicts unless an explicit audited migration enables them.

    Full-market requests are downloaded in bounded batches so a transient
    provider failure cannot silently erase an entire IDX universe. A failed
    batch is reported as DOWNLOAD_ERROR for each affected ticker and remains a
    hard incomplete backfill.

    `end` follows Yahoo/yfinance semantics and is exclusive.
    """

    raw_dir = Path(raw_dir)
    report_dir = Path(report_dir)
    symbols = sorted({normalise_ticker(value) for value in tickers})
    downloaded, download_errors = _download_in_batches(
        symbols,
        start,
        end,
        downloader=downloader,
        batch_size=batch_size,
    )
    rows: list[dict[str, object]] = []

    for ticker in symbols:
        path = raw_dir / f"{ticker}.parquet"
        existing = pd.read_parquet(path) if path.exists() else pd.DataFrame()
        if ticker in download_errors:
            rows.append(
                {
                    "ticker": ticker,
                    "status": "DOWNLOAD_ERROR",
                    "existing_rows": len(existing),
                    "incoming_rows": 0,
                    "stored_rows": len(existing),
                    "revision_conflicts": 0,
                    "error": download_errors[ticker],
                }
            )
            continue

        incoming = downloaded.get(ticker, pd.DataFrame())
        if incoming.empty:
            rows.append(
                {
                    "ticker": ticker,
                    "status": "NO_PROVIDER_ROWS",
                    "existing_rows": len(existing),
                    "incoming_rows": 0,
                    "stored_rows": len(existing),
                    "revision_conflicts": 0,
                }
            )
            continue

        try:
            merged, conflicts = merge_daily_history(
                existing,
                incoming,
                ticker,
                allow_revisions=allow_revisions,
            )
        except DataRevisionConflict as error:
            rows.append(
                {
                    "ticker": ticker,
                    "status": "REVISION_CONFLICT",
                    "existing_rows": len(existing),
                    "incoming_rows": len(incoming),
                    "stored_rows": len(existing),
                    "revision_conflicts": None,
                    "error": str(error),
                }
            )
            continue

        write_parquet_atomic(merged, path)
        rows.append(
            {
                "ticker": ticker,
                "status": "UPDATED",
                "existing_rows": len(existing),
                "incoming_rows": len(incoming),
                "stored_rows": len(merged),
                "revision_conflicts": len(conflicts),
                "first_date": pd.to_datetime(merged["date"])
                .min()
                .date()
                .isoformat(),
                "last_date": pd.to_datetime(merged["date"])
                .max()
                .date()
                .isoformat(),
            }
        )

    report = pd.DataFrame(rows)
    write_csv_atomic(report, report_dir / "price_backfill_report.csv")
    summary = {
        "start": start,
        "end": end,
        "requested_tickers": len(symbols),
        "batch_size": batch_size,
        "batches_requested": (len(symbols) + batch_size - 1) // batch_size if symbols else 0,
        "updated": int(report["status"].eq("UPDATED").sum())
        if not report.empty
        else 0,
        "no_provider_rows": int(report["status"].eq("NO_PROVIDER_ROWS").sum())
        if not report.empty
        else 0,
        "download_errors": int(report["status"].eq("DOWNLOAD_ERROR").sum())
        if not report.empty
        else 0,
        "revision_conflicts": int(report["status"].eq("REVISION_CONFLICT").sum())
        if not report.empty
        else 0,
        "complete": bool(len(report)) and bool(report["status"].eq("UPDATED").all()),
        "note": (
            "NO_PROVIDER_ROWS is unresolved absence, not proof of suspension or no-trade; "
            "DOWNLOAD_ERROR is a provider/request failure and never counts as coverage."
        ),
    }
    _atomic_json(summary, report_dir / "price_backfill_summary.json")
    return summary


def run_exchange_window_price_backfill(
    tickers: list[str],
    exchange_sessions: pd.DatetimeIndex,
    raw_dir: str | Path,
    report_dir: str | Path,
    *,
    downloader: Downloader = download_daily,
    allow_revisions: bool = False,
    batch_size: int = 100,
) -> dict[str, object]:
    """Backfill the inclusive official exchange-session window safely for Yahoo.

    Yahoo/yfinance treats `end` as exclusive. Derive the provider request from
    the official IDX session calendar and request through one calendar day after
    the final required exchange session so the last session cannot be omitted.
    """

    sessions = (
        pd.DatetimeIndex(pd.to_datetime(exchange_sessions))
        .tz_localize(None)
        .normalize()
        .unique()
        .sort_values()
    )
    if len(sessions) == 0:
        raise ValueError("At least one official exchange session is required")

    first_session = pd.Timestamp(sessions[0]).normalize()
    last_session = pd.Timestamp(sessions[-1]).normalize()
    provider_end_exclusive = last_session + pd.Timedelta(days=1)

    summary = run_price_backfill(
        tickers,
        first_session.date().isoformat(),
        provider_end_exclusive.date().isoformat(),
        raw_dir,
        report_dir,
        downloader=downloader,
        allow_revisions=allow_revisions,
        batch_size=batch_size,
    )
    summary.update(
        {
            "exchange_first_session": first_session.date().isoformat(),
            "exchange_last_session": last_session.date().isoformat(),
            "provider_end_exclusive": provider_end_exclusive.date().isoformat(),
            "exchange_sessions_requested": int(len(sessions)),
        }
    )
    _atomic_json(summary, Path(report_dir) / "price_backfill_summary.json")
    return summary
