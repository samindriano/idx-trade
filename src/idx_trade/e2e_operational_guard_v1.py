"""Fail-closed operational guards for the controlled E2E paper runtime.

This module does not capture market data, open outcomes, or run a model.  It
only protects the existing E2E entrypoints from stale phase execution,
mutable-checkout deployment, and concurrent runtime transactions.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Iterable, Iterator, Mapping
from uuid import uuid4
from zoneinfo import ZoneInfo


JAKARTA = ZoneInfo("Asia/Jakarta")
PREOPEN_START = time(9, 2)
PREOPEN_END = time(9, 22, 59)
POST_EOD_START = time(18, 0)
SCHEMA_VERSION = "idx_trade_e2e_operational_guard_v1"


class E2EOperationalGuardError(RuntimeError):
    """Raised when an operational safety invariant is not proven."""


@dataclass(frozen=True)
class DeploymentAttestation:
    repo_root: Path
    branch: str
    head: str
    expected_branch: str
    expected_commit: str
    clean: bool


@dataclass(frozen=True)
class PhaseWindow:
    phase: str
    session_date: str
    now_jakarta: str
    status: str


def _local_now(value: datetime | None) -> datetime:
    current = value or datetime.now(tz=JAKARTA)
    if current.tzinfo is None:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CLOCK_MUST_BE_TIMEZONE_AWARE")
    return current.astimezone(JAKARTA)


def _iso_date(value: object) -> str:
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_SESSION_DATE_INVALID") from exc
    return parsed.isoformat()


def _run_git(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise E2EOperationalGuardError("E2E_DEPLOYMENT_GIT_ATTESTATION_FAILED") from exc
    return completed.stdout.strip()


def attest_deployment(
    repo_root: str | Path,
    *,
    expected_branch: str,
    expected_commit: str,
) -> DeploymentAttestation:
    """Require the exact clean source identity before operational work."""

    root = Path(repo_root).expanduser().resolve()
    if not root.is_dir():
        raise E2EOperationalGuardError("E2E_DEPLOYMENT_REPO_MISSING")
    branch = _run_git(root, "branch", "--show-current")
    head = _run_git(root, "rev-parse", "HEAD").lower()
    dirty = _run_git(root, "status", "--porcelain")
    expected = str(expected_commit).strip().lower()
    if branch != str(expected_branch).strip():
        raise E2EOperationalGuardError("E2E_DEPLOYMENT_BRANCH_MISMATCH")
    if head != expected:
        raise E2EOperationalGuardError("E2E_DEPLOYMENT_COMMIT_MISMATCH")
    if dirty:
        raise E2EOperationalGuardError("E2E_DEPLOYMENT_WORKTREE_DIRTY")
    return DeploymentAttestation(root, branch, head, str(expected_branch), expected, True)


def load_session_dates(path: str | Path) -> tuple[str, ...]:
    """Load the exact date column from the already-attested official calendar."""

    calendar = Path(path).expanduser().resolve()
    if not calendar.is_file():
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CALENDAR_MISSING")
    lines = [line.strip() for line in calendar.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines or lines[0].lower() not in {"date", "session_date"}:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CALENDAR_SCHEMA_INVALID")
    values = tuple(sorted({_iso_date(line.split(",", 1)[0]) for line in lines[1:]}))
    if not values:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_CALENDAR_EMPTY")
    return values


def require_phase_window(
    *,
    phase: str,
    session_date: str,
    official_session_dates: Iterable[str],
    now: datetime | None = None,
) -> PhaseWindow:
    """Prove a same-day phase window before a consumer can execute."""

    current = _local_now(now)
    session = _iso_date(session_date)
    sessions = {_iso_date(value) for value in official_session_dates}
    if session not in sessions:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_SESSION_NOT_IN_OFFICIAL_CALENDAR")
    if current.date().isoformat() != session:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_NOT_SAME_JAKARTA_DATE")
    if phase == "PREOPEN":
        if current.time() < PREOPEN_START:
            raise E2EOperationalGuardError("E2E_PREOPEN_TOO_EARLY")
        if current.time() > PREOPEN_END:
            raise E2EOperationalGuardError("E2E_PREOPEN_WINDOW_MISSED")
    elif phase == "POST_EOD":
        if current.time() < POST_EOD_START:
            raise E2EOperationalGuardError("E2E_POST_EOD_TOO_EARLY")
    else:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_PHASE_INVALID")
    return PhaseWindow(phase, session, current.isoformat(), "PASS")


@contextmanager
def exclusive_run_lock(path: str | Path) -> Iterator[None]:
    """Hold an OS-level one-byte lock; crashes release it automatically."""

    lock_path = Path(path).expanduser().resolve()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            handle.write(b"0")
            handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise E2EOperationalGuardError("E2E_OPERATIONAL_RUN_ALREADY_IN_PROGRESS") from exc
        else:  # pragma: no cover - Windows is the deployment platform.
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise E2EOperationalGuardError("E2E_OPERATIONAL_RUN_ALREADY_IN_PROGRESS") from exc
        yield
    finally:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:  # pragma: no cover
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def write_status_atomic(path: str | Path, payload: Mapping[str, object]) -> str:
    """Persist a redacted operational status without partial final files."""

    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    body = {"schema_version": SCHEMA_VERSION, **dict(payload)}
    encoded = (json.dumps(body, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    temporary.write_bytes(encoded)
    os.replace(temporary, target)
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "DeploymentAttestation",
    "E2EOperationalGuardError",
    "JAKARTA",
    "PhaseWindow",
    "POST_EOD_START",
    "PREOPEN_END",
    "PREOPEN_START",
    "attest_deployment",
    "exclusive_run_lock",
    "load_session_dates",
    "require_phase_window",
    "write_status_atomic",
]
