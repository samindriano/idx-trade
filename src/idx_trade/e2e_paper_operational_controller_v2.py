"""Dual-calendar live PAPER controller.

V1 helper primitives remain the audited implementation for deployment, CA,
status, and child-process boundaries.  V2 changes only calendar semantics:
observed IDX sessions remain the EOD parent, while an independently hash-pinned
planned Bursa schedule controls holidays and future execution dates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Mapping

from . import e2e_paper_operational_controller_v1 as v1
from .e2e_operational_guard_v1 import (
    E2EOperationalGuardError,
    JAKARTA,
    attest_deployment,
    exclusive_run_lock,
    write_phase_attestation,
    write_status_atomic,
)
from .e2e_paper_continuity_schedule_v1 import (
    advance_missed_execution_no_certified_open_with_schedule,
)
from .e2e_paper_orchestration_v1 import (
    PREPARED_SCHEMA,
    _read_verified_json,
    bootstrap_t0,
    derive_required_execution_tickers,
    load_score_manifest,
)
from .e2e_paper_schedule_binding_v1 import verify_prepared_schedule_binding
from .official_trading_schedule_v1 import (
    OfficialTradingScheduleError,
    load_verified_official_trading_schedule,
)
from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_execution_v1_verify_schedule_v1 import (
    verify_eod_execution_inputs_with_schedule,
)


@dataclass(frozen=True)
class OperationalControllerConfigV2:
    base: v1.OperationalControllerConfig
    execution_schedule_attestation_path: Path
    execution_schedule_attestation_sha256: str

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)


def _status_path(config: OperationalControllerConfigV2) -> Path:
    return config.runtime_root / "operational" / "latest.json"


def _verified_prepared_for_session(
    config: OperationalControllerConfigV2,
    session: str,
) -> tuple[list[Path], list[Path]]:
    """Return (schedule-bound candidates, legacy/unbound candidates)."""

    raw = v1._prepared_for_session(config, session)
    verified: list[Path] = []
    unbound: list[Path] = []
    for path in raw:
        try:
            verify_prepared_schedule_binding(
                config.runtime_root,
                prepared_path=path,
                expected_schedule_attestation_path=config.execution_schedule_attestation_path,
                expected_schedule_attestation_sha256=config.execution_schedule_attestation_sha256,
            )
            verified.append(path)
        except Exception:
            unbound.append(path)
    return verified, unbound


def run_operational_cycle_v2(
    config: OperationalControllerConfigV2,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    deployment = attest_deployment(
        config.repo_root,
        expected_branch=config.expected_branch,
        expected_commit=config.expected_commit,
    )
    config.runtime_root.mkdir(parents=True, exist_ok=True)
    lock_path = config.runtime_root / "operational" / "controller.lock"
    with exclusive_run_lock(lock_path):
        current = (now or datetime.now(tz=JAKARTA)).astimezone(JAKARTA)
        today = current.date().isoformat()
        status: dict[str, Any] = {
            "controller_status": "RUNNING",
            "controller_contract": "DUAL_CALENDAR_V1",
            "started_at_jakarta": current.isoformat(),
            "decision_session_date": None,
            "execution_session_date": None,
            "deployment": {
                "repo_root": str(deployment.repo_root),
                "branch": deployment.branch,
                "head": deployment.head,
                "expected_commit": deployment.expected_commit,
                "clean": deployment.clean,
            },
            "provider_calls": False,
            "model_refit": False,
            "model_rescore": False,
            "outcome_access": False,
        }

        def finish(**updates: Any) -> dict[str, Any]:
            status.update(updates)
            status["finished_at_jakarta"] = datetime.now(tz=JAKARTA).isoformat()
            status["status_sha256"] = write_status_atomic(_status_path(config), status)
            return status

        try:
            schedule = load_verified_official_trading_schedule(
                config.execution_schedule_attestation_path,
                expected_sha256=config.execution_schedule_attestation_sha256,
            )
            status.update(
                {
                    "observed_calendar_path": str(config.calendar_path.resolve()),
                    "execution_schedule_attestation_path": str(schedule.attestation_path.resolve()),
                    "execution_schedule_attestation_sha256": schedule.attestation_sha256,
                    "execution_schedule_source_reference": schedule.source_reference,
                    "execution_schedule_coverage_start": schedule.coverage_start,
                    "execution_schedule_coverage_end": schedule.coverage_end,
                }
            )
            today_date = date.fromisoformat(today)
            if today_date < date.fromisoformat(schedule.coverage_start) or today_date > date.fromisoformat(schedule.coverage_end):
                return finish(
                    controller_status="WAITING_OFFICIAL_SCHEDULE_COVERAGE",
                    reason="TODAY_OUTSIDE_VERIFIED_PLANNED_SCHEDULE_COVERAGE",
                )
            if today not in schedule.session_dates:
                return finish(
                    controller_status="WEEKEND_OR_HOLIDAY_NOOP",
                    reason="NO_PLANNED_OFFICIAL_SESSION_TODAY",
                )

            prepared, unbound = _verified_prepared_for_session(config, today)
            if unbound:
                return finish(
                    controller_status="FAIL_CLOSED_PREPARED_SCHEDULE_BINDING_INVALID",
                    reason="PREPARED_PARENT_NOT_BOUND_TO_CURRENT_PLANNED_SCHEDULE",
                    unbound_prepared_candidates=[str(path) for path in unbound],
                )
            status["execution_session_date"] = today

            if current.time() < time(9, 2):
                if len(prepared) > 1:
                    return finish(
                        controller_status="FAIL_CLOSED_AMBIGUOUS_PREPARED_PARENT",
                        prepared_candidates=[str(path) for path in prepared],
                    )
                if not prepared:
                    return finish(
                        controller_status="WAITING_PREPARED_EXECUTION",
                        reason="NO_PREPARED_EXECUTION_FOR_TODAY",
                    )
                if current.time() < config.preopen_capture_start:
                    return finish(
                        controller_status="WAITING_PREOPEN_CAPTURE_WINDOW",
                        reason="PREOPEN_CA_CAPTURE_NOT_OPEN",
                        prepared_path=str(prepared[0]),
                    )
                missing = v1._config_missing(config)
                if missing:
                    return finish(
                        controller_status="WAITING_OPERATIONAL_CONFIGURATION",
                        reason=missing,
                        prepared_path=str(prepared[0]),
                    )
                payload = v1._read_json(prepared[0])
                ca_status = v1._ensure_ca_phase(
                    config,
                    session=today,
                    through_session=str(payload.get("execution_session_date") or ""),
                    phase="PREOPEN",
                    required_tickers=tuple(payload.get("required_tickers") or ()),
                    now=current,
                )
                return finish(
                    controller_status="PREOPEN_CA_READY" if ca_status in {"CAPTURED", "REUSED"} else ca_status,
                    phase="PREOPEN",
                    ca_phase_status=ca_status,
                    provider_calls=ca_status == "CAPTURED",
                    prepared_path=str(prepared[0]),
                )

            if current.time() <= time(9, 22, 59):
                if len(prepared) > 1:
                    return finish(
                        controller_status="FAIL_CLOSED_AMBIGUOUS_PREPARED_PARENT",
                        prepared_candidates=[str(path) for path in prepared],
                    )
                if not prepared:
                    return finish(
                        controller_status="WAITING_PREPARED_EXECUTION",
                        reason="NO_PREPARED_EXECUTION_FOR_TODAY",
                    )
                missing = v1._config_missing(config)
                if missing:
                    return finish(
                        controller_status="WAITING_OPERATIONAL_CONFIGURATION",
                        reason=missing,
                        prepared_path=str(prepared[0]),
                    )
                payload = v1._read_json(prepared[0])
                through_session = str(payload.get("execution_session_date") or "")
                try:
                    sidecar = v1._verify_phase_sidecar(
                        config, today, "PREOPEN", through_session=through_session
                    )
                except E2EOperationalGuardError as exc:
                    return finish(
                        controller_status="WAITING_PREOPEN_CA_CAPTURE",
                        reason=str(exc),
                        prepared_path=str(prepared[0]),
                    )
                open_manifest = config.official_open_root / today / "manifest.json"
                if not open_manifest.is_file():
                    return finish(
                        controller_status="WAITING_OFFICIAL_OPEN",
                        reason="CERTIFIED_OPEN_MANIFEST_MISSING",
                        prepared_path=str(prepared[0]),
                        ca_phase_sidecar=str(v1._phase_sidecar_path(config, today, "PREOPEN")),
                    )
                ca_attestation_path = Path(str(sidecar["ca_attestation_path"])).expanduser().resolve()
                current_score_path = Path(str(payload["current_score"]["manifest_path"])).expanduser().resolve()
                previous_ref = payload.get("previous_score")
                previous_score_path = (
                    None
                    if not isinstance(previous_ref, Mapping)
                    else Path(str(previous_ref["manifest_path"])).expanduser().resolve()
                )
                eod = payload["eod_inputs"]
                before_execution = config.runtime_root / "executions" / f"{today}.json"
                was_complete = before_execution.is_file()
                phase_attestation_path, _ = write_phase_attestation(
                    config.runtime_root,
                    phase="PREOPEN",
                    session_date=today,
                    expected_branch=config.expected_branch,
                    expected_commit=config.expected_commit,
                    issued_at=current,
                )
                command = [
                    str(Path(config.python_exe).expanduser().resolve()),
                    str((config.repo_root / "scripts" / "run_e2e_paper_preopen_v2.py").resolve()),
                    "--runtime-root", str(config.runtime_root.resolve()),
                    "--prepared", str(prepared[0].resolve()),
                    "--current-score-manifest", str(current_score_path),
                    "--session-ohlcv", str(Path(str(eod["ohlcv"]["path"])).expanduser().resolve()),
                    "--model-input", str(Path(str(eod["model_input"]["path"])).expanduser().resolve()),
                    "--calendar", str(Path(str(eod["calendar"]["path"])).expanduser().resolve()),
                    "--execution-schedule-attestation", str(schedule.attestation_path.resolve()),
                    "--execution-schedule-attestation-sha256", schedule.attestation_sha256,
                    "--open-manifest", str(open_manifest.resolve()),
                    "--ca-attestation", str(ca_attestation_path),
                    "--expected-branch", config.expected_branch,
                    "--expected-commit", config.expected_commit,
                    "--phase-attestation", str(phase_attestation_path.resolve()),
                    "--ca-journal", str(v1._journal_paths(config, today, "PREOPEN")[1].resolve()),
                ]
                if previous_score_path is not None:
                    command.extend(("--previous-score-manifest", str(previous_score_path)))
                v1._run_child(config, "preopen_v2", command)
                execution = v1._read_json(before_execution)
                return finish(
                    controller_status="ALREADY_COMPLETE" if was_complete else "EXECUTION_COMPLETE",
                    phase="PREOPEN",
                    ca_phase_sidecar=str(v1._phase_sidecar_path(config, today, "PREOPEN")),
                    execution_path=str(before_execution.resolve()),
                    execution_sha256=v1._sha256(before_execution),
                    execution_status=execution.get("status"),
                )

            execution = config.runtime_root / "executions" / f"{today}.json"
            if current.time() < time(18, 0):
                if execution.is_file():
                    return finish(
                        controller_status="ALREADY_COMPLETE",
                        phase="PREOPEN",
                        execution_path=str(execution.resolve()),
                        execution_sha256=v1._sha256(execution),
                    )
                return finish(
                    controller_status="PREOPEN_WINDOW_MISSED_NO_EXECUTION",
                    reason="NO_RETROACTIVE_PAPER_EXECUTION",
                )

            pointer = v1._pipeline_pointer(config)
            score_ref = v1._verify_score_pointer(
                pointer, today, expected_forward_root=config.forward_runtime_root
            )
            eod_ref = pointer.get("eod") if isinstance(pointer.get("eod"), dict) else {}
            status["upstream_pointer_path"] = str(
                config.forward_runtime_root
                / "forward_monitoring"
                / "eod_automation"
                / "v4_x1_pipeline"
                / "latest.json"
            )
            if (
                eod_ref.get("status") != "NO_MISSING_SESSION"
                or score_ref.get("status") not in {"V4_X1_SCORE_ALREADY_DONE_VERIFIED", "V4_X1_PROSPECTIVE_SCORE_DONE"}
                or score_ref.get("session_date") != today
            ):
                return finish(
                    controller_status="WAITING_UPSTREAM_EOD_SCORE",
                    reason="CANONICAL_EOD_OR_SAME_DAY_SCORE_NOT_READY",
                )
            missing = v1._config_missing(config)
            if missing:
                return finish(
                    controller_status="WAITING_OPERATIONAL_CONFIGURATION",
                    reason=missing,
                    decision_session_date=today,
                    score_manifest_path=score_ref.get("manifest_path"),
                    score_manifest_sha256=score_ref.get("manifest_sha256"),
                )

            # Retire an exact session's prepared order only when that prepared
            # parent is already bound to the planned schedule and no Open exists.
            if not (config.official_open_root / today / "manifest.json").is_file() and len(prepared) == 1:
                prepared_payload = _read_verified_json(prepared[0], PREPARED_SCHEMA)
                if str(prepared_payload.get("execution_session_date") or "") == today:
                    required_prepared = tuple(
                        sorted(str(value) for value in (prepared_payload.get("required_tickers") or ()))
                    )
                    prepared_ca = v1._reconcile_prepared_ca(
                        prepared_payload, required_tickers=required_prepared
                    )
                    missed = advance_missed_execution_no_certified_open_with_schedule(
                        config.runtime_root,
                        prepared_path=prepared[0],
                        observed_calendar_path=str(prepared_payload["eod_inputs"]["calendar"]["path"]),
                        execution_schedule_attestation_path=schedule.attestation_path,
                        execution_schedule_attestation_sha256=schedule.attestation_sha256,
                        ca_reconciliation=prepared_ca,
                        official_open_root=config.official_open_root,
                        issued_at=current,
                    )
                    return finish(
                        controller_status="MISSED_EXECUTION_NO_CERTIFIED_OPEN",
                        reason="NO_CERTIFIED_OPEN_FOR_EXACT_EXECUTION_SESSION",
                        decision_session_date=missed.decision_session_date,
                        execution_session_date=missed.execution_session_date,
                        missed_execution_path=str(missed.path),
                        missed_execution_sha256=missed.file_sha256,
                        runtime_snapshot_path=str(missed.runtime_snapshot_path),
                        runtime_snapshot_sha256=missed.runtime_snapshot_sha256,
                        prepared_order_expired=True,
                        no_retroactive_execution=True,
                    )

            eod_paths = v1._session_manifest(config, today)
            current_score = load_score_manifest(score_ref["manifest_path"])
            previous_path = v1._previous_score_manifest(config, today)
            previous_score = None if previous_path is None else load_score_manifest(previous_path)
            required = tuple(
                sorted({str(value).strip().upper() for value in current_score.scores["ticker"].tolist()})
            )
            try:
                eod_inputs = verify_eod_execution_inputs_with_schedule(
                    session_ohlcv_path=eod_paths["session_ohlcv"],
                    model_input_path=eod_paths["model_input"],
                    official_calendar_path=eod_paths["calendar"],
                    execution_schedule_attestation_path=schedule.attestation_path,
                    execution_schedule_attestation_sha256=schedule.attestation_sha256,
                    decision_session_date=today,
                    required_tickers=required,
                )
            except DecisionV1Error as error:
                if str(error) == "EXECUTION_V1_NEXT_OFFICIAL_SESSION_UNAVAILABLE":
                    return finish(
                        controller_status="WAITING_OFFICIAL_CALENDAR_SUCCESSOR",
                        reason="NO_VERIFIED_NEXT_OFFICIAL_SESSION_YET",
                        decision_session_date=today,
                    )
                raise

            bootstrap_t0(config.runtime_root, session_date=today)
            required = derive_required_execution_tickers(
                config.runtime_root,
                current_score=current_score,
                previous_score=previous_score,
                eod_inputs=eod_inputs,
            )
            ca_status = v1._ensure_ca_phase(
                config,
                session=today,
                through_session=eod_inputs.next_official_session_date,
                phase="POST_EOD",
                required_tickers=required,
                now=current,
            )
            sidecar = v1._verify_phase_sidecar(
                config,
                today,
                "POST_EOD",
                through_session=eod_inputs.next_official_session_date,
            )
            ca_attestation_path = Path(str(sidecar["ca_attestation_path"])).expanduser().resolve()
            phase_attestation_path, _ = write_phase_attestation(
                config.runtime_root,
                phase="POST_EOD",
                session_date=today,
                expected_branch=config.expected_branch,
                expected_commit=config.expected_commit,
                issued_at=current,
            )
            command = [
                str(Path(config.python_exe).expanduser().resolve()),
                str((config.repo_root / "scripts" / "run_e2e_paper_post_eod_v2.py").resolve()),
                "--runtime-root", str(config.runtime_root.resolve()),
                "--current-score-manifest", str(current_score.manifest_path.resolve()),
                "--session-ohlcv", str(eod_paths["session_ohlcv"]),
                "--model-input", str(eod_paths["model_input"]),
                "--calendar", str(eod_paths["calendar"]),
                "--execution-schedule-attestation", str(schedule.attestation_path.resolve()),
                "--execution-schedule-attestation-sha256", schedule.attestation_sha256,
                "--ca-attestation", str(ca_attestation_path),
                "--expected-branch", config.expected_branch,
                "--expected-commit", config.expected_commit,
                "--phase-attestation", str(phase_attestation_path.resolve()),
                "--ca-journal", str(v1._journal_paths(config, today, "POST_EOD")[1].resolve()),
            ]
            if previous_path is not None:
                command.extend(("--previous-score-manifest", str(previous_path)))
            v1._run_child(config, "post_eod_v2", command)
            prepared_after, unbound_after = _verified_prepared_for_session(
                config, eod_inputs.next_official_session_date
            )
            if unbound_after or len(prepared_after) != 1:
                raise E2EOperationalGuardError("E2E_OPERATIONAL_PREPARED_OUTPUT_INVALID")
            return finish(
                controller_status="POST_EOD_PREPARED",
                phase="POST_EOD",
                provider_calls=ca_status == "CAPTURED",
                ca_phase_status=ca_status,
                prepared_path=str(prepared_after[0].resolve()),
                prepared_sha256=v1._sha256(prepared_after[0]),
                decision_session_date=today,
                execution_session_date=eod_inputs.next_official_session_date,
            )
        except OfficialTradingScheduleError as error:
            return finish(
                controller_status="FAIL_CLOSED",
                error_code=type(error).__name__.upper(),
                error_message=str(error),
            )
        except Exception as error:
            return finish(
                controller_status="FAIL_CLOSED",
                error_code=type(error).__name__.upper(),
                error_message=str(error),
            )


__all__ = ["OperationalControllerConfigV2", "run_operational_cycle_v2"]
