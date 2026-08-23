from __future__ import annotations

from pathlib import Path

from scripts.run_e2e_paper_scheduled_v1 import scheduler_exit_code


def test_scheduler_status_exit_contract() -> None:
    assert scheduler_exit_code("WEEKEND_OR_HOLIDAY_NOOP") == 0
    assert scheduler_exit_code("WAITING_OPERATIONAL_CONFIGURATION") == 1
    assert scheduler_exit_code("EXECUTION_COMPLETE") == 0
    assert scheduler_exit_code("FAIL_CLOSED") == 1


def test_task_installer_isolated_and_retry_safe() -> None:
    script = Path(__file__).parents[1] / "scripts" / "install_e2e_paper_task.ps1"
    text = script.read_text(encoding="utf-8")
    for at in ("08:30", "08:45", "09:00", "09:02", "09:07", "09:12", "09:17", "09:22", "18:35", "19:35", "20:35"):
        assert at in text
    assert '"18:05"' not in text
    assert "-AtLogOn" in text
    assert "-StartWhenAvailable" in text
    assert "-MultipleInstances IgnoreNew" in text
    assert "-RunOnlyIfNetworkAvailable" in text
    assert "--config-sha256" in text
    assert "IDXTrade-ForwardEOD" not in text
    assert "IDXTrade-ForwardOpenArchive" not in text
