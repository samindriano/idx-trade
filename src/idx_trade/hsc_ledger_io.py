from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Mapping

from .hsc_ledger import (
    HSCEvent,
    HSCMethodologyVersion,
    HSCReplayResult,
    HSCRevisionKind,
    HSCStatus,
)


HSC_EVENT_COLUMNS = (
    "event_id",
    "ticker",
    "status",
    "ownership_as_of_date",
    "published_at",
    "concentration_pct",
    "determination_methodology_version",
    "idx_announcement_no",
    "ksei_announcement_no",
    "revision_kind",
    "supersedes_event_id",
    "source_url",
    "source_sha256",
    "metadata_source_sha256",
)


def _required_text(record: Mapping[str, str], name: str) -> str:
    value = str(record.get(name, "")).strip()
    if not value:
        raise ValueError(f"{name} is empty")
    return value


def _optional_text(record: Mapping[str, str], name: str) -> str | None:
    value = str(record.get(name, "")).strip()
    return value or None


def hsc_event_from_record(record: Mapping[str, str]) -> HSCEvent:
    missing = [column for column in HSC_EVENT_COLUMNS if column not in record]
    if missing:
        raise ValueError(f"HSC event record missing columns: {missing}")

    concentration_text = str(record.get("concentration_pct", "")).strip()
    concentration = float(concentration_text) if concentration_text else None

    try:
        ownership_as_of_date = date.fromisoformat(
            _required_text(record, "ownership_as_of_date")
        )
    except ValueError as exc:
        raise ValueError("ownership_as_of_date must be ISO YYYY-MM-DD") from exc

    try:
        published_at = datetime.fromisoformat(_required_text(record, "published_at"))
    except ValueError as exc:
        raise ValueError("published_at must be an ISO datetime with timezone offset") from exc

    try:
        status = HSCStatus(_required_text(record, "status"))
        methodology = HSCMethodologyVersion(
            _required_text(record, "determination_methodology_version")
        )
        revision_kind = HSCRevisionKind(_required_text(record, "revision_kind"))
    except ValueError as exc:
        raise ValueError(f"invalid HSC enum value: {exc}") from exc

    return HSCEvent(
        event_id=_required_text(record, "event_id"),
        ticker=_required_text(record, "ticker"),
        status=status,
        ownership_as_of_date=ownership_as_of_date,
        published_at=published_at,
        concentration_pct=concentration,
        determination_methodology_version=methodology,
        idx_announcement_no=_required_text(record, "idx_announcement_no"),
        ksei_announcement_no=_required_text(record, "ksei_announcement_no"),
        revision_kind=revision_kind,
        supersedes_event_id=_optional_text(record, "supersedes_event_id"),
        source_url=_required_text(record, "source_url"),
        source_sha256=_required_text(record, "source_sha256"),
        metadata_source_sha256=_required_text(record, "metadata_source_sha256"),
    )


def load_hsc_events_csv(path: str | Path) -> tuple[HSCEvent, ...]:
    source = Path(path)
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = tuple(reader.fieldnames or ())
        if actual != HSC_EVENT_COLUMNS:
            raise ValueError(
                "HSC event CSV header mismatch: "
                f"expected={HSC_EVENT_COLUMNS} actual={actual}"
            )
        events = tuple(hsc_event_from_record(record) for record in reader)
    if not events:
        raise ValueError("HSC event CSV is empty")
    return events


def reconciliation_report(replay: HSCReplayResult) -> dict[str, object]:
    methodology_counts: dict[str, int] = {}
    for state in replay.active.values():
        key = state.determination_methodology_version.value
        methodology_counts[key] = methodology_counts.get(key, 0) + 1

    published = [event.published_at for event in replay.events]
    return {
        "event_count": len(replay.events),
        "active_count": len(replay.active),
        "active_tickers": sorted(replay.active_tickers),
        "first_published_at": min(published).isoformat() if published else None,
        "last_published_at": max(published).isoformat() if published else None,
        "active_determination_methodology_counts": dict(sorted(methodology_counts.items())),
    }
