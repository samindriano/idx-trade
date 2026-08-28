"""Dispatch existing cloud workflows when a native schedule run is absent.

This is a trigger watchdog only.  It never calls IDX, Zapi, Stockbit, R2, or
any capture/runtime code.  GitHub CLI authentication is deliberately resolved
by ``gh`` itself; no token is accepted as a command-line argument or written
to the watchdog state.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Mapping, Sequence


UTC = timezone.utc
JAKARTA = timezone(timedelta(hours=7), name="Asia/Jakarta")
DEFAULT_REPOSITORY = "samindriano/idx-trade"
DEFAULT_STATE_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "IDXTrade" / "github_schedule_watchdog_v1"
WATCHDOG_SCHEMA = "idx_trade_github_schedule_watchdog_v1"
SLOT_RUN_NAME_PREFIX = "IDX-SLOT:"
# Keep the lower bound narrow enough that a prior phase of the same workflow
# (for example E2E POST_EOD 18:35 versus 19:05) cannot masquerade as coverage
# for the current slot. A delayed run is still observed because its created_at
# is after the current slot's due time.
RUN_LOOKBACK = timedelta(minutes=2)
LATE_GRACE = timedelta(hours=2)


@dataclass(frozen=True)
class Slot:
    slot_id: str
    due_local: time
    workflow_file: str
    workflow_id: str
    input_name: str
    input_value: str
    latest_local: time | None = None

    def window_end(self, day: date) -> datetime:
        if self.latest_local is not None:
            return datetime.combine(day, self.latest_local, tzinfo=JAKARTA)
        return _slot_due(day, self) + LATE_GRACE


SLOTS: tuple[Slot, ...] = (
    # Morning fallback checks are deliberately short-lived.  In particular,
    # PREOPEN_CA is never dispatched at or after the existing 09:02 WIB hard
    # cutoff; a later logon cannot turn it into a retroactive capture.
    Slot(
        "E2E_PREOPEN_CA_0830",
        time(8, 30),
        "e2e-paper-cloud-orchestration.yml",
        "e2e-paper-cloud-orchestration.yml",
        "phase",
        "PREOPEN_CA",
        latest_local=time(8, 39),
    ),
    Slot(
        "E2E_PREOPEN_CA_0845",
        time(8, 45),
        "e2e-paper-cloud-orchestration.yml",
        "e2e-paper-cloud-orchestration.yml",
        "phase",
        "PREOPEN_CA",
        latest_local=time(8, 54),
    ),
    Slot(
        "E2E_PREOPEN_CA_0855",
        time(8, 55),
        "e2e-paper-cloud-orchestration.yml",
        "e2e-paper-cloud-orchestration.yml",
        "phase",
        "PREOPEN_CA",
        latest_local=time(9, 2),
    ),
    Slot(
        "OFFICIAL_OPEN_0902",
        time(9, 2),
        "official-open-prospective-cloud-capture.yml",
        "official-open-prospective-cloud-capture.yml",
        "slot",
        "0902",
        latest_local=time(9, 8),
    ),
    Slot(
        "E2E_PREOPEN_0903",
        time(9, 3),
        "e2e-paper-cloud-orchestration.yml",
        "e2e-paper-cloud-orchestration.yml",
        "phase",
        "PREOPEN",
        latest_local=time(9, 9),
    ),
    Slot(
        "OFFICIAL_OPEN_0912",
        time(9, 12),
        "official-open-prospective-cloud-capture.yml",
        "official-open-prospective-cloud-capture.yml",
        "slot",
        "0912",
        latest_local=time(9, 18),
    ),
    Slot(
        "E2E_PREOPEN_0913",
        time(9, 13),
        "e2e-paper-cloud-orchestration.yml",
        "e2e-paper-cloud-orchestration.yml",
        "phase",
        "PREOPEN",
        latest_local=time(9, 19),
    ),
    Slot(
        "OFFICIAL_OPEN_0922",
        time(9, 22),
        "official-open-prospective-cloud-capture.yml",
        "official-open-prospective-cloud-capture.yml",
        "slot",
        "0922",
        latest_local=time(9, 23),
    ),
    Slot(
        "E2E_PREOPEN_0922",
        time(9, 22),
        "e2e-paper-cloud-orchestration.yml",
        "e2e-paper-cloud-orchestration.yml",
        "phase",
        "PREOPEN",
        latest_local=time(9, 23),
    ),
    Slot(
        "STOCKBIT_INTRADAY_1830",
        time(18, 30),
        "stockbit-intraday-cloud-production.yml",
        "stockbit-intraday-cloud-production.yml",
        "slot",
        "1830",
    ),
    Slot(
        "E2E_POST_EOD_1835",
        time(18, 35),
        "e2e-paper-cloud-orchestration.yml",
        "e2e-paper-cloud-orchestration.yml",
        "phase",
        "POST_EOD",
    ),
    Slot(
        "E2E_POST_EOD_1905",
        time(19, 5),
        "e2e-paper-cloud-orchestration.yml",
        "e2e-paper-cloud-orchestration.yml",
        "phase",
        "POST_EOD",
    ),
    Slot(
        "STOCKBIT_INTRADAY_1930",
        time(19, 30),
        "stockbit-intraday-cloud-production.yml",
        "stockbit-intraday-cloud-production.yml",
        "slot",
        "1930",
    ),
    Slot(
        "E2E_POST_EOD_1935",
        time(19, 35),
        "e2e-paper-cloud-orchestration.yml",
        "e2e-paper-cloud-orchestration.yml",
        "phase",
        "POST_EOD",
    ),
    Slot(
        "STOCKBIT_INTRADAY_2030",
        time(20, 30),
        "stockbit-intraday-cloud-production.yml",
        "stockbit-intraday-cloud-production.yml",
        "slot",
        "2030",
    ),
)


class WatchdogError(RuntimeError):
    """Fail-closed watchdog error."""


Runner = Callable[[Sequence[str]], tuple[int, str]]


def _default_runner(command: Sequence[str]) -> tuple[int, str]:
    child_env = dict(os.environ)
    for key in (
        "ZAPI_API_KEY",
        "IDX_API_KEY",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "STOCKBIT_STREAM_AUTHOR_HMAC_KEY",
    ):
        child_env.pop(key, None)
    completed = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
        env=child_env,
    )
    # Never persist or print command output.  gh owns credential handling and
    # may redact its own diagnostics, but the watchdog has no reason to keep it.
    return completed.returncode, completed.stdout


def _parse_now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(JAKARTA)
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise WatchdogError("WATCHDOG_NOW_MUST_BE_TIMEZONE_AWARE")
    return parsed.astimezone(JAKARTA)


def _slot_due(day: date, slot: Slot) -> datetime:
    return datetime.combine(day, slot.due_local, tzinfo=JAKARTA)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slot_key(day: date, slot: Slot) -> str:
    return f"{day.isoformat()}__{slot.slot_id}"


def _marker_path(state_root: Path, day: date, slot: Slot) -> Path:
    return state_root / "dispatch_markers" / f"{_slot_key(day, slot)}.json"


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
    temporary.replace(path)


def _append_event(state_root: Path, payload: Mapping[str, Any]) -> None:
    state_root.mkdir(parents=True, exist_ok=True)
    event_path = state_root / "events.jsonl"
    with event_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def _has_exact_slot_run_name(row: Mapping[str, Any], slot_id: str) -> bool:
    """Return whether GitHub's run-name metadata contains this exact slot token."""

    expected = f"{SLOT_RUN_NAME_PREFIX}{slot_id}"
    pattern = re.compile(
        rf"(?:^|[^A-Za-z0-9_]){re.escape(expected)}(?:$|[^A-Za-z0-9_])"
    )
    return any(
        isinstance(row.get(field), str) and pattern.search(row[field])
        for field in ("display_title", "run_name", "runName")
    )


