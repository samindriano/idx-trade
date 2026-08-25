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
)
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


def _artifact_stage(
    *,
    stage: str,
    expected: str,
    session_date: str,
    path: str | Path | None,
    required: bool = True,
    expected_status: str | None = None,
    expected_fields: Sequence[tuple[str, object]] = (),
    require_outcome_clean: bool = True,
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
                require_outcome_clean=require_outcome_clean,
            ),
            session_date=session_date,
        )
        observed_status = result["status"]
        if observed_status == "COMPLETE":
            observed_status = _status(_json_object(safe).payload) or PASS
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
        _metadata_identity(metadata.payload, session_date)
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
                observed_status if observed_status in {PASS, LEGITIMATE_NOOP, PENDING_EXPECTED} else PASS,
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
    runner = str(payload.get("runner") or payload.get("module") or "")
    if "run_official_open_capture_v2.ps1" not in runner and "official_open_capture_runtime_v2" not in runner:
        yield "SCHEDULER_RUNNER_MISMATCH"
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
    if PROVENANCE_INVALID in statuses:
        return "SESSION_PROVENANCE_INVALID", blockers
    if IMPLEMENTATION_DEFECT in statuses:
        return "SESSION_IMPLEMENTATION_DEFECT", blockers
    if FAIL_CLOSED_EXTERNAL in statuses:
        return "SESSION_FAIL_CLOSED_EXTERNAL", blockers
    if PENDING_EXPECTED in statuses or NOT_READ in statuses:
        return "SESSION_PENDING_EXPECTED", blockers
    if LEGITIMATE_NOOP in statuses:
        return "SESSION_HEALTHY_LEGITIMATE_NOOP", blockers
    return "SESSION_HEALTHY", blockers


