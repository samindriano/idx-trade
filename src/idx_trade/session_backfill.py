from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .providers.idx_sessions import (
    IDX_DAILY_STATISTICS_SOURCE_ID,
    IDX_DIGITAL_STATISTICS_SOURCE_ID,
    ExchangeSessionSourceResult,
    _fetch_json,
    daily_statistics_url,
    fetch_exchange_sessions_month,
    fetch_exchange_sessions_month_with_source,
    monthly_session_data_url,
)
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
    fetch_json=None,
    fetch_daily_statistics_json=None,
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
        monthly_url = monthly_session_data_url(period.year, period.month)
        daily_url = daily_statistics_url(
            pd.Timestamp(period.start_time), pd.Timestamp(period.end_time)
        )
        try:
            if fetch_month is fetch_exchange_sessions_month:
                result = fetch_exchange_sessions_month_with_source(
                    period.year,
                    period.month,
                    fetch_json=fetch_json or _fetch_json,
                    fetch_daily_statistics_json=fetch_daily_statistics_json,
                )
                month_sessions = result.sessions
                source_identity = result.source_identity
                source_ref = result.source_ref
                fallback_reason = result.fallback_reason
                attempted_identities = result.attempted_source_identities
                attempted_refs = result.attempted_source_refs
            else:
                raw_result = fetch_month(period.year, period.month)
                if isinstance(raw_result, ExchangeSessionSourceResult):
                    result = raw_result
                    month_sessions = result.sessions
                    source_identity = result.source_identity
                    source_ref = result.source_ref
                    fallback_reason = result.fallback_reason
                    attempted_identities = result.attempted_source_identities
                    attempted_refs = result.attempted_source_refs
                else:
                    month_sessions = pd.DatetimeIndex(raw_result)
                    source_identity = "INJECTED_FETCH_MONTH"
                    source_ref = monthly_url
                    fallback_reason = ""
                    attempted_identities = (source_identity,)
                    attempted_refs = (source_ref,)
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
                    "source_identity": source_identity,
                    "source_ref": source_ref,
                    "source_name": source_identity,
                    "fallback_reason": fallback_reason,
                    "attempted_source_identities": json.dumps(
                        list(attempted_identities), ensure_ascii=False
                    ),
                    "attempted_source_refs": json.dumps(
                        list(attempted_refs), ensure_ascii=False
                    ),
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
                    "source_identity": "IDX_SESSION_SOURCE_UNRESOLVED",
                    "source_ref": "|".join((monthly_url, daily_url)),
                    "source_name": "IDX_OFFICIAL_SESSION_SOURCES",
                    "fallback_reason": "",
                    "attempted_source_identities": json.dumps(
                        [
                            IDX_DIGITAL_STATISTICS_SOURCE_ID,
                            IDX_DAILY_STATISTICS_SOURCE_ID,
                        ],
                        ensure_ascii=False,
                    ),
                    "attempted_source_refs": json.dumps(
                        [monthly_url, daily_url], ensure_ascii=False
                    ),
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
        "source": "IDX_OFFICIAL_EXCHANGE_SESSION_SOURCES",
        "source_identity": (
            source_report["source_identity"].dropna().astype(str).drop_duplicates().iloc[0]
            if not source_report.empty
            and source_report["source_identity"].dropna().astype(str).drop_duplicates().size == 1
            else "MULTI_SOURCE_OR_UNRESOLVED"
        ),
        "source_identities": (
            sorted(source_report["source_identity"].dropna().astype(str).unique().tolist())
            if not source_report.empty
            else []
        ),
        "source_references": (
            sorted(source_report["source_ref"].dropna().astype(str).unique().tolist())
            if not source_report.empty
            else []
        ),
        "fallback_months": (
            int(source_report["fallback_reason"].fillna("").astype(str).ne("").sum())
            if not source_report.empty
            else 0
        ),
    }
    _atomic_json(summary, report_dir / "exchange_session_summary.json")
    return summary
