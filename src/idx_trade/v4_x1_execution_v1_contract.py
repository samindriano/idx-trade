from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from numbers import Integral
from typing import Literal

from .v4_x1_decision_v1_contract import DecisionV1Error, TradeIntent
from .v4_x1_decision_seat_policy_v1 import DecisionSeatClosePolicyV1
from .v4_x1_sizing_v1 import SizingPlan
from .v4_x1_quantity_obligation_v1 import (
    QuantityObligation,
    cancel_remaining,
    normalize_obligations,
    obligations_payload,
)

EXECUTION_RULE_ID = "V4_X1_EXECUTION_V1"
PAPER_STATE_SOURCE = "EXECUTABLE_PAPER_V1"
LEGACY_POSITION_ONLY = "LEGACY_POSITION_ONLY"
UNKNOWN_ORPHANED_PARTIAL = "UNKNOWN_ORPHANED_PARTIAL"
OBLIGATION_V1_STATE = "OBLIGATION_V1"
LOT_SIZE_SHARES = 100
BUY_FEE_BPS = 15.0
SELL_FEE_BPS = 25.0
SLIPPAGE_BPS = 10.0
STAMP_DUTY_IDR = 10_000.0
STAMP_DUTY_THRESHOLD_IDR = 10_000_000.0
MAX_ENTRY_WEIGHT = 0.15
MAX_ORDER_NOTIONAL_SHARE_REFERENCE_VALUE = 0.01
_EXECUTION_PLAN_TOKEN = object()


@dataclass(frozen=True)
class PaperPosition:
    ticker: str
    shares: int


@dataclass(frozen=True)
class PendingPaperIntent:
    side: Literal["BUY", "SELL"]
    ticker: str
    rank_consensus: int | None
    reason: str
    replacement_peer: str | None = None


@dataclass(frozen=True)
class PaperPortfolioState:
    as_of_session_date: str
    cash_idr: float
    positions: tuple[PaperPosition, ...]
    pending_buys: tuple[PendingPaperIntent, ...] = ()
    pending_sells: tuple[PendingPaperIntent, ...] = ()
    reconciliation_required: bool = False
    source: str = PAPER_STATE_SOURCE
    obligations: tuple[QuantityObligation, ...] = ()


@dataclass(frozen=True)
class PlannedSell:
    ticker: str
    shares: int
    rank_consensus: int | None
    reason: str
    replacement_peer: str | None


@dataclass(frozen=True)
class ExecutionOrderPlan:
    decision_session_date: str
    execution_session_date: str
    state_hash: str
    eod_nav_idr: float
    projected_cash_for_sizing_idr: float
    sizing_plan: SizingPlan
    sells: tuple[PlannedSell, ...]
    effective_buy_intents: tuple[TradeIntent, ...]
    target_positions: tuple[str, ...]
    regular_market_values_t: dict[str, float]
    eod_ohlcv_sha256: str
    eod_model_input_sha256: str
    official_calendar_sha256: str
    rule_id: str = EXECUTION_RULE_ID
    _verification_token: object | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class FillRecord:
    side: str
    ticker: str
    planned_shares: int
    filled_shares: int
    raw_open: float | None
    effective_price: float | None
    gross_notional: float
    fee_idr: float
    cash_effect_idr: float
    status: str
    replacement_peer: str | None = None


@dataclass(frozen=True)
class ExecutionResult:
    execution_session_date: str
    state_before_hash: str
    state_after: PaperPortfolioState
    fills: tuple[FillRecord, ...]
    stamp_duty_idr: float
    gross_turnover_idr: float
    pending_transition_count: int
    reconciliation_required: bool
    rule_id: str = EXECUTION_RULE_ID


def ticker(value: object) -> str:
    value = str(value).upper().replace(".JK", "").strip()
    if not value:
        raise DecisionV1Error("EXECUTION_V1_EMPTY_TICKER")
    return value


