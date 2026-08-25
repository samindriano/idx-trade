from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from idx_trade.forward_session_audit_v1 import (
    IMPLEMENTATION_DEFECT,
    LEGITIMATE_NOOP,
    NOT_APPLICABLE,
    NOT_READ,
    PASS,
    PENDING_EXPECTED,
    PROVENANCE_INVALID,
    SessionAuditError,
    audit_session,
    summarize_ledgers,
    write_json,
)


SESSION = "2026-08-26"


def _write(path: Path, payload: dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    path.write_text(body, encoding="utf-8")
    return hashlib.sha256(body.encode()).hexdigest()


def _safe_guarded(status: str = "PASS", **extra: object) -> dict[str, object]:
    return {
        "status": status,
        "session_date": SESSION,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "guards": {
            "protected_outcome_accessed": False,
            "realized_forward_outcome_loaded": False,
        },
        **extra,
    }


def _fixture(tmp_path: Path, *, decision_status: str = "PASS", include_open: bool = True):
    forward = tmp_path / "forward"
    e2e = tmp_path / "e2e"
    calendar = tmp_path / "calendar.json"
    runtime = tmp_path / "runtime.json"
    stockbit = tmp_path / "stockbit.json"
    ca = tmp_path / "ca.json"
    scheduler = tmp_path / "scheduler.json"
    _write(calendar, {"status": "PASS", "session_date": SESSION, "is_trading_session": True})
    _write(runtime, {"status": "PASS", "session_date": SESSION, "runtime_sha256": "abc", "expected_runtime_sha256": "abc"})
    _write(stockbit, _safe_guarded(captured_at_utc="2026-08-26T09:10:00+07:00"))
    _write(ca, _safe_guarded(evidence_at_utc="2026-08-26T18:00:00+07:00"))
    _write(
        scheduler,
        {
            "status": "PASS",
            "session_date": SESSION,
            "task_name": "IDXTrade-E2E-OfficialOpen",
            "runner": "scripts/run_official_open_capture_v2.ps1",
            "triggers": ["09:02", "09:07", "09:12", "09:17", "09:22", "AtLogOn"],
            "start_when_available": True,
            "multiple_instances": "IgnoreNew",
            "network_required": True,
        },
    )

    eod_dir = forward / "sessions" / SESSION
    snapshot = eod_dir / "model_input.bin"
    evidence = eod_dir / "session_evidence.bin"
    eod_dir.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(b"synthetic model input bytes")
    evidence.write_bytes(b"synthetic evidence bytes")
    _write(
        eod_dir / "manifest.json",
        _safe_guarded(
            "DATA_READY",
            snapshot_path=snapshot.name,
            snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            evidence_path=evidence.name,
            evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
        ),
    )

    score_dir = forward / "model_runs" / SESSION / "v4_x1_clean_geometry3_prospective_v1"
    score_artifact = score_dir / "score.bin"
    score_dir.mkdir(parents=True, exist_ok=True)
    score_artifact.write_bytes(b"synthetic score bytes")
    _write(score_dir / "manifest.json", _safe_guarded("DONE", score_artifact_path=score_artifact.name, score_artifact_sha256=hashlib.sha256(score_artifact.read_bytes()).hexdigest()))

    _write(e2e / "state" / "decisions" / f"{SESSION}.json", _safe_guarded(decision_status, decision_state=decision_status, trade_count=0 if decision_status == "LEGITIMATE_NOOP" else 1, evidence_at_utc="2026-08-26T18:01:00+07:00"))
    if decision_status != "LEGITIMATE_NOOP":
        _write(e2e / "prepared" / f"{SESSION}.json", _safe_guarded("PASS", execution_session_date=SESSION, prepared_at_utc="2026-08-26T18:02:00+07:00"))

    raw = e2e / "official_open" / SESSION / "raw.bin"
    normalized = e2e / "official_open" / SESSION / "normalized.bin"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(b"synthetic official IDX raw bytes")
    normalized.write_bytes(b"synthetic official IDX normalized bytes")
    if include_open:
        _write(
            raw.parent / "manifest.json",
            {
                "status": "PASS",
                "session_date": SESSION,
                "authority": "IDX",
                "upstream_path": "TradingSummary/GetStockSummary",
                "field_semantics": "IDX_OFFICIAL_OPENPRICE",
                "transport": "DIRECT_IDX_HTTPS",
                "transport_policy": "DIRECT_IDX_THEN_ZAPI_RAW_V1",
                "fallback_policy": "NONE",
                "execution_grade": True,
                "raw_artifact_path": raw.name,
                "raw_artifact_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                "normalized_artifact_path": normalized.name,
                "normalized_artifact_sha256": hashlib.sha256(normalized.read_bytes()).hexdigest(),
                "captured_at_utc": "2026-08-26T09:03:00+07:00",
            },
        )

    if decision_status != "LEGITIMATE_NOOP":
        _write(
            e2e / "executions" / f"{SESSION}.json",
            _safe_guarded(
                "PASS",
                execution_session_date=SESSION,
                prepared_at_utc="2026-08-26T18:02:00+07:00",
                executed_at_utc="2026-08-26T18:03:00+07:00",
                execution_id="exec-1",
                duplicate_count=0,
                retroactive_fill=False,
            ),
        )
    _write(
        ca.parent / "unused.json",
        {},
    )
    _write(
        e2e / "dividend_acquisition_v1" / "journals" / f"{SESSION}.json",
        _safe_guarded("PASS", evidence_at_utc="2026-08-26T18:00:00+07:00"),
    )
    _write(
        e2e / "forward_execution_v1_1" / "state_snapshots" / f"{SESSION}.json",
        _safe_guarded("PASS", execution_session_date=SESSION, continuity_valid=True, evidence_at_utc="2026-08-26T18:04:00+07:00"),
    )
    return {
        "forward": forward,
        "e2e": e2e,
        "calendar": calendar,
        "runtime": runtime,
        "stockbit": stockbit,
        "ca": ca,
        "scheduler": scheduler,
    }


def _audit(paths: dict[str, Path], **kwargs: object) -> dict[str, object]:
    return audit_session(
        SESSION,
        forward_monitoring_root=paths["forward"],
        e2e_runtime_root=paths["e2e"],
        calendar_metadata=paths["calendar"],
        runtime_identity=paths["runtime"],
        stockbit_capture=paths["stockbit"],
        ca_dividend=paths["ca"],
        scheduler_metadata=paths["scheduler"],
        reported_at_utc="2026-08-26T20:00:00+07:00",
        **kwargs,
    )


def test_complete_genuine_style_session_is_healthy(tmp_path: Path):
    report = _audit(_fixture(tmp_path))
    assert report["overall_status"] == "SESSION_HEALTHY"
    assert all(stage["status"] == PASS for stage in report["stages"])


def test_holiday_is_non_trading_and_does_not_require_downstream_artifacts(tmp_path: Path):
    calendar = tmp_path / "calendar.json"
    _write(calendar, {"status": "PASS", "session_date": SESSION, "is_trading_session": False, "classification": "HOLIDAY"})
    report = audit_session(SESSION, calendar_metadata=calendar, reported_at_utc="2026-08-26T20:00:00+07:00")
    assert report["overall_status"] == "NON_TRADING_SESSION"
    assert all(stage["status"] == NOT_APPLICABLE for stage in report["stages"][1:])


def test_missing_official_open_is_pending_not_healthy(tmp_path: Path):
    report = _audit(_fixture(tmp_path, include_open=False))
    by_name = {stage["stage"]: stage for stage in report["stages"]}
    assert report["overall_status"] == "SESSION_PENDING_EXPECTED"
    assert by_name["official_open_evidence"]["status"] == PENDING_EXPECTED
    assert by_name["paper_execution"]["status"] == PENDING_EXPECTED


def test_tampered_open_manifest_is_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path)
    manifest = paths["e2e"] / "official_open" / SESSION / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["authority"] = "OTHER"
    _write(manifest, payload)
    report = _audit(paths)
    stage = next(stage for stage in report["stages"] if stage["stage"] == "official_open_evidence")
    assert stage["status"] == PROVENANCE_INVALID
    assert report["overall_status"] == "SESSION_PROVENANCE_INVALID"


def test_open_declared_raw_hash_tamper_is_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path)
    raw = paths["e2e"] / "official_open" / SESSION / "raw.bin"
    raw.write_bytes(b"tampered official IDX raw bytes")
    report = _audit(paths)
    stage = next(stage for stage in report["stages"] if stage["stage"] == "official_open_evidence")
    assert stage["status"] == PROVENANCE_INVALID
    assert "DECLARED_ARTIFACT_SHA256_MISMATCH:raw_artifact_path" in stage["causal_notes"]


def test_firsttrade_and_duplicate_open_evidence_are_rejected(tmp_path: Path):
    paths = _fixture(tmp_path)
    manifest = paths["e2e"] / "official_open" / SESSION / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["execution_field"] = "FirstTrade"
    payload["duplicate_key_count"] = 1
    _write(manifest, payload)
    report = _audit(paths)
    stage = next(stage for stage in report["stages"] if stage["stage"] == "official_open_evidence")
    assert stage["status"] == PROVENANCE_INVALID
    assert "FORBIDDEN_OPEN_FIELD:FirstTrade" in stage["causal_notes"]
    assert "DUPLICATE_OFFICIAL_OPEN_KEYS:duplicate_key_count" in stage["causal_notes"]


def test_legitimate_decision_zero_trade_is_explicit_noop(tmp_path: Path):
    paths = _fixture(tmp_path, decision_status="LEGITIMATE_NOOP")
    report = _audit(paths)
    by_name = {stage["stage"]: stage for stage in report["stages"]}
    assert report["overall_status"] == "SESSION_HEALTHY_LEGITIMATE_NOOP"
    assert by_name["decision_v2"]["status"] == LEGITIMATE_NOOP
    assert by_name["prepared_order"]["status"] == NOT_APPLICABLE
    assert by_name["paper_execution"]["status"] == NOT_APPLICABLE


def test_prepared_order_without_open_is_pending(tmp_path: Path):
    report = _audit(_fixture(tmp_path, include_open=False))
    assert next(stage for stage in report["stages"] if stage["stage"] == "prepared_order")["status"] == PASS
    assert report["overall_status"] == "SESSION_PENDING_EXPECTED"


@pytest.mark.parametrize(
    "mutator,expected_stage,expected_status",
    [
        (lambda p: p.update({"session_date": "2026-08-25"}), "decision_v2", PROVENANCE_INVALID),
        (lambda p: p.update({"stale_artifact": True}), "execution", PROVENANCE_INVALID),
        (lambda p: p.update({"duplicate_count": 2}), "execution", IMPLEMENTATION_DEFECT),
        (lambda p: p.update({"continuity_valid": False}), "paperstate", PROVENANCE_INVALID),
    ],
)
def test_identity_stale_duplicate_and_continuity_fail_closed(tmp_path: Path, mutator, expected_stage: str, expected_status: str):
    paths = _fixture(tmp_path)
    path = {
        "decision_v2": paths["e2e"] / "state" / "decisions" / f"{SESSION}.json",
        "execution": paths["e2e"] / "executions" / f"{SESSION}.json",
        "paperstate": paths["e2e"] / "forward_execution_v1_1" / "state_snapshots" / f"{SESSION}.json",
    }[expected_stage]
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutator(payload)
    _write(path, payload)
    report = _audit(paths)
    stage = next(stage for stage in report["stages"] if stage["stage"] == {"paperstate": "paperstate_continuity", "execution": "paper_execution", "decision_v2": "decision_v2"}[expected_stage])
    assert stage["status"] == expected_status


