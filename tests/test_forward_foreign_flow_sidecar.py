from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.forward_foreign_flow import enrich_session_foreign_flow, verify_session_foreign_flow
from idx_trade.provenance import sha256_file
from idx_trade.forward_foreign_flow_runtime import run_foreign_flow_catchup


def _session(root: Path) -> Path:
    directory = root / "forward_monitoring" / "sessions" / "2026-08-12"
    directory.mkdir(parents=True)
    payload = {
        "recordsTotal": 2,
        "recordsFiltered": 2,
        "data": [
            {"StockCode": "BBCA", "Date": "2026-08-12", "ForeignBuy": 1200, "ForeignSell": 1000},
            {"StockCode": "GOTOM", "Date": "2026-08-12", "ForeignBuy": 0, "ForeignSell": 0},
        ],
    }
    raw = json.dumps(payload, sort_keys=True).encode()
    raw_path = directory / "idx_stock_summary.raw.json"
    raw_path.write_bytes(raw)
    manifest = {
        "status": "DATA_READY",
        "session_date": "2026-08-12",
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "stock_summary_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "stock_summary_source": {
            "source": "IDX_OFFICIAL",
            "endpoint": "https://www.idx.id/primary/TradingSummary/GetStockSummary",
            "params": {"date": "20260812"},
            "source_ref": "https://www.idx.id/primary/TradingSummary/GetStockSummary?date=20260812",
            "session_date": "2026-08-12",
            "observed_available_at_utc": "2026-08-12T11:05:00+00:00",
            "row_count": 2,
            "records_total": 2,
            "records_filtered": 2,
            "completeness_status": "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
    return directory


def test_sidecar_is_offline_idempotent_and_hash_bound(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    first = enrich_session_foreign_flow(tmp_path, "2026-08-12")
    second = enrich_session_foreign_flow(tmp_path, "2026-08-12")
    assert first["provider_calls"] == 0
    assert first["sidecar_sha256"] == second["sidecar_sha256"]
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert verify_session_foreign_flow(tmp_path, "2026-08-12")
    frame = pd.read_parquet(directory / "idx_foreign_flow.parquet")
    assert frame.loc[0, "foreign_net"] == 200


def test_parent_revision_fails_closed(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    enrich_session_foreign_flow(tmp_path, "2026-08-12")
    (directory / "idx_stock_summary.raw.json").write_text("{}")
    assert not verify_session_foreign_flow(tmp_path, "2026-08-12")
    with pytest.raises(RuntimeError, match="raw SHA mismatch"):
        enrich_session_foreign_flow(tmp_path, "2026-08-12")


def test_catchup_never_refetches_provider(tmp_path: Path) -> None:
    _session(tmp_path)
    first = run_foreign_flow_catchup(tmp_path)
    second = run_foreign_flow_catchup(tmp_path)
    assert first["provider_calls"] == second["provider_calls"] == 0
    assert len(first["created"]) == 1
    assert second["created"] == []
    assert second["already_valid"] == ["2026-08-12"]
    assert len(first["verified"]) == len(second["verified"]) == 1
    assert second["verified"][0]["four_character_codes"] == 1
    assert second["verified"][0]["five_character_codes"] == 1
    assert second["verified"][0]["zero_flow_rows"] == 1
    assert second["verified"][0]["provider_calls"] == 0


def test_parent_must_be_data_ready_and_have_exact_source_contract(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    parent_path = directory / "manifest.json"
    parent = json.loads(parent_path.read_text())
    parent["status"] = "FETCHING"
    parent_path.write_text(json.dumps(parent, sort_keys=True))
    with pytest.raises(RuntimeError, match="DATA_READY"):
        enrich_session_foreign_flow(tmp_path, "2026-08-12")

    parent["status"] = "DATA_READY"
    parent["stock_summary_source"]["params"]["date"] = "20260811"
    parent_path.write_text(json.dumps(parent, sort_keys=True))
    with pytest.raises(RuntimeError, match="parameter mismatch"):
        enrich_session_foreign_flow(tmp_path, "2026-08-12")


def test_parent_source_requires_https_and_canonical_completeness(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    parent_path = directory / "manifest.json"
    parent = json.loads(parent_path.read_text())
    parent["stock_summary_source"]["source_ref"] = "http://www.idx.id/unsafe"
    parent_path.write_text(json.dumps(parent, sort_keys=True))
    with pytest.raises(RuntimeError, match="HTTPS"):
        enrich_session_foreign_flow(tmp_path, "2026-08-12")

    parent["stock_summary_source"]["source_ref"] = "https://www.idx.id/safe"
    parent["stock_summary_source"]["completeness_status"] = "UNVERIFIED"
    parent_path.write_text(json.dumps(parent, sort_keys=True))
    with pytest.raises(RuntimeError, match="completeness"):
        enrich_session_foreign_flow(tmp_path, "2026-08-12")


def test_valid_sidecar_can_complete_interrupted_manifest_without_rewrite(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    parent_before = (directory / "manifest.json").read_bytes()
    first = enrich_session_foreign_flow(tmp_path, "2026-08-12")
    sidecar_before = (directory / "idx_foreign_flow.parquet").read_bytes()
    (directory / "idx_foreign_flow.manifest.json").unlink()
    second = enrich_session_foreign_flow(tmp_path, "2026-08-12")
    assert first["sidecar_sha256"] == second["sidecar_sha256"]
    assert sidecar_before == (directory / "idx_foreign_flow.parquet").read_bytes()
    assert parent_before == (directory / "manifest.json").read_bytes()
    assert verify_session_foreign_flow(tmp_path, "2026-08-12")


def test_coherent_sidecar_and_sidecar_manifest_tamper_fails_canonical_verification(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    enrich_session_foreign_flow(tmp_path, "2026-08-12")
    sidecar_path = directory / "idx_foreign_flow.parquet"
    manifest_path = directory / "idx_foreign_flow.manifest.json"
    tampered = pd.read_parquet(sidecar_path)
    tampered.loc[0, "foreign_buy"] = 9999
    tampered.loc[0, "foreign_net"] = 8999
    tampered.to_parquet(sidecar_path, index=False)
    sidecar_manifest = json.loads(manifest_path.read_text())
    sidecar_manifest["sidecar_sha256"] = sha256_file(sidecar_path)
    manifest_path.write_text(json.dumps(sidecar_manifest, indent=2, sort_keys=True))
    assert not verify_session_foreign_flow(tmp_path, "2026-08-12")


def test_existing_conflicting_sidecar_is_never_overwritten(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    enrich_session_foreign_flow(tmp_path, "2026-08-12")
    sidecar_path = directory / "idx_foreign_flow.parquet"
    tampered = pd.read_parquet(sidecar_path)
    tampered.loc[0, "foreign_buy"] = 9999
    tampered.loc[0, "foreign_net"] = 8999
    tampered.to_parquet(sidecar_path, index=False)
    before = sidecar_path.read_bytes()
    with pytest.raises(RuntimeError, match="sidecar revision conflict"):
        enrich_session_foreign_flow(tmp_path, "2026-08-12")
    assert sidecar_path.read_bytes() == before


def test_runtime_rejects_non_data_ready_parent_without_provider_calls(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    parent_path = directory / "manifest.json"
    parent = json.loads(parent_path.read_text())
    parent["status"] = "DATA_FAILED"
    parent_path.write_text(json.dumps(parent, sort_keys=True))
    result = run_foreign_flow_catchup(tmp_path)
    assert result["status"] == "INCOMPLETE"
    assert result["provider_calls"] == 0
    assert result["created"] == []
    assert result["failed"][0]["session_date"] == "2026-08-12"
