"""Verified planned IDX trading schedule for forward PAPER execution.

The existing forward ``exchange_sessions.csv`` proves sessions that have
already occurred from IDX statistical publications.  PAPER execution also
needs a separate, forward-looking schedule authority to determine holidays and
the next scheduled exchange session without mutating that observed-session
parent.

This module intentionally does not fetch a source or infer holidays.  It
verifies an externally captured official Bursa calendar attestation whose
listed holidays were reviewed against the hash-bound source document.  The
session list is deterministically recomputed as weekdays minus those published
Bursa holidays over the attested coverage interval.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SCHEMA_VERSION = "idx_official_trading_schedule_v1"
AUTHORITY = "IDX"
SEMANTICS = "PLANNED_OFFICIAL_TRADING_SCHEDULE"
DERIVATION = "WEEKDAYS_MINUS_PUBLISHED_BURSA_HOLIDAYS"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class OfficialTradingScheduleError(RuntimeError):
    """Raised when the planned trading schedule cannot be proven."""


@dataclass(frozen=True)
class VerifiedOfficialTradingSchedule:
    attestation_path: Path
    attestation_sha256: str
    source_document_path: Path
    source_document_sha256: str
    source_reference: str
    coverage_start: str
    coverage_end: str
    holiday_dates: tuple[str, ...]
    session_dates: tuple[str, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _iso_date(value: object, code: str) -> str:
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise OfficialTradingScheduleError(code) from exc
    return parsed.isoformat()


def _resolve_artifact(attestation: Path, value: object, code: str) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise OfficialTradingScheduleError(code)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (attestation.parent / path).resolve()
    else:
        path = path.resolve()
    if not path.is_file():
        raise OfficialTradingScheduleError(code)
    return path


def derive_planned_sessions(
    *,
    coverage_start: str,
    coverage_end: str,
    holiday_dates: tuple[str, ...] | list[str],
) -> tuple[str, ...]:
    """Derive the attested plan as weekdays minus explicitly published holidays."""

    start = date.fromisoformat(_iso_date(coverage_start, "OFFICIAL_SCHEDULE_START_INVALID"))
    end = date.fromisoformat(_iso_date(coverage_end, "OFFICIAL_SCHEDULE_END_INVALID"))
    if end < start:
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_END_PRECEDES_START")

    normalized_holidays = tuple(
        sorted(
            {
                _iso_date(value, "OFFICIAL_SCHEDULE_HOLIDAY_INVALID")
                for value in holiday_dates
            }
        )
    )
    if len(normalized_holidays) != len(tuple(holiday_dates)):
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_HOLIDAY_DUPLICATE")
    for value in normalized_holidays:
        holiday = date.fromisoformat(value)
        if holiday < start or holiday > end:
            raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_HOLIDAY_OUTSIDE_COVERAGE")
        if holiday.weekday() >= 5:
            raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_WEEKEND_HOLIDAY_REDUNDANT")

    holidays = set(normalized_holidays)
    sessions: list[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current.isoformat() not in holidays:
            sessions.append(current.isoformat())
        current += timedelta(days=1)
    if not sessions:
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_EMPTY")
    return tuple(sessions)


def load_verified_official_trading_schedule(
    attestation_path: str | Path,
    *,
    expected_sha256: str | None = None,
) -> VerifiedOfficialTradingSchedule:
    """Load and cryptographically verify one planned-session attestation."""

    attestation = Path(attestation_path).expanduser().resolve()
    if not attestation.is_file():
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_ATTESTATION_MISSING")
    actual_attestation_sha = _sha256(attestation)
    if expected_sha256 is not None:
        expected = str(expected_sha256).strip().lower()
        if not _SHA256_RE.fullmatch(expected) or expected != actual_attestation_sha:
            raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_ATTESTATION_SHA_MISMATCH")

    try:
        payload = json.loads(attestation.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_ATTESTATION_INVALID") from exc
    if not isinstance(payload, dict):
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_ATTESTATION_NOT_OBJECT")

    declared_payload_sha = str(payload.get("payload_sha256") or "").lower()
    body = dict(payload)
    body.pop("payload_sha256", None)
    if not _SHA256_RE.fullmatch(declared_payload_sha) or _canonical_hash(body) != declared_payload_sha:
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_PAYLOAD_SHA_MISMATCH")

    expected_contract = {
        "schema_version": SCHEMA_VERSION,
        "authority": AUTHORITY,
        "semantics": SEMANTICS,
        "derivation": DERIVATION,
    }
    for key, expected_value in expected_contract.items():
        if payload.get(key) != expected_value:
            raise OfficialTradingScheduleError(
                f"OFFICIAL_SCHEDULE_CONTRACT_MISMATCH:{key}"
            )

    source_reference = str(payload.get("source_reference") or "").strip()
    if not source_reference:
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_SOURCE_REFERENCE_MISSING")
    source_path = _resolve_artifact(
        attestation,
        payload.get("source_document_path"),
        "OFFICIAL_SCHEDULE_SOURCE_DOCUMENT_MISSING",
    )
    source_sha = str(payload.get("source_document_sha256") or "").lower()
    if not _SHA256_RE.fullmatch(source_sha) or _sha256(source_path) != source_sha:
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_SOURCE_DOCUMENT_SHA_MISMATCH")

    coverage_start = _iso_date(
        payload.get("coverage_start"), "OFFICIAL_SCHEDULE_START_INVALID"
    )
    coverage_end = _iso_date(
        payload.get("coverage_end"), "OFFICIAL_SCHEDULE_END_INVALID"
    )
    raw_holidays = payload.get("holiday_dates")
    raw_sessions = payload.get("session_dates")
    if not isinstance(raw_holidays, list) or not isinstance(raw_sessions, list):
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_DATE_LIST_MISSING")

    holidays = tuple(
        _iso_date(value, "OFFICIAL_SCHEDULE_HOLIDAY_INVALID") for value in raw_holidays
    )
    sessions = tuple(
        _iso_date(value, "OFFICIAL_SCHEDULE_SESSION_INVALID") for value in raw_sessions
    )
    if sessions != tuple(sorted(set(sessions))):
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_SESSION_ORDER_OR_DUPLICATE_INVALID")
    if any(date.fromisoformat(value).weekday() >= 5 for value in sessions):
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_WEEKEND_SESSION")

    derived = derive_planned_sessions(
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        holiday_dates=list(holidays),
    )
    if sessions != derived:
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_DERIVATION_MISMATCH")

    return VerifiedOfficialTradingSchedule(
        attestation_path=attestation,
        attestation_sha256=actual_attestation_sha,
        source_document_path=source_path,
        source_document_sha256=source_sha,
        source_reference=source_reference,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        holiday_dates=tuple(sorted(holidays)),
        session_dates=sessions,
    )


def next_planned_session(
    schedule: VerifiedOfficialTradingSchedule,
    decision_session_date: str,
) -> str:
    decision = _iso_date(
        decision_session_date, "OFFICIAL_SCHEDULE_DECISION_SESSION_INVALID"
    )
    if decision < schedule.coverage_start or decision > schedule.coverage_end:
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_DECISION_OUTSIDE_COVERAGE")
    if decision not in schedule.session_dates:
        raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_DECISION_NOT_SCHEDULED_SESSION")
    for session in schedule.session_dates:
        if session > decision:
            return session
    raise OfficialTradingScheduleError("OFFICIAL_SCHEDULE_NEXT_SESSION_UNAVAILABLE")


__all__ = [
    "AUTHORITY",
    "DERIVATION",
    "SCHEMA_VERSION",
    "SEMANTICS",
    "OfficialTradingScheduleError",
    "VerifiedOfficialTradingSchedule",
    "derive_planned_sessions",
    "load_verified_official_trading_schedule",
    "next_planned_session",
]
