"""Deterministic controller boundary for the live PAPER E2E runtime.

The controller is deliberately a consumer of the existing forward EOD, X1,
official Open, and dividend runtimes.  It does not create a provider, score,
ledger, or outcome path.  Until the existing V1.2 CA acquisition outputs are
present and explicitly configured, it records a fail-closed waiting state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
import hashlib
import json
from pathlib import Path
from typing import Any

from .e2e_operational_guard_v1 import (
    E2EOperationalGuardError,
    JAKARTA,
    attest_deployment,
    exclusive_run_lock,
    load_session_dates,
    require_phase_window,
    write_status_atomic,
)


@dataclass(frozen=True)
class OperationalControllerConfig:
    runtime_root: Path
    forward_runtime_root: Path
    calendar_path: Path
    official_open_root: Path
    repo_root: Path
    expected_branch: str
    expected_commit: str


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise E2EOperationalGuardError("E2E_OPERATIONAL_UPSTREAM_POINTER_MISSING")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_UPSTREAM_POINTER_INVALID") from exc
    if not isinstance(value, dict):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_UPSTREAM_POINTER_INVALID")
    return value


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise E2EOperationalGuardError("E2E_OPERATIONAL_ARTIFACT_MISSING")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    ).hexdigest()


def _pipeline_pointer(config: OperationalControllerConfig) -> dict[str, Any]:
    pointer = _read_json(
        config.forward_runtime_root
        / "forward_monitoring"
        / "eod_automation"
        / "v4_x1_pipeline"
        / "latest.json"
    )
    run_log_path = Path(str(pointer.get("run_log_path") or "")).expanduser().resolve()
    declared_run_log_sha = str(pointer.get("run_log_sha256") or "")
    if not run_log_path.is_file() or _sha256(run_log_path) != declared_run_log_sha:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_UPSTREAM_LOG_HASH_MISMATCH")
    return pointer


def _verify_score_pointer(pointer: dict[str, Any], session: str) -> dict[str, Any]:
    score = pointer.get("x1_score")
    if not isinstance(score, dict):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_SCORE_POINTER_MISSING")
    path = Path(str(score.get("manifest_path") or "")).expanduser().resolve()
    if not path.is_file() or _sha256(path) != str(score.get("manifest_sha256") or ""):
        raise E2EOperationalGuardError("E2E_OPERATIONAL_SCORE_MANIFEST_HASH_MISMATCH")
    if str(score.get("session_date") or "") != session:
        raise E2EOperationalGuardError("E2E_OPERATIONAL_SCORE_SESSION_MISMATCH")
    return score


def _status_path(config: OperationalControllerConfig) -> Path:
    return config.runtime_root / "operational" / "latest.json"


def _prepared_for_session(config: OperationalControllerConfig, session: str) -> list[Path]:
    prepared_dir = config.runtime_root / "prepared"
    candidates: list[Path] = []
    for path in sorted(prepared_dir.glob("*.json")) if prepared_dir.is_dir() else ():
        try:
            payload = _read_json(path)
        except E2EOperationalGuardError:
            continue
        if str(payload.get("schema_version") or "") != "idx_trade_e2e_paper_prepared_execution_v1":
            continue
        declared = str(payload.get("payload_sha256") or "")
        body = dict(payload)
        body.pop("payload_sha256", None)
        if not declared or _canonical_hash(body) != declared:
            continue
        if str(payload.get("execution_session_date") or "") != session:
            continue
        eod = payload.get("eod_inputs")
        if not isinstance(eod, dict):
            continue
        valid_refs = True
        for key in ("ohlcv", "model_input", "calendar"):
            ref = eod.get(key)
            if not isinstance(ref, dict):
                valid_refs = False
                break
            ref_path = Path(str(ref.get("path") or "")).expanduser().resolve()
            if not ref_path.is_file() or _sha256(ref_path) != str(ref.get("sha256") or ""):
                valid_refs = False
                break
        if valid_refs:
            candidates.append(path)
    return candidates


def run_operational_cycle(
    config: OperationalControllerConfig,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run one no-backfill controller pass and persist its operational state."""

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
        try:
            sessions = load_session_dates(config.calendar_path)
            status["calendar_path"] = str(config.calendar_path.resolve())
            status["calendar_session_count"] = len(sessions)
            if today not in sessions:
                status.update({
                    "controller_status": "WEEKEND_OR_HOLIDAY_NOOP",
                    "reason": "NO_OFFICIAL_SESSION_TODAY",
                })
            elif current.time().hour < 9 or (
                current.time().hour == 9 and current.time().minute < 2
            ):
                status.update({
                    "controller_status": "WAITING_PREOPEN_WINDOW",
                    "reason": "PREOPEN_NOT_OPEN",
                    "execution_session_date": today,
                })
            elif current.time() <= time(9, 22, 59):
                prepared = _prepared_for_session(config, today)
                status["execution_session_date"] = today
                if len(prepared) > 1:
                    status.update({
                        "controller_status": "FAIL_CLOSED_AMBIGUOUS_PREPARED_PARENT",
                        "prepared_candidates": [str(p) for p in prepared],
                    })
                elif not prepared:
                    status.update({
                        "controller_status": "WAITING_PREPARED_EXECUTION",
                        "reason": "NO_PREPARED_EXECUTION_FOR_TODAY",
                    })
                else:
                    open_manifest = config.official_open_root / today / "manifest.json"
                    status["prepared_path"] = str(prepared[0])
                    if not open_manifest.is_file():
                        status.update({
                            "controller_status": "WAITING_OFFICIAL_OPEN",
                            "reason": "CERTIFIED_OPEN_MANIFEST_MISSING",
                        })
                    else:
                        status.update({
                            "controller_status": "WAITING_CA_RECONCILIATION",
                            "reason": "CA_PREOPEN_INPUT_NOT_CONFIGURED",
                            "open_manifest_path": str(open_manifest),
                        })
            elif current.time() < time(18, 0):
                status.update({
                    "controller_status": "PREOPEN_WINDOW_MISSED_NO_EXECUTION",
                    "reason": "NO_RETROACTIVE_PAPER_EXECUTION",
                    "execution_session_date": today,
                })
            else:
                pointer = _pipeline_pointer(config)
                score = _verify_score_pointer(pointer, today)
                eod = pointer.get("eod") if isinstance(pointer.get("eod"), dict) else {}
                status["upstream_pointer_path"] = str(
                    config.forward_runtime_root
                    / "forward_monitoring"
                    / "eod_automation"
                    / "v4_x1_pipeline"
                    / "latest.json"
                )
                if (
                    eod.get("status") != "NO_MISSING_SESSION"
                    or score.get("status") not in {"V4_X1_SCORE_ALREADY_DONE_VERIFIED", "V4_X1_PROSPECTIVE_SCORE_DONE"}
                    or str(score.get("session_date") or "") != today
                ):
                    status.update({
                        "controller_status": "WAITING_UPSTREAM_EOD_SCORE",
                        "reason": "CANONICAL_EOD_OR_SAME_DAY_SCORE_NOT_READY",
                    })
                else:
                    status["calendar_sha256"] = _sha256(config.calendar_path)
                    status.update({
                        "controller_status": "WAITING_CA_RECONCILIATION",
                        "reason": "CA_POST_EOD_INPUT_NOT_CONFIGURED",
                        "decision_session_date": today,
                        "score_manifest_path": score.get("manifest_path"),
                        "score_manifest_sha256": score.get("manifest_sha256"),
                    })
            status["finished_at_jakarta"] = datetime.now(tz=JAKARTA).isoformat()
            status["status_sha256"] = write_status_atomic(_status_path(config), status)
            return status
        except Exception as error:
            status.update({
                "controller_status": "FAIL_CLOSED",
                "error_code": type(error).__name__.upper(),
                "error_message": str(error),
                "finished_at_jakarta": datetime.now(tz=JAKARTA).isoformat(),
            })
            status["status_sha256"] = write_status_atomic(_status_path(config), status)
            raise


__all__ = ["OperationalControllerConfig", "run_operational_cycle"]
