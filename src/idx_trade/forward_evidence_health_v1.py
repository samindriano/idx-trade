"""Outcome-blind forward evidence completeness and health reporting.

The health layer is deliberately metadata/hash based.  It never loads model
labels, realized outcomes, parquet values, or a protected outcome vault.  A
missing artifact is a pending state, not evidence that the session is ready.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "idx_trade_forward_evidence_health_v1"
HEALTH_STATUSES = frozenset(
    {
        "COMPLETE",
        "PENDING_EXPECTED",
        "ACQUISITION_RETRYING",
        "FAIL_CLOSED_EXTERNAL",
        "PROVENANCE_INVALID",
        "STATE_TRANSITION_BLOCKED",
        "NOT_YET_MATURE",
        "NOT_EXPECTED",
    }
)
PROTECTED_OUTCOME_STATUS = "PROTECTED_NOT_READ"
_PROTECTED_PATH_TOKENS = ("outcome", "label", "realized", "vault")
_PROTECTED_FLAG_KEYS = (
    "outcome_access",
    "outcome_accessed",
    "forward_outcomes_accessed",
    "fresh_forward_outcomes_accessed",
    "protected_outcome_accessed",
    "realized_forward_outcome_loaded",
    "real_outcome_access_marker_written",
)
_SAFE_SUMMARY_KEYS = frozenset(
    {
        "current_forward_counter",
        "stockbit_last_status",
        "official_open_status",
        "decision_state",
        "pending_orders",
        "paperstate_continuity",
        "ca_dividend_state",
        "known_blockers",
        "next_scheduled_action",
    }
)


class EvidenceHealthError(RuntimeError):
    """Raised when a health input cannot be safely interpreted."""


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    path: Path | None
    required: bool = True
    expected_sha256: str | None = None
    session_fields: tuple[str, ...] = ("session_date",)
    expected_status: str | None = None
    expected_fields: tuple[tuple[str, object], ...] = ()
    require_outcome_clean: bool = False


def sha256_file(path: str | Path) -> str:
    target = Path(path).expanduser().resolve()
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _session(value: object) -> str:
    if not isinstance(value, str) or len(value) != 10:
        raise EvidenceHealthError("FORWARD_HEALTH_SESSION_INVALID")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise EvidenceHealthError("FORWARD_HEALTH_SESSION_INVALID") from exc


def _safe_path(path: Path) -> Path:
    lowered = str(path).lower().replace("\\", "/")
    if any(
        token in component
        for component in lowered.split("/")
        for token in _PROTECTED_PATH_TOKENS
    ):
        raise EvidenceHealthError("FORWARD_HEALTH_PROTECTED_ARTIFACT_PATH_REFUSED")
    return path.expanduser().resolve()


def _read_safe_metadata(path: Path) -> dict[str, Any]:
    """Read only a JSON metadata document, never a data/label artifact."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceHealthError("FORWARD_HEALTH_METADATA_INVALID") from exc
    if not isinstance(payload, dict):
        raise EvidenceHealthError("FORWARD_HEALTH_METADATA_INVALID")
    for key in _PROTECTED_FLAG_KEYS:
        if key in payload and payload[key] is not False:
            raise EvidenceHealthError("FORWARD_HEALTH_OUTCOME_GUARD_NOT_CLEAN")
    guards = payload.get("guards")
    if isinstance(guards, Mapping):
        for key in _PROTECTED_FLAG_KEYS:
            if key in guards and guards[key] is not False:
                raise EvidenceHealthError("FORWARD_HEALTH_OUTCOME_GUARD_NOT_CLEAN")
    return payload


def _identity_value(payload: Mapping[str, Any], fields: Sequence[str]) -> object:
    for field in fields:
        if field in payload:
            return payload[field]
    return None


