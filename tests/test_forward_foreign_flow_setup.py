from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.forward_foreign_flow_runtime import run_foreign_flow_catchup
from idx_trade.foreign_flow_features_v2 import FEATURE_COLUMNS_V2, OUTPUT_COLUMNS_V2
from idx_trade.forward_foreign_flow_setup import (
    SETUP_MANIFEST_FILENAME,
    SETUP_SIDECAR_FILENAME,
    enrich_prospective_foreign_flow_setup,
    enrich_session_foreign_flow_setup,
    verify_prospective_foreign_flow_setup,
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


def _prospective_representation(root: Path) -> tuple[Path, Path, Path]:
    calendar = root / "forward_monitoring" / "calendar" / "exchange_sessions.csv"
    calendar.parent.mkdir(parents=True, exist_ok=True)
    calendar.write_text("date\n2026-08-11\n2026-08-12\n", encoding="utf-8")
    directory = (
        root
        / "forward_monitoring"
        / "prospective"
        / "foreign_flow_representation_v2"
        / "2026-08-12"
    )
    directory.mkdir(parents=True)
    representation = _representation(directory)
    manifest_path = representation.with_name("foreign_flow_representation_v2.manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "status": "FOREIGN_FLOW_REPRESENTATION_V2_FORWARD_READY",
            "schema": "idx-trade/foreign-flow-representation-v2-forward-v1",
            "feature_columns": list(FEATURE_COLUMNS_V2),
            "output_columns": list(OUTPUT_COLUMNS_V2),
            "artifact_path": str(representation.resolve()),
            "feature_session": "2026-08-12",
            "flow_through_session": "2026-08-11",
            "row_count": 1,
            "ticker_count": 1,
            "provider_calls": 0,
            "fresh_forward_accessed": False,
            "outcomes_or_labels_accessed": False,
            "outcome_metrics_computed": False,
            "model_fit": False,
            "model_scoring": False,
            "prohibited_actions": {
                "fresh_forward_accessed": False,
                "outcomes_or_labels_accessed": False,
                "model_fit": False,
                "model_scoring": False,
            },
            "input_provenance": {
                "official_sessions_path": str(calendar.resolve()),
                "official_sessions_sha256": sha256_file(calendar),
                "source_session": "2026-08-11",
                "feature_session": "2026-08-12",
            },
        }
    )
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return representation, manifest_path, calendar


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


def test_prospective_setup_exists_before_target_capture(tmp_path: Path) -> None:
    representation, representation_manifest, calendar = _prospective_representation(tmp_path)

    result = enrich_prospective_foreign_flow_setup(representation, representation_manifest)
    setup_path = representation.with_name(SETUP_SIDECAR_FILENAME)
    setup_manifest_path = representation.with_name(SETUP_MANIFEST_FILENAME)

    assert result["status"] == "FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_READY"
    assert result["source_session"] == "2026-08-11"
    assert setup_path.is_file()
    assert setup_manifest_path.is_file()
    assert not (tmp_path / "forward_monitoring" / "sessions" / "2026-08-12").exists()
    assert verify_prospective_foreign_flow_setup(
        representation,
        representation_manifest,
    )
    saved = json.loads(setup_manifest_path.read_text(encoding="utf-8"))
    assert saved["target_session_captured"] is False
    assert saved["calendar"]["sha256"] == sha256_file(calendar)
    assert saved["source_session"] == "2026-08-11"
    assert saved["feature_session"] == "2026-08-12"
    assert saved["provider_calls"] == 0
    assert saved["outcome_blind"] is True
    assert saved["forward_outcomes_accessed"] is False


