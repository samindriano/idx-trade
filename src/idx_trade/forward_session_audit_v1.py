"""Outcome-blind, read-only audit of one forward trading session.

This module inspects only trusted JSON metadata and raw bytes for hashes.  It
never runs a capture/scorer/executor and never loads parquet values, labels,
realized returns, or a protected outcome vault.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .forward_evidence_health_v1 import (
    ArtifactSpec,
    EvidenceHealthError,
    check_artifact,
    discover_session_artifacts,
    evaluate_session,
    sha256_file,
)
from .official_trading_schedule_v1 import (
    OfficialTradingScheduleError,
    load_verified_official_trading_schedule,
    next_planned_session,
)
from .e2e_paper_schedule_binding_v1 import verify_prepared_schedule_binding


SCHEMA_VERSION = "idx_trade_forward_session_audit_v1"
SUMMARY_SCHEMA_VERSION = "idx_trade_forward_session_audit_summary_v1"

PASS = "PASS"
LEGITIMATE_NOOP = "LEGITIMATE_NOOP"
PENDING_EXPECTED = "PENDING_EXPECTED"
FAIL_CLOSED_EXTERNAL = "FAIL_CLOSED_EXTERNAL"
PROVENANCE_INVALID = "PROVENANCE_INVALID"
IMPLEMENTATION_DEFECT = "IMPLEMENTATION_DEFECT"
NOT_APPLICABLE = "NOT_APPLICABLE"
NOT_READ = "NOT_READ"

STAGES = (
    "official_trading_calendar",
    "runtime_identity",
    "stockbit_scheduled_capture",
    "canonical_eod_capture",
    "v4_x1_scoring",
    "decision_v2",
    "prepared_order",
    "prepared_order_schedule_binding",
    "official_open_evidence",
    "paper_execution",
    "ca_dividend",
    "paperstate_continuity",
    "forward_evidence_health",
    "scheduler_task",
)

_PROTECTED_TOKENS = ("outcome", "realized", "label", "vault")
_PROTECTED_FLAGS = (
    "outcome_access",
    "outcome_accessed",
    "forward_outcomes_accessed",
    "fresh_forward_outcomes_accessed",
    "protected_outcome_accessed",
    "realized_forward_outcome_loaded",
    "real_outcome_access_marker_written",
    "forward_outcome_access_marker_written",
)
_SAFE_TIMESTAMP_FIELDS = (
    "scheduled_at_utc",
    "scheduled_timestamp_utc",
    "scheduled_at",
    "captured_at_utc",
    "capture_timestamp_utc",
    "observed_at_utc",
    "evidence_at_utc",
    "recorded_at_utc",
    "created_at_utc",
    "prepared_at_utc",
    "prepared_timestamp_utc",
    "executed_at_utc",
    "execution_timestamp_utc",
    "official_open_at_utc",
    "run_at_jakarta",
    "capture_timestamp_jakarta",
    "issued_at_jakarta",
)
_SEVERITY = {
    PASS: 0,
    LEGITIMATE_NOOP: 0,
    NOT_APPLICABLE: 0,
    NOT_READ: 1,
    PENDING_EXPECTED: 1,
    FAIL_CLOSED_EXTERNAL: 2,
    PROVENANCE_INVALID: 3,
    IMPLEMENTATION_DEFECT: 4,
}
_SESSION_FIELDS = (
    "session_date",
    "execution_session_date",
    "target_session_date",
    "artifact_session_date",
    "produced_for_session_date",
)
_SUCCESS_STATUSES = frozenset(
    {
        "PASS",
        "COMPLETE",
        "DONE",
        "DATA_READY",
        "CERTIFIED",
        "READY",
        "SUCCESS",
        "EXECUTION_COMPLETE",
        "PREPARED_EXECUTION",
        "ALREADY_CAPTURED",
    }
)
_NOOP_STATUSES = frozenset(
    {
        "LEGITIMATE_NOOP",
        "NOOP",
        "NO_TRADE",
        "NO_TRADES",
        "NO_PREPARED_ORDER",
        "WEEKEND_NO_SESSION",
        "HOLIDAY_NO_SESSION",
        "WEEKEND_OR_HOLIDAY_NOOP",
        "MISSED_EXECUTION_NO_CERTIFIED_OPEN",
    }
)
_PENDING_STATUSES = frozenset(
    {
        "PENDING",
        "PENDING_EXPECTED",
        "WAITING",
        "RETRYING",
        "ACQUISITION_RETRYING",
        "SOURCE_NOT_READY_OR_NO_SESSION",
        "CAPTURE_RETRYING",
    }
)
_FAIL_STATUSES = frozenset(
    {
        "FAIL_CLOSED",
        "FAIL_CLOSED_EXTERNAL",
        "CAPTURE_FAIL_CLOSED",
        "DATA_FAILED",
        "ERROR",
        "FAILED",
    }
)


class SessionAuditError(RuntimeError):
    """Raised for an unsafe or malformed audit input."""


@dataclass(frozen=True)
class SafeMetadata:
    path: Path
    sha256: str
    payload: dict[str, Any]


def _session(value: object) -> str:
    if not isinstance(value, str):
        raise SessionAuditError("SESSION_DATE_INVALID")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise SessionAuditError("SESSION_DATE_INVALID") from exc


def _safe_path(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    lowered = str(path).lower().replace("\\", "/")
    if any(token in part for part in lowered.split("/") for token in _PROTECTED_TOKENS):
        raise SessionAuditError("PROTECTED_METADATA_PATH_REFUSED")
    return path


def _json_object(path: str | Path) -> SafeMetadata:
    safe = _safe_path(path)
    if not safe.is_file():
        raise SessionAuditError("METADATA_MISSING")
    try:
        raw = safe.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SessionAuditError("METADATA_INVALID") from exc
    if not isinstance(payload, dict):
        raise SessionAuditError("METADATA_INVALID")
    for key in _PROTECTED_FLAGS:
        if key in payload and payload[key] is not False:
            raise SessionAuditError("OUTCOME_GUARD_NOT_CLEAN")
    guards = payload.get("guards")
    if isinstance(guards, Mapping):
        for key in _PROTECTED_FLAGS:
            if key in guards and guards[key] is not False:
                raise SessionAuditError("OUTCOME_GUARD_NOT_CLEAN")
    return SafeMetadata(safe, hashlib.sha256(raw).hexdigest(), payload)


def _timestamp(payload: Mapping[str, Any]) -> str | None:
    for key in _SAFE_TIMESTAMP_FIELDS:
        value = payload.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise SessionAuditError(f"TIMESTAMP_INVALID:{key}")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SessionAuditError(f"TIMESTAMP_INVALID:{key}") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise SessionAuditError(f"TIMESTAMP_MISSING_TIMEZONE:{key}")
        return parsed.astimezone(timezone.utc).isoformat()
    return None


def _metadata_identity(payload: Mapping[str, Any], session_date: str) -> str | None:
    present = []
    for key in _SESSION_FIELDS:
        if key in payload:
            value = payload[key]
            if value is None:
                continue
            present.append(_session(value))
    if not present:
        return None
    if any(value != session_date for value in present):
        raise SessionAuditError("SESSION_IDENTITY_MISMATCH")
    return session_date


def _metadata_identity_for_fields(
    payload: Mapping[str, Any],
    expected_session_date: str,
    fields: Sequence[str],
) -> str | None:
    present: list[str] = []
    for key in fields:
        if key not in payload or payload[key] is None:
            continue
        present.append(_session(payload[key]))
    if not present:
        return None
    if any(value != expected_session_date for value in present):
        raise SessionAuditError("SESSION_IDENTITY_MISMATCH")
    return expected_session_date


def _status(payload: Mapping[str, Any]) -> str | None:
    for key in ("status", "state", "result", "capture_status", "stage_status"):
        value = payload.get(key)
        if not isinstance(value, str):
            continue
        upper = value.upper()
        if upper in _SUCCESS_STATUSES:
            return PASS
        if upper in _NOOP_STATUSES:
            return LEGITIMATE_NOOP
        if upper in _PENDING_STATUSES:
            return PENDING_EXPECTED
        if upper in _FAIL_STATUSES or "FAIL_CLOSED" in upper:
            return FAIL_CLOSED_EXTERNAL
        if "TAMPER" in upper or "MISMATCH" in upper or "INVALID" in upper:
            return PROVENANCE_INVALID
        if "DEFECT" in upper:
            return IMPLEMENTATION_DEFECT
    return None


def _stage(
    stage: str,
    expected: str,
    session_date: str,
    status: str,
    *,
    observed: Mapping[str, Any] | None = None,
    path: Path | None = None,
    sha256: str | None = None,
    scheduled_timestamp: str | None = None,
    evidence_timestamp: str | None = None,
    notes: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "stage": stage,
        "expected": expected,
        "observed": dict(observed or {}),
        "status": status,
        "session_date": session_date,
        "artifact_path": str(path) if path else None,
        "artifact_sha256": sha256,
        "scheduled_timestamp_utc": scheduled_timestamp,
        "evidence_timestamp_utc": evidence_timestamp,
        "causal_notes": list(notes),
    }


def _set_stricter(stage: dict[str, Any], status: str, note: str) -> None:
    """Apply cross-stage evidence without ever downgrading severity."""

    current = str(stage.get("status"))
    if _SEVERITY.get(status, 99) >= _SEVERITY.get(current, 99):
        stage["status"] = status
    else:
        stage.setdefault("causal_notes", []).append(
            f"DOWNGRADE_REFUSED:{current}->{status}"
        )
    if note not in stage.setdefault("causal_notes", []):
        stage["causal_notes"].append(note)


def _resolve_noop(stage: dict[str, Any], note: str) -> None:
    """Resolve only an unstarted/pending stage after a certified no-op.

    A legitimate no-trade decision can make a downstream artifact genuinely
    not applicable.  Existing external failures, provenance failures, and
    implementation defects remain immutable and are never downgraded.
    """

    if stage.get("status") in {NOT_READ, PENDING_EXPECTED, PASS, LEGITIMATE_NOOP, NOT_APPLICABLE}:
        stage["status"] = NOT_APPLICABLE
    if note not in stage.setdefault("causal_notes", []):
        stage["causal_notes"].append(note)


def _safe_observed(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Expose operational identity only; never copy arbitrary metadata."""

    keys = (
        "status",
        "runtime_sha256",
        "expected_runtime_sha256",
        "active_runtime_changed",
        "transport",
        "authority",
        "upstream_path",
        "field_semantics",
        "transport_policy",
        "task_name",
        "runner",
        "module",
        "is_trading_session",
        "classification",
        "trade_count",
        "duplicate_count",
        "continuity_valid",
        "paperstate_continuity_valid",
        "stale_artifact",
    )
    return {key: payload[key] for key in keys if key in payload}


