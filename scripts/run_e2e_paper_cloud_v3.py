"""Cloud E2E PAPER V3 adapter with durable pre-09:02 CA continuity.

V2 remains the POST_EOD security-master remediation. V3 adds only operational
continuity needed by fresh GitHub runners:

* PREOPEN_CA is an immutable pre-09:02 checkpoint, not an execution stage.
* PREOPEN restores that checkpoint before admitting Official Open/executing.
* T0 remains anchored to the original bootstrap session on later POST_EOD days.

No model, score, sizing, execution, outcome, or retroactive rule is changed.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade import e2e_paper_operational_controller_v2 as controller_v2  # noqa: E402
from idx_trade.e2e_paper_cloud_runtime_v1 import (  # noqa: E402
    CloudInputBundle,
    CloudPaperRuntimeError,
    build_runtime_snapshot,
    restore_runtime_snapshot,
)
from idx_trade.e2e_paper_preopen_ca_cloud_v1 import (  # noqa: E402
    CHECKPOINT_STAGE,
    CHECKPOINT_STATUS,
    commit_preopen_ca_checkpoint,
    load_preopen_ca_checkpoint,
    run_preopen_ca_cycle,
    validate_existing_t0_or_bootstrap,
)
from scripts import run_e2e_paper_cloud_v1 as v1  # noqa: E402
from scripts import run_e2e_paper_cloud_v2 as v2  # noqa: E402


UTC = timezone.utc


def _schedule_ref_sha(bundle: CloudInputBundle) -> str:
    ref = next((row for row in bundle.refs if row.role == "execution_schedule"), None)
    if ref is None:
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_SCHEDULE_ROLE_MISSING")
    return ref.sha256


@contextmanager
def _patched_v1_continuity() -> Iterator[None]:
    """Make V2 checkpoint-aware without changing the accepted V1/V2 modules."""

    original_archive = v1.CloudPaperArchive
    original_controller = v1.run_operational_cycle_v2
    original_bootstrap = controller_v2.bootstrap_t0

    class CheckpointAwareArchive(original_archive):
        def latest_snapshot(self, planned_sessions, *, before_or_equal):  # type: ignore[override]
            standard = super().latest_snapshot(
                planned_sessions,
                before_or_equal=before_or_equal,
            )
            session = date.fromisoformat(before_or_equal).isoformat()
            if session not in set(planned_sessions):
                return standard
            manifest_key = os.getenv("E2E_CLOUD_INPUT_MANIFEST_KEY", "inputs/manifest.json")
            bundle = CloudInputBundle.load(self.store, manifest_key)
            checkpoint = load_preopen_ca_checkpoint(
                self.store,
                session_date=session,
                expected_schedule_sha256=_schedule_ref_sha(bundle),
                expected_input_manifest_sha256=bundle.manifest_sha256,
                expected_code_commit=v1._git_head(v1.REPO_ROOT),
            )
            if checkpoint is None:
                return standard
            if standard is not None:
                standard_payload = standard[2]
                if (
                    str(standard_payload.get("session_date") or "") == session
                    and str(standard_payload.get("stage") or "") in {"PREOPEN", "POST_EOD"}
                ):
                    return standard
            return (
                checkpoint.snapshot_bytes,
                checkpoint.snapshot_sha256,
                checkpoint.payload,
            )

    def controller_adapter(config, *, now=None):
        def stable_bootstrap(runtime_root, *, session_date, initial_nav_idr=None):
            kwargs = {}
            if initial_nav_idr is not None:
                kwargs["initial_nav_idr"] = initial_nav_idr

            def original(root, *, session_date):
                return original_bootstrap(root, session_date=session_date, **kwargs)

            return validate_existing_t0_or_bootstrap(
                runtime_root,
                session_date=session_date,
                original_bootstrap=original,
            )

        controller_v2.bootstrap_t0 = stable_bootstrap
        try:
            return original_controller(config, now=now)
        finally:
            controller_v2.bootstrap_t0 = original_bootstrap

    v1.CloudPaperArchive = CheckpointAwareArchive
    v1.run_operational_cycle_v2 = controller_adapter
    try:
        yield
    finally:
        v1.CloudPaperArchive = original_archive
        v1.run_operational_cycle_v2 = original_controller
        controller_v2.bootstrap_t0 = original_bootstrap


def _run_preopen_ca_once(*, session_date: str | None = None) -> dict[str, object]:
    now = v1._now()
    session = now.date().isoformat()
    if session_date:
        requested = date.fromisoformat(session_date).isoformat()
        if requested != session:
            raise CloudPaperRuntimeError("CLOUD_E2E_RETROACTIVE_SESSION_FORBIDDEN")
        session = requested

    store = v1.build_cloud_store_from_env()
    manifest_key = os.getenv("E2E_CLOUD_INPUT_MANIFEST_KEY", "inputs/manifest.json")
    bundle = CloudInputBundle.load(store, manifest_key)
    input_root = Path(os.getenv("E2E_CLOUD_INPUT_ROOT", "/tmp/idx-trade-e2e-inputs")).resolve()
    roles = bundle.materialize(store, input_root)
    schedule = v1.load_schedule_from_bundle(bundle, roles)
    if session < schedule.coverage_start or session > schedule.coverage_end:
        raise CloudPaperRuntimeError("CLOUD_E2E_SESSION_OUTSIDE_SCHEDULE_COVERAGE")
    if session not in schedule.session_dates:
        return {
            "status": "NOOP",
            "controller_status": "WEEKEND_OR_HOLIDAY_NOOP",
            "session_date": session,
            "stage": CHECKPOINT_STAGE,
            "outcome_accessed": False,
            "protected_forward_accessed": False,
            "model_refit": False,
        }

    schedule_sha = v1._sha(roles["execution_schedule"])
    input_sha = bundle.manifest_sha256
    code_commit = v1._git_head(v1.REPO_ROOT)
    existing = load_preopen_ca_checkpoint(
        store,
        session_date=session,
        expected_schedule_sha256=schedule_sha,
        expected_input_manifest_sha256=input_sha,
        expected_code_commit=code_commit,
    )
    if existing is not None:
        return {
            "status": "ALREADY_CHECKPOINTED",
            "controller_status": CHECKPOINT_STATUS,
            "session_date": session,
            "stage": CHECKPOINT_STAGE,
            "commit_sha256": existing.commit_sha256,
        }

    roots = v1._roots()
    archive = v1.CloudPaperArchive(store)
    prior = archive.latest_snapshot(schedule.session_dates, before_or_equal=session)
    if prior is not None:
        snapshot_bytes, snapshot_sha, _ = prior
        restore_runtime_snapshot(snapshot_bytes, roots, expected_sha256=snapshot_sha)
    for root in roots.values():
        root.mkdir(parents=True, exist_ok=True)

    config = v1._controller_config(
        roots=roots,
        roles=roles,
        schedule_path=roles["execution_schedule"],
        now=now,
    )
    missing = v1._config_missing(config.base)
    if missing:
        raise CloudPaperRuntimeError("CLOUD_OPERATIONAL_PREREQUISITE:" + missing)

    started = v1._now()
    controller_result = run_preopen_ca_cycle(config, now=started)
    finished = v1._now()
    controller_status = str(controller_result.get("controller_status") or "FAIL_CLOSED")
    result: dict[str, object] = {
        "schema_version": "idx_trade_e2e_paper_preopen_ca_result_v1",
        "session_date": session,
        "stage": CHECKPOINT_STAGE,
        "controller_status": controller_status,
        "controller_result": controller_result,
        "observed_started_at_utc": started.astimezone(UTC).isoformat(),
        "observed_finished_at_utc": finished.astimezone(UTC).isoformat(),
        "outcome_accessed": False,
        "protected_forward_accessed": False,
        "model_refit": False,
        "paper_state_mutated": False,
        "order_created": False,
        "fill_created": False,
        "retroactive_execution_authorized": False,
    }
    if controller_status == CHECKPOINT_STATUS:
        snapshot, snapshot_sha, snapshot_meta = build_runtime_snapshot(roots)
        checkpoint = commit_preopen_ca_checkpoint(
            store,
            session_date=session,
            snapshot_bytes=snapshot,
            snapshot_metadata=snapshot_meta,
            result_payload=result,
            schedule_attestation_sha256=schedule_sha,
            input_manifest_sha256=input_sha,
            code_identity={
                "repo": "samindriano/idx-trade",
                "commit": code_commit,
                "runner_sha256": v1._sha(Path(__file__).resolve()),
            },
        )
        result.update(
            {
                "status": "COMMITTED",
                "commit_sha256": checkpoint.commit_sha256,
                "snapshot_sha256": snapshot_sha,
            }
        )
        return result
    if controller_status in {
        "WAITING_PREPARED_EXECUTION",
        "WAITING_PREOPEN_CAPTURE_WINDOW",
    }:
        result["status"] = "WAITING"
        return result
    if controller_status == "WEEKEND_OR_HOLIDAY_NOOP":
        result["status"] = "NOOP"
        return result
    result["status"] = "FAILED"
    return result


def run_once(*, phase: str | None = None, session_date: str | None = None) -> dict[str, object]:
    if phase == CHECKPOINT_STAGE:
        return _run_preopen_ca_once(session_date=session_date)
    with _patched_v1_continuity():
        return v2.run_once(phase=phase, session_date=session_date)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("auto", "POST_EOD", "PREOPEN", CHECKPOINT_STAGE),
        default="auto",
    )
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
    return 0 if result.get("status") in {
        "COMMITTED",
        "ALREADY_COMMITTED",
        "ALREADY_CHECKPOINTED",
        "WAITING",
        "NOOP",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