def check_artifact(spec: ArtifactSpec, *, session_date: str) -> dict[str, object]:
    """Check one declared artifact without opening data values."""

    session = _session(session_date)
    base: dict[str, object] = {
        "name": spec.name,
        "required": spec.required,
        "path": str(spec.path.expanduser().resolve()) if spec.path else None,
        "status": "NOT_EXPECTED" if not spec.required else "PENDING_EXPECTED",
        "observed_sha256": None,
        "expected_sha256": spec.expected_sha256,
        "reason": None,
    }
    if spec.path is None:
        base["reason"] = "ARTIFACT_NOT_DECLARED"
        return base
    try:
        path = _safe_path(spec.path)
    except EvidenceHealthError as exc:
        base["status"] = "PROVENANCE_INVALID"
        base["reason"] = str(exc)
        return base
    base["path"] = str(path)
    if not path.is_file():
        base["reason"] = "ARTIFACT_MISSING"
        return base
    try:
        observed = sha256_file(path)
    except OSError:
        base["status"] = "FAIL_CLOSED_EXTERNAL"
        base["reason"] = "ARTIFACT_UNREADABLE"
        return base
    base["observed_sha256"] = observed
    if spec.expected_sha256 and observed != spec.expected_sha256.lower():
        base["status"] = "PROVENANCE_INVALID"
        base["reason"] = "ARTIFACT_SHA256_MISMATCH"
        return base
    if path.suffix.lower() == ".json":
        try:
            metadata = _read_safe_metadata(path)
            identity = _identity_value(metadata, spec.session_fields)
            if spec.session_fields and identity is None:
                base["status"] = "PROVENANCE_INVALID"
                base["reason"] = "SESSION_IDENTITY_MISSING"
                return base
            if identity is not None and str(identity) != session:
                base["status"] = "PROVENANCE_INVALID"
                base["reason"] = "SESSION_IDENTITY_MISMATCH"
                return base
            if spec.expected_status is not None and metadata.get("status") != spec.expected_status:
                base["status"] = "PROVENANCE_INVALID"
                base["reason"] = "ARTIFACT_STATUS_MISMATCH"
                return base
            for field, expected in spec.expected_fields:
                if metadata.get(field) != expected:
                    base["status"] = "PROVENANCE_INVALID"
                    base["reason"] = f"METADATA_FIELD_MISMATCH:{field}"
                    return base
            if spec.require_outcome_clean:
                outcome_blind = metadata.get("outcome_blind")
                if outcome_blind is not True:
                    guards = metadata.get("guards")
                    if not isinstance(guards, Mapping) or any(
                        guards.get(key) is not False for key in _PROTECTED_FLAG_KEYS
                        if key in guards
                    ):
                        base["status"] = "PROVENANCE_INVALID"
                        base["reason"] = "OUTCOME_BLIND_ATTESTATION_MISSING"
                        return base
        except EvidenceHealthError as exc:
            base["status"] = "PROVENANCE_INVALID"
            base["reason"] = str(exc)
            return base
    base["status"] = "COMPLETE"
    return base


def evaluate_session(
    session_date: str,
    artifacts: Sequence[ArtifactSpec],
    *,
    safe_summary: Mapping[str, object] | None = None,
    reported_at_utc: str | None = None,
) -> dict[str, object]:
    """Evaluate a session's declared evidence contract outcome-blind."""

    session = _session(session_date)
    checks = [check_artifact(item, session_date=session) for item in artifacts]
    statuses = {str(item["status"]) for item in checks}
    if "PROVENANCE_INVALID" in statuses:
        overall = "PROVENANCE_INVALID"
    elif "STATE_TRANSITION_BLOCKED" in statuses:
        overall = "STATE_TRANSITION_BLOCKED"
    elif "FAIL_CLOSED_EXTERNAL" in statuses:
        overall = "FAIL_CLOSED_EXTERNAL"
    elif "ACQUISITION_RETRYING" in statuses:
        overall = "ACQUISITION_RETRYING"
    elif "PENDING_EXPECTED" in statuses:
        overall = "PENDING_EXPECTED"
    else:
        overall = "COMPLETE"
    summary = {
        key: value
        for key, value in (safe_summary or {}).items()
        if key in _SAFE_SUMMARY_KEYS
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "session_date": session,
        "overall_status": overall,
        "protected_outcomes": {
            "status": PROTECTED_OUTCOME_STATUS,
            "accessed": False,
            "values_loaded": False,
        },
        "artifacts": checks,
        "operational_summary": summary,
        "reported_at_utc": reported_at_utc or datetime.now(timezone.utc).isoformat(),
    }


