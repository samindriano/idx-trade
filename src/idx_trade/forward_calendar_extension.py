"""Immutable official IDX forward-calendar extension evidence.

This module deliberately stops at calendar evidence. It does not score models,
open outcomes, or create an O2 counter entry.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import pandas as pd

from .ohlcv_o2_forward import ForwardContractError, sha256_file
from .providers.idx_sessions import (
    ExchangeSessionSourceResult,
    _fetch_json,
    fetch_exchange_sessions_month_with_source,
)


HISTORICAL_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
HISTORICAL_SESSION_COUNT = 1260
TRADING_HOURS_SOURCE_ID = "IDX_EQUITY_TRADING_HOURS_CURRENT"
TRADING_HOURS_SOURCE_URL = "https://www.idx.id/en/products-services/trading-hours-and-mechanism/"
SESSION_START_TIME = "08:45:00"
JAKARTA_TZ = "Asia/Jakarta"


class CalendarExtensionError(ForwardContractError):
    """Raised when official calendar extension evidence is not trustworthy."""


@dataclass(frozen=True)
class TradingHoursEvidence:
    source_identity: str
    source_ref: str
    retrieved_at_utc: str
    raw_sha256: str
    session_start_time: str = SESSION_START_TIME
    timezone: str = JAKARTA_TZ


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _normalise_html_text(raw_html: str) -> str:
    value = html.unescape(str(raw_html))
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def verify_official_trading_hours(raw_html: str, *, source_ref: str = TRADING_HOURS_SOURCE_URL) -> TradingHoursEvidence:
    """Verify the live official page supports the frozen 08:45 rule."""

    text = _normalise_html_text(raw_html)
    pre_open = re.search(
        r"Pre\s*opening\s*\(Input\).*?Monday\s*-\s*Friday\s+08[.:]45[.:]00\s*[–-]\s*08[.:]57[.:]59",
        text,
        flags=re.IGNORECASE,
    )
    session_i = re.search(
        r"Session\s*I.*?Monday\s*-\s*Thursday\s+09[.:]00[.:]00\s*[–-]\s*12[.:]00[.:]00",
        text,
        flags=re.IGNORECASE,
    )
    if pre_open is None or session_i is None:
        raise CalendarExtensionError(
            "official IDX trading-hours page does not support the frozen 08:45/09:00 rule"
        )
    return TradingHoursEvidence(
        source_identity=TRADING_HOURS_SOURCE_ID,
        source_ref=source_ref,
        retrieved_at_utc=_utc_now(),
        raw_sha256=_sha256_bytes(str(raw_html).encode("utf-8")),
    )


def _read_historical_calendar(path: Path) -> pd.DatetimeIndex:
    if not path.is_file():
        raise CalendarExtensionError(f"historical calendar is missing: {path}")
    actual = sha256_file(path)
    if actual != HISTORICAL_CALENDAR_SHA256:
        raise CalendarExtensionError(
            f"historical calendar SHA mismatch: expected {HISTORICAL_CALENDAR_SHA256}, got {actual}"
        )
    frame = pd.read_csv(path)
    if list(frame.columns) != ["date"]:
        raise CalendarExtensionError("historical calendar schema is not the frozen date-only artifact")
    dates = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    if dates.isna().any() or len(dates) != HISTORICAL_SESSION_COUNT:
        raise CalendarExtensionError("historical calendar count or dates are invalid")
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise CalendarExtensionError("historical calendar dates are not unique and increasing")
    if dates.iloc[-1].date().isoformat() != "2026-07-31":
        raise CalendarExtensionError("historical calendar does not end at 2026-07-31")
    return pd.DatetimeIndex(dates)


def _session_start(session_date: pd.Timestamp) -> str:
    timestamp = pd.Timestamp(session_date).tz_localize(JAKARTA_TZ).replace(hour=8, minute=45, second=0, microsecond=0)
    return timestamp.isoformat()


def _assert_extension_invariants(frame: pd.DataFrame, historical_dates: pd.DatetimeIndex, hours: TradingHoursEvidence) -> None:
    required = {"session_index", "session_date", "session_start"}
    if not required.issubset(frame.columns):
        raise CalendarExtensionError(f"extension missing columns: {sorted(required - set(frame.columns))}")
    if frame.empty:
        raise CalendarExtensionError("official IDX extension contains no dates")
    indexes = pd.to_numeric(frame["session_index"], errors="coerce")
    dates = pd.to_datetime(frame["session_date"], errors="coerce")
    if indexes.isna().any() or dates.isna().any():
        raise CalendarExtensionError("extension contains invalid identity values")
    if indexes.astype(int).iloc[0] != HISTORICAL_SESSION_COUNT + 1:
        raise CalendarExtensionError("extension does not start at session index 1261")
    first_index = HISTORICAL_SESSION_COUNT + 1
    if indexes.astype(int).tolist() != list(range(first_index, first_index + len(frame))):
        raise CalendarExtensionError("extension session indexes are not consecutive")
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise CalendarExtensionError("extension dates are not unique and increasing")
    if dates.iloc[0] <= historical_dates[-1] or set(dates).intersection(set(historical_dates)):
        raise CalendarExtensionError("extension overlaps the historical calendar")
    if (dates.dt.weekday > 4).any():
        raise CalendarExtensionError("extension contains a weekend date")
    starts = pd.to_datetime(frame["session_start"], utc=True, errors="coerce")
    expected = pd.Series([_session_start(value) for value in dates], index=frame.index)
    expected_utc = pd.to_datetime(expected, utc=True)
    if starts.isna().any() or not starts.eq(expected_utc).all():
        raise CalendarExtensionError("extension session_start does not follow the verified IDX rule")
    if hours.session_start_time != SESSION_START_TIME or hours.timezone != JAKARTA_TZ:
        raise CalendarExtensionError("trading-hours evidence does not match the frozen session-start rule")


def extend_official_calendar(
    *,
    historical_calendar_path: Path,
    end: str | pd.Timestamp,
    trading_hours: TradingHoursEvidence,
    fetch_month: Callable[..., ExchangeSessionSourceResult] = fetch_exchange_sessions_month_with_source,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex]:
    """Fetch official dates and continue identity after the frozen anchor."""

    historical_dates = _read_historical_calendar(historical_calendar_path)
    start = historical_dates[-1] + pd.Timedelta(days=1)
    end_ts = pd.Timestamp(end).normalize()
    if end_ts < start:
        raise CalendarExtensionError("extension end precedes the historical anchor")
    months = pd.period_range(start.to_period("M"), end_ts.to_period("M"), freq="M")
    sessions: set[pd.Timestamp] = set()
    source_rows: list[dict[str, Any]] = []
    for period in months:
        try:
            result = fetch_month(period.year, period.month)
            if not isinstance(result, ExchangeSessionSourceResult):
                raise CalendarExtensionError("session provider did not return auditable source result")
            month_sessions = [
                pd.Timestamp(value).normalize()
                for value in result.sessions
                if start <= pd.Timestamp(value).normalize() <= end_ts
            ]
            sessions.update(month_sessions)
            source_rows.append(
                {
                    "year": period.year,
                    "month": period.month,
                    "source_identity": result.source_identity,
                    "source_ref": result.source_ref,
                    "fallback_reason": result.fallback_reason,
                    "attempted_source_identities": json.dumps(list(result.attempted_source_identities)),
                    "attempted_source_refs": json.dumps(list(result.attempted_source_refs)),
                    "sessions_in_requested_range": len(month_sessions),
                    "status": "PARSED",
                    "error": "",
                }
            )
        except Exception as error:
            source_rows.append(
                {
                    "year": period.year,
                    "month": period.month,
                    "source_identity": "IDX_SESSION_SOURCE_UNRESOLVED",
                    "source_ref": "",
                    "fallback_reason": "",
                    "attempted_source_identities": "",
                    "attempted_source_refs": "",
                    "sessions_in_requested_range": 0,
                    "status": "ERROR",
                    "error": str(error),
                }
            )
    ordered = pd.DatetimeIndex(sorted(sessions))
    frame = pd.DataFrame(
        {
            "session_index": range(HISTORICAL_SESSION_COUNT + 1, HISTORICAL_SESSION_COUNT + 1 + len(ordered)),
            "session_date": [value.date().isoformat() for value in ordered],
            "session_start": [_session_start(value) for value in ordered],
        }
    )
    _assert_extension_invariants(frame, historical_dates, trading_hours)
    return frame, pd.DataFrame(source_rows), historical_dates


def resolve_first_post_freeze_extension_session(extension: pd.DataFrame, freeze_timestamp: Any) -> dict[str, Any]:
    if extension.empty:
        raise CalendarExtensionError("no official extension sessions available after the historical anchor")
    starts = pd.to_datetime(extension["session_start"], utc=True, errors="coerce")
    freeze = pd.Timestamp(freeze_timestamp)
    freeze = freeze.tz_localize("UTC") if freeze.tzinfo is None else freeze.tz_convert("UTC")
    eligible = extension.loc[starts > freeze].sort_values("session_index", kind="mergesort")
    if eligible.empty:
        raise CalendarExtensionError("no official extension session starts strictly after the freeze timestamp")
    row = eligible.iloc[0]
    return {
        "session_index": int(row["session_index"]),
        "session_date": str(row["session_date"]),
        "session_start": str(pd.Timestamp(row["session_start"]).isoformat()),
        "freeze_timestamp": freeze.isoformat(),
    }


def write_extension_artifacts(
    *,
    output_dir: Path,
    extension: pd.DataFrame,
    source_report: pd.DataFrame,
    historical_calendar_path: Path,
    trading_hours: TradingHoursEvidence,
    trading_hours_raw: bytes,
    first_session: Mapping[str, Any] | None,
    freeze_timestamp: Any,
    raw_source_manifest: list[Mapping[str, Any]],
    status: str,
) -> dict[str, Any]:
    """Write an immutable evidence bundle outside the Git repository."""

    output_dir.mkdir(parents=True, exist_ok=True)
    extension_path = output_dir / "forward_exchange_sessions.csv"
    source_path = output_dir / "exchange_session_sources.csv"
    hours_path = output_dir / "trading_hours.html"
    manifest_path = output_dir / "manifest.json"
    if any(path.exists() for path in (extension_path, source_path, hours_path, manifest_path)):
        raise CalendarExtensionError("refusing to overwrite existing calendar-extension artifacts")
    extension.to_csv(extension_path, index=False)
    source_report.to_csv(source_path, index=False)
    hours_path.write_bytes(trading_hours_raw)
    manifest: dict[str, Any] = {
        "schema": "idx-trade/official-forward-calendar-extension-v1",
        "status": status,
        "generated_at_utc": _utc_now(),
        "historical_calendar_path": str(historical_calendar_path),
        "historical_calendar_sha256": HISTORICAL_CALENDAR_SHA256,
        "historical_session_count": HISTORICAL_SESSION_COUNT,
        "extension_path": str(extension_path),
        "extension_sha256": sha256_file(extension_path),
        "extension_rows": int(len(extension)),
        "source_report_path": str(source_path),
        "source_report_sha256": sha256_file(source_path),
        "trading_hours_source_identity": trading_hours.source_identity,
        "trading_hours_source_ref": trading_hours.source_ref,
        "trading_hours_retrieved_at_utc": trading_hours.retrieved_at_utc,
        "trading_hours_raw_path": str(hours_path),
        "trading_hours_raw_sha256": sha256_file(hours_path),
        "session_start_rule": f"{SESSION_START_TIME} {JAKARTA_TZ}",
        "freeze_timestamp": str(pd.Timestamp(freeze_timestamp).isoformat()),
        "first_post_freeze_session": dict(first_session) if first_session is not None else None,
        "raw_source_manifest": [dict(item) for item in raw_source_manifest],
        "o2_scoring_performed": False,
        "o2_counter_entry_created": False,
        "outcomes_accessed": False,
        "third_party_calendar_used": False,
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps({k: v for k, v in manifest.items() if k != "manifest_sha256"}, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest
