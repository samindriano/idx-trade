from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from .historical_statutory_free_float import (
    FreeFloatRevisionKind,
    FreeFloatSourceFamily,
    HistoricalFreeFloatObservation,
)


HISTORICAL_FF_COLUMNS = (
    "record_id",
    "ticker",
    "as_of_date",
    "published_at",
    "free_float_shares",
    "free_float_pct",
    "total_listed_shares",
    "source_family",
    "revision_kind",
    "supersedes_record_id",
    "announcement_no",
    "source_url",
    "source_sha256",
    "metadata_source_sha256",
    "source_row_key",
)


def _parse_int(value: str, *, field: str, allow_blank: bool = False) -> int | None:
    stripped = value.strip()
    if not stripped and allow_blank:
        return None
    if not stripped or not stripped.isdigit():
        raise ValueError(f"{field} must be a non-negative base-10 integer")
    return int(stripped)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError("as_of_date must be ISO YYYY-MM-DD") from exc


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError("published_at must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("published_at must include an explicit timezone offset")
    return parsed


def load_historical_ff_csv(path: str | Path) -> tuple[HistoricalFreeFloatObservation, ...]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != HISTORICAL_FF_COLUMNS:
            raise ValueError("historical FF CSV header mismatch")

        rows: list[HistoricalFreeFloatObservation] = []
        for line_no, raw in enumerate(reader, start=2):
            try:
                supersedes = raw["supersedes_record_id"].strip() or None
                row_key = raw["source_row_key"].strip() or None
                total = _parse_int(
                    raw["total_listed_shares"],
                    field="total_listed_shares",
                    allow_blank=True,
                )
                rows.append(
                    HistoricalFreeFloatObservation(
                        record_id=raw["record_id"].strip(),
                        ticker=raw["ticker"].strip(),
                        as_of_date=_parse_date(raw["as_of_date"]),
                        published_at=_parse_timestamp(raw["published_at"]),
                        free_float_shares=int(
                            _parse_int(
                                raw["free_float_shares"],
                                field="free_float_shares",
                            )
                        ),
                        free_float_pct=float(raw["free_float_pct"].strip()),
                        total_listed_shares=total,
                        source_family=FreeFloatSourceFamily(raw["source_family"].strip()),
                        revision_kind=FreeFloatRevisionKind(raw["revision_kind"].strip()),
                        supersedes_record_id=supersedes,
                        announcement_no=raw["announcement_no"].strip(),
                        source_url=raw["source_url"].strip(),
                        source_sha256=raw["source_sha256"].strip(),
                        metadata_source_sha256=raw["metadata_source_sha256"].strip(),
                        source_row_key=row_key,
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid historical FF row at CSV line {line_no}: {exc}") from exc

    if not rows:
        raise ValueError("historical FF CSV is empty")
    return tuple(rows)
