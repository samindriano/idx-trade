from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


SCHEMA_VERSION = "v4_x1_prospective_preaccess_readiness_v1"
REQUIRED_SESSION_COUNT = 100
MODEL_NAME = "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1"
MODEL_GENERATION = "V4-X1-CLEAN"
MODEL_FINGERPRINT = "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf"
RANKING_SEMANTICS = "alpha_consensus DESC, ticker ASC"
CANONICAL_TARGET_ID = "CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1"
PROTECTED_STATUS = "PROTECTED_NOT_READ"

PARTIAL_INVENTORY_COLUMNS = (
    "forward_position",
    "session_index",
    "session_date",
    "score_artifact_path",
    "score_artifact_sha256",
    "score_manifest_path",
    "score_manifest_sha256",
)

READINESS_COMPONENT_STATUSES = frozenset(
    {
        "READY",
        "ACCUMULATING",
        "PENDING_EXPECTED",
        "NOT_AVAILABLE",
        "PROVENANCE_INVALID",
        "ACCESS_CONTAMINATION",
        PROTECTED_STATUS,
    }
)

OVERALL_STATUSES = frozenset(
    {
        "ACCUMULATING_OUTCOME_BLIND",
        "PREACCESS_REQUIREMENTS_INCOMPLETE",
        "PREACCESS_READY_FOR_EXISTING_GATE",
        "PREACCESS_PROVENANCE_INVALID",
        "PREACCESS_ACCESS_CONTAMINATED",
    }
)

_PROTECTED_PATH_TOKENS = frozenset({"outcome", "label", "realized", "vault"})
_PROTECTED_ACCESS_KEYS = frozenset(
    {
        "outcome_access",
        "outcome_accessed",
        "forward_outcomes_accessed",
        "fresh_forward_outcomes_accessed",
        "protected_outcome_accessed",
        "realized_forward_outcome_loaded",
        "real_outcome_access_marker_written",
        "real_protected_loader_called",
        "real_loader_called",
        "real_marker_written",
        "protected_outcomes_accessed",
    }
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class PreAccessReadinessError(RuntimeError):
    """Raised when a pre-access readiness input violates the frozen boundary."""


def _normalize_session(value: object) -> str:
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            raise PreAccessReadinessError("SESSION_DATE_INVALID")
        return value.tz_localize(None).date().isoformat() if value.tzinfo else value.date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or "").strip()
    try:
        # Preserve civil date semantics; never convert through UTC.
        return pd.Timestamp(text).tz_localize(None).date().isoformat() if pd.Timestamp(text).tzinfo else pd.Timestamp(text).date().isoformat()
    except (TypeError, ValueError, OverflowError) as exc:
        raise PreAccessReadinessError("SESSION_DATE_INVALID") from exc


def _require_sha256(value: object, *, label: str) -> str:
    text = str(value or "").strip().lower()
    if not _HEX64.fullmatch(text):
        raise PreAccessReadinessError(f"{label}_SHA256_INVALID")
    return text


def _canonical_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _path_components(value: object) -> tuple[str, ...]:
    text = str(value or "").strip().lower().replace("\\", "/")
    return tuple(part for part in text.split("/") if part)


def assert_safe_reference(value: object, *, label: str) -> str:
    """Reject semantic references to protected material before any file read occurs."""

    text = str(value or "").strip()
    if not text:
        raise PreAccessReadinessError(f"{label}_REFERENCE_EMPTY")
    for component in _path_components(text):
        if any(token in component for token in _PROTECTED_PATH_TOKENS):
            raise PreAccessReadinessError(f"{label}_PROTECTED_REFERENCE_REFUSED")
    return text


def _walk_mapping(value: object, *, path: str = "root") -> Iterable[tuple[str, object]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield child_path, child
            yield from _walk_mapping(child, path=child_path)
    elif isinstance(value, (list, tuple)):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]"
            yield child_path, child
            yield from _walk_mapping(child, path=child_path)


