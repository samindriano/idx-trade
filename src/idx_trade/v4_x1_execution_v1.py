from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Mapping

from .v4_x1_decision_v1_contract import DecisionPlan, DecisionV1Error
from .v4_x1_sizing_v1 import SizingPlan, size_decision_v1_entries

EXPECTED_EXECUTION_CONFIG_SHA256 = "498e544b6fc5a711c6aad0ea42c7895bf9b0d424bb025b96586719a596a284e5"
EXECUTION_RULE_ID = "V4_X1_EXECUTION_V1"
PAPER_STATE_SOURCE = "EXECUTABLE_PAPER_V1"
LOT_SIZE_SHARES = 100
BUY_FEE_BPS = 15.0
SELL_FEE_BPS = 25.0
SLIPPAGE_BPS = 10.0
STAMP_DUTY_IDR = 10_000.0
STAMP_DUTY_THRESHOLD_IDR = 10_000_000.0
MAX_ENTRY_WEIGHT = 0.15


@dataclass(frozen=True)
class PaperPosition:
    ticker: str
    shares: int


@dataclass(frozen=True)
class PaperPortfolioState:
    as_of_session_date: str
    cash_idr: float
    positions: tuple[PaperPosition, ...]
    reconciliation_required: bool = False
    source: str = PAPER_STATE_SOURCE


@dataclass(frozen=True)
class PlannedSell:
    ticker: str
    shares: int
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
    decision_plan: DecisionPlan
    rule_id: str = EXECUTION_RULE_ID


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
    reconciliation_required: bool
    rule_id: str = EXECUTION_RULE_ID


