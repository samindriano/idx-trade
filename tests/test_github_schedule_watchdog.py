from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

from scripts.github_schedule_watchdog import JAKARTA, run_once


UTC = timezone.utc


def _runner_with_runs(runs_by_workflow: dict[str, list[dict[str, object]]]):
    calls: list[list[str]] = []

    def runner(command: list[str] | tuple[str, ...]):
        args = list(command)
        calls.append(args)
        if "api" in args:
            workflow = args[2].split("/")[-2]
            payload = {"workflow_runs": runs_by_workflow.get(workflow, [])}
            return 0, json.dumps(payload)
        if args[:2] == ["gh", "workflow"] or "workflow" in args:
            return 0, ""
        raise AssertionError(args)

    return runner, calls


def test_weekend_is_noop_and_does_not_query_github(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(command):
        calls.append(list(command))
        raise AssertionError("weekend must not call gh")

    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 29, 12, 0, tzinfo=JAKARTA),
        runner=runner,
    )

    assert result["status"] == "NON_TRADING_WEEKEND_NO_DISPATCH"
    assert calls == []
    assert (tmp_path / "events.jsonl").is_file()


def test_missing_native_runs_dispatches_due_post_close_slots(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs({})
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 18, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    assert [action["slot"] for action in result["actions"]] == ["STOCKBIT_1830", "E2E_1835"]
    assert all(action["status"] == "DISPATCH_REQUESTED" for action in result["actions"])
    markers = sorted((tmp_path / "dispatch_markers").glob("*.json"))
    assert len(markers) == 2
    assert any("stockbit-intraday-cloud-production.yml" in call for call in calls)
    assert any("e2e-paper-cloud-orchestration.yml" in call for call in calls)
    assert all("ZAPI_API_KEY" not in " ".join(call) for call in calls)


def test_missing_native_runs_dispatch_due_morning_stages(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs({})
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 9, 6, tzinfo=JAKARTA),
        runner=runner,
    )

    assert [action["slot"] for action in result["actions"]] == [
        "OFFICIAL_OPEN_0902",
        "E2E_PREOPEN_0903",
    ]
    assert all(action["status"] == "DISPATCH_REQUESTED" for action in result["actions"])
    assert any("official-open-prospective-cloud-capture.yml" in call for call in calls)
    assert any("e2e-paper-cloud-orchestration.yml" in call for call in calls)


def test_preopen_ca_never_dispatches_at_or_after_hard_cutoff(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs({})
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 9, 2, tzinfo=JAKARTA),
        runner=runner,
    )

    assert all(action["slot"] != "E2E_PREOPEN_CA_0855" for action in result["actions"])
    assert not any("PREOPEN_CA" in " ".join(call) for call in calls)


def test_morning_dispatch_does_not_backfill_expired_slot(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs({})
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 9, 10, tzinfo=JAKARTA),
        runner=runner,
    )

    assert result["actions"] == []
    assert calls == []


def test_existing_schedule_or_dispatch_run_suppresses_duplicate(tmp_path: Path) -> None:
    created = "2026-08-27T11:31:00Z"
    runner, calls = _runner_with_runs(
        {"stockbit-intraday-cloud-production.yml": [{"id": 123, "event": "schedule", "head_branch": "main", "created_at": created}]}
    )
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 18, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    stockbit = next(action for action in result["actions"] if action["slot"] == "STOCKBIT_1830")
    assert stockbit["status"] == "ALREADY_COVERED"
    assert not (tmp_path / "dispatch_markers" / "2026-08-27__STOCKBIT_1830.json").exists()
    dispatch_calls = [call for call in calls if "workflow" in call and "run" in call]
    assert len(dispatch_calls) == 1


def test_native_only_coverage_does_not_dispatch_the_already_created_slot(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs(
        {
            "e2e-paper-cloud-orchestration.yml": [
                {
                    "id": 321,
                    "event": "schedule",
                    "head_branch": "main",
                    "status": "completed",
                    "conclusion": "success",
                    "created_at": "2026-08-27T11:35:00Z",
                }
            ]
        }
    )

    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 18, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    e2e = next(action for action in result["actions"] if action["slot"] == "E2E_1835")
    assert e2e["status"] == "ALREADY_COVERED"
    assert not any(
        "e2e-paper-cloud-orchestration.yml" in call and "workflow" in call and "run" in call
        for call in calls
    )


def test_delayed_native_execution_is_still_seen_without_covering_a_later_slot(
    tmp_path: Path,
) -> None:
    runner, calls = _runner_with_runs(
        {
            "e2e-paper-cloud-orchestration.yml": [
                {
                    "id": 654,
                    "event": "schedule",
                    "head_branch": "main",
                    "status": "in_progress",
                    "conclusion": None,
                    # The run was enqueued at the 18:35 schedule, although its
                    # execution is still delayed at 19:05.
                    "created_at": "2026-08-27T11:35:00Z",
                }
            ]
        }
    )

    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 19, 10, tzinfo=JAKARTA),
        runner=runner,
    )

    statuses = {action["slot"]: action["status"] for action in result["actions"]}
    assert statuses["E2E_1835"] == "ALREADY_COVERED"
    assert statuses["E2E_1905"] == "DISPATCH_REQUESTED"
    assert any(
        "e2e-paper-cloud-orchestration.yml" in call
        and "POST_EOD" in " ".join(call)
        and "workflow" in call
        and "run" in call
        for call in calls
    )


