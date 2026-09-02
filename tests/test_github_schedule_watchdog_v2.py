from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from scripts import github_schedule_watchdog as v1
from scripts import github_schedule_watchdog_v2 as v2


def _slot(slot_id: str):
    return next(slot for slot in v1.SLOTS if slot.slot_id == slot_id)


def _runner_with_open_runs(runs: list[dict[str, object]]):
    calls: list[list[str]] = []

    def runner(command):
        args = list(command)
        calls.append(args)
        if "api" in args:
            workflow = args[2].split("/")[-2]
            return 0, json.dumps(
                {"workflow_runs": runs if workflow == v2.OFFICIAL_OPEN_WORKFLOW else []}
            )
        return 0, ""

    return runner, calls


def test_official_open_hmac_matches_independent_vector() -> None:
    fields = v2._official_open_attestation_fields(
        repository="samindriano/idx-trade",
        slot=_slot("OFFICIAL_OPEN_0902"),
        session_date="2026-09-02",
        current=datetime(2026, 9, 2, 9, 6, tzinfo=v1.JAKARTA),
        signing_key="test-secret",
        nonce="nonce_1234567890abcd",
    )
    assert fields == {
        "session_date": "2026-09-02",
        "scheduler_issued_at": "2026-09-02T02:06:00+00:00",
        "scheduler_nonce": "nonce_1234567890abcd",
        "scheduler_signature": "ea0cd9324e33852e9f7722e6eb42795213c5b8b30c8a44208c8dbee9df3e89f1",
    }


def test_official_open_dispatch_contains_proof_but_never_key(monkeypatch) -> None:
    monkeypatch.setenv(v2.SIGNING_KEY_ENV, "test-secret")
    calls: list[list[str]] = []

    def runner(command):
        calls.append(list(command))
        return 0, ""

    result = v2._dispatch_v2(
        runner=runner,
        repository="samindriano/idx-trade",
        slot=_slot("OFFICIAL_OPEN_0902"),
        gh_exe="gh",
        current=datetime(2026, 9, 2, 9, 6, tzinfo=v1.JAKARTA),
        nonce_factory=lambda: "nonce_1234567890abcd",
    )
    assert result == 0
    assert len(calls) == 1
    joined = " ".join(calls[0])
    assert "slot=0902" in joined
    assert "session_date=2026-09-02" in joined
    assert "scheduler_issued_at=2026-09-02T02:06:00+00:00" in joined
    assert "scheduler_nonce=nonce_1234567890abcd" in joined
    assert "scheduler_signature=ea0cd9324e33852e9f7722e6eb42795213c5b8b30c8a44208c8dbee9df3e89f1" in joined
    assert "test-secret" not in joined
    assert v2.SIGNING_KEY_ENV not in joined


def test_missing_signing_key_fails_before_gh(monkeypatch) -> None:
    monkeypatch.delenv(v2.SIGNING_KEY_ENV, raising=False)
    calls: list[list[str]] = []

    def runner(command):
        calls.append(list(command))
        return 0, ""

    result = v2._dispatch_v2(
        runner=runner,
        repository="samindriano/idx-trade",
        slot=_slot("OFFICIAL_OPEN_0902"),
        gh_exe="gh",
        current=datetime(2026, 9, 2, 9, 6, tzinfo=v1.JAKARTA),
    )
    assert result == 97
    assert calls == []


def test_non_open_dispatch_remains_unattested(monkeypatch) -> None:
    monkeypatch.setenv(v2.SIGNING_KEY_ENV, "test-secret")
    calls: list[list[str]] = []

    def runner(command):
        calls.append(list(command))
        return 0, ""

    result = v2._dispatch_v2(
        runner=runner,
        repository="samindriano/idx-trade",
        slot=_slot("E2E_PREOPEN_0903"),
        gh_exe="gh",
        current=datetime(2026, 9, 2, 9, 6, tzinfo=v1.JAKARTA),
    )
    assert result == 0
    joined = " ".join(calls[0])
    assert "phase=PREOPEN" in joined
    assert "trigger_slot=E2E_PREOPEN_0903" in joined
    assert "scheduler_signature=" not in joined
    assert "scheduler_nonce=" not in joined


