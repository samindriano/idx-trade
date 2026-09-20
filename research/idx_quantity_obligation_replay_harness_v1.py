"""Outcome-blind spec harness for the proposed quantity-obligation contract.

This module is deliberately not imported by production runtime code. It tests
the state invariants proposed in the 2026-09-20 quantity-obligation checkpoint
using only in-memory synthetic state.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from typing import Any


LOT_SIZE = 100


class ObligationContractError(ValueError):
    """Raised when the synthetic contract invariant is violated."""


@dataclass(frozen=True)
class QuantityObligation:
    obligation_id: str
    canonical_ticker: str
    side: str
    planned_shares: int
    filled_shares: int = 0
    remaining_shares: int = 0
    relinquished_shares: int = 0
    status: str = "PLANNED"
    created_session_date: str = ""
    last_attempt_session_date: str | None = None
    attempt_count: int = 0
    last_reason: str = ""
    replacement_group_id: str | None = None
    applied_event_ids: tuple[str, ...] = ()

    def validate(self) -> "QuantityObligation":
        if self.side not in {"BUY", "SELL"}:
            raise ObligationContractError("SIDE_INVALID")
        quantities = (
            self.planned_shares,
            self.filled_shares,
            self.remaining_shares,
            self.relinquished_shares,
        )
        if any(value < 0 or value % LOT_SIZE for value in quantities):
            raise ObligationContractError("QUANTITY_NOT_WHOLE_LOT")
        if self.planned_shares != (
            self.filled_shares
            + self.remaining_shares
            + self.relinquished_shares
        ):
            raise ObligationContractError("QUANTITY_CONSERVATION_FAILED")
        if self.status == "FILLED" and self.remaining_shares != 0:
            raise ObligationContractError("FILLED_WITH_REMAINDER")
        if self.status in {"CANCELED", "EXPIRED"} and self.remaining_shares != 0:
            raise ObligationContractError("CLOSED_WITH_REMAINDER")
        return self


@dataclass(frozen=True)
class ReplayState:
    session_date: str
    cash_idr: float
    position_shares: int
    obligation: QuantityObligation
    settled_event_ids: tuple[str, ...] = ()

    def validate(self) -> "ReplayState":
        if self.cash_idr < 0 or self.position_shares < 0:
            raise ObligationContractError("PORTFOLIO_QUANTITY_INVALID")
        self.obligation.validate()
        if self.obligation.side == "BUY":
            expected_position = self.obligation.filled_shares
            if self.position_shares != expected_position:
                raise ObligationContractError("POSITION_FILL_RECONCILIATION_FAILED")
        return self


def plan_obligation(
    *, obligation_id: str, ticker: str, side: str, planned_shares: int,
    session_date: str, replacement_group_id: str | None = None,
) -> QuantityObligation:
    return QuantityObligation(
        obligation_id=obligation_id,
        canonical_ticker=ticker,
        side=side,
        planned_shares=planned_shares,
        remaining_shares=planned_shares,
        status="PLANNED",
        created_session_date=session_date,
        replacement_group_id=replacement_group_id,
    ).validate()


def apply_fill(
    state: ReplayState, *, event_id: str, session_date: str,
    filled_shares: int, reason: str,
) -> ReplayState:
    if event_id in state.obligation.applied_event_ids:
        return state.validate()
    if filled_shares <= 0 or filled_shares % LOT_SIZE:
        raise ObligationContractError("FILL_NOT_WHOLE_LOT")
    obligation = state.obligation
    if filled_shares > obligation.remaining_shares:
        raise ObligationContractError("FILL_EXCEEDS_REMAINING")
    next_filled = obligation.filled_shares + filled_shares
    next_remaining = obligation.remaining_shares - filled_shares
    next_status = "FILLED" if next_remaining == 0 else "PARTIAL"
    updated = replace(
        obligation,
        filled_shares=next_filled,
        remaining_shares=next_remaining,
        status=next_status,
        last_attempt_session_date=session_date,
        attempt_count=obligation.attempt_count + 1,
        last_reason=reason,
        applied_event_ids=(*obligation.applied_event_ids, event_id),
    )
    position_delta = filled_shares if obligation.side == "BUY" else -filled_shares
    return replace(
        state,
        session_date=session_date,
        position_shares=state.position_shares + position_delta,
        obligation=updated,
    ).validate()


def cancel_remaining(
    state: ReplayState, *, event_id: str, session_date: str, reason: str,
) -> ReplayState:
    if event_id in state.obligation.applied_event_ids:
        return state.validate()
    obligation = state.obligation
    canceled = obligation.remaining_shares
    updated = replace(
        obligation,
        remaining_shares=0,
        relinquished_shares=obligation.relinquished_shares + canceled,
        status="CANCELED",
        last_attempt_session_date=session_date,
        last_reason=reason,
        applied_event_ids=(*obligation.applied_event_ids, event_id),
    )
    return replace(
        state,
        session_date=session_date,
        obligation=updated,
    ).validate()


def settle_dividend(
    state: ReplayState, *, event_id: str, entitled_shares: int,
    dividend_per_share_idr: float, session_date: str,
) -> ReplayState:
    if event_id in state.settled_event_ids:
        return state.validate()
    if entitled_shares < 0 or entitled_shares % LOT_SIZE:
        raise ObligationContractError("ENTITLEMENT_NOT_WHOLE_LOT")
    amount = entitled_shares * dividend_per_share_idr
    return replace(
        state,
        session_date=session_date,
        cash_idr=state.cash_idr + amount,
        settled_event_ids=(*state.settled_event_ids, event_id),
    ).validate()


def legacy_quantity_classification(
    *, planned_shares: int | None, filled_shares: int,
) -> str:
    if planned_shares is None and filled_shares > 0:
        return "UNKNOWN_ORPHANED_PARTIAL"
    if planned_shares is not None and planned_shares == filled_shares:
        return "COMPLETE_HISTORICAL_FILL"
    if planned_shares is not None and filled_shares == 0:
        return "EXPLICIT_ZERO_LOT_PENDING"
    return "REQUIRES_RECONCILIATION"


def canonical_payload(state: ReplayState) -> dict[str, Any]:
    return {
        "session_date": state.session_date,
        "cash_idr": round(state.cash_idr, 6),
        "position_shares": state.position_shares,
        "obligation": {
            "obligation_id": state.obligation.obligation_id,
            "canonical_ticker": state.obligation.canonical_ticker,
            "side": state.obligation.side,
            "planned_shares": state.obligation.planned_shares,
            "filled_shares": state.obligation.filled_shares,
            "remaining_shares": state.obligation.remaining_shares,
            "relinquished_shares": state.obligation.relinquished_shares,
            "status": state.obligation.status,
            "created_session_date": state.obligation.created_session_date,
            "last_attempt_session_date": state.obligation.last_attempt_session_date,
            "attempt_count": state.obligation.attempt_count,
            "last_reason": state.obligation.last_reason,
            "replacement_group_id": state.obligation.replacement_group_id,
            "applied_event_ids": list(state.obligation.applied_event_ids),
        },
        "settled_event_ids": list(state.settled_event_ids),
    }


def state_from_payload(payload: dict[str, Any]) -> ReplayState:
    """Reconstruct a spec state from its canonical JSON-compatible payload."""
    obligation_payload = payload["obligation"]
    obligation = QuantityObligation(
        obligation_id=str(obligation_payload["obligation_id"]),
        canonical_ticker=str(obligation_payload["canonical_ticker"]),
        side=str(obligation_payload["side"]),
        planned_shares=int(obligation_payload["planned_shares"]),
        filled_shares=int(obligation_payload["filled_shares"]),
        remaining_shares=int(obligation_payload["remaining_shares"]),
        relinquished_shares=int(obligation_payload["relinquished_shares"]),
        status=str(obligation_payload["status"]),
        created_session_date=str(obligation_payload["created_session_date"]),
        last_attempt_session_date=obligation_payload["last_attempt_session_date"],
        attempt_count=int(obligation_payload["attempt_count"]),
        last_reason=str(obligation_payload["last_reason"]),
        replacement_group_id=obligation_payload["replacement_group_id"],
        applied_event_ids=tuple(obligation_payload["applied_event_ids"]),
    )
    return ReplayState(
        session_date=str(payload["session_date"]),
        cash_idr=float(payload["cash_idr"]),
        position_shares=int(payload["position_shares"]),
        obligation=obligation,
        settled_event_ids=tuple(payload["settled_event_ids"]),
    ).validate()


def state_hash(state: ReplayState) -> str:
    state.validate()
    encoded = (json.dumps(canonical_payload(state), sort_keys=True) + "\n").encode()
    return hashlib.sha256(encoded).hexdigest()


def run_spec_scenario() -> dict[str, Any]:
    state = ReplayState(
        session_date="2026-08-21",
        cash_idr=45_000_000.0,
        position_shares=0,
        obligation=plan_obligation(
            obligation_id="BUY-BBCA-2026-08-21-01",
            ticker="BBCA",
            side="BUY",
            planned_shares=5_000,
            session_date="2026-08-21",
            replacement_group_id="REPLACE-AAA-BBCA-01",
        ),
    )
    state = apply_fill(
        state, event_id="FILL-1", session_date="2026-08-24",
        filled_shares=2_400, reason="OPEN_CAPACITY_PARTIAL",
    )
    after_first_fill_hash = state_hash(state)

    # A cold reload is represented by canonical serialization/deserialization
    # through JSON. Re-applying the same event must be idempotent.
    reloaded_payload = json.loads(json.dumps(canonical_payload(state)))
    reloaded_state = state_from_payload(reloaded_payload)
    reloaded_hash_before = state_hash(reloaded_state)
    duplicate = apply_fill(
        reloaded_state, event_id="FILL-1", session_date="2026-08-24",
        filled_shares=2_400, reason="DUPLICATE_REPLAY",
    )
    duplicate_hash = state_hash(duplicate)

    state = apply_fill(
        duplicate, event_id="FILL-2", session_date="2026-08-25",
        filled_shares=1_000, reason="RETRY_CAPACITY_PARTIAL",
    )
    actual_at_cum = state.position_shares
    state = settle_dividend(
        state, event_id="DIV-1", entitled_shares=actual_at_cum,
        dividend_per_share_idr=25.0, session_date="2026-08-26",
    )
    payment_hash = state_hash(state)
    state = cancel_remaining(
        state, event_id="CANCEL-1", session_date="2026-08-27",
        reason="CANCELED_BY_TARGET_REVERSAL",
    )
    canceled_hash = state_hash(state)
    replayed_cancel = cancel_remaining(
        state, event_id="CANCEL-1", session_date="2026-08-27",
        reason="DUPLICATE_CANCEL_REPLAY",
    )

    result = {
        "initial_planned_shares": 5_000,
        "after_first_fill": {
            "filled": 2_400,
            "remaining": 2_600,
            "status": "PARTIAL",
            "hash": after_first_fill_hash,
        },
        "duplicate_fill_idempotent": duplicate_hash == reloaded_hash_before,
        "after_retry": {
            "filled": 3_400,
            "remaining": 1_600,
            "attempt_count": 2,
        },
        "ca_entitlement_shares": actual_at_cum,
        "ca_payment_idr": actual_at_cum * 25.0,
        "cash_after_payment_idr": state.cash_idr,
        "payment_hash": payment_hash,
        "after_reversal": {
            "status": state.obligation.status,
            "filled": state.obligation.filled_shares,
            "remaining": state.obligation.remaining_shares,
            "relinquished": state.obligation.relinquished_shares,
            "hash": canceled_hash,
        },
        "duplicate_cancel_idempotent": replayed_cancel == state,
        "legacy_positive_partial_without_plan": legacy_quantity_classification(
            planned_shares=None, filled_shares=2_400,
        ),
        "reloaded_payload_keys": sorted(reloaded_payload),
        "final_state": canonical_payload(state),
    }
    if not result["duplicate_fill_idempotent"]:
        raise ObligationContractError("DUPLICATE_FILL_NOT_IDEMPOTENT")
    if not result["duplicate_cancel_idempotent"]:
        raise ObligationContractError("DUPLICATE_CANCEL_NOT_IDEMPOTENT")
    state.validate()
    return result


if __name__ == "__main__":
    print(json.dumps(run_spec_scenario(), indent=2, sort_keys=True))
