from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from idx_trade.hsc_ledger import replay_hsc_events
from idx_trade.hsc_ledger_io import (
    HSC_EVENT_COLUMNS,
    load_hsc_events_csv,
    reconciliation_report,
)


TZ = timezone(timedelta(hours=7))


def _row(
    *,
    event_id: str = "bren-original",
    ticker: str = "BREN",
    status: str = "HSC_ACTIVE",
    concentration_pct: str = "97.31",
    methodology: str = "HSC_2026_INITIAL",
    revision_kind: str = "ORIGINAL",
    supersedes_event_id: str = "",
    published_at: str = "2026-04-02T18:02:00+07:00",
    source_sha: str = "a" * 64,
    metadata_sha: str = "b" * 64,
) -> dict[str, str]:
    return {
        "event_id": event_id,
        "ticker": ticker,
        "status": status,
        "ownership_as_of_date": "2026-03-31",
        "published_at": published_at,
        "concentration_pct": concentration_pct,
        "determination_methodology_version": methodology,
        "idx_announcement_no": "Peng-00002-HSC/BEI.WAS/04-2026",
        "ksei_announcement_no": "KSEI-2149/DIR/0426",
        "revision_kind": revision_kind,
        "supersedes_event_id": supersedes_event_id,
        "source_url": "https://www.idx.id/StaticData/bren.pdf",
        "source_sha256": source_sha,
        "metadata_source_sha256": metadata_sha,
    }


def _write(path: Path, rows: list[dict[str, str]], header=HSC_EVENT_COLUMNS) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in header})


def test_csv_loader_requires_exact_header_and_nonempty_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    _write(bad, [_row()], header=HSC_EVENT_COLUMNS[:-1])
    with pytest.raises(ValueError, match="header mismatch"):
        load_hsc_events_csv(bad)

    empty = tmp_path / "empty.csv"
    _write(empty, [])
    with pytest.raises(ValueError, match="CSV is empty"):
        load_hsc_events_csv(empty)


def test_csv_loader_parses_timezone_and_replay(tmp_path: Path) -> None:
    path = tmp_path / "events.csv"
    _write(path, [_row()])
    events = load_hsc_events_csv(path)
    assert len(events) == 1
    assert events[0].published_at.utcoffset() == timedelta(hours=7)
    replay = replay_hsc_events(events)
    assert replay.active_tickers == frozenset({"BREN"})


def test_csv_loader_allows_blank_concentration_only_for_removal(tmp_path: Path) -> None:
    path = tmp_path / "events.csv"
    original = _row()
    removal = _row(
        event_id="bren-removal",
        status="HSC_REMOVED",
        concentration_pct="",
        revision_kind="REMOVAL",
        published_at="2026-07-03T15:10:24+07:00",
        source_sha="c" * 64,
        metadata_sha="d" * 64,
    )
    _write(path, [original, removal])
    events = load_hsc_events_csv(path)
    assert events[1].concentration_pct is None
    assert replay_hsc_events(events).active_tickers == frozenset()


def test_reconciliation_report_preserves_determination_methodology_counts(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.csv"
    old = _row()
    new = _row(
        event_id="dcii-july",
        ticker="DCII",
        concentration_pct="99.96",
        methodology="HSC_2026_PRICE_IMPACT_REVISION",
        published_at="2026-07-15T08:00:00+07:00",
        source_sha="c" * 64,
        metadata_sha="d" * 64,
    )
    new["ownership_as_of_date"] = "2026-06-30"
    new["idx_announcement_no"] = "official-number-from-ledger"
    new["ksei_announcement_no"] = "official-ksei-number-from-ledger"
    _write(path, [old, new])
    report = reconciliation_report(replay_hsc_events(load_hsc_events_csv(path)))
    assert report["active_count"] == 2
    assert report["active_determination_methodology_counts"] == {
        "HSC_2026_INITIAL": 1,
        "HSC_2026_PRICE_IMPACT_REVISION": 1,
    }
