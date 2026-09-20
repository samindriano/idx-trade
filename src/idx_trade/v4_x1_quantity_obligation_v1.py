"""Versioned quantity-obligation contract for the V4-X1 paper runtime.

This module is intentionally independent of the existing ticker-level pending
views.  It is the quantity owner for the remediation lane; callers may project
compatibility views, but must not infer completion from ticker membership.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import hashlib
import json
from copy import deepcopy
from typing import Any, Literal

from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_decision_seat_policy_v1 import (
    DecisionSeatClosePolicyV1,
    authorize_decision_seat_close,
    verify_decision_seat_policy_payload,
)


QUANTITY_OBLIGATION_SCHEMA = "idx_trade_quantity_obligation_v1"
LOT_SIZE_SHARES = 100
OBLIGATION_SIDES = frozenset({"BUY", "SELL"})
OBLIGATION_STATUSES = frozenset(
    {"PLANNED", "PARTIAL", "BLOCKED", "FILLED", "CANCELED", "RELINQUISHED"}
)
EVENT_TYPES = frozenset({"PLANNED", "FILL", "BLOCK", "RETRY", "CANCEL", "RELINQUISH"})


def canonical_security_identity(value: object) -> str:
    """Use the retained runtime's canonical ticker normalization for V1.

    This is deliberately small and deterministic.  Full issuer/ISIN authority
    remains a later identity contract and is not inferred here.
    """

    symbol = str(value).upper().replace(".JK", "").strip()
    if not symbol:
        raise DecisionV1Error("QUANTITY_OBLIGATION_EMPTY_SECURITY")
    return symbol


def _session(value: object, code: str) -> str:
    text = str(value or "").strip()
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise DecisionV1Error(code) from exc
    if parsed.isoformat() != text:
        raise DecisionV1Error(code)
    return text


def _shares(value: object, code: str, *, allow_zero: bool = True) -> int:
    if isinstance(value, bool):
        raise DecisionV1Error(code)
    try:
        numeric = int(value)
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(code) from exc
    try:
        if float(value) != numeric:
            raise DecisionV1Error(code)
    except (TypeError, ValueError, OverflowError) as exc:
        raise DecisionV1Error(code) from exc
    if numeric < 0 or (not allow_zero and numeric == 0) or numeric % LOT_SIZE_SHARES:
        raise DecisionV1Error(code)
    return numeric


def _text(value: object, code: str, *, allow_empty: bool = False) -> str:
    text = str(value or "").strip()
    if not text and not allow_empty:
        raise DecisionV1Error(code)
    return text


@dataclass(frozen=True)
class ObligationEvent:
    event_id: str
    event_type: Literal[
        "PLANNED", "FILL", "BLOCK", "RETRY", "CANCEL", "RELINQUISH"
    ]
    session_date: str
    filled_delta_shares: int = 0
    relinquished_delta_shares: int = 0
    reason: str = ""
    parent_state_sha256: str | None = None
    policy_sha256: str | None = None
    policy_payload: dict[str, Any] | None = None

    def validate(self) -> "ObligationEvent":
        _text(self.event_id, "QUANTITY_OBLIGATION_EVENT_ID_INVALID")
        if self.event_type not in EVENT_TYPES:
            raise DecisionV1Error("QUANTITY_OBLIGATION_EVENT_TYPE_INVALID")
        _session(self.session_date, "QUANTITY_OBLIGATION_EVENT_DATE_INVALID")
        _shares(
            self.filled_delta_shares,
            "QUANTITY_OBLIGATION_EVENT_FILLED_INVALID",
        )
        _shares(
            self.relinquished_delta_shares,
            "QUANTITY_OBLIGATION_EVENT_RELINQUISHED_INVALID",
        )
        if self.filled_delta_shares and self.event_type != "FILL":
            raise DecisionV1Error("QUANTITY_OBLIGATION_EVENT_FILL_TYPE_MISMATCH")
        if self.relinquished_delta_shares and self.event_type not in {
            "CANCEL",
            "RELINQUISH",
        }:
            raise DecisionV1Error(
                "QUANTITY_OBLIGATION_EVENT_RELINQUISH_TYPE_MISMATCH"
            )
        if self.parent_state_sha256 is not None:
            parent = _text(
                self.parent_state_sha256,
                "QUANTITY_OBLIGATION_PARENT_HASH_INVALID",
            )
            if len(parent) != 64 or any(c not in "0123456789abcdef" for c in parent.lower()):
                raise DecisionV1Error("QUANTITY_OBLIGATION_PARENT_HASH_INVALID")
        if self.event_type in {"CANCEL", "RELINQUISH"}:
            if self.policy_sha256 is None:
                raise DecisionV1Error(
                    "QUANTITY_OBLIGATION_CLOSE_POLICY_PROVENANCE_REQUIRED"
                )
            if self.policy_payload is None:
                raise DecisionV1Error(
                    "QUANTITY_OBLIGATION_CLOSE_POLICY_PAYLOAD_REQUIRED"
                )
            verified_policy = verify_decision_seat_policy_payload(
                self.policy_payload
            )
            if verified_policy["policy_sha256"] != self.policy_sha256:
                raise DecisionV1Error(
                    "QUANTITY_OBLIGATION_CLOSE_POLICY_HASH_MISMATCH"
                )
            required_status = (
                "RELINQUISHED"
                if self.event_type == "RELINQUISH"
                else "CANCELED"
            )
            if required_status not in verified_policy["allowed_close_statuses"]:
                raise DecisionV1Error(
                    "QUANTITY_OBLIGATION_CLOSE_POLICY_STATUS_NOT_AUTHORIZED"
                )
            if self.reason not in verified_policy["allowed_close_reasons"]:
                raise DecisionV1Error(
                    "QUANTITY_OBLIGATION_CLOSE_POLICY_REASON_NOT_AUTHORIZED"
                )
        elif self.policy_sha256 is not None or self.policy_payload is not None:
            raise DecisionV1Error(
                "QUANTITY_OBLIGATION_POLICY_PROVENANCE_TYPE_MISMATCH"
            )
        if self.policy_sha256 is not None:
            policy_sha = _text(
                self.policy_sha256,
                "QUANTITY_OBLIGATION_POLICY_HASH_INVALID",
            )
            if len(policy_sha) != 64 or any(
                c not in "0123456789abcdef" for c in policy_sha
            ):
                raise DecisionV1Error("QUANTITY_OBLIGATION_POLICY_HASH_INVALID")
        return self


@dataclass(frozen=True)
class QuantityObligation:
    schema_version: str
    obligation_id: str
    canonical_ticker: str
    side: Literal["BUY", "SELL"]
    planned_shares: int
    filled_shares: int
    remaining_shares: int
    relinquished_shares: int
    status: str
    created_session_date: str
    latest_attempt_session_date: str | None
    attempt_count: int
    replacement_group_id: str | None
    parent_state_sha256: str | None
    rank_consensus: int | None = None
    event_history: tuple[ObligationEvent, ...] = ()

    def validate(self) -> "QuantityObligation":
        if self.schema_version != QUANTITY_OBLIGATION_SCHEMA:
            raise DecisionV1Error("QUANTITY_OBLIGATION_SCHEMA_INVALID")
        _text(self.obligation_id, "QUANTITY_OBLIGATION_ID_INVALID")
        canonical = canonical_security_identity(self.canonical_ticker)
        if canonical != self.canonical_ticker:
            raise DecisionV1Error("QUANTITY_OBLIGATION_SECURITY_NOT_CANONICAL")
        if self.side not in OBLIGATION_SIDES:
            raise DecisionV1Error("QUANTITY_OBLIGATION_SIDE_INVALID")
        planned = _shares(
            self.planned_shares,
            "QUANTITY_OBLIGATION_PLANNED_INVALID",
            allow_zero=False,
        )
        filled = _shares(self.filled_shares, "QUANTITY_OBLIGATION_FILLED_INVALID")
        remaining = _shares(
            self.remaining_shares,
            "QUANTITY_OBLIGATION_REMAINING_INVALID",
        )
        relinquished = _shares(
            self.relinquished_shares,
            "QUANTITY_OBLIGATION_RELINQUISHED_INVALID",
        )
        if planned != filled + remaining + relinquished:
            raise DecisionV1Error("QUANTITY_OBLIGATION_CONSERVATION_FAILED")
        if self.status not in OBLIGATION_STATUSES:
            raise DecisionV1Error("QUANTITY_OBLIGATION_STATUS_INVALID")
        if remaining and self.status in {"FILLED", "CANCELED", "RELINQUISHED"}:
            raise DecisionV1Error("QUANTITY_OBLIGATION_CLOSED_WITH_REMAINDER")
        if self.status == "FILLED" and (filled != planned or relinquished != 0):
            raise DecisionV1Error("QUANTITY_OBLIGATION_FILLED_STATE_INVALID")
        if self.status in {"CANCELED", "RELINQUISHED"} and remaining != 0:
            raise DecisionV1Error("QUANTITY_OBLIGATION_RELINQUISHED_STATE_INVALID")
        _session(self.created_session_date, "QUANTITY_OBLIGATION_CREATED_DATE_INVALID")
        if self.latest_attempt_session_date is not None:
            _session(
                self.latest_attempt_session_date,
                "QUANTITY_OBLIGATION_ATTEMPT_DATE_INVALID",
            )
        if (
            isinstance(self.attempt_count, bool)
            or not isinstance(self.attempt_count, int)
            or self.attempt_count < 0
        ):
            raise DecisionV1Error("QUANTITY_OBLIGATION_ATTEMPT_COUNT_INVALID")
        if self.replacement_group_id is not None:
            _text(
                self.replacement_group_id,
                "QUANTITY_OBLIGATION_REPLACEMENT_GROUP_INVALID",
            )
        if self.rank_consensus is not None and (
            isinstance(self.rank_consensus, bool)
            or not isinstance(self.rank_consensus, int)
            or self.rank_consensus < 1
        ):
            raise DecisionV1Error("QUANTITY_OBLIGATION_RANK_INVALID")
        if self.parent_state_sha256 is not None:
            parent = _text(
                self.parent_state_sha256,
                "QUANTITY_OBLIGATION_PARENT_HASH_INVALID",
            )
            if len(parent) != 64 or any(c not in "0123456789abcdef" for c in parent.lower()):
                raise DecisionV1Error("QUANTITY_OBLIGATION_PARENT_HASH_INVALID")
        event_ids: set[str] = set()
        for event in self.event_history:
            event.validate()
            if event.event_id in event_ids:
                raise DecisionV1Error("QUANTITY_OBLIGATION_DUPLICATE_EVENT_ID")
            event_ids.add(event.event_id)
        if self.attempt_count != sum(
            event.event_type in {"FILL", "BLOCK", "RETRY"}
            for event in self.event_history
        ):
            raise DecisionV1Error("QUANTITY_OBLIGATION_ATTEMPT_COUNT_MISMATCH")
        return self


def plan_obligation(
    *,
    obligation_id: str,
    ticker: str,
    side: Literal["BUY", "SELL"],
    planned_shares: int,
    session_date: str,
    replacement_group_id: str | None = None,
    parent_state_sha256: str | None = None,
    rank_consensus: int | None = None,
) -> QuantityObligation:
    obligation = QuantityObligation(
        schema_version=QUANTITY_OBLIGATION_SCHEMA,
        obligation_id=_text(obligation_id, "QUANTITY_OBLIGATION_ID_INVALID"),
        canonical_ticker=canonical_security_identity(ticker),
        side=side,
        planned_shares=_shares(
            planned_shares,
            "QUANTITY_OBLIGATION_PLANNED_INVALID",
            allow_zero=False,
        ),
        filled_shares=0,
        remaining_shares=_shares(
            planned_shares,
            "QUANTITY_OBLIGATION_PLANNED_INVALID",
            allow_zero=False,
        ),
        relinquished_shares=0,
        status="PLANNED",
        created_session_date=_session(
            session_date,
            "QUANTITY_OBLIGATION_CREATED_DATE_INVALID",
        ),
        latest_attempt_session_date=None,
        attempt_count=0,
        replacement_group_id=replacement_group_id,
        parent_state_sha256=parent_state_sha256,
        rank_consensus=rank_consensus,
        event_history=(
            ObligationEvent(
                event_id=f"{obligation_id}:PLANNED",
                event_type="PLANNED",
                session_date=session_date,
                reason="PLANNED",
                parent_state_sha256=parent_state_sha256,
            ),
        ),
    )
    return obligation.validate()


def _apply_event(
    obligation: QuantityObligation,
    event: ObligationEvent,
    *,
    next_status: str,
    next_filled: int | None = None,
    next_remaining: int | None = None,
    next_relinquished: int | None = None,
    increment_attempt: bool,
) -> QuantityObligation:
    obligation.validate()
    event.validate()
    for existing in obligation.event_history:
        if existing.event_id == event.event_id:
            if existing != event:
                raise DecisionV1Error("QUANTITY_OBLIGATION_EVENT_CONFLICT")
            return obligation
    updated = replace(
        obligation,
        filled_shares=(
            obligation.filled_shares
            if next_filled is None
            else next_filled
        ),
        remaining_shares=(
            obligation.remaining_shares
            if next_remaining is None
            else next_remaining
        ),
        relinquished_shares=(
            obligation.relinquished_shares
            if next_relinquished is None
            else next_relinquished
        ),
        status=next_status,
        latest_attempt_session_date=(
            event.session_date
            if increment_attempt
            else obligation.latest_attempt_session_date
        ),
        attempt_count=(
            obligation.attempt_count + 1
            if increment_attempt
            else obligation.attempt_count
        ),
        event_history=(*obligation.event_history, event),
    )
    return updated.validate()


def apply_fill(
    obligation: QuantityObligation,
    *,
    event_id: str,
    session_date: str,
    filled_shares: int,
    reason: str,
    parent_state_sha256: str | None = None,
) -> QuantityObligation:
    filled = _shares(
        filled_shares,
        "QUANTITY_OBLIGATION_FILL_INVALID",
        allow_zero=False,
    )
    event = ObligationEvent(
        event_id=_text(event_id, "QUANTITY_OBLIGATION_EVENT_ID_INVALID"),
        event_type="FILL",
        session_date=session_date,
        filled_delta_shares=filled,
        reason=_text(reason, "QUANTITY_OBLIGATION_REASON_INVALID"),
        parent_state_sha256=parent_state_sha256,
    )
    for existing in obligation.event_history:
        if existing.event_id == event.event_id:
            if existing != event:
                raise DecisionV1Error("QUANTITY_OBLIGATION_EVENT_CONFLICT")
            return obligation
    if filled > obligation.remaining_shares:
        raise DecisionV1Error("QUANTITY_OBLIGATION_FILL_EXCEEDS_REMAINING")
    next_filled = obligation.filled_shares + filled
    next_remaining = obligation.remaining_shares - filled
    return _apply_event(
        obligation,
        event,
        next_status="FILLED" if next_remaining == 0 else "PARTIAL",
        next_filled=next_filled,
        next_remaining=next_remaining,
        increment_attempt=True,
    )


def mark_blocked(
    obligation: QuantityObligation,
    *,
    event_id: str,
    session_date: str,
    reason: str,
    parent_state_sha256: str | None = None,
) -> QuantityObligation:
    return _apply_event(
        obligation,
        ObligationEvent(
            event_id=_text(event_id, "QUANTITY_OBLIGATION_EVENT_ID_INVALID"),
            event_type="BLOCK",
            session_date=session_date,
            reason=_text(reason, "QUANTITY_OBLIGATION_REASON_INVALID"),
            parent_state_sha256=parent_state_sha256,
        ),
        next_status="BLOCKED",
        increment_attempt=True,
    )


def mark_retry(
    obligation: QuantityObligation,
    *,
    event_id: str,
    session_date: str,
    reason: str,
    parent_state_sha256: str | None = None,
) -> QuantityObligation:
    return _apply_event(
        obligation,
        ObligationEvent(
            event_id=_text(event_id, "QUANTITY_OBLIGATION_EVENT_ID_INVALID"),
            event_type="RETRY",
            session_date=session_date,
            reason=_text(reason, "QUANTITY_OBLIGATION_REASON_INVALID"),
            parent_state_sha256=parent_state_sha256,
        ),
        next_status="PARTIAL" if obligation.filled_shares else "PLANNED",
        increment_attempt=True,
    )


def cancel_remaining(
    obligation: QuantityObligation,
    *,
    event_id: str,
    session_date: str,
    reason: str,
    parent_state_sha256: str | None = None,
    status: Literal["CANCELED", "RELINQUISHED"] = "CANCELED",
    seat_policy: DecisionSeatClosePolicyV1 | None = None,
) -> QuantityObligation:
    policy_sha256 = authorize_decision_seat_close(
        seat_policy,
        status=status,
        reason=reason,
    )
    policy_payload = seat_policy.payload() if seat_policy is not None else None
    event_type = "RELINQUISH" if status == "RELINQUISHED" else "CANCEL"
    event_id_text = _text(event_id, "QUANTITY_OBLIGATION_EVENT_ID_INVALID")
    reason_text = _text(reason, "QUANTITY_OBLIGATION_REASON_INVALID")
    for existing in obligation.event_history:
        if existing.event_id == event_id_text:
            if (
                existing.event_type != event_type
                or existing.session_date != session_date
                or existing.reason != reason_text
                or existing.parent_state_sha256 != parent_state_sha256
                or existing.policy_sha256 != policy_sha256
                or existing.policy_payload != policy_payload
            ):
                raise DecisionV1Error("QUANTITY_OBLIGATION_EVENT_CONFLICT")
            return obligation
    remaining = obligation.remaining_shares
    if remaining <= 0:
        # A duplicate cancellation is idempotent only through the event ID;
        # a new close event with no quantity would create ambiguous lineage.
        raise DecisionV1Error("QUANTITY_OBLIGATION_NO_REMAINING_TO_CANCEL")
    return _apply_event(
        obligation,
        ObligationEvent(
            event_id=event_id_text,
            event_type=event_type,
            session_date=session_date,
            relinquished_delta_shares=remaining,
            reason=reason_text,
            parent_state_sha256=parent_state_sha256,
            policy_sha256=policy_sha256,
            policy_payload=policy_payload,
        ),
        next_status=status,
        next_remaining=0,
        next_relinquished=obligation.relinquished_shares + remaining,
        increment_attempt=False,
    )


def obligation_payload(obligation: QuantityObligation) -> dict[str, Any]:
    obligation.validate()
    return {
        "schema_version": obligation.schema_version,
        "obligation_id": obligation.obligation_id,
        "canonical_ticker": obligation.canonical_ticker,
        "side": obligation.side,
        "planned_shares": obligation.planned_shares,
        "filled_shares": obligation.filled_shares,
        "remaining_shares": obligation.remaining_shares,
        "relinquished_shares": obligation.relinquished_shares,
        "status": obligation.status,
        "created_session_date": obligation.created_session_date,
        "latest_attempt_session_date": obligation.latest_attempt_session_date,
        "attempt_count": obligation.attempt_count,
        "replacement_group_id": obligation.replacement_group_id,
        "parent_state_sha256": obligation.parent_state_sha256,
        "rank_consensus": obligation.rank_consensus,
        "event_history": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "session_date": event.session_date,
                "filled_delta_shares": event.filled_delta_shares,
                "relinquished_delta_shares": event.relinquished_delta_shares,
                "reason": event.reason,
                "parent_state_sha256": event.parent_state_sha256,
                **(
                    {"policy_sha256": event.policy_sha256}
                    if event.policy_sha256 is not None
                    else {}
                ),
                **(
                    {"policy_payload": deepcopy(event.policy_payload)}
                    if event.policy_payload is not None
                    else {}
                ),
            }
            for event in obligation.event_history
        ],
    }


def _event_from_payload(value: object) -> ObligationEvent:
    if not isinstance(value, dict):
        raise DecisionV1Error("QUANTITY_OBLIGATION_EVENT_PAYLOAD_INVALID")
    event = ObligationEvent(
        event_id=str(value.get("event_id") or ""),
        event_type=str(value.get("event_type") or ""),  # type: ignore[arg-type]
        session_date=str(value.get("session_date") or ""),
        filled_delta_shares=value.get("filled_delta_shares", 0),
        relinquished_delta_shares=value.get("relinquished_delta_shares", 0),
        reason=str(value.get("reason") or ""),
        parent_state_sha256=value.get("parent_state_sha256"),
        policy_sha256=value.get("policy_sha256"),
        policy_payload=value.get("policy_payload"),
    )
    return event.validate()


def obligation_from_payload(value: object) -> QuantityObligation:
    if not isinstance(value, dict):
        raise DecisionV1Error("QUANTITY_OBLIGATION_PAYLOAD_INVALID")
    history_raw = value.get("event_history", [])
    if not isinstance(history_raw, list):
        raise DecisionV1Error("QUANTITY_OBLIGATION_EVENT_HISTORY_INVALID")
    obligation = QuantityObligation(
        schema_version=str(value.get("schema_version") or ""),
        obligation_id=str(value.get("obligation_id") or ""),
        canonical_ticker=str(value.get("canonical_ticker") or ""),
        side=str(value.get("side") or ""),  # type: ignore[arg-type]
        planned_shares=value.get("planned_shares", -1),
        filled_shares=value.get("filled_shares", -1),
        remaining_shares=value.get("remaining_shares", -1),
        relinquished_shares=value.get("relinquished_shares", -1),
        status=str(value.get("status") or ""),
        created_session_date=str(value.get("created_session_date") or ""),
        latest_attempt_session_date=value.get("latest_attempt_session_date"),
        attempt_count=value.get("attempt_count", -1),
        replacement_group_id=value.get("replacement_group_id"),
        parent_state_sha256=value.get("parent_state_sha256"),
        rank_consensus=value.get("rank_consensus"),
        event_history=tuple(_event_from_payload(row) for row in history_raw),
    )
    normalized = obligation.validate()
    if obligation_payload(normalized) != value:
        raise DecisionV1Error("QUANTITY_OBLIGATION_PAYLOAD_NOT_CANONICAL")
    return normalized


def obligation_hash(obligation: QuantityObligation) -> str:
    encoded = (
        json.dumps(obligation_payload(obligation), sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_obligations(
    obligations: tuple[QuantityObligation, ...] | list[QuantityObligation],
) -> tuple[QuantityObligation, ...]:
    by_id: dict[str, QuantityObligation] = {}
    for obligation in obligations:
        obligation.validate()
        if obligation.obligation_id in by_id:
            raise DecisionV1Error("QUANTITY_OBLIGATION_DUPLICATE_ID")
        by_id[obligation.obligation_id] = obligation
    return tuple(by_id[key] for key in sorted(by_id))


def obligations_payload(
    obligations: tuple[QuantityObligation, ...] | list[QuantityObligation],
) -> list[dict[str, Any]]:
    return [obligation_payload(row) for row in normalize_obligations(obligations)]


def obligations_hash(
    obligations: tuple[QuantityObligation, ...] | list[QuantityObligation],
) -> str:
    encoded = (
        json.dumps(obligations_payload(obligations), sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "QUANTITY_OBLIGATION_SCHEMA",
    "LOT_SIZE_SHARES",
    "ObligationEvent",
    "QuantityObligation",
    "canonical_security_identity",
    "plan_obligation",
    "apply_fill",
    "mark_blocked",
    "mark_retry",
    "cancel_remaining",
    "obligation_payload",
    "obligation_from_payload",
    "obligation_hash",
    "normalize_obligations",
    "obligations_payload",
    "obligations_hash",
]
