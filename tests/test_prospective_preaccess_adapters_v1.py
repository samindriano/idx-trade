from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

import idx_trade.prospective_preaccess_adapters_v1 as adapters
from idx_trade.prospective_preaccess_adapters_v1 import (
    adapt_code_pins,
    adapt_runtime_counter,
    ProductionAdapterError,
    build_production_readiness,
    discover_score_inventory,
    discover_sealed_target_producer,
    gate_shape_inventory_sha256,
    load_official_schedule,
    discover_named_component,
    project_score_frame_to_gate_shape,
    validate_partial_session_inventory,
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
        "ranking": "alpha_consensus DESC, ticker ASC",
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
    session_dates = ["2026-08-21", "2026-08-24", "2026-08-25"]
    sessions_sha = _sha_bytes("\n".join(session_dates).encode("utf-8"))
    _write_json(
        calendar / "exchange_session_summary.json",
        {
            "complete": True,
            "source": "IDX_OFFICIAL_EXCHANGE_SESSION_SOURCES",
            "source_identity": "IDX_DAILY_STATISTICS_PUBLICATION_LISTING",
            "exchange_sessions": len(session_dates),
            "first_session": session_dates[0],
            "last_session": session_dates[-1],
            "sessions_sha256": sessions_sha,
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


def test_production_score_evidence_is_not_gate_admission_when_shape_differs(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    manifest_path = _add_manifest(data_root, "2026-08-21")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["output"]["columns"] = ["ticker", "date", "raw_control_h5", "alpha_consensus"]
    _write_json(manifest_path, payload)
    dates, _ = load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")
    _, source = discover_score_inventory(
        monitoring / "model_runs", official_sessions=dates, data_root=data_root
    )
    assert source["production_evidence_status"] == "READY"
    assert source["score_gate_admission"]["status"] == "NOT_AVAILABLE"
    assert source["score_gate_admission"]["projection_contract"].startswith("EXACT_")


def test_gate_shape_inventory_hash_matches_frozen_gate_formula(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    _add_manifest(data_root, "2026-08-21")
    _add_manifest(data_root, "2026-08-24")
    dates, _ = load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")
    frame, source = discover_score_inventory(
        monitoring / "model_runs", official_sessions=dates, data_root=data_root
    )
    from idx_trade.prospective_evaluation_gate_v1 import _inventory_hash

    gate_frame = frame.copy()
    gate_frame["session_date"] = pd.to_datetime(gate_frame["session_date"])
    assert gate_shape_inventory_sha256(frame) == _inventory_hash(gate_frame)
    assert source["score_gate_admission"]["status"] == "READY"


def test_path_only_changes_do_not_change_gate_shape_hash(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    _add_manifest(data_root, "2026-08-21")
    dates, _ = load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")
    frame, _ = discover_score_inventory(
        monitoring / "model_runs", official_sessions=dates, data_root=data_root
    )
    relocated = frame.copy()
    relocated["score_artifact_path"] = relocated["score_artifact_path"].map(
        lambda value: f"D:/relocated/{Path(value).name}"
    )
    relocated["score_manifest_path"] = relocated["score_manifest_path"].map(
        lambda value: f"D:/relocated/{Path(value).name}"
    )
    partial_original = validate_partial_session_inventory(frame)["partial_inventory_sha256"]
    partial_relocated = validate_partial_session_inventory(relocated)["partial_inventory_sha256"]
    assert partial_original != partial_relocated
    assert gate_shape_inventory_sha256(frame) == gate_shape_inventory_sha256(relocated)


def test_counter_sessions_differ_from_inventory_are_provenance_invalid(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    _add_manifest(data_root, "2026-08-21")
    _add_manifest(data_root, "2026-08-24")
    dates, _ = load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")
    frame, _ = discover_score_inventory(
        monitoring / "model_runs", official_sessions=dates, data_root=data_root
    )
    status = monitoring / "eod_automation" / "v4_x1_pipeline" / "latest.json"
    _write_json(
        status,
        {"x1_counter": {"completed": 1, "target": 100, "remaining": 99, "sessions": ["2026-08-21"]}},
    )
    result = adapt_runtime_counter(status, discovered_inventory=frame)
    assert result["status"] == "PROVENANCE_INVALID"
    assert "SESSIONS_DO_NOT_MATCH" in result["reason"]


def test_counter_completed_differs_from_inventory_count_is_provenance_invalid(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    _add_manifest(data_root, "2026-08-21")
    _add_manifest(data_root, "2026-08-24")
    dates, _ = load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")
    frame, _ = discover_score_inventory(
        monitoring / "model_runs", official_sessions=dates, data_root=data_root
    )
    status = monitoring / "eod_automation" / "v4_x1_pipeline" / "latest.json"
    _write_json(
        status,
        {
            "x1_counter": {
                "completed": 1,
                "target": 100,
                "remaining": 99,
                "sessions": ["2026-08-21", "2026-08-24"],
            }
        },
    )
    result = adapt_runtime_counter(status, discovered_inventory=frame)
    assert result["status"] == "PROVENANCE_INVALID"
    assert "INTERNAL_COUNTS_INVALID" in result["reason"]


def _inventory_100() -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=100, freq="D")
    return pd.DataFrame(
        {
            "forward_position": range(1, 101),
            "session_index": range(1, 101),
            "session_date": [value.date().isoformat() for value in dates],
            "score_artifact_path": [f"D:/safe/scores/{index}.parquet" for index in range(100)],
            "score_artifact_sha256": ["a" * 64] * 100,
            "score_manifest_path": [f"D:/safe/manifests/{index}.json" for index in range(100)],
            "score_manifest_sha256": ["b" * 64] * 100,
        }
    )


def test_runtime_100_without_canonical_counter_attestation_is_pending(tmp_path: Path) -> None:
    inventory = _inventory_100()
    status = tmp_path / "latest.json"
    _write_json(
        status,
        {
            "x1_counter": {
                "completed": 100,
                "target": 100,
                "remaining": 0,
                "sessions": inventory["session_date"].tolist(),
            }
        },
    )
    result = adapt_runtime_counter(status, discovered_inventory=inventory)
    assert result["status"] == "PENDING_EXPECTED"
    assert "ATTESTATION_MISSING" in result["reason"]


def test_calendar_sessions_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    summary = monitoring / "calendar" / "exchange_session_summary.json"
    payload = json.loads(summary.read_text(encoding="utf-8"))
    payload["sessions_sha256"] = "0" * 64
    _write_json(summary, payload)
    with pytest.raises(ProductionAdapterError, match="CALENDAR_SESSIONS_SHA256_MISMATCH"):
        load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")


def test_calendar_coverage_count_mismatch_fails_closed(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    summary = monitoring / "calendar" / "exchange_session_summary.json"
    payload = json.loads(summary.read_text(encoding="utf-8"))
    payload["exchange_sessions"] = 99
    _write_json(summary, payload)
    with pytest.raises(ProductionAdapterError, match="CALENDAR_DECLARED_COUNT_MISMATCH"):
        load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")


def test_code_pin_blob_mismatch_is_provenance_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = Path(__file__).resolve().parents[1]
    real = adapters._git_blob_sha1_file

    def wrong_blob(path: str | Path) -> str:
        if Path(path).name == "prospective_evaluation_v1.py":
            return "0" * 40
        return real(path)

    monkeypatch.setattr(adapters, "_git_blob_sha1_file", wrong_blob)
    result = adapt_code_pins(repo)
    assert result["status"] == "PROVENANCE_INVALID"
    assert "GIT_BLOB_MISMATCH" in result["reason"]


def test_target_construction_sha_mismatch_is_provenance_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = Path(__file__).resolve().parents[1]
    real = adapters.sha256_file

    def wrong_sha(path: str | Path) -> str:
        if Path(path).name == "v4_x1_canonical_target_v1.py":
            return "0" * 64
        return real(path)

    monkeypatch.setattr(adapters, "sha256_file", wrong_sha)
    result = adapt_code_pins(repo)
    assert result["status"] == "PROVENANCE_INVALID"
    assert "SHA256_MISMATCH" in result["reason"]


def test_dirty_access_policy_fails_closed(tmp_path: Path) -> None:
    source_repo = Path(__file__).resolve().parents[1]
    target_repo = tmp_path / "repo"
    for relative in (
        "config/v4_x1_prospective_evaluation_code_pin_v1.json",
        "config/v4_x1_prospective_evaluation_contract_v1.json",
        "config/v4_x1_canonical_target_spec_v1.json",
        "src/idx_trade/prospective_evaluation_v1.py",
        "src/idx_trade/prospective_evaluation_gate_v1.py",
        "src/idx_trade/v4_x1_canonical_target_v1.py",
        "docs/checkpoints/2026-08-24_V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1.md",
    ):
        destination = target_repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_repo / relative, destination)
    pin_path = target_repo / "config/v4_x1_prospective_evaluation_code_pin_v1.json"
    payload = json.loads(pin_path.read_text(encoding="utf-8"))
    payload["access_policy"]["real_loader_allowed"] = True
    _write_json(pin_path, payload)
    result = adapt_code_pins(target_repo)
    assert result["status"] == "PROVENANCE_INVALID"
    assert "ACCESS_POLICY_DIRTY" in result["reason"]


def test_protected_subtree_is_skipped_without_reading_content(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    protected = data_root / "outcome_vault"
    protected.mkdir(parents=True)
    (protected / "target_manifest.json").write_bytes(b"not-json-and-must-not-be-opened")
    result = discover_named_component(
        name="target_attestation", data_root=data_root, filename_tokens=("target", "manifest")
    )
    assert result["status"] == "NOT_AVAILABLE"


def test_unrelated_model_manifest_is_not_opened_by_exact_discovery(tmp_path: Path) -> None:
    data_root, monitoring = _runtime(tmp_path)
    _add_manifest(data_root, "2026-08-21")
    unrelated = monitoring / "model_runs" / "2026-08-21" / "hgb_xs_market" / "manifest.json"
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    unrelated.write_bytes(b"this is intentionally invalid JSON")
    dates, _ = load_official_schedule(monitoring / "calendar" / "exchange_sessions.csv")
    frame, source = discover_score_inventory(
        monitoring / "model_runs", official_sessions=dates, data_root=data_root
    )
    assert len(frame) == 1
    assert source["candidate_manifest_count"] == 1


def test_historical_target_producer_presence_does_not_make_attestation_ready(tmp_path: Path) -> None:
    data_root, _ = _runtime(tmp_path)
    repo = tmp_path / "repo"
    semantic = repo / "src" / "idx_trade" / "v4_x1_canonical_target_v1.py"
    semantic.parent.mkdir(parents=True, exist_ok=True)
    semantic.write_text("# outcome-free semantic pin\n", encoding="utf-8")
    result = discover_sealed_target_producer(repo_root=repo, data_root=data_root)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["historical_materializer_promotion_allowed"] is False
    assert result["target_values"] == "PROTECTED_NOT_READ"


def test_gate_projection_selects_exact_columns_without_reranking() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2026-08-21", "2026-08-21"],
            "ticker": ["ZZZ", "AAA"],
            "alpha_consensus": [0.1, 0.9],
        }
    )
    projected = project_score_frame_to_gate_shape(frame)
    assert projected.equals(frame)
