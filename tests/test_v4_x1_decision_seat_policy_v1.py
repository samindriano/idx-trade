from __future__ import annotations

import hashlib
import json

import pytest

from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_decision_seat_policy_v1 import (
    DecisionSeatClosePolicyV1,
    SEAT_POLICY_SCHEMA,
    authorize_decision_seat_close,
    verify_decision_seat_policy_payload,
)


def _policy(*, reasons: tuple[str, ...] = ("EXPLICIT_CLOSE",)) -> DecisionSeatClosePolicyV1:
    return DecisionSeatClosePolicyV1(
        schema_version=SEAT_POLICY_SCHEMA,
        policy_id="synthetic-seat-policy-v1",
        authorization_ref="synthetic-authority-ref",
        allowed_close_statuses=("CANCELED", "RELINQUISHED"),
        allowed_close_reasons=reasons,
    )


def test_policy_payload_is_hash_bound_and_canonical() -> None:
    payload = _policy().payload()
    assert verify_decision_seat_policy_payload(payload) == payload
    assert authorize_decision_seat_close(
        _policy(),
        status="CANCELED",
        reason="EXPLICIT_CLOSE",
    ) == payload["policy_sha256"]


def test_policy_is_required_for_explicit_close_authorization() -> None:
    with pytest.raises(DecisionV1Error, match="SEAT_POLICY_REQUIRED"):
        authorize_decision_seat_close(
            None,
            status="CANCELED",
            reason="EXPLICIT_CLOSE",
        )


@pytest.mark.parametrize(
    ("status", "reason", "error"),
    (
        ("CANCELED", "UNDECLARED_REASON", "REASON_NOT_AUTHORIZED"),
        ("RELINQUISHED", "UNDECLARED_REASON", "REASON_NOT_AUTHORIZED"),
    ),
)
def test_policy_rejects_undeclared_close_semantics(
    status: str,
    reason: str,
    error: str,
) -> None:
    with pytest.raises(DecisionV1Error, match=error):
        authorize_decision_seat_close(_policy(), status=status, reason=reason)


def test_policy_rejects_hash_valid_noncanonical_extension() -> None:
    payload = _policy().payload()
    payload["unexpected_extension"] = True
    body = dict(payload)
    body.pop("policy_sha256")
    payload["policy_sha256"] = hashlib.sha256(
        (json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    with pytest.raises(DecisionV1Error, match="PAYLOAD_NOT_CANONICAL"):
        verify_decision_seat_policy_payload(payload)
