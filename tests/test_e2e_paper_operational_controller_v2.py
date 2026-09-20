from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from idx_trade import e2e_paper_operational_controller_v1 as v1
from idx_trade import e2e_paper_operational_controller_v2 as v2
from idx_trade.e2e_operational_guard_v1 import DeploymentAttestation, JAKARTA


def _config(tmp_path: Path) -> v2.OperationalControllerConfigV2:
    base = v1.OperationalControllerConfig(
        runtime_root=tmp_path / "runtime",
        forward_runtime_root=tmp_path / "forward",
        calendar_path=tmp_path / "calendar.csv",
        official_open_root=tmp_path / "open",
        repo_root=tmp_path / "repo",
        expected_branch="integration/test",
        expected_commit="abc123",
    )
    return v2.OperationalControllerConfigV2(
        base=base,
        execution_schedule_attestation_path=tmp_path / "schedule.json",
        execution_schedule_attestation_sha256="a" * 64,
    )


@pytest.mark.parametrize(
    ("phase", "side_effect"),
    (
        ("PREOPEN", "CA_CAPTURE"),
        ("PREOPEN", "PHASE_ATTESTATION"),
        ("PREOPEN", "CHILD_EXECUTION"),
        ("POST_EOD", "BOOTSTRAP_T0_WRITE"),
        ("POST_EOD", "CA_CAPTURE"),
        ("POST_EOD", "PHASE_ATTESTATION"),
        ("POST_EOD", "CHILD_EXECUTION"),
        ("POST_EOD", "MISSED_EXECUTION_WRITE"),
    ),
)
def test_dual_calendar_controller_preserves_recovery_boundary(
    tmp_path: Path,
    monkeypatch,
    phase: str,
    side_effect: str,
) -> None:
    config = _config(tmp_path)
    status = {
        "controller_status": "RUNNING",
        "controller_contract": "DUAL_CALENDAR_V1",
        "started_at_jakarta": "2026-08-24T18:00:00+07:00",
        "provider_calls": False,
        "outcome_access": False,
    }
    v1._persist_running_boundary(
        config,
        status,
        phase=phase,
        side_effect=side_effect,
    )
    monkeypatch.setattr(
        v2,
        "attest_deployment",
        lambda *args, **kwargs: DeploymentAttestation(
            config.repo_root,
            "integration/test",
            "abc123",
            "integration/test",
            "abc123",
            True,
        ),
    )
    monkeypatch.setattr(v2, "exclusive_run_lock", lambda path: nullcontext())

    recovered = v2.run_operational_cycle_v2(
        config,
        now=v2.datetime(2026, 8, 24, 18, 1, tzinfo=JAKARTA),
    )

    assert recovered["controller_status"] == "RECOVERY_REQUIRED"
    assert recovered["controller_contract"] == "DUAL_CALENDAR_V1"
    assert recovered["interrupted_phase"] == phase
    assert recovered["interrupted_side_effect"] == side_effect
    assert recovered["provider_calls"] is False
    assert recovered["outcome_access"] is False


def test_dual_calendar_missed_execution_uses_bound_prepared_parent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = _config(tmp_path)
    prepared_path = config.runtime_root / "prepared" / "2026-08-24.json"
    prepared_path.parent.mkdir(parents=True)
    prepared_payload = {
        "schema_version": "idx_trade_e2e_paper_prepared_execution_v1",
        "status": "PREPARED_EXECUTION",
        "decision_session_date": "2026-08-24",
        "execution_session_date": "2026-08-24",
        "bootstrap": True,
        "required_tickers": ["BBCA"],
        "state": {},
        "current_score": {},
        "previous_score": None,
        "previous_execution": None,
        "decision_plan": {},
        "decision_plan_sha256": "",
        "execution_plan": {},
        "execution_plan_sha256": "",
        "eod_inputs": {"calendar": {"path": str(tmp_path / "calendar.csv")}},
        "ca_reconciliation": {},
        "ca_timing_matrix": {},
        "decision_identity_binding": None,
        "runtime_lineage": {},
        "outcome_access": False,
        "payload_sha256": "",
    }
    prepared_path.write_text(json.dumps(prepared_payload), encoding="utf-8")

    @dataclass(frozen=True)
    class Missed:
        decision_session_date: str = "2026-08-24"
        execution_session_date: str = "2026-08-25"
        path: Path = tmp_path / "missed.json"
        file_sha256: str = "1" * 64
        runtime_snapshot_path: Path = tmp_path / "snapshot.json"
        runtime_snapshot_sha256: str = "2" * 64

    schedule = SimpleNamespace(
        coverage_start="2026-08-24",
        coverage_end="2026-08-28",
        session_dates=("2026-08-24", "2026-08-25", "2026-08-26"),
        attestation_path=config.execution_schedule_attestation_path,
        attestation_sha256=config.execution_schedule_attestation_sha256,
        source_reference="TEST_SCHEDULE",
    )
    monkeypatch.setattr(v2, "attest_deployment", lambda *args, **kwargs: SimpleNamespace(
        repo_root=config.repo_root,
        branch=config.expected_branch,
        head=config.expected_commit,
        expected_commit=config.expected_commit,
        clean=True,
    ))
    monkeypatch.setattr(v2, "exclusive_run_lock", lambda path: nullcontext())
    monkeypatch.setattr(v2, "load_verified_official_trading_schedule", lambda *args, **kwargs: schedule)
    monkeypatch.setattr(v2, "_verified_prepared_for_session", lambda *args, **kwargs: ([prepared_path], []))
    monkeypatch.setattr(v1, "_pipeline_pointer", lambda config: {"eod": {"status": "NO_MISSING_SESSION"}})
    monkeypatch.setattr(
        v1,
        "_verify_score_pointer",
        lambda *args, **kwargs: {
            "status": "V4_X1_SCORE_ALREADY_DONE_VERIFIED",
            "session_date": "2026-08-24",
        },
    )
    monkeypatch.setattr(v1, "_config_missing", lambda config: None)
    monkeypatch.setattr(v1, "_reconcile_prepared_ca", lambda *args, **kwargs: object())
    seen: dict[str, object] = {}

    def fake_missed(*args, **kwargs):
        seen.update(kwargs)
        return Missed()

    monkeypatch.setattr(v2, "advance_missed_execution_no_certified_open_with_schedule", fake_missed)

    result = v2.run_operational_cycle_v2(
        config,
        now=v2.datetime(2026, 8, 24, 18, 1, tzinfo=JAKARTA),
    )

    assert result["controller_status"] == "MISSED_EXECUTION_NO_CERTIFIED_OPEN"
    assert seen["prepared_path"] == prepared_path
    assert result["provider_calls"] is False
    assert result["outcome_access"] is False
