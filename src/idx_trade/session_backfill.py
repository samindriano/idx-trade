from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .providers.idx_sessions import fetch_exchange_sessions_month, monthly_session_page_url
from .storage import write_csv_atomic


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def _sessions_sha256(sessions: pd.DatetimeIndex) -> str:
    canonical = "\n".join(pd.Timestamp(value).date().isoformat() for value in sessions)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_exchange_session_backfill(
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    report_dir: str | Path,
    *,
    fetch_month=fetch_exchange_sessions_month,
) -> dict[str, object]:
    """Persist official IDX Exchange-Day evidence for a candidate research range."""

    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    if end_ts < start_ts:
        raise ValueError("end precedes start")

    report_dir = Path(report_dir)
    months = pd.period_range(start_ts.to_period("M"), end_ts.to_period("M"), freq="M")
    sessions: set[pd.Timestamp] = set()
    source_rows: list[dict[str, object]] = []

    for period in months:
        url = monthly_session_page_url(period.year, period.month)
        try:
            month_sessions = pd.DatetimeIndex(fetch_month(period.year, period.month))
            clipped = [
                pd.Timestamp(value).normalize()
                for value in month_sessions
                if start_ts <= pd.Timestamp(value).normalize() <= end_ts
            ]
            sessions.update(clipped)
            source_rows.append(
                {
                    "year": period.year,
                    "month": period.month,
                    "source_ref": url,
                    "status": "PARSED",
                    "sessions_in_requested_range": len(clipped),
                    "error": "",
                }
            )
        except Exception as error:
            source_rows.append(
                {
                    "year": period.year,
                    "month": period.month,
                    "source_ref": url,
                    "status": "ERROR",
                    "sessions_in_requested_range": 0,
                    "error": str(error),
                }
            )

    source_report = pd.DataFrame(source_rows)
    write_csv_atomic(source_report, report_dir / "exchange_session_sources.csv")

    ordered = pd.DatetimeIndex(sorted(sessions))
    session_frame = pd.DataFrame({"date": ordered})
    write_csv_atomic(session_frame, report_dir / "exchange_sessions.csv")

    errors = int(source_report["status"].ne("PARSED").sum()) if not source_report.empty else len(months)
    summary = {
        "start": start_ts.date().isoformat(),
        "end": end_ts.date().isoformat(),
        "requested_months": len(months),
        "parsed_months": int(source_report["status"].eq("PARSED").sum()) if not source_report.empty else 0,
        "error_months": errors,
        "exchange_sessions": len(ordered),
        "first_session": ordered.min().date().isoformat() if len(ordered) else None,
        "last_session": ordered.max().date().isoformat() if len(ordered) else None,
        "sessions_sha256": _sessions_sha256(ordered),
        "complete": bool(len(ordered)) and errors == 0,
        "source": "IDX_DIGITAL_STATISTICS_DAILY_TRADING_TABLE",
    }
    _atomic_json(summary, report_dir / "exchange_session_summary.json")
    return summary
