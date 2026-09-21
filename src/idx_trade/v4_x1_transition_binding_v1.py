"""Fail-closed joins between identity, execution causes, obligations, and Decision."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any, Sequence

from .decision_v2_minimal import DecisionV2Plan
from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_execution_cause_v1 import ExecutionCauseV1
from .v4_x1_execution_v1_contract import ExecutionResult
from .v4_x1_identity_contract_v1 import (
    SecurityIdentityV1,
    normalize_security_identities,
    resolve_security_identity,
    security_identity_hash,
)
from .v4_x1_quantity_obligation_v1 import (
    QuantityObligation,
    normalize_obligations,
    obligation_hash,
    obligations_hash,
)


TRANSITION_BINDING_SCHEMA = "idx_trade_transition_binding_v1"
_DECISION_KEYS = frozenset(
    {
        "schema_version",
        "binding_type",
        "decision_session_date",
        "decision_rule_id",
        "identity_hash",
        "resolutions",
    }
)
_CAUSE_KEYS = frozenset(
    {
        "schema_version",
        "binding_type",
        "execution_session_date",
        "obligations_hash",
        "joins",
    }
)
_RESOLUTION_KEYS = frozenset(
    {
        "ticker",
        "canonical_security_id",
        "instrument_class",
        "identity_revision",
        "source_evidence_sha256",
    }
)
_JOIN_KEYS = frozenset(
    {
        "cause_id",
        "obligation_id",
        "obligation_sha256",
        "remaining_shares",
        "next_decision_action",
    }
)


def _canonical_hash(value: object) -> str:
    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and value == value.lower()
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _require_sha(value: object) -> None:
    if not _is_sha(value):
        raise DecisionV1Error("TRANSITION_BINDING_HASH_INVALID")


def _plan_tickers(plan: DecisionV2Plan) -> tuple[str, ...]:
    values: set[str] = set(plan.current_shadow_positions) | set(plan.target_positions)
    values.update(plan.hold_tickers)
    values.update(row.ticker for row in plan.incumbent_observations)
    values.update(row.ticker for row in plan.challenger_observations)
    for intent in (*plan.buy_intents, *plan.sell_intents):
        values.add(intent.ticker)
        if intent.replacement_peer is not None:
            values.add(intent.replacement_peer)
    return tuple(sorted(values))


def build_decision_identity_binding_v1(
    plan: DecisionV2Plan,
    identities: Sequence[SecurityIdentityV1],
) -> dict[str, Any]:
    """Resolve every Decision ticker against caller-supplied identity evidence."""

    if not isinstance(plan, DecisionV2Plan):
        raise DecisionV1Error("TRANSITION_BINDING_DECISION_PLAN_REQUIRED")
    rows = normalize_security_identities(tuple(identities))
    if not rows:
        raise DecisionV1Error("TRANSITION_BINDING_IDENTITY_EVIDENCE_REQUIRED")
    resolutions: list[dict[str, Any]] = []
    for ticker in _plan_tickers(plan):
        identity = resolve_security_identity(
            rows,
            ticker=ticker,
            as_of_session_date=plan.decision_session_date,
        )
        resolutions.append(
            {
                "ticker": ticker,
                "canonical_security_id": identity.canonical_security_id,
                "instrument_class": identity.instrument_class,
                "identity_revision": identity.identity_revision,
                "source_evidence_sha256": identity.source_evidence_sha256,
            }
        )
    body: dict[str, Any] = {
        "schema_version": TRANSITION_BINDING_SCHEMA,
        "binding_type": "DECISION_IDENTITY",
        "decision_session_date": plan.decision_session_date,
        "decision_rule_id": plan.rule_id,
        "identity_hash": security_identity_hash(rows),
        "resolutions": resolutions,
    }
    body["payload_sha256"] = _canonical_hash(body)
    return body


def _build_cause_obligation_binding_payload(
    *,
    obligations: Sequence[QuantityObligation],
    execution_session_date: str,
    causes: Sequence[ExecutionCauseV1],
) -> dict[str, Any]:
    """Build a cause/obligation join from verified state-after rows."""

    normalized_obligations = normalize_obligations(tuple(obligations))
    joins: list[dict[str, Any]] = []
    for cause in causes:
        if not isinstance(cause, ExecutionCauseV1):
            raise DecisionV1Error("TRANSITION_BINDING_CAUSE_INVALID")
        matches = tuple(
            row
            for row in normalized_obligations
            if row.side == cause.side
            and row.canonical_ticker == cause.ticker
            and row.latest_attempt_session_date == execution_session_date
        )
        if cause.planned_shares == 0:
            if len(matches) > 1:
                raise DecisionV1Error("TRANSITION_BINDING_OBLIGATION_JOIN_AMBIGUOUS")
            if matches:
                obligation = matches[0]
                joins.append(
                    {
                        "cause_id": cause.cause_id,
                        "obligation_id": obligation.obligation_id,
                        "obligation_sha256": obligation_hash(obligation),
                        "remaining_shares": obligation.remaining_shares,
                        "next_decision_action": (
                            "RETRY_OBLIGATION"
                            if obligation.remaining_shares
                            else "NONE"
                        ),
                    }
                )
                continue
            joins.append(
                {
                    "cause_id": cause.cause_id,
                    "obligation_id": None,
                    "obligation_sha256": None,
                    "remaining_shares": 0,
                    "next_decision_action": "NONE",
                }
            )
            continue
        if len(matches) != 1:
            raise DecisionV1Error("TRANSITION_BINDING_OBLIGATION_JOIN_AMBIGUOUS")
        obligation = matches[0]
        if obligation.remaining_shares != cause.remaining_shares:
            raise DecisionV1Error("TRANSITION_BINDING_REMAINDER_MISMATCH")
        joins.append(
            {
                "cause_id": cause.cause_id,
                "obligation_id": obligation.obligation_id,
                "obligation_sha256": obligation_hash(obligation),
                "remaining_shares": obligation.remaining_shares,
                "next_decision_action": (
                    "RETRY_OBLIGATION" if obligation.remaining_shares else "NONE"
                ),
            }
        )
    body: dict[str, Any] = {
        "schema_version": TRANSITION_BINDING_SCHEMA,
        "binding_type": "CAUSE_OBLIGATION",
        "execution_session_date": execution_session_date,
        "obligations_hash": obligations_hash(normalized_obligations),
        "joins": joins,
    }
    body["payload_sha256"] = _canonical_hash(body)
    return body


def build_cause_obligation_binding_v1(
    result: ExecutionResult,
    causes: Sequence[ExecutionCauseV1],
) -> dict[str, Any]:
    """Bind each execution cause to the obligation it changed."""

    if not isinstance(result, ExecutionResult):
        raise DecisionV1Error("TRANSITION_BINDING_EXECUTION_RESULT_REQUIRED")
    return _build_cause_obligation_binding_payload(
        obligations=result.state_after.obligations,
        execution_session_date=result.execution_session_date,
        causes=causes,
    )


def verify_cause_obligation_binding_v1(
    value: object,
    *,
    execution_session_date: str,
    causes: Sequence[ExecutionCauseV1],
    obligations: Sequence[QuantityObligation],
) -> dict[str, Any]:
    """Verify every persisted join against the exact state-after obligations."""

    payload = verify_transition_binding_payload(value)
    if payload.get("binding_type") != "CAUSE_OBLIGATION":
        raise DecisionV1Error("TRANSITION_BINDING_CAUSE_TYPE_INVALID")
    if payload.get("execution_session_date") != execution_session_date:
        raise DecisionV1Error("TRANSITION_BINDING_CAUSE_SESSION_MISMATCH")
    expected = _build_cause_obligation_binding_payload(
        obligations=obligations,
        execution_session_date=execution_session_date,
        causes=causes,
    )
    if payload != expected:
        raise DecisionV1Error("TRANSITION_BINDING_CAUSE_CONTENT_MISMATCH")
    return payload


def verify_decision_identity_binding_v1(
    value: object,
    identities: Sequence[SecurityIdentityV1],
) -> dict[str, Any]:
    """Revalidate a persisted Decision identity binding on idempotent replay."""

    payload = verify_transition_binding_payload(value)
    if payload.get("binding_type") != "DECISION_IDENTITY":
        raise DecisionV1Error("TRANSITION_BINDING_IDENTITY_TYPE_INVALID")
    rows = normalize_security_identities(tuple(identities))
    if not rows or payload.get("identity_hash") != security_identity_hash(rows):
        raise DecisionV1Error("TRANSITION_BINDING_IDENTITY_HASH_MISMATCH")
    for resolution in payload.get("resolutions", ()):
        if not isinstance(resolution, dict):
            raise DecisionV1Error("TRANSITION_BINDING_IDENTITY_ROW_INVALID")
        identity = resolve_security_identity(
            rows,
            ticker=resolution.get("ticker"),
            as_of_session_date=str(payload.get("decision_session_date") or ""),
        )
        if (
            resolution.get("canonical_security_id") != identity.canonical_security_id
            or resolution.get("instrument_class") != identity.instrument_class
            or resolution.get("identity_revision") != identity.identity_revision
            or resolution.get("source_evidence_sha256")
            != identity.source_evidence_sha256
        ):
            raise DecisionV1Error("TRANSITION_BINDING_IDENTITY_ROW_MISMATCH")
    return payload


def verify_transition_binding_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionV1Error("TRANSITION_BINDING_PAYLOAD_REQUIRED")
    raw_declared = value.get("payload_sha256")
    if (
        not isinstance(raw_declared, str)
        or raw_declared != raw_declared.lower()
        or len(raw_declared) != 64
        or any(char not in "0123456789abcdef" for char in raw_declared)
    ):
        raise DecisionV1Error("TRANSITION_BINDING_PAYLOAD_HASH_MISMATCH")
    payload = dict(value)
    declared = payload.pop("payload_sha256")
    if _canonical_hash(payload) != declared:
        raise DecisionV1Error("TRANSITION_BINDING_PAYLOAD_HASH_MISMATCH")
    binding_type = payload.get("binding_type")
    expected_keys = (
        _DECISION_KEYS if binding_type == "DECISION_IDENTITY" else _CAUSE_KEYS
    )
    if set(payload) != expected_keys:
        raise DecisionV1Error("TRANSITION_BINDING_PAYLOAD_NOT_CANONICAL")
    if payload.get("schema_version") != TRANSITION_BINDING_SCHEMA:
        raise DecisionV1Error("TRANSITION_BINDING_SCHEMA_MISMATCH")
    if binding_type not in {"DECISION_IDENTITY", "CAUSE_OBLIGATION"}:
        raise DecisionV1Error("TRANSITION_BINDING_TYPE_INVALID")
    session_key = (
        "decision_session_date"
        if binding_type == "DECISION_IDENTITY"
        else "execution_session_date"
    )
    session = payload[session_key]
    if not isinstance(session, str):
        raise DecisionV1Error("TRANSITION_BINDING_DATE_INVALID")
    try:
        parsed_session = date.fromisoformat(session)
    except ValueError as exc:
        raise DecisionV1Error("TRANSITION_BINDING_DATE_INVALID") from exc
    if parsed_session.isoformat() != session:
        raise DecisionV1Error("TRANSITION_BINDING_DATE_INVALID")
    hash_keys = (
        ("identity_hash",)
        if binding_type == "DECISION_IDENTITY"
        else ("obligations_hash",)
    )
    for key in hash_keys:
        candidate = payload[key]
        if (
            not isinstance(candidate, str)
            or candidate != candidate.lower()
            or len(candidate) != 64
            or any(char not in "0123456789abcdef" for char in candidate)
        ):
            raise DecisionV1Error("TRANSITION_BINDING_HASH_INVALID")
    rows = payload[
        "resolutions" if binding_type == "DECISION_IDENTITY" else "joins"
    ]
    if not isinstance(rows, list):
        raise DecisionV1Error("TRANSITION_BINDING_ROWS_INVALID")
    if binding_type == "DECISION_IDENTITY":
        if not isinstance(payload["decision_rule_id"], str) or not payload["decision_rule_id"]:
            raise DecisionV1Error("TRANSITION_BINDING_RULE_INVALID")
        previous_ticker: str | None = None
        for row in rows:
            if not isinstance(row, dict) or set(row) != _RESOLUTION_KEYS:
                raise DecisionV1Error("TRANSITION_BINDING_ROW_NOT_CANONICAL")
            ticker = row["ticker"]
            if (
                not isinstance(ticker, str)
                or not ticker
                or (
                    previous_ticker is not None
                    and ticker <= previous_ticker
                )
                or not isinstance(row["canonical_security_id"], str)
                or not row["canonical_security_id"]
                or not isinstance(row["instrument_class"], str)
                or not row["instrument_class"]
                or not isinstance(row["identity_revision"], str)
                or not row["identity_revision"]
            ):
                raise DecisionV1Error("TRANSITION_BINDING_ROW_NOT_CANONICAL")
            _require_sha(row["source_evidence_sha256"])
            previous_ticker = ticker
    else:
        for row in rows:
            if not isinstance(row, dict) or set(row) != _JOIN_KEYS:
                raise DecisionV1Error("TRANSITION_BINDING_ROW_NOT_CANONICAL")
            if (
                not isinstance(row["cause_id"], str)
                or len(row["cause_id"]) != 64
                or any(char not in "0123456789abcdef" for char in row["cause_id"])
                or (
                    row["obligation_id"] is not None
                    and (
                        not isinstance(row["obligation_id"], str)
                        or not row["obligation_id"]
                    )
                )
                or (
                    row["obligation_sha256"] is not None
                    and not _is_sha(row["obligation_sha256"])
                )
                or isinstance(row["remaining_shares"], bool)
                or not isinstance(row["remaining_shares"], int)
                or row["remaining_shares"] < 0
                or row["next_decision_action"] not in {"RETRY_OBLIGATION", "NONE"}
            ):
                raise DecisionV1Error("TRANSITION_BINDING_ROW_NOT_CANONICAL")
    payload["payload_sha256"] = declared
    return payload


__all__ = [
    "TRANSITION_BINDING_SCHEMA",
    "build_decision_identity_binding_v1",
    "build_cause_obligation_binding_v1",
    "verify_cause_obligation_binding_v1",
    "verify_decision_identity_binding_v1",
    "verify_transition_binding_payload",
]
