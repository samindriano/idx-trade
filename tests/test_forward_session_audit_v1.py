from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from idx_trade.forward_session_audit_v1 import (
    FAIL_CLOSED_EXTERNAL,
    IMPLEMENTATION_DEFECT,
    LEGITIMATE_NOOP,
    NOT_APPLICABLE,
    PASS,
    PENDING_EXPECTED,
    PROVENANCE_INVALID,
    audit_session,
    summarize_ledgers,
    write_json,
)
from idx_trade.official_trading_schedule_v1 import derive_planned_sessions


DECISION = "2026-08-26"
EXECUTION = "2026-08-27"


def _write(path: Path, payload: dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    encoded = body.encode("utf-8")
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()


def _canonical_hash(payload: dict[str, object]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    return hashlib.sha256(body.encode()).hexdigest()


def _guarded(status: str = "PASS", *, session_date: str | None = None, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "guards": {
            "protected_outcome_accessed": False,
            "realized_forward_outcome_loaded": False,
        },
    }
    if session_date is not None:
        payload["session_date"] = session_date
    payload.update(extra)
    return payload


def _set_payload_hash(payload: dict[str, object]) -> dict[str, object]:
    body = dict(payload)
    body.pop("payload_sha256", None)
    body["payload_sha256"] = _canonical_hash(body)
    return body


def _fixture(
    tmp_path: Path,
    *,
    include_open: bool = True,
    include_execution: bool = True,
    decision_status: str = "PASS",
    prepared_execution: str = EXECUTION,
    prepared_decision: str = DECISION,
    decision_time: str = "2026-08-26T18:01:00+07:00",
    prepared_time: str = "2026-08-26T18:02:00+07:00",
    open_time: str = "2026-08-27T09:03:00+07:00",
    execution_time: str = "2026-08-27T09:05:00+07:00",
    calendar_status: str = "PASS",
    calendar_trading: bool = True,
    scheduler_runner: str = "scripts/run_official_open_capture.ps1",
    scheduler_module: str = "idx_trade.official_open_capture_runtime_v2",
) -> dict[str, Path]:
    forward = tmp_path / "forward"
    e2e = tmp_path / "e2e"
    calendar = tmp_path / "calendar.json"
    runtime = tmp_path / "runtime.json"
    stockbit = tmp_path / "stockbit.json"
    ca = tmp_path / "ca.json"
    scheduler = tmp_path / "scheduler.json"
    schedule_source = tmp_path / "schedule-source.json"
    schedule_attestation = tmp_path / "schedule-attestation.json"

    _write(
        calendar,
        _guarded(
            calendar_status,
            session_date=EXECUTION,
            is_trading_session=calendar_trading,
            classification="REGULAR" if calendar_trading else "HOLIDAY",
        ),
    )
    _write(
        runtime,
        _guarded(
            session_date=EXECUTION,
            runtime_sha256="abc",
            expected_runtime_sha256="abc",
            evidence_at_utc="2026-08-27T08:55:00+07:00",
        ),
    )
    _write(stockbit, _guarded(session_date=EXECUTION, captured_at_utc="2026-08-27T09:10:00+07:00"))
    _write(ca, _guarded(session_date=EXECUTION, execution_session_date=EXECUTION, decision_session_date=DECISION, evidence_at_utc="2026-08-27T18:00:00+07:00"))
    _write(
        scheduler,
        _guarded(
            session_date=EXECUTION,
            execution_session_date=EXECUTION,
            task_name="IDXTrade-E2E-OfficialOpen",
            runner=scheduler_runner,
            module=scheduler_module,
            triggers=["09:02", "09:07", "09:12", "09:17", "09:22", "AtLogOn"],
            start_when_available=True,
            multiple_instances="IgnoreNew",
            network_required=True,
        ),
    )

    schedule_source.write_bytes(b"official schedule source fixture")
    schedule_sessions = list(derive_planned_sessions(
        coverage_start="2026-08-25",
        coverage_end="2026-08-28",
        holiday_dates=[],
    ))
    schedule_payload: dict[str, object] = {
        "schema_version": "idx_official_trading_schedule_v1",
        "authority": "IDX",
        "semantics": "PLANNED_OFFICIAL_TRADING_SCHEDULE",
        "derivation": "WEEKDAYS_MINUS_PUBLISHED_BURSA_HOLIDAYS",
        "source_reference": "fixture-official-schedule",
        "source_document_path": str(schedule_source.resolve()),
        "source_document_sha256": hashlib.sha256(schedule_source.read_bytes()).hexdigest(),
        "coverage_start": "2026-08-25",
        "coverage_end": "2026-08-28",
        "holiday_dates": [],
        "session_dates": schedule_sessions,
    }
    _write(schedule_attestation, _set_payload_hash(schedule_payload))

    eod_dir = forward / "sessions" / DECISION
    snapshot = eod_dir / "model_input.bin"
    evidence = eod_dir / "session_evidence.bin"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_bytes(b"synthetic model input bytes")
    evidence.write_bytes(b"synthetic evidence bytes")
    _write(
        eod_dir / "manifest.json",
        _guarded(
            "DATA_READY",
            session_date=DECISION,
            snapshot_path=snapshot.name,
            snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            evidence_path=evidence.name,
            evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
        ),
    )

    score_dir = forward / "model_runs" / DECISION / "v4_x1_clean_geometry3_prospective_v1"
    score_artifact = score_dir / "score.bin"
    score_artifact.parent.mkdir(parents=True, exist_ok=True)
    score_artifact.write_bytes(b"synthetic score bytes")
    score_manifest = score_dir / "manifest.json"
    score_sha = _write(
        score_manifest,
        _guarded(
            "DONE",
            session_date=DECISION,
            score_artifact_path=score_artifact.name,
            score_artifact_sha256=hashlib.sha256(score_artifact.read_bytes()).hexdigest(),
        ),
    )

    # This state/decisions file is intentionally not the Decision authority;
    # the auditor must use the embedded prepared decision plan instead.
    _write(e2e / "state" / "decisions" / f"{DECISION}.json", {"not_decision_authority": True})

    raw = e2e / "official_open" / EXECUTION / "raw.bin"
    normalized = e2e / "official_open" / EXECUTION / "normalized.bin"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(b"synthetic official IDX raw bytes")
    normalized.write_bytes(b"synthetic official IDX normalized bytes")
    if include_open:
        _write(
            raw.parent / "manifest.json",
            {
                "schema_version": "idx_official_open_evidence_v1_1",
                "session_date": EXECUTION,
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
                "capture_timestamp_jakarta": open_time,
                "duplicate_key_count": 0,
            },
        )

    prepared_path = e2e / "prepared" / f"{prepared_decision}.json"
    empty_plan = decision_status == "LEGITIMATE_NOOP"
    decision_plan: dict[str, object] = {
        "decision_session_date": prepared_decision,
        "current_shadow_positions": [],
        "target_positions": [] if empty_plan else ["BBCA"],
        "buy_intents": [] if empty_plan else [{"side": "BUY", "ticker": "BBCA", "rank_consensus": 1, "reason": "fixture", "replacement_peer": None}],
        "sell_intents": [],
        "hold_tickers": [],
        "incumbent_observations": [],
        "challenger_observations": [],
        "unfilled_slots": 0,
        "capacity_state": "AVAILABLE",
        "rule_id": "fixture",
        "bootstrap": False,
    }
    execution_plan: dict[str, object] = {
        "decision_session_date": prepared_decision,
        "execution_session_date": prepared_execution,
        "state_hash": "state-hash",
        "eod_nav_idr": 1000000.0,
        "projected_cash_for_sizing_idr": 1000000.0,
        "sizing_plan": {"decision_session_date": prepared_decision, "nav_idr": 1000000.0, "available_cash_idr": 1000000.0, "target_weight_per_name": 1.0, "max_entry_weight_per_name": 1.0, "entries": [] if empty_plan else [{"ticker": "BBCA", "shares": 1}], "total_sized_notional": 0.0 if empty_plan else 1000.0, "residual_cash_after_sizing_reference": 1000000.0, "rule_id": "fixture"},
        "sells": [],
        "effective_buy_intents": [] if empty_plan else [{"side": "BUY", "ticker": "BBCA", "rank_consensus": 1, "reason": "fixture", "replacement_peer": None}],
        "target_positions": [] if empty_plan else ["BBCA"],
        "regular_market_values_t": {"BBCA": 1000.0},
        "eod_ohlcv_sha256": "0" * 64,
        "eod_model_input_sha256": "1" * 64,
        "official_calendar_sha256": hashlib.sha256(calendar.read_bytes()).hexdigest(),
        "rule_id": "fixture",
    }
    prepared_payload: dict[str, object] = {
        "schema_version": "idx_trade_e2e_paper_prepared_execution_v1",
        "status": "PREPARED_EXECUTION",
        "decision_session_date": prepared_decision,
        "execution_session_date": prepared_execution,
        "bootstrap": False,
        "required_tickers": ["BBCA"],
        "state": {"snapshot_path": str((e2e / "forward_execution_v1_1" / "state_snapshots" / f"{EXECUTION}.json").resolve()), "snapshot_sha256": "snapshot", "state_sha256": "state"},
        "decision_plan": decision_plan,
        "decision_plan_sha256": _canonical_hash(decision_plan),
        "execution_plan": execution_plan,
        "execution_plan_sha256": _canonical_hash(execution_plan),
        "outcome_access": False,
        "current_score": {
            "manifest_path": str(score_manifest.resolve()),
            "manifest_sha256": score_sha,
            "session_date": prepared_decision,
        },
        "eod_inputs": {
            "calendar": {"path": str(calendar.resolve()), "sha256": hashlib.sha256(calendar.read_bytes()).hexdigest()},
            "ohlcv": {"path": str(evidence.resolve()), "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()},
            "model_input": {"path": str(snapshot.resolve()), "sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest()},
        },
    }
    _write(prepared_path, _set_payload_hash(prepared_payload))
    binding_payload: dict[str, object] = {
        "schema_version": "idx_trade_e2e_prepared_schedule_binding_v1",
        "decision_session_date": prepared_decision,
        "execution_session_date": prepared_execution,
        "prepared_path": str(prepared_path.resolve()),
        "prepared_sha256": hashlib.sha256(prepared_path.read_bytes()).hexdigest(),
        "observed_calendar_path": str(calendar.resolve()),
        "observed_calendar_sha256": hashlib.sha256(calendar.read_bytes()).hexdigest(),
        "execution_schedule_attestation_path": str(schedule_attestation.resolve()),
        "execution_schedule_attestation_sha256": hashlib.sha256(schedule_attestation.read_bytes()).hexdigest(),
        "execution_schedule_source_path": str(schedule_source.resolve()),
        "execution_schedule_source_sha256": hashlib.sha256(schedule_source.read_bytes()).hexdigest(),
        "execution_schedule_source_reference": "fixture-official-schedule",
        "outcome_access": False,
    }
    binding_path = e2e / "prepared_schedule" / f"{prepared_decision}.json"
    _write(binding_path, _set_payload_hash(binding_payload))

    execution_path = e2e / "executions" / f"{EXECUTION}.json"
    if include_execution:
        execution_payload = {
            "schema_version": "idx_trade_e2e_paper_execution_v1",
            "status": "EXECUTION_COMPLETE",
            "session_date": EXECUTION,
            "decision_session_date": DECISION,
            "execution_session_date": EXECUTION,
            "prepared_path": str(prepared_path.resolve()),
            "prepared_sha256": hashlib.sha256(prepared_path.read_bytes()).hexdigest(),
            "open_manifest_path": str((raw.parent / "manifest.json").resolve()) if include_open else None,
            "open_manifest_sha256": hashlib.sha256((raw.parent / "manifest.json").read_bytes()).hexdigest() if include_open else None,
            "open_normalized_path": str(normalized.resolve()),
            "open_normalized_sha256": hashlib.sha256(normalized.read_bytes()).hexdigest(),
            "runtime_snapshot_path": str((e2e / "forward_execution_v1_1" / "state_snapshots" / f"{EXECUTION}.json").resolve()),
            "runtime_snapshot_sha256": "runtime-placeholder",
            "duplicate_count": 0,
            "retroactive_fill": False,
            "fills": [], "gross_turnover_idr": 0.0, "stamp_duty_idr": 0.0,
            "outcome_access": False,
        }
        _write(execution_path, _set_payload_hash(execution_payload))

    _write(
        e2e / "dividend_acquisition_v1" / "journals" / f"{EXECUTION}.json",
        _guarded(session_date=EXECUTION, execution_session_date=EXECUTION, decision_session_date=DECISION, evidence_at_utc="2026-08-27T18:00:00+07:00"),
    )
    snapshot_payload: dict[str, object] = {
        "schema_version": "idx_trade_forward_dividend_runtime_state_v1_1",
        "session_date": EXECUTION,
        "state": {"base_paper_state": {}, "dividend_ledger": {}},
        "certified_dividend_registry": [],
        "hashes": {"runtime_state_sha256": "runtime-state"},
        "previous_snapshot": None,
    }
    snapshot_payload["snapshot_payload_sha256"] = _canonical_hash(snapshot_payload)
    snapshot_path = e2e / "forward_execution_v1_1" / "state_snapshots" / f"{EXECUTION}.json"
    snapshot_sha = _write(snapshot_path, snapshot_payload)
    if include_execution:
        execution_payload = json.loads(execution_path.read_text(encoding="utf-8"))
        execution_payload["runtime_snapshot_sha256"] = snapshot_sha
        _write(execution_path, _set_payload_hash(execution_payload))
    return {
        "forward": forward,
        "e2e": e2e,
        "calendar": calendar,
        "runtime": runtime,
        "stockbit": stockbit,
        "ca": ca,
        "scheduler": scheduler,
        "prepared": prepared_path,
        "execution": execution_path,
        "binding": binding_path,
        "schedule_attestation": schedule_attestation,
    }


def _audit(paths: dict[str, Path], **kwargs: object) -> dict[str, object]:
    return audit_session(
        EXECUTION,
        forward_monitoring_root=paths["forward"],
        e2e_runtime_root=paths["e2e"],
        calendar_metadata=paths["calendar"],
        runtime_identity=paths["runtime"],
        stockbit_capture=paths["stockbit"],
        ca_dividend=paths["ca"],
        scheduler_metadata=paths["scheduler"],
        reported_at_utc="2026-08-27T20:00:00+07:00",
        **kwargs,
    )


def _by_name(report: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(stage["stage"]): stage for stage in report["stages"]}  # type: ignore[index]


def test_complete_t_to_t_plus_one_chain_is_healthy(tmp_path: Path):
    report = _audit(_fixture(tmp_path))
    assert report["overall_status"] == "SESSION_HEALTHY"
    assert report["decision_session_date"] == DECISION
    assert report["execution_session_date"] == EXECUTION
    assert all(stage["status"] == PASS for stage in report["stages"])


def test_valid_holiday_is_non_trading_only_after_calendar_pass(tmp_path: Path):
    calendar = tmp_path / "calendar.json"
    _write(calendar, _guarded(session_date=EXECUTION, is_trading_session=False, classification="HOLIDAY"))
    report = audit_session(EXECUTION, calendar_metadata=calendar, reported_at_utc="2026-08-27T20:00:00+07:00")
    assert report["overall_status"] == "NON_TRADING_SESSION"
    assert all(stage["status"] == NOT_APPLICABLE for stage in report["stages"][1:])


def test_invalid_calendar_cannot_become_holiday(tmp_path: Path):
    calendar = tmp_path / "calendar.json"
    _write(calendar, _guarded("FAIL_CLOSED_EXTERNAL", session_date=EXECUTION, is_trading_session=False))
    report = audit_session(EXECUTION, calendar_metadata=calendar, reported_at_utc="2026-08-27T20:00:00+07:00")
    assert report["overall_status"] != "NON_TRADING_SESSION"
    assert _by_name(report)["official_trading_calendar"]["status"] == FAIL_CLOSED_EXTERNAL


def test_missing_open_without_execution_is_pending(tmp_path: Path):
    paths = _fixture(tmp_path, include_open=False, include_execution=False)
    report = _audit(paths)
    stages = _by_name(report)
    assert report["overall_status"] == "SESSION_PENDING_EXPECTED"
    assert stages["official_open_evidence"]["status"] == PENDING_EXPECTED
    assert stages["paper_execution"]["status"] == PENDING_EXPECTED


def test_successful_execution_without_open_is_implementation_defect(tmp_path: Path):
    report = _audit(_fixture(tmp_path, include_open=False, include_execution=True))
    stages = _by_name(report)
    assert stages["paper_execution"]["status"] == IMPLEMENTATION_DEFECT
    assert "SUCCESSFUL_EXECUTION_WITHOUT_CERTIFIED_OPEN" in stages["paper_execution"]["causal_notes"]


def test_existing_execution_provenance_failure_is_never_downgraded(tmp_path: Path):
    paths = _fixture(tmp_path, include_open=False, include_execution=True)
    payload = json.loads(paths["execution"].read_text(encoding="utf-8"))
    payload["prepared_path"] = str((tmp_path / "wrong-prepared.json").resolve())
    _write(paths["execution"], _set_payload_hash(payload))
    assert _by_name(_audit(paths))["paper_execution"]["status"] == PROVENANCE_INVALID


def test_prepared_after_open_is_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path)
    payload = json.loads(paths["prepared"].read_text(encoding="utf-8"))
    payload["prepared_timestamp_utc"] = "2026-08-27T09:04:00+07:00"
    _write(paths["prepared"], _set_payload_hash(payload))
    binding = json.loads(paths["binding"].read_text(encoding="utf-8"))
    binding["prepared_sha256"] = hashlib.sha256(paths["prepared"].read_bytes()).hexdigest()
    _write(paths["binding"], _set_payload_hash(binding))
    execution = json.loads(paths["execution"].read_text(encoding="utf-8"))
    execution["prepared_sha256"] = hashlib.sha256(paths["prepared"].read_bytes()).hexdigest()
    _write(paths["execution"], _set_payload_hash(execution))
    report = _audit(paths)
    stage = _by_name(report)["paper_execution"]
    assert stage["status"] == PROVENANCE_INVALID
    assert "PREPARED_AFTER_OFFICIAL_OPEN" in stage["causal_notes"]


def test_open_after_execution_is_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path)
    manifest = paths["e2e"] / "official_open" / EXECUTION / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["capture_timestamp_jakarta"] = "2026-08-27T09:06:00+07:00"
    _write(manifest, payload)
    execution = json.loads(paths["execution"].read_text(encoding="utf-8"))
    execution["open_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    execution["execution_timestamp_utc"] = "2026-08-27T09:05:00+07:00"
    _write(paths["execution"], _set_payload_hash(execution))
    report = _audit(paths)
    stage = _by_name(report)["paper_execution"]
    assert stage["status"] == PROVENANCE_INVALID
    assert "OFFICIAL_OPEN_AFTER_EXECUTION" in stage["causal_notes"]


def test_execution_before_prepared_is_implementation_defect_when_other_chain_is_valid(tmp_path: Path):
    paths = _fixture(tmp_path)
    prepared = json.loads(paths["prepared"].read_text(encoding="utf-8"))
    prepared["prepared_timestamp_utc"] = "2026-08-26T18:02:00+07:00"
    _write(paths["prepared"], _set_payload_hash(prepared))
    binding = json.loads(paths["binding"].read_text(encoding="utf-8"))
    binding["prepared_sha256"] = hashlib.sha256(paths["prepared"].read_bytes()).hexdigest()
    _write(paths["binding"], _set_payload_hash(binding))
    payload = json.loads(paths["execution"].read_text(encoding="utf-8"))
    payload["prepared_sha256"] = hashlib.sha256(paths["prepared"].read_bytes()).hexdigest()
    payload["execution_timestamp_utc"] = "2026-08-26T18:01:00+07:00"
    _write(paths["execution"], _set_payload_hash(payload))
    report = _audit(paths)
    stage = _by_name(report)["paper_execution"]
    assert stage["status"] == IMPLEMENTATION_DEFECT
    assert "EXECUTION_BEFORE_PREPARED_ORDER" in stage["causal_notes"]


def test_wrong_prepared_parent_sha_is_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path)
    payload = json.loads(paths["execution"].read_text(encoding="utf-8"))
    payload["prepared_sha256"] = "0" * 64
    _write(paths["execution"], _set_payload_hash(payload))
    stage = _by_name(_audit(paths))["paper_execution"]
    assert stage["status"] == PROVENANCE_INVALID
    assert "DECLARED_ARTIFACT_SHA256_MISMATCH:prepared_path" in stage["causal_notes"]


def test_wrong_prepared_parent_path_is_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path)
    payload = json.loads(paths["execution"].read_text(encoding="utf-8"))
    payload["prepared_path"] = str((tmp_path / "wrong-prepared.json").resolve())
    _write(paths["execution"], _set_payload_hash(payload))
    stage = _by_name(_audit(paths))["paper_execution"]
    assert stage["status"] == PROVENANCE_INVALID
    assert "DECLARED_ARTIFACT_MISSING:prepared_path" in stage["causal_notes"]


def test_wrong_prepared_execution_session_is_explicitly_invalid(tmp_path: Path):
    paths = _fixture(tmp_path, prepared_execution="2026-08-28")
    report = _audit(paths, prepared_metadata=paths["prepared"])
    assert _by_name(report)["prepared_order"]["status"] == PROVENANCE_INVALID


def test_wrong_decision_parent_identity_is_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path)
    payload = json.loads(paths["prepared"].read_text(encoding="utf-8"))
    payload["decision_session_date"] = "2026-08-25"
    payload["decision_plan"]["decision_session_date"] = "2026-08-25"  # type: ignore[index]
    payload["current_score"]["session_date"] = "2026-08-25"  # type: ignore[index]
    _write(paths["prepared"], _set_payload_hash(payload))
    stage = _by_name(_audit(paths))["prepared_order"]
    assert stage["status"] == PROVENANCE_INVALID
    assert stage["causal_notes"]


def test_wrong_open_session_is_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path)
    manifest = paths["e2e"] / "official_open" / EXECUTION / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["session_date"] = DECISION
    _write(manifest, payload)
    assert _by_name(_audit(paths))["official_open_evidence"]["status"] == PROVENANCE_INVALID


def test_backdated_open_evidence_is_rejected(tmp_path: Path):
    paths = _fixture(tmp_path)
    manifest = paths["e2e"] / "official_open" / EXECUTION / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["backdated_fill"] = True
    _write(manifest, payload)
    stage = _by_name(_audit(paths))["official_open_evidence"]
    assert stage["status"] == PROVENANCE_INVALID
    assert "RETROACTIVE_OFFICIAL_OPEN_REJECTED" in stage["causal_notes"]


def test_unknown_status_is_not_pass(tmp_path: Path):
    paths = _fixture(tmp_path)
    payload = json.loads(paths["stockbit"].read_text(encoding="utf-8"))
    payload["status"] = "MAYBE_OK"
    _write(paths["stockbit"], payload)
    assert _by_name(_audit(paths))["stockbit_scheduled_capture"]["status"] == PROVENANCE_INVALID


def test_scheduler_requires_actual_action_and_runtime_module(tmp_path: Path):
    paths = _fixture(tmp_path, scheduler_runner="scripts/run_official_open_capture_v2.ps1")
    stage = _by_name(_audit(paths))["scheduler_task"]
    assert stage["status"] == PROVENANCE_INVALID
    assert "SCHEDULER_RUNNER_WRONG_VERSION" in stage["causal_notes"]


def test_scheduler_accepts_actual_action_and_module_identity(tmp_path: Path):
    assert _by_name(_audit(_fixture(tmp_path)))["scheduler_task"]["status"] == PASS


def test_legitimate_zero_trade_is_explicit_noop(tmp_path: Path):
    report = _audit(_fixture(tmp_path, decision_status="LEGITIMATE_NOOP", include_execution=False))
    stages = _by_name(report)
    assert report["overall_status"] == "SESSION_HEALTHY_LEGITIMATE_NOOP"
    assert stages["decision_v2"]["status"] == LEGITIMATE_NOOP
    assert stages["prepared_order"]["status"] == PASS
    assert stages["paper_execution"]["status"] == NOT_APPLICABLE
    assert stages["forward_evidence_health"]["status"] == NOT_APPLICABLE


def test_duplicate_execution_is_implementation_defect(tmp_path: Path):
    paths = _fixture(tmp_path)
    payload = json.loads(paths["execution"].read_text(encoding="utf-8"))
    payload["duplicate_count"] = 2
    _write(paths["execution"], _set_payload_hash(payload))
    assert _by_name(_audit(paths))["paper_execution"]["status"] == IMPLEMENTATION_DEFECT


def test_state_continuity_break_is_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path)
    path = paths["e2e"] / "forward_execution_v1_1" / "state_snapshots" / f"{EXECUTION}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["continuity_valid"] = False
    _write(path, payload)
    assert _by_name(_audit(paths))["paperstate_continuity"]["status"] == PROVENANCE_INVALID


def test_guard_missing_from_blind_manifest_is_rejected(tmp_path: Path):
    paths = _fixture(tmp_path)
    path = paths["forward"] / "sessions" / DECISION / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("forward_outcomes_accessed")
    _write(path, payload)
    assert _by_name(_audit(paths))["canonical_eod_capture"]["status"] == PROVENANCE_INVALID


def test_protected_path_is_refused_without_read(tmp_path: Path):
    paths = _fixture(tmp_path)
    report = audit_session(
        EXECUTION,
        calendar_metadata=paths["calendar"],
        stockbit_capture=tmp_path / "protected_outcomes" / "stockbit.json",
        reported_at_utc="2026-08-27T20:00:00+07:00",
    )
    stage = _by_name(report)["stockbit_scheduled_capture"]
    assert stage["status"] == PROVENANCE_INVALID
    assert "PROTECTED_METADATA_PATH_REFUSED" in stage["causal_notes"]


def test_summary_tracks_nontrading_and_resets_stockbit_failure_streak():
    def ledger(session: str, overall: str, stockbit_status: str) -> dict[str, object]:
        return {
            "session_date": session,
            "execution_session_date": session,
            "overall_status": overall,
            "stages": [
                {"stage": "stockbit_scheduled_capture", "status": stockbit_status, "observed": {}},
                {"stage": "paperstate_continuity", "status": PASS if overall != "NON_TRADING_SESSION" else NOT_APPLICABLE, "observed": {}},
            ],
        }

    summary = summarize_ledgers([
        ledger("2026-08-27", "SESSION_FAIL_CLOSED_EXTERNAL", "FAIL_CLOSED_EXTERNAL"),
        ledger("2026-08-28", "NON_TRADING_SESSION", NOT_APPLICABLE),
        ledger("2026-08-29", "SESSION_HEALTHY", PASS),
    ])
    assert summary["healthy_count"] == 1
    assert summary["non_trading_count"] == 1
    assert summary["latest_healthy_session"] == "2026-08-29"
    assert summary["consecutive_stockbit_provider_failures"] == 0
    assert summary["paperstate_continuity_status"] == PASS


def test_stats_are_operational_only_and_deterministic(tmp_path: Path):
    report = _audit(_fixture(tmp_path))
    summary = summarize_ledgers([report, report])
    assert summary["healthy_count"] == 2
    assert summary["latest_healthy_session"] == EXECUTION
    assert "returns" not in json.dumps(summary).lower()
    first, first_sha = write_json(tmp_path / "ledger.json", report)
    second, second_sha = write_json(tmp_path / "ledger-2.json", report)
    assert first_sha == second_sha
    assert first.read_bytes() == second.read_bytes()


def test_production_open_manifest_without_status_is_accepted(tmp_path: Path):
    paths = _fixture(tmp_path)
    manifest = json.loads((paths["e2e"] / "official_open" / EXECUTION / "manifest.json").read_text())
    assert "status" not in manifest
    assert _by_name(_audit(paths))["official_open_evidence"]["status"] == PASS


def test_unknown_status_on_statusless_canonical_open_is_not_accepted(tmp_path: Path):
    paths = _fixture(tmp_path)
    manifest = paths["e2e"] / "official_open" / EXECUTION / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["status"] = "MAYBE_OK"
    _write(manifest, payload)
    assert _by_name(_audit(paths))["official_open_evidence"]["status"] == PROVENANCE_INVALID


def test_production_runtime_snapshot_without_status_is_accepted(tmp_path: Path):
    paths = _fixture(tmp_path)
    snapshot = json.loads((paths["e2e"] / "forward_execution_v1_1" / "state_snapshots" / f"{EXECUTION}.json").read_text())
    assert "status" not in snapshot
    assert _by_name(_audit(paths))["paperstate_continuity"]["status"] == PASS


def test_state_decision_metadata_is_not_decision_authority(tmp_path: Path):
    paths = _fixture(tmp_path)
    assert json.loads((paths["e2e"] / "state" / "decisions" / f"{DECISION}.json").read_text())["not_decision_authority"] is True
    stage = _by_name(_audit(paths))["decision_v2"]
    assert stage["status"] == PASS
    assert stage["observed"]["decision_source"] == "prepared_execution_payload"


def test_canonical_prepared_and_execution_need_no_synthetic_timestamps(tmp_path: Path):
    paths = _fixture(tmp_path)
    prepared = json.loads(paths["prepared"].read_text())
    execution = json.loads(paths["execution"].read_text())
    assert "prepared_at_utc" not in prepared
    assert "executed_at_utc" not in execution
    assert _audit(paths)["overall_status"] == "SESSION_HEALTHY"


def test_exact_prepared_schedule_open_execution_hash_chain_passes(tmp_path: Path):
    paths = _fixture(tmp_path)
    report = _audit(paths)
    stages = _by_name(report)
    assert stages["prepared_order_schedule_binding"]["status"] == PASS
    assert stages["official_open_evidence"]["status"] == PASS
    assert stages["paper_execution"]["status"] == PASS
    assert stages["paper_execution"]["artifact_sha256"] == hashlib.sha256(paths["execution"].read_bytes()).hexdigest()


def test_wrong_next_planned_session_fails_closed(tmp_path: Path):
    paths = _fixture(tmp_path)
    binding = json.loads(paths["binding"].read_text())
    binding["execution_session_date"] = "2026-08-28"
    _write(paths["binding"], _set_payload_hash(binding))
    assert _by_name(_audit(paths))["prepared_order_schedule_binding"]["status"] == PROVENANCE_INVALID


def test_wrong_schedule_attestation_sha_fails_closed(tmp_path: Path):
    paths = _fixture(tmp_path)
    binding = json.loads(paths["binding"].read_text())
    binding["execution_schedule_attestation_sha256"] = "0" * 64
    _write(paths["binding"], _set_payload_hash(binding))
    assert _by_name(_audit(paths))["prepared_order_schedule_binding"]["status"] == PROVENANCE_INVALID


def test_pending_order_prevents_false_noop_resolution(tmp_path: Path):
    paths = _fixture(tmp_path, include_open=False, include_execution=False)
    prepared = json.loads(paths["prepared"].read_text())
    plan = dict(prepared["execution_plan"])
    plan["target_positions"] = []
    plan["effective_buy_intents"] = []
    plan["pending_orders"] = [{"ticker": "BBCA", "side": "BUY"}]
    plan["sizing_plan"] = dict(plan["sizing_plan"])
    plan["sizing_plan"]["entries"] = []
    prepared["execution_plan"] = plan
    prepared["execution_plan_sha256"] = _canonical_hash(plan)
    _write(paths["prepared"], _set_payload_hash(prepared))
    binding = json.loads(paths["binding"].read_text())
    binding["prepared_sha256"] = hashlib.sha256(paths["prepared"].read_bytes()).hexdigest()
    _write(paths["binding"], _set_payload_hash(binding))
    stages = _by_name(_audit(paths))
    assert stages["decision_v2"]["status"] == PASS
    assert stages["paper_execution"]["status"] == PENDING_EXPECTED


def test_missed_execution_is_legitimate_continuity_not_success(tmp_path: Path):
    paths = _fixture(tmp_path, include_open=False, include_execution=False)
    snapshot = paths["e2e"] / "forward_execution_v1_1" / "state_snapshots" / f"{EXECUTION}.json"
    snapshot_sha = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    binding_sha = hashlib.sha256(paths["binding"].read_bytes()).hexdigest()
    missed = {
        "schema_version": "idx_trade_e2e_paper_missed_execution_v1",
        "status": "MISSED_EXECUTION_NO_CERTIFIED_OPEN",
        "decision_session_date": DECISION,
        "execution_session_date": EXECUTION,
        "reason": "NO_CERTIFIED_OFFICIAL_OPEN",
        "prepared_path": str(paths["prepared"].resolve()),
        "prepared_sha256": hashlib.sha256(paths["prepared"].read_bytes()).hexdigest(),
        "schedule_binding_path": str(paths["binding"].resolve()),
        "schedule_binding_sha256": binding_sha,
        "prior_runtime_snapshot_path": str(snapshot.resolve()),
        "prior_runtime_snapshot_sha256": snapshot_sha,
        "runtime_snapshot_path": str(snapshot.resolve()),
        "runtime_snapshot_sha256": snapshot_sha,
        "open_manifest_present": False,
        "fills": 0,
        "gross_turnover_idr": 0.0,
        "costs_idr": 0.0,
        "no_retroactive_execution": True,
        "outcome_access": False,
    }
    missed_path = paths["e2e"] / "missed_executions" / f"{EXECUTION}.json"
    _write(missed_path, _set_payload_hash(missed))
    report = _audit(paths)
    stages = _by_name(report)
    assert stages["paper_execution"]["status"] == LEGITIMATE_NOOP
    assert report["overall_status"] == "SESSION_MISSED_EXECUTION_NO_CERTIFIED_OPEN"


def test_successful_execution_requires_exact_open_and_prepared_parents(tmp_path: Path):
    paths = _fixture(tmp_path)
    execution = json.loads(paths["execution"].read_text())
    assert execution["prepared_sha256"] == hashlib.sha256(paths["prepared"].read_bytes()).hexdigest()
    assert execution["open_manifest_sha256"] == hashlib.sha256((paths["e2e"] / "official_open" / EXECUTION / "manifest.json").read_bytes()).hexdigest()
    assert _by_name(_audit(paths))["paper_execution"]["status"] == PASS


def test_implementation_defect_precedes_provenance_invalid(tmp_path: Path):
    paths = _fixture(tmp_path, include_open=False)
    execution = json.loads(paths["execution"].read_text())
    execution["duplicate_count"] = 2
    _write(paths["execution"], _set_payload_hash(execution))
    report = _audit(paths)
    assert _by_name(report)["paper_execution"]["status"] == IMPLEMENTATION_DEFECT
    assert report["overall_status"] == "SESSION_IMPLEMENTATION_DEFECT"


def test_production_shape_offline_smoke_is_healthy(tmp_path: Path):
    report = _audit(_fixture(tmp_path))
    assert report["overall_status"] == "SESSION_HEALTHY"
    assert report["guards"]["protected_outcomes_accessed"] is False


@pytest.mark.parametrize("status", ["FAIL_CLOSED_EXTERNAL", "IMPLEMENTATION_DEFECT", "MYSTERY_STATUS"])
def test_non_success_statuses_fail_closed(tmp_path: Path, status: str):
    paths = _fixture(tmp_path)
    payload = json.loads(paths["stockbit"].read_text(encoding="utf-8"))
    payload["status"] = status
    _write(paths["stockbit"], payload)
    stage = _by_name(_audit(paths))["stockbit_scheduled_capture"]
    expected = {
        "FAIL_CLOSED_EXTERNAL": FAIL_CLOSED_EXTERNAL,
        "IMPLEMENTATION_DEFECT": IMPLEMENTATION_DEFECT,
        "MYSTERY_STATUS": PROVENANCE_INVALID,
    }[status]
    assert stage["status"] == expected
