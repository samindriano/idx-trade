import json

import pytest

from idx_trade.certification import (
    create_certified_snapshot_manifest,
    verify_certified_snapshot_manifest,
)


def _passed_gate():
    return {
        "passed": True,
        "full_universe_summary": {
            "passed": True,
            "window_start": "2026-06-02",
            "window_end": "2026-07-31",
            "required_tickers": 900,
            "passed_tickers": 900,
            "failed_tickers": 0,
            "unknown_sessions": 0,
            "missing_active_prices": 0,
            "quarantined_nonactive_bars": 262,
            "blocker_counts": {},
            "failed_ticker_symbols": [],
        },
    }


def test_certified_snapshot_requires_full_universe_pass(tmp_path):
    artifact = tmp_path / "prices.parquet"
    artifact.write_bytes(b"prices")
    failed = _passed_gate()
    failed["passed"] = False
    with pytest.raises(RuntimeError, match="failed full-universe"):
        create_certified_snapshot_manifest(
            failed,
            {"prices": artifact},
            code_commit="abc123",
            output_path=tmp_path / "manifest.json",
        )


def test_certified_snapshot_hashes_artifacts_and_detects_drift(tmp_path):
    prices = tmp_path / "prices.parquet"
    anchors = tmp_path / "anchors.csv"
    prices.write_bytes(b"price-snapshot-v1")
    anchors.write_text("ticker,state\nAAAA,ACTIVE\n", encoding="utf-8")

    manifest_path = tmp_path / "certified_snapshot.json"
    manifest = create_certified_snapshot_manifest(
        _passed_gate(),
        {"prices": prices, "tradability_anchors": anchors},
        code_commit="abc123",
        output_path=manifest_path,
        metadata={"purpose": "pre-model certification"},
    )

    assert manifest["code_commit"] == "abc123"
    assert manifest["data_gate"]["failed_tickers"] == 0
    assert set(manifest["artifacts"]) == {"prices", "tradability_anchors"}
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["snapshot_schema_version"] == 1

    clean = verify_certified_snapshot_manifest(manifest)
    assert clean["valid"] is True
    assert clean["verified_artifacts"] == 2

    anchors.write_text("ticker,state\nAAAA,NO_TRADE\n", encoding="utf-8")
    drifted = verify_certified_snapshot_manifest(manifest)
    assert drifted["valid"] is False
    assert drifted["mismatches"][0]["status"] == "HASH_MISMATCH"
