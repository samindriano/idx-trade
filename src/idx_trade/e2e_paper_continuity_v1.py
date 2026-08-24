"""Fail-closed continuity transitions for missed PAPER executions.

This module records a whole-session execution miss when the exact prepared
execution parent exists but no certified Official Open was available.  It
never creates fills, prices, cash movements, or a replacement execution
artifact.  The immutable state snapshot is advanced only after every parent
and calendar invariant has been checked.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from . import forward_dividend_v1 as dividend
from . import forward_dividend_runtime_v1_1 as dividend_runtime
from .e2e_operational_guard_v1 import JAKARTA, load_session_dates
from .e2e_paper_orchestration_v1 import (
    E2EPaperOrchestrationError,
    E2EPaperPaths,
    PREPARED_SCHEMA,
    _historical_dividend_states,
    _atomic_write,
    _canonical_hash,
    _date,
    _read_verified_json,
    _sha256_file,
    _verify_reconciliation,
    _write_meta,
)
from .forward_dividend_execution_v1_1 import VerifiedDividendCAReconciliation


MISSED_SCHEMA = "idx_trade_e2e_paper_missed_execution_v1"
MISSED_STATUS = "MISSED_EXECUTION_NO_CERTIFIED_OPEN"


@dataclass(frozen=True)
class MissedExecutionResult:
    path: Path
    file_sha256: str
    runtime_snapshot_path: Path
    runtime_snapshot_sha256: str
    decision_session_date: str
    execution_session_date: str
    status: str


def _read_missed(path: Path) -> dict[str, Any]:
    payload = _read_verified_json(path, MISSED_SCHEMA)
    body = dict(payload)
    declared = str(body.pop("payload_sha256") or "")
    if not declared or _canonical_hash(body) != declared:
        raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_PAYLOAD_HASH_MISMATCH")
    return payload


def _official_open_manifest(official_open_root: str | Path | None, execution: str) -> Path | None:
    if official_open_root is None:
        return None
    return Path(official_open_root).expanduser().resolve() / execution / "manifest.json"


def advance_missed_execution_no_certified_open(
    runtime_root: str | Path,
    *,
    prepared_path: str | Path,
    official_calendar_path: str | Path,
    ca_reconciliation: VerifiedDividendCAReconciliation,
    official_open_root: str | Path | None = None,
    issued_at: datetime | None = None,
) -> MissedExecutionResult:
    """Advance state across one exact execution session without an Open.

    The prepared plan remains immutable and is marked expired by a sibling
    audit artifact.  A state snapshot is advanced with zero fills/costs and
    the existing dividend lifecycle only.  The current state must already be
    as-of the decision session; silently bridging an unknown prior gap is not
    permitted.
    """

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
    if not isinstance(eod_inputs, dict):
        raise E2EPaperOrchestrationError("E2E_PREPARED_EOD_REFERENCE_MISSING")
    calendar_ref = eod_inputs.get("calendar")
    if not isinstance(calendar_ref, dict):
        raise E2EPaperOrchestrationError("E2E_PREPARED_CALENDAR_REFERENCE_MISSING")
    calendar = Path(str(calendar_ref.get("path") or "")).expanduser().resolve()
    if calendar != Path(official_calendar_path).expanduser().resolve():
        raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_CALENDAR_PATH_MISMATCH")
    if not calendar.is_file() or _sha256_file(calendar) != str(calendar_ref.get("sha256") or ""):
        raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_CALENDAR_SHA_MISMATCH")
    sessions = load_session_dates(calendar)
    if decision not in sessions or execution not in sessions:
        raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_SESSION_NOT_OFFICIAL")
    decision_index = sessions.index(decision)
    if decision_index + 1 >= len(sessions) or sessions[decision_index + 1] != execution:
        raise E2EPaperOrchestrationError("E2E_MISSED_EXECUTION_NOT_IMMEDIATE_NEXT_SESSION")

    open_manifest = _official_open_manifest(official_open_root, execution)
    if open_manifest is not None and open_manifest.exists():
        raise E2EPaperOrchestrationError("E2E_CERTIFIED_OPEN_EXISTS_CANNOT_MARK_MISSED")

    paths = E2EPaperPaths.from_root(runtime_root)
    execution_path = paths.execution_dir / f"{execution}.json"
    if execution_path.exists():
        raise E2EPaperOrchestrationError("E2E_EXECUTION_EXISTS_CANNOT_MARK_MISSED")
    missed_path = paths.root / "missed_executions" / f"{execution}.json"
    if missed_path.exists():
        prior = _read_missed(missed_path)
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

    advanced_base = replace(state.base_state, as_of_session_date=execution)
    advanced = replace(
        state,
        base_state=advanced_base,
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
        "certified_event_ids": sorted(event.event_id for event in ca_reconciliation.certified_events),
    }
    audit = {
        "schema_version": MISSED_SCHEMA,
        "status": MISSED_STATUS,
        "decision_session_date": decision,
        "execution_session_date": execution,
        "reason": "NO_CERTIFIED_OFFICIAL_OPEN",
        "prepared_path": str(prepared),
        "prepared_sha256": _sha256_file(prepared),
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


__all__ = [
    "MISSED_SCHEMA",
    "MISSED_STATUS",
    "MissedExecutionResult",
    "advance_missed_execution_no_certified_open",
]