def _verify_declared_hashes(metadata: SafeMetadata) -> list[str]:
    """Verify declared sibling artifacts by bytes, without parsing their values."""

    failures: list[str] = []
    for key, value in metadata.payload.items():
        if not key.endswith("_path") or not isinstance(value, str):
            continue
        hash_key = f"{key[:-5]}_sha256"
        declared = metadata.payload.get(hash_key)
        if not isinstance(declared, str):
            continue
        child = _safe_path(Path(value) if Path(value).is_absolute() else metadata.path.parent / value)
        if not child.is_file():
            failures.append(f"DECLARED_ARTIFACT_MISSING:{key}")
            continue
        if sha256_file(child) != declared.lower():
            failures.append(f"DECLARED_ARTIFACT_SHA256_MISMATCH:{key}")
    return failures


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    body = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _verify_payload_hash(payload: Mapping[str, Any], label: str) -> str | None:
    declared = payload.get("payload_sha256")
    if not isinstance(declared, str) or not declared:
        return f"{label}_PAYLOAD_HASH_MISSING"
    body = dict(payload)
    body.pop("payload_sha256", None)
    if _canonical_hash(body) != declared.lower():
        return f"{label}_PAYLOAD_HASH_MISMATCH"
    return None


def _verify_named_payload_hash(
    payload: Mapping[str, Any], field: str, label: str
) -> str | None:
    declared = payload.get(field)
    if not isinstance(declared, str) or not declared:
        return f"{label}_HASH_MISSING"
    body = dict(payload)
    body.pop(field, None)
    if _canonical_hash(body) != declared.lower():
        return f"{label}_HASH_MISMATCH"
    return None


def _verify_file_reference(
    metadata_path: Path,
    reference: object,
    label: str,
) -> list[str]:
    if not isinstance(reference, Mapping):
        return [f"{label}_REFERENCE_MISSING"]
    raw_path = reference.get("path")
    declared_sha = reference.get("sha256")
    if not isinstance(raw_path, str) or not isinstance(declared_sha, str):
        return [f"{label}_REFERENCE_INVALID"]
    try:
        child = _safe_path(
            Path(raw_path)
            if Path(raw_path).is_absolute()
            else metadata_path.parent / raw_path
        )
    except SessionAuditError as exc:
        return [f"{label}_{exc}"]
    if not child.is_file():
        return [f"{label}_MISSING"]
    if sha256_file(child) != declared_sha.lower():
        return [f"{label}_SHA256_MISMATCH"]
    return []


def _validate_prepared_contract(
    payload: Mapping[str, Any],
    *,
    execution_session_date: str,
    metadata_path: Path,
) -> Iterable[str]:
    notes: list[str] = []
    if payload.get("outcome_access") is not False:
        notes.append("PREPARED_OUTCOME_ACCESS_GUARD_INVALID")
    hash_failure = _verify_payload_hash(payload, "PREPARED")
    if hash_failure:
        notes.append(hash_failure)
    if payload.get("schema_version") != "idx_trade_e2e_paper_prepared_execution_v1":
        notes.append("PREPARED_SCHEMA_MISMATCH")
    decision_value = payload.get("decision_session_date")
    execution_value = payload.get("execution_session_date")
    try:
        decision = _session(decision_value)
        execution = _session(execution_value)
    except SessionAuditError:
        notes.append("PREPARED_SESSION_IDENTITY_INVALID")
    else:
        if execution != execution_session_date:
            notes.append("PREPARED_EXECUTION_SESSION_MISMATCH")
        if decision == execution:
            notes.append("DECISION_AND_EXECUTION_SESSION_MUST_DIFFER")
        decision_plan = payload.get("decision_plan")
        if isinstance(decision_plan, Mapping):
            if decision_plan.get("decision_session_date") != decision:
                notes.append("PREPARED_DECISION_PARENT_MISMATCH")
            declared_decision_hash = payload.get("decision_plan_sha256")
            if not isinstance(declared_decision_hash, str) or _canonical_hash(decision_plan) != declared_decision_hash.lower():
                notes.append("PREPARED_DECISION_PLAN_SHA256_MISMATCH")
        else:
            notes.append("PREPARED_DECISION_PARENT_MISSING")
        execution_plan = payload.get("execution_plan")
        if not isinstance(execution_plan, Mapping):
            notes.append("PREPARED_EXECUTION_PLAN_MISSING")
        else:
            if execution_plan.get("decision_session_date") != decision:
                notes.append("PREPARED_EXECUTION_PLAN_DECISION_MISMATCH")
            if execution_plan.get("execution_session_date") != execution:
                notes.append("PREPARED_EXECUTION_PLAN_EXECUTION_MISMATCH")
            declared_execution_hash = payload.get("execution_plan_sha256")
            if not isinstance(declared_execution_hash, str) or _canonical_hash(execution_plan) != declared_execution_hash.lower():
                notes.append("PREPARED_EXECUTION_PLAN_SHA256_MISMATCH")
        current_score = payload.get("current_score")
        if isinstance(current_score, Mapping):
            if current_score.get("session_date") != decision:
                notes.append("PREPARED_SCORE_DECISION_SESSION_MISMATCH")
            score_path = current_score.get("manifest_path") or current_score.get("path")
            score_sha = current_score.get("manifest_sha256") or current_score.get("sha256")
            if score_path is None or score_sha is None:
                notes.append("PREPARED_SCORE_PARENT_REFERENCE_MISSING")
            else:
                notes.extend(
                    _verify_file_reference(
                        metadata_path,
                        {"path": score_path, "sha256": score_sha},
                        "PREPARED_SCORE",
                    )
                )
                try:
                    score_file = _safe_path(
                        Path(score_path)
                        if Path(score_path).is_absolute()
                        else metadata_path.parent / str(score_path)
                    )
                    score_metadata = _json_object(score_file)
                    _metadata_identity_for_fields(
                        score_metadata.payload,
                        decision,
                        ("decision_session_date", "session_date"),
                    )
                except SessionAuditError as exc:
                    notes.append(f"PREPARED_SCORE_PARENT_IDENTITY:{exc}")
        else:
            notes.append("PREPARED_SCORE_PARENT_MISSING")
        declared_next = payload.get("next_official_session_date")
        if declared_next is not None and declared_next != execution:
            notes.append("PREPARED_NEXT_OFFICIAL_SESSION_MISMATCH")
    if payload.get("status") != "PREPARED_EXECUTION":
        notes.append("PREPARED_STATUS_MISMATCH")
    eod_inputs = payload.get("eod_inputs")
    if not isinstance(eod_inputs, Mapping):
        notes.append("PREPARED_EOD_PARENT_MISSING")
    else:
        for key in ("calendar", "ohlcv", "model_input"):
            notes.extend(_verify_file_reference(metadata_path, eod_inputs.get(key), f"PREPARED_EOD_{key.upper()}"))
    return notes


