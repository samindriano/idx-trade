"""Immutable planned-schedule parent for E2E PAPER prepared executions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .e2e_paper_orchestration_v1 import (
    E2EPaperOrchestrationError,
    PREPARED_SCHEMA,
    _atomic_write,
    _canonical_hash,
    _date,
    _read_verified_json,
    _sha256_file,
)
from .official_trading_schedule_v1 import (
    OfficialTradingScheduleError,
    load_verified_official_trading_schedule,
    next_planned_session,
)
from .v4_x1_execution_v1_verify_schedule_v1 import (
    VerifiedScheduledEODExecutionInputs,
)


SCHEMA_VERSION = "idx_trade_e2e_prepared_schedule_binding_v1"


@dataclass(frozen=True)
class VerifiedPreparedScheduleBinding:
    path: Path
    file_sha256: str
    decision_session_date: str
    execution_session_date: str
    prepared_path: Path
    prepared_sha256: str
    schedule_attestation_path: Path
    schedule_attestation_sha256: str


def _binding_path(runtime_root: str | Path, decision_session_date: str) -> Path:
    decision = _date(decision_session_date)
    return (
        Path(runtime_root).expanduser().resolve()
        / "prepared_schedule"
        / f"{decision}.json"
    )


def write_prepared_schedule_binding(
    runtime_root: str | Path,
    *,
    prepared_path: str | Path,
    eod_inputs: VerifiedScheduledEODExecutionInputs,
) -> VerifiedPreparedScheduleBinding:
    """Bind one immutable prepared artifact to the exact planned schedule."""

    if not isinstance(eod_inputs, VerifiedScheduledEODExecutionInputs):
        raise E2EPaperOrchestrationError("E2E_SCHEDULED_EOD_INPUTS_REQUIRED")
    prepared = Path(prepared_path).expanduser().resolve()
    payload = _read_verified_json(prepared, PREPARED_SCHEMA)
    body = dict(payload)
    declared = str(body.pop("payload_sha256") or "")
    if not declared or _canonical_hash(body) != declared:
        raise E2EPaperOrchestrationError("E2E_PREPARED_PAYLOAD_SHA_MISMATCH")

    decision = _date(payload.get("decision_session_date"))
    execution = _date(payload.get("execution_session_date"))
    if decision != eod_inputs.session_date:
        raise E2EPaperOrchestrationError("E2E_SCHEDULE_BINDING_DECISION_MISMATCH")
    if execution != eod_inputs.next_official_session_date:
        raise E2EPaperOrchestrationError("E2E_SCHEDULE_BINDING_EXECUTION_MISMATCH")

    eod_ref = payload.get("eod_inputs")
    if not isinstance(eod_ref, dict) or not isinstance(eod_ref.get("calendar"), dict):
        raise E2EPaperOrchestrationError("E2E_PREPARED_EOD_REFERENCE_MISSING")
    observed_ref = eod_ref["calendar"]
    if (
        str(observed_ref.get("path") or "")
        != str(eod_inputs.official_calendar_path.resolve())
        or str(observed_ref.get("sha256") or "")
        != eod_inputs.official_calendar_sha256
    ):
        raise E2EPaperOrchestrationError("E2E_SCHEDULE_BINDING_OBSERVED_CALENDAR_MISMATCH")

    try:
        schedule = load_verified_official_trading_schedule(
            eod_inputs.execution_schedule_attestation_path,
            expected_sha256=eod_inputs.execution_schedule_attestation_sha256,
        )
        expected_execution = next_planned_session(schedule, decision)
    except OfficialTradingScheduleError as exc:
        raise E2EPaperOrchestrationError(
            f"E2E_SCHEDULE_BINDING_SCHEDULE_INVALID:{exc}"
        ) from exc
    if expected_execution != execution:
        raise E2EPaperOrchestrationError("E2E_SCHEDULE_BINDING_NEXT_SESSION_MISMATCH")

    binding_payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "decision_session_date": decision,
        "execution_session_date": execution,
        "prepared_path": str(prepared),
        "prepared_sha256": _sha256_file(prepared),
        "observed_calendar_path": str(eod_inputs.official_calendar_path.resolve()),
        "observed_calendar_sha256": eod_inputs.official_calendar_sha256,
        "execution_schedule_attestation_path": str(schedule.attestation_path.resolve()),
        "execution_schedule_attestation_sha256": schedule.attestation_sha256,
        "execution_schedule_source_path": str(schedule.source_document_path.resolve()),
        "execution_schedule_source_sha256": schedule.source_document_sha256,
        "execution_schedule_source_reference": schedule.source_reference,
        "outcome_access": False,
    }
    binding_payload["payload_sha256"] = _canonical_hash(binding_payload)
    target = _binding_path(runtime_root, decision)
    path, sha = _atomic_write(target, binding_payload)
    return VerifiedPreparedScheduleBinding(
        path=path,
        file_sha256=sha,
        decision_session_date=decision,
        execution_session_date=execution,
        prepared_path=prepared,
        prepared_sha256=_sha256_file(prepared),
        schedule_attestation_path=schedule.attestation_path,
        schedule_attestation_sha256=schedule.attestation_sha256,
    )


def verify_prepared_schedule_binding(
    runtime_root: str | Path,
    *,
    prepared_path: str | Path,
    expected_schedule_attestation_path: str | Path,
    expected_schedule_attestation_sha256: str,
) -> VerifiedPreparedScheduleBinding:
    """Reverify prepared, observed calendar, source document, and next session."""

    prepared = Path(prepared_path).expanduser().resolve()
    prepared_payload = _read_verified_json(prepared, PREPARED_SCHEMA)
    prepared_body = dict(prepared_payload)
    prepared_declared = str(prepared_body.pop("payload_sha256") or "")
    if not prepared_declared or _canonical_hash(prepared_body) != prepared_declared:
        raise E2EPaperOrchestrationError("E2E_PREPARED_PAYLOAD_SHA_MISMATCH")
    decision = _date(prepared_payload.get("decision_session_date"))
    execution = _date(prepared_payload.get("execution_session_date"))

    path = _binding_path(runtime_root, decision)
    payload = _read_verified_json(path, SCHEMA_VERSION)
    body = dict(payload)
    declared = str(body.pop("payload_sha256") or "")
    if not declared or _canonical_hash(body) != declared:
        raise E2EPaperOrchestrationError("E2E_SCHEDULE_BINDING_PAYLOAD_SHA_MISMATCH")
    if (
        payload.get("decision_session_date") != decision
        or payload.get("execution_session_date") != execution
        or str(payload.get("prepared_path") or "") != str(prepared)
        or str(payload.get("prepared_sha256") or "") != _sha256_file(prepared)
    ):
        raise E2EPaperOrchestrationError("E2E_SCHEDULE_BINDING_PREPARED_PARENT_MISMATCH")

    observed = prepared_payload.get("eod_inputs")
    observed_ref = observed.get("calendar") if isinstance(observed, dict) else None
    if not isinstance(observed_ref, dict):
        raise E2EPaperOrchestrationError("E2E_PREPARED_CALENDAR_REFERENCE_MISSING")
    observed_path = Path(str(observed_ref.get("path") or "")).expanduser().resolve()
    if (
        not observed_path.is_file()
        or _sha256_file(observed_path) != str(observed_ref.get("sha256") or "")
        or str(payload.get("observed_calendar_path") or "") != str(observed_path)
        or str(payload.get("observed_calendar_sha256") or "")
        != str(observed_ref.get("sha256") or "")
    ):
        raise E2EPaperOrchestrationError("E2E_SCHEDULE_BINDING_OBSERVED_CALENDAR_MISMATCH")

    expected_path = Path(expected_schedule_attestation_path).expanduser().resolve()
    if str(payload.get("execution_schedule_attestation_path") or "") != str(expected_path):
        raise E2EPaperOrchestrationError("E2E_SCHEDULE_BINDING_ATTESTATION_PATH_MISMATCH")
    try:
        schedule = load_verified_official_trading_schedule(
            expected_path,
            expected_sha256=expected_schedule_attestation_sha256,
        )
        expected_execution = next_planned_session(schedule, decision)
    except OfficialTradingScheduleError as exc:
        raise E2EPaperOrchestrationError(
            f"E2E_SCHEDULE_BINDING_SCHEDULE_INVALID:{exc}"
        ) from exc
    if (
        str(payload.get("execution_schedule_attestation_sha256") or "")
        != schedule.attestation_sha256
        or str(payload.get("execution_schedule_source_path") or "")
        != str(schedule.source_document_path.resolve())
        or str(payload.get("execution_schedule_source_sha256") or "")
        != schedule.source_document_sha256
        or str(payload.get("execution_schedule_source_reference") or "")
        != schedule.source_reference
        or expected_execution != execution
    ):
        raise E2EPaperOrchestrationError("E2E_SCHEDULE_BINDING_SCHEDULE_PARENT_MISMATCH")

    return VerifiedPreparedScheduleBinding(
        path=path,
        file_sha256=_sha256_file(path),
        decision_session_date=decision,
        execution_session_date=execution,
        prepared_path=prepared,
        prepared_sha256=_sha256_file(prepared),
        schedule_attestation_path=schedule.attestation_path,
        schedule_attestation_sha256=schedule.attestation_sha256,
    )


__all__ = [
    "SCHEMA_VERSION",
    "VerifiedPreparedScheduleBinding",
    "verify_prepared_schedule_binding",
    "write_prepared_schedule_binding",
]