def test_execution_before_prepared_is_implementation_defect(tmp_path: Path):
    paths = _fixture(tmp_path)
    execution = paths["e2e"] / "executions" / f"{SESSION}.json"
    payload = json.loads(execution.read_text(encoding="utf-8"))
    payload["executed_at_utc"] = "2026-08-26T18:01:00+07:00"
    _write(execution, payload)
    report = _audit(paths)
    stage = next(stage for stage in report["stages"] if stage["stage"] == "paper_execution")
    assert stage["status"] == IMPLEMENTATION_DEFECT
    assert "EXECUTION_BEFORE_PREPARED_ORDER" in stage["causal_notes"]


def test_protected_path_is_refused_without_read(tmp_path: Path):
    paths = _fixture(tmp_path)
    report = audit_session(
        SESSION,
        calendar_metadata=paths["calendar"],
        stockbit_capture=tmp_path / "protected_outcomes" / "stockbit.json",
        reported_at_utc="2026-08-26T20:00:00+07:00",
    )
    stage = next(stage for stage in report["stages"] if stage["stage"] == "stockbit_scheduled_capture")
    assert stage["status"] == PROVENANCE_INVALID
    assert "PROTECTED_METADATA_PATH_REFUSED" in stage["causal_notes"]


def test_runtime_identity_unavailable_and_mismatch_are_not_healthy(tmp_path: Path):
    paths = _fixture(tmp_path)
    report = audit_session(SESSION, calendar_metadata=paths["calendar"], reported_at_utc="2026-08-26T20:00:00+07:00")
    assert next(stage for stage in report["stages"] if stage["stage"] == "runtime_identity")["status"] == NOT_READ
    assert report["overall_status"] == "SESSION_PENDING_EXPECTED"
    runtime = json.loads(paths["runtime"].read_text(encoding="utf-8"))
    runtime["runtime_sha256"] = "wrong"
    _write(paths["runtime"], runtime)
    report = _audit(paths)
    assert next(stage for stage in report["stages"] if stage["stage"] == "runtime_identity")["status"] == PROVENANCE_INVALID


def test_scheduler_wrong_runner_is_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path)
    scheduler = json.loads(paths["scheduler"].read_text(encoding="utf-8"))
    scheduler["runner"] = "wrong_runner.ps1"
    _write(paths["scheduler"], scheduler)
    report = _audit(paths)
    assert next(stage for stage in report["stages"] if stage["stage"] == "scheduler_task")["status"] == PROVENANCE_INVALID


def test_outcome_blind_claim_without_guard_is_rejected(tmp_path: Path):
    paths = _fixture(tmp_path)
    eod = paths["forward"] / "sessions" / SESSION / "manifest.json"
    payload = json.loads(eod.read_text(encoding="utf-8"))
    payload.pop("forward_outcomes_accessed")
    _write(eod, payload)
    report = _audit(paths)
    stage = next(stage for stage in report["stages"] if stage["stage"] == "canonical_eod_capture")
    assert stage["status"] == PROVENANCE_INVALID


def test_stats_are_operational_only_and_deterministic(tmp_path: Path):
    paths = _fixture(tmp_path)
    report = _audit(paths)
    summary = summarize_ledgers([report, report])
    assert summary["healthy_count"] == 2
    assert summary["latest_healthy_session"] == SESSION
    assert "official_open_transport_distribution" in summary
    assert "returns" not in json.dumps(summary).lower()
    first, first_sha = write_json(tmp_path / "ledger.json", report)
    second, second_sha = write_json(tmp_path / "ledger-2.json", report)
    assert first_sha == second_sha
    assert first.read_bytes() == second.read_bytes()
