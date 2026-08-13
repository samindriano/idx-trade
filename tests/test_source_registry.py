"""Regression tests for the evidence-bound source registry."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from idx_trade.source_registry import (
    RegistryValidationError,
    assert_source_registry,
    load_source_registry,
    validate_source_registry,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "data_source_provenance_registry.v1.json"


def _registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def test_canonical_registry_is_valid_and_git_pins_resolve() -> None:
    registry = load_source_registry(REGISTRY_PATH, repo_root=ROOT, verify_git=True)
    assert registry["source_count"] == 18
    assert registry["checkpoint_count"] == 20


def test_all_known_source_families_have_explicit_status_and_use_boundary() -> None:
    registry = _registry()
    source_ids = {source["source_id"] for source in registry["sources"]}
    assert {
        "YAHOO_RAW_OHLCV",
        "WILDAN_OPEN_RECOVERY",
        "IDX_STOCK_SUMMARY_EXECUTION",
        "IDX_INDEX_SUMMARY",
        "IDX_FOREIGN_FLOW",
        "IDX_FINANCIAL_PIT",
        "KSEI_OWNERSHIP",
        "IDX_PIT_SECTOR_HISTORY",
        "IDX_CORPORATE_ACTIONS",
        "STOCKBIT_INTRADAY",
        "IDX_MARGIN_SUMMARY",
        "IDX_HISTORICAL_SECURITY_UNIVERSE",
        "IDX_TRADABILITY_ANNOUNCEMENTS",
    } <= source_ids
    for source in registry["sources"]:
        assert source["status"]
        assert source["pit_status"]
        assert source["permitted_uses"]
        assert source["prohibited_uses"]
        assert source["unresolved_findings"] or source["status"] == "CERTIFIED_BOUNDED"


def test_unknown_field_fails_closed() -> None:
    registry = _registry()
    registry["sources"][0]["new_unsupported_flag"] = True
    issues = validate_source_registry(registry)
    assert any(issue.code == "UNKNOWN_FIELD" for issue in issues)


def test_non_pit_source_cannot_permit_pit_replay() -> None:
    registry = _registry()
    source = registry["sources"][0]
    source["permitted_uses"].append("PIT_REPLAY")
    issues = validate_source_registry(registry)
    assert any(issue.code == "PIT_OVERCLAIM" for issue in issues)


def test_unknown_timing_cannot_name_a_field() -> None:
    registry = _registry()
    timing = registry["sources"][0]["timing"]["publication"]
    timing["field"] = "published_at"
    issues = validate_source_registry(registry)
    assert any(issue.code == "CONTRADICTORY_TIMING" for issue in issues)


def test_stale_review_is_detected_against_registry_as_of() -> None:
    registry = _registry()
    registry["sources"][0]["freshness"] = {
        "policy": "REVIEW_REQUIRED",
        "last_reviewed": "2020-01-01",
        "stale_after_days": 30,
    }
    issues = validate_source_registry(registry)
    assert any(issue.code == "STALE_ENTRY" for issue in issues)


def test_duplicate_source_id_and_count_mismatch_are_rejected() -> None:
    registry = _registry()
    registry["sources"].append(copy.deepcopy(registry["sources"][0]))
    issues = validate_source_registry(registry)
    codes = {issue.code for issue in issues}
    assert "DUPLICATE_IDENTIFIER" in codes
    assert "COUNT_MISMATCH" in codes


def test_blocked_or_shadow_sources_cannot_be_operationalized() -> None:
    registry = _registry()
    shadow = next(source for source in registry["sources"] if source["source_id"] == "STOCKBIT_INTRADAY")
    shadow["permitted_uses"].append("CANONICAL_EOD")
    issues = validate_source_registry(registry)
    assert any(issue.code == "STATUS_USE_CONTRADICTION" for issue in issues)


def test_assert_and_load_raise_for_invalid_json_contract() -> None:
    registry = _registry()
    registry["sources"][0]["prohibited_uses"].remove("PIT_REPLAY")
    with pytest.raises(RegistryValidationError):
        assert_source_registry(registry)

    bad_path = ROOT / "tests" / ".tmp-invalid-source-registry.json"
    bad_path.write_text("{not json", encoding="utf-8")
    try:
        with pytest.raises(RegistryValidationError):
            load_source_registry(bad_path)
    finally:
        bad_path.unlink(missing_ok=True)
