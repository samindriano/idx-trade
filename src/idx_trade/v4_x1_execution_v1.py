from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .v4_x1_decision_v1_contract import DecisionPlan, DecisionV1Error, TradeIntent
from .v4_x1_sizing_v1 import (
    VerifiedDecisionPlan,
    _VERIFIED_DECISION_PLAN_TOKEN,
    _SIZING_PLAN_TOKEN,
    _size_entries_for_intents,
)
from .v4_x1_execution_v1_verify import (
    VerifiedCorporateActionAttestation,
    VerifiedEODExecutionInputs,
    VerifiedOpenExecutionInputs,
    _CA_ATTESTATION_TOKEN,
    _EOD_INPUT_TOKEN,
    _OPEN_INPUT_TOKEN,
)
from .v4_x1_execution_v1_contract import (
    BUY_FEE_BPS,
    EXECUTION_RULE_ID,
    FillRecord,
    ExecutionOrderPlan,
    ExecutionResult,
    LOT_SIZE_SHARES,
    MAX_ENTRY_WEIGHT,
    MAX_ORDER_NOTIONAL_SHARE_REFERENCE_VALUE,
    PAPER_STATE_SOURCE,
    PaperPortfolioState,
    PaperPosition,
    PendingPaperIntent,
    PlannedSell,
    SELL_FEE_BPS,
    STAMP_DUTY_IDR,
    STAMP_DUTY_THRESHOLD_IDR,
    _EXECUTION_PLAN_TOKEN,
    normalize_state,
    paper_state_hash,
)
from .v4_x1_execution_v1_allocator import (
    buy_effective_price,
    fee,
    joint_open_allocation,
    sell_effective_price,
)

EXPECTED_EXECUTION_CONFIG_SHA256 = "9f90b6c846689796f63948a758e0cef8d8a6aac0e119a22806f7b6fb41cbf096"


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
        "sizing_reference_price": "VERIFIED_RAW_CLOSE_T",
        "execution_base_price": "VERIFIED_RAW_OPEN_T_PLUS_1",
        "sell_before_buy": True,
        "primary_buy_fee_bps": BUY_FEE_BPS,
        "primary_sell_fee_bps": SELL_FEE_BPS,
        "corporate_action_attestation_required": True,
        "max_order_notional_share_reference_day_value": MAX_ORDER_NOTIONAL_SHARE_REFERENCE_VALUE,
        "strategic_cash_overlay": False,
        "historical_pnl_authorized": False,
        "paper_nonfill_policy": "PERSIST_PENDING_TRANSITION_NOT_SHADOW_MUTATION",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise DecisionV1Error(f"EXECUTION_V1_CONFIG_CONTRACT_CHANGED:{key}")


def _merge_effective_intents(
    decision_plan: DecisionPlan,
    positions: dict[str, int],
    pending_buys: dict[str, PendingPaperIntent],
    pending_sells: dict[str, PendingPaperIntent],
) -> tuple[tuple[TradeIntent, ...], tuple[TradeIntent, ...]]:
    target = set(decision_plan.target_positions)
    new_buys = {x.ticker: x for x in decision_plan.buy_intents}
    new_sells = {x.ticker: x for x in decision_plan.sell_intents}

    for ticker, row in pending_buys.items():
        if ticker in target and ticker not in positions and ticker not in new_buys:
            new_buys[ticker] = TradeIntent(
                "BUY_INTENT", ticker, row.rank_consensus,
                "PAPER_RETRY_" + row.reason, row.replacement_peer,
            )
    for ticker, row in pending_sells.items():
        if ticker not in target and ticker in positions and ticker not in new_sells:
            new_sells[ticker] = TradeIntent(
                "SELL_INTENT", ticker, row.rank_consensus,
                "PAPER_RETRY_" + row.reason, row.replacement_peer,
            )

    unexplained_missing = (target - set(positions)) - set(new_buys)
    unexplained_extra = (set(positions) - target) - set(new_sells)
    if unexplained_missing or unexplained_extra:
        raise DecisionV1Error(
            f"EXECUTION_V1_UNEXPLAINED_SHADOW_PAPER_DIVERGENCE:"
            f"MISSING={sorted(unexplained_missing)}:EXTRA={sorted(unexplained_extra)}"
        )

    buys = tuple(sorted(
        new_buys.values(), key=lambda x: (int(x.rank_consensus or 10**9), x.ticker)
    ))
    sells = tuple(sorted(new_sells.values(), key=lambda x: x.ticker))
    return buys, sells


