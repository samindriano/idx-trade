from __future__ import annotations

from datetime import datetime, timezone, timedelta, time
import json
from pathlib import Path
import re

from scripts.github_schedule_watchdog import (
    JAKARTA,
    SLOTS,
    _dispatch,
    _exact_slot_runs,
    _slot_due,
    run_once,
)


UTC = timezone.utc

CANONICAL_SLOT_IDS = {
    "E2E_PREOPEN_CA_0830",
    "E2E_PREOPEN_CA_0845",
    "E2E_PREOPEN_CA_0855",
    "E2E_PREOPEN_0903",
    "E2E_PREOPEN_0913",
    "E2E_PREOPEN_0922",
    "E2E_POST_EOD_1835",
    "E2E_POST_EOD_1905",
    "E2E_POST_EOD_1935",
    "STOCKBIT_INTRADAY_1830",
    "STOCKBIT_INTRADAY_1930",
    "STOCKBIT_INTRADAY_2030",
    "OFFICIAL_OPEN_0902",
    "OFFICIAL_OPEN_0912",
    "OFFICIAL_OPEN_0922",
}

E2E_SLOT_IDS = {
    "E2E_PREOPEN_CA_0830",
    "E2E_PREOPEN_CA_0845",
    "E2E_PREOPEN_CA_0855",
    "E2E_PREOPEN_0903",
    "E2E_PREOPEN_0913",
    "E2E_PREOPEN_0922",
    "E2E_POST_EOD_1835",
    "E2E_POST_EOD_1905",
    "E2E_POST_EOD_1935",
}


def test_watchdog_slot_surface_uses_canonical_logical_ids() -> None:
    assert {slot.slot_id for slot in SLOTS} == CANONICAL_SLOT_IDS
    assert not any(slot.slot_id in {"E2E_1835", "E2E_1905", "E2E_1935"} for slot in SLOTS)
    assert not any(
        slot.slot_id in {"STOCKBIT_1830", "STOCKBIT_1930", "STOCKBIT_2030"}
        for slot in SLOTS
    )


def test_final_0922_slots_close_at_0923() -> None:
    final_slots = [slot for slot in SLOTS if slot.due_local == time(9, 22)]
    assert {slot.slot_id for slot in final_slots} == {
        "OFFICIAL_OPEN_0922",
        "E2E_PREOPEN_0922",
    }
    assert {slot.latest_local for slot in final_slots} == {time(9, 23)}


def _dispatch_command(slot) -> list[str]:
    calls: list[list[str]] = []

    def runner(command):
        calls.append(list(command))
        return 0, ""

    assert _dispatch(
        runner=runner,
        repository="samindriano/idx-trade",
        slot=slot,
        gh_exe="gh",
    ) == 0
    assert len(calls) == 1
    return calls[0]


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

    assert [action["slot"] for action in result["actions"]] == [
        "STOCKBIT_INTRADAY_1830",
        "E2E_POST_EOD_1835",
    ]
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
        {
            "stockbit-intraday-cloud-production.yml": [
                {
                    "id": 123,
                    "event": "schedule",
                    "head_branch": "main",
                    "created_at": created,
                    "display_title": "IDX-SLOT:STOCKBIT_INTRADAY_1830",
                }
            ]
        }
    )
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 18, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    stockbit = next(
        action
        for action in result["actions"]
        if action["slot"] == "STOCKBIT_INTRADAY_1830"
    )
    assert stockbit["status"] == "ALREADY_COVERED"
    assert not (
        tmp_path
        / "dispatch_markers"
        / "2026-08-27__STOCKBIT_INTRADAY_1830.json"
    ).exists()
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
                    "display_title": "IDX-SLOT:E2E_POST_EOD_1835",
                }
            ]
        }
    )

    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 18, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    e2e = next(
        action
        for action in result["actions"]
        if action["slot"] == "E2E_POST_EOD_1835"
    )
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
                    "created_at": "2026-08-27T11:35:00Z",
                    "display_title": "IDX-SLOT:E2E_POST_EOD_1835",
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
    assert statuses["E2E_POST_EOD_1835"] == "ALREADY_COVERED"
    assert statuses["E2E_POST_EOD_1905"] == "DISPATCH_REQUESTED"
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
                    "display_title": "IDX-SLOT:STOCKBIT_INTRADAY_1830",
                }
            ]
        }
    )
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 18, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    stockbit = next(
        action
        for action in result["actions"]
        if action["slot"] == "STOCKBIT_INTRADAY_1830"
    )
    assert stockbit["status"] == "ALREADY_COVERED"


