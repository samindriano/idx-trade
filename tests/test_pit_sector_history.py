from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from idx_trade.pit_sector_history import (
    acquire_official_sources,
    attach_sector_asof,
    is_official_idx_url,
    materialize_sector_intervals,
    normalise_sector_events,
    validate_source_inventory,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AAAA",
                "sector_code": "D",
                "effective_from": "2021-01-25",
                "announced_at": "2021-01-13",
                "source_id": "BASE",
                "source_sha256": SHA_A,
            },
            {
                "ticker": "AAAA",
                "sector_code": "C",
                "effective_from": "2024-07-01",
                "announced_at": "2024-06-24",
                "source_id": "ANNUAL_2024",
                "source_sha256": SHA_B,
            },
        ]
    )


def test_official_idx_url_is_fail_closed() -> None:
    assert is_official_idx_url("https://www.idx.co.id/media/example.zip")
    assert is_official_idx_url("https://gopublic.idx.co.id/media/example.pdf")
    assert is_official_idx_url("https://www.idx.id/id/data-pasar")
    assert not is_official_idx_url("http://www.idx.co.id/media/example.zip")
    assert not is_official_idx_url("https://idx.co.id.evil.example/file.zip")
    assert not is_official_idx_url("https://example.com/file.zip")


def test_inventory_blocks_partial_acquisition() -> None:
    inventory = {
        "schema_version": 1,
        "sources": [
            {
                "source_id": "BASE",
                "source_type": "INITIAL_BASELINE_PACKAGE",
                "announcement_ref": "Peng-X",
                "announced_at": "2021-01-13",
                "effective_from": "2021-01-25",
                "status": "READY_FOR_ACQUISITION",
                "download_url": "https://www.idx.co.id/media/base.zip",
            },
            {
                "source_id": "ANNUAL_2022",
                "source_type": "ANNUAL_CLASSIFICATION_EVALUATION",
                "announcement_ref": "UNRESOLVED",
                "announced_at": None,
                "effective_from": None,
                "status": "DISCOVERY_REQUIRED",
                "download_url": "",
            },
        ],
    }
    audit = validate_source_inventory(inventory)
    assert audit["sources_total"] == 2
    assert audit["sources_ready"] == 1
    assert audit["sources_blocked"] == 1
    assert audit["complete_for_acquisition"] is False
    with pytest.raises(RuntimeError, match="inventory incomplete"):
        acquire_official_sources(inventory, output_dir="unused")


def test_ready_source_requires_verified_dates_and_official_url() -> None:
    inventory = {
        "schema_version": 1,
        "sources": [
            {
                "source_id": "BAD",
                "source_type": "INITIAL_BASELINE_PACKAGE",
                "announcement_ref": "Peng-X",
                "announced_at": None,
                "effective_from": "2021-01-25",
                "status": "READY_FOR_ACQUISITION",
                "download_url": "https://example.com/base.zip",
            }
        ],
    }
    with pytest.raises(ValueError, match="verified announced/effective date"):
        validate_source_inventory(inventory)


def test_pit_join_does_not_backfill_future_sector() -> None:
    signals = pd.DataFrame(
        {
            "ticker": ["AAAA", "AAAA", "AAAA"],
            "date": ["2021-01-20", "2023-05-02", "2024-07-01"],
        }
    )
    joined = attach_sector_asof(signals, _events())
    assert pd.isna(joined.loc[0, "sector_code"])
    assert joined.loc[0, "sector_pit_known"] == False  # noqa: E712
    assert joined.loc[1, "sector_code"] == "D"
    assert joined.loc[2, "sector_code"] == "C"


def test_pit_from_is_max_of_effective_and_announcement() -> None:
    events = pd.DataFrame(
        [
            {
                "ticker": "AAAA",
                "sector_code": "D",
                "effective_from": "2021-01-25",
                "announced_at": "2021-01-13",
                "source_id": "BASE",
                "source_sha256": SHA_A,
            },
            {
                "ticker": "BBBB",
                "sector_code": "B",
                "effective_from": "2023-07-03",
                "announced_at": "2023-07-05",
                "source_id": "LATE_NOTICE",
                "source_sha256": SHA_B,
            },
        ]
    )
    normalised = normalise_sector_events(events).set_index("ticker")
    assert normalised.loc["AAAA", "pit_from"] == pd.Timestamp("2021-01-25")
    assert normalised.loc["BBBB", "pit_from"] == pd.Timestamp("2023-07-05")

    signals = pd.DataFrame(
        {
            "ticker": ["BBBB", "BBBB"],
            "date": ["2023-07-04", "2023-07-05"],
        }
    )
    joined = attach_sector_asof(signals, events)
    assert pd.isna(joined.loc[0, "sector_code"])
    assert joined.loc[1, "sector_code"] == "B"


def test_conflicting_same_effective_date_fails_closed() -> None:
    events = pd.DataFrame(
        [
            {
                "ticker": "AAAA",
                "sector_code": "D",
                "effective_from": "2024-07-01",
                "announced_at": "2024-06-24",
                "source_id": "S1",
                "source_sha256": SHA_A,
            },
            {
                "ticker": "AAAA",
                "sector_code": "C",
                "effective_from": "2024-07-01",
                "announced_at": "2024-06-24",
                "source_id": "S2",
                "source_sha256": SHA_B,
            },
        ]
    )
    with pytest.raises(ValueError, match="conflicting sector events"):
        normalise_sector_events(events)


def test_source_hash_is_mandatory() -> None:
    events = _events()
    events.loc[0, "source_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="64-hex"):
        normalise_sector_events(events)


def test_materialized_intervals_preserve_effective_and_pit_boundaries() -> None:
    intervals = materialize_sector_intervals(_events())
    first = intervals.iloc[0]
    assert first["effective_to"] == pd.Timestamp("2024-06-30")
    assert first["pit_to"] == pd.Timestamp("2024-06-30")
    assert pd.isna(intervals.iloc[1]["effective_to"])
    assert pd.isna(intervals.iloc[1]["pit_to"])
