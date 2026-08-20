from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Literal

from .v4_x1_decision_v1_contract import DecisionV1Error, TradeIntent
from .v4_x1_sizing_v1 import SizingPlan

EXECUTION_RULE_ID = "V4_X1_EXECUTION_V1"
PAPER_STATE_SOURCE = "EXECUTABLE_PAPER_V1"
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


def normalize_pending(rows: tuple[PendingPaperIntent, ...], side: str) -> dict[str, PendingPaperIntent]:
    out: dict[str, PendingPaperIntent] = {}
    for row in rows:
        if row.side != side:
            raise DecisionV1Error("EXECUTION_V1_PENDING_SIDE_MISMATCH")
        symbol = ticker(row.ticker)
        if symbol in out:
            raise DecisionV1Error("EXECUTION_V1_DUPLICATE_PENDING_INTENT")
        out[symbol] = PendingPaperIntent(
            side=side, ticker=symbol, rank_consensus=row.rank_consensus,
            reason=row.reason, replacement_peer=row.replacement_peer,
        )
    return out


def normalize_state(state: PaperPortfolioState) -> tuple[float, dict[str, int], dict[str, PendingPaperIntent], dict[str, PendingPaperIntent]]:
    if not isinstance(state, PaperPortfolioState):
        raise DecisionV1Error("EXECUTION_V1_PAPER_STATE_REQUIRED")
    if state.source != PAPER_STATE_SOURCE:
        raise DecisionV1Error("EXECUTION_V1_NON_PAPER_STATE_FORBIDDEN")
    cash = finite_nonnegative(state.cash_idr, "EXECUTION_V1_CASH_INVALID")
    positions: dict[str, int] = {}
    for position in state.positions:
        symbol = ticker(position.ticker)
        shares = int(position.shares)
        if shares <= 0 or shares % LOT_SIZE_SHARES:
            raise DecisionV1Error("EXECUTION_V1_POSITION_NOT_WHOLE_LOT")
        if symbol in positions:
            raise DecisionV1Error("EXECUTION_V1_DUPLICATE_POSITION")
        positions[symbol] = shares
    pending_buys = normalize_pending(state.pending_buys, "BUY")
    pending_sells = normalize_pending(state.pending_sells, "SELL")
    if set(pending_buys) & set(positions):
        raise DecisionV1Error("EXECUTION_V1_PENDING_BUY_ALREADY_HELD")
    if set(pending_sells) - set(positions):
        raise DecisionV1Error("EXECUTION_V1_PENDING_SELL_WITHOUT_POSITION")
    return cash, positions, pending_buys, pending_sells


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
    return hashlib.sha256(
        (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