def test_manual_open_workflow_dispatch_cannot_suppress_trusted_recovery(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(v2.SIGNING_KEY_ENV, "test-secret")
    runner, calls = _runner_with_open_runs(
        [
            {
                "id": 901,
                "event": "workflow_dispatch",
                "head_branch": "main",
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-09-02T02:03:00Z",
                "display_title": "IDX-SLOT:OFFICIAL_OPEN_0902",
            }
        ]
    )
    result = v2.run_once(
        state_root=tmp_path,
        now=datetime(2026, 9, 2, 9, 6, tzinfo=v1.JAKARTA),
        runner=runner,
        gh_exe="gh",
    )
    action = next(item for item in result["actions"] if item["slot"] == "OFFICIAL_OPEN_0902")
    assert action["status"] == "DISPATCH_REQUESTED_AMBIGUOUS_RUN"
    assert action["ambiguous_run_ids"] == [901]
    dispatch = next(call for call in calls if "workflow" in call and "run" in call)
    assert "scheduler_signature=" in " ".join(dispatch)


def test_inflight_native_open_run_does_not_consume_sole_recovery_check(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(v2.SIGNING_KEY_ENV, "test-secret")
    runner, calls = _runner_with_open_runs(
        [
            {
                "id": 902,
                "event": "schedule",
                "head_branch": "main",
                "status": "in_progress",
                "conclusion": None,
                "created_at": "2026-09-02T02:02:00Z",
                "display_title": "IDX-SLOT:OFFICIAL_OPEN_0902",
            }
        ]
    )
    result = v2.run_once(
        state_root=tmp_path,
        now=datetime(2026, 9, 2, 9, 6, tzinfo=v1.JAKARTA),
        runner=runner,
        gh_exe="gh",
    )
    action = next(item for item in result["actions"] if item["slot"] == "OFFICIAL_OPEN_0902")
    assert action["status"] == "DISPATCH_REQUESTED_AMBIGUOUS_RUN"
    assert any("scheduler_signature=" in " ".join(call) for call in calls if "workflow" in call)


def test_completed_successful_native_open_run_suppresses_recovery(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(v2.SIGNING_KEY_ENV, "test-secret")
    runner, calls = _runner_with_open_runs(
        [
            {
                "id": 903,
                "event": "schedule",
                "head_branch": "main",
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-09-02T02:02:00Z",
                "display_title": "IDX-SLOT:OFFICIAL_OPEN_0902",
            }
        ]
    )
    result = v2.run_once(
        state_root=tmp_path,
        now=datetime(2026, 9, 2, 9, 6, tzinfo=v1.JAKARTA),
        runner=runner,
        gh_exe="gh",
    )
    action = next(item for item in result["actions"] if item["slot"] == "OFFICIAL_OPEN_0902")
    assert action["status"] == "ALREADY_COVERED"
    assert action["run_ids"] == [903]
    assert not any("workflow" in call and "run" in call for call in calls)


def test_prior_local_marker_deduplicates_own_visible_dispatch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(v2.SIGNING_KEY_ENV, "test-secret")
    marker = tmp_path / "dispatch_markers" / "2026-09-02__OFFICIAL_OPEN_0902.json"
    marker.parent.mkdir(parents=True)
    marker.write_text("{}\n", encoding="utf-8")
    runner, calls = _runner_with_open_runs(
        [
            {
                "id": 904,
                "event": "workflow_dispatch",
                "head_branch": "main",
                "status": "in_progress",
                "conclusion": None,
                "created_at": "2026-09-02T02:05:00Z",
                "display_title": "IDX-SLOT:OFFICIAL_OPEN_0902",
            }
        ]
    )
    result = v2.run_once(
        state_root=tmp_path,
        now=datetime(2026, 9, 2, 9, 6, tzinfo=v1.JAKARTA),
        runner=runner,
        gh_exe="gh",
    )
    action = next(item for item in result["actions"] if item["slot"] == "OFFICIAL_OPEN_0902")
    assert action["status"] == "DISPATCH_ALREADY_REQUESTED_NO_VISIBLE_RUN"
    assert not any("workflow" in call and "run" in call for call in calls)


def test_run_once_persists_no_signature_or_nonce(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(v2.SIGNING_KEY_ENV, "test-secret")
    calls: list[list[str]] = []

    def runner(command):
        args = list(command)
        calls.append(args)
        if "api" in args:
            return 0, json.dumps({"workflow_runs": []})
        return 0, ""

    result = v2.run_once(
        state_root=tmp_path,
        now=datetime(2026, 9, 2, 9, 6, tzinfo=v1.JAKARTA),
        runner=runner,
        gh_exe="gh",
    )
    open_action = next(action for action in result["actions"] if action["slot"] == "OFFICIAL_OPEN_0902")
    assert open_action["status"] == "DISPATCH_REQUESTED"

    marker = tmp_path / "dispatch_markers" / "2026-09-02__OFFICIAL_OPEN_0902.json"
    marker_text = marker.read_text(encoding="utf-8")
    events_text = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert "scheduler_signature" not in marker_text
    assert "scheduler_nonce" not in marker_text
    assert "test-secret" not in marker_text
    assert "scheduler_signature" not in events_text
    assert "scheduler_nonce" not in events_text
    assert "test-secret" not in events_text


def test_patch_restores_v1_hooks(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(v2.SIGNING_KEY_ENV, "test-secret")
    original_dispatch = v1._dispatch
    original_exact_slot_runs = v1._exact_slot_runs

    def runner(command):
        args = list(command)
        if "api" in args:
            return 0, json.dumps({"workflow_runs": []})
        return 0, ""

    v2.run_once(
        state_root=tmp_path,
        now=datetime(2026, 9, 2, 9, 6, tzinfo=v1.JAKARTA),
        runner=runner,
        gh_exe="gh",
    )
    assert v1._dispatch is original_dispatch
    assert v1._exact_slot_runs is original_exact_slot_runs
