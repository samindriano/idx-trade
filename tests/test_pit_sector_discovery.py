from __future__ import annotations

import json
from pathlib import Path

import pytest

from idx_trade.pit_sector_discovery import validate_discovery_evidence_registry
from idx_trade.pit_sector_history import load_source_inventory, validate_source_inventory


def _canonical() -> dict:
    return {
        "schema_version": 1,
        "sources": [
            {
                "source_id": "BLOCKED_2022",
                "source_type": "ANNUAL_CLASSIFICATION_CHANGE",
                "announcement_ref": "UNRESOLVED",
                "announced_at": "2022-06-24",
                "effective_from": "2022-07-01",
                "status": "DISCOVERY_REQUIRED",
                "download_url": "",
            },
            {
                "source_id": "READY_2021",
                "source_type": "ANNUAL_CLASSIFICATION_CHANGE",
                "announcement_ref": "Peng-X",
                "announced_at": "2021-06-24",
                "effective_from": "2021-07-01",
                "status": "READY_FOR_ACQUISITION",
                "download_url": "https://www.idx.id/example.zip",
            },
        ],
    }


def _evidence() -> dict:
    return {
        "schema_version": 1,
        "evidence": [
            {
                "evidence_id": "NEWS_2022",
                "canonical_source_id": "BLOCKED_2022",
                "role": "SECONDARY_DISCOVERY_NOT_CANONICAL",
                "publisher": "Example News",
                "published_at": "2022-06-30",
                "url": "https://example.com/report",
                "claims": {
                    "announcement_date": "2022-06-24",
                    "effective_date": "2022-07-01",
                    "affected_count": 2,
                    "affected_tickers": ["AAAA", "BBBB"],
                },
                "note": "Discovery only.",
            }
        ],
    }


def test_discovery_evidence_is_explicitly_non_promoting() -> None:
    audit = validate_discovery_evidence_registry(_evidence(), _canonical())
    assert audit["evidence_total"] == 1
    assert audit["canonical_sources_touched"] == ["BLOCKED_2022"]
    assert audit["canonical_promotions_authorized"] == 0
    assert audit["canonical_gate_unchanged"] is True

    canonical_audit = validate_source_inventory(_canonical())
    assert canonical_audit["sources_blocked"] == 1
    assert canonical_audit["complete_for_acquisition"] is False


def test_discovery_evidence_cannot_target_ready_source() -> None:
    payload = _evidence()
    payload["evidence"][0]["canonical_source_id"] = "READY_2021"
    with pytest.raises(ValueError, match="only target a blocked canonical source"):
        validate_discovery_evidence_registry(payload, _canonical())


def test_discovery_evidence_rejects_canonical_role_or_non_https() -> None:
    payload = _evidence()
    payload["evidence"][0]["role"] = "CANONICAL"
    with pytest.raises(ValueError, match="unsupported discovery role"):
        validate_discovery_evidence_registry(payload, _canonical())

    payload = _evidence()
    payload["evidence"][0]["url"] = "http://example.com/report"
    with pytest.raises(ValueError, match="must be HTTPS"):
        validate_discovery_evidence_registry(payload, _canonical())


def test_discovery_evidence_validates_ticker_count_and_dates() -> None:
    payload = _evidence()
    payload["evidence"][0]["claims"]["affected_count"] = 3
    with pytest.raises(ValueError, match="affected_count disagrees"):
        validate_discovery_evidence_registry(payload, _canonical())

    payload = _evidence()
    payload["evidence"][0]["claims"]["affected_tickers"] = ["AAAA", "aaaa"]
    with pytest.raises(ValueError, match="empty/duplicate"):
        validate_discovery_evidence_registry(payload, _canonical())


def test_committed_revival_registry_preserves_all_three_blockers() -> None:
    root = Path(__file__).parents[1]
    canonical = load_source_inventory(root / "config" / "pit_sector_sources_v1.json")
    revival = json.loads((root / "config" / "pit_sector_revival_evidence_v1.json").read_text(encoding="utf-8"))

    audit = validate_discovery_evidence_registry(revival, canonical)
    assert audit["evidence_total"] == 5
    assert audit["canonical_sources_touched"] == [
        "IDX_IC_ANNUAL_CLASSIFICATION_2022",
        "IDX_IC_ANNUAL_CLASSIFICATION_2023",
        "IDX_IC_ANNUAL_CLASSIFICATION_2026",
    ]
    assert audit["canonical_promotions_authorized"] == 0

    canonical_audit = validate_source_inventory(canonical)
    blocked = {item["source_id"] for item in canonical_audit["blockers"]}
    assert blocked == {
        "IDX_IC_ANNUAL_CLASSIFICATION_2022",
        "IDX_IC_ANNUAL_CLASSIFICATION_2023",
        "IDX_IC_ANNUAL_CLASSIFICATION_2026",
    }
