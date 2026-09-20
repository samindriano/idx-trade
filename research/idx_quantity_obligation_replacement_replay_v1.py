"""Synthetic SELL/replacement replay harness for the obligation design.

This is research-only code. It intentionally does not import or mutate the
production execution state.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from typing import Any

from research.idx_quantity_obligation_replay_harness_v1 import (
    LOT_SIZE,
    ObligationContractError,
    QuantityObligation,
    plan_obligation,
)


@dataclass(frozen=True)
class ReplacementReplayState:
    session_date: str
    cash_idr: float
    initial_positions: tuple[tuple[str, int], ...]
    positions: tuple[tuple[str, int], ...]
    obligations: tuple[QuantityObligation, ...]

    def validate(self) -> "ReplacementReplayState":
        initial = dict(self.initial_positions)
        actual = dict(self.positions)
        if any(value < 0 or value % LOT_SIZE for value in (*initial.values(), *actual.values())):
            raise ObligationContractError("POSITION_NOT_WHOLE_LOT")
        if self.cash_idr < 0:
            raise ObligationContractError("CASH_NEGATIVE")
        if len({row.obligation_id for row in self.obligations}) != len(self.obligations):
            raise ObligationContractError("DUPLICATE_OBLIGATION_ID")
        expected = dict(initial)
        for obligation in self.obligations:
            obligation.validate()
            sign = 1 if obligation.side == "BUY" else -1
            expected[obligation.canonical_ticker] = (
                expected.get(obligation.canonical_ticker, 0)
                + sign * obligation.filled_shares
            )
        expected = {ticker: shares for ticker, shares in expected.items() if shares}
        if actual != expected:
            raise ObligationContractError(
                f"POSITION_OBLIGATION_MISMATCH:{actual}!={expected}"
            )
        return self


def _replace(state: ReplacementReplayState, updated: QuantityObligation) -> ReplacementReplayState:
    return replace(
        state,
        obligations=tuple(
            updated if row.obligation_id == updated.obligation_id else row
            for row in state.obligations
        ),
    )


def _position_delta(state: ReplacementReplayState, ticker: str, delta: int) -> ReplacementReplayState:
    positions = dict(state.positions)
    positions[ticker] = positions.get(ticker, 0) + delta
    if positions[ticker] < 0:
        raise ObligationContractError("POSITION_NEGATIVE")
    if positions[ticker] == 0:
        del positions[ticker]
    return replace(state, positions=tuple(sorted(positions.items())))


def _find(state: ReplacementReplayState, obligation_id: str) -> QuantityObligation:
    for row in state.obligations:
        if row.obligation_id == obligation_id:
            return row
    raise ObligationContractError("OBLIGATION_NOT_FOUND")


def apply_fill(
    state: ReplacementReplayState, *, obligation_id: str, event_id: str,
    session_date: str, filled_shares: int, reason: str,
) -> ReplacementReplayState:
    row = _find(state, obligation_id)
    if event_id in row.applied_event_ids:
        return state.validate()
    if filled_shares <= 0 or filled_shares % LOT_SIZE:
        raise ObligationContractError("FILL_NOT_WHOLE_LOT")
    if filled_shares > row.remaining_shares:
        raise ObligationContractError("FILL_EXCEEDS_REMAINING")
    remaining = row.remaining_shares - filled_shares
    updated = replace(
        row,
        filled_shares=row.filled_shares + filled_shares,
        remaining_shares=remaining,
        status="FILLED" if remaining == 0 else "PARTIAL",
        last_attempt_session_date=session_date,
        attempt_count=row.attempt_count + 1,
        last_reason=reason,
        applied_event_ids=(*row.applied_event_ids, event_id),
    )
    sign = 1 if row.side == "BUY" else -1
    return _position_delta(_replace(state, updated), row.canonical_ticker, sign * filled_shares).validate()


def record_blocked(
    state: ReplacementReplayState, *, obligation_id: str, event_id: str,
    session_date: str, reason: str,
) -> ReplacementReplayState:
    row = _find(state, obligation_id)
    if event_id in row.applied_event_ids:
        return state.validate()
    if row.remaining_shares == 0:
        raise ObligationContractError("BLOCKED_FILLED_OBLIGATION")
    updated = replace(
        row,
        status="BLOCKED",
        last_attempt_session_date=session_date,
        attempt_count=row.attempt_count + 1,
        last_reason=reason,
        applied_event_ids=(*row.applied_event_ids, event_id),
    )
    return _replace(state, updated).validate()


def cancel_remaining(
    state: ReplacementReplayState, *, obligation_id: str, event_id: str,
    session_date: str, reason: str,
) -> ReplacementReplayState:
    row = _find(state, obligation_id)
    if event_id in row.applied_event_ids:
        return state.validate()
    updated = replace(
        row,
        remaining_shares=0,
        relinquished_shares=row.relinquished_shares + row.remaining_shares,
        status="CANCELED",
        last_attempt_session_date=session_date,
        last_reason=reason,
        applied_event_ids=(*row.applied_event_ids, event_id),
    )
    return _replace(state, updated).validate()


def payload(state: ReplacementReplayState) -> dict[str, Any]:
    return {
        "session_date": state.session_date,
        "cash_idr": round(state.cash_idr, 6),
        "initial_positions": list(state.initial_positions),
        "positions": list(state.positions),
        "obligations": [
            {
                "obligation_id": row.obligation_id,
                "canonical_ticker": row.canonical_ticker,
                "side": row.side,
                "planned_shares": row.planned_shares,
                "filled_shares": row.filled_shares,
                "remaining_shares": row.remaining_shares,
                "relinquished_shares": row.relinquished_shares,
                "status": row.status,
                "created_session_date": row.created_session_date,
                "last_attempt_session_date": row.last_attempt_session_date,
                "attempt_count": row.attempt_count,
                "last_reason": row.last_reason,
                "replacement_group_id": row.replacement_group_id,
                "applied_event_ids": list(row.applied_event_ids),
            }
            for row in state.obligations
        ],
    }


def from_payload(raw: dict[str, Any]) -> ReplacementReplayState:
    obligations = tuple(
        QuantityObligation(
            obligation_id=row["obligation_id"],
            canonical_ticker=row["canonical_ticker"],
            side=row["side"],
            planned_shares=int(row["planned_shares"]),
            filled_shares=int(row["filled_shares"]),
            remaining_shares=int(row["remaining_shares"]),
            relinquished_shares=int(row["relinquished_shares"]),
            status=row["status"],
            created_session_date=row["created_session_date"],
            last_attempt_session_date=row["last_attempt_session_date"],
            attempt_count=int(row["attempt_count"]),
            last_reason=row["last_reason"],
            replacement_group_id=row["replacement_group_id"],
            applied_event_ids=tuple(row["applied_event_ids"]),
        )
        for row in raw["obligations"]
    )
    return ReplacementReplayState(
        session_date=raw["session_date"],
        cash_idr=float(raw["cash_idr"]),
        initial_positions=tuple((str(t), int(s)) for t, s in raw["initial_positions"]),
        positions=tuple((str(t), int(s)) for t, s in raw["positions"]),
        obligations=obligations,
    ).validate()


def state_hash(state: ReplacementReplayState) -> str:
    state.validate()
    encoded = (json.dumps(payload(state), sort_keys=True) + "\n").encode()
    return hashlib.sha256(encoded).hexdigest()


def run_replacement_scenario() -> dict[str, Any]:
    sell = plan_obligation(
        obligation_id="SELL-AAA-2026-08-21-01", ticker="AAA", side="SELL",
        planned_shares=5_000, session_date="2026-08-21",
        replacement_group_id="REPLACE-AAA-BBB-01",
    )
    buy = plan_obligation(
        obligation_id="BUY-BBB-2026-08-21-01", ticker="BBB", side="BUY",
        planned_shares=5_000, session_date="2026-08-21",
        replacement_group_id="REPLACE-AAA-BBB-01",
    )
    state = ReplacementReplayState(
        session_date="2026-08-21", cash_idr=45_000_000.0,
        initial_positions=(("AAA", 5_000),),
        positions=(("AAA", 5_000),), obligations=(sell, buy),
    ).validate()
    state = apply_fill(
        state, obligation_id=sell.obligation_id, event_id="SELL-FILL-1",
        session_date="2026-08-24", filled_shares=1_000,
        reason="PARTIAL_EXIT_CAPACITY",
    )
    state = record_blocked(
        state, obligation_id=buy.obligation_id, event_id="BUY-BLOCK-1",
        session_date="2026-08-24", reason="BLOCKED_BY_UNRESOLVED_PAIRED_SELL",
    )
    first_hash = state_hash(state)
    reloaded = from_payload(json.loads(json.dumps(payload(state))))
    reload_hash = state_hash(reloaded)
    state = apply_fill(
        reloaded, obligation_id=sell.obligation_id, event_id="SELL-FILL-2",
        session_date="2026-08-25", filled_shares=1_000,
        reason="RETRY_CAPACITY_PARTIAL",
    )
    state = record_blocked(
        state, obligation_id=buy.obligation_id, event_id="BUY-BLOCK-2",
        session_date="2026-08-25", reason="BLOCKED_BY_UNRESOLVED_PAIRED_SELL",
    )
    state = cancel_remaining(
        state, obligation_id=sell.obligation_id, event_id="SELL-CANCEL-1",
        session_date="2026-08-26", reason="CANCELED_BY_TARGET_REVERSAL",
    )
    state = cancel_remaining(
        state, obligation_id=buy.obligation_id, event_id="BUY-CANCEL-1",
        session_date="2026-08-26", reason="CANCELED_BY_TARGET_REVERSAL",
    )
    replayed = cancel_remaining(
        state, obligation_id=buy.obligation_id, event_id="BUY-CANCEL-1",
        session_date="2026-08-26", reason="DUPLICATE_CANCEL_REPLAY",
    )
    rows = {row.obligation_id: row for row in state.obligations}
    return {
        "first_partial": {
            "positions": list(from_payload(json.loads(json.dumps(payload(reloaded)))).positions),
            "sell_filled": 1_000,
            "sell_remaining": 4_000,
            "buy_status": "BLOCKED",
            "reload_hash_equal": first_hash == reload_hash,
        },
        "after_retry": {
            "positions": list(state.positions),
            "sell_filled": 2_000,
            "sell_remaining_before_cancel": 3_000,
            "buy_filled": 0,
        },
        "after_reversal": {
            "positions": list(state.positions),
            "sell_relinquished": rows[sell.obligation_id].relinquished_shares,
            "buy_relinquished": rows[buy.obligation_id].relinquished_shares,
            "sell_status": rows[sell.obligation_id].status,
            "buy_status": rows[buy.obligation_id].status,
            "event_ids": sorted({event for row in rows.values() for event in row.applied_event_ids}),
            "duplicate_cancel_idempotent": replayed == state,
        },
        "final_hash": state_hash(state),
    }


if __name__ == "__main__":
    print(json.dumps(run_replacement_scenario(), indent=2, sort_keys=True))
