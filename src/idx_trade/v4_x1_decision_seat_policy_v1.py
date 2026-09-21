"""Versioned authorization envelope for explicit Decision-seat closure.

The runtime owns the transition mechanics, but it must not invent which close
status or reason is authorized.  This module therefore verifies a caller-
supplied, hash-bound policy and deliberately provides no production default.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from .v4_x1_decision_v1_contract import DecisionV1Error


SEAT_POLICY_SCHEMA = "idx_trade_decision_seat_policy_v1"
SEAT_CLOSE_STATUSES = frozenset({"CANCELED", "RELINQUISHED"})
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_POLICY_KEYS = frozenset(
    {
        "schema_version",
        "policy_id",
        "authorization_ref",
        "allowed_close_statuses",
        "allowed_close_reasons",
        "outcome_access",
        "policy_sha256",
    }
)


def _canonical_hash(value: object) -> str:
    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise DecisionV1Error(code)
    return value


def _sha(value: object, code: str) -> str:
    text = _text(value, code)
    if not _SHA_RE.fullmatch(text) or text.lower() != text:
        raise DecisionV1Error(code)
    return text


def _canonical_values(
    values: tuple[str, ...],
    *,
    code: str,
    allowed: frozenset[str] | None = None,
) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise DecisionV1Error(code)
    if any(not isinstance(value, str) or not value or value.strip() != value for value in values):
        raise DecisionV1Error(code)
    if len(set(values)) != len(values) or tuple(sorted(values)) != values:
        raise DecisionV1Error(code)
    if allowed is not None and not set(values).issubset(allowed):
        raise DecisionV1Error(code)
    return values


@dataclass(frozen=True)
class DecisionSeatClosePolicyV1:
    schema_version: str
    policy_id: str
    authorization_ref: str
    allowed_close_statuses: tuple[str, ...]
    allowed_close_reasons: tuple[str, ...]
    outcome_access: bool = False

    def payload(self) -> dict[str, Any]:
        if self.schema_version != SEAT_POLICY_SCHEMA:
            raise DecisionV1Error("DECISION_SEAT_POLICY_SCHEMA_INVALID")
        _text(self.policy_id, "DECISION_SEAT_POLICY_ID_INVALID")
        _text(self.authorization_ref, "DECISION_SEAT_POLICY_AUTHORIZATION_REF_INVALID")
        _canonical_values(
            self.allowed_close_statuses,
            code="DECISION_SEAT_POLICY_STATUS_SET_INVALID",
            allowed=SEAT_CLOSE_STATUSES,
        )
        _canonical_values(
            self.allowed_close_reasons,
            code="DECISION_SEAT_POLICY_REASON_SET_INVALID",
        )
        if self.outcome_access is not False:
            raise DecisionV1Error("DECISION_SEAT_POLICY_OUTCOME_ACCESS_INVALID")
        body = {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "authorization_ref": self.authorization_ref,
            "allowed_close_statuses": list(self.allowed_close_statuses),
            "allowed_close_reasons": list(self.allowed_close_reasons),
            "outcome_access": False,
        }
        body["policy_sha256"] = _canonical_hash(body)
        return body


def verify_decision_seat_policy_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionV1Error("DECISION_SEAT_POLICY_REQUIRED")
    payload = dict(value)
    if set(payload) != _POLICY_KEYS:
        raise DecisionV1Error("DECISION_SEAT_POLICY_PAYLOAD_NOT_CANONICAL")
    declared = _sha(
        payload.pop("policy_sha256", None),
        "DECISION_SEAT_POLICY_HASH_INVALID",
    )
    try:
        computed = _canonical_hash(payload)
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(
            "DECISION_SEAT_POLICY_PAYLOAD_NOT_CANONICAL"
        ) from exc
    if computed != declared:
        raise DecisionV1Error("DECISION_SEAT_POLICY_HASH_MISMATCH")
    statuses = payload.get("allowed_close_statuses")
    reasons = payload.get("allowed_close_reasons")
    if not isinstance(statuses, list) or not isinstance(reasons, list):
        raise DecisionV1Error("DECISION_SEAT_POLICY_PAYLOAD_NOT_CANONICAL")
    try:
        policy = DecisionSeatClosePolicyV1(
            schema_version=payload["schema_version"],
            policy_id=payload["policy_id"],
            authorization_ref=payload["authorization_ref"],
            allowed_close_statuses=tuple(statuses),
            allowed_close_reasons=tuple(reasons),
            outcome_access=payload["outcome_access"],
        )
        canonical = policy.payload()
    except (DecisionV1Error, KeyError, TypeError) as exc:
        if isinstance(exc, DecisionV1Error):
            raise
        raise DecisionV1Error("DECISION_SEAT_POLICY_PAYLOAD_NOT_CANONICAL") from exc
    expected = {**payload, "policy_sha256": declared}
    if canonical != expected:
        raise DecisionV1Error("DECISION_SEAT_POLICY_PAYLOAD_NOT_CANONICAL")
    return expected


def authorize_decision_seat_close(
    policy: DecisionSeatClosePolicyV1 | None,
    *,
    status: str,
    reason: str,
) -> str:
    """Return the verified policy hash or fail closed without a policy."""

    if not isinstance(policy, DecisionSeatClosePolicyV1):
        raise DecisionV1Error("DECISION_SEAT_POLICY_REQUIRED")
    payload = verify_decision_seat_policy_payload(policy.payload())
    if status not in payload["allowed_close_statuses"]:
        raise DecisionV1Error("DECISION_SEAT_POLICY_STATUS_NOT_AUTHORIZED")
    if reason not in payload["allowed_close_reasons"]:
        raise DecisionV1Error("DECISION_SEAT_POLICY_REASON_NOT_AUTHORIZED")
    return str(payload["policy_sha256"])


__all__ = [
    "SEAT_POLICY_SCHEMA",
    "SEAT_CLOSE_STATUSES",
    "DecisionSeatClosePolicyV1",
    "verify_decision_seat_policy_payload",
    "authorize_decision_seat_close",
]
