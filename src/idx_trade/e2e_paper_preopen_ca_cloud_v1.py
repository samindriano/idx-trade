"""Durable cloud PREOPEN-CA checkpoint for fresh-runner PAPER orchestration.

The scientific E2E stages remain POST_EOD and PREOPEN.  This module adds one
operational checkpoint only: before 09:02 Jakarta, capture the PREOPEN corporate
action refresh for a prepared D->E execution, using D POST_EOD as the immutable
journal parent, then persist the resulting runtime snapshot so the 09:03+
PREOPEN consumer can continue on a fresh GitHub runner.

No model, outcome, scoring, sizing, execution, or PaperState rule is changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence

from . import e2e_paper_operational_controller_v1 as v1
from . import e2e_paper_operational_controller_v2 as v2
from .e2e_operational_guard_v1 import JAKARTA, attest_deployment, exclusive_run_lock
from .e2e_paper_cloud_runtime_v1 import (
    CONTRACT_VERSION,
    CloudInputBundle,
    CloudObjectStore,
    CloudPaperRuntimeError,
    PutResult,
    build_runtime_snapshot,
    canonical_json_bytes,
    sha256_bytes,
)
from .forward_dividend_execution_v1_1 import (
    _load_and_verify_post_eod_attestation_v1_2,
)
from .forward_dividend_orchestration_v1 import POST_EOD, PREOPEN, load_journal_document
from .official_trading_schedule_v1 import load_verified_official_trading_schedule


CHECKPOINT_SCHEMA = "idx_trade_e2e_paper_preopen_ca_checkpoint_v1"
CHECKPOINT_STAGE = "PREOPEN_CA"
CHECKPOINT_STATUS = "PREOPEN_CA_READY"
PREOPEN_CA_CUTOFF = time(9, 2)
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class PreopenCACheckpoint:
    session_date: str
    commit_key: str
    commit_sha256: str
    snapshot_key: str
    snapshot_sha256: str
    snapshot_bytes: bytes
    result_key: str
    result_sha256: str
    payload: dict[str, Any]


def checkpoint_commit_key(session_date: str) -> str:
    session = date.fromisoformat(session_date).isoformat()
    return f"sessions/{session}/checkpoints/PREOPEN_CA/commit.json"


def _checkpoint_snapshot_key(session_date: str) -> str:
    session = date.fromisoformat(session_date).isoformat()
    return f"sessions/{session}/checkpoints/PREOPEN_CA/runtime_snapshot.zip"


def _checkpoint_result_key(session_date: str) -> str:
    session = date.fromisoformat(session_date).isoformat()
    return f"sessions/{session}/checkpoints/PREOPEN_CA/result.json"


def _json_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudPaperRuntimeError(label + "_JSON_INVALID") from exc
    if not isinstance(payload, dict):
        raise CloudPaperRuntimeError(label + "_NOT_OBJECT")
    return payload


def _require_sha(value: object, label: str) -> str:
    text = str(value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise CloudPaperRuntimeError(label + "_SHA_INVALID")
    return text


def load_preopen_ca_checkpoint(
    store: CloudObjectStore,
    *,
    session_date: str,
    expected_schedule_sha256: str,
    expected_input_manifest_sha256: str,
    expected_code_commit: str,
) -> PreopenCACheckpoint | None:
    session = date.fromisoformat(session_date).isoformat()
    key = checkpoint_commit_key(session)
    raw = store.read(key)
    if raw is None:
        return None
    payload = _json_object(raw, "CLOUD_PREOPEN_CA_CHECKPOINT")
    expected_schedule = _require_sha(expected_schedule_sha256, "CLOUD_PREOPEN_CA_SCHEDULE")
    expected_input = _require_sha(expected_input_manifest_sha256, "CLOUD_PREOPEN_CA_INPUT")
    code_commit = str(expected_code_commit or "").strip().lower()
    if not _GIT_SHA.fullmatch(code_commit):
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_CODE_GIT_SHA_INVALID")
    expected = {
        "schema_version": CHECKPOINT_SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "commit_state": "COMMITTED",
        "session_date": session,
        "stage": CHECKPOINT_STAGE,
        "stage_status": CHECKPOINT_STATUS,
        "schedule_attestation_sha256": expected_schedule,
        "input_manifest_sha256": expected_input,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_CHECKPOINT_IDENTITY_MISMATCH:" + field)
    code_identity = payload.get("code_identity")
    if not isinstance(code_identity, Mapping) or str(code_identity.get("commit") or "").lower() != code_commit:
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_CHECKPOINT_CODE_MISMATCH")
    snapshot = payload.get("snapshot")
    result = payload.get("result")
    if not isinstance(snapshot, Mapping) or not isinstance(result, Mapping):
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_CHECKPOINT_CHILD_REF_INVALID")
    snapshot_key = str(snapshot.get("key") or "")
    result_key = str(result.get("key") or "")
    if snapshot_key != _checkpoint_snapshot_key(session) or result_key != _checkpoint_result_key(session):
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_CHECKPOINT_CHILD_KEY_MISMATCH")
    snapshot_sha = _require_sha(snapshot.get("sha256"), "CLOUD_PREOPEN_CA_SNAPSHOT")
    result_sha = _require_sha(result.get("sha256"), "CLOUD_PREOPEN_CA_RESULT")
    snapshot_bytes = store.read(snapshot_key)
    result_bytes = store.read(result_key)
    if snapshot_bytes is None or sha256_bytes(snapshot_bytes) != snapshot_sha:
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_SNAPSHOT_HASH_MISMATCH")
    if result_bytes is None or sha256_bytes(result_bytes) != result_sha:
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_RESULT_HASH_MISMATCH")
    result_payload = _json_object(result_bytes, "CLOUD_PREOPEN_CA_RESULT")
    if (
        result_payload.get("session_date") != session
        or result_payload.get("stage") != CHECKPOINT_STAGE
        or result_payload.get("controller_status") != CHECKPOINT_STATUS
    ):
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_RESULT_IDENTITY_MISMATCH")
    guards = payload.get("guards")
    if not isinstance(guards, Mapping) or any(
        guards.get(name) is not False
        for name in (
            "outcome_accessed",
            "protected_forward_accessed",
            "model_refit",
            "paper_state_mutated",
            "order_created",
            "fill_created",
            "retroactive_execution_authorized",
        )
    ):
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_CHECKPOINT_GUARD_INVALID")
    return PreopenCACheckpoint(
        session_date=session,
        commit_key=key,
        commit_sha256=sha256_bytes(raw),
        snapshot_key=snapshot_key,
        snapshot_sha256=snapshot_sha,
        snapshot_bytes=snapshot_bytes,
        result_key=result_key,
        result_sha256=result_sha,
        payload=payload,
    )


def commit_preopen_ca_checkpoint(
    store: CloudObjectStore,
    *,
    session_date: str,
    snapshot_bytes: bytes,
    snapshot_metadata: Mapping[str, Any],
    result_payload: Mapping[str, Any],
    schedule_attestation_sha256: str,
    input_manifest_sha256: str,
    code_identity: Mapping[str, Any],
) -> PreopenCACheckpoint:
    session = date.fromisoformat(session_date).isoformat()
    schedule_sha = _require_sha(schedule_attestation_sha256, "CLOUD_PREOPEN_CA_SCHEDULE")
    input_sha = _require_sha(input_manifest_sha256, "CLOUD_PREOPEN_CA_INPUT")
    code_commit = str(code_identity.get("commit") or "").strip().lower()
    if not _GIT_SHA.fullmatch(code_commit):
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_CODE_GIT_SHA_INVALID")
    result = dict(result_payload)
    if (
        result.get("session_date") != session
        or result.get("stage") != CHECKPOINT_STAGE
        or result.get("controller_status") != CHECKPOINT_STATUS
    ):
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_RESULT_IDENTITY_MISMATCH")
    snapshot_sha = sha256_bytes(snapshot_bytes)
    result_bytes = canonical_json_bytes(result)
    result_sha = sha256_bytes(result_bytes)
    snapshot_key = _checkpoint_snapshot_key(session)
    result_key = _checkpoint_result_key(session)
    store.put_if_absent(snapshot_key, snapshot_bytes, "application/zip")
    store.put_if_absent(result_key, result_bytes, "application/json")
    body = {
        "schema_version": CHECKPOINT_SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "commit_state": "COMMITTED",
        "session_date": session,
        "stage": CHECKPOINT_STAGE,
        "stage_status": CHECKPOINT_STATUS,
        "schedule_attestation_sha256": schedule_sha,
        "input_manifest_sha256": input_sha,
        "code_identity": dict(code_identity),
        "snapshot": {
            "key": snapshot_key,
            "sha256": snapshot_sha,
            "metadata": dict(snapshot_metadata),
        },
        "result": {"key": result_key, "sha256": result_sha},
        "guards": {
            "outcome_accessed": False,
            "protected_forward_accessed": False,
            "model_refit": False,
            "paper_state_mutated": False,
            "order_created": False,
            "fill_created": False,
            "retroactive_execution_authorized": False,
        },
    }
    commit_bytes = canonical_json_bytes(body)
    store.put_if_absent(checkpoint_commit_key(session), commit_bytes, "application/json")
    loaded = load_preopen_ca_checkpoint(
        store,
        session_date=session,
        expected_schedule_sha256=schedule_sha,
        expected_input_manifest_sha256=input_sha,
        expected_code_commit=code_commit,
    )
    if loaded is None:
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_CHECKPOINT_NOT_READABLE")
    return loaded


def _current_input_identity(store: CloudObjectStore, manifest_key: str) -> tuple[str, str]:
    bundle = CloudInputBundle.load(store, manifest_key)
    schedule_ref = next((ref for ref in bundle.refs if ref.role == "execution_schedule"), None)
    if schedule_ref is None:
        raise CloudPaperRuntimeError("CLOUD_PREOPEN_CA_SCHEDULE_ROLE_MISSING")
    return schedule_ref.sha256, bundle.manifest_sha256


def _ensure_preopen_ca_phase(
    config: v1.OperationalControllerConfig,
    *,
    phase_session: str,
    from_session: str,
    through_session: str,
    required_tickers: Sequence[str],
    now: datetime,
    clock: Callable[[], datetime] | None = None,
) -> str:
    current = now.astimezone(JAKARTA)
    if current.date().isoformat() != phase_session:
        raise v1.E2EOperationalGuardError("E2E_PREOPEN_CA_PHASE_SESSION_MISMATCH")
    if current.time() < config.preopen_capture_start:
        return "WAITING_PREOPEN_CAPTURE_WINDOW"
    if current.time() >= PREOPEN_CA_CUTOFF:
        return "MISSED_PREOPEN_CA_CAPTURE"
    decision = date.fromisoformat(from_session).isoformat()
    execution = date.fromisoformat(through_session).isoformat()
    if execution != phase_session or decision >= execution:
        raise v1.E2EOperationalGuardError("E2E_PREOPEN_CA_DECISION_EXECUTION_SCOPE_INVALID")
    tickers = tuple(sorted({str(value).strip().upper() for value in required_tickers if str(value).strip()}))
    if not tickers:
        raise v1.E2EOperationalGuardError("E2E_PREOPEN_CA_REQUIRED_TICKERS_EMPTY")

    batch, journal = v1._journal_paths(config, phase_session, PREOPEN)
    sidecar = v1._phase_sidecar_path(config, phase_session, PREOPEN)
    if sidecar.is_file():
        payload = v1._verify_phase_sidecar(
            config,
            phase_session,
            PREOPEN,
            through_session=execution,
        )
        if payload.get("from_session_date") != decision:
            raise v1.E2EOperationalGuardError("E2E_PREOPEN_CA_PARENT_SCOPE_MISMATCH")
        if list(payload.get("required_tickers") or []) != list(tickers):
            raise v1.E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_TICKER_SCOPE_CHANGED")
        _load_and_verify_post_eod_attestation_v1_2(
            path=Path(str(payload["ca_attestation_path"])).expanduser().resolve(),
            expected_from_session_date=decision,
            expected_through_session_date=execution,
            required_tickers=tickers,
        )
        return "REUSED"
    if journal.exists() or batch.exists():
        raise v1.E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_PARTIAL")

    missing = v1._config_missing(config)
    if missing:
        raise v1.E2EOperationalGuardError(missing)
    prior = v1._journal_paths(config, decision, POST_EOD)[1]
    if not prior.is_file():
        raise v1.E2EOperationalGuardError("E2E_PREOPEN_POST_EOD_JOURNAL_MISSING")
    prior_doc = load_journal_document(prior)
    if prior_doc.journal.as_of_date != decision or prior_doc.journal.capture_phase != POST_EOD:
        raise v1.E2EOperationalGuardError("E2E_PREOPEN_POST_EOD_JOURNAL_SCOPE_MISMATCH")

    if config.ca_attestation_root is None or config.ca_capture_script is None:
        raise v1.E2EOperationalGuardError("E2E_PREOPEN_CA_DYNAMIC_CAPTURE_REQUIRED")
    attestation_root = Path(config.ca_attestation_root).expanduser().resolve()
    attestation_path = attestation_root / "attestations" / f"{phase_session}_PREOPEN.json"
    capture_root = attestation_root / "captures" / f"{phase_session}_PREOPEN"
    if attestation_path.exists() or capture_root.exists():
        raise v1.E2EOperationalGuardError("E2E_PREOPEN_CA_ATTESTATION_PARTIAL")

    capture_command = [
        str(Path(config.uv_exe).expanduser().resolve()),
        "run",
        "--project",
        str((Path(config.provider_checkout).expanduser().resolve() / "python").resolve()),
        "python",
        str(Path(config.ca_capture_script).expanduser().resolve()),
        "--provider-checkout",
        str(Path(config.provider_checkout).expanduser().resolve()),
        "--phase",
        PREOPEN,
        "--from-session",
        decision,
        "--through-session",
        execution,
        "--tickers",
        ",".join(tickers),
        "--output-dir",
        str(capture_root),
        "--attestation-output",
        str(attestation_path),
    ]
    v1._run_child(config, "ca_capture_preopen_cloud", capture_command)
    _load_and_verify_post_eod_attestation_v1_2(
        path=attestation_path,
        expected_from_session_date=decision,
        expected_through_session_date=execution,
        required_tickers=tickers,
    )

    acquisition_command = [
        str(Path(config.python_exe).expanduser().resolve()),
        str((config.repo_root / "scripts" / "run_forward_dividend_acquisition_batch_v1.py").resolve()),
        "--provider-checkout",
        str(Path(config.provider_checkout).expanduser().resolve()),
        "--runtime-root",
        str(config.runtime_root.expanduser().resolve()),
        "--as-of-date",
        phase_session,
        "--capture-phase",
        PREOPEN,
        "--uv-exe",
        str(Path(config.uv_exe).expanduser().resolve()),
        "--python-exe",
        str(Path(config.python_exe).expanduser().resolve()),
        "--prior-journal",
        str(prior.resolve()),
    ]
    for ticker in tickers:
        acquisition_command.extend(("--ticker", ticker))
    v1._run_child(config, "ca_preopen_cloud", acquisition_command)

    finished = (clock or (lambda: datetime.now(tz=JAKARTA)))().astimezone(JAKARTA)
    if finished.date().isoformat() != phase_session or finished.time() >= PREOPEN_CA_CUTOFF:
        raise v1.E2EOperationalGuardError("E2E_OPERATIONAL_PREOPEN_CA_CAPTURE_AFTER_CUTOFF")
    if not journal.is_file() or not batch.is_dir():
        raise v1.E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_OUTPUT_MISSING")
    journal_doc = load_journal_document(journal)
    if journal_doc.journal.as_of_date != phase_session or journal_doc.journal.capture_phase != PREOPEN:
        raise v1.E2EOperationalGuardError("E2E_OPERATIONAL_CA_PHASE_OUTPUT_MISMATCH")

    body: dict[str, Any] = {
        "schema_version": "idx_trade_e2e_operational_ca_phase_v1",
        "phase": PREOPEN,
        "session_date": phase_session,
        "from_session_date": decision,
        "through_session_date": execution,
        "started_at_jakarta": current.isoformat(),
        "finished_at_jakarta": finished.isoformat(),
        "required_tickers": list(tickers),
        "journal_path": str(journal.resolve()),
        "journal_sha256": v1._sha256(journal),
        "batch_root": str(batch.resolve()),
        "provider_commit": str(config.provider_expected_commit).lower(),
        "ca_attestation_path": str(attestation_path.resolve()),
        "ca_attestation_sha256": v1._sha256(attestation_path),
        "ca_attestation_status": "CAPTURED",
    }
    body["payload_sha256"] = v1._canonical_hash(body)
    v1._write_json_immutable(sidecar, body)
    verified = v1._verify_phase_sidecar(
        config,
        phase_session,
        PREOPEN,
        through_session=execution,
    )
    if verified.get("from_session_date") != decision:
        raise v1.E2EOperationalGuardError("E2E_PREOPEN_CA_PARENT_SCOPE_MISMATCH")
    return "CAPTURED"


def run_preopen_ca_cycle(
    config: v2.OperationalControllerConfigV2,
    *,
    now: datetime,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    deployment = attest_deployment(
        config.repo_root,
        expected_branch=config.expected_branch,
        expected_commit=config.expected_commit,
    )
    config.runtime_root.mkdir(parents=True, exist_ok=True)
    with exclusive_run_lock(config.runtime_root / "operational" / "controller.lock"):
        current = now.astimezone(JAKARTA)
        today = current.date().isoformat()
        schedule = load_verified_official_trading_schedule(
            config.execution_schedule_attestation_path,
            expected_sha256=config.execution_schedule_attestation_sha256,
        )
        status: dict[str, Any] = {
            "controller_status": "RUNNING",
            "controller_contract": "PREOPEN_CA_DURABLE_CHECKPOINT_V1",
            "session_date": today,
            "deployment": {
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
        if today not in schedule.session_dates:
            return {**status, "controller_status": "WEEKEND_OR_HOLIDAY_NOOP"}
        if current.time() < config.preopen_capture_start:
            return {**status, "controller_status": "WAITING_PREOPEN_CAPTURE_WINDOW"}
        if current.time() >= PREOPEN_CA_CUTOFF:
            return {**status, "controller_status": "MISSED_PREOPEN_CA_CAPTURE"}
        prepared, unbound = v2._verified_prepared_for_session(config, today)
        if unbound:
            return {
                **status,
                "controller_status": "FAIL_CLOSED_PREPARED_SCHEDULE_BINDING_INVALID",
                "unbound_prepared_candidates": [str(path) for path in unbound],
            }
        if len(prepared) > 1:
            return {
                **status,
                "controller_status": "FAIL_CLOSED_AMBIGUOUS_PREPARED_PARENT",
                "prepared_candidates": [str(path) for path in prepared],
            }
        if not prepared:
            return {
                **status,
                "controller_status": "WAITING_PREPARED_EXECUTION",
                "reason": "NO_PREPARED_EXECUTION_FOR_TODAY",
            }
        payload = v1._read_json(prepared[0])
        decision = date.fromisoformat(str(payload.get("decision_session_date") or "")).isoformat()
        execution = date.fromisoformat(str(payload.get("execution_session_date") or "")).isoformat()
        if execution != today or decision >= execution:
            raise v1.E2EOperationalGuardError("E2E_PREOPEN_CA_PREPARED_SCOPE_INVALID")
        required = tuple(sorted({str(value).strip().upper() for value in (payload.get("required_tickers") or ()) if str(value).strip()}))
        ca_status = _ensure_preopen_ca_phase(
            config.base,
            phase_session=today,
            from_session=decision,
            through_session=execution,
            required_tickers=required,
            now=current,
            clock=clock,
        )
        controller_status = CHECKPOINT_STATUS if ca_status in {"CAPTURED", "REUSED"} else ca_status
        return {
            **status,
            "controller_status": controller_status,
            "phase": CHECKPOINT_STAGE,
            "ca_phase_status": ca_status,
            "provider_calls": ca_status == "CAPTURED",
            "prepared_path": str(prepared[0].resolve()),
            "decision_session_date": decision,
            "execution_session_date": execution,
            "ca_phase_sidecar": str(v1._phase_sidecar_path(config.base, today, PREOPEN).resolve()),
        }


def validate_existing_t0_or_bootstrap(
    runtime_root: str | Path,
    *,
    session_date: str,
    original_bootstrap: Callable[..., Path],
) -> Path:
    """Keep the immutable T0 root anchored to its first session across D+N."""
    root = Path(runtime_root).expanduser().resolve()
    t0 = root / "t0" / "T0.json"
    if not t0.is_file():
        return original_bootstrap(root, session_date=session_date)
    try:
        payload = json.loads(t0.read_text(encoding="utf-8"))
        original_session = date.fromisoformat(str(payload.get("session_date") or "")).isoformat()
    except Exception as exc:
        raise v1.E2EOperationalGuardError("E2E_T0_EXISTING_ROOT_INVALID") from exc
    if original_session > date.fromisoformat(session_date).isoformat():
        raise v1.E2EOperationalGuardError("E2E_T0_EXISTING_ROOT_FROM_FUTURE")
    return original_bootstrap(root, session_date=original_session)


__all__ = [
    "CHECKPOINT_STAGE",
    "CHECKPOINT_STATUS",
    "PreopenCACheckpoint",
    "checkpoint_commit_key",
    "commit_preopen_ca_checkpoint",
    "load_preopen_ca_checkpoint",
    "run_preopen_ca_cycle",
    "validate_existing_t0_or_bootstrap",
]