def _validate_execution_contract(
    payload: Mapping[str, Any],
    *,
    prepared_path: Path | None,
    prepared_sha256: str | None,
    decision_session_date: str | None,
    execution_session_date: str,
    open_metadata: SafeMetadata | None,
) -> Iterable[str]:
    notes: list[str] = []
    if payload.get("schema_version") != "idx_trade_e2e_paper_execution_v1":
        notes.append("EXECUTION_SCHEMA_MISMATCH")
    if payload.get("status") == "EXECUTION_COMPLETE":
        hash_failure = _verify_payload_hash(payload, "EXECUTION")
        if hash_failure:
            notes.append(hash_failure)
    if payload.get("execution_session_date") != execution_session_date:
        notes.append("EXECUTION_SESSION_MISMATCH")
    if decision_session_date is not None and payload.get("decision_session_date") != decision_session_date:
        notes.append("EXECUTION_DECISION_SESSION_MISMATCH")
    if prepared_path is not None:
        if payload.get("prepared_path") != str(prepared_path.resolve()):
            notes.append("EXECUTION_PREPARED_PATH_MISMATCH")
        if prepared_sha256 and payload.get("prepared_sha256") != prepared_sha256:
            notes.append("EXECUTION_PREPARED_SHA256_MISMATCH")
    elif payload.get("status") == "EXECUTION_COMPLETE":
        notes.append("EXECUTION_PREPARED_PARENT_UNAVAILABLE")
    if open_metadata is not None:
        if payload.get("open_manifest_path") != str(open_metadata.path.resolve()):
            notes.append("EXECUTION_OPEN_MANIFEST_PATH_MISMATCH")
        if payload.get("open_manifest_sha256") != open_metadata.sha256:
            notes.append("EXECUTION_OPEN_MANIFEST_SHA256_MISMATCH")
    elif payload.get("status") == "EXECUTION_COMPLETE":
        notes.append("EXECUTION_OPEN_PARENT_UNAVAILABLE")
    runtime_path = payload.get("runtime_snapshot_path")
    runtime_sha = payload.get("runtime_snapshot_sha256")
    if not isinstance(runtime_path, str) or not isinstance(runtime_sha, str):
        notes.append("EXECUTION_RUNTIME_SNAPSHOT_REFERENCE_MISSING")
    else:
        notes.extend(_verify_file_reference(Path(str(payload.get("prepared_path") or ".")).parent, {"path": runtime_path, "sha256": runtime_sha}, "EXECUTION_RUNTIME_SNAPSHOT"))
    return notes


def _validate_runtime_snapshot(payload: Mapping[str, Any]) -> Iterable[str]:
    if payload.get("schema_version") != "idx_trade_forward_dividend_runtime_state_v1_1":
        yield "RUNTIME_SNAPSHOT_SCHEMA_MISMATCH"
    if not isinstance(payload.get("state"), Mapping):
        yield "RUNTIME_SNAPSHOT_STATE_MISSING"
    if not isinstance(payload.get("hashes"), Mapping):
        yield "RUNTIME_SNAPSHOT_HASHES_MISSING"
    failure = _verify_named_payload_hash(payload, "snapshot_payload_sha256", "RUNTIME_SNAPSHOT")
    if failure:
        yield failure


def _validate_schedule_binding(
    payload: Mapping[str, Any],
    *,
    binding_path: Path,
    prepared_path: Path,
    prepared_payload: Mapping[str, Any],
    execution_session_date: str,
) -> Iterable[str]:
    notes: list[str] = []
    if payload.get("schema_version") != "idx_trade_e2e_prepared_schedule_binding_v1":
        notes.append("PREPARED_SCHEDULE_BINDING_SCHEMA_MISMATCH")
    failure = _verify_payload_hash(payload, "SCHEDULE_BINDING")
    if failure:
        notes.append(failure)
    decision = prepared_payload.get("decision_session_date")
    if payload.get("decision_session_date") != decision or payload.get("execution_session_date") != execution_session_date:
        notes.append("PREPARED_SCHEDULE_BINDING_SESSION_MISMATCH")
    if payload.get("prepared_path") != str(prepared_path.resolve()) or payload.get("prepared_sha256") != sha256_file(prepared_path):
        notes.append("PREPARED_SCHEDULE_BINDING_PREPARED_PARENT_MISMATCH")
    eod_inputs = prepared_payload.get("eod_inputs")
    observed_calendar = eod_inputs.get("calendar") if isinstance(eod_inputs, Mapping) else None
    if not isinstance(observed_calendar, Mapping):
        notes.append("PREPARED_SCHEDULE_BINDING_CALENDAR_REFERENCE_MISSING")
    else:
        if payload.get("observed_calendar_path") != str(Path(str(observed_calendar.get("path") or "")).resolve()):
            notes.append("PREPARED_SCHEDULE_BINDING_OBSERVED_CALENDAR_PATH_MISMATCH")
        if payload.get("observed_calendar_sha256") != observed_calendar.get("sha256"):
            notes.append("PREPARED_SCHEDULE_BINDING_OBSERVED_CALENDAR_SHA256_MISMATCH")
        if not Path(str(observed_calendar.get("path") or "")).is_file() or sha256_file(Path(str(observed_calendar.get("path") or ""))) != observed_calendar.get("sha256"):
            notes.append("PREPARED_SCHEDULE_BINDING_OBSERVED_CALENDAR_BYTES_MISMATCH")
    attestation_raw = payload.get("execution_schedule_attestation_path")
    attestation_sha = payload.get("execution_schedule_attestation_sha256")
    try:
        attestation = _safe_path(str(attestation_raw))
        canonical_binding_path = binding_path.parent.parent / "prepared_schedule" / f"{decision}.json"
        if binding_path != canonical_binding_path.resolve():
            notes.append("PREPARED_SCHEDULE_BINDING_PATH_NONCANONICAL")
        verify_prepared_schedule_binding(
            binding_path.parent.parent,
            prepared_path=prepared_path,
            expected_schedule_attestation_path=attestation,
            expected_schedule_attestation_sha256=str(attestation_sha or ""),
        )
        schedule = load_verified_official_trading_schedule(attestation, expected_sha256=str(attestation_sha or ""))
        if next_planned_session(schedule, str(decision)) != execution_session_date:
            notes.append("PREPARED_SCHEDULE_BINDING_NEXT_SESSION_MISMATCH")
        if payload.get("execution_schedule_source_path") != str(schedule.source_document_path.resolve()):
            notes.append("PREPARED_SCHEDULE_BINDING_SOURCE_PATH_MISMATCH")
        if payload.get("execution_schedule_source_sha256") != schedule.source_document_sha256:
            notes.append("PREPARED_SCHEDULE_BINDING_SOURCE_SHA256_MISMATCH")
        if payload.get("execution_schedule_source_reference") != schedule.source_reference:
            notes.append("PREPARED_SCHEDULE_BINDING_SOURCE_REFERENCE_MISMATCH")
    except (SessionAuditError, OfficialTradingScheduleError, OSError, ValueError) as exc:
        notes.append(f"PREPARED_SCHEDULE_BINDING_SCHEDULE_INVALID:{exc}")
    return notes


