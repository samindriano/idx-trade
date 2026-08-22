from __future__ import annotations

from dataclasses import replace

from .decision_v2_minimal import DecisionV2Error, DecisionV2Intent, DecisionV2Plan
from .v4_x1_decision_v1_contract import DecisionV1Error, TradeIntent
from .v4_x1_execution_v1_allocator import fee, sell_effective_price
from .v4_x1_execution_v1_contract import (
    ExecutionOrderPlan,
    PaperPortfolioState,
    PendingPaperIntent,
    PlannedSell,
    SELL_FEE_BPS,
    _EXECUTION_PLAN_TOKEN,
    normalize_state,
    paper_state_hash,
)
from .v4_x1_execution_v1_verify import (
    VerifiedEODExecutionInputs,
    _EOD_INPUT_TOKEN,
)
from .v4_x1_sizing_v1 import _SIZING_PLAN_TOKEN, _size_entries_core
from .v4_x1_sizing_v1_decision_v2_adapter import (
    VerifiedDecisionV2SizingPlan,
    _require_verified_v2,
)


def _mechanical_intent(intent: DecisionV2Intent) -> TradeIntent:
    return TradeIntent(
        side=intent.side,
        ticker=intent.ticker,
        rank_consensus=intent.rank_consensus,
        reason=intent.reason,
        replacement_peer=intent.replacement_peer,
    )


def _paper_explained_shadow(
    positions: dict[str, int],
    pending_buys: dict[str, PendingPaperIntent],
    pending_sells: dict[str, PendingPaperIntent],
) -> set[str]:
    shadow = set(positions)
    shadow.difference_update(pending_sells)
    shadow.update(pending_buys)
    return shadow