def audit_session(
    session_date: str,
    *,
    forward_monitoring_root: str | Path | None = None,
    e2e_runtime_root: str | Path | None = None,
    calendar_metadata: str | Path | None = None,
    runtime_identity: str | Path | None = None,
    stockbit_capture: str | Path | None = None,
    ca_dividend: str | Path | None = None,
    scheduler_metadata: str | Path | None = None,
    reported_at_utc: str = "2026-01-01T00:00:00+00:00",
) -> dict[str, Any]:
    session = _session(session_date)
    forward_root = Path(forward_monitoring_root).expanduser().resolve() if forward_monitoring_root else None
    e2e_root = Path(e2e_runtime_root).expanduser().resolve() if e2e_runtime_root else None
    stages: list[dict[str, Any]] = []

    calendar_stage, calendar_meta = _artifact_stage(
        stage="official_trading_calendar",
        expected="EXACT_OFFICIAL_CALENDAR_CLASSIFICATION",
        session_date=session,
        path=calendar_metadata,
        require_outcome_clean=False,
        extra_validator=lambda p: ("CALENDAR_SESSION_DATE_MISSING",) if "session_date" not in p else (),
    )
    stages.append(calendar_stage)
    is_trading = bool(calendar_meta and calendar_meta.payload.get("is_trading_session") is True)
    is_nontrading = bool(calendar_meta and calendar_meta.payload.get("is_trading_session") is False)
    if calendar_meta and is_nontrading:
        for stage_name in STAGES[1:]:
            stages.append(_stage(stage_name, "NOT_RUN_ON_NON_TRADING_SESSION", session, NOT_APPLICABLE, notes=("NON_TRADING_SESSION",)))
        return _report(session, "NON_TRADING_SESSION", stages, [], reported_at_utc)
    if calendar_meta and calendar_stage["status"] == PASS and not is_trading:
        calendar_stage["status"] = PROVENANCE_INVALID

    runtime_stage, _ = _artifact_stage(
        stage="runtime_identity",
        expected="DEPLOYED_RUNTIME_IDENTITY_AND_SHA",
        session_date=session,
        path=runtime_identity,
        require_outcome_clean=False,
        extra_validator=_validate_runtime_identity,
    )
    stages.append(runtime_stage)
    stockbit_stage, _ = _artifact_stage(
        stage="stockbit_scheduled_capture",
        expected="SCHEDULED_STOCKBIT_CAPTURE_METADATA",
        session_date=session,
        path=stockbit_capture,
        require_outcome_clean=True,
    )
    stages.append(stockbit_stage)

    discovered: tuple[ArtifactSpec, ...] = ()
    if forward_root is not None and e2e_root is not None:
        discovered = discover_session_artifacts(
            forward_monitoring_root=forward_root,
            e2e_runtime_root=e2e_root,
            session_date=session,
        )
    by_name = {item.name: item for item in discovered}
    eod_stage, _ = _artifact_stage(
        stage="canonical_eod_capture",
        expected="DATA_READY_CANONICAL_EOD_MANIFEST",
        session_date=session,
        path=by_name.get("eod_manifest").path if by_name.get("eod_manifest") else None,
        expected_status="DATA_READY",
    )
    stages.append(eod_stage)
    score_stage, _ = _artifact_stage(
        stage="v4_x1_scoring",
        expected="DONE_OUTCOME_BLIND_V4_X1_SCORE_MANIFEST",
        session_date=session,
        path=by_name.get("v4_x1_score_manifest").path if by_name.get("v4_x1_score_manifest") else None,
        expected_status="DONE",
    )
    stages.append(score_stage)

    decision_path = _known_path(e2e_root, "state", "decisions", f"{session}.json")
    decision_stage, decision_meta = _artifact_stage(
        stage="decision_v2",
        expected="DECISION_V2_METADATA",
        session_date=session,
        path=decision_path,
    )
    stages.append(decision_stage)
    decision_noop = decision_stage["status"] == LEGITIMATE_NOOP or bool(
        decision_meta and decision_meta.payload.get("trade_count") == 0
    )

    prepared_path = by_name.get("prepared_order").path if by_name.get("prepared_order") else _known_path(e2e_root, "prepared", f"{session}.json")
    prepared_stage, prepared_meta = _artifact_stage(
        stage="prepared_order",
        expected="PREPARED_ORDER_OR_EXPLICIT_NOOP",
        session_date=session,
        path=prepared_path,
    )
    if decision_noop and prepared_stage["status"] in {NOT_READ, PENDING_EXPECTED}:
        prepared_stage["status"] = NOT_APPLICABLE
        prepared_stage["causal_notes"] = ["DECISION_V2_LEGITIMATE_NOOP"]
    stages.append(prepared_stage)

    open_path = by_name.get("official_open_manifest").path if by_name.get("official_open_manifest") else _known_path(e2e_root, "official_open", session, "manifest.json")
    open_stage, open_meta = _artifact_stage(
        stage="official_open_evidence",
        expected="IDX_OPENPRICE_EXECUTION_GRADE_MANIFEST",
        session_date=session,
        path=open_path,
        require_outcome_clean=False,
        extra_validator=_validate_open_contract,
    )
    stages.append(open_stage)

    execution_path = by_name.get("execution_result").path if by_name.get("execution_result") else _known_path(e2e_root, "executions", f"{session}.json")
    execution_stage, execution_meta = _artifact_stage(
        stage="paper_execution",
        expected="EXECUTION_OR_LEGITIMATE_NOOP_OR_PENDING",
        session_date=session,
        path=execution_path,
        extra_validator=_validate_state_lineage,
    )
    stages.append(execution_stage)
    if decision_noop and execution_stage["status"] in {NOT_READ, PENDING_EXPECTED}:
        execution_stage["status"] = NOT_APPLICABLE
        execution_stage["causal_notes"] = ["DECISION_V2_LEGITIMATE_NOOP"]
    elif not decision_noop and open_stage["status"] not in {PASS, LEGITIMATE_NOOP}:
        execution_stage["status"] = PENDING_EXPECTED
        execution_stage["causal_notes"].append("OFFICIAL_OPEN_UNAVAILABLE_BEFORE_EXECUTION")

    ca_path = ca_dividend or _known_path(e2e_root, "dividend_acquisition_v1", "journals", f"{session}.json")
    ca_stage, _ = _artifact_stage(
        stage="ca_dividend",
        expected="CA_DIVIDEND_OPERATIONAL_METADATA",
        session_date=session,
        path=ca_path,
    )
    stages.append(ca_stage)
    paperstate_path = by_name.get("paper_state_snapshot").path if by_name.get("paper_state_snapshot") else _known_path(e2e_root, "forward_execution_v1_1", "state_snapshots", f"{session}.json")
    paperstate_stage, _ = _artifact_stage(
        stage="paperstate_continuity",
        expected="PAPERSTATE_CONTINUITY_METADATA",
        session_date=session,
        path=paperstate_path,
        extra_validator=_validate_state_lineage,
    )
    stages.append(paperstate_stage)

    if decision_noop:
        stages.append(
            _stage(
                "forward_evidence_health",
                "NO_DOWNSTREAM_FORWARD_EVIDENCE_REQUIRED_AFTER_LEGITIMATE_NOOP",
                session,
                NOT_APPLICABLE,
                notes=("DECISION_V2_LEGITIMATE_NOOP",),
            )
        )
    elif discovered:
        health = evaluate_session(session, discovered, reported_at_utc=reported_at_utc)
        health_status = _map_health_status(str(health.get("overall_status")))
        stages.append(
            _stage(
                "forward_evidence_health",
                "ALL_DECLARED_SAFE_FORWARD_ARTIFACTS_HASH_AND_IDENTITY_VALID",
                session,
                health_status,
                observed={"health_overall_status": health.get("overall_status")},
                evidence_timestamp=reported_at_utc,
                notes=tuple(
                    f"{item.get('name')}:{item.get('status')}:{item.get('reason')}"
                    for item in health.get("artifacts", [])
                    if item.get("status") != "COMPLETE"
                ),
            )
        )
    else:
        stages.append(_stage("forward_evidence_health", "SAFE_HEALTH_REPORT", session, NOT_READ, notes=("ROOTS_NOT_DECLARED",)))

    scheduler_stage, _ = _artifact_stage(
        stage="scheduler_task",
        expected="INSTALLED_TASK_READ_ONLY_METADATA",
        session_date=session,
        path=scheduler_metadata,
        require_outcome_clean=False,
        extra_validator=_validate_scheduler,
    )
    stages.append(scheduler_stage)

    # Cross-stage ordering is metadata-only.  It deliberately never opens a data file.
    prepared_ts = _stage_timestamp(prepared_stage)
    execution_ts = _stage_timestamp(execution_stage)
    if prepared_ts and execution_ts and execution_ts < prepared_ts:
        execution_stage["status"] = IMPLEMENTATION_DEFECT
        execution_stage["causal_notes"].append("EXECUTION_BEFORE_PREPARED_ORDER")
    if execution_meta:
        duplicate_count = execution_meta.payload.get("duplicate_count", 0)
        if isinstance(duplicate_count, int) and duplicate_count > 0:
            execution_stage["status"] = IMPLEMENTATION_DEFECT
            execution_stage["causal_notes"].append("DUPLICATE_EXECUTION_EVIDENCE")
        if execution_meta.payload.get("retroactive_fill") is True or execution_meta.payload.get("backdated_fill") is True:
            execution_stage["status"] = PROVENANCE_INVALID
            execution_stage["causal_notes"].append("RETROACTIVE_FILL_REJECTED")
    overall, blockers = _aggregate(calendar_stage["status"], stages[1:])
    return _report(session, overall, stages, blockers, reported_at_utc)