def _decision_has_no_operational_work(payload: Mapping[str, Any]) -> bool:
    """Return true only for an explicit empty canonical execution plan."""

    plan = payload.get("execution_plan")
    if not isinstance(plan, Mapping):
        return False
    for key in ("pending_buys", "pending_sells", "pending_orders", "open_orders"):
        value = plan.get(key)
        if value not in (None, [], {}):
            return False
    for key in ("sells", "effective_buy_intents", "target_positions"):
        if plan.get(key) != []:
            return False
    sizing = plan.get("sizing_plan")
    if not isinstance(sizing, Mapping) or sizing.get("entries") != []:
        return False
    return True


def _validate_missed_execution_contract(
    payload: Mapping[str, Any],
    *,
    prepared_path: Path | None,
    prepared_sha256: str | None,
    expected_binding_path: Path | None,
    execution_session_date: str,
) -> Iterable[str]:
    if payload.get("schema_version") != "idx_trade_e2e_paper_missed_execution_v1":
        yield "MISSED_EXECUTION_SCHEMA_MISMATCH"
    if payload.get("status") != "MISSED_EXECUTION_NO_CERTIFIED_OPEN":
        yield "MISSED_EXECUTION_STATUS_MISMATCH"
    failure = _verify_payload_hash(payload, "MISSED_EXECUTION")
    if failure:
        yield failure
    if payload.get("execution_session_date") != execution_session_date:
        yield "MISSED_EXECUTION_SESSION_MISMATCH"
    if prepared_path is None or payload.get("prepared_path") != str(prepared_path.resolve()) or payload.get("prepared_sha256") != prepared_sha256:
        yield "MISSED_EXECUTION_PREPARED_PARENT_MISMATCH"
    if expected_binding_path is None or payload.get("schedule_binding_path") != str(expected_binding_path.resolve()):
        yield "MISSED_EXECUTION_SCHEDULE_BINDING_PARENT_MISMATCH"
    if payload.get("reason") != "NO_CERTIFIED_OFFICIAL_OPEN":
        yield "MISSED_EXECUTION_REASON_MISMATCH"
    if payload.get("open_manifest_present") is not False or payload.get("no_retroactive_execution") is not True:
        yield "MISSED_EXECUTION_RETROACTIVE_OR_OPEN_FLAG_INVALID"
    if payload.get("fills") != 0 or payload.get("gross_turnover_idr") != 0.0 or payload.get("costs_idr") != 0.0:
        yield "MISSED_EXECUTION_NONZERO_EXECUTION_VALUES"


def _find_prepared_parent(
    e2e_root: Path | None,
    execution_session_date: str,
    explicit_path: str | Path | None,
) -> Path | None:
    if explicit_path is not None:
        return _safe_path(explicit_path)
    if e2e_root is None:
        return None
    candidates: list[Path] = []
    for path in sorted((e2e_root / "prepared").glob("*.json")):
        try:
            metadata = _json_object(path)
        except SessionAuditError:
            continue
        if metadata.payload.get("execution_session_date") == execution_session_date:
            candidates.append(path)
    if len(candidates) > 1:
        raise SessionAuditError("PREPARED_PARENT_AMBIGUOUS")
    return candidates[0] if candidates else None


def _artifact_stage(
    *,
    stage: str,
    expected: str,
    session_date: str,
    path: str | Path | None,
    required: bool = True,
    expected_status: str | None = None,
    expected_fields: Sequence[tuple[str, object]] = (),
    session_fields: Sequence[str] = ("session_date",),
    require_outcome_clean: bool = True,
    status_required: bool = True,
    extra_validator: Any = None,
) -> tuple[dict[str, Any], SafeMetadata | None]:
    if path is None:
        return (
            _stage(stage, expected, session_date, NOT_READ, notes=("METADATA_INPUT_NOT_DECLARED",)),
            None,
        )
    try:
        safe = _safe_path(path)
        result = check_artifact(
            ArtifactSpec(
                name=stage,
                path=safe,
                required=required,
                expected_status=expected_status,
                expected_fields=tuple(expected_fields),
                session_fields=tuple(session_fields),
                require_outcome_clean=require_outcome_clean,
            ),
            session_date=session_date,
        )
        observed_status = result["status"]
        if observed_status == "COMPLETE":
            stage_payload = _json_object(safe).payload
            mapped_status = _status(stage_payload)
            if mapped_status is None:
                status_declared = any(
                    isinstance(stage_payload.get(key), str)
                    for key in ("status", "state", "result", "capture_status", "stage_status")
                )
                if status_required or status_declared:
                    return (
                        _stage(
                            stage,
                            expected,
                            session_date,
                            PROVENANCE_INVALID,
                            path=safe,
                            sha256=result.get("observed_sha256"),
                            notes=("STATUS_MISSING_OR_UNKNOWN",),
                        ),
                        None,
                    )
                mapped_status = PASS
            observed_status = mapped_status
        elif observed_status == "PENDING_EXPECTED":
            observed_status = PENDING_EXPECTED
        elif observed_status == "PROVENANCE_INVALID":
            return (
                _stage(
                    stage,
                    expected,
                    session_date,
                    PROVENANCE_INVALID,
                    path=safe,
                    sha256=result.get("observed_sha256"),
                    notes=(str(result.get("reason") or "PROVENANCE_INVALID"),),
                ),
                None,
            )
        if not safe.is_file():
            observed_status = PENDING_EXPECTED if required else NOT_READ
            return (
                _stage(stage, expected, session_date, observed_status, path=safe, notes=("ARTIFACT_MISSING",)),
                None,
            )
        metadata = _json_object(safe)
        _metadata_identity_for_fields(metadata.payload, session_date, session_fields)
        timestamp = _evidence_timestamp(metadata.payload)
        notes: list[str] = []
        declared_failures = _verify_declared_hashes(metadata)
        if declared_failures:
            return (
                _stage(
                    stage,
                    expected,
                    session_date,
                    PROVENANCE_INVALID,
                    observed=_safe_observed(metadata.payload),
                    path=metadata.path,
                    sha256=metadata.sha256,
                    evidence_timestamp=timestamp,
                    notes=tuple(declared_failures),
                ),
                metadata,
            )
        if extra_validator is not None:
            extra_notes = list(extra_validator(metadata.payload))
            if extra_notes:
                return (
                    _stage(
                        stage,
                        expected,
                        session_date,
                        PROVENANCE_INVALID,
                        observed=_safe_observed(metadata.payload),
                        path=metadata.path,
                        sha256=metadata.sha256,
                        evidence_timestamp=timestamp,
                        notes=tuple(extra_notes),
                    ),
                    metadata,
                )
        if observed_status == PASS and metadata.payload.get("status") in _NOOP_STATUSES:
            observed_status = LEGITIMATE_NOOP
        return (
            _stage(
                stage,
                expected,
                session_date,
                observed_status,
                observed=_safe_observed(metadata.payload),
                path=metadata.path,
                sha256=metadata.sha256,
                scheduled_timestamp=_timestamp_for(metadata.payload, "scheduled_at_utc", "scheduled_timestamp_utc", "scheduled_at"),
                evidence_timestamp=timestamp,
                notes=notes,
            ),
            metadata,
        )
    except (EvidenceHealthError, SessionAuditError, OSError) as exc:
        reason = str(exc)
        status = PROVENANCE_INVALID if any(token in reason for token in ("INVALID", "MISMATCH", "GUARD", "REFUSED", "TIMESTAMP")) else FAIL_CLOSED_EXTERNAL
        return (
            _stage(stage, expected, session_date, status, path=Path(path) if path else None, notes=(reason,)),
            None,
        )