def prepare_execution_v1(
    verified_plan: VerifiedDecisionPlan,
    paper_state: PaperPortfolioState,
    *,
    eod_inputs: VerifiedEODExecutionInputs,
) -> ExecutionOrderPlan:
    if (
        not isinstance(verified_plan, VerifiedDecisionPlan)
        or verified_plan._verification_token is not _VERIFIED_DECISION_PLAN_TOKEN
    ):
        raise DecisionV1Error("EXECUTION_V1_VERIFIED_DECISION_PLAN_REQUIRED")
    decision_plan = verified_plan.plan
    if not isinstance(decision_plan, DecisionPlan) or decision_plan.rule_id != "V4_X1_DECISION_V1":
        raise DecisionV1Error("EXECUTION_V1_DECISION_PLAN_REQUIRED")
    if (
        not isinstance(eod_inputs, VerifiedEODExecutionInputs)
        or eod_inputs._verification_token is not _EOD_INPUT_TOKEN
    ):
        raise DecisionV1Error("EXECUTION_V1_VERIFIED_EOD_INPUT_REQUIRED")
    if eod_inputs.session_date != decision_plan.decision_session_date:
        raise DecisionV1Error("EXECUTION_V1_EOD_DECISION_SESSION_MISMATCH")

    cash, positions, pending_buys, pending_sells = normalize_state(paper_state)
    if paper_state.reconciliation_required:
        raise DecisionV1Error("EXECUTION_V1_PRIOR_RECONCILIATION_REQUIRED")
    if decision_plan.execution_reference != "OFFICIAL_OPEN_T_PLUS_1":
        raise DecisionV1Error("EXECUTION_V1_DECISION_EXECUTION_REFERENCE_CHANGED")

    effective_buys, effective_sells = _merge_effective_intents(
        decision_plan, positions, pending_buys, pending_sells
    )
    involved = set(positions) | set(decision_plan.target_positions)
    missing_close = involved - set(eod_inputs.raw_close_prices)
    if missing_close:
        raise DecisionV1Error(f"EXECUTION_V1_VERIFIED_CLOSE_MISSING:{sorted(missing_close)}")
    closes = {t: float(eod_inputs.raw_close_prices[t]) for t in involved}
    eod_nav = cash + sum(shares * closes[ticker] for ticker, shares in positions.items())
    if eod_nav <= 0:
        raise DecisionV1Error("EXECUTION_V1_EOD_NAV_INVALID")

    sells: list[PlannedSell] = []
    projected_cash = cash
    for intent in effective_sells:
        shares = positions.get(intent.ticker, 0)
        if shares <= 0:
            raise DecisionV1Error("EXECUTION_V1_EFFECTIVE_SELL_WITHOUT_POSITION")
        sells.append(PlannedSell(
            ticker=intent.ticker,
            shares=shares,
            rank_consensus=intent.rank_consensus,
            reason=intent.reason,
            replacement_peer=intent.replacement_peer,
        ))
        effective = sell_effective_price(closes[intent.ticker])
        gross = shares * effective
        projected_cash += gross - fee(gross, SELL_FEE_BPS)

    projected_cash = min(projected_cash, eod_nav)
    sizing_plan = _size_entries_for_intents(
        verified_plan,
        effective_buys,
        nav_idr=eod_nav,
        available_cash_idr=projected_cash,
        reference_prices=closes,
    )
    if sizing_plan._verification_token is not _SIZING_PLAN_TOKEN:
        raise DecisionV1Error("EXECUTION_V1_SIZING_PLAN_NOT_VERIFIED")

    return ExecutionOrderPlan(
        decision_session_date=decision_plan.decision_session_date,
        execution_session_date=eod_inputs.next_official_session_date,
        state_hash=paper_state_hash(paper_state),
        eod_nav_idr=float(eod_nav),
        projected_cash_for_sizing_idr=float(projected_cash),
        sizing_plan=sizing_plan,
        sells=tuple(sells),
        effective_buy_intents=effective_buys,
        target_positions=decision_plan.target_positions,
        regular_market_values_t={
            t: float(eod_inputs.regular_market_values.get(t, 0.0))
            for t in involved
        },
        eod_ohlcv_sha256=eod_inputs.ohlcv_artifact_sha256,
        eod_model_input_sha256=eod_inputs.model_input_sha256,
        official_calendar_sha256=eod_inputs.official_calendar_sha256,
        _verification_token=_EXECUTION_PLAN_TOKEN,
    )


