from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.pit_sector_history import (
    acquire_official_sources,
    attach_sector_asof,
    is_official_idx_url,
    load_source_inventory,
    materialize_sector_intervals,
    normalise_sector_events,
    validate_source_inventory,
    validate_effective_date_evidence,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def _palm_source() -> dict:
    return {
        "source_id": "IDX_IC_INCIDENTAL_PALM_2023",
        "source_type": "INCIDENTAL_CLASSIFICATION_CHANGE",
        "announcement_ref": "Peng-00236/BEI.POP/09-2023",
        "announced_at": "2023-09-29",
        "effective_from": "2023-10-02",
        "status": "READY_FOR_ACQUISITION",
        "download_url": "https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/Peng-00236_BEI.POP_09-2023.zip",
        "raw_attachment": {"sha256": "3b85b0f1bbd0cdee1ef6dc99de2b5570da892e908458303d0fbfe29bf81959d9"},
        "effective_date_evidence": {
            "source_id": "IDX_IC_INCIDENTAL_PALM_EFFECTIVE_2023",
            "source_type": "OFFICIAL_EFFECTIVE_DATE_EVIDENCE",
            "announcement_ref": "Peng-00016/BEI.PP1/10-2023",
            "announced_at": "2023-10-02",
            "effective_from": "2023-10-02",
            "download_url": "https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202310/3fc602c18b_d3dffbcb7c.pdf",
            "source_sha256": "2088a9fde16bc8ac8c0da687901eb79cc7dc2124bf9c673315ebb70c1c496fb4",
            "bytes": 5738,
            "content_type": "application/pdf",
            "linkage": {
                "canonical_source_id": "IDX_IC_INCIDENTAL_PALM_2023",
                "canonical_announcement_ref": "Peng-00236/BEI.POP/09-2023",
                "canonical_source_sha256": "3b85b0f1bbd0cdee1ef6dc99de2b5570da892e908458303d0fbfe29bf81959d9",
                "linked_tickers": ["PALM"],
                "classification_change": "PALM Consumer Non-Cyclicals to Financials",
                "linkage_statement": "The official IDX issuer disclosure embeds and references the Peng-00236 classification attachment and states the effective date."
            }
        }
    }


class _FakeResponse:
    def __init__(self, payload: bytes, content_type: str) -> None:
        self.status_code = 200
        self.headers = {"Content-Type": content_type}
        self.content = payload


class _FakeSession:
    def __init__(self, responses: dict[str, _FakeResponse]) -> None:
        self.responses = responses

    def get(self, url: str, *, allow_redirects: bool, timeout: tuple[float, float]) -> _FakeResponse:
        assert allow_redirects is False
        assert timeout == (10.0, 60.0)
        return self.responses[url]


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


def test_multidocument_official_effective_date_evidence_validates() -> None:
    source = _palm_source()
    evidence = validate_effective_date_evidence(source)
    assert evidence is not None
    assert evidence["effective_from"] == pd.Timestamp("2023-10-02")
    assert evidence["knowledge_at"] == pd.Timestamp("2023-10-02")
    assert evidence["linked_tickers"] == ["PALM"]

    audit = validate_source_inventory({"schema_version": 2, "sources": [source]})
    assert audit["sources_ready"] == 1
    assert audit["effective_date_evidence_validated"] == 1


def test_multidocument_effective_date_evidence_can_be_announced_after_effective_date() -> None:
    source = _palm_source()
    source["announced_at"] = "2024-06-24"
    source["effective_from"] = "2024-07-01"
    evidence = source["effective_date_evidence"]
    evidence["announced_at"] = "2024-07-05"
    evidence["effective_from"] = "2024-07-01"

    validated = validate_effective_date_evidence(source)
    assert validated is not None
    assert validated["effective_from"] == pd.Timestamp("2024-07-01")
    assert validated["announced_at"] == pd.Timestamp("2024-07-05")
    assert validated["knowledge_at"] == pd.Timestamp("2024-07-05")


def test_multidocument_effective_date_evidence_rejects_cross_event_linkage() -> None:
    source = _palm_source()
    source["effective_date_evidence"]["linkage"]["canonical_announcement_ref"] = "Peng-WRONG"
    with pytest.raises(ValueError, match="canonical ref linkage mismatch"):
        validate_effective_date_evidence(source)


def test_multidocument_effective_date_evidence_rejects_inferred_canonical_date() -> None:
    source = _palm_source()
    source["effective_from"] = None
    with pytest.raises(ValueError, match="canonical effective_from must be explicit"):
        validate_effective_date_evidence(source)


def test_multidocument_effective_date_evidence_rejects_canonical_hash_mismatch() -> None:
    source = _palm_source()
    source["effective_date_evidence"]["linkage"]["canonical_source_sha256"] = SHA_A
    with pytest.raises(ValueError, match="canonical hash linkage mismatch"):
        validate_effective_date_evidence(source)


def test_acquisition_records_and_hashes_nested_effective_date_evidence(tmp_path: Path) -> None:
    source = _palm_source()
    canonical_url = "https://www.idx.id/canonical.zip"
    evidence_url = "https://www.idx.id/effective.pdf"
    canonical_payload = b"canonical"
    evidence_payload = b"official effective date evidence"
    source["download_url"] = canonical_url
    source["raw_attachment"] = {}
    source["effective_date_evidence"]["download_url"] = evidence_url
    source["effective_date_evidence"]["source_sha256"] = hashlib.sha256(evidence_payload).hexdigest()
    session = _FakeSession(
        {
            canonical_url: _FakeResponse(canonical_payload, "application/zip"),
            evidence_url: _FakeResponse(evidence_payload, "application/pdf"),
        }
    )

    manifest = acquire_official_sources(
        {"schema_version": 2, "sources": [source]},
        output_dir=tmp_path,
        session=session,
    )
    entry = manifest["entries"][0]
    assert entry["raw_sha256"] == hashlib.sha256(canonical_payload).hexdigest()
    assert entry["effective_date_evidence"]["raw_sha256"] == hashlib.sha256(evidence_payload).hexdigest()
    assert entry["effective_date_evidence"]["announced_at"] == "2023-10-02 00:00:00"
    assert entry["effective_date_evidence"]["knowledge_at"] == "2023-10-02 00:00:00"
    assert (tmp_path / "raw" / entry["effective_date_evidence"]["raw_file"]).read_bytes() == evidence_payload


def test_committed_palm_is_promoted_only_with_valid_official_evidence() -> None:
    inventory_path = Path(__file__).parents[1] / "config" / "pit_sector_sources_v1.json"
    inventory = load_source_inventory(inventory_path)
    palm = next(source for source in inventory["sources"] if source["source_id"] == "IDX_IC_INCIDENTAL_PALM_2023")
    assert palm["status"] == "READY_FOR_ACQUISITION"
    assert validate_effective_date_evidence(palm)["effective_from"] == pd.Timestamp("2023-10-02")


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


def test_pit_join_waits_for_late_supporting_knowledge() -> None:
    events = pd.DataFrame(
        [
            {
                "ticker": "CCCC",
                "sector_code": "C",
                "effective_from": "2024-07-01",
                "announced_at": "2024-06-24",
                "knowledge_at": "2024-07-05",
                "source_id": "ANNUAL_WITH_LATE_EVIDENCE",
                "source_sha256": SHA_A,
            }
        ]
    )
    normalised = normalise_sector_events(events)
    assert normalised.loc[0, "pit_from"] == pd.Timestamp("2024-07-05")

    signals = pd.DataFrame(
        {
            "ticker": ["CCCC", "CCCC", "CCCC"],
            "date": ["2024-07-01", "2024-07-04", "2024-07-05"],
        }
    )
    joined = attach_sector_asof(signals, events)
    assert pd.isna(joined.loc[0, "sector_code"])
    assert pd.isna(joined.loc[1, "sector_code"])
    assert joined.loc[2, "sector_code"] == "C"
    assert joined.loc[2, "knowledge_at"] == pd.Timestamp("2024-07-05")


def test_non_monotonic_pit_knowledge_order_fails_closed() -> None:
    events = pd.DataFrame(
        [
            {
                "ticker": "DDDD",
                "sector_code": "A",
                "effective_from": "2024-07-01",
                "announced_at": "2024-06-24",
                "knowledge_at": "2024-08-01",
                "source_id": "OLDER_EVENT_KNOWN_LATE",
                "source_sha256": SHA_A,
            },
            {
                "ticker": "DDDD",
                "sector_code": "B",
                "effective_from": "2024-07-15",
                "announced_at": "2024-07-10",
                "knowledge_at": "2024-07-15",
                "source_id": "NEWER_EVENT_KNOWN_EARLIER",
                "source_sha256": SHA_B,
            },
        ]
    )
    with pytest.raises(ValueError, match="non-monotonic PIT knowledge order"):
        normalise_sector_events(events)


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