def verify_execution_v1_config(config_path: str | Path) -> None:
    path = Path(config_path).expanduser().resolve()
    if not path.is_file():
        raise DecisionV1Error(f"EXECUTION_V1_CONFIG_MISSING:{path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != EXPECTED_EXECUTION_CONFIG_SHA256:
        raise DecisionV1Error(
            f"EXECUTION_V1_CONFIG_SHA_MISMATCH:{actual}!={EXPECTED_EXECUTION_CONFIG_SHA256}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "decision_rule": "V4_X1_DECISION_V1",
        "sizing_rule": "V4_X1_SIZING_V1",
        "paper_state_source": PAPER_STATE_SOURCE,
        "sizing_reference_price": "RAW_CLOSE_T",
        "execution_base_price": "RAW_OPEN_T_PLUS_1",
        "sell_before_buy": True,
        "primary_buy_fee_bps": BUY_FEE_BPS,
        "primary_sell_fee_bps": SELL_FEE_BPS,
        "primary_slippage_bps_each_side": SLIPPAGE_BPS,
        "corporate_action_continuity_required": True,
        "strategic_cash_overlay": False,
        "historical_pnl_authorized": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise DecisionV1Error(f"EXECUTION_V1_CONFIG_CONTRACT_CHANGED:{key}")


def _ticker(value: object) -> str:
    ticker = str(value).upper().replace(".JK", "").strip()
    if not ticker:
        raise DecisionV1Error("EXECUTION_V1_EMPTY_TICKER")
    return ticker


def _finite_positive(value: object, code: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(code) from exc
    if not math.isfinite(x) or x <= 0:
        raise DecisionV1Error(code)
    return x


def _finite_nonnegative(value: object, code: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(code) from exc
    if not math.isfinite(x) or x < 0:
        raise DecisionV1Error(code)
    return x


def _normalize_state(state: PaperPortfolioState) -> tuple[float, dict[str, int]]:
    if not isinstance(state, PaperPortfolioState):
        raise DecisionV1Error("EXECUTION_V1_PAPER_STATE_REQUIRED")
    if state.source != PAPER_STATE_SOURCE:
        raise DecisionV1Error("EXECUTION_V1_NON_PAPER_STATE_FORBIDDEN")
    cash = _finite_nonnegative(state.cash_idr, "EXECUTION_V1_CASH_INVALID")
    positions: dict[str, int] = {}
    for position in state.positions:
        ticker = _ticker(position.ticker)
        shares = int(position.shares)
        if shares <= 0 or shares % LOT_SIZE_SHARES:
            raise DecisionV1Error("EXECUTION_V1_POSITION_NOT_WHOLE_LOT")
        if ticker in positions:
            raise DecisionV1Error("EXECUTION_V1_DUPLICATE_POSITION")
        positions[ticker] = shares
    return cash, positions


def paper_state_hash(state: PaperPortfolioState) -> str:
    cash, positions = _normalize_state(state)
    payload = {
        "as_of_session_date": state.as_of_session_date,
        "cash_idr": round(cash, 6),
        "positions": sorted(positions.items()),
        "reconciliation_required": bool(state.reconciliation_required),
        "source": state.source,
    }
    return hashlib.sha256(
        (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()


def _require_prices(
    tickers: set[str],
    prices: Mapping[str, float],
    *,
    code_prefix: str,
) -> dict[str, float]:
    result: dict[str, float] = {}
    for ticker in sorted(tickers):
        if ticker not in prices:
            raise DecisionV1Error(f"{code_prefix}_MISSING:{ticker}")
        result[ticker] = _finite_positive(prices[ticker], f"{code_prefix}_INVALID:{ticker}")
    return result


def _fee(gross: float, bps: float) -> float:
    return gross * bps / 10_000.0


def _sell_effective_price(raw_price: float) -> float:
    return raw_price * (1.0 - SLIPPAGE_BPS / 10_000.0)


def _buy_effective_price(raw_price: float) -> float:
    return raw_price * (1.0 + SLIPPAGE_BPS / 10_000.0)


def prepare_execution_v1(
    decision_plan: DecisionPlan,
    paper_state: PaperPortfolioState,
    *,
    next_session_date: str,
    raw_close_prices_t: Mapping[str, float],
) -> ExecutionOrderPlan:
    if not isinstance(decision_plan, DecisionPlan) or decision_plan.rule_id != "V4_X1_DECISION_V1":
        raise DecisionV1Error("EXECUTION_V1_DECISION_PLAN_REQUIRED")

    cash, positions = _normalize_state(paper_state)
    if paper_state.reconciliation_required:
        raise DecisionV1Error("EXECUTION_V1_PRIOR_RECONCILIATION_REQUIRED")
    if decision_plan.execution_reference != "OFFICIAL_OPEN_T_PLUS_1":
        raise DecisionV1Error("EXECUTION_V1_DECISION_EXECUTION_REFERENCE_CHANGED")
    import pandas as pd
    state_date = pd.to_datetime(paper_state.as_of_session_date, errors="coerce")
    decision_date = pd.to_datetime(decision_plan.decision_session_date, errors="coerce")
    next_date = pd.to_datetime(next_session_date, errors="coerce")
    if pd.isna(state_date) or pd.isna(decision_date) or pd.isna(next_date):
        raise DecisionV1Error("EXECUTION_V1_SESSION_DATE_INVALID")
    if pd.Timestamp(state_date).normalize() > pd.Timestamp(decision_date).normalize():
        raise DecisionV1Error("EXECUTION_V1_PAPER_STATE_FROM_FUTURE")
    if pd.Timestamp(next_date).normalize() <= pd.Timestamp(decision_date).normalize():
        raise DecisionV1Error("EXECUTION_V1_NEXT_SESSION_NOT_AFTER_DECISION")

    involved = set(positions) | set(decision_plan.target_positions)
    closes = _require_prices(involved, raw_close_prices_t, code_prefix="EXECUTION_V1_RAW_CLOSE")

    eod_nav = cash + sum(shares * closes[ticker] for ticker, shares in positions.items())
    if eod_nav <= 0:
        raise DecisionV1Error("EXECUTION_V1_EOD_NAV_INVALID")

    sell_intents = {intent.ticker: intent for intent in decision_plan.sell_intents}
    sells: list[PlannedSell] = []
    projected_cash = cash
    for ticker, intent in sorted(sell_intents.items()):
        shares = positions.get(ticker, 0)
        sells.append(PlannedSell(ticker=ticker, shares=shares, replacement_peer=intent.replacement_peer))
        if shares:
            effective = _sell_effective_price(closes[ticker])
            gross = shares * effective
            projected_cash += gross - _fee(gross, SELL_FEE_BPS)

    projected_cash = min(projected_cash, eod_nav)
    sizing_plan = size_decision_v1_entries(
        decision_plan,
        nav_idr=eod_nav,
        available_cash_idr=projected_cash,
        reference_prices=closes,
    )

    return ExecutionOrderPlan(
        decision_session_date=decision_plan.decision_session_date,
        execution_session_date=str(next_session_date),
        state_hash=paper_state_hash(paper_state),
        eod_nav_idr=float(eod_nav),
        projected_cash_for_sizing_idr=float(projected_cash),
        sizing_plan=sizing_plan,
        sells=tuple(sells),
        decision_plan=decision_plan,
    )


def execute_open_v1(
    order_plan: ExecutionOrderPlan,
    paper_state: PaperPortfolioState,
    *,
    execution_session_date: str,
    raw_open_prices_t1: Mapping[str, float],
    tradable_tickers: set[str],
    corporate_action_continuity_ok: bool,
) -> ExecutionResult:
    if not corporate_action_continuity_ok:
        raise DecisionV1Error("EXECUTION_V1_CA_CONTINUITY_REQUIRED")
    if order_plan.rule_id != EXECUTION_RULE_ID:
        raise DecisionV1Error("EXECUTION_V1_ORDER_RULE_CHANGED")
    if str(execution_session_date) != order_plan.execution_session_date:
        raise DecisionV1Error("EXECUTION_V1_SESSION_DATE_MISMATCH")
    before_hash = paper_state_hash(paper_state)
    if before_hash != order_plan.state_hash:
        raise DecisionV1Error("EXECUTION_V1_STATE_HASH_MISMATCH")

    cash, positions = _normalize_state(paper_state)
    tradable = {_ticker(t) for t in tradable_tickers}
    fills: list[FillRecord] = []
    sell_resolution: dict[str, bool] = {}

    # Sells always resolve before buys.
    for order in order_plan.sells:
        ticker = order.ticker
        shares = positions.get(ticker, 0)
        if shares == 0:
            sell_resolution[ticker] = True
            fills.append(FillRecord(
                side="SELL",
                ticker=ticker,
                planned_shares=order.shares,
                filled_shares=0,
                raw_open=None,
                effective_price=None,
                gross_notional=0.0,
                fee_idr=0.0,
                cash_effect_idr=0.0,
                status="NO_POSITION_NOOP",
                replacement_peer=order.replacement_peer,
            ))
            continue

        raw = raw_open_prices_t1.get(ticker)
        if ticker not in tradable or raw is None:
            sell_resolution[ticker] = False
            fills.append(FillRecord(
                side="SELL",
                ticker=ticker,
                planned_shares=shares,
                filled_shares=0,
                raw_open=None,
                effective_price=None,
                gross_notional=0.0,
                fee_idr=0.0,
                cash_effect_idr=0.0,
                status="MARKET_EXIT_UNAVAILABLE",
                replacement_peer=order.replacement_peer,
            ))
            continue
        try:
            raw_price = _finite_positive(raw, f"EXECUTION_V1_RAW_OPEN_INVALID:{ticker}")
        except DecisionV1Error:
            sell_resolution[ticker] = False
            fills.append(FillRecord(
                side="SELL", ticker=ticker, planned_shares=shares, filled_shares=0,
                raw_open=None, effective_price=None, gross_notional=0.0,
                fee_idr=0.0, cash_effect_idr=0.0, status="MARKET_EXIT_UNAVAILABLE",
                replacement_peer=order.replacement_peer,
            ))
            continue
        effective = _sell_effective_price(raw_price)
        gross = shares * effective
        fee = _fee(gross, SELL_FEE_BPS)
        proceeds = gross - fee
        cash += proceeds
        del positions[ticker]
        sell_resolution[ticker] = True
        fills.append(FillRecord(
            side="SELL", ticker=ticker, planned_shares=shares, filled_shares=shares,
            raw_open=raw_price, effective_price=effective, gross_notional=gross,
            fee_idr=fee, cash_effect_idr=proceeds, status="FILLED",
            replacement_peer=order.replacement_peer,
        ))

    buy_intents = {intent.ticker: intent for intent in order_plan.decision_plan.buy_intents}
    sizing_by_ticker = {entry.ticker: entry for entry in order_plan.sizing_plan.entries}

    eligible: list[tuple[str, object, object, float]] = []
    blocked: list[FillRecord] = []
    for ticker in sorted(sizing_by_ticker):
        entry = sizing_by_ticker[ticker]
        intent = buy_intents[ticker]
        if entry.shares <= 0:
            blocked.append(FillRecord(
                side="BUY", ticker=ticker, planned_shares=0, filled_shares=0,
                raw_open=None, effective_price=None, gross_notional=0.0, fee_idr=0.0,
                cash_effect_idr=0.0, status=entry.status,
                replacement_peer=intent.replacement_peer,
            ))
            continue
        if intent.replacement_peer is not None and not sell_resolution.get(intent.replacement_peer, False):
            blocked.append(FillRecord(
                side="BUY", ticker=ticker, planned_shares=entry.shares, filled_shares=0,
                raw_open=None, effective_price=None, gross_notional=0.0, fee_idr=0.0,
                cash_effect_idr=0.0, status="BLOCKED_BY_UNRESOLVED_PAIRED_SELL",
                replacement_peer=intent.replacement_peer,
            ))
            continue
        raw = raw_open_prices_t1.get(ticker)
        if ticker not in tradable or raw is None:
            blocked.append(FillRecord(
                side="BUY", ticker=ticker, planned_shares=entry.shares, filled_shares=0,
                raw_open=None, effective_price=None, gross_notional=0.0, fee_idr=0.0,
                cash_effect_idr=0.0, status="MARKET_ENTRY_UNAVAILABLE",
                replacement_peer=intent.replacement_peer,
            ))
            continue
        try:
            raw_price = _finite_positive(raw, f"EXECUTION_V1_RAW_OPEN_INVALID:{ticker}")
        except DecisionV1Error:
            blocked.append(FillRecord(
                side="BUY", ticker=ticker, planned_shares=entry.shares, filled_shares=0,
                raw_open=None, effective_price=None, gross_notional=0.0, fee_idr=0.0,
                cash_effect_idr=0.0, status="MARKET_ENTRY_UNAVAILABLE",
                replacement_peer=intent.replacement_peer,
            ))
            continue
        eligible.append((ticker, entry, intent, raw_price))

    # Reserve stamp duty conservatively whenever maximum executable turnover can cross threshold.
    sell_gross = sum(fill.gross_notional for fill in fills if fill.side == "SELL")
    max_buy_gross = sum(entry.shares * _buy_effective_price(raw) for _, entry, _, raw in eligible)
    stamp_reserve = STAMP_DUTY_IDR if sell_gross + max_buy_gross > STAMP_DUTY_THRESHOLD_IDR else 0.0
    buy_cash_pool = max(0.0, cash - stamp_reserve)
    per_entry_cash = buy_cash_pool / len(eligible) if eligible else 0.0

    for ticker, entry, intent, raw_price in eligible:
        if ticker in positions:
            raise DecisionV1Error("EXECUTION_V1_BUY_ALREADY_HELD_ACTUAL")
        effective = _buy_effective_price(raw_price)
        debit_per_lot = effective * LOT_SIZE_SHARES * (1.0 + BUY_FEE_BPS / 10_000.0)
        budget = min(entry.desired_notional, per_entry_cash)
        max_by_budget = int(math.floor(budget / debit_per_lot + 1e-12))
        max_by_cap = int(math.floor(
            (MAX_ENTRY_WEIGHT * order_plan.eod_nav_idr)
            / (effective * LOT_SIZE_SHARES)
            + 1e-12
        ))
        planned_lots = entry.shares // LOT_SIZE_SHARES
        lots = max(0, min(planned_lots, max_by_budget, max_by_cap))
        shares = lots * LOT_SIZE_SHARES
        if shares == 0:
            fills.append(FillRecord(
                side="BUY", ticker=ticker, planned_shares=entry.shares, filled_shares=0,
                raw_open=raw_price, effective_price=effective, gross_notional=0.0,
                fee_idr=0.0, cash_effect_idr=0.0,
                status="ZERO_FILL_CASH_GAP_OR_CAP_CONSTRAINT",
                replacement_peer=intent.replacement_peer,
            ))
            continue
        gross = shares * effective
        fee = _fee(gross, BUY_FEE_BPS)
        debit = gross + fee
        if debit > cash + 1e-6:
            raise DecisionV1Error("EXECUTION_V1_BUY_CASH_INVARIANT_BROKEN")
        cash -= debit
        positions[ticker] = shares
        fills.append(FillRecord(
            side="BUY", ticker=ticker, planned_shares=entry.shares, filled_shares=shares,
            raw_open=raw_price, effective_price=effective, gross_notional=gross,
            fee_idr=fee, cash_effect_idr=-debit, status="FILLED",
            replacement_peer=intent.replacement_peer,
        ))

    fills.extend(blocked)
    gross_turnover = sum(fill.gross_notional for fill in fills)
    stamp = STAMP_DUTY_IDR if gross_turnover > STAMP_DUTY_THRESHOLD_IDR else 0.0
    if stamp:
        if cash + 1e-6 < stamp:
            raise DecisionV1Error("EXECUTION_V1_STAMP_DUTY_CASH_SHORTFALL")
        cash -= stamp

    if cash < -1e-6:
        raise DecisionV1Error("EXECUTION_V1_NEGATIVE_CASH")
    if any(shares <= 0 or shares % LOT_SIZE_SHARES for shares in positions.values()):
        raise DecisionV1Error("EXECUTION_V1_FINAL_POSITION_INVARIANT_BROKEN")

    operational_failure_statuses = {
        "MARKET_EXIT_UNAVAILABLE",
        "MARKET_ENTRY_UNAVAILABLE",
        "BLOCKED_BY_UNRESOLVED_PAIRED_SELL",
        "ZERO_FILL_CASH_GAP_OR_CAP_CONSTRAINT",
    }
    reconciliation_required = any(fill.status in operational_failure_statuses for fill in fills)

    state_after = PaperPortfolioState(
        as_of_session_date=str(execution_session_date),
        cash_idr=float(max(cash, 0.0)),
        positions=tuple(
            PaperPosition(ticker=ticker, shares=shares)
            for ticker, shares in sorted(positions.items())
        ),
        reconciliation_required=bool(reconciliation_required),
    )
    return ExecutionResult(
        execution_session_date=str(execution_session_date),
        state_before_hash=before_hash,
        state_after=state_after,
        fills=tuple(fills),
        stamp_duty_idr=float(stamp),
        gross_turnover_idr=float(gross_turnover),
        reconciliation_required=bool(reconciliation_required),
    )