def execute_open_v1(
    order_plan: ExecutionOrderPlan,
    paper_state: PaperPortfolioState,
    *,
    open_inputs: VerifiedOpenExecutionInputs,
    ca_attestation: VerifiedCorporateActionAttestation,
) -> ExecutionResult:
    if (
        not isinstance(order_plan, ExecutionOrderPlan)
        or order_plan._verification_token is not _EXECUTION_PLAN_TOKEN
    ):
        raise DecisionV1Error("EXECUTION_V1_VERIFIED_ORDER_PLAN_REQUIRED")
    if order_plan.sizing_plan._verification_token is not _SIZING_PLAN_TOKEN:
        raise DecisionV1Error("EXECUTION_V1_VERIFIED_SIZING_PLAN_REQUIRED")
    if (
        not isinstance(open_inputs, VerifiedOpenExecutionInputs)
        or open_inputs._verification_token is not _OPEN_INPUT_TOKEN
    ):
        raise DecisionV1Error("EXECUTION_V1_VERIFIED_OPEN_INPUT_REQUIRED")
    if (
        not isinstance(ca_attestation, VerifiedCorporateActionAttestation)
        or ca_attestation._verification_token is not _CA_ATTESTATION_TOKEN
    ):
        raise DecisionV1Error("EXECUTION_V1_VERIFIED_CA_ATTESTATION_REQUIRED")
    if open_inputs.session_date != order_plan.execution_session_date:
        raise DecisionV1Error("EXECUTION_V1_SESSION_DATE_MISMATCH")
    if (
        ca_attestation.from_session_date != order_plan.decision_session_date
        or ca_attestation.through_session_date != order_plan.execution_session_date
        or ca_attestation.status != "NO_RELEVANT_EVENTS"
    ):
        raise DecisionV1Error("EXECUTION_V1_CA_ATTESTATION_SCOPE_MISMATCH")

    before_hash = paper_state_hash(paper_state)
    if before_hash != order_plan.state_hash:
        raise DecisionV1Error("EXECUTION_V1_STATE_HASH_MISMATCH")

    cash, positions, _, _ = normalize_state(paper_state)
    involved = set(positions) | set(order_plan.target_positions)
    if not involved.issubset(ca_attestation.covered_tickers):
        raise DecisionV1Error("EXECUTION_V1_CA_ATTESTATION_COVERAGE_MISMATCH")

    fills: list[FillRecord] = []
    pending_sells: dict[str, PendingPaperIntent] = {}
    pending_buys: dict[str, PendingPaperIntent] = {}
    sell_resolution: dict[str, bool] = {}

    for order in order_plan.sells:
        ticker = order.ticker
        shares = positions.get(ticker, 0)
        if shares <= 0:
            raise DecisionV1Error("EXECUTION_V1_PLANNED_SELL_POSITION_DISAPPEARED")
        raw = open_inputs.raw_open_prices.get(ticker)
        if raw is None:
            sell_resolution[ticker] = False
            pending_sells[ticker] = PendingPaperIntent(
                "SELL", ticker, order.rank_consensus, order.reason, order.replacement_peer
            )
            fills.append(FillRecord(
                "SELL", ticker, shares, 0, None, None, 0.0, 0.0, 0.0,
                "MARKET_EXIT_UNAVAILABLE_PENDING", order.replacement_peer,
            ))
            continue
        effective = sell_effective_price(float(raw))
        capacity_notional = (
            MAX_ORDER_NOTIONAL_SHARE_REFERENCE_VALUE
            * max(0.0, order_plan.regular_market_values_t.get(ticker, 0.0))
        )
        max_capacity_lots = int(capacity_notional // (effective * LOT_SIZE_SHARES))
        fill_shares = min(shares, max_capacity_lots * LOT_SIZE_SHARES)
        if fill_shares <= 0:
            sell_resolution[ticker] = False
            pending_sells[ticker] = PendingPaperIntent(
                "SELL", ticker, order.rank_consensus,
                "REFERENCE_DAY_EXIT_CAPACITY_ZERO", order.replacement_peer,
            )
            fills.append(FillRecord(
                "SELL", ticker, shares, 0, float(raw), effective, 0.0, 0.0, 0.0,
                "REFERENCE_DAY_EXIT_CAPACITY_ZERO_PENDING", order.replacement_peer,
            ))
            continue
        gross = fill_shares * effective
        sell_fee = fee(gross, SELL_FEE_BPS)
        proceeds = gross - sell_fee
        cash += proceeds
        remaining = shares - fill_shares
        if remaining > 0:
            positions[ticker] = remaining
            sell_resolution[ticker] = False
            pending_sells[ticker] = PendingPaperIntent(
                "SELL", ticker, order.rank_consensus,
                "PARTIAL_EXIT_CAPACITY", order.replacement_peer,
            )
            status = "SIMULATED_PARTIAL_EXIT_CAPACITY_FILL_PENDING"
        else:
            del positions[ticker]
            sell_resolution[ticker] = True
            status = "SIMULATED_FILLED_EXIT_CAPACITY_GUARDED"
        fills.append(FillRecord(
            "SELL", ticker, shares, fill_shares, float(raw), effective, gross, sell_fee, proceeds,
            status, order.replacement_peer,
        ))

    intent_by_ticker = {x.ticker: x for x in order_plan.effective_buy_intents}
    sizing_by_ticker = {x.ticker: x for x in order_plan.sizing_plan.entries}
    eligible_entries = []
    raw_prices: dict[str, float] = {}
    for ticker, entry in sorted(sizing_by_ticker.items()):
        intent = intent_by_ticker[ticker]
        if entry.shares <= 0:
            pending_buys[ticker] = PendingPaperIntent(
                "BUY", ticker, intent.rank_consensus, entry.status, intent.replacement_peer
            )
            fills.append(FillRecord(
                "BUY", ticker, 0, 0, None, None, 0.0, 0.0, 0.0,
                f"{entry.status}_PENDING", intent.replacement_peer,
            ))
            continue
        if intent.replacement_peer is not None and not sell_resolution.get(intent.replacement_peer, False):
            pending_buys[ticker] = PendingPaperIntent(
                "BUY", ticker, intent.rank_consensus,
                "BLOCKED_BY_UNRESOLVED_PAIRED_SELL", intent.replacement_peer,
            )
            fills.append(FillRecord(
                "BUY", ticker, entry.shares, 0, None, None, 0.0, 0.0, 0.0,
                "BLOCKED_BY_UNRESOLVED_PAIRED_SELL_PENDING", intent.replacement_peer,
            ))
            continue
        raw = open_inputs.raw_open_prices.get(ticker)
        if raw is None:
            pending_buys[ticker] = PendingPaperIntent(
                "BUY", ticker, intent.rank_consensus,
                "MARKET_ENTRY_UNAVAILABLE", intent.replacement_peer,
            )
            fills.append(FillRecord(
                "BUY", ticker, entry.shares, 0, None, None, 0.0, 0.0, 0.0,
                "MARKET_ENTRY_UNAVAILABLE_PENDING", intent.replacement_peer,
            ))
            continue
        eligible_entries.append(entry)
        raw_prices[ticker] = float(raw)

    sell_gross = sum(x.gross_notional for x in fills if x.side == "SELL")
    allocation = joint_open_allocation(
        entries=eligible_entries,
        intents=intent_by_ticker,
        raw_open_prices=raw_prices,
        regular_values=order_plan.regular_market_values_t,
        eod_nav=order_plan.eod_nav_idr,
        cash=cash,
        sell_gross=sell_gross,
    )

    for entry in eligible_entries:
        ticker = entry.ticker
        intent = intent_by_ticker[ticker]
        lots = int(allocation.get(ticker, 0))
        shares = lots * LOT_SIZE_SHARES
        raw = raw_prices[ticker]
        effective = buy_effective_price(raw)
        if shares <= 0:
            reason = (
                "REFERENCE_DAY_CAPACITY_ZERO"
                if order_plan.regular_market_values_t.get(ticker, 0.0) <= 0
                else "JOINT_CASH_GAP_CAP_OR_CAPACITY_CONSTRAINT"
            )
            pending_buys[ticker] = PendingPaperIntent(
                "BUY", ticker, intent.rank_consensus, reason, intent.replacement_peer
            )
            fills.append(FillRecord(
                "BUY", ticker, entry.shares, 0, raw, effective, 0.0, 0.0, 0.0,
                reason + "_PENDING", intent.replacement_peer,
            ))
            continue
        if ticker in positions:
            raise DecisionV1Error("EXECUTION_V1_BUY_ALREADY_HELD_ACTUAL")
        gross = shares * effective
        buy_fee = fee(gross, BUY_FEE_BPS)
        debit = gross + buy_fee
        if debit > cash + 1e-6:
            raise DecisionV1Error("EXECUTION_V1_BUY_CASH_INVARIANT_BROKEN")
        if gross > MAX_ENTRY_WEIGHT * order_plan.eod_nav_idr + 1e-6:
            raise DecisionV1Error("EXECUTION_V1_ENTRY_CAP_INVARIANT_BROKEN")
        capacity_notional = (
            MAX_ORDER_NOTIONAL_SHARE_REFERENCE_VALUE
            * max(0.0, order_plan.regular_market_values_t.get(ticker, 0.0))
        )
        if gross > capacity_notional + 1e-6:
            raise DecisionV1Error("EXECUTION_V1_CAPACITY_INVARIANT_BROKEN")
        cash -= debit
        positions[ticker] = shares
        fills.append(FillRecord(
            "BUY", ticker, entry.shares, shares, raw, effective, gross, buy_fee, -debit,
            "SIMULATED_FILLED_JOINT_LOT_CAPACITY_GUARDED", intent.replacement_peer,
        ))

    gross_turnover = sum(x.gross_notional for x in fills)
    stamp = STAMP_DUTY_IDR if gross_turnover > STAMP_DUTY_THRESHOLD_IDR else 0.0
    if stamp:
        if cash + 1e-6 < stamp:
            raise DecisionV1Error("EXECUTION_V1_STAMP_DUTY_CASH_SHORTFALL")
        cash -= stamp
    if cash < -1e-6:
        raise DecisionV1Error("EXECUTION_V1_NEGATIVE_CASH")
    if any(shares <= 0 or shares % LOT_SIZE_SHARES for shares in positions.values()):
        raise DecisionV1Error("EXECUTION_V1_FINAL_POSITION_INVARIANT_BROKEN")

    target = set(order_plan.target_positions)
    missing = target - set(positions)
    extra = set(positions) - target
    if missing != set(pending_buys) or extra != set(pending_sells):
        raise DecisionV1Error(
            f"EXECUTION_V1_PENDING_TRANSITION_ACCOUNTING_BROKEN:"
            f"MISSING={sorted(missing)}:PBUY={sorted(pending_buys)}:"
            f"EXTRA={sorted(extra)}:PSELL={sorted(pending_sells)}"
        )

    state_after = PaperPortfolioState(
        as_of_session_date=open_inputs.session_date,
        cash_idr=float(max(cash, 0.0)),
        positions=tuple(PaperPosition(t, s) for t, s in sorted(positions.items())),
        pending_buys=tuple(sorted(pending_buys.values(), key=lambda x: x.ticker)),
        pending_sells=tuple(sorted(pending_sells.values(), key=lambda x: x.ticker)),
        reconciliation_required=False,
    )
    return ExecutionResult(
        execution_session_date=open_inputs.session_date,
        state_before_hash=before_hash,
        state_after=state_after,
        fills=tuple(fills),
        stamp_duty_idr=float(stamp),
        gross_turnover_idr=float(gross_turnover),
        pending_transition_count=len(pending_buys) + len(pending_sells),
        reconciliation_required=False,
    )


__all__ = [
    "EXECUTION_RULE_ID", "PAPER_STATE_SOURCE", "PaperPosition", "PendingPaperIntent",
    "PaperPortfolioState", "PlannedSell", "ExecutionOrderPlan", "FillRecord",
    "ExecutionResult", "paper_state_hash", "prepare_execution_v1", "execute_open_v1",
    "verify_execution_v1_config",
]
