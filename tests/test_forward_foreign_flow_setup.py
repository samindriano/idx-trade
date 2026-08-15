from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.forward_foreign_flow_runtime import run_foreign_flow_catchup
from idx_trade.forward_foreign_flow_setup import (
    SETUP_MANIFEST_FILENAME,
    SETUP_SIDECAR_FILENAME,
    enrich_session_foreign_flow_setup,
    verify_session_foreign_flow_setup,
)
from idx_trade.provenance import sha256_file


def _session(root: Path) -> Path:
    directory = root / "forward_monitoring" / "sessions" / "2026-08-12"
    directory.mkdir(parents=True)
    calendar = root / "forward_monitoring" / "calendar" / "exchange_sessions.csv"
    calendar.parent.mkdir(parents=True)
    calendar.write_text("date\n2026-08-11\n2026-08-12\n", encoding="utf-8")
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
        "calendar_path": str(calendar),
        "calendar_sha256": sha256_file(calendar),
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


def _representation(directory: Path) -> Path:
    frame = pd.DataFrame(
        [
            {
                "ticker": "BBCA",
                "feature_session": "2026-08-12",
                "flow_through_session": "2026-08-11",
                "foreign_participation_1": 0.05,
                "foreign_participation_mean_5": 0.04,
                "foreign_flow_shock_1": 2.0,
                "foreign_flow_shock_mean_5": 1.5,
                "foreign_flow_shock_mean_20": 1.2,
                "foreign_flow_shock_percentile_120": 0.95,
                "xs_rank_foreign_flow_shock_1": 0.8,
                "xs_rank_foreign_flow_shock_mean_5": 0.9,
                "xs_rank_foreign_flow_shock_mean_20": 0.85,
                "foreign_weighted_persistence_5": 0.7,
                "foreign_weighted_persistence_20": 0.8,
                "foreign_signed_streak_10": 0.4,
                "foreign_flow_acceleration_5_20": 0.1,
                "foreign_flow_price_divergence_5": 0.25,
                "foreign_flow_price_divergence_20": 0.2,
            }
        ]
    )
    path = directory / "foreign_flow_representation_v2.parquet"
    frame.to_parquet(path, index=False)
    manifest = {
        "status": "FOREIGN_FLOW_REPRESENTATION_V2_READY",
        "artifact_sha256": sha256_file(path),
        "outcome_blind": True,
        "no_provider_calls": True,
        "fresh_forward_accessed": False,
        "outcome_metrics_computed": False,
        "prohibited_actions": {
            "fresh_forward_accessed": False,
            "outcomes_or_labels_accessed": False,
            "model_fit": False,
            "model_scoring": False,
        },
    }
    (directory / "foreign_flow_representation_v2.manifest.json").write_text(
        json.dumps(manifest, sort_keys=True)
    )
    return path


def test_setup_sidecar_is_idempotent_and_pins_v2_and_parent(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    representation = _representation(directory)

    first = enrich_session_foreign_flow_setup(tmp_path, "2026-08-12")
    sidecar = directory / SETUP_SIDECAR_FILENAME
    manifest = directory / SETUP_MANIFEST_FILENAME
    before = sidecar.read_bytes()
    second = enrich_session_foreign_flow_setup(tmp_path, "2026-08-12")

    assert first["provider_calls"] == second["provider_calls"] == 0
    assert first["setup_sidecar_sha256"] == second["setup_sidecar_sha256"]
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert before == sidecar.read_bytes()
    assert verify_session_foreign_flow_setup(tmp_path, "2026-08-12")
    saved = json.loads(manifest.read_text())
    assert saved["representation_sha256"] == sha256_file(representation)
    assert saved["parent_session_manifest_sha256"]
    assert saved["source_raw_sha256"]
    assert saved["outcome_blind"] is True
    assert saved["forward_outcomes_accessed"] is False


def test_setup_fails_closed_on_representation_revision_after_creation(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    representation = _representation(directory)
    enrich_session_foreign_flow_setup(tmp_path, "2026-08-12")
    changed = pd.read_parquet(representation)
    changed.loc[0, "foreign_flow_shock_1"] = 99.0
    changed.to_parquet(representation, index=False)
    assert not verify_session_foreign_flow_setup(tmp_path, "2026-08-12")
    with pytest.raises(RuntimeError, match="SHA mismatch"):
        enrich_session_foreign_flow_setup(tmp_path, "2026-08-12")


def test_setup_fails_closed_on_noncausal_flow_through_session(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    representation = _representation(directory)
    frame = pd.read_parquet(representation)
    frame.loc[0, "flow_through_session"] = "2026-08-12"
    frame.to_parquet(representation, index=False)
    manifest_path = directory / "foreign_flow_representation_v2.manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifact_sha256"] = sha256_file(representation)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(RuntimeError, match="prior official session"):
        enrich_session_foreign_flow_setup(tmp_path, "2026-08-12")


def test_setup_rejects_extra_outcome_like_representation_columns(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    representation = _representation(directory)
    frame = pd.read_parquet(representation)
    frame["future_return_t1"] = 0.1
    frame.to_parquet(representation, index=False)
    manifest_path = directory / "foreign_flow_representation_v2.manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifact_sha256"] = sha256_file(representation)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(RuntimeError, match="non-contract columns"):
        enrich_session_foreign_flow_setup(tmp_path, "2026-08-12")


def test_runtime_wires_setup_only_when_v2_representation_is_present(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    _representation(directory)
    result = run_foreign_flow_catchup(tmp_path)
    assert result["provider_calls"] == 0
    assert len(result["setup_state_created"]) == 1
    assert result["setup_state_created"][0]["session_date"] == "2026-08-12"
    assert result["setup_state_skipped_no_representation"] == []
    assert result["status"] == "COMPLETE"


def test_runtime_marks_missing_v2_input_without_failing_raw_sidecar(tmp_path: Path) -> None:
    _session(tmp_path)
    result = run_foreign_flow_catchup(tmp_path)
    assert result["status"] == "COMPLETE"
    assert result["setup_state_skipped_no_representation"] == ["2026-08-12"]
    assert result["setup_state_created"] == []
