from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PS1 = ROOT / "scripts" / "run_forward_eod_v4_x1_pipeline.ps1"
UPDATE_TASK_PS1 = ROOT / "scripts" / "update_forward_eod_task_v4_x1.ps1"


def test_pipeline_wrapper_invokes_only_scoped_legacy_compat_module() -> None:
    source = PIPELINE_PS1.read_text(encoding="utf-8")
    assert "idx_trade.v4_x1_eod_legacy_compat" in source
    assert "idx_trade.v4_x1_eod_pipeline" not in source

    # PowerShell-facing parameters are declared as variables, while the
    # Python module receives GNU-style CLI flags. Verify both sides.
    assert '[string]$RuntimeRoot' in source
    assert '[string]$X1ModelRoot' in source
    assert '[string]$RepoRoot' in source
    assert '[string]$PythonExe' in source
    assert "--runtime-root $resolvedRuntime" in source
    assert "--x1-model-root $resolvedModel" in source
    assert "--repo-root $resolvedRepo" in source
    assert "& $PythonExe -m idx_trade.v4_x1_eod_legacy_compat" in source

    # The wrapper must not become a second market-data/provider path.
    assert "fetch_stock_summary" not in source
    assert "download_daily" not in source


def test_task_update_has_three_evening_triggers_logon_and_retry() -> None:
    source = UPDATE_TASK_PS1.read_text(encoding="utf-8")
    for clock in ("18:30", "19:30", "20:30"):
        assert f'-At "{clock}"' in source
    assert "New-ScheduledTaskTrigger -AtLogOn" in source
    assert "-RestartCount 3" in source
    assert "New-TimeSpan -Minutes 10" in source
    assert "-WakeToRun" in source
    assert "-StartWhenAvailable" in source
    assert "-RunOnlyIfNetworkAvailable" in source
    assert "-MultipleInstances IgnoreNew" in source
    assert "-AllowStartIfOnBatteries" in source
    assert "-DontStopIfGoingOnBatteries" in source


def test_task_update_repoints_existing_canonical_task_not_second_task() -> None:
    source = UPDATE_TASK_PS1.read_text(encoding="utf-8")
    assert '[string]$TaskName = "IDXTrade-ForwardEOD"' in source
    assert "Get-ScheduledTask -TaskName $TaskName" in source
    assert "Set-ScheduledTask" in source
    assert "Register-ScheduledTask" not in source
    assert "run_forward_eod_v4_x1_pipeline.ps1" in source
    assert "TASK_UPDATE_PASS" in source