def finite_nonnegative(value: object, code: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(code) from exc
    if not math.isfinite(x) or x < 0:
        raise DecisionV1Error(code)
    return x


def whole_lot_shares(value: object, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise DecisionV1Error(code)
    shares = int(value)
    if shares <= 0 or shares % LOT_SIZE_SHARES:
        raise DecisionV1Error(code)
    return shares


def rank_consensus_value(value: object, code: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise DecisionV1Error(code)
    rank = int(value)
    if rank <= 0:
        raise DecisionV1Error(code)
    return rank


def normalize_pending(rows: tuple[PendingPaperIntent, ...], side: str) -> dict[str, PendingPaperIntent]:
    out: dict[str, PendingPaperIntent] = {}
    for row in rows:
        if row.side != side:
            raise DecisionV1Error("EXECUTION_V1_PENDING_SIDE_MISMATCH")
        symbol = ticker(row.ticker)
        if symbol in out:
            raise DecisionV1Error("EXECUTION_V1_DUPLICATE_PENDING_INTENT")
        out[symbol] = PendingPaperIntent(
            side=side,
            ticker=symbol,
            rank_consensus=rank_consensus_value(
                row.rank_consensus,
                "EXECUTION_V1_PENDING_RANK_INVALID",
            ),
            reason=row.reason,
            replacement_peer=row.replacement_peer,
        )
    return out


def pending_intents_from_obligations(
    obligations: tuple[QuantityObligation, ...] | list[QuantityObligation],
) -> tuple[tuple[PendingPaperIntent, ...], tuple[PendingPaperIntent, ...]]:
    """Project only unfulfilled obligation remainder into legacy pending views."""

    buys: list[PendingPaperIntent] = []
    sells: list[PendingPaperIntent] = []
    for obligation in normalize_obligations(obligations):
        if obligation.remaining_shares <= 0:
            continue
        latest_event = obligation.event_history[-1]
        row = PendingPaperIntent(
            side=obligation.side,
            ticker=obligation.canonical_ticker,
            rank_consensus=obligation.rank_consensus,
            reason=latest_event.reason,
            replacement_peer=obligation.replacement_group_id,
        )
        (buys if obligation.side == "BUY" else sells).append(row)
    return (
        tuple(sorted(buys, key=lambda row: row.ticker)),
        tuple(sorted(sells, key=lambda row: row.ticker)),
    )


def normalize_state(state: PaperPortfolioState) -> tuple[float, dict[str, int], dict[str, PendingPaperIntent], dict[str, PendingPaperIntent]]:
    if not isinstance(state, PaperPortfolioState):
        raise DecisionV1Error("EXECUTION_V1_PAPER_STATE_REQUIRED")
    if state.source != PAPER_STATE_SOURCE:
        raise DecisionV1Error("EXECUTION_V1_NON_PAPER_STATE_FORBIDDEN")
    cash = finite_nonnegative(state.cash_idr, "EXECUTION_V1_CASH_INVALID")
    positions: dict[str, int] = {}
    for position in state.positions:
        symbol = ticker(position.ticker)
        shares = whole_lot_shares(
            position.shares,
            "EXECUTION_V1_POSITION_NOT_WHOLE_LOT",
        )
        if symbol in positions:
            raise DecisionV1Error("EXECUTION_V1_DUPLICATE_POSITION")
        positions[symbol] = shares
    pending_buys = normalize_pending(state.pending_buys, "BUY")
    pending_sells = normalize_pending(state.pending_sells, "SELL")
    obligations = normalize_obligations(state.obligations)
    if obligations:
        expected_buys, expected_sells = pending_intents_from_obligations(obligations)
        expected_buys_map = normalize_pending(expected_buys, "BUY")
        expected_sells_map = normalize_pending(expected_sells, "SELL")
        if pending_buys != expected_buys_map or pending_sells != expected_sells_map:
            raise DecisionV1Error("EXECUTION_V1_OBLIGATION_PENDING_PROJECTION_MISMATCH")
    elif set(pending_buys) & set(positions):
        raise DecisionV1Error("EXECUTION_V1_PENDING_BUY_ALREADY_HELD")
    if set(pending_sells) - set(positions):
        raise DecisionV1Error("EXECUTION_V1_PENDING_SELL_WITHOUT_POSITION")
    return cash, positions, pending_buys, pending_sells


def close_obligation_explicitly(
    state: PaperPortfolioState,
    *,
    obligation_id: str,
    event_id: str,
    session_date: str,
    reason: str,
    status: Literal["CANCELED", "RELINQUISHED"] = "CANCELED",
    parent_state_sha256: str | None = None,
    seat_policy: DecisionSeatClosePolicyV1 | None = None,
) -> PaperPortfolioState:
    """Apply only a caller-supplied close event; never infer a reversal close."""

    if status not in {"CANCELED", "RELINQUISHED"}:
        raise DecisionV1Error("EXECUTION_V1_OBLIGATION_CLOSE_STATUS_INVALID")
    if not isinstance(obligation_id, str) or not obligation_id:
        raise DecisionV1Error("EXECUTION_V1_OBLIGATION_CLOSE_ID_INVALID")
    normalize_state(state)
    obligations = list(normalize_obligations(state.obligations))
    matching = [
        index
        for index, obligation in enumerate(obligations)
        if obligation.obligation_id == obligation_id
    ]
    if not matching:
        raise DecisionV1Error("EXECUTION_V1_OBLIGATION_CLOSE_NOT_FOUND")
    index = matching[0]
    existing_event = next(
        (
            event
            for event in obligations[index].event_history
            if event.event_id == event_id
        ),
        None,
    )
    if existing_event is None:
        before_hash = paper_state_hash(state)
        if parent_state_sha256 is not None and parent_state_sha256 != before_hash:
            raise DecisionV1Error("EXECUTION_V1_OBLIGATION_CLOSE_PARENT_MISMATCH")
        event_parent_state_sha256 = before_hash
    else:
        # Replay the same event against its post-transition state without
        # mistaking the new state hash for a conflicting parent. The primitive
        # below still compares every event field and rejects altered bytes.
        event_parent_state_sha256 = (
            existing_event.parent_state_sha256
            if parent_state_sha256 is None
            else parent_state_sha256
        )
    obligations[index] = cancel_remaining(
        obligations[index],
        event_id=event_id,
        session_date=session_date,
        reason=reason,
        parent_state_sha256=event_parent_state_sha256,
        status=status,
        seat_policy=seat_policy,
    )
    pending_buys, pending_sells = pending_intents_from_obligations(obligations)
    updated = PaperPortfolioState(
        as_of_session_date=state.as_of_session_date,
        cash_idr=state.cash_idr,
        positions=state.positions,
        pending_buys=pending_buys,
        pending_sells=pending_sells,
        reconciliation_required=state.reconciliation_required,
        source=state.source,
        obligations=tuple(obligations),
    )
    normalize_state(updated)
    return updated


def classify_state_for_migration(state: PaperPortfolioState) -> str:
    """Classify legacy evidence without inventing a missing quantity vector."""

    cash, positions, pending_buys, pending_sells = normalize_state(state)
    del cash
    if state.obligations:
        return OBLIGATION_V1_STATE
    if positions or pending_buys or pending_sells:
        return UNKNOWN_ORPHANED_PARTIAL
    return LEGACY_POSITION_ONLY


def paper_state_hash(state: PaperPortfolioState) -> str:
    cash, positions, pending_buys, pending_sells = normalize_state(state)
    def payload(rows: dict[str, PendingPaperIntent]) -> list[tuple[object, ...]]:
        return [
            (x.side, x.ticker, x.rank_consensus, x.reason, x.replacement_peer)
            for x in sorted(rows.values(), key=lambda y: y.ticker)
        ]
    value = {
        "as_of_session_date": state.as_of_session_date,
        "cash_idr": round(cash, 6),
        "positions": sorted(positions.items()),
        "pending_buys": payload(pending_buys),
        "pending_sells": payload(pending_sells),
        "reconciliation_required": bool(state.reconciliation_required),
        "source": state.source,
    }
    if state.obligations:
        value["obligations"] = obligations_payload(state.obligations)
    return hashlib.sha256(
        (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
