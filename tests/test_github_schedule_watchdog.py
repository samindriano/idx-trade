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
        now=datetime(2026, 8, 28, 9, 0, tzinfo=JAKARTA),
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