def _is_production_main_run(row: Mapping[str, Any]) -> bool:
    """Require an explicit production main branch or ref identity."""

    branch = row.get("head_branch")
    branch = branch.strip() if isinstance(branch, str) else None
    ref = row.get("ref")
    ref = ref.strip() if isinstance(ref, str) else None
    valid_refs = {"main", "refs/heads/main"}
    if branch is not None and branch != "main":
        return False
    if ref is not None and ref not in valid_refs:
        return False
    return branch == "main" or ref in valid_refs


def _parse_created_at(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(JAKARTA)


def _exact_slot_runs(
    *,
    runs: Sequence[Mapping[str, Any]],
    slot: Slot,
    due: datetime,
    observation: datetime | None = None,
) -> list[dict[str, Any]]:
    cutoff = slot.window_end(due.date())
    observed = observation.astimezone(JAKARTA) if observation is not None else None
    exact: list[dict[str, Any]] = []
    for row in runs:
        if row.get("event") not in {"schedule", "workflow_dispatch"}:
            continue
        if not _is_production_main_run(row):
            continue
        if not _has_exact_slot_run_name(row, slot.slot_id):
            continue
        created = _parse_created_at(row.get("created_at"))
        if created is None or created < due or created >= cutoff:
            continue
        if observed is not None and created > observed:
            continue
        exact.append(dict(row))
    return exact


def _query_runs(
    *, runner: Runner, repository: str, slot: Slot, due: datetime, now: datetime, gh_exe: str | None
) -> list[dict[str, Any]]:
    start = due - RUN_LOOKBACK
    cutoff = slot.window_end(due.date())
    end = min(now, cutoff)
    if end < start:
        return []
    gh = gh_exe or shutil.which("gh") or "gh"
    command = [
        gh,
        "api",
        f"repos/{repository}/actions/workflows/{slot.workflow_id}/runs",
        "--method",
        "GET",
        "-f",
        "per_page=100",
        "-f",
        f"created={_iso_utc(start)}..{_iso_utc(end)}",
    ]
    return_code, stdout = runner(command)
    if return_code != 0:
        raise WatchdogError(f"GITHUB_RUN_QUERY_FAILED:{slot.slot_id}:{return_code}")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise WatchdogError(f"GITHUB_RUN_QUERY_INVALID_JSON:{slot.slot_id}") from exc
    rows = payload.get("workflow_runs")
    if not isinstance(rows, list):
        raise WatchdogError(f"GITHUB_RUN_QUERY_MISSING_LIST:{slot.slot_id}")
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        created = _parse_created_at(row.get("created_at"))
        if created is None:
            continue
        if not (start <= created <= end):
            continue
        result.append(
            {
                "id": row.get("id"),
                "event": row.get("event"),
                "status": row.get("status"),
                "conclusion": row.get("conclusion"),
                "created_at": row.get("created_at"),
                "display_title": row.get("display_title"),
                "run_name": row.get("run_name"),
                "runName": row.get("runName"),
                "head_branch": row.get("head_branch"),
                "ref": row.get("ref"),
            }
        )
    return result


def _dispatch(
    *, runner: Runner, repository: str, slot: Slot, gh_exe: str | None
) -> int:
    gh = gh_exe or shutil.which("gh") or "gh"
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
    if slot.workflow_file == "e2e-paper-cloud-orchestration.yml":
        command.extend(["--field", f"trigger_slot={slot.slot_id}"])
    return_code, _ = runner(command)
    return return_code


def run_once(
    *,
    repository: str = DEFAULT_REPOSITORY,
    state_root: Path = DEFAULT_STATE_ROOT,
    now: datetime | None = None,
    runner: Runner | None = None,
    gh_exe: str | None = None,
) -> dict[str, Any]:
    """Perform one current-day trigger check without touching market data."""

    current = (now or datetime.now(JAKARTA)).astimezone(JAKARTA)
    if current.weekday() >= 5:
        result = {
            "schema_version": WATCHDOG_SCHEMA,
            "status": "NON_TRADING_WEEKEND_NO_DISPATCH",
            "observed_at_utc": datetime.now(UTC).isoformat(),
            "current_session_date": current.date().isoformat(),
            "actions": [],
            "provider_calls": 0,
            "protected_outcomes_accessed": False,
        }
        _append_event(state_root, result)
        return result

    run = runner or _default_runner
    actions: list[dict[str, Any]] = []
    for slot in SLOTS:
        due = _slot_due(current.date(), slot)
        if not (due <= current < slot.window_end(current.date())):
            continue
        marker = _marker_path(state_root, current.date(), slot)
        try:
            existing = _query_runs(
                runner=run,
                repository=repository,
                slot=slot,
                due=due,
                now=current,
                gh_exe=gh_exe,
            )
        except WatchdogError as exc:
            action = {
                "slot": slot.slot_id,
                "status": "FAIL_CLOSED_QUERY",
                "error": str(exc),
            }
            actions.append(action)
            _append_event(
                state_root,
                {
                    "schema_version": WATCHDOG_SCHEMA,
                    "observed_at_utc": datetime.now(UTC).isoformat(),
                    "current_session_date": current.date().isoformat(),
                    **action,
                    "provider_calls": 0,
                    "protected_outcomes_accessed": False,
                },
            )
            continue

        exact = _exact_slot_runs(
            runs=existing, slot=slot, due=due, observation=current
        )
        if exact:
            action = {
                "slot": slot.slot_id,
                "status": "ALREADY_COVERED",
                "run_ids": [row.get("id") for row in exact],
                "run_events": [row.get("event") for row in exact],
                "run_names": [
                    next(
                        (
                            row.get(field)
                            for field in ("display_title", "run_name", "runName")
                            if isinstance(row.get(field), str)
                        ),
                        None,
                    )
                    for row in exact
                ],
                "run_metadata": [
                    {
                        "id": row.get("id"),
                        "event": row.get("event"),
                        "display_title": row.get("display_title"),
                        "run_name": row.get("run_name"),
                        "runName": row.get("runName"),
                        "created_at": row.get("created_at"),
                        "head_branch": row.get("head_branch"),
                        "ref": row.get("ref"),
                    }
                    for row in exact
                ],
            }
            actions.append(action)
            continue

        if marker.exists():
            action = {
                "slot": slot.slot_id,
                "status": "DISPATCH_ALREADY_REQUESTED_NO_VISIBLE_RUN",
            }
            actions.append(action)
            _append_event(
                state_root,
                {
                    "schema_version": WATCHDOG_SCHEMA,
                    "observed_at_utc": datetime.now(UTC).isoformat(),
                    "current_session_date": current.date().isoformat(),
                    **action,
                    "provider_calls": 0,
                    "protected_outcomes_accessed": False,
                },
            )
            continue

        return_code = _dispatch(runner=run, repository=repository, slot=slot, gh_exe=gh_exe)
        if return_code != 0:
            action = {
                "slot": slot.slot_id,
                "status": "FAIL_CLOSED_DISPATCH",
                "dispatch_exit_code": return_code,
            }
            actions.append(action)
            _append_event(
                state_root,
                {
                    "schema_version": WATCHDOG_SCHEMA,
                    "observed_at_utc": datetime.now(UTC).isoformat(),
                    "current_session_date": current.date().isoformat(),
                    **action,
                    "provider_calls": 0,
                    "protected_outcomes_accessed": False,
                },
            )
            continue

        marker_payload = {
            "schema_version": WATCHDOG_SCHEMA,
            "status": "DISPATCH_REQUESTED",
            "repository": repository,
            "slot": slot.slot_id,
            "session_date": current.date().isoformat(),
            "workflow": slot.workflow_file,
            "input_name": slot.input_name,
            "input_value": slot.input_value,
            "requested_at_utc": datetime.now(UTC).isoformat(),
            "provider_calls": 0,
            "protected_outcomes_accessed": False,
        }
        _write_json_atomic(marker, marker_payload)
        action = {
            "slot": slot.slot_id,
            "status": "DISPATCH_REQUESTED_AMBIGUOUS_RUN" if existing else "DISPATCH_REQUESTED",
            "workflow": slot.workflow_file,
            "input_name": slot.input_name,
            "input_value": slot.input_value,
        }
        if existing:
            action["ambiguous_run_ids"] = [row.get("id") for row in existing]
        actions.append(action)
        _append_event(
            state_root,
            {
                "schema_version": WATCHDOG_SCHEMA,
                "observed_at_utc": datetime.now(UTC).isoformat(),
                "current_session_date": current.date().isoformat(),
                **action,
                "provider_calls": 0,
                "protected_outcomes_accessed": False,
            },
        )

    status = "NO_DUE_SLOTS" if not actions else "TRIGGER_CHECK_COMPLETE"
    result = {
        "schema_version": WATCHDOG_SCHEMA,
        "status": status,
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "current_session_date": current.date().isoformat(),
        "actions": actions,
        "provider_calls": 0,
        "protected_outcomes_accessed": False,
    }
    _append_event(state_root, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPOSITORY)
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT)
    parser.add_argument("--gh-exe", help="Absolute gh executable path for scheduled execution")
    parser.add_argument("--now", help="Timezone-aware ISO timestamp; test-only override")
    args = parser.parse_args()
    result = run_once(
        repository=args.repo,
        state_root=args.state_root,
        now=_parse_now(args.now),
        gh_exe=args.gh_exe,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if all(action.get("status") not in {"FAIL_CLOSED_QUERY", "FAIL_CLOSED_DISPATCH"} for action in result["actions"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
