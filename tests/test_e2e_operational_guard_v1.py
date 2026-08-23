from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from idx_trade.e2e_operational_guard_v1 import (
    E2EOperationalGuardError,
    JAKARTA,
    attest_deployment,
    exclusive_run_lock,
    load_session_dates,
    require_phase_attestation,
    require_phase_window,
    write_phase_attestation,
    write_status_atomic,
)


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 24, hour, minute, tzinfo=JAKARTA)


def test_preopen_requires_exact_same_day_and_frozen_window() -> None:
    sessions = ("2026-08-24",)
    assert require_phase_window(
        phase="PREOPEN",
        session_date="2026-08-24",
        official_session_dates=sessions,
        now=_at(9, 2),
    ).status == "PASS"
    with pytest.raises(E2EOperationalGuardError, match="TOO_EARLY"):
        require_phase_window(
            phase="PREOPEN", session_date="2026-08-24", official_session_dates=sessions, now=_at(9, 1)
        )
    with pytest.raises(E2EOperationalGuardError, match="WINDOW_MISSED"):
        require_phase_window(
            phase="PREOPEN", session_date="2026-08-24", official_session_dates=sessions, now=_at(9, 23)
        )
    with pytest.raises(E2EOperationalGuardError, match="NOT_SAME"):
        require_phase_window(
            phase="PREOPEN", session_date="2026-08-24", official_session_dates=sessions,
            now=datetime(2026, 8, 25, 9, 2, tzinfo=JAKARTA),
        )


def test_post_eod_and_non_session_fail_closed() -> None:
    assert require_phase_window(
        phase="POST_EOD", session_date="2026-08-24", official_session_dates=("2026-08-24",), now=_at(18)
    ).status == "PASS"
    with pytest.raises(E2EOperationalGuardError, match="POST_EOD_TOO_EARLY"):
        require_phase_window(
            phase="POST_EOD", session_date="2026-08-24", official_session_dates=("2026-08-24",), now=_at(17, 59)
        )
    with pytest.raises(E2EOperationalGuardError, match="NOT_IN_OFFICIAL"):
        require_phase_window(
            phase="PREOPEN", session_date="2026-08-25", official_session_dates=("2026-08-24",), now=_at(9, 2)
        )


def test_calendar_loader_and_status_write_are_deterministic(tmp_path: Path) -> None:
    calendar = tmp_path / "sessions.csv"
    calendar.write_text("date\n2026-08-25\n2026-08-24\n", encoding="utf-8")
    assert load_session_dates(calendar) == ("2026-08-24", "2026-08-25")
    status = tmp_path / "operational" / "latest.json"
    sha = write_status_atomic(status, {"status": "WEEKEND_OR_HOLIDAY_NOOP", "outcome_access": False})
    assert status.is_file()
    assert sha
    assert json.loads(status.read_text(encoding="utf-8"))["outcome_access"] is False


@pytest.mark.parametrize(
    ("contents", "error"),
    [
        ("date\n2026-08-24\n2026-08-24\n", "DUPLICATE_DATE"),
        ("date\n2026-08-22\n", "WEEKEND_SESSION"),
    ],
)
def test_calendar_loader_rejects_duplicate_or_weekend_rows(
    tmp_path: Path, contents: str, error: str
) -> None:
    calendar = tmp_path / "sessions.csv"
    calendar.write_text(contents, encoding="utf-8")
    with pytest.raises(E2EOperationalGuardError, match=error):
        load_session_dates(calendar)


def test_exclusive_lock_rejects_second_holder(tmp_path: Path) -> None:
    lock = tmp_path / "run.lock"
    with exclusive_run_lock(lock):
        with pytest.raises(E2EOperationalGuardError, match="ALREADY_IN_PROGRESS"):
            with exclusive_run_lock(lock):
                pass


def test_deployment_attestation_rejects_wrong_identity_and_dirty_tree(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    (tmp_path / "tracked.txt").write_text("ok", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "test"], cwd=tmp_path, check=True, capture_output=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    assert attest_deployment(tmp_path, expected_branch="master", expected_commit=head).clean is True
    (tmp_path / "tracked.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(E2EOperationalGuardError, match="WORKTREE_DIRTY"):
        attest_deployment(tmp_path, expected_branch="master", expected_commit=head)


def test_phase_attestation_is_immutable_and_parent_bound(tmp_path: Path) -> None:
    path, digest = write_phase_attestation(
        tmp_path,
        phase="PREOPEN",
        session_date="2026-08-24",
        expected_branch="integration/test",
        expected_commit="a" * 40,
        issued_at=_at(8, 30),
    )
    assert path.is_file()
    assert digest
    assert require_phase_attestation(
        tmp_path,
        phase="PREOPEN",
        session_date="2026-08-24",
        expected_branch="integration/test",
        expected_commit="a" * 40,
        now=_at(8, 31),
    )[1] == digest
    with pytest.raises(E2EOperationalGuardError, match="PARENT_MISMATCH"):
        require_phase_attestation(
            tmp_path,
            phase="PREOPEN",
            session_date="2026-08-24",
            expected_branch="integration/test",
            expected_commit="b" * 40,
            now=_at(8, 31),
        )
    with pytest.raises(E2EOperationalGuardError, match="EXPIRED"):
        require_phase_attestation(
            tmp_path,
            phase="PREOPEN",
            session_date="2026-08-24",
            expected_branch="integration/test",
            expected_commit="a" * 40,
            now=_at(8, 46),
        )
    with pytest.raises(E2EOperationalGuardError, match="IMMUTABLE_CONFLICT"):
        write_phase_attestation(
            tmp_path,
            phase="PREOPEN",
            session_date="2026-08-24",
            expected_branch="integration/test",
            expected_commit="b" * 40,
            issued_at=_at(8, 30),
        )