def validate_outcome_blind_metadata(payload: Mapping[str, Any]) -> None:
    """Validate access-guard semantics without reading target/performance values.

    Words such as ``target`` are permitted in public frozen contract metadata because
    target identity is not itself protected. Access flags must be explicitly false,
    and any referenced protected path is rejected before a file can be read.
    """

    for path, value in _walk_mapping(payload):
        key = path.rsplit(".", 1)[-1].split("[")[0].lower()
        if key in _PROTECTED_ACCESS_KEYS and value is not False:
            raise PreAccessReadinessError(f"OUTCOME_GUARD_NOT_CLEAN:{path}")
        if key.endswith("path") or key.endswith("file") or key.endswith("dir") or key.endswith("root"):
            if isinstance(value, (str, Path)) and str(value).strip():
                assert_safe_reference(value, label="METADATA")


def _coerce_partial_inventory(inventory: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(PARTIAL_INVENTORY_COLUMNS) - set(inventory.columns))
    if missing:
        raise PreAccessReadinessError(f"PARTIAL_INVENTORY_MISSING_COLUMNS:{','.join(missing)}")
    data = inventory[list(PARTIAL_INVENTORY_COLUMNS)].copy()
    if len(data) > REQUIRED_SESSION_COUNT:
        raise PreAccessReadinessError("PARTIAL_INVENTORY_EXCEEDS_100")
    if data.empty:
        return data

    try:
        data["forward_position"] = pd.to_numeric(data["forward_position"], errors="raise").astype(int)
        data["session_index"] = pd.to_numeric(data["session_index"], errors="raise").astype(int)
    except Exception as exc:
        raise PreAccessReadinessError("PARTIAL_INVENTORY_NUMERIC_IDENTITY_INVALID") from exc
    data["session_date"] = data["session_date"].map(_normalize_session)
    data = data.sort_values("forward_position", kind="mergesort").reset_index(drop=True)

    expected_positions = list(range(1, len(data) + 1))
    if data["forward_position"].tolist() != expected_positions:
        raise PreAccessReadinessError("PARTIAL_INVENTORY_POSITIONS_NOT_CONTIGUOUS_1_TO_N")
    if data["session_date"].duplicated().any() or data["session_index"].duplicated().any():
        raise PreAccessReadinessError("PARTIAL_INVENTORY_DUPLICATE_SESSION_IDENTITY")
    dates = pd.to_datetime(data["session_date"], errors="raise")
    if not dates.is_monotonic_increasing:
        raise PreAccessReadinessError("PARTIAL_INVENTORY_DATE_ORDER_INVALID")
    if len(data) > 1 and not (data["session_index"].diff().iloc[1:] > 0).all():
        raise PreAccessReadinessError("PARTIAL_INVENTORY_INDEX_ORDER_INVALID")
    for column in ("score_artifact_path", "score_manifest_path"):
        refs = data[column].map(lambda value: assert_safe_reference(value, label=column.upper()))
        if refs.duplicated().any():
            raise PreAccessReadinessError(f"PARTIAL_INVENTORY_DUPLICATE_{column.upper()}")
        data[column] = refs
    for column in ("score_artifact_sha256", "score_manifest_sha256"):
        data[column] = data[column].map(lambda value: _require_sha256(value, label=column.upper()))
    return data


def validate_partial_session_inventory(inventory: pd.DataFrame) -> dict[str, Any]:
    """Validate a 0..100 rolling inventory without reading score/outcome values.

    This is deliberately weaker than the final gate's exact 100-row validator. At
    100/100 the existing protected-access gate remains authoritative and must re-read
    and re-hash the inputs before any access can be authorized.
    """

    data = _coerce_partial_inventory(inventory)
    rows = [
        {
            "forward_position": int(row.forward_position),
            "session_index": int(row.session_index),
            "session_date": str(row.session_date),
            "score_artifact_path": str(row.score_artifact_path),
            "score_artifact_sha256": str(row.score_artifact_sha256),
            "score_manifest_path": str(row.score_manifest_path),
            "score_manifest_sha256": str(row.score_manifest_sha256),
        }
        for row in data.itertuples(index=False)
    ]
    count = len(rows)
    return {
        "status": "READY" if count == REQUIRED_SESSION_COUNT else "ACCUMULATING",
        "observed_sessions": count,
        "required_sessions": REQUIRED_SESSION_COUNT,
        "remaining_sessions": REQUIRED_SESSION_COUNT - count,
        "first_session_date": rows[0]["session_date"] if rows else None,
        "last_session_date": rows[-1]["session_date"] if rows else None,
        "partial_inventory_sha256": _canonical_hash(rows),
        "final_gate_revalidation_required": True,
        "rows": rows,
    }


