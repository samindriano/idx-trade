"""Run one cloud-first E2E PAPER stage using the existing local engines.

The GitHub job is ephemeral; durable state is the immutable R2 stage commit
and its verified runtime snapshot.  This runner performs no historical
backfill and never reads realized outcomes.  It exits successfully for an
expected waiting state so the next scheduled retry can continue the same
session, and exits non-zero for a fail-closed state.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time as clock
from typing import Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.e2e_paper_cloud_runtime_v1 import (  # noqa: E402
    CONTRACT_VERSION,
    CloudObjectStore,
    CloudInputBundle,
    CloudPaperArchive,
    CloudPaperRuntimeError,
    build_cloud_store_from_env,
    build_runtime_snapshot,
    load_schedule_from_bundle,
    materialize_official_open_from_cloud,
    OFFICIAL_OPEN_EXECUTION_END,
    restore_runtime_snapshot,
    sha256_bytes,
)
from idx_trade.e2e_paper_operational_controller_v1 import (  # noqa: E402
    OperationalControllerConfig,
    _config_missing,
)
from idx_trade.e2e_paper_operational_controller_v2 import (  # noqa: E402
    OperationalControllerConfigV2,
    run_operational_cycle_v2,
)
from idx_trade.v4_x1_clean_eod_pipeline import run_clean_eod_pipeline  # noqa: E402


JAKARTA = ZoneInfo("Asia/Jakarta")
UTC = timezone.utc
EXPECTED_WAITING = {
    "WAITING_PREOPEN_WINDOW",
    "WAITING_PREPARED_EXECUTION",
    "WAITING_PREOPEN_CA_CAPTURE",
    "WAITING_OFFICIAL_OPEN",
    "WAITING_UPSTREAM_EOD_SCORE",
    "WAITING_OFFICIAL_CALENDAR_SUCCESSOR",
    "PREOPEN_WINDOW_MISSED_NO_EXECUTION",
}
EXPECTED_TERMINAL = {
    "POST_EOD_PREPARED",
    "EXECUTION_COMPLETE",
    "ALREADY_COMPLETE",
    "MISSED_EXECUTION_NO_CERTIFIED_OPEN",
}
PREOPEN_EXECUTION_TERMINAL = {"EXECUTION_COMPLETE", "ALREADY_COMPLETE"}


def _now() -> datetime:
    return datetime.now(tz=JAKARTA)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip().lower()


def _roots() -> dict[str, Path]:
    return {
        "paper": Path(os.getenv("E2E_CLOUD_PAPER_ROOT", "/tmp/idx-trade-e2e-paper-runtime")).resolve(),
        "forward": Path(os.getenv("E2E_CLOUD_FORWARD_ROOT", "/tmp/idx-trade-e2e-forward-runtime")).resolve(),
        "official_open": Path(os.getenv("E2E_CLOUD_OFFICIAL_OPEN_ROOT", "/tmp/idx-trade-e2e-official-open")).resolve(),
        "ca": Path(os.getenv("E2E_CLOUD_CA_ROOT", "/tmp/idx-trade-e2e-ca")).resolve(),
    }


def _resolve_phase(current: datetime) -> str:
    if current.time().hour >= 18:
        return "POST_EOD"
    if (current.time().hour, current.time().minute) >= (9, 2) and current.time().hour == 9:
        return "PREOPEN"
    raise CloudPaperRuntimeError("CLOUD_E2E_OUTSIDE_SCHEDULED_PHASE_WINDOW")


def wait_for_official_open_from_cloud(
    store: CloudObjectStore,
    *,
    session_date: str,
    target_root: Path,
    expected_capture_code_ref: str,
    now_fn: Callable[[], datetime] = _now,
    sleep_fn: Callable[[float], None] = clock.sleep,
    poll_interval_seconds: float = 5.0,
    max_wait_seconds: float = 90.0,
) -> dict[str, object] | None:
    """Poll briefly for a same-window producer commit without extending PREOPEN."""

    started = now_fn()
    if started.tzinfo is None:
        raise CloudPaperRuntimeError("CLOUD_E2E_CLOCK_NOT_TIMEZONE_AWARE")
    started = started.astimezone(JAKARTA)
    hard_deadline = datetime.combine(
        started.date(), OFFICIAL_OPEN_EXECUTION_END, tzinfo=JAKARTA
    )
    wait_until = min(
        hard_deadline,
        started + timedelta(seconds=max(0.0, float(max_wait_seconds))),
    )
    while True:
        current = now_fn()
        if current.tzinfo is None:
            raise CloudPaperRuntimeError("CLOUD_E2E_CLOCK_NOT_TIMEZONE_AWARE")
        current = current.astimezone(JAKARTA)
        if current > hard_deadline:
            return None
        result = materialize_official_open_from_cloud(
            store,
            session_date=session_date,
            target_root=target_root,
            eligibility_now=current,
            expected_capture_code_ref=expected_capture_code_ref,
        )
        if result is not None:
            return result
        if current >= wait_until:
            return None
        remaining = min(
            (wait_until - current).total_seconds(),
            (hard_deadline - current).total_seconds(),
        )
        if remaining <= 0:
            return None
        sleep_fn(min(float(poll_interval_seconds), remaining))


def _controller_config(
    *,
    roots: dict[str, Path],
    roles: dict[str, Path],
    schedule_path: Path,
    now: datetime,
) -> OperationalControllerConfigV2:
    provider_raw = os.getenv("E2E_CLOUD_PROVIDER_CHECKOUT", "").strip()
    provider_commit = os.getenv("E2E_CLOUD_PROVIDER_COMMIT", "").strip().lower()
    uv = shutil.which(os.getenv("E2E_CLOUD_UV_COMMAND", "uv"))
    clean_script = REPO_ROOT / "scripts" / "capture_forward_ca_idx_bei.py"
    if not clean_script.is_file():
        raise CloudPaperRuntimeError("CLOUD_CA_CAPTURE_SCRIPT_MISSING")
    branch = os.getenv("E2E_CLOUD_EXPECTED_BRANCH", "cloud-pinned-runtime").strip()
    commit = _git_head(REPO_ROOT)
    initial_journal = roles.get("initial_journal")
    base = OperationalControllerConfig(
        runtime_root=roots["paper"],
        forward_runtime_root=roots["forward"],
        calendar_path=roots["forward"] / "forward_monitoring" / "calendar" / "exchange_sessions.csv",
        official_open_root=roots["official_open"],
        repo_root=REPO_ROOT,
        expected_branch=branch,
        expected_commit=commit,
        provider_checkout=Path(provider_raw).resolve() if provider_raw else None,
        provider_expected_commit=provider_commit or None,
        uv_exe=Path(uv).resolve() if uv else None,
        python_exe=Path(sys.executable).resolve(),
        ca_attestation_root=roots["ca"],
        ca_capture_script=clean_script.resolve(),
        ca_capture_script_sha256=_sha(clean_script),
        initial_journal_path=initial_journal.resolve() if initial_journal else None,
        initial_journal_sha256=_sha(initial_journal) if initial_journal else None,
    )
    return OperationalControllerConfigV2(
        base=base,
        execution_schedule_attestation_path=schedule_path,
        execution_schedule_attestation_sha256=_sha(schedule_path),
    )


def _result_payload(
    *,
    session: str,
    stage: str,
    started: datetime,
    finished: datetime,
    status: dict[str, object],
    official_open_admission: dict[str, object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": CONTRACT_VERSION,
        "session_date": session,
        "stage": stage,
        "observed_started_at_utc": started.astimezone(UTC).isoformat(),
        "observed_finished_at_utc": finished.astimezone(UTC).isoformat(),
        "controller_status": str(status.get("controller_status") or ""),
        "controller_result": status,
        "observed_availability_only": True,
        "outcome_accessed": False,
        "protected_forward_accessed": False,
        "model_refit": False,
    }
    if stage == "PREOPEN":
        result["official_open_cloud_admission"] = (
            dict(official_open_admission) if official_open_admission is not None else None
        )
    return result


def _require_terminal_preopen_admission(
    *,
    stage: str,
    controller_status: str,
    official_open_admission: dict[str, object] | None,
) -> None:
    """Do not durably claim a cloud PREOPEN execution without cloud admission."""

    if (
        stage == "PREOPEN"
        and controller_status in PREOPEN_EXECUTION_TERMINAL
        and official_open_admission is None
    ):
        raise CloudPaperRuntimeError(
            "CLOUD_E2E_PREOPEN_TERMINAL_WITHOUT_OFFICIAL_OPEN_ADMISSION"
        )


def run_once(*, phase: str | None = None, session_date: str | None = None) -> dict[str, object]:
    now = _now()
    if session_date:
        requested = date.fromisoformat(session_date)
        if requested != now.date():
            raise CloudPaperRuntimeError("CLOUD_E2E_RETROACTIVE_SESSION_FORBIDDEN")
        session = requested.isoformat()
    else:
        session = now.date().isoformat()
    store = build_cloud_store_from_env()
    archive = CloudPaperArchive(store)
    manifest_key = os.getenv("E2E_CLOUD_INPUT_MANIFEST_KEY", "inputs/manifest.json")
    bundle = CloudInputBundle.load(store, manifest_key)
    roots = _roots()
    input_root = Path(os.getenv("E2E_CLOUD_INPUT_ROOT", "/tmp/idx-trade-e2e-inputs")).resolve()
    roles = bundle.materialize(store, input_root)
    schedule = load_schedule_from_bundle(bundle, roles)
    if session < schedule.coverage_start or session > schedule.coverage_end:
        raise CloudPaperRuntimeError("CLOUD_E2E_SESSION_OUTSIDE_SCHEDULE_COVERAGE")

    chosen = phase or _resolve_phase(now)
    schedule_sha = _sha(roles["execution_schedule"])
    input_sha = bundle.manifest_sha256
    if session not in schedule.session_dates:
        existing = archive.existing_commit(session, "NOOP")
        if existing is not None:
            archive.verify_existing_identity(
                existing,
                schedule_attestation_sha256=schedule_sha,
                input_manifest_sha256=input_sha,
            )
            return {"status": "ALREADY_COMMITTED", "controller_status": "WEEKEND_OR_HOLIDAY_NOOP", "commit_sha256": existing.commit_sha256}
        snapshot, snapshot_sha, snapshot_meta = build_runtime_snapshot(roots)
        run_id = f"{now.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
        result = {
            "session_date": session,
            "stage": "NOOP",
            "controller_status": "WEEKEND_OR_HOLIDAY_NOOP",
            "reason": "NO_PLANNED_OFFICIAL_SESSION_TODAY",
            "observed_started_at_utc": now.astimezone(UTC).isoformat(),
            "observed_finished_at_utc": _now().astimezone(UTC).isoformat(),
            "outcome_accessed": False,
            "protected_forward_accessed": False,
            "model_refit": False,
        }
        commit = archive.commit_stage(
            session_date=session,
            stage="NOOP",
            status="WEEKEND_OR_HOLIDAY_NOOP",
            run_id=run_id,
            snapshot_bytes=snapshot,
            snapshot_sha256=snapshot_sha,
            snapshot_metadata=snapshot_meta,
            result_payload=result,
            schedule_attestation_sha256=schedule_sha,
            input_manifest_sha256=input_sha,
            code_identity={"repo": "samindriano/idx-trade", "commit": _git_head(REPO_ROOT)},
        )
        return {"status": "COMMITTED", "controller_status": "WEEKEND_OR_HOLIDAY_NOOP", "commit_sha256": commit.commit_sha256}

    if chosen not in ("POST_EOD", "PREOPEN"):
        raise CloudPaperRuntimeError("CLOUD_E2E_PHASE_INVALID")
    existing = archive.existing_commit(session, chosen)
    if existing is not None:
        archive.verify_existing_identity(
            existing,
            schedule_attestation_sha256=schedule_sha,
            input_manifest_sha256=input_sha,
        )
        return {
            "status": "ALREADY_COMMITTED",
            "controller_status": existing.status,
            "session_date": session,
            "stage": chosen,
            "commit_sha256": existing.commit_sha256,
        }

    prior = archive.latest_snapshot(schedule.session_dates, before_or_equal=session)
    if prior is not None:
        snapshot_bytes, snapshot_sha, _ = prior
        restore_runtime_snapshot(snapshot_bytes, roots, expected_sha256=snapshot_sha)
    for root in roots.values():
        root.mkdir(parents=True, exist_ok=True)

    run_id = f"{now.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    archive.record_attempt(
        session_date=session,
        stage=chosen,
        run_id=run_id,
        payload={
            "contract_version": CONTRACT_VERSION,
            "status": "STARTED",
            "schedule_attestation_sha256": schedule_sha,
            "input_manifest_sha256": input_sha,
            "outcome_accessed": False,
            "protected_forward_accessed": False,
            "model_refit": False,
        },
    )

    config = _controller_config(
        roots=roots,
        roles=roles,
        schedule_path=roles["execution_schedule"],
        now=now,
    )
    missing_config = _config_missing(config.base)
    if missing_config:
        raise CloudPaperRuntimeError("CLOUD_OPERATIONAL_PREREQUISITE:" + missing_config)

    official_open_admission: dict[str, object] | None = None
    if chosen == "PREOPEN":
        official_env = dict(os.environ)
        official_env["E2E_CLOUD_STORAGE_PREFIX"] = os.getenv(
            "E2E_CLOUD_OFFICIAL_OPEN_PREFIX", "official-open-v1"
        )
        official_store = build_cloud_store_from_env(official_env)
        official_open_admission = wait_for_official_open_from_cloud(
            official_store,
            session_date=session,
            target_root=roots["official_open"],
            expected_capture_code_ref=os.getenv(
                "E2E_CLOUD_EXPECTED_OFFICIAL_OPEN_CAPTURE_CODE_REF", ""
            ),
        )

    effective_now = _now()
    started = effective_now
    if chosen == "POST_EOD":
        model_root = roles["model_manifest"].parent
        pipeline_kwargs = {
            "clean_panel": roles["clean_panel"],
            "clean_security_master": roles["clean_security_master"],
            "repo_root": REPO_ROOT,
            "observed_by": effective_now.astimezone(UTC).isoformat(),
        }
        # The V2 adapter consumes the cloud input hash at the outer runtime
        # boundary.  Direct V1 remains byte/signature compatible with the
        # frozen clean pipeline and therefore receives no adapter-only field.
        parameters = inspect.signature(run_clean_eod_pipeline).parameters
        if any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()):
            pipeline_kwargs["population_input_manifest_sha256"] = input_sha
        run_clean_eod_pipeline(
            roots["forward"],
            model_root,
            **pipeline_kwargs,
        )
    status = run_operational_cycle_v2(config, now=effective_now)
    finished = _now()
    controller_status = str(status.get("controller_status") or "FAIL_CLOSED")
    _require_terminal_preopen_admission(
        stage=chosen,
        controller_status=controller_status,
        official_open_admission=official_open_admission,
    )
    result = _result_payload(
        session=session,
        stage=chosen,
        started=started,
        finished=finished,
        status=status,
        official_open_admission=official_open_admission,
    )
    if controller_status in EXPECTED_TERMINAL:
        snapshot, snapshot_sha, snapshot_meta = build_runtime_snapshot(roots)
        commit = archive.commit_stage(
            session_date=session,
            stage=chosen,
            status=controller_status,
            run_id=run_id,
            snapshot_bytes=snapshot,
            snapshot_sha256=snapshot_sha,
            snapshot_metadata=snapshot_meta,
            result_payload=result,
            schedule_attestation_sha256=schedule_sha,
            input_manifest_sha256=input_sha,
            code_identity={
                "repo": "samindriano/idx-trade",
                "commit": _git_head(REPO_ROOT),
                "runner_sha256": _sha(Path(__file__).resolve()),
            },
        )
        result.update({"status": "COMMITTED", "commit_sha256": commit.commit_sha256, "snapshot_sha256": snapshot_sha})
        return result
    archive.record_attempt(
        session_date=session,
        stage=chosen,
        run_id=run_id + "-result",
        payload={"status": controller_status, "result": result},
    )
    result["status"] = "WAITING" if controller_status in EXPECTED_WAITING else "FAILED"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("auto", "POST_EOD", "PREOPEN"), default="auto")
    parser.add_argument("--session-date")
    args = parser.parse_args()
    try:
        result = run_once(
            phase=None if args.phase == "auto" else args.phase,
            session_date=args.session_date,
        )
    except Exception as exc:
        result = {
            "status": "FAILED",
            "controller_status": "FAIL_CLOSED",
            "error_code": type(exc).__name__.upper(),
            "error_message": str(exc),
            "outcome_accessed": False,
            "protected_forward_accessed": False,
            "model_refit": False,
        }
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if result.get("status") in {"COMMITTED", "ALREADY_COMMITTED", "WAITING"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
