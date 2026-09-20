"""Hash-bound, fail-closed provenance for legacy state migration decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any

from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_execution_v1_contract import (
    LEGACY_POSITION_ONLY,
    OBLIGATION_V1_STATE,
    UNKNOWN_ORPHANED_PARTIAL,
    PaperPortfolioState,
    classify_state_for_migration,
    paper_state_hash,
)


MIGRATION_PROVENANCE_SCHEMA = "idx_trade_migration_provenance_v1"
MIGRATION_REQUIRES_LEGACY_MODE = "MIGRATION_REQUIRES_LEGACY_MODE"
MIGRATION_ALREADY_COMPATIBLE = "MIGRATION_ALREADY_COMPATIBLE"
MIGRATION_BLOCKED_RECONCILIATION = "MIGRATION_BLOCKED_RECONCILIATION"
REQUIRES_RECONCILIATION = "REQUIRES_RECONCILIATION"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_hash(value: object) -> str:
    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_sha(value: object, code: str) -> str:
    normalized = str(value).strip().lower()
    if not _SHA_RE.fullmatch(normalized):
        raise DecisionV1Error(code)
    return normalized


def _require_date(value: object, code: str) -> str:
    normalized = str(value).strip()
    try:
        date.fromisoformat(normalized)
    except ValueError as exc:
        raise DecisionV1Error(code) from exc
    return normalized


def _require_utc_timestamp(value: object) -> str:
    normalized = str(value).strip()
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_TIMESTAMP_NOT_UTC")
    if not normalized.endswith("Z"):
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_TIMESTAMP_NOT_CANONICAL")
    return normalized


def _disposition(classification: str) -> str:
    if classification == LEGACY_POSITION_ONLY:
        return MIGRATION_REQUIRES_LEGACY_MODE
    if classification == OBLIGATION_V1_STATE:
        return MIGRATION_ALREADY_COMPATIBLE
    if classification == UNKNOWN_ORPHANED_PARTIAL:
        return MIGRATION_BLOCKED_RECONCILIATION
    if classification == REQUIRES_RECONCILIATION:
        return MIGRATION_BLOCKED_RECONCILIATION
    raise DecisionV1Error("MIGRATION_PROVENANCE_V1_CLASSIFICATION_INVALID")


@dataclass(frozen=True)
class MigrationProvenanceV1:
    schema_version: str
    source_artifact_sha256: str
    source_schema_version: str
    source_session_date: str
    source_state_sha256: str | None
    classification: str
    disposition: str
    reason_code: str
    decided_at_utc: str
    runtime_lineage_sha256: str | None = None

    def payload(self) -> dict[str, Any]:
        body = asdict(self)
        body["payload_sha256"] = _canonical_hash(body)
        return body


def build_migration_provenance_v1(
    state: PaperPortfolioState,
    *,
    source_artifact_sha256: str,
    source_schema_version: str,
    decided_at_utc: str,
    runtime_lineage_sha256: str | None = None,
) -> MigrationProvenanceV1:
    """Record the classifier result without reconstructing legacy quantities."""

    if not isinstance(state, PaperPortfolioState):
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_STATE_REQUIRED")
    artifact_sha = _require_sha(
        source_artifact_sha256,
        "MIGRATION_PROVENANCE_V1_SOURCE_ARTIFACT_SHA_INVALID",
    )
    schema = str(source_schema_version).strip()
    if not schema:
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_SOURCE_SCHEMA_INVALID")
    session = _require_date(
        state.as_of_session_date,
        "MIGRATION_PROVENANCE_V1_SOURCE_DATE_INVALID",
    )
    timestamp = _require_utc_timestamp(decided_at_utc)
    lineage_sha = (
        None
        if runtime_lineage_sha256 is None
        else _require_sha(
            runtime_lineage_sha256,
            "MIGRATION_PROVENANCE_V1_RUNTIME_LINEAGE_SHA_INVALID",
        )
    )

    try:
        classification = classify_state_for_migration(state)
        state_sha = paper_state_hash(state)
        reason = f"CLASSIFIED_{classification}"
    except DecisionV1Error as exc:
        classification = REQUIRES_RECONCILIATION
        state_sha = None
        reason = str(exc)

    return MigrationProvenanceV1(
        schema_version=MIGRATION_PROVENANCE_SCHEMA,
        source_artifact_sha256=artifact_sha,
        source_schema_version=schema,
        source_session_date=session,
        source_state_sha256=state_sha,
        classification=classification,
        disposition=_disposition(classification),
        reason_code=reason,
        decided_at_utc=timestamp,
        runtime_lineage_sha256=lineage_sha,
    )


def verify_migration_provenance_payload(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_REQUIRED")
    payload = dict(value)
    declared = _require_sha(
        payload.pop("payload_sha256", None),
        "MIGRATION_PROVENANCE_V1_PAYLOAD_HASH_INVALID",
    )
    if _canonical_hash(payload) != declared:
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_PAYLOAD_HASH_MISMATCH")
    if payload.get("schema_version") != MIGRATION_PROVENANCE_SCHEMA:
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_SCHEMA_MISMATCH")
    _require_sha(
        payload.get("source_artifact_sha256"),
        "MIGRATION_PROVENANCE_V1_SOURCE_ARTIFACT_SHA_INVALID",
    )
    source_schema = str(payload.get("source_schema_version") or "").strip()
    if not source_schema:
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_SOURCE_SCHEMA_INVALID")
    _require_date(
        payload.get("source_session_date"),
        "MIGRATION_PROVENANCE_V1_SOURCE_DATE_INVALID",
    )
    state_sha = payload.get("source_state_sha256")
    if state_sha is not None:
        _require_sha(state_sha, "MIGRATION_PROVENANCE_V1_SOURCE_STATE_SHA_INVALID")
    classification = str(payload.get("classification") or "")
    disposition = str(payload.get("disposition") or "")
    if disposition != _disposition(classification):
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_DISPOSITION_MISMATCH")
    reason = str(payload.get("reason_code") or "").strip()
    if not reason:
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_REASON_MISSING")
    _require_utc_timestamp(payload.get("decided_at_utc"))
    lineage_sha = payload.get("runtime_lineage_sha256")
    if lineage_sha is not None:
        _require_sha(lineage_sha, "MIGRATION_PROVENANCE_V1_RUNTIME_LINEAGE_SHA_INVALID")
    payload["payload_sha256"] = declared
    return payload


def write_migration_provenance_v1(
    path: str | Path,
    provenance: MigrationProvenanceV1,
) -> Path:
    """Create an immutable provenance artifact; same bytes are idempotent."""

    if not isinstance(provenance, MigrationProvenanceV1):
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_OBJECT_REQUIRED")
    payload = provenance.payload()
    verify_migration_provenance_payload(payload)
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if target.exists():
        if target.read_bytes() != data:
            raise DecisionV1Error("MIGRATION_PROVENANCE_V1_IMMUTABLE_CONFLICT")
        return target
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temp = Path(temp_name)
    try:
        with open(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
        if target.exists():
            if target.read_bytes() != data:
                raise DecisionV1Error("MIGRATION_PROVENANCE_V1_IMMUTABLE_CONFLICT")
            return target
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    if target.read_bytes() != data:
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_WRITE_MISMATCH")
    return target


def load_migration_provenance_v1(path: str | Path) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DecisionV1Error("MIGRATION_PROVENANCE_V1_READ_FAILED") from exc
    return verify_migration_provenance_payload(value)


__all__ = [
    "MIGRATION_PROVENANCE_SCHEMA",
    "MIGRATION_REQUIRES_LEGACY_MODE",
    "MIGRATION_ALREADY_COMPATIBLE",
    "MIGRATION_BLOCKED_RECONCILIATION",
    "REQUIRES_RECONCILIATION",
    "MigrationProvenanceV1",
    "build_migration_provenance_v1",
    "verify_migration_provenance_payload",
    "write_migration_provenance_v1",
    "load_migration_provenance_v1",
]
