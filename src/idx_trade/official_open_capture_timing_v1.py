"""Fail-closed timing admission for production Official Open capture slots.

This module decides only whether an observation is timely enough to occupy the
immutable production capture slot.  It does not execution-admit the evidence
for trading and does not access model, outcome, PaperState, order, or counter
state.
"""

from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
import json
from typing import Mapping

from .official_open_evidence_v1 import JAKARTA


SLOT_WINDOWS = {
    "0902": (time(9, 2), time(9, 8)),
    "0912": (time(9, 12), time(9, 18)),
    "0922": (time(9, 22), time(9, 23)),
}


class OfficialOpenCaptureTimingError(RuntimeError):
    """Raised when a production capture would occupy a slot outside its window."""


def _session(value: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise OfficialOpenCaptureTimingError(
            "OFFICIAL_OPEN_CAPTURE_TIMING_SESSION_INVALID"
        ) from exc


def _window(session_date: str, slot: str) -> tuple[datetime, datetime]:
    session = _session(session_date)
    logical_slot = str(slot).strip()
    if logical_slot not in SLOT_WINDOWS:
        raise OfficialOpenCaptureTimingError(
            f"OFFICIAL_OPEN_CAPTURE_TIMING_SLOT_INVALID:{logical_slot}"
        )
    due_time, cutoff_time = SLOT_WINDOWS[logical_slot]
    return (
        datetime.combine(session, due_time, tzinfo=JAKARTA),
        datetime.combine(session, cutoff_time, tzinfo=JAKARTA),
    )


def require_timestamp_in_slot_window(
    *, session_date: str, slot: str, observed_at: datetime
) -> datetime:
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise OfficialOpenCaptureTimingError(
            "OFFICIAL_OPEN_CAPTURE_TIMING_TIMESTAMP_NAIVE"
        )
    observed = observed_at.astimezone(JAKARTA)
    due, cutoff = _window(session_date, slot)
    if observed < due:
        raise OfficialOpenCaptureTimingError(
            "OFFICIAL_OPEN_CAPTURE_BEFORE_SLOT_DUE"
        )
    if observed >= cutoff:
        raise OfficialOpenCaptureTimingError(
            "OFFICIAL_OPEN_CAPTURE_WINDOW_EXPIRED"
        )
    return observed


def require_runner_start_in_slot_window(
    *, session_date: str, slot: str, now: datetime | None = None
) -> datetime:
    return require_timestamp_in_slot_window(
        session_date=session_date,
        slot=slot,
        observed_at=now or datetime.now(JAKARTA),
    )


def validate_source_manifest_timing(
    *, manifest_path: Path, session_date: str, slot: str
) -> Path:
    try:
        payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfficialOpenCaptureTimingError(
            "OFFICIAL_OPEN_CAPTURE_TIMING_SOURCE_MANIFEST_INVALID"
        ) from exc
    if not isinstance(payload, Mapping):
        raise OfficialOpenCaptureTimingError(
            "OFFICIAL_OPEN_CAPTURE_TIMING_SOURCE_MANIFEST_INVALID"
        )
    if payload.get("session_date") != _session(session_date).isoformat():
        raise OfficialOpenCaptureTimingError(
            "OFFICIAL_OPEN_CAPTURE_TIMING_SOURCE_SESSION_MISMATCH"
        )
    raw_timestamp = str(payload.get("capture_timestamp_jakarta") or "")
    try:
        captured = datetime.fromisoformat(raw_timestamp)
    except ValueError as exc:
        raise OfficialOpenCaptureTimingError(
            "OFFICIAL_OPEN_CAPTURE_TIMING_SOURCE_TIMESTAMP_INVALID"
        ) from exc
    require_timestamp_in_slot_window(
        session_date=session_date,
        slot=slot,
        observed_at=captured,
    )
    return Path(manifest_path)


__all__ = [
    "OfficialOpenCaptureTimingError",
    "SLOT_WINDOWS",
    "require_runner_start_in_slot_window",
    "require_timestamp_in_slot_window",
    "validate_source_manifest_timing",
]