def test_prospective_setup_is_invariant_to_later_target_data(tmp_path: Path) -> None:
    representation, representation_manifest, _ = _prospective_representation(tmp_path)
    enrich_prospective_foreign_flow_setup(representation, representation_manifest)
    setup_path = representation.with_name(SETUP_SIDECAR_FILENAME)
    setup_manifest_path = representation.with_name(SETUP_MANIFEST_FILENAME)
    sidecar_before = setup_path.read_bytes()
    manifest_before = setup_manifest_path.read_bytes()

    target = tmp_path / "forward_monitoring" / "sessions" / "2026-08-12"
    target.mkdir(parents=True)
    pd.DataFrame(
        [{"ticker": "BBCA", "session_date": "2026-08-12", "close": 999999.0}]
    ).to_parquet(target / "late_market.parquet", index=False)
    pd.DataFrame(
        [{"ticker": "BBCA", "session_date": "2026-08-12", "foreign_net": -999999.0}]
    ).to_parquet(target / "late_flow.parquet", index=False)

    assert verify_prospective_foreign_flow_setup(representation, representation_manifest)
    assert sidecar_before == setup_path.read_bytes()
    assert manifest_before == setup_manifest_path.read_bytes()


def test_prospective_setup_fails_closed_on_representation_revision(tmp_path: Path) -> None:
    representation, representation_manifest, _ = _prospective_representation(tmp_path)
    enrich_prospective_foreign_flow_setup(representation, representation_manifest)
    changed = pd.read_parquet(representation)
    changed.loc[0, "foreign_flow_shock_1"] = 99.0
    changed.to_parquet(representation, index=False)

    assert not verify_prospective_foreign_flow_setup(representation, representation_manifest)
    with pytest.raises(RuntimeError, match="SHA mismatch"):
        enrich_prospective_foreign_flow_setup(representation, representation_manifest)


def test_prospective_setup_rejects_wrong_output_location(tmp_path: Path) -> None:
    representation, representation_manifest, _ = _prospective_representation(tmp_path)

    with pytest.raises(RuntimeError, match="share the Representation V2 directory"):
        enrich_prospective_foreign_flow_setup(
            representation,
            representation_manifest,
            output_directory=tmp_path / "other",
        )


def test_prospective_setup_rejects_manifest_flag_or_count_drift(tmp_path: Path) -> None:
    representation, representation_manifest, _ = _prospective_representation(tmp_path)
    manifest = json.loads(representation_manifest.read_text(encoding="utf-8"))
    manifest["provider_calls"] = 1
    representation_manifest.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    assert not verify_prospective_foreign_flow_setup(representation, representation_manifest)
    with pytest.raises(RuntimeError, match="provider-call flag"):
        enrich_prospective_foreign_flow_setup(representation, representation_manifest)

    representation, representation_manifest, _ = _prospective_representation(tmp_path / "count")
    manifest = json.loads(representation_manifest.read_text(encoding="utf-8"))
    manifest["row_count"] = 2
    representation_manifest.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    assert not verify_prospective_foreign_flow_setup(representation, representation_manifest)


def test_prospective_setup_rejects_calendar_revision(tmp_path: Path) -> None:
    representation, representation_manifest, calendar = _prospective_representation(tmp_path)
    enrich_prospective_foreign_flow_setup(representation, representation_manifest)
    calendar.write_text("date\n2026-08-10\n2026-08-12\n", encoding="utf-8")
    assert not verify_prospective_foreign_flow_setup(representation, representation_manifest)


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


def test_runtime_consumes_prospective_representation_after_target_capture(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    prospective = (
        tmp_path
        / "forward_monitoring"
        / "prospective"
        / "foreign_flow_representation_v2"
        / "2026-08-12"
    )
    prospective.mkdir(parents=True)
    representation = _representation(prospective)

    result = run_foreign_flow_catchup(tmp_path)

    assert result["status"] == "COMPLETE"
    assert result["setup_state_consumed_prospective"] == ["2026-08-12"]
    setup_manifest = json.loads(
        (directory / "idx_foreign_flow_setup.manifest.json").read_text()
    )
    assert setup_manifest["representation_path"] == str(representation)
    assert setup_manifest["representation_sha256"] == sha256_file(representation)
    assert verify_session_foreign_flow_setup(
        tmp_path,
        "2026-08-12",
        representation_path=representation,
        representation_manifest_path=prospective / "foreign_flow_representation_v2.manifest.json",
    )


def test_runtime_marks_missing_v2_input_without_failing_raw_sidecar(tmp_path: Path) -> None:
    _session(tmp_path)
    result = run_foreign_flow_catchup(tmp_path)
    assert result["status"] == "COMPLETE"
    assert result["setup_state_skipped_no_representation"] == ["2026-08-12"]
    assert result["setup_state_created"] == []
