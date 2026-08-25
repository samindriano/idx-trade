from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from idx_trade.forward_evidence_health_v1 import (
    ArtifactSpec,
    EvidenceHealthError,
    build_operational_summary,
    check_artifact,
    discover_session_artifacts,
    evaluate_session,
    write_health_report,
)


SESSION = "2026-08-25"


def _write_json(path: Path, payload: dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    path.write_text(body, encoding="utf-8")
    return hashlib.sha256(body.encode()).hexdigest()


def _core(tmp_path: Path) -> list[ArtifactSpec]:
    eod = tmp_path / "eod" / "manifest.json"
    score = tmp_path / "score" / "manifest.json"
    open_manifest = tmp_path / "open" / "manifest.json"
    _write_json(eod, {"status": "DATA_READY", "session_date": SESSION, "outcome_blind": True, "forward_outcomes_accessed": False})
    _write_json(score, {"status": "DONE", "session_date": SESSION, "guards": {"protected_outcome_accessed": False, "realized_forward_outcome_loaded": False}})
    _write_json(open_manifest, {"session_date": SESSION, "authority": "IDX", "upstream_path": "TradingSummary/GetStockSummary", "field_semantics": "IDX_OFFICIAL_OPENPRICE"})
    return [
        ArtifactSpec("eod", eod, expected_status="DATA_READY", require_outcome_clean=True),
        ArtifactSpec("score", score, expected_status="DONE", require_outcome_clean=True),
        ArtifactSpec("open", open_manifest, expected_fields=(("authority", "IDX"), ("upstream_path", "TradingSummary/GetStockSummary"), ("field_semantics", "IDX_OFFICIAL_OPENPRICE"))),
    ]


def test_complete_requires_all_declared_safe_artifacts(tmp_path: Path):
    report = evaluate_session(SESSION, _core(tmp_path), reported_at_utc="2026-08-25T00:00:00+00:00")
    assert report["overall_status"] == "COMPLETE"
    assert report["protected_outcomes"] == {"status": "PROTECTED_NOT_READ", "accessed": False, "values_loaded": False}
    assert all(item["status"] == "COMPLETE" for item in report["artifacts"])


def test_missing_required_artifact_is_pending_not_complete(tmp_path: Path):
    specs = _core(tmp_path)
    specs.append(ArtifactSpec("prepared_order", tmp_path / "prepared" / f"{SESSION}.json"))
    report = evaluate_session(SESSION, specs, reported_at_utc="2026-08-25T00:00:00+00:00")
    assert report["overall_status"] == "PENDING_EXPECTED"
    pending = [item for item in report["artifacts"] if item["name"] == "prepared_order"][0]
    assert pending["reason"] == "ARTIFACT_MISSING"


def test_hash_tamper_is_provenance_invalid(tmp_path: Path):
    specs = _core(tmp_path)
    path = specs[0].path
    assert path is not None
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    path.write_text(path.read_text(encoding="utf-8").replace("DATA_READY", "DATA_FAILED"), encoding="utf-8")
    specs[0] = ArtifactSpec("eod", path, expected_sha256=expected, expected_status="DATA_READY", require_outcome_clean=True)
    result = check_artifact(specs[0], session_date=SESSION)
    assert result["status"] == "PROVENANCE_INVALID"
    assert result["reason"] == "ARTIFACT_SHA256_MISMATCH"


def test_session_identity_and_outcome_guard_fail_closed(tmp_path: Path):
    path = tmp_path / "score" / "manifest.json"
    _write_json(path, {"status": "DONE", "session_date": "2026-08-24", "guards": {"protected_outcome_accessed": True}})
    result = check_artifact(ArtifactSpec("score", path, expected_status="DONE", require_outcome_clean=True), session_date=SESSION)
    assert result["status"] == "PROVENANCE_INVALID"
    assert result["reason"] in {"SESSION_IDENTITY_MISMATCH", "FORWARD_HEALTH_OUTCOME_GUARD_NOT_CLEAN"}


def test_protected_path_is_refused_before_read(tmp_path: Path):
    path = tmp_path / "protected_outcomes" / "manifest.json"
    path.parent.mkdir()
    path.write_text("{}", encoding="utf-8")
    result = check_artifact(ArtifactSpec("protected", path), session_date=SESSION)
    assert result["status"] == "PROVENANCE_INVALID"
    assert result["reason"] == "FORWARD_HEALTH_PROTECTED_ARTIFACT_PATH_REFUSED"


def test_report_hash_is_deterministic_for_fixed_timestamp(tmp_path: Path):
    report = evaluate_session(SESSION, _core(tmp_path), reported_at_utc="2026-08-25T00:00:00+00:00")
    first, first_sha = write_health_report(tmp_path / "a.json", report)
    second, second_sha = write_health_report(tmp_path / "b.json", report)
    assert first.read_bytes() == second.read_bytes()
    assert first_sha == second_sha


def test_operational_summary_is_status_only_and_lists_blockers(tmp_path: Path):
    report = evaluate_session(SESSION, _core(tmp_path), reported_at_utc="2026-08-25T00:00:00+00:00")
    summary = build_operational_summary(
        report,
        stockbit_last_status="COMPLETE_SHADOW",
        current_forward_counter="NOT_READ",
        next_scheduled_action="NEXT_GENUINE_SCHEDULED_SESSION",
    )
    assert summary["current_session"] == SESSION
    assert summary["stockbit_last_status"] == "COMPLETE_SHADOW"
    assert summary["current_forward_counter"] == "NOT_READ"
    assert summary["known_blockers"] == []
    assert "outcome" not in json.dumps(summary).lower()


def test_discovery_declares_operational_inputs_without_reading_values(tmp_path: Path):
    specs = discover_session_artifacts(
        forward_monitoring_root=tmp_path / "forward",
        e2e_runtime_root=tmp_path / "e2e",
        session_date=SESSION,
    )
    names = {item.name for item in specs}
    assert {"eod_manifest", "v4_x1_score_manifest", "official_open_manifest", "prepared_order", "execution_result", "paper_state_snapshot"} <= names
    assert next(item for item in specs if item.name == "operational_status").required is False
