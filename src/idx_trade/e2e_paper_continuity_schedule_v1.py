"""Dual-calendar missed-Open continuity transition for forward PAPER."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from . import forward_dividend_v1 as dividend
from . import forward_dividend_runtime_v1_1 as dividend_runtime
from .e2e_operational_guard_v1 import JAKARTA, load_session_dates
from .e2e_paper_continuity_v1 import MISSED_SCHEMA, MISSED_STATUS, MissedExecutionResult
from .e2e_paper_orchestration_v1 import (
    E2EPaperOrchestrationError,
    E2EPaperPaths,
    PREPARED_SCHEMA,
    _atomic_write,
    _canonical_hash,
    _date,
    _historical_dividend_states,
    _read_verified_json,
    _sha256_file,
    _verify_reconciliation,
    _write_meta,
)
from .e2e_paper_schedule_binding_v1 import verify_prepared_schedule_binding
from .forward_dividend_execution_v1_1 import VerifiedDividendCAReconciliation


def _read_missed(path: Path) -> dict[str, Any]:
    payload = _read_verified_json(path, MISSED_SCHEMA)
    body = dict(payload)
    declared = str(body.pop("payload_sha256") or "")
    if not declared or _canonical_hash(body) != declared:
        raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_PAYLOAD_HASH_MISMATCH")
    return payload


def advance_missed_execution_no_certified_open_with_schedule(
    runtime_root: str | Path,
    *,
    prepared_path: str | Path,
    observed_calendar_path: str | Path,
    execution_schedule_attestation_path: str | Path,
    execution_schedule_attestation_sha256: str,
    ca_reconciliation: VerifiedDividendCAReconciliation,
    official_open_root: str | Path | None = None,
    issued_at: datetime | None = None,
) -> MissedExecutionResult:
    """Advance one exact prepared session with zero fills and dual-calendar proof."""

    prepared = Path(prepared_path).expanduser().resolve()
    payload = _read_verified_json(prepared, PREPARED_SCHEMA)
    body = dict(payload)
    declared = str(body.pop("payload_sha256") or "")
    if not declared or _canonical_hash(body) != declared:
        raise E2EPaperOrchestrationError("E2E_PREPARED_PAYLOAD_SHA_MISMATCH")
    if payload.get("status") != "PREPARED_EXECUTION":
        raise E2EPaperOrchestrationError("E2E_PREPARED_STATUS_INVALID")

    decision = _date(payload.get("decision_session_date"))
    execution = _date(payload.get("execution_session_date"))
    eod_inputs = payload.get("eod_inputs")
    calendar_ref = eod_inputs.get("calendar") if isinstance(eod_inputs, dict) else None
    if not isinstance(calendar_ref, dict):
        raise E2EPaperOrchestrationError("E2E_PREPARED_CALENDAR_REFERENCE_MISSING")
    observed = Path(observed_calendar_path).expanduser().resolve()
    if (
        observed != Path(str(calendar_ref.get("path") or "")).expanduser().resolve()
        or not observed.is_file()
        or _sha256_file(observed) != str(calendar_ref.get("sha256") or "")
    ):
        raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_CALENDAR_PARENT_MISMATCH")
    if decision not in load_session_dates(observed):
        raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_DECISION_NOT_OBSERVED")

    binding = verify_prepared_schedule_binding(
        runtime_root,
        prepared_path=prepared,
        expected_schedule_attestation_path=execution_schedule_attestation_path,
        expected_schedule_attestation_sha256=execution_schedule_attestation_sha256,
    )
    if (
        binding.decision_session_date != decision
        or binding.execution_session_date != execution
    ):
        raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_SCHEDULE_BINDING_MISMATCH")

    if official_open_root is not None:
        open_manifest = (
            Path(official_open_root).expanduser().resolve()
            / execution
            / "manifest.json"
        )
        if open_manifest.exists():
            raise E2EPaperOrchestrationError("E2E_CERTIFIED_OPEN_EXISTS_CANNOT_MARK_MISSED")

    paths = E2EPaperPaths.from_root(runtime_root)
    execution_path = paths.execution_dir / f"{execution}.json"
    if execution_path.exists():
        raise E2EPaperOrchestrationError("E2E_EXECUTION_EXISTS_CANNOT_MARK_MISSED")
    missed_path = paths.root / "missed_executions" / f"{execution}.json"
    if missed_path.exists():
        prior = _read_missed(missed_path)
        if (
            str(prior.get("schedule_binding_path") or "") != str(binding.path.resolve())
            or str(prior.get("schedule_binding_sha256") or "") != binding.file_sha256
        ):
            raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_SCHEDULE_PARENT_MISMATCH")
        snapshot_path = Path(str(prior["runtime_snapshot_path"])).expanduser().resolve()
        snapshot = dividend_runtime.load_runtime_snapshot(snapshot_path)
        if snapshot.file_sha256 != str(prior["runtime_snapshot_sha256"]):
            raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_SNAPSHOT_SHA_MISMATCH")
        return MissedExecutionResult(
            missed_path,
            _sha256_file(missed_path),
            snapshot.path,
            snapshot.file_sha256,
            decision,
            execution,
            MISSED_STATUS,
        )

    if not isinstance(ca_reconciliation, VerifiedDividendCAReconciliation):
        raise E2EPaperOrchestrationError("E2E_VERIFIED_CA_RECONCILIATION_REQUIRED")
    _verify_reconciliation(
        ca_reconciliation,
        decision_date=decision,
        execution_date=execution,
        required_tickers=tuple(payload.get("required_tickers") or ()),
    )
    state_snapshot = dividend_runtime.load_latest_runtime_snapshot(paths.root)
    state = state_snapshot.state
    if state.base_state.as_of_session_date != decision:
        raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_STATE_SESSION_MISMATCH")

    advanced = replace(
        state,
        base_state=replace(state.base_state, as_of_session_date=execution),
    )
    advanced = dividend.process_dividend_eod(
        advanced,
        ca_reconciliation.certified_events,
        session_date=execution,
        historical_states_by_date=_historical_dividend_states(paths),
    )
    new_snapshot = dividend_runtime.write_runtime_snapshot(
        paths.root,
        advanced,
        state_snapshot.certified_dividend_registry,
        previous_snapshot=state_snapshot,
    )

    issued = (issued_at or datetime.now(tz=JAKARTA)).astimezone(JAKARTA).isoformat()
    ca_payload = {
        "from_session_date": ca_reconciliation.from_session_date,
        "through_session_date": ca_reconciliation.through_session_date,
        "attestation_path": str(ca_reconciliation.attestation_path.resolve()),
        "attestation_sha256": ca_reconciliation.attestation_sha256,
        "source_path": str(ca_reconciliation.source_path.resolve()),
        "source_sha256": ca_reconciliation.source_sha256,
        "certified_event_ids": sorted(
            event.event_id for event in ca_reconciliation.certified_events
        ),
    }
    audit: dict[str, Any] = {
        "schema_version": MISSED_SCHEMA,
        "status": MISSED_STATUS,
        "decision_session_date": decision,
        "execution_session_date": execution,
        "reason": "NO_CERTIFIED_OFFICIAL_OPEN",
        "prepared_path": str(prepared),
        "prepared_sha256": _sha256_file(prepared),
        "schedule_binding_path": str(binding.path.resolve()),
        "schedule_binding_sha256": binding.file_sha256,
        "execution_schedule_attestation_path": str(binding.schedule_attestation_path.resolve()),
        "execution_schedule_attestation_sha256": binding.schedule_attestation_sha256,
        "prior_runtime_snapshot_path": str(state_snapshot.path.resolve()),
        "prior_runtime_snapshot_sha256": state_snapshot.file_sha256,
        "runtime_snapshot_path": str(new_snapshot.path.resolve()),
        "runtime_snapshot_sha256": new_snapshot.file_sha256,
        "prior_state_sha256": dividend.dividend_aware_state_hash(state),
        "result_state_sha256": dividend.dividend_aware_state_hash(advanced),
        "open_manifest_present": False,
        "prepared_order_expired": True,
        "fills": 0,
        "gross_turnover_idr": 0.0,
        "costs_idr": 0.0,
        "no_retroactive_execution": True,
        "ca_reconciliation": ca_payload,
        "issued_at_jakarta": issued,
        "outcome_access": False,
    }
    audit["payload_sha256"] = _canonical_hash(audit)
    path, sha = _atomic_write(missed_path, audit)

    current_score = payload.get("current_score")
    if not isinstance(current_score, dict):
        raise E2EPaperOrchestrationError("E2E_PREPARED_CURRENT_SCORE_REFERENCE_MISSING")
    _write_meta(
        paths,
        {
            "last_score_manifest_path": str(current_score.get("manifest_path") or ""),
            "last_score_manifest_sha256": str(current_score.get("manifest_sha256") or ""),
            "last_score_session_date": decision,
            "last_execution_session_date": execution,
            "last_execution_path": str(path),
            "last_execution_sha256": sha,
            "last_execution_status": MISSED_STATUS,
            "runtime_snapshot_path": str(new_snapshot.path.resolve()),
            "runtime_snapshot_sha256": new_snapshot.file_sha256,
        },
    )
    return MissedExecutionResult(
        path,
        sha,
        new_snapshot.path,
        new_snapshot.file_sha256,
        decision,
        execution,
        MISSED_STATUS,
    )


__all__ = ["advance_missed_execution_no_certified_open_with_schedule"]