def test_delayed_1830_run_near_1930_cannot_cover_stockbit_1930(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs(
        {
            "stockbit-intraday-cloud-production.yml": [
                {
                    "id": 111,
                    "event": "schedule",
                    "head_branch": "main",
                    "status": "in_progress",
                    "conclusion": None,
                    "created_at": "2026-08-27T12:29:00Z",
                    "display_title": "IDX-SLOT:STOCKBIT_INTRADAY_1830",
                }
            ]
        }
    )

    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 19, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    action = next(
        item
        for item in result["actions"]
        if item["slot"] == "STOCKBIT_INTRADAY_1930"
    )
    assert action["status"] == "DISPATCH_REQUESTED_AMBIGUOUS_RUN"
    assert action["ambiguous_run_ids"] == [111]
    assert any(
        "stockbit-intraday-cloud-production.yml" in call
        and "slot=1930" in " ".join(call)
        for call in calls
    )


def test_exact_1930_native_run_covers_stockbit_1930(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs(
        {
            "stockbit-intraday-cloud-production.yml": [
                {
                    "id": 222,
                    "event": "schedule",
                    "head_branch": "main",
                    "status": "completed",
                    "conclusion": "success",
                    "created_at": "2026-08-27T12:30:00Z",
                    "display_title": "IDX-SLOT:STOCKBIT_INTRADAY_1930",
                }
            ]
        }
    )

    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 19, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    action = next(
        item
        for item in result["actions"]
        if item["slot"] == "STOCKBIT_INTRADAY_1930"
    )
    assert action["status"] == "ALREADY_COVERED"
    assert not any("slot=1930" in " ".join(call) for call in calls)


def test_exact_watchdog_dispatch_run_covers_intended_current_slot(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs(
        {
            "stockbit-intraday-cloud-production.yml": [
                {
                    "id": 333,
                    "event": "workflow_dispatch",
                    "head_branch": "main",
                    "status": "in_progress",
                    "conclusion": None,
                    "created_at": "2026-08-27T12:30:30Z",
                    "display_title": "IDX-SLOT:STOCKBIT_INTRADAY_1930",
                }
            ]
        }
    )

    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 19, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    action = next(
        item
        for item in result["actions"]
        if item["slot"] == "STOCKBIT_INTRADAY_1930"
    )
    assert action["status"] == "ALREADY_COVERED"
    assert not any("slot=1930" in " ".join(call) for call in calls)


def test_out_of_order_delayed_schedule_cannot_suppress_later_valid_slot(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs(
        {
            "stockbit-intraday-cloud-production.yml": [
                {
                    "id": 444,
                    "event": "schedule",
                    "head_branch": "main",
                    "status": "queued",
                    "conclusion": None,
                    "created_at": "2026-08-27T12:29:59Z",
                    "display_title": "IDX-SLOT:STOCKBIT_INTRADAY_1830",
                }
            ]
        }
    )

    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 19, 40, tzinfo=JAKARTA),
        runner=runner,
    )

    action = next(
        item
        for item in result["actions"]
        if item["slot"] == "STOCKBIT_INTRADAY_1930"
    )
    assert action["status"] == "DISPATCH_REQUESTED_AMBIGUOUS_RUN"
    assert any("slot=1930" in " ".join(call) for call in calls)


def test_prior_same_workflow_slot_does_not_suppress_current_slot(tmp_path: Path) -> None:
    runner, calls = _runner_with_runs(
        {
            "e2e-paper-cloud-orchestration.yml": [
                {
                    "id": 456,
                    "event": "workflow_dispatch",
                    "head_branch": "main",
                    "created_at": "2026-08-27T11:36:00Z",
                    "display_title": "IDX-SLOT:E2E_POST_EOD_1835",
                }
            ]
        }
    )
    result = run_once(
        state_root=tmp_path,
        now=datetime(2026, 8, 27, 19, 10, tzinfo=JAKARTA),
        runner=runner,
    )

    e2e_retry = next(
        action
        for action in result["actions"]
        if action["slot"] == "E2E_POST_EOD_1905"
    )
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
    assert statuses["STOCKBIT_INTRADAY_1830"] == "DISPATCH_ALREADY_REQUESTED_NO_VISIBLE_RUN"
    assert statuses["E2E_POST_EOD_1835"] == "DISPATCH_ALREADY_REQUESTED_NO_VISIBLE_RUN"


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


def test_exact_run_detection_accepts_schedule_and_dispatch_and_retains_metadata(
    tmp_path: Path,
) -> None:
    for event in ("schedule", "workflow_dispatch"):
        state_root = tmp_path / event
        runner, calls = _runner_with_runs(
            {
                "e2e-paper-cloud-orchestration.yml": [
                    {
                        "id": 700 if event == "schedule" else 701,
                        "event": event,
                        "head_branch": "main",
                        "ref": "refs/heads/main",
                        "status": "in_progress",
                        "conclusion": None,
                        "created_at": "2026-08-27T11:36:00Z",
                        "display_title": "IDX-SLOT:E2E_POST_EOD_1835",
                        "run_name": "IDX-SLOT:E2E_POST_EOD_1835",
                    }
                ]
            }
        )

        result = run_once(
            state_root=state_root,
            now=datetime(2026, 8, 27, 18, 40, tzinfo=JAKARTA),
            runner=runner,
        )

        action = next(
            item
            for item in result["actions"]
            if item["slot"] == "E2E_POST_EOD_1835"
        )
        assert action["status"] == "ALREADY_COVERED"
        assert action["run_events"] == [event]
        assert action["run_names"] == ["IDX-SLOT:E2E_POST_EOD_1835"]
        assert action["run_metadata"] == [
            {
                "id": 700 if event == "schedule" else 701,
                "event": event,
                "display_title": "IDX-SLOT:E2E_POST_EOD_1835",
                "run_name": "IDX-SLOT:E2E_POST_EOD_1835",
                "runName": None,
                "created_at": "2026-08-27T11:36:00Z",
                "head_branch": "main",
                "ref": "refs/heads/main",
            }
        ]
        assert not any(
            "e2e-paper-cloud-orchestration.yml" in call
            and "workflow" in call
            and "run" in call
            for call in calls
        )


def test_exact_run_detection_requires_slot_identity_and_bounded_observation() -> None:
    slot = next(slot for slot in SLOTS if slot.slot_id == "E2E_POST_EOD_1905")
    due = _slot_due(datetime(2026, 8, 27, tzinfo=JAKARTA).date(), slot)
    cutoff = slot.window_end(due.date())
    observation = due + timedelta(minutes=10)
    base = {
        "id": 800,
        "event": "schedule",
        "head_branch": "main",
        "ref": "main",
        "status": "completed",
        "conclusion": "success",
        "display_title": "IDX-SLOT:E2E_POST_EOD_1905",
    }

    def accepted(
        created_at: datetime, *, observed_at: datetime = observation
    ) -> list[dict[str, object]]:
        return _exact_slot_runs(
            runs=[{**base, "created_at": created_at.isoformat()}],
            slot=slot,
            due=due,
            observation=observed_at,
        )

    assert accepted(due - timedelta(seconds=1)) == []
    assert accepted(due) != []
    assert accepted(cutoff - timedelta(seconds=1), observed_at=cutoff) != []
    assert accepted(cutoff) == []
    assert accepted(observation + timedelta(seconds=1)) == []

    wrong_slot = {
        **base,
        "created_at": (due + timedelta(minutes=1)).isoformat(),
        "display_title": "IDX-SLOT:E2E_POST_EOD_1835",
    }
    assert _exact_slot_runs(
        runs=[wrong_slot], slot=slot, due=due, observation=observation
    ) == []

    wrong_identity_suffix = {
        **base,
        "created_at": (due + timedelta(minutes=1)).isoformat(),
        "display_title": "IDX-SLOT:E2E_POST_EOD_1905_EXTRA",
    }
    assert _exact_slot_runs(
        runs=[wrong_identity_suffix], slot=slot, due=due, observation=observation
    ) == []


def test_exact_run_detection_requires_production_main() -> None:
    slot = next(slot for slot in SLOTS if slot.slot_id == "STOCKBIT_INTRADAY_1930")
    due = _slot_due(datetime(2026, 8, 27, tzinfo=JAKARTA).date(), slot)
    base = {
        "id": 801,
        "event": "schedule",
        "created_at": (due + timedelta(seconds=1)).isoformat(),
        "display_title": "IDX-SLOT:STOCKBIT_INTRADAY_1930",
    }
    observation = due + timedelta(minutes=5)

    assert _exact_slot_runs(
        runs=[{**base, "head_branch": "feature/watchdog"}],
        slot=slot,
        due=due,
        observation=observation,
    ) == []
    assert _exact_slot_runs(
        runs=[{**base, "head_branch": "main", "ref": "refs/heads/feature"}],
        slot=slot,
        due=due,
        observation=observation,
    ) == []
    assert _exact_slot_runs(
        runs=[{**base, "ref": "refs/heads/main"}],
        slot=slot,
        due=due,
        observation=observation,
    ) != []


def test_every_watchdog_e2e_slot_id_is_in_actual_workflow_allow_list() -> None:
    workflow = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "e2e-paper-cloud-orchestration.yml"
    ).read_text(encoding="utf-8")
    run_name_contract = workflow.split("\non:", 1)[0]
    allowed_by_schedule = {
        slot_id
        for _, slot_id in re.findall(
            r"github\.event\.schedule == '([^']+)' && '(E2E_[A-Z0-9_]+)'",
            run_name_contract,
        )
    }
    allow_list = re.search(
        r'case "\$E2E_TRIGGER_SLOT_INPUT" in\s+([A-Z0-9_|]+)\) ;;', workflow
    )

    assert "trigger_slot:" in workflow
    assert "inputs.trigger_slot ||" not in run_name_contract
    assert "does not agree with phase" in workflow
    assert allow_list is not None
    allowed_by_input = set(allow_list.group(1).split("|"))
    assert allowed_by_input == E2E_SLOT_IDS
    assert allowed_by_schedule == E2E_SLOT_IDS
    assert {
        slot.slot_id
        for slot in SLOTS
        if slot.workflow_file == "e2e-paper-cloud-orchestration.yml"
    } == allowed_by_schedule
    for slot_id in E2E_SLOT_IDS:
        phase = (
            "PREOPEN_CA"
            if slot_id.startswith("E2E_PREOPEN_CA_")
            else "PREOPEN"
            if slot_id.startswith("E2E_PREOPEN_")
            else "POST_EOD"
        )
        assert f"inputs.phase == '{phase}' && inputs.trigger_slot == '{slot_id}' && '{slot_id}'" in run_name_contract


def test_watchdog_and_cloudflare_use_identical_canonical_slot_contracts() -> None:
    root = Path(__file__).parents[1]
    core = (root / "infra" / "cloudflare_github_scheduler" / "src" / "core.mjs").read_text(
        encoding="utf-8"
    )
    cloudflare_slots = {
        slot_id: (workflow_file, input_name, input_value)
        for slot_id, workflow_file, input_name, input_value in re.findall(
            r"\{ id: '([^']+)', due: '[^']+', checkDelayMin: \d+, latest: '[^']+', "
            r"workflow: '([^']+)', inputName: '([^']+)', inputValue: '([^']+)' \}",
            core,
        )
    }
    watchdog_slots = {
        slot.slot_id: (slot.workflow_file, slot.input_name, slot.input_value)
        for slot in SLOTS
    }
    assert cloudflare_slots == watchdog_slots


def test_watchdog_official_and_intraday_slots_match_actual_workflows() -> None:
    root = Path(__file__).parents[1]
    expected_by_workflow = {
        "official-open-prospective-cloud-capture.yml": {
            slot.slot_id
            for slot in SLOTS
            if slot.workflow_file == "official-open-prospective-cloud-capture.yml"
        },
        "stockbit-intraday-cloud-production.yml": {
            slot.slot_id
            for slot in SLOTS
            if slot.workflow_file == "stockbit-intraday-cloud-production.yml"
        },
    }
    for workflow_file, expected_ids in expected_by_workflow.items():
        workflow = (root / ".github" / "workflows" / workflow_file).read_text(
            encoding="utf-8"
        )
        actual = re.findall(
            r"\(github\.event\.schedule == '([^']+)' \|\| inputs\.slot == '([^']+)'\)"
            r" && '(OFFICIAL_OPEN_\d{4}|STOCKBIT_INTRADAY_\d{4})'",
            workflow,
        )
        assert {slot_id for _, _, slot_id in actual} == expected_ids
        for cron, input_value, slot_id in actual:
            assert cron
            assert any(
                slot.workflow_file == workflow_file
                and slot.input_name == "slot"
                and slot.input_value == input_value
                and slot.slot_id == slot_id
                for slot in SLOTS
            )


def test_stockbit_stream_is_outside_both_redundant_trigger_paths() -> None:
    root = Path(__file__).parents[1]
    core = (root / "infra" / "cloudflare_github_scheduler" / "src" / "core.mjs").read_text(
        encoding="utf-8"
    )
    assert all("stream" not in slot.workflow_file.lower() for slot in SLOTS)
    assert "stream-prospective" not in core.lower()
    for workflow_file in (
        "e2e-paper-cloud-orchestration.yml",
        "official-open-prospective-cloud-capture.yml",
        "stockbit-intraday-cloud-production.yml",
    ):
        workflow = (root / ".github" / "workflows" / workflow_file).read_text(
            encoding="utf-8"
        )
        assert "stockbit-stream" not in workflow.lower()


def test_every_e2e_slot_dispatches_phase_and_exact_trigger_slot() -> None:
    e2e_slots = [
        slot for slot in SLOTS if slot.workflow_file == "e2e-paper-cloud-orchestration.yml"
    ]
    assert e2e_slots

    for slot in e2e_slots:
        command = _dispatch_command(slot)
        assert command == [
            "gh",
            "workflow",
            "run",
            slot.workflow_file,
            "--repo",
            "samindriano/idx-trade",
            "--ref",
            "main",
            "--field",
            f"phase={slot.input_value}",
            "--field",
            f"trigger_slot={slot.slot_id}",
        ]


def test_non_e2e_dispatch_keeps_existing_exact_slot_input() -> None:
    non_e2e_slots = [
        slot for slot in SLOTS if slot.workflow_file != "e2e-paper-cloud-orchestration.yml"
    ]
    assert non_e2e_slots

    for slot in non_e2e_slots:
        command = _dispatch_command(slot)
        assert command == [
            "gh",
            "workflow",
            "run",
            slot.workflow_file,
            "--repo",
            "samindriano/idx-trade",
            "--ref",
            "main",
            "--field",
            f"{slot.input_name}={slot.input_value}",
        ]


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
    assert "AddHours(9).AddMinutes(22)" in text
    assert "AddHours(9).AddMinutes(26)" not in text
    assert "AddHours(18).AddMinutes(40)" in text
    assert "-MultipleInstances IgnoreNew" in text


def test_production_workflows_keep_trigger_paths_and_recovery_topology_safe() -> None:
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

    assert "\nconcurrency:\n" not in e2e
    assert "no workflow-level concurrency group" in e2e
    assert "conditional immutable R2 stage/checkpoint commit" in e2e
    # Intraday retains its independently reviewed same-session provider fencing.
    assert "cancel-in-progress: false" in stockbit