def test_external_only_trigger_path_dispatches_when_native_is_absent(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs({})
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 19, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    assert any(action["status"] == "DISPATCH_REQUESTED" for action in result["actions"])
    assert any("workflow" in call and "run" in call for call in calls)


def test_queued_or_in_progress_run_counts_as_coverage(tmp_path: Path) -> None:
    runner, _ = _runner_with_runs(
        {
            "stockbit-intraday-cloud-production.yml": [
                {
                    "id": 987,
                    "event": "workflow_dispatch",
                    "head_branch": "main",
                    "status": "queued",
                    "conclusion": None,
                    "created_at": "2026-08-27T11:40:00Z",
                }
            ]
        }
    )
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 18, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    stockbit = next(action for action in result["actions"] if action["slot"] == "STOCKBIT_1830")
    assert stockbit["status"] == "ALREADY_COVERED"


def test_prior_same_workflow_slot_does_not_suppress_current_slot(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs(
        {
            "e2e-paper-cloud-orchestration.yml": [
                {
                    "id": 456,
                    "event": "workflow_dispatch",
                    "head_branch": "main",
                    "created_at": "2026-08-27T11:36:00Z",
                }
            ]
        }
    )
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 19, 10, tzinfo=JAKARTA),
        runner=runner,
    )

    e2e_retry = next(action for action in result["actions"] if action["slot"] == "E2E_1905")
    assert e2e_retry["status"] == "DISPATCH_REQUESTED"
    assert any(
        "e2e-paper-cloud-orchestration.yml" in call and "POST_EOD" in " ".join(call)
        for call in calls
    )


def test_marker_prevents_repeat_when_github_run_is_not_yet_visible(tmp_path: Path) -> None:
    runner, _ = _runner_with_runs({})
    first = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 18, 40, tzinfo=JAKARTA),
        runner=runner,
    )
    assert first["actions"]
    second = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 18, 41, tzinfo=JAKARTA),
        runner=runner,
    )
    statuses = {action["slot"]: action["status"] for action in second["actions"]}
    assert statuses["STOCKBIT_1830"] == "DISPATCH_ALREADY_REQUESTED_NO_VISIBLE_RUN"
    assert statuses["E2E_1835"] == "DISPATCH_ALREADY_REQUESTED_NO_VISIBLE_RUN"


def test_next_day_never_dispatches_previous_session(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs({})
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 28, 9, 30, tzinfo=JAKARTA),
        runner=runner,
    )
    assert result["status"] == "NO_DUE_SLOTS"
    assert result["actions"] == []
    assert not calls


def test_query_failure_is_fail_closed_without_dispatch(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(command):
        calls.append(list(command))
        if "api" in command:
            return 1, ""
        raise AssertionError("dispatch must not follow query failure")

    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 18, 40, tzinfo=JAKARTA),
        runner=runner,
    )
    assert all(action["status"] == "FAIL_CLOSED_QUERY" for action in result["actions"])
    assert not list((tmp_path / "dispatch_markers").glob("*.json"))


def test_installer_contract_allows_lightweight_watchdog_on_battery() -> None:
    installer = Path(__file__).parents[1] / "scripts" / "install_github_schedule_watchdog.ps1"
    text = installer.read_text(encoding="utf-8")
    assert "-AllowStartIfOnBatteries" in text
    assert "-DontStopIfGoingOnBatteries" in text


def test_installer_contract_has_morning_and_post_close_checks() -> None:
    installer = Path(__file__).parents[1] / "scripts" / "install_github_schedule_watchdog.ps1"
    text = installer.read_text(encoding="utf-8")
    assert "AddHours(8).AddMinutes(34)" in text
    assert "AddHours(8).AddMinutes(49)" in text
    assert "AddHours(8).AddMinutes(59)" in text
    assert "AddHours(9).AddMinutes(6)" in text
    assert "AddHours(18).AddMinutes(40)" in text
    assert "-MultipleInstances IgnoreNew" in text


def test_production_workflows_keep_trigger_paths_and_phase_concurrency_isolated() -> None:
    root = Path(__file__).parents[1]
    e2e = (root / ".github" / "workflows" / "e2e-paper-cloud-orchestration.yml").read_text(
        encoding="utf-8"
    )
    stockbit = (root / ".github" / "workflows" / "stockbit-intraday-cloud-production.yml").read_text(
        encoding="utf-8"
    )

    for schedule in (
        "30 1 * * 1-5",
        "45 1 * * 1-5",
        "55 1 * * 1-5",
        "3 2 * * 1-5",
        "13 2 * * 1-5",
        "22 2 * * 1-5",
        "35 11 * * 1-5",
        "5 12 * * 1-5",
        "35 12 * * 1-5",
    ):
        assert schedule in e2e
    for phase in ("PREOPEN_CA", "PREOPEN", "POST_EOD"):
        assert phase in e2e
    assert "cancel-in-progress: false" in e2e
    assert "'preopen-ca'" in e2e
    assert "'preopen'" in e2e
    assert "'post-eod'" in e2e
    assert "cancel-in-progress: false" in stockbit