def _reconcile_effective_intents_v2(
    plan: DecisionV2Plan,
    positions: dict[str, int],
    pending_buys: dict[str, PendingPaperIntent],
    pending_sells: dict[str, PendingPaperIntent],
) -> tuple[tuple[TradeIntent, ...], tuple[TradeIntent, ...]]:
    """Reconcile Decision V2 shadow intents against executable paper state.

    A prior pending BUY means the Decision shadow owns the ticker while paper does
    not. A prior pending SELL means the Decision shadow no longer owns the ticker
    while paper still does. When the Decision reverses before the pending action
    fills, the opposite current intent cancels the obsolete pending transition;
    it must not create an impossible SELL-without-position or BUY-already-held.
    """

    target = set(plan.target_positions)
    actual = set(positions)
    current_shadow = set(plan.current_shadow_positions)
    explained_shadow = _paper_explained_shadow(positions, pending_buys, pending_sells)
    if current_shadow != explained_shadow:
        raise DecisionV2Error(
            "EXECUTION_V1_DECISION_V2_SHADOW_PAPER_LINEAGE_MISMATCH:"
            f"DECISION={sorted(current_shadow)}:PAPER_EXPLAINED={sorted(explained_shadow)}"
        )

    raw_buys = tuple(_mechanical_intent(x) for x in plan.buy_intents)
    raw_sells = tuple(_mechanical_intent(x) for x in plan.sell_intents)
    if len({x.ticker for x in raw_buys}) != len(raw_buys):
        raise DecisionV2Error("EXECUTION_V1_DECISION_V2_DUPLICATE_BUY_INTENT")
    if len({x.ticker for x in raw_sells}) != len(raw_sells):
        raise DecisionV2Error("EXECUTION_V1_DECISION_V2_DUPLICATE_SELL_INTENT")

    new_buys = {x.ticker: x for x in raw_buys}
    new_sells = {x.ticker: x for x in raw_sells}
    if set(new_buys) & set(new_sells):
        raise DecisionV2Error("EXECUTION_V1_DECISION_V2_BUY_SELL_OVERLAP")
    if set(new_buys) - target:
        raise DecisionV2Error("EXECUTION_V1_DECISION_V2_BUY_OUTSIDE_TARGET")
    if set(new_sells) & target:
        raise DecisionV2Error("EXECUTION_V1_DECISION_V2_SELL_STILL_IN_TARGET")

    required_buys = target - actual
    required_sells = actual - target
    effective_buys: dict[str, TradeIntent] = {}
    effective_sells: dict[str, TradeIntent] = {}
    pre_resolved_sell_peers: set[str] = set()

    for ticker, intent in new_buys.items():
        if ticker in required_buys:
            effective_buys[ticker] = intent
            continue
        # Decision reversed a previously pending SELL before paper managed to
        # dispose of the shares. Actual paper already matches the new target.
        if ticker in actual and ticker in pending_sells:
            continue
        raise DecisionV2Error(
            f"EXECUTION_V1_DECISION_V2_BUY_ALREADY_HELD_UNEXPLAINED:{ticker}"
        )

    for ticker, intent in new_sells.items():
        if ticker in required_sells:
            effective_sells[ticker] = intent
            continue
        # Decision reversed a previously pending BUY before paper ever acquired
        # the shares. There is nothing to sell; the stale pending BUY is canceled.
        if ticker not in actual and ticker in pending_buys:
            pre_resolved_sell_peers.add(ticker)
            continue
        raise DecisionV2Error(
            f"EXECUTION_V1_DECISION_V2_SELL_WITHOUT_POSITION_UNEXPLAINED:{ticker}"
        )

    for ticker, row in pending_buys.items():
        if ticker in required_buys:
            effective_buys.setdefault(
                ticker,
                TradeIntent(
                    "BUY_INTENT",
                    ticker,
                    row.rank_consensus,
                    "PAPER_RETRY_" + row.reason,
                    row.replacement_peer,
                ),
            )
            continue
        if ticker not in target:
            if ticker not in new_sells:
                raise DecisionV2Error(
                    f"EXECUTION_V1_DECISION_V2_PENDING_BUY_CANCEL_WITHOUT_SELL_INTENT:{ticker}"
                )
            continue
        raise DecisionV2Error(
            f"EXECUTION_V1_DECISION_V2_PENDING_BUY_STATE_INVALID:{ticker}"
        )

    for ticker, row in pending_sells.items():
        if ticker in required_sells:
            effective_sells.setdefault(
                ticker,
                TradeIntent(
                    "SELL_INTENT",
                    ticker,
                    row.rank_consensus,
                    "PAPER_RETRY_" + row.reason,
                    row.replacement_peer,
                ),
            )
            continue
        if ticker in target:
            if ticker not in new_buys:
                raise DecisionV2Error(
                    f"EXECUTION_V1_DECISION_V2_PENDING_SELL_CANCEL_WITHOUT_BUY_INTENT:{ticker}"
                )
            continue
        raise DecisionV2Error(
            f"EXECUTION_V1_DECISION_V2_PENDING_SELL_STATE_INVALID:{ticker}"
        )

    if set(effective_buys) != required_buys or set(effective_sells) != required_sells:
        raise DecisionV2Error(
            "EXECUTION_V1_DECISION_V2_RECONCILIATION_INCOMPLETE:"
            f"REQUIRED_BUYS={sorted(required_buys)}:EFFECTIVE_BUYS={sorted(effective_buys)}:"
            f"REQUIRED_SELLS={sorted(required_sells)}:EFFECTIVE_SELLS={sorted(effective_sells)}"
        )

    # If a replacement SELL is already resolved because that ticker was only a
    # never-filled pending BUY, its paired BUY must not remain artificially
    # blocked by execute_open_v1's sell-resolution dependency.
    for ticker, intent in tuple(effective_buys.items()):
        if intent.replacement_peer in pre_resolved_sell_peers:
            effective_buys[ticker] = replace(
                intent,
                reason="PAPER_PAIR_SELL_ALREADY_ABSENT_" + intent.reason,
                replacement_peer=None,
            )

    buys = tuple(
        sorted(
            effective_buys.values(),
            key=lambda x: (int(x.rank_consensus or 10**9), x.ticker),
        )
    )
    sells = tuple(sorted(effective_sells.values(), key=lambda x: x.ticker))
    return buys, sells


