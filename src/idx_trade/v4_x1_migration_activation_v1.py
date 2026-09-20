"""Explicit, immutable authorization gate for legacy snapshot activation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any

from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_migration_provenance_v1 import (
    MIGRATION_ALREADY_COMPATIBLE,
    MIGRATION_BLOCKED_RECONCILIATION,
    MIGRATION_REQUIRES_LEGACY_MODE,
    verify_migration_provenance_payload,
)


ACTIVATION_POLICY_SCHEMA = "idx_trade_migration_activation_policy_v1"
ACTIVATION_DECISION_SCHEMA = "idx_trade_migration_activation_decision_v1"
ACTIVATE_COMPATIBLE = "ACTIVATE_COMPATIBLE"
ACTIVATE_LEGACY_MODE = "ACTIVATE_LEGACY_MODE"
REQUIRES_AUTHORIZATION = "REQUIRES_AUTHORIZATION"
BLOCKED_RECONCILIATION = "BLOCKED_RECONCILIATION"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_hash(value: object) -> str:
    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_text(value: object, code: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise DecisionV1Error(code)
    return text


def _sha(value: object, code: str) -> str:
    text = _required_text(value, code).lower()
    if not _SHA_RE.fullmatch(text):
        raise DecisionV1Error(code)
    return text


@dataclass(frozen=True)
class MigrationActivationPolicyV1:
    schema_version: str
    policy_id: str
    authorization_ref: str
    allow_legacy_mode: bool
    outcome_access: bool = False

    def payload(self) -> dict[str, Any]:
        if self.schema_version != ACTIVATION_POLICY_SCHEMA:
            raise DecisionV1Error("MIGRATION_ACTIVATION_POLICY_SCHEMA_INVALID")
        _required_text(self.policy_id, "MIGRATION_ACTIVATION_POLICY_ID_MISSING")
        _required_text(
            self.authorization_ref,
            "MIGRATION_ACTIVATION_POLICY_AUTHORIZATION_REF_MISSING",
        )
        if not isinstance(self.allow_legacy_mode, bool):
            raise DecisionV1Error("MIGRATION_ACTIVATION_POLICY_LEGACY_FLAG_INVALID")
        if self.outcome_access is not False:
            raise DecisionV1Error("MIGRATION_ACTIVATION_POLICY_OUTCOME_ACCESS_INVALID")
        body = asdict(self)
        body["policy_sha256"] = _canonical_hash(body)
        return body


@dataclass(frozen=True)
class MigrationActivationDecisionV1:
    schema_version: str
    provenance_payload_sha256: str
    policy_sha256: str
    activation_status: str
    reason_code: str
    outcome_access: bool = False

    def payload(self) -> dict[str, Any]:
        if self.schema_version != ACTIVATION_DECISION_SCHEMA:
            raise DecisionV1Error("MIGRATION_ACTIVATION_DECISION_SCHEMA_INVALID")
        _sha(
            self.provenance_payload_sha256,
            "MIGRATION_ACTIVATION_PROVENANCE_SHA_INVALID",
        )
        _sha(self.policy_sha256, "MIGRATION_ACTIVATION_POLICY_SHA_INVALID")
        if self.activation_status not in {
            ACTIVATE_COMPATIBLE,
            ACTIVATE_LEGACY_MODE,
            REQUIRES_AUTHORIZATION,
            BLOCKED_RECONCILIATION,
        }:
            raise DecisionV1Error("MIGRATION_ACTIVATION_STATUS_INVALID")
        _required_text(self.reason_code, "MIGRATION_ACTIVATION_REASON_MISSING")
        if self.outcome_access is not False:
            raise DecisionV1Error("MIGRATION_ACTIVATION_OUTCOME_ACCESS_INVALID")
        body = asdict(self)
        body["payload_sha256"] = _canonical_hash(body)
        return body


def verify_migration_activation_policy_payload(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionV1Error("MIGRATION_ACTIVATION_POLICY_REQUIRED")
    payload = dict(value)
    declared = _sha(
        payload.pop("policy_sha256", None),
        "MIGRATION_ACTIVATION_POLICY_SHA_INVALID",
    )
    if _canonical_hash(payload) != declared:
        raise DecisionV1Error("MIGRATION_ACTIVATION_POLICY_HASH_MISMATCH")
    policy = MigrationActivationPolicyV1(**payload)
    if policy.payload()["policy_sha256"] != declared:
        raise DecisionV1Error("MIGRATION_ACTIVATION_POLICY_HASH_MISMATCH")
    return {**payload, "policy_sha256": declared}


def verify_migration_activation_decision_payload(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionV1Error("MIGRATION_ACTIVATION_DECISION_REQUIRED")
    payload = dict(value)
    declared = _sha(
        payload.pop("payload_sha256", None),
        "MIGRATION_ACTIVATION_DECISION_HASH_INVALID",
    )
    if _canonical_hash(payload) != declared:
        raise DecisionV1Error("MIGRATION_ACTIVATION_DECISION_HASH_MISMATCH")
    decision = MigrationActivationDecisionV1(**payload)
    if decision.payload()["payload_sha256"] != declared:
        raise DecisionV1Error("MIGRATION_ACTIVATION_DECISION_HASH_MISMATCH")
    return {**payload, "payload_sha256": declared}


def authorize_migration_activation(
    provenance_payload: dict[str, Any],
    policy: MigrationActivationPolicyV1,
) -> MigrationActivationDecisionV1:
    """Return an explicit activation decision; never mutate runtime state."""

    provenance = verify_migration_provenance_payload(provenance_payload)
    policy_payload = verify_migration_activation_policy_payload(policy.payload())
    disposition = provenance.get("disposition")
    if disposition == MIGRATION_ALREADY_COMPATIBLE:
        status = ACTIVATE_COMPATIBLE
        reason = "SOURCE_ALREADY_COMPATIBLE"
    elif disposition == MIGRATION_REQUIRES_LEGACY_MODE:
        if policy.allow_legacy_mode:
            status = ACTIVATE_LEGACY_MODE
            reason = "EXPLICIT_LEGACY_MODE_AUTHORIZATION"
        else:
            status = REQUIRES_AUTHORIZATION
            reason = "LEGACY_MODE_NOT_AUTHORIZED_BY_POLICY"
    elif disposition == MIGRATION_BLOCKED_RECONCILIATION:
        status = BLOCKED_RECONCILIATION
        reason = "SOURCE_REQUIRES_RECONCILIATION"
    else:
        raise DecisionV1Error("MIGRATION_ACTIVATION_DISPOSITION_INVALID")
    return MigrationActivationDecisionV1(
        schema_version=ACTIVATION_DECISION_SCHEMA,
        provenance_payload_sha256=str(provenance["payload_sha256"]),
        policy_sha256=str(policy_payload["policy_sha256"]),
        activation_status=status,
        reason_code=reason,
    )


def _write_immutable(path: str | Path, payload: dict[str, Any], *, conflict_code: str) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if target.exists():
        if target.read_bytes() != data:
            raise DecisionV1Error(conflict_code)
        return target
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temp = Path(temp_name)
    try:
        with open(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
        if target.exists():
            if target.read_bytes() != data:
                raise DecisionV1Error(conflict_code)
        else:
            temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    return target


def write_migration_activation_decision_v1(
    path: str | Path,
    decision: MigrationActivationDecisionV1,
) -> Path:
    if not isinstance(decision, MigrationActivationDecisionV1):
        raise DecisionV1Error("MIGRATION_ACTIVATION_DECISION_OBJECT_REQUIRED")
    payload = decision.payload()
    verify_migration_activation_decision_payload(payload)
    return _write_immutable(
        path,
        payload,
        conflict_code="MIGRATION_ACTIVATION_DECISION_IMMUTABLE_CONFLICT",
    )


def load_migration_activation_decision_v1(path: str | Path) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DecisionV1Error("MIGRATION_ACTIVATION_DECISION_READ_FAILED") from exc
    return verify_migration_activation_decision_payload(payload)


__all__ = [
    "ACTIVATION_POLICY_SCHEMA",
    "ACTIVATION_DECISION_SCHEMA",
    "ACTIVATE_COMPATIBLE",
    "ACTIVATE_LEGACY_MODE",
    "REQUIRES_AUTHORIZATION",
    "BLOCKED_RECONCILIATION",
    "MigrationActivationPolicyV1",
    "MigrationActivationDecisionV1",
    "authorize_migration_activation",
    "verify_migration_activation_policy_payload",
    "verify_migration_activation_decision_payload",
    "write_migration_activation_decision_v1",
    "load_migration_activation_decision_v1",
]