def calendar_eligibility(
    signal_sessions: Sequence[object],
    official_trading_sessions: Sequence[object],
    *,
    as_of_session: object | None = None,
) -> dict[str, Any]:
    """Compute H5/H10 calendar eligibility without checking target availability."""

    if as_of_session is None:
        raise PreAccessReadinessError("AS_OF_SESSION_REQUIRED")
    official = sorted({_normalize_session(value) for value in official_trading_sessions})
    cutoff = _normalize_session(as_of_session)
    official = [value for value in official if value <= cutoff]
    positions = {value: idx for idx, value in enumerate(official)}

    rows: list[dict[str, Any]] = []
    h5_count = 0
    h10_count = 0
    for raw in signal_sessions:
        session = _normalize_session(raw)
        if session not in positions:
            row = {
                "session_date": session,
                "calendar_identity_status": "PROVENANCE_INVALID",
                "observed_successor_sessions": None,
                "h5_calendar_eligible": False,
                "h10_calendar_eligible": False,
                "target_values": PROTECTED_STATUS,
            }
        else:
            successors = len(official) - positions[session] - 1
            h5 = successors >= 5
            h10 = successors >= 10
            h5_count += int(h5)
            h10_count += int(h10)
            row = {
                "session_date": session,
                "calendar_identity_status": "READY",
                "observed_successor_sessions": successors,
                "h5_calendar_eligible": h5,
                "h10_calendar_eligible": h10,
                "target_values": PROTECTED_STATUS,
            }
        rows.append(row)
    return {
        "h5_calendar_eligible_count": h5_count,
        "h10_calendar_eligible_count": h10_count,
        "evaluated_signal_sessions": len(rows),
        "target_values": PROTECTED_STATUS,
        "rows": rows,
    }


def inspect_access_state(
    *,
    persisted_status: str,
    protected_outcomes_accessed: bool = False,
    real_protected_loader_called: bool = False,
    real_outcome_access_marker_written: bool = False,
) -> dict[str, Any]:
    """Translate the existing gate's status-only result into readiness semantics."""

    if protected_outcomes_accessed or real_protected_loader_called or real_outcome_access_marker_written:
        return {
            "status": "ACCESS_CONTAMINATION",
            "persisted_status": str(persisted_status),
            "protected_outcomes_accessed": bool(protected_outcomes_accessed),
            "real_protected_loader_called": bool(real_protected_loader_called),
            "real_outcome_access_marker_written": bool(real_outcome_access_marker_written),
        }
    status = str(persisted_status).strip()
    clean = status in {
        "PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT",
        "PRE_FLIGHT_BLOCKED",
    }
    if status in {"REAL_ACCESS_AUTHORIZED", "REAL_ACCESS_ALREADY_COMPLETED"}:
        clean = False
    if status in {"ORPHAN_OR_INTERRUPTED_STATE", "INTEGRITY_FAILURE"}:
        return {
            "status": "PROVENANCE_INVALID",
            "persisted_status": status,
            "protected_outcomes_accessed": False,
            "real_protected_loader_called": False,
            "real_outcome_access_marker_written": False,
        }
    return {
        "status": "READY" if clean else "PENDING_EXPECTED",
        "persisted_status": status,
        "protected_outcomes_accessed": False,
        "real_protected_loader_called": False,
        "real_outcome_access_marker_written": False,
    }


