from __future__ import annotations

import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pandas as pd

from .providers.yahoo import download_daily
from .security_master import normalise_ticker
from .storage import DataRevisionConflict, merge_daily_history, write_csv_atomic, write_parquet_atomic


Downloader = Callable[[list[str], str, str | None], dict[str, pd.DataFrame]]


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def run_price_backfill(
    tickers: list[str],
    start: str,
    end: str | None,
    raw_dir: str | Path,
    report_dir: str | Path,
    *,
    downloader: Downloader = download_daily,
    allow_revisions: bool = False,
) -> dict[str, object]:
    """Download and persist canonical daily price histories with revision guards.

    Existing mature history is never silently rewritten. Provider revisions are
    reported as conflicts unless an explicit audited migration enables them.
    """

    raw_dir = Path(raw_dir)
    report_dir = Path(report_dir)
    symbols = sorted({normalise_ticker(value) for value in tickers})
    downloaded = downloader(symbols, start, end)
    rows: list[dict[str, object]] = []

    for ticker in symbols:
        incoming = downloaded.get(ticker, pd.DataFrame())
        path = raw_dir / f"{ticker}.parquet"
        existing = pd.read_parquet(path) if path.exists() else pd.DataFrame()
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
                "first_date": pd.to_datetime(merged["date"]).min().date().isoformat(),
                "last_date": pd.to_datetime(merged["date"]).max().date().isoformat(),
            }
        )

    report = pd.DataFrame(rows)
    write_csv_atomic(report, report_dir / "price_backfill_report.csv")
    summary = {
        "start": start,
        "end": end,
        "requested_tickers": len(symbols),
        "updated": int(report["status"].eq("UPDATED").sum()) if not report.empty else 0,
        "no_provider_rows": int(report["status"].eq("NO_PROVIDER_ROWS").sum()) if not report.empty else 0,
        "revision_conflicts": int(report["status"].eq("REVISION_CONFLICT").sum()) if not report.empty else 0,
        "complete": bool(len(report)) and bool(report["status"].eq("UPDATED").all()),
        "note": "NO_PROVIDER_ROWS is unresolved absence, not proof of suspension or no-trade.",
    }
    _atomic_json(summary, report_dir / "price_backfill_summary.json")
    return summary