def prepare_execution_v1_from_decision_v2(
    verified_plan: VerifiedDecisionV2SizingPlan,
    paper_state: PaperPortfolioState,
    *,
    eod_inputs: VerifiedEODExecutionInputs,
) -> ExecutionOrderPlan:
    """Prepare unchanged Execution V1 mechanics from a verified Decision V2 plan."""

    plan = _require_verified_v2(verified_plan)
    if (
        not isinstance(eod_inputs, VerifiedEODExecutionInputs)
        or eod_inputs._verification_token is not _EOD_INPUT_TOKEN
    ):
        raise DecisionV1Error("EXECUTION_V1_VERIFIED_EOD_INPUT_REQUIRED")
    if eod_inputs.session_date != plan.decision_session_date:
        raise DecisionV2Error("EXECUTION_V1_DECISION_V2_EOD_SESSION_MISMATCH")
    if paper_state.as_of_session_date != plan.decision_session_date:
        raise DecisionV2Error(
            "EXECUTION_V1_DECISION_V2_PAPER_STATE_SESSION_MISMATCH:"
            f"STATE={paper_state.as_of_session_date}:DECISION={plan.decision_session_date}"
        )

    cash, positions, pending_buys, pending_sells = normalize_state(paper_state)
    if paper_state.reconciliation_required:
        raise DecisionV1Error("EXECUTION_V1_PRIOR_RECONCILIATION_REQUIRED")

    effective_buys, effective_sells = _reconcile_effective_intents_v2(
        plan,
        positions,
        pending_buys,
        pending_sells,
    )

    involved = set(positions) | set(plan.target_positions)
    missing_close = involved - set(eod_inputs.raw_close_prices)
    if missing_close:
        raise DecisionV1Error(
            f"EXECUTION_V1_VERIFIED_CLOSE_MISSING:{sorted(missing_close)}"
        )
    closes = {ticker: float(eod_inputs.raw_close_prices[ticker]) for ticker in involved}
    eod_nav = cash + sum(
        shares * closes[ticker] for ticker, shares in positions.items()
    )
    if eod_nav <= 0:
        raise DecisionV1Error("EXECUTION_V1_EOD_NAV_INVALID")

    sells: list[PlannedSell] = []
    projected_cash = cash
    for intent in effective_sells:
        shares = positions.get(intent.ticker, 0)
        if shares <= 0:
            raise DecisionV1Error("EXECUTION_V1_EFFECTIVE_SELL_WITHOUT_POSITION")
        sells.append(
            PlannedSell(
                ticker=intent.ticker,
                shares=shares,
                rank_consensus=intent.rank_consensus,
                reason=intent.reason,
                replacement_peer=intent.replacement_peer,
            )
        )
        effective = sell_effective_price(closes[intent.ticker])
        gross = shares * effective
        projected_cash += gross - fee(gross, SELL_FEE_BPS)

    projected_cash = min(projected_cash, eod_nav)
    sizing_plan = _size_entries_core(
        decision_session_date=plan.decision_session_date,
        target_positions=plan.target_positions,
        intents=effective_buys,
        nav_idr=eod_nav,
        available_cash_idr=projected_cash,
        reference_prices=closes,
    )
    if sizing_plan._verification_token is not _SIZING_PLAN_TOKEN:
        raise DecisionV1Error("EXECUTION_V1_SIZING_PLAN_NOT_VERIFIED")

    return ExecutionOrderPlan(
        decision_session_date=plan.decision_session_date,
        execution_session_date=eod_inputs.next_official_session_date,
        state_hash=paper_state_hash(paper_state),
        eod_nav_idr=float(eod_nav),
        projected_cash_for_sizing_idr=float(projected_cash),
        sizing_plan=sizing_plan,
        sells=tuple(sells),
        effective_buy_intents=effective_buys,
        target_positions=plan.target_positions,
        regular_market_values_t={
            ticker: float(eod_inputs.regular_market_values.get(ticker, 0.0))
            for ticker in involved
        },
        eod_ohlcv_sha256=eod_inputs.ohlcv_artifact_sha256,
        eod_model_input_sha256=eod_inputs.model_input_sha256,
        official_calendar_sha256=eod_inputs.official_calendar_sha256,
        _verification_token=_EXECUTION_PLAN_TOKEN,
    )


__all__ = [
    "prepare_execution_v1_from_decision_v2",
]
