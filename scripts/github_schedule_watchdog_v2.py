"""Trusted-dispatch successor for the GitHub schedule watchdog.

All V1 scheduling, slot windows, coverage checks, markers, and non-Official-Open
behavior remain unchanged.  Only Official Open workflow_dispatch requests are
augmented with the HMAC attestation required by the recovery producer.

The signing key is read from the watchdog process environment and is never
placed on the gh command line, marker files, events, or child environment.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import hashlib
import hmac
import json
import os
import secrets
from typing import Callable, Iterator, Sequence

from scripts import github_schedule_watchdog as v1


ATTESTATION_SCHEMA = "idx_official_open_external_scheduler_attestation_v1"
SIGNING_KEY_ENV = "OFFICIAL_OPEN_SCHEDULER_HMAC_KEY"
OFFICIAL_OPEN_WORKFLOW = "official-open-prospective-cloud-capture.yml"


Runner = Callable[[Sequence[str]], tuple[int, str]]


def _default_runner_v2(command: Sequence[str]) -> tuple[int, str]:
    """Delegate to subprocess with all market/archive/signing secrets removed."""

    child_env = dict(os.environ)
    for key in (
        "ZAPI_API_KEY",
        "IDX_API_KEY",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "STOCKBIT_STREAM_AUTHOR_HMAC_KEY",
        SIGNING_KEY_ENV,
    ):
        child_env.pop(key, None)

    import subprocess

    completed = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
        env=child_env,
    )
    return completed.returncode, completed.stdout


def _issued_at_utc(current: datetime) -> str:
    if current.tzinfo is None:
        raise v1.WatchdogError("WATCHDOG_NOW_MUST_BE_TIMEZONE_AWARE")
    return current.astimezone(v1.UTC).replace(microsecond=0).isoformat()


def _official_open_attestation_fields(
    *,
    repository: str,
    slot: v1.Slot,
    session_date: str,
    current: datetime,
    signing_key: str,
    nonce: str,
) -> dict[str, str]:
    if repository != v1.DEFAULT_REPOSITORY:
        raise v1.WatchdogError("OFFICIAL_OPEN_ATTESTATION_REPOSITORY_INVALID")
    if slot.workflow_file != OFFICIAL_OPEN_WORKFLOW or slot.input_name != "slot":
        raise v1.WatchdogError("OFFICIAL_OPEN_ATTESTATION_SLOT_INVALID")
    if slot.input_value not in {"0902", "0912", "0922"}:
        raise v1.WatchdogError("OFFICIAL_OPEN_ATTESTATION_SLOT_INVALID")
    if not signing_key:
        raise v1.WatchdogError("OFFICIAL_OPEN_SCHEDULER_HMAC_KEY_MISSING")
    if not v1.re.fullmatch(r"[A-Za-z0-9_-]{16,128}", nonce):
        raise v1.WatchdogError("OFFICIAL_OPEN_ATTESTATION_NONCE_INVALID")

    issued_at = _issued_at_utc(current)
    body = {
        "schema_version": ATTESTATION_SCHEMA,
        "repository": repository,
        "session_date": session_date,
        "slot": slot.input_value,
        "issued_at_utc": issued_at,
        "nonce": nonce,
    }
    canonical = json.dumps(
        body,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    signature = hmac.new(signing_key.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    return {
        "session_date": session_date,
        "scheduler_issued_at": issued_at,
        "scheduler_nonce": nonce,
        "scheduler_signature": signature,
    }


def _dispatch_v2(
    *,
    runner: Runner,
    repository: str,
    slot: v1.Slot,
    gh_exe: str | None,
    current: datetime,
    nonce_factory: Callable[[], str] = lambda: secrets.token_urlsafe(24),
) -> int:
    gh = gh_exe or v1.shutil.which("gh") or "gh"
    command = [
        gh,
        "workflow",
        "run",
        slot.workflow_file,
        "--repo",
        repository,
        "--ref",
        "main",
        "--field",
        f"{slot.input_name}={slot.input_value}",
    ]

    if slot.workflow_file == OFFICIAL_OPEN_WORKFLOW:
        signing_key = os.environ.get(SIGNING_KEY_ENV, "")
        try:
            fields = _official_open_attestation_fields(
                repository=repository,
                slot=slot,
                session_date=current.astimezone(v1.JAKARTA).date().isoformat(),
                current=current,
                signing_key=signing_key,
                nonce=nonce_factory(),
            )
        except v1.WatchdogError:
            # Preserve V1's per-slot FAIL_CLOSED_DISPATCH result shape without
            # invoking gh when a trusted proof cannot be produced.
            return 97
        for name in (
            "session_date",
            "scheduler_issued_at",
            "scheduler_nonce",
            "scheduler_signature",
        ):
            command.extend(["--field", f"{name}={fields[name]}"])
    elif slot.workflow_file == "e2e-paper-cloud-orchestration.yml":
        command.extend(["--field", f"trigger_slot={slot.slot_id}"])

    return_code, _ = runner(command)
    return return_code


@contextmanager
def _patched_dispatch(current: datetime) -> Iterator[None]:
    original = v1._dispatch

    def bound_dispatch(*, runner, repository, slot, gh_exe):
        return _dispatch_v2(
            runner=runner,
            repository=repository,
            slot=slot,
            gh_exe=gh_exe,
            current=current,
        )

    v1._dispatch = bound_dispatch
    try:
        yield
    finally:
        v1._dispatch = original


def run_once(
    *,
    repository: str = v1.DEFAULT_REPOSITORY,
    state_root=v1.DEFAULT_STATE_ROOT,
    now: datetime | None = None,
    runner: Runner | None = None,
    gh_exe: str | None = None,
):
    current = (now or datetime.now(v1.JAKARTA)).astimezone(v1.JAKARTA)
    safe_runner = runner or _default_runner_v2
    with _patched_dispatch(current):
        return v1.run_once(
            repository=repository,
            state_root=state_root,
            now=current,
            runner=safe_runner,
            gh_exe=gh_exe,
        )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=v1.DEFAULT_REPOSITORY)
    parser.add_argument("--state-root", type=v1.Path, default=v1.DEFAULT_STATE_ROOT)
    parser.add_argument("--gh-exe", help="Absolute gh executable path for scheduled execution")
    parser.add_argument("--now", help="Timezone-aware ISO timestamp; test-only override")
    args = parser.parse_args()
    result = run_once(
        repository=args.repo,
        state_root=args.state_root,
        now=v1._parse_now(args.now),
        gh_exe=args.gh_exe,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if all(
        action.get("status") not in {"FAIL_CLOSED_QUERY", "FAIL_CLOSED_DISPATCH"}
        for action in result["actions"]
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
