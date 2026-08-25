from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.prospective_preaccess_adapters_v1 import (
    ProductionAdapterError,
    build_production_readiness,
    discover_score_inventory,
    discover_sealed_target_producer,
    load_official_schedule,
)


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, payload: dict) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return _sha_bytes(data)


def _manifest(path: Path, artifact: Path, *, artifact_sha: str | None = None) -> dict:
    return {
        "schema_version": "v4_x1_prospective_score_manifest_v2",
        "status": "DONE",
        "session_date": path.parent.parent.name,
        "model_id": "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1",
        "generation": "V4-X1-CLEAN",
        "model_fingerprint": "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf",
        "rows": 2,
        "guards": {
            "historical_prediction_generated": False,
            "model_refit": False,
            "model_retuned": False,
            "protected_outcome_accessed": False,
            "provider_calls": False,
            "realized_forward_outcome_loaded": False,
            "science_changed": False,
        },
        "output": {
            "artifact_path": str(artifact),
            "artifact_sha256": artifact_sha or _sha_bytes(artifact.read_bytes()),
            "columns": ["session_date", "ticker", "alpha_consensus"],
        },
    }


def _runtime(tmp_path: Path) -> tuple[Path, Path]:
    data_root = tmp_path / "data"
    monitoring = data_root / "forward_monitoring"
    calendar = monitoring / "calendar"
    calendar.mkdir(parents=True)
    (calendar / "exchange_sessions.csv").write_text(
        "date\n2026-08-21\n2026-08-24\n2026-08-25\n", encoding="utf-8"
    )
    _write_json(
        calendar / "exchange_session_summary.json",
        {
            "complete": True,
            "source": "IDX_OFFICIAL_EXCHANGE_SESSION_SOURCES",
            "source_identity": "IDX_DAILY_STATISTICS_PUBLICATION_LISTING",
            "sessions_sha256": "a" * 64,
        },
    )
    return data_root, monitoring


def _add_manifest(data_root: Path, date: str, content: bytes = b"not-a-parquet") -> Path:
    manifest_dir = data_root / "forward_monitoring" / "model_runs" / date / "v4_x1_clean_geometry3_prospective_v1"
    artifact = manifest_dir / "score_artifact.parquet"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(content)
    manifest_path = manifest_dir / "manifest.json"
    _write_json(manifest_path, _manifest(manifest_path, artifact))
    return manifest_path


def test_discovery_rehashes_artifact_without_loading_score_rows(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    _add_manifest(data_root, "2026-08-21")
    _add_manifest(data_root, "2026-08-24")
    dates, schedule = load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")
    frame, source = discover_score_inventory(
        monitoring / "model_runs", official_sessions=dates, data_root=data_root
    )
    assert frame["forward_position"].tolist() == [1, 2]
    assert frame["session_index"].tolist() == [1, 2]
    assert source["artifact_values_loaded"] is False
    assert source["artifact_bytes_rehashed"] is True
    assert schedule["status"] == "READY"


def test_tampered_score_artifact_fails_closed(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    manifest_path = _add_manifest(data_root, "2026-08-21")
    artifact = manifest_path.parent / "score_artifact.parquet"
    artifact.write_bytes(b"tampered")
    dates, _ = load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")
    with pytest.raises(ProductionAdapterError, match="SCORE_ARTIFACT_SHA256_MISMATCH"):
        discover_score_inventory(monitoring / "model_runs", official_sessions=dates, data_root=data_root)


def test_target_discovery_is_explicitly_missing_without_reading_target_values(tmp_path: Path) -> None:
    data_root, _ = _runtime(tmp_path)
    result = discover_sealed_target_producer(repo_root=tmp_path / "repo", data_root=data_root)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["target_values"] == "PROTECTED_NOT_READ"
    assert result["producer_path_exists"] is False


def test_actual_runtime_shape_stays_accumulating_and_dependency_blocked(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    _add_manifest(data_root, "2026-08-21")
    pipeline = monitoring / "eod_automation" / "v4_x1_pipeline" / "latest.json"
    _write_json(
        pipeline,
        {
            "x1_counter": {
                "completed": 1,
                "target": 100,
                "remaining": 99,
                "sessions": ["2026-08-21"],
                "artifact_verification": "PASS_ALL_DONE_ROWS",
            }
        },
    )
    report = build_production_readiness(
        repo_root=tmp_path / "repo", data_root=data_root, as_of_session="2026-08-25"
    )
    assert report["readiness"]["overall_status"] == "ACCUMULATING_OUTCOME_BLIND"
    assert report["readiness"]["components"]["counter"]["status"] == "ACCUMULATING"
    assert report["readiness"]["components"]["target_attestation"]["status"] == "NOT_AVAILABLE"
    assert report["guards"]["target_values_loaded"] is False


def test_forbidden_score_column_fails_closed(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    manifest_path = _add_manifest(data_root, "2026-08-21")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["output"]["columns"].append("realized_return")
    _write_json(manifest_path, payload)
    dates, _ = load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")
    with pytest.raises(ProductionAdapterError, match="SCORE_MANIFEST_FORBIDDEN_COLUMNS"):
        discover_score_inventory(monitoring / "model_runs", official_sessions=dates, data_root=data_root)