def _normalize_component(name: str, payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {"name": name, "status": "NOT_AVAILABLE", "reason": "NOT_SUPPLIED"}
    validate_outcome_blind_metadata(payload)
    status = str(payload.get("status") or "").strip().upper()
    if status not in READINESS_COMPONENT_STATUSES:
        raise PreAccessReadinessError(f"COMPONENT_STATUS_INVALID:{name}:{status}")
    return {"name": name, **dict(payload), "status": status}


def build_readiness_report(
    *,
    inventory: pd.DataFrame,
    official_trading_sessions: Sequence[object],
    as_of_session: object | None,
    access_state: Mapping[str, Any],
    contract_identity: Mapping[str, Any],
    counter: Mapping[str, Any] | None = None,
    target_attestation: Mapping[str, Any] | None = None,
    paper_attestation: Mapping[str, Any] | None = None,
    benchmark_attestation: Mapping[str, Any] | None = None,
    prior_access_audit: Mapping[str, Any] | None = None,
    code_pins: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble one deterministic, outcome-blind readiness report."""

    validate_outcome_blind_metadata(contract_identity)
    model = contract_identity.get("model")
    target = contract_identity.get("target_identity")
    identity_ok = (
        isinstance(model, Mapping)
        and model.get("model_id") == MODEL_NAME
        and model.get("generation") == MODEL_GENERATION
        and model.get("fingerprint") == MODEL_FINGERPRINT
        and model.get("ranking") == RANKING_SEMANTICS
        and isinstance(target, Mapping)
        and target.get("status") == "RESOLVED"
        and target.get("target_id") == CANONICAL_TARGET_ID
    )
    identity = {
        "status": "READY" if identity_ok else "PROVENANCE_INVALID",
        "model_id": MODEL_NAME,
        "generation": MODEL_GENERATION,
        "model_fingerprint": MODEL_FINGERPRINT,
        "ranking": RANKING_SEMANTICS,
        "canonical_target_id": CANONICAL_TARGET_ID,
    }

    try:
        inv = validate_partial_session_inventory(inventory)
    except PreAccessReadinessError as exc:
        inv = {
            "status": "PROVENANCE_INVALID",
            "observed_sessions": None,
            "required_sessions": REQUIRED_SESSION_COUNT,
            "remaining_sessions": None,
            "reason": str(exc),
            "rows": [],
        }
    signal_dates = [row["session_date"] for row in inv.get("rows", [])]
    cal = calendar_eligibility(signal_dates, official_trading_sessions, as_of_session=as_of_session)
    if any(row["calendar_identity_status"] != "READY" for row in cal["rows"]):
        cal["status"] = "PROVENANCE_INVALID"
    elif inv.get("observed_sessions") == REQUIRED_SESSION_COUNT and cal["h10_calendar_eligible_count"] == REQUIRED_SESSION_COUNT:
        cal["status"] = "READY"
    else:
        cal["status"] = "ACCUMULATING"

    access = dict(access_state)
    if access.get("status") not in {"READY", "PROVENANCE_INVALID", "ACCESS_CONTAMINATION", "PENDING_EXPECTED"}:
        raise PreAccessReadinessError("ACCESS_STATE_STATUS_INVALID")

    components = {
        "counter": _normalize_component("counter", counter),
        "target_attestation": _normalize_component("target_attestation", target_attestation),
        "paper_attestation": _normalize_component("paper_attestation", paper_attestation),
        "benchmark_attestation": _normalize_component("benchmark_attestation", benchmark_attestation),
        "prior_access_audit": _normalize_component("prior_access_audit", prior_access_audit),
        "code_pins": _normalize_component("code_pins", code_pins),
    }
    components["target_attestation"]["target_values"] = PROTECTED_STATUS

    all_statuses = [identity["status"], inv["status"], cal["status"], access["status"]] + [
        item["status"] for item in components.values()
    ]
    if "ACCESS_CONTAMINATION" in all_statuses:
        overall = "PREACCESS_ACCESS_CONTAMINATED"
    elif "PROVENANCE_INVALID" in all_statuses:
        overall = "PREACCESS_PROVENANCE_INVALID"
    else:
        observed = inv.get("observed_sessions")
        if observed != REQUIRED_SESSION_COUNT or cal["h10_calendar_eligible_count"] != REQUIRED_SESSION_COUNT:
            overall = "ACCUMULATING_OUTCOME_BLIND"
        elif all(item["status"] == "READY" for item in components.values()) and access["status"] == "READY" and identity["status"] == "READY":
            overall = "PREACCESS_READY_FOR_EXISTING_GATE"
        else:
            overall = "PREACCESS_REQUIREMENTS_INCOMPLETE"

    return {
        "schema_version": SCHEMA_VERSION,
        "overall_status": overall,
        "identity": identity,
        "inventory": inv,
        "calendar_eligibility": cal,
        "components": components,
        "access_state": access,
        "protected_outcomes": {
            "status": PROTECTED_STATUS,
            "accessed": False,
            "values_loaded": False,
        },
        "existing_gate_preflight_eligible": overall == "PREACCESS_READY_FOR_EXISTING_GATE",
        "guards": {
            "protected_outcomes_accessed": False,
            "real_protected_loader_called": False,
            "real_outcome_access_marker_written": False,
            "forward_counter_changed": False,
            "provider_capture_triggered": False,
            "model_changed": False,
            "decision_changed": False,
            "sizing_changed": False,
            "execution_science_changed": False,
            "active_runtime_changed": False,
            "scheduler_changed": False,
        },
    }


def render_readiness_text(report: Mapping[str, Any]) -> str:
    inv = report.get("inventory") if isinstance(report.get("inventory"), Mapping) else {}
    cal = report.get("calendar_eligibility") if isinstance(report.get("calendar_eligibility"), Mapping) else {}
    identity = report.get("identity") if isinstance(report.get("identity"), Mapping) else {}
    access = report.get("access_state") if isinstance(report.get("access_state"), Mapping) else {}
    components = report.get("components") if isinstance(report.get("components"), Mapping) else {}

    def cstatus(name: str) -> str:
        item = components.get(name)
        return str(item.get("status", "NOT_AVAILABLE")) if isinstance(item, Mapping) else "NOT_AVAILABLE"

    lines = [
        "V4-X1 PROSPECTIVE PRE-ACCESS READINESS",
        "",
        "Accumulation",
        f"  scored/inventory          {inv.get('observed_sessions', 'N/A')} / {inv.get('required_sessions', REQUIRED_SESSION_COUNT)}",
        f"  H5 calendar eligible      {cal.get('h5_calendar_eligible_count', 'N/A')} / {inv.get('observed_sessions', 'N/A')}",
        f"  H10 calendar eligible     {cal.get('h10_calendar_eligible_count', 'N/A')} / {inv.get('observed_sessions', 'N/A')}",
        "",
        "Frozen identity",
        f"  model + target            {identity.get('status', 'NOT_AVAILABLE')}",
        "",
        "Pre-access requirements",
        f"  counter                   {cstatus('counter')}",
        f"  target attestation        {cstatus('target_attestation')} ({PROTECTED_STATUS})",
        f"  PaperState                {cstatus('paper_attestation')}",
        f"  benchmark                 {cstatus('benchmark_attestation')}",
        f"  prior access audit        {cstatus('prior_access_audit')}",
        f"  code pins                 {cstatus('code_pins')}",
        f"  access state              {access.get('status', 'NOT_AVAILABLE')}",
        "",
        f"Overall: {report.get('overall_status', 'PREACCESS_PROVENANCE_INVALID')}",
    ]
    return "\n".join(lines)


__all__ = [
    "CANONICAL_TARGET_ID",
    "MODEL_FINGERPRINT",
    "MODEL_GENERATION",
    "MODEL_NAME",
    "OVERALL_STATUSES",
    "PARTIAL_INVENTORY_COLUMNS",
    "PROTECTED_STATUS",
    "PreAccessReadinessError",
    "READINESS_COMPONENT_STATUSES",
    "REQUIRED_SESSION_COUNT",
    "RANKING_SEMANTICS",
    "SCHEMA_VERSION",
    "assert_safe_reference",
    "build_readiness_report",
    "calendar_eligibility",
    "inspect_access_state",
    "render_readiness_text",
    "validate_outcome_blind_metadata",
    "validate_partial_session_inventory",
]