def _stage_timestamp(stage: Mapping[str, Any]) -> str | None:
    return stage.get("evidence_timestamp_utc") or stage.get("scheduled_timestamp_utc")


def _report(session: str, overall: str, stages: Sequence[Mapping[str, Any]], blockers: Sequence[str], reported_at_utc: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA_VERSION,
        "session_date": session,
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
    statuses = [str(item.get("overall_status")) for item in ledgers]
    healthy = {"SESSION_HEALTHY", "SESSION_HEALTHY_LEGITIMATE_NOOP", "NON_TRADING_SESSION"}
    transports: dict[str, int] = {}
    missing: dict[str, int] = {}
    provider_failures: list[bool] = []
    continuity: list[str] = []
    latest_healthy: str | None = None
    for ledger in ledgers:
        session = str(ledger.get("session_date"))
        if ledger.get("overall_status") in healthy and (latest_healthy is None or session > latest_healthy):
            latest_healthy = session
        for stage in ledger.get("stages", []):
            name = str(stage.get("stage"))
            status = str(stage.get("status"))
            if status in {NOT_READ, PENDING_EXPECTED}:
                missing[name] = missing.get(name, 0) + 1
            if name == "official_open_evidence":
                transport = stage.get("observed", {}).get("transport")
                if transport:
                    transports[str(transport)] = transports.get(str(transport), 0) + 1
            if name == "stockbit_scheduled_capture" and status == FAIL_CLOSED_EXTERNAL:
                provider_failures.append(True)
            if name == "paperstate_continuity":
                continuity.append(status)
    consecutive = 0
    for failed in reversed(provider_failures):
        if not failed:
            break
        consecutive += 1
    return {
        "schema": SUMMARY_SCHEMA_VERSION,
        "session_count": len(ledgers),
        "healthy_count": sum(status in healthy for status in statuses),
        "incomplete_count": sum(status == "SESSION_PENDING_EXPECTED" for status in statuses),
        "fail_closed_count": sum(status == "SESSION_FAIL_CLOSED_EXTERNAL" for status in statuses),
        "provenance_invalid_count": sum(status == "SESSION_PROVENANCE_INVALID" for status in statuses),
        "implementation_defect_count": sum(status == "SESSION_IMPLEMENTATION_DEFECT" for status in statuses),
        "latest_healthy_session": latest_healthy,
        "consecutive_provider_failures": consecutive,
        "official_open_transport_distribution": transports,
        "missing_stage_frequency": missing,
        "paperstate_continuity_status": "PASS" if continuity and all(value == PASS for value in continuity) else ("PENDING_EXPECTED" if not continuity else "FAIL_CLOSED_EXTERNAL"),
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