def _timestamp_for(payload: Mapping[str, Any], *keys: str) -> str | None:
    subset = {key: payload[key] for key in keys if key in payload}
    return _timestamp(subset)


def _evidence_timestamp(payload: Mapping[str, Any]) -> str | None:
    """Choose the event timestamp without confusing preparation and execution."""

    for keys in (
        ("executed_at_utc", "execution_timestamp_utc"),
        ("prepared_at_utc", "prepared_timestamp_utc"),
        ("official_open_at_utc",),
        ("captured_at_utc", "capture_timestamp_utc"),
        ("evidence_at_utc", "observed_at_utc", "recorded_at_utc", "created_at_utc"),
        ("run_at_jakarta",),
        ("capture_timestamp_jakarta", "issued_at_jakarta"),
        ("scheduled_at_utc", "scheduled_timestamp_utc", "scheduled_at"),
    ):
        value = _timestamp_for(payload, *keys)
        if value is not None:
            return value
    return None


def _validate_open_contract(payload: Mapping[str, Any]) -> Iterable[str]:
    expected = {
        "authority": "IDX",
        "upstream_path": "TradingSummary/GetStockSummary",
        "field_semantics": "IDX_OFFICIAL_OPENPRICE",
        "transport_policy": "DIRECT_IDX_THEN_ZAPI_RAW_V1",
        "fallback_policy": "NONE",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            yield f"OFFICIAL_OPEN_CONTRACT_MISMATCH:{key}"
    if payload.get("execution_grade") is not True:
        yield "OFFICIAL_OPEN_EXECUTION_GRADE_MISSING"
    for key in ("execution_field", "open_field", "price_field"):
        value = payload.get(key)
        if value in {"FirstTrade", "IEP", "IEV"}:
            yield f"FORBIDDEN_OPEN_FIELD:{value}"
    for key in ("duplicate_key_count", "duplicate_count"):
        value = payload.get(key)
        if isinstance(value, int) and value > 0:
            yield f"DUPLICATE_OFFICIAL_OPEN_KEYS:{key}"
    if payload.get("retroactive_fill") is True or payload.get("backdated_fill") is True:
        yield "RETROACTIVE_OFFICIAL_OPEN_REJECTED"
    text = json.dumps(payload, sort_keys=True).lower()
    for forbidden in ("firsttrade", "iep", "iev", "generic_ohlc"):
        if forbidden in text:
            yield f"FORBIDDEN_OPEN_SEMANTIC:{forbidden}"


def _validate_runtime_identity(payload: Mapping[str, Any]) -> Iterable[str]:
    expected = payload.get("expected_runtime_sha256")
    observed = payload.get("runtime_sha256")
    if expected is not None and observed != expected:
        yield "RUNTIME_SHA256_MISMATCH"
    if payload.get("active_runtime_changed") is True:
        yield "ACTIVE_RUNTIME_CHANGED"


def _validate_scheduler(payload: Mapping[str, Any]) -> Iterable[str]:
    runner = str(
        payload.get("runner")
        or payload.get("action")
        or payload.get("task_action")
        or ""
    )
    module = str(
        payload.get("module")
        or payload.get("runtime_module")
        or payload.get("python_module")
        or ""
    )
    if "scripts/run_official_open_capture.ps1" not in runner.replace("\\", "/"):
        yield "SCHEDULER_RUNNER_MISMATCH"
    if "run_official_open_capture_v2.ps1" in runner.replace("\\", "/"):
        yield "SCHEDULER_RUNNER_WRONG_VERSION"
    if "official_open_capture_runtime_v2" not in module:
        yield "SCHEDULER_RUNTIME_MODULE_BINDING_MISSING"
    if payload.get("task_name") not in {None, "IDXTrade-E2E-OfficialOpen"}:
        yield "SCHEDULER_TASK_MISMATCH"
    required_times = {"09:02", "09:07", "09:12", "09:17", "09:22"}
    triggers = {str(item)[:5] for item in payload.get("triggers", [])} if isinstance(payload.get("triggers"), list) else set()
    if triggers and not required_times.issubset(triggers):
        yield "SCHEDULER_RETRY_TRIGGER_MISSING"
    if payload.get("start_when_available") is False:
        yield "SCHEDULER_START_WHEN_AVAILABLE_DISABLED"
    if payload.get("multiple_instances") not in {None, "IgnoreNew"}:
        yield "SCHEDULER_MULTIPLE_INSTANCE_POLICY_MISMATCH"
    if payload.get("network_required") is False:
        yield "SCHEDULER_NETWORK_REQUIREMENT_MISSING"


def _validate_state_lineage(payload: Mapping[str, Any]) -> Iterable[str]:
    for key in ("continuity_valid", "paperstate_continuity_valid"):
        if key in payload and payload[key] is not True:
            yield "PAPERSTATE_CONTINUITY_BREAK"
    if payload.get("stale_artifact") is True:
        yield "STALE_ARTIFACT_REUSE"
    for key in ("artifact_session_date", "produced_for_session_date"):
        if key in payload and payload[key] != payload.get("session_date", payload.get("execution_session_date")):
            yield "STALE_OR_WRONG_SESSION_ARTIFACT"


def _validate_decision_execution_link(
    payload: Mapping[str, Any],
    *,
    decision_session_date: str | None,
    execution_session_date: str,
) -> Iterable[str]:
    if decision_session_date is not None and payload.get("decision_session_date") not in {None, decision_session_date}:
        yield "DECISION_EXECUTION_PARENT_MISMATCH"
    declared_execution = payload.get("execution_session_date", payload.get("session_date"))
    if declared_execution != execution_session_date:
        yield "EXECUTION_SESSION_MISMATCH"


def _known_path(root: Path | None, *parts: str) -> Path | None:
    if root is None:
        return None
    return root.joinpath(*parts)


def _map_health_status(value: str) -> str:
    return {
        "COMPLETE": PASS,
        "PENDING_EXPECTED": PENDING_EXPECTED,
        "FAIL_CLOSED_EXTERNAL": FAIL_CLOSED_EXTERNAL,
        "PROVENANCE_INVALID": PROVENANCE_INVALID,
        "STATE_TRANSITION_BLOCKED": IMPLEMENTATION_DEFECT,
        "ACQUISITION_RETRYING": PENDING_EXPECTED,
    }.get(value, PENDING_EXPECTED)


def _aggregate(calendar_status: str, stages: Sequence[Mapping[str, Any]]) -> tuple[str, list[str]]:
    if calendar_status == LEGITIMATE_NOOP:
        return "NON_TRADING_SESSION", []
    statuses = [str(item["status"]) for item in stages]
    blockers = [
        f"{item['stage']}:{item['status']}:{';'.join(item.get('causal_notes', []))}"
        for item in stages
        if item["status"] not in {PASS, LEGITIMATE_NOOP, NOT_APPLICABLE}
    ]
    if IMPLEMENTATION_DEFECT in statuses:
        return "SESSION_IMPLEMENTATION_DEFECT", blockers
    if PROVENANCE_INVALID in statuses:
        return "SESSION_PROVENANCE_INVALID", blockers
    if any(
        item.get("observed", {}).get("continuity_transition") == "MISSED_EXECUTION_NO_CERTIFIED_OPEN"
        for item in stages
        if isinstance(item.get("observed"), Mapping)
    ):
        return "SESSION_MISSED_EXECUTION_NO_CERTIFIED_OPEN", blockers
    if FAIL_CLOSED_EXTERNAL in statuses:
        return "SESSION_FAIL_CLOSED_EXTERNAL", blockers
    if PENDING_EXPECTED in statuses or NOT_READ in statuses:
        return "SESSION_PENDING_EXPECTED", blockers
    if LEGITIMATE_NOOP in statuses:
        return "SESSION_HEALTHY_LEGITIMATE_NOOP", blockers
    return "SESSION_HEALTHY", blockers


def audit_session(
    execution_session_date: str,
    *,
    forward_monitoring_root: str | Path | None = None,
    e2e_runtime_root: str | Path | None = None,
    calendar_metadata: str | Path | None = None,
    runtime_identity: str | Path | None = None,
    stockbit_capture: str | Path | None = None,
    ca_dividend: str | Path | None = None,
    scheduler_metadata: str | Path | None = None,
    prepared_metadata: str | Path | None = None,
    schedule_binding_metadata: str | Path | None = None,
    reported_at_utc: str = "2026-01-01T00:00:00+00:00",
) -> dict[str, Any]:
    """Audit one execution session using the accepted decision t -> T graph.

    ``execution_session_date`` is the ledger anchor.  A verified prepared
    parent identifies decision session ``t`` and is the only authority used to
    bind EOD, score, and Decision artifacts to that earlier session.
    """

    session = _session(execution_session_date)
    forward_root = Path(forward_monitoring_root).expanduser().resolve() if forward_monitoring_root else None
    e2e_root = Path(e2e_runtime_root).expanduser().resolve() if e2e_runtime_root else None
    calendar_stage, calendar_meta = _artifact_stage(
        stage="official_trading_calendar",
        expected="EXACT_OFFICIAL_CALENDAR_CLASSIFICATION",
        session_date=session,
        path=calendar_metadata,
        require_outcome_clean=False,
        extra_validator=lambda p: ("CALENDAR_SESSION_DATE_MISSING",) if "session_date" not in p else (),
    )
    stage_by_name: dict[str, dict[str, Any]] = {
        "official_trading_calendar": calendar_stage,
    }
    is_nontrading = bool(
        calendar_stage["status"] == PASS
        and calendar_meta
        and calendar_meta.payload.get("is_trading_session") is False
    )
    if is_nontrading:
        for stage_name in STAGES[1:]:
            stage_by_name[stage_name] = _stage(
                stage_name,
                "NOT_RUN_ON_NON_TRADING_SESSION",
                session,
                NOT_APPLICABLE,
                notes=("NON_TRADING_SESSION",),
            )
        stages = [stage_by_name[name] for name in STAGES]
        return _report(session, "NON_TRADING_SESSION", stages, [], reported_at_utc, None)

    runtime_stage, _ = _artifact_stage(
        stage="runtime_identity",
        expected="DEPLOYED_RUNTIME_IDENTITY_AND_SHA",
        session_date=session,
        path=runtime_identity,
        require_outcome_clean=False,
        extra_validator=_validate_runtime_identity,
    )
    stage_by_name["runtime_identity"] = runtime_stage
    stockbit_stage, _ = _artifact_stage(
        stage="stockbit_scheduled_capture",
        expected="SCHEDULED_STOCKBIT_CAPTURE_METADATA",
        session_date=session,
        path=stockbit_capture,
        require_outcome_clean=True,
    )
    stage_by_name["stockbit_scheduled_capture"] = stockbit_stage

    try:
        selected_prepared = _find_prepared_parent(e2e_root, session, prepared_metadata)
        prepared_resolution_error = None
    except SessionAuditError as exc:
        selected_prepared = None
        prepared_resolution_error = str(exc)

    if prepared_resolution_error:
        prepared_stage = _stage(
            "prepared_order",
            "PREPARED_ORDER_BOUND_TO_EXECUTION_SESSION",
            session,
            PROVENANCE_INVALID,
            notes=(prepared_resolution_error,),
        )
        prepared_meta = None
    else:
        prepared_stage, prepared_meta = _artifact_stage(
            stage="prepared_order",
            expected="PREPARED_ORDER_BOUND_TO_EXECUTION_SESSION",
            session_date=session,
            path=selected_prepared,
            session_fields=("execution_session_date",),
            require_outcome_clean=False,
            extra_validator=(
                None
                if selected_prepared is None
                else lambda payload: _validate_prepared_contract(
                    payload,
                    execution_session_date=session,
                    metadata_path=selected_prepared,
                )
            ),
        )
        if selected_prepared is None:
            _set_stricter(prepared_stage, PENDING_EXPECTED, "PREPARED_PARENT_NOT_FOUND_FOR_EXECUTION_SESSION")
    stage_by_name["prepared_order"] = prepared_stage

    decision_date: str | None = None
    if prepared_stage["status"] == PASS and prepared_meta is not None:
        try:
            decision_date = _session(prepared_meta.payload.get("decision_session_date"))
        except SessionAuditError:
            _set_stricter(prepared_stage, PROVENANCE_INVALID, "PREPARED_DECISION_SESSION_INVALID")
        else:
            if selected_prepared is not None and selected_prepared.stem != decision_date:
                _set_stricter(prepared_stage, PROVENANCE_INVALID, "PREPARED_PATH_DECISION_SESSION_MISMATCH")

    discovered_for_decision: tuple[ArtifactSpec, ...] = ()
    if decision_date and forward_root is not None and e2e_root is not None:
        discovered_for_decision = discover_session_artifacts(
            forward_monitoring_root=forward_root,
            e2e_runtime_root=e2e_root,
            session_date=decision_date,
        )
    by_name = {item.name: item for item in discovered_for_decision}

    if decision_date is None:
        for name, expected in (
            ("canonical_eod_capture", "DATA_READY_CANONICAL_EOD_MANIFEST"),
            ("v4_x1_scoring", "DONE_OUTCOME_BLIND_V4_X1_SCORE_MANIFEST"),
            ("decision_v2", "DECISION_V2_METADATA"),
        ):
            stage_by_name[name] = _stage(name, expected, session, PENDING_EXPECTED, notes=("DECISION_PARENT_NOT_CERTIFIED",))
        decision_meta = None
    else:
        eod_stage, _ = _artifact_stage(
            stage="canonical_eod_capture",
            expected="DATA_READY_CANONICAL_EOD_MANIFEST_FOR_DECISION_SESSION",
            session_date=decision_date,
            path=by_name.get("eod_manifest").path if by_name.get("eod_manifest") else None,
            expected_status="DATA_READY",
        )
        score_stage, _ = _artifact_stage(
            stage="v4_x1_scoring",
            expected="DONE_OUTCOME_BLIND_V4_X1_SCORE_MANIFEST_FOR_DECISION_SESSION",
            session_date=decision_date,
            path=by_name.get("v4_x1_score_manifest").path if by_name.get("v4_x1_score_manifest") else None,
            expected_status="DONE",
        )
        decision_meta = prepared_meta
        decision_status = PASS if prepared_stage["status"] == PASS else prepared_stage["status"]
        decision_stage = _stage(
            "decision_v2",
            "CANONICAL_DECISION_PLAN_EMBEDDED_IN_PREPARED_EXECUTION",
            decision_date,
            decision_status,
            path=selected_prepared,
            sha256=prepared_meta.sha256 if prepared_meta else None,
            observed={"decision_source": "prepared_execution_payload"},
            notes=("CANONICAL_DECISION_PLAN_FROM_PREPARED",),
        )
        stage_by_name["canonical_eod_capture"] = eod_stage
        stage_by_name["v4_x1_scoring"] = score_stage
        stage_by_name["decision_v2"] = decision_stage

    decision_noop = bool(
        prepared_meta is not None
        and prepared_stage["status"] == PASS
        and _decision_has_no_operational_work(prepared_meta.payload)
    )

    binding_path = None
    if selected_prepared is not None and decision_date is not None:
        binding_path = _safe_path(schedule_binding_metadata) if schedule_binding_metadata else _known_path(e2e_root, "prepared_schedule", f"{decision_date}.json")
    if binding_path is not None and prepared_meta is not None:
        binding_stage, _ = _artifact_stage(
            stage="prepared_order_schedule_binding",
            expected="PREPARED_ORDER_BOUND_TO_OFFICIAL_SCHEDULE",
            session_date=session,
            path=binding_path,
            session_fields=("execution_session_date",),
            require_outcome_clean=False,
            status_required=False,
            extra_validator=lambda payload: _validate_schedule_binding(
                payload,
                binding_path=binding_path,
                prepared_path=selected_prepared,
                prepared_payload=prepared_meta.payload,
                execution_session_date=session,
            ),
        )
        if binding_stage["status"] == PASS:
            binding_stage["observed"]["binding_path"] = str(binding_path)
    else:
        binding_stage = _stage(
            "prepared_order_schedule_binding",
            "PREPARED_ORDER_BOUND_TO_OFFICIAL_SCHEDULE",
            session,
            PENDING_EXPECTED if prepared_stage["status"] == PASS else NOT_READ,
            notes=("PREPARED_SCHEDULE_BINDING_NOT_DECLARED",),
        )
    stage_by_name["prepared_order_schedule_binding"] = binding_stage

    open_path = _known_path(e2e_root, "official_open", session, "manifest.json")
    open_stage, open_meta = _artifact_stage(
        stage="official_open_evidence",
        expected="IDX_OPENPRICE_EXECUTION_GRADE_MANIFEST_FOR_EXECUTION_SESSION",
        session_date=session,
        path=open_path,
        session_fields=("session_date", "execution_session_date"),
        require_outcome_clean=False,
        status_required=False,
        extra_validator=_validate_open_contract,
    )
    stage_by_name["official_open_evidence"] = open_stage

    execution_path = _known_path(e2e_root, "executions", f"{session}.json")
    missed_path = _known_path(e2e_root, "missed_executions", f"{session}.json")
    existing_execution = execution_path is not None and execution_path.is_file()
    execution_stage, execution_meta = _artifact_stage(
        stage="paper_execution",
        expected="EXECUTION_BOUND_TO_PREPARED_PARENT_OR_PENDING",
        session_date=session,
        path=execution_path if existing_execution else missed_path,
        expected_status="EXECUTION_COMPLETE" if existing_execution else "MISSED_EXECUTION_NO_CERTIFIED_OPEN",
        session_fields=("execution_session_date", "session_date"),
        require_outcome_clean=False,
        status_required=True,
        extra_validator=lambda payload: (
            [*_validate_state_lineage(payload)]
            + ([*_validate_execution_contract(
                payload,
                prepared_path=selected_prepared,
                prepared_sha256=prepared_meta.sha256 if prepared_meta else None,
                decision_session_date=decision_date,
                execution_session_date=session,
                open_metadata=open_meta,
            )] if existing_execution else [*_validate_missed_execution_contract(
                payload,
                prepared_path=selected_prepared,
                prepared_sha256=prepared_meta.sha256 if prepared_meta else None,
                expected_binding_path=binding_path,
                execution_session_date=session,
            )])
        ),
    )
    if not existing_execution and execution_stage["status"] == LEGITIMATE_NOOP:
        execution_stage["observed"]["continuity_transition"] = "MISSED_EXECUTION_NO_CERTIFIED_OPEN"
        execution_stage.setdefault("causal_notes", []).append("MISSED_EXECUTION_CONTINUITY")
    stage_by_name["paper_execution"] = execution_stage

    if decision_noop:
        stage_by_name["decision_v2"]["status"] = LEGITIMATE_NOOP
        stage_by_name["decision_v2"].setdefault("causal_notes", []).append("DECISION_V2_EXPLICIT_EMPTY_EXECUTION_PLAN")
        if execution_stage["status"] in {NOT_READ, PENDING_EXPECTED}:
            _resolve_noop(execution_stage, "DECISION_V2_LEGITIMATE_NOOP")
        elif execution_stage["status"] == PASS:
            _set_stricter(execution_stage, IMPLEMENTATION_DEFECT, "EXECUTION_AFTER_LEGITIMATE_NOOP")
    elif open_stage["status"] not in {PASS, LEGITIMATE_NOOP} and existing_execution:
        if execution_stage["status"] in {NOT_READ, PENDING_EXPECTED}:
            _set_stricter(execution_stage, PENDING_EXPECTED, "OFFICIAL_OPEN_UNAVAILABLE_BEFORE_EXECUTION")
        elif execution_stage["status"] in {PASS, LEGITIMATE_NOOP} or "EXECUTION_OPEN_PARENT_UNAVAILABLE" in execution_stage.get("causal_notes", []):
            _set_stricter(execution_stage, IMPLEMENTATION_DEFECT, "SUCCESSFUL_EXECUTION_WITHOUT_CERTIFIED_OPEN")

    ca_path = ca_dividend or _known_path(e2e_root, "dividend_acquisition_v1", "journals", f"{session}.json")
    ca_stage, _ = _artifact_stage(
        stage="ca_dividend",
        expected="CA_DIVIDEND_OPERATIONAL_METADATA_FOR_EXECUTION_SESSION",
        session_date=session,
        path=ca_path,
        session_fields=("execution_session_date", "session_date"),
        extra_validator=lambda payload: _validate_decision_execution_link(
            payload,
            decision_session_date=decision_date,
            execution_session_date=session,
        ),
    )
    stage_by_name["ca_dividend"] = ca_stage

    paperstate_path = _known_path(e2e_root, "forward_execution_v1_1", "state_snapshots", f"{session}.json")
    paperstate_stage, _ = _artifact_stage(
        stage="paperstate_continuity",
        expected="PAPERSTATE_CONTINUITY_METADATA_FOR_EXECUTION_SESSION",
        session_date=session,
        path=paperstate_path,
        session_fields=("execution_session_date", "session_date"),
        require_outcome_clean=False,
        status_required=False,
        extra_validator=lambda payload: [
            *_validate_state_lineage(payload),
            *_validate_runtime_snapshot(payload),
        ],
    )
    stage_by_name["paperstate_continuity"] = paperstate_stage

    if decision_noop:
        stage_by_name["forward_evidence_health"] = _stage(
            "forward_evidence_health",
            "NO_DOWNSTREAM_FORWARD_EVIDENCE_REQUIRED_AFTER_LEGITIMATE_NOOP",
            session,
            NOT_APPLICABLE,
            notes=("DECISION_V2_LEGITIMATE_NOOP",),
        )
    elif discovered_for_decision:
        health_specs = tuple(
            item for item in discovered_for_decision
            if item.name in {"eod_manifest", "v4_x1_score_manifest"}
        )
        health = evaluate_session(decision_date or session, health_specs, reported_at_utc=reported_at_utc)
        stage_by_name["forward_evidence_health"] = _stage(
            "forward_evidence_health",
            "DECISION_SESSION_FORWARD_ARTIFACT_HEALTH",
            session,
            _map_health_status(str(health.get("overall_status"))),
            observed={"health_overall_status": health.get("overall_status"), "decision_session_date": decision_date},
            evidence_timestamp=reported_at_utc,
            notes=tuple(
                f"{item.get('name')}:{item.get('status')}:{item.get('reason')}"
                for item in health.get("artifacts", [])
                if item.get("status") != "COMPLETE"
            ),
        )
    else:
        stage_by_name["forward_evidence_health"] = _stage(
            "forward_evidence_health",
            "DECISION_SESSION_FORWARD_ARTIFACT_HEALTH",
            session,
            NOT_READ,
            notes=("DECISION_PARENT_NOT_CERTIFIED",),
        )

    scheduler_stage, _ = _artifact_stage(
        stage="scheduler_task",
        expected="INSTALLED_TASK_READ_ONLY_METADATA",
        session_date=session,
        path=scheduler_metadata,
        require_outcome_clean=False,
        session_fields=("session_date", "execution_session_date"),
        extra_validator=_validate_scheduler,
    )
    stage_by_name["scheduler_task"] = scheduler_stage

    # Cross-stage ordering is metadata-only and uses immutable parent identity.
    prepared_ts = _stage_timestamp(prepared_stage)
    decision_stage = stage_by_name.get("decision_v2", {})
    decision_ts = _stage_timestamp(decision_stage)
    open_ts = _stage_timestamp(open_stage)
    execution_ts = _stage_timestamp(execution_stage)
    if decision_stage.get("status") == PASS and prepared_stage["status"] == PASS:
        if decision_ts and prepared_ts and decision_ts >= prepared_ts:
            _set_stricter(prepared_stage, PROVENANCE_INVALID, "DECISION_NOT_BEFORE_PREPARED")
    if execution_stage["status"] == PASS:
        if prepared_ts and open_ts and prepared_ts >= open_ts:
            _set_stricter(execution_stage, PROVENANCE_INVALID, "PREPARED_AFTER_OFFICIAL_OPEN")
        if open_ts and execution_ts and open_ts > execution_ts:
            _set_stricter(execution_stage, PROVENANCE_INVALID, "OFFICIAL_OPEN_AFTER_EXECUTION")
        if execution_ts and prepared_ts and execution_ts < prepared_ts:
            _set_stricter(execution_stage, IMPLEMENTATION_DEFECT, "EXECUTION_BEFORE_PREPARED_ORDER")
    if execution_meta:
        duplicate_count = execution_meta.payload.get("duplicate_count", 0)
        if isinstance(duplicate_count, int) and duplicate_count > 0:
            _set_stricter(execution_stage, IMPLEMENTATION_DEFECT, "DUPLICATE_EXECUTION_EVIDENCE")
        if execution_meta.payload.get("retroactive_fill") is True or execution_meta.payload.get("backdated_fill") is True:
            _set_stricter(execution_stage, PROVENANCE_INVALID, "RETROACTIVE_FILL_REJECTED")

    stages = [stage_by_name[name] for name in STAGES]
    overall, blockers = _aggregate(calendar_stage["status"], stages[1:])
    return _report(session, overall, stages, blockers, reported_at_utc, decision_date)


def _stage_timestamp(stage: Mapping[str, Any]) -> str | None:
    return stage.get("evidence_timestamp_utc") or stage.get("scheduled_timestamp_utc")


def _report(
    session: str,
    overall: str,
    stages: Sequence[Mapping[str, Any]],
    blockers: Sequence[str],
    reported_at_utc: str,
    decision_session_date: str | None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_VERSION,
        "ledger_anchor": "execution_session_date",
        "session_date": session,
        "execution_session_date": session,
        "decision_session_date": decision_session_date,
        "overall_status": overall,
        "runtime_identity": next((dict(item["observed"]) for item in stages if item["stage"] == "runtime_identity"), {}),
        "stages": [dict(item) for item in stages],
        "blockers": list(blockers),
        "guards": {
            "protected_outcomes_accessed": False,
            "real_protected_loader_called": False,
            "real_outcome_access_marker_written": False,
            "provider_capture_triggered": False,
            "model_changed": False,
            "forward_counter_changed": False,
        },
        "reported_at_utc": reported_at_utc,
    }


def summarize_ledgers(ledgers: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(ledgers, key=lambda item: str(item.get("execution_session_date", item.get("session_date", ""))))
    statuses = [str(item.get("overall_status")) for item in ordered]
    healthy_trading = {"SESSION_HEALTHY", "SESSION_HEALTHY_LEGITIMATE_NOOP"}
    transports: dict[str, int] = {}
    missing: dict[str, int] = {}
    continuity: list[tuple[str, str]] = []
    latest_healthy: str | None = None
    non_trading_count = 0
    missed_execution_count = 0
    consecutive_stockbit_failures = 0
    for ledger in ordered:
        session = str(ledger.get("execution_session_date", ledger.get("session_date")))
        overall = str(ledger.get("overall_status"))
        if overall == "NON_TRADING_SESSION":
            non_trading_count += 1
        if overall == "SESSION_MISSED_EXECUTION_NO_CERTIFIED_OPEN":
            missed_execution_count += 1
        if overall in healthy_trading and (latest_healthy is None or session > latest_healthy):
            latest_healthy = session
        stockbit_status: str | None = None
        for stage in ledger.get("stages", []):
            name = str(stage.get("stage"))
            status = str(stage.get("status"))
            if status in {NOT_READ, PENDING_EXPECTED}:
                missing[name] = missing.get(name, 0) + 1
            if name == "official_open_evidence":
                transport = stage.get("observed", {}).get("transport")
                if transport:
                    transports[str(transport)] = transports.get(str(transport), 0) + 1
            if name == "stockbit_scheduled_capture":
                stockbit_status = status
            if name == "paperstate_continuity":
                continuity.append((overall, status))
        if overall == "NON_TRADING_SESSION":
            continue
        if stockbit_status == FAIL_CLOSED_EXTERNAL:
            consecutive_stockbit_failures += 1
        elif stockbit_status == PASS:
            consecutive_stockbit_failures = 0
    return {
        "schema": SUMMARY_SCHEMA_VERSION,
        "session_count": len(ordered),
        "healthy_count": sum(status in healthy_trading for status in statuses),
        "non_trading_count": non_trading_count,
        "missed_execution_count": missed_execution_count,
        "incomplete_count": sum(status == "SESSION_PENDING_EXPECTED" for status in statuses),
        "fail_closed_count": sum(status == "SESSION_FAIL_CLOSED_EXTERNAL" for status in statuses),
        "provenance_invalid_count": sum(status == "SESSION_PROVENANCE_INVALID" for status in statuses),
        "implementation_defect_count": sum(status == "SESSION_IMPLEMENTATION_DEFECT" for status in statuses),
        "latest_healthy_session": latest_healthy,
        "consecutive_stockbit_provider_failures": consecutive_stockbit_failures,
        "official_open_transport_distribution": transports,
        "missing_stage_frequency": missing,
        "paperstate_continuity_status": (
            "PASS"
            if any(overall != "NON_TRADING_SESSION" for overall, _ in continuity)
            and all(status == PASS for overall, status in continuity if overall != "NON_TRADING_SESSION")
            else ("NOT_APPLICABLE" if continuity and all(overall == "NON_TRADING_SESSION" for overall, _ in continuity) else "PENDING_EXPECTED" if not continuity else "FAIL_CLOSED_EXTERNAL")
        ),
        "guards": {"protected_outcomes_accessed": False, "provider_capture_triggered": False},
    }


def write_json(path: str | Path, payload: Mapping[str, Any]) -> tuple[Path, str]:
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    temporary = target.with_name(f".{target.name}.{__import__('os').getpid()}.tmp")
    temporary.write_bytes(body)
    temporary.replace(target)
    return target, hashlib.sha256(body).hexdigest()


__all__ = [
    "FAIL_CLOSED_EXTERNAL",
    "IMPLEMENTATION_DEFECT",
    "LEGITIMATE_NOOP",
    "NOT_APPLICABLE",
    "NOT_READ",
    "PASS",
    "PENDING_EXPECTED",
    "PROVENANCE_INVALID",
    "SCHEMA_VERSION",
    "STAGES",
    "SessionAuditError",
    "audit_session",
    "summarize_ledgers",
    "write_json",
]