def build_operational_summary(
    report: Mapping[str, object],
    *,
    stockbit_last_status: str = "NOT_READ",
    current_forward_counter: int | str = "NOT_READ",
    next_scheduled_action: str = "NOT_READ",
) -> dict[str, object]:
    """Build a safe rolling summary from statuses, never from outcome values."""

    checks = report.get("artifacts")
    by_name = {
        str(item.get("name")): str(item.get("status"))
        for item in checks
        if isinstance(item, Mapping)
    } if isinstance(checks, list) else {}
    blockers = [
        f"{item.get('name')}:{item.get('status')}:{item.get('reason')}"
        for item in checks
        if isinstance(item, Mapping)
        and item.get("required") is True
        and item.get("status") not in {"COMPLETE"}
    ] if isinstance(checks, list) else []
    return {
        "current_session": report.get("session_date"),
        "current_forward_counter": current_forward_counter,
        "stockbit_last_status": stockbit_last_status,
        "official_open_status": by_name.get("official_open_manifest", "NOT_READ"),
        "decision_state": by_name.get("decision_v2_result", "NOT_READ"),
        "pending_orders": by_name.get("prepared_order", "NOT_READ"),
        "paperstate_continuity": by_name.get("paper_state_snapshot", "NOT_READ"),
        "ca_dividend_state": (
            "PENDING_EXPECTED"
            if any(
                by_name.get(name) != "COMPLETE"
                for name in ("prepared_order", "execution_result", "paper_state_snapshot")
            )
            else "NOT_DECLARED"
        ),
        "known_blockers": blockers,
        "next_scheduled_action": next_scheduled_action,
    }


def write_health_report(path: str | Path, report: Mapping[str, object]) -> tuple[Path, str]:
    """Atomically write a redacted health report and return its SHA-256."""

    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    body = dict(report)
    encoded = _canonical_bytes(body)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_bytes(encoded)
    os.replace(temporary, target)
    return target, hashlib.sha256(encoded).hexdigest()


def discover_session_artifacts(
    *,
    forward_monitoring_root: str | Path,
    e2e_runtime_root: str | Path,
    session_date: str,
) -> tuple[ArtifactSpec, ...]:
    """Discover only known safe metadata/artifact paths for one session."""

    session = _session(session_date)
    forward = Path(forward_monitoring_root).expanduser().resolve()
    e2e = Path(e2e_runtime_root).expanduser().resolve()
    model_root = forward / "model_runs" / session
    model_candidates = sorted(
        path / "manifest.json"
        for path in model_root.glob("v4_x1_clean_geometry3_prospective_v1")
        if (path / "manifest.json").is_file()
    )
    model_manifest = model_candidates[0] if model_candidates else None
    return (
        ArtifactSpec(
            "eod_manifest",
            forward / "sessions" / session / "manifest.json",
            expected_status="DATA_READY",
            require_outcome_clean=True,
        ),
        ArtifactSpec(
            "v4_x1_score_manifest",
            model_manifest,
            expected_status="DONE",
            require_outcome_clean=True,
        ),
        ArtifactSpec(
            "official_open_manifest",
            e2e / "official_open" / session / "manifest.json",
            expected_fields=(
                ("authority", "IDX"),
                ("upstream_path", "TradingSummary/GetStockSummary"),
                ("field_semantics", "IDX_OFFICIAL_OPENPRICE"),
            ),
        ),
        ArtifactSpec("decision_v2_result", e2e / "state" / "decisions" / f"{session}.json"),
        ArtifactSpec("prepared_order", e2e / "prepared" / f"{session}.json", session_fields=("execution_session_date", "session_date")),
        ArtifactSpec("execution_result", e2e / "executions" / f"{session}.json", session_fields=("execution_session_date", "session_date")),
        ArtifactSpec(
            "paper_state_snapshot",
            e2e / "forward_execution_v1_1" / "state_snapshots" / f"{session}.json",
            session_fields=("execution_session_date", "session_date"),
        ),
        ArtifactSpec("operational_status", e2e / "operational" / "latest.json", required=False, session_fields=()),
    )


__all__ = [
    "ArtifactSpec",
    "EvidenceHealthError",
    "HEALTH_STATUSES",
    "PROTECTED_OUTCOME_STATUS",
    "SCHEMA_VERSION",
    "check_artifact",
    "discover_session_artifacts",
    "evaluate_session",
    "sha256_file",
    "write_health_report",
]
