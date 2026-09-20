from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path

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
