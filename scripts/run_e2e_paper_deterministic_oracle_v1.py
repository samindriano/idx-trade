"""Deterministic economic oracles for the frozen E2E paper contracts.

This is deliberately separate from the production-artifact replay.  It uses
synthetic, token-gated inputs to assert exact state/economic results for the
already-frozen Decision V2, Sizing V1 and Execution V1 policies.  It never
opens providers, outcome artifacts, or scheduler/runtime data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade import forward_dividend_v1 as dividend
from idx_trade import forward_dividend_orchestration_v1 as orchestration
import idx_trade.e2e_paper_orchestration_v1 as e2e_orchestration_module
import idx_trade.v4_x1_execution_v1_verify as execution_verify_module
from idx_trade.decision_v2_minimal import DecisionV2Intent, DecisionV2Plan
from idx_trade.e2e_paper_orchestration_v1 import _canonical_hash, bootstrap_t0
from idx_trade.v4_x1_decision_v1_contract import DecisionPlan, TradeIntent
from idx_trade.v4_x1_decision_v2_minimal import V4_X1_DECISION_V2_MINIMAL_PROFILE_V1
from idx_trade.v4_x1_execution_v1 import execute_open_v1, prepare_execution_v1
from idx_trade.v4_x1_execution_v1_contract import (
    PaperPortfolioState,
    PaperPosition,
    PendingPaperIntent,
    STAMP_DUTY_THRESHOLD_IDR,
)
from idx_trade.v4_x1_execution_v1_decision_v2_adapter import prepare_execution_v1_from_decision_v2
from idx_trade.v4_x1_execution_v1_verify import (
    VerifiedCorporateActionAttestation,
    VerifiedEODExecutionInputs,
    VerifiedOpenExecutionInputs,
    _CA_ATTESTATION_TOKEN,
    _EOD_INPUT_TOKEN,
    _OPEN_INPUT_TOKEN,
)
from idx_trade.v4_x1_sizing_v1 import VerifiedDecisionPlan, _VERIFIED_DECISION_PLAN_TOKEN
from idx_trade.v4_x1_sizing_v1_decision_v2_adapter import (
    VerifiedDecisionV2SizingPlan,
    _VERIFIED_DECISION_V2_SIZING_PLAN_TOKEN,
)
from idx_trade.e2e_replay_boundary_v1 import replay_boundary_static_audit_v1


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _state(date: str, cash: float = 50_000_000.0, positions: dict[str, int] | None = None) -> PaperPortfolioState:
    return PaperPortfolioState(
        date,
        cash,
        tuple(PaperPosition(ticker, shares) for ticker, shares in sorted((positions or {}).items())),
        (),
        (),
    )


def _decision(
    date: str,
    target: tuple[str, ...],
    *,
    current: tuple[str, ...] = (),
    buys: tuple[tuple[str, int, str, str | None], ...] = (),
    sells: tuple[tuple[str, int, str, str | None], ...] = (),
) -> VerifiedDecisionPlan:
    plan = DecisionPlan(
        date,
        "OFFICIAL_OPEN_T_PLUS_1",
        current,
        target,
        tuple(TradeIntent("BUY_INTENT", *row) for row in buys),
        tuple(TradeIntent("SELL_INTENT", *row) for row in sells),
        tuple(ticker for ticker in target if ticker in current),
        0,
    )
    return VerifiedDecisionPlan(
        plan,
        date,
        "synthetic-score-artifact-sha",
        _verification_token=_VERIFIED_DECISION_PLAN_TOKEN,
    )


def _eod(date: str, next_date: str, closes: dict[str, float], values: dict[str, float] | None = None) -> VerifiedEODExecutionInputs:
    return VerifiedEODExecutionInputs(
        date,
        next_date,
        closes,
        values or {ticker: 1_000_000_000.0 for ticker in closes},
        Path("synthetic-eod-ohlcv.parquet"),
        "a" * 64,
        Path("synthetic-model-input.parquet"),
        "b" * 64,
        Path("synthetic-calendar.csv"),
        "c" * 64,
        _verification_token=_EOD_INPUT_TOKEN,
    )


def _open(date: str, prices: dict[str, float]) -> VerifiedOpenExecutionInputs:
    return VerifiedOpenExecutionInputs(
        date,
        prices,
        frozenset(prices),
        Path("synthetic-open.parquet"),
        "d" * 64,
        _verification_token=_OPEN_INPUT_TOKEN,
    )


def _ca(date: str, next_date: str, tickers: tuple[str, ...]) -> VerifiedCorporateActionAttestation:
    return VerifiedCorporateActionAttestation(
        date,
        next_date,
        frozenset(tickers),
        "NO_RELEVANT_EVENTS",
        Path("synthetic-ca.json"),
        "e" * 64,
        Path("synthetic-ca-source.csv"),
        "f" * 64,
        _verification_token=_CA_ATTESTATION_TOKEN,
    )


def _fill_payload(result: object) -> dict[str, object]:
    fill = result.fills[0]
    return {
        "ticker": fill.ticker,
        "side": fill.side,
        "planned_shares": fill.planned_shares,
        "filled_shares": fill.filled_shares,
        "raw_open": fill.raw_open,
        "effective_price": fill.effective_price,
        "gross_notional": fill.gross_notional,
        "fee_idr": fill.fee_idr,
        "cash_effect_idr": fill.cash_effect_idr,
    }


def _run_cost_capacity_scenarios() -> dict[str, object]:
    buy = _decision(
        "2026-08-24",
        ("AAA",),
        buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),),
    )
    state = _state("2026-08-24")
    order = prepare_execution_v1(
        buy,
        state,
        eod_inputs=_eod("2026-08-24", "2026-08-25", {"AAA": 1_000.0}),
    )
    result = execute_open_v1(
        order,
        state,
        open_inputs=_open("2026-08-25", {"AAA": 1_000.0}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ("AAA",)),
    )
    if not result.fills or result.fills[0].filled_shares <= 0:
        raise RuntimeError("ORACLE_COST_CAPACITY_NO_FILL")
    fill = _fill_payload(result)
    if fill["filled_shares"] % 100 != 0:
        raise RuntimeError("ORACLE_LOT_SIZE_FAILED")
    if abs(float(fill["effective_price"]) - 1001.0) > 1e-9:
        raise RuntimeError("ORACLE_BUY_SLIPPAGE_FAILED")
    if abs(float(fill["fee_idr"]) - float(fill["gross_notional"]) * 0.0015) > 1e-6:
        raise RuntimeError("ORACLE_BUY_FEE_FAILED")

    stamp = result.stamp_duty_idr
    if abs(stamp - (10_000.0 if result.gross_turnover_idr > STAMP_DUTY_THRESHOLD_IDR else 0.0)) > 1e-6:
        raise RuntimeError("ORACLE_STAMP_THRESHOLD_FAILED")

    threshold_decision = _decision(
        "2026-08-24",
        ("AAA", "BBB"),
        buys=(
            ("AAA", 1, "FILL_VACANCY_TOP10", None),
            ("BBB", 2, "FILL_VACANCY_TOP10", None),
        ),
    )
    threshold_state = _state("2026-08-24")
    threshold_order = prepare_execution_v1(
        threshold_decision,
        threshold_state,
        eod_inputs=_eod(
            "2026-08-24", "2026-08-25", {"AAA": 1_000.0, "BBB": 1_000.0}
        ),
    )
    threshold_result = execute_open_v1(
        threshold_order,
        threshold_state,
        open_inputs=_open("2026-08-25", {"AAA": 1_000.0, "BBB": 1_000.0}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ("AAA", "BBB")),
    )
    if threshold_result.gross_turnover_idr < 10_000_000.0 or threshold_result.stamp_duty_idr != 10_000.0:
        raise RuntimeError("ORACLE_STAMP_THRESHOLD_PLUS_ONE_FAILED")

    equal_decision = _decision(
        "2026-08-24",
        (),
        current=("EQUAL",),
        sells=(("EQUAL", 1, "CONFIRMED_EXIT", None),),
    )
    equal_state = _state("2026-08-24", positions={"EQUAL": 10_000})
    equal_order = prepare_execution_v1(
        equal_decision,
        equal_state,
        eod_inputs=_eod("2026-08-24", "2026-08-25", {"EQUAL": 1_000.0}),
    )
    equal_raw_open = 1_000.0 / (1.0 - 0.001)
    equal_result = execute_open_v1(
        equal_order,
        equal_state,
        open_inputs=_open("2026-08-25", {"EQUAL": equal_raw_open}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ("EQUAL",)),
    )
    if abs(equal_result.gross_turnover_idr - STAMP_DUTY_THRESHOLD_IDR) > 1e-5:
        raise RuntimeError("ORACLE_STAMP_THRESHOLD_EQUALITY_INPUT_FAILED")
    if equal_result.stamp_duty_idr != 0.0:
        raise RuntimeError("ORACLE_STAMP_THRESHOLD_EQUALITY_FAILED")

    capacity_decision = _decision(
        "2026-08-24",
        ("CAP",),
        buys=(("CAP", 1, "FILL_VACANCY_TOP10", None),),
    )
    capacity_state = _state("2026-08-24")
    capacity_order = prepare_execution_v1(
        capacity_decision,
        capacity_state,
        eod_inputs=_eod(
            "2026-08-24", "2026-08-25", {"CAP": 1_000.0}, {"CAP": 100_000_000.0}
        ),
    )
    capacity_result = execute_open_v1(
        capacity_order,
        capacity_state,
        open_inputs=_open("2026-08-25", {"CAP": 1_000.0}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ("CAP",)),
    )
    capacity_fill = next(fill for fill in capacity_result.fills if fill.side == "BUY")
    if capacity_fill.gross_notional > 1_000_000.0 + 1e-6 or capacity_fill.filled_shares % 100 != 0:
        raise RuntimeError("ORACLE_ONE_PERCENT_CAPACITY_FAILED")

    sell_decision = _decision(
        "2026-08-24",
        (),
        current=("SELL",),
        sells=(("SELL", 1, "CONFIRMED_EXIT", None),),
    )
    sell_state = _state("2026-08-24", positions={"SELL": 10_000})
    sell_order = prepare_execution_v1(
        sell_decision,
        sell_state,
        eod_inputs=_eod(
            "2026-08-24", "2026-08-25", {"SELL": 1_000.0}, {"SELL": 1_000_000_000.0}
        ),
    )
    sell_result = execute_open_v1(
        sell_order,
        sell_state,
        open_inputs=_open("2026-08-25", {"SELL": 1_000.0}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ("SELL",)),
    )
    sell_fill = next(fill for fill in sell_result.fills if fill.side == "SELL")
    if sell_fill.filled_shares != 10_000 or abs(sell_fill.effective_price - 999.0) > 1e-9:
        raise RuntimeError("ORACLE_SELL_SLIPPAGE_OR_LOT_FAILED")
    if abs(sell_fill.fee_idr - sell_fill.gross_notional * 0.0025) > 1e-6:
        raise RuntimeError("ORACLE_SELL_FEE_FAILED")
    if sell_result.gross_turnover_idr != sell_fill.gross_notional or sell_result.stamp_duty_idr != 0.0:
        raise RuntimeError("ORACLE_SELL_BELOW_THRESHOLD_STAMP_FAILED")

    sell_threshold_state = _state("2026-08-24", positions={"SELL": 10_200})
    sell_threshold_order = prepare_execution_v1(
        sell_decision,
        sell_threshold_state,
        eod_inputs=_eod(
            "2026-08-24", "2026-08-25", {"SELL": 1_000.0}, {"SELL": 2_000_000_000.0}
        ),
    )
    sell_threshold_result = execute_open_v1(
        sell_threshold_order,
        sell_threshold_state,
        open_inputs=_open("2026-08-25", {"SELL": 1_000.0}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ("SELL",)),
    )
    if sell_threshold_result.gross_turnover_idr <= 10_000_000.0 or sell_threshold_result.stamp_duty_idr != 10_000.0:
        raise RuntimeError("ORACLE_SELL_ABOVE_THRESHOLD_STAMP_FAILED")
    return {
        "status": "PASS",
        "fill": fill,
        "cash_after": result.state_after.cash_idr,
        "gross_turnover_idr": result.gross_turnover_idr,
        "stamp_duty_idr": stamp,
        "threshold_plus_one_stamp_duty_idr": threshold_result.stamp_duty_idr,
        "threshold_plus_one_turnover_idr": threshold_result.gross_turnover_idr,
        "threshold_equal_turnover_idr": equal_result.gross_turnover_idr,
        "threshold_equal_stamp_duty_idr": equal_result.stamp_duty_idr,
        "capacity_gross_notional_idr": capacity_fill.gross_notional,
        "capacity_filled_shares": capacity_fill.filled_shares,
        "sell_below_threshold": {
            "filled_shares": sell_fill.filled_shares,
            "effective_price": sell_fill.effective_price,
            "gross_notional": sell_fill.gross_notional,
            "fee_idr": sell_fill.fee_idr,
            "stamp_duty_idr": sell_result.stamp_duty_idr,
        },
        "sell_above_threshold_stamp_duty_idr": sell_threshold_result.stamp_duty_idr,
        "positions_after": [(row.ticker, row.shares) for row in result.state_after.positions],
        "pending_buys_after": [row.ticker for row in result.state_after.pending_buys],
        "pending_sells_after": [row.ticker for row in result.state_after.pending_sells],
    }


def _event() -> dividend.CertifiedCashDividend:
    return dividend.CertifiedCashDividend(
        event_id="CASH_DIVIDEND_AAA_ORACLE_001",
        ticker="AAA",
        announcement_timestamp="2026-08-25T12:00:00+07:00",
        knowledge_at_timestamp="2026-08-25T12:00:00+07:00",
        gross_dividend_per_share_idr=25.0,
        cum_date="2026-08-25",
        ex_date="2026-08-26",
        record_date="2026-08-26",
        payment_date="2026-08-28",
        source_evidence_sha256="a" * 64,
    )


def _run_dividend_lifecycle_scenarios() -> dict[str, object]:
    event = _event()
    held = dividend.DividendAwarePaperState(
        _state("2026-08-25", cash=1_000_000.0, positions={"AAA": 5_000}), dividend.DividendLedger()
    )
    cum = dividend.process_dividend_eod(held, (event,), session_date="2026-08-25")
    if [row.entitled_shares for row in cum.dividend_ledger.entitlements] != [5_000]:
        raise RuntimeError("ORACLE_CUM_ENTITLEMENT_FAILED")

    sold_on_cum = dividend.DividendAwarePaperState(
        _state("2026-08-25", cash=1_000_000.0), dividend.DividendLedger()
    )
    sold_cum = dividend.process_dividend_eod(
        sold_on_cum, (event,), session_date="2026-08-25"
    )
    if sold_cum.dividend_ledger.entitlements:
        raise RuntimeError("ORACLE_SELL_ON_CUM_ENTITLEMENT_FAILED")

    ex = dividend.DividendAwarePaperState(
        _state("2026-08-26", cash=1_000_000.0, positions={"AAA": 5_000}), cum.dividend_ledger
    )
    ex = dividend.process_dividend_eod(ex, (event,), session_date="2026-08-26")
    sold_ex = dividend.DividendAwarePaperState(
        _state("2026-08-26", cash=1_000_000.0), cum.dividend_ledger
    )
    sold_ex = dividend.process_dividend_eod(sold_ex, (event,), session_date="2026-08-26")
    if len(ex.dividend_ledger.receivables) != 1 or ex.dividend_ledger.receivables[0].gross_amount_idr != 125_000.0:
        raise RuntimeError("ORACLE_EX_RECEIVABLE_FAILED")
    if not sold_ex.dividend_ledger.receivables:
        raise RuntimeError("ORACLE_SELL_ON_EX_CLAIM_FAILED")
    if dividend.paper_total_return_nav_idr(ex, {"AAA": 1_000.0}) != 6_125_000.0:
        raise RuntimeError("ORACLE_TOTAL_RETURN_NAV_FAILED")
    if ex.base_state.cash_idr != 1_000_000.0:
        raise RuntimeError("ORACLE_RECEIVABLE_SPENDABLE_CASH_FAILED")

    bought_on_ex = dividend.DividendAwarePaperState(
        _state("2026-08-26", cash=1_000_000.0, positions={"AAA": 5_000}), dividend.DividendLedger()
    )
    bought_ex = dividend.process_dividend_eod(
        bought_on_ex,
        (event,),
        session_date="2026-08-26",
        historical_states_by_date={"2026-08-25": sold_on_cum},
    )
    if bought_ex.dividend_ledger.receivables or bought_ex.dividend_ledger.entitlements:
        raise RuntimeError("ORACLE_BUY_ON_EX_ENTITLEMENT_FAILED")

    payment = dividend.DividendAwarePaperState(
        _state("2026-08-28", cash=1_000_000.0), ex.dividend_ledger
    )
    payment = dividend.process_dividend_eod(payment, (event,), session_date="2026-08-28")
    if payment.base_state.cash_idr != 1_125_000.0 or len(payment.dividend_ledger.settlements) != 1:
        raise RuntimeError("ORACLE_PAYMENT_SETTLEMENT_FAILED")
    replayed = dividend.process_dividend_eod(payment, (event,), session_date="2026-08-28")
    if dividend.dividend_aware_state_hash(replayed) != dividend.dividend_aware_state_hash(payment):
        raise RuntimeError("ORACLE_PAYMENT_IDEMPOTENCY_FAILED")

    late = dividend.process_dividend_eod(
        dividend.DividendAwarePaperState(_state("2026-08-26"), dividend.DividendLedger()),
        (event,),
        session_date="2026-08-26",
        historical_states_by_date={"2026-08-25": held},
    )
    if not late.dividend_ledger.receivables:
        raise RuntimeError("ORACLE_LATE_KNOWN_RECONCILIATION_FAILED")
    return {
        "status": "PASS",
        "cum_entitled_shares": 5_000,
        "sell_on_cum_entitled_shares": 0,
        "buy_on_ex_entitled_shares": 0,
        "ex_receivable_idr": 125_000.0,
        "total_return_nav_idr": 6_125_000.0,
        "spendable_cash_idr": ex.base_state.cash_idr,
        "payment_cash_idr": payment.base_state.cash_idr,
        "settlement_count_after_replay": len(replayed.dividend_ledger.settlements),
        "late_known_receivable_idr": late.dividend_ledger.receivables[0].gross_amount_idr,
    }


def _run_pending_scenarios() -> dict[str, object]:
    decision = _decision(
        "2026-08-24",
        ("AAA",),
        buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),),
    )
    state = _state("2026-08-24")
    order = prepare_execution_v1(
        decision,
        state,
        eod_inputs=_eod("2026-08-24", "2026-08-25", {"AAA": 100_000.0}),
    )
    missing_open = _open("2026-08-25", {})
    first = execute_open_v1(
        order,
        state,
        open_inputs=missing_open,
        ca_attestation=_ca("2026-08-24", "2026-08-25", ("AAA",)),
    )
    if [row.ticker for row in first.state_after.pending_buys] != ["AAA"]:
        raise RuntimeError("ORACLE_MISSING_OPEN_PENDING_BUY_FAILED")
    resolved_order = prepare_execution_v1(
        _decision("2026-08-25", ("AAA",), current=(), buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),)),
        first.state_after,
        eod_inputs=_eod("2026-08-25", "2026-08-26", {"AAA": 1_000.0}),
    )
    resolved = execute_open_v1(
        resolved_order,
        first.state_after,
        open_inputs=_open("2026-08-26", {"AAA": 1_000.0}),
        ca_attestation=_ca("2026-08-25", "2026-08-26", ("AAA",)),
    )
    if any(row.ticker == "AAA" for row in resolved.state_after.pending_buys):
        raise RuntimeError("ORACLE_PENDING_BUY_RESOLUTION_FAILED")

    sell_decision = _decision(
        "2026-08-24",
        (),
        current=("SELLP",),
        sells=(("SELLP", 1, "CONFIRMED_EXIT", None),),
    )
    sell_state = _state("2026-08-24", positions={"SELLP": 5_000})
    sell_order = prepare_execution_v1(
        sell_decision,
        sell_state,
        eod_inputs=_eod("2026-08-24", "2026-08-25", {"SELLP": 1_000.0}),
    )
    sell_first = execute_open_v1(
        sell_order,
        sell_state,
        open_inputs=_open("2026-08-25", {}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ("SELLP",)),
    )
    if [row.ticker for row in sell_first.state_after.pending_sells] != ["SELLP"]:
        raise RuntimeError("ORACLE_MISSING_OPEN_PENDING_SELL_FAILED")
    sell_retry_order = prepare_execution_v1(
        _decision("2026-08-25", (), current=("SELLP",)),
        sell_first.state_after,
        eod_inputs=_eod("2026-08-25", "2026-08-26", {"SELLP": 1_000.0}),
    )
    sell_resolved = execute_open_v1(
        sell_retry_order,
        sell_first.state_after,
        open_inputs=_open("2026-08-26", {"SELLP": 1_000.0}),
        ca_attestation=_ca("2026-08-25", "2026-08-26", ("SELLP",)),
    )
    if any(row.ticker == "SELLP" for row in sell_resolved.state_after.pending_sells):
        raise RuntimeError("ORACLE_PENDING_SELL_RESOLUTION_FAILED")
    if any(row.ticker == "SELLP" for row in sell_resolved.state_after.positions):
        raise RuntimeError("ORACLE_PENDING_SELL_POSITION_REMAINS_FAILED")

    # A paired replacement must not be falsely blocked when the SELL peer was
    # only a never-filled pending BUY. This exercises the real Decision V2
    # adapter path, which cancels the impossible SELL and clears the peer.
    paired_state = PaperPortfolioState(
        "2026-08-24",
        50_000_000.0,
        (),
        (PendingPaperIntent("BUY", "AAA", 5, "MARKET_ENTRY_UNAVAILABLE"),),
        (),
    )
    paired_plan = DecisionV2Plan(
        decision_session_date="2026-08-24",
        current_shadow_positions=("AAA",),
        target_positions=("BBB",),
        buy_intents=(DecisionV2Intent("BUY_INTENT", "BBB", 1, "SOFT_RANK_GAP_REPLACEMENT", "AAA"),),
        sell_intents=(DecisionV2Intent("SELL_INTENT", "AAA", 21, "SOFT_RANK_GAP_REPLACEMENT", "BBB"),),
        hold_tickers=(),
        incumbent_observations=(),
        challenger_observations=(),
        unfilled_slots=9,
        capacity_state="UNFILLED_NO_QUALIFIED_CHALLENGER",
        rule_id=V4_X1_DECISION_V2_MINIMAL_PROFILE_V1.rule_id,
        bootstrap=False,
    )
    paired_verified = VerifiedDecisionV2SizingPlan(
        plan=paired_plan,
        current_score_session_date="2026-08-24",
        current_score_artifact_sha256="g" * 64,
        previous_score_session_date="2026-08-21",
        previous_score_artifact_sha256="h" * 64,
        _verification_token=_VERIFIED_DECISION_V2_SIZING_PLAN_TOKEN,
    )
    paired_order = prepare_execution_v1_from_decision_v2(
        paired_verified,
        paired_state,
        eod_inputs=_eod("2026-08-24", "2026-08-25", {"BBB": 1_000.0}),
    )
    if paired_order.effective_buy_intents[0].replacement_peer is not None:
        raise RuntimeError("ORACLE_PAIRED_REPLACEMENT_PEER_NOT_CLEARED")
    if not paired_order.effective_buy_intents[0].reason.startswith("PAPER_PAIR_SELL_ALREADY_ABSENT_"):
        raise RuntimeError("ORACLE_PAIRED_REPLACEMENT_REASON_NOT_EXPLICIT")
    paired_result = execute_open_v1(
        paired_order,
        paired_state,
        open_inputs=_open("2026-08-25", {"BBB": 1_000.0}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ("AAA", "BBB")),
    )
    if any(row.ticker == "BBB" for row in paired_result.state_after.pending_buys):
        raise RuntimeError("ORACLE_PAIRED_REPLACEMENT_FALSE_BLOCK_FAILED")
    if any(row.ticker == "AAA" for row in paired_result.state_after.pending_sells):
        raise RuntimeError("ORACLE_UNHELD_SELL_PEER_CREATED_PENDING_FAILED")
    return {
        "status": "PASS",
        "first_pending_buys": [row.ticker for row in first.state_after.pending_buys],
        "resolved_pending_buys": [row.ticker for row in resolved.state_after.pending_buys],
        "resolved_positions": [(row.ticker, row.shares) for row in resolved.state_after.positions],
        "first_pending_sells": [row.ticker for row in sell_first.state_after.pending_sells],
        "resolved_pending_sells": [row.ticker for row in sell_resolved.state_after.pending_sells],
        "resolved_sell_positions": [(row.ticker, row.shares) for row in sell_resolved.state_after.positions],
        "paired_replacement_buy_resolved": True,
        "unheld_sell_peer_pending": [row.ticker for row in paired_result.state_after.pending_sells],
    }


def _run_blocker_recovery_scenario() -> dict[str, object]:
    blocker = orchestration.BlockingDividendJournalEntry(
        "A1", "AAA", "AMBIGUOUS_DIVIDEND_CANDIDATE"
    )
    prior = orchestration.DividendAcquisitionJournal(
        as_of_date="2026-08-24",
        required_tickers=("AAA",),
        coverage=(),
        blockers=(blocker,),
    )
    resolution = orchestration.DividendBlockerResolutionEntry(
        blocker_announcement_identity="A1",
        blocker_ticker="AAA",
        blocker_classification="AMBIGUOUS_DIVIDEND_CANDIDATE",
        resolver_announcement_identity="A1",
        resolver_ticker="AAA",
        resolver_event_id="E1",
        resolver_event_sha256="a" * 64,
        resolver_evidence_dir="C:/synthetic-evidence",
        resolver_review_sha256="b" * 64,
        resolver_status=orchestration.BLOCKER_RESOLUTION_CERTIFIED_LIVE,
        resolution_kind="SAME_ANNOUNCEMENT_RECOVERY",
    )
    certified = orchestration.CertifiedDividendJournalEntry(
        "A1", "AAA", "E1", "a" * 64, "C:/synthetic-evidence", "b" * 64
    )
    merged = orchestration.merge_journal_state(
        prior_journal=prior,
        as_of_date="2026-08-25",
        capture_phase=orchestration.PREOPEN,
        required_tickers=("AAA",),
        coverage=(),
        current_certified=(certified,),
        current_blocker_resolutions=(resolution,),
    )
    if orchestration.unresolved_blockers_for_tickers(merged, ("AAA",)):
        raise RuntimeError("ORACLE_SAME_ANNOUNCEMENT_BLOCKER_NOT_RESOLVED")
    unrelated_live = orchestration.DividendAcquisitionJournal(
        as_of_date="2026-08-25",
        required_tickers=("AAA",),
        coverage=(),
        certified_events=(certified,),
        blockers=(
            orchestration.BlockingDividendJournalEntry(
                "A2", "AAA", "BLOCKED_LIVE_UNRESOLVED"
            ),
        ),
    )
    visible = orchestration.unresolved_blockers_for_tickers(unrelated_live, ("AAA",))
    if [row.announcement_identity for row in visible] != ["A2"]:
        raise RuntimeError("ORACLE_CERTIFIED_EVENT_HID_LIVE_BLOCKER")
    return {
        "status": "PASS",
        "blocker_identity": "A1",
        "resolution_kind": "SAME_ANNOUNCEMENT_RECOVERY",
        "unresolved_after": [],
        "certified_event_ids": [row.event_id for row in merged.certified_events],
        "unrelated_live_blocker_visible": [row.announcement_identity for row in visible],
    }


def run(output_dir: Path) -> Path:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"DETERMINISTIC_ORACLE_OUTPUT_NOT_EMPTY:{output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = bootstrap_t0(output_dir, session_date="2026-08-24")
    scenarios = {
        "cost_capacity_lot_fee_stamp": _run_cost_capacity_scenarios(),
        "dividend_entitlement_receivable_payment": _run_dividend_lifecycle_scenarios(),
        "missing_open_pending_recovery": _run_pending_scenarios(),
        "same_announcement_blocker_recovery": _run_blocker_recovery_scenario(),
    }
    body = {
        "schema_version": "idx_trade_e2e_paper_deterministic_oracle_v1",
        "replay_kind": "DETERMINISTIC_ECONOMIC_ORACLE_REPLAY",
        "synthetic_only": True,
        "scope": {
            **replay_boundary_static_audit_v1(
                (Path(__file__), e2e_orchestration_module.__file__, execution_verify_module.__file__),
                source_kind="synthetic_modules_only",
            ),
            "official_session_contract": "synthetic_weekday_sessions_only",
        },
        "scenarios": scenarios,
        "t0": {"path": str(t0.resolve()), "sha256": _sha(t0)},
        "checks": {
            "explicit_expected_state_oracles": True,
            "fees_slippage_lots_stamp_capacity": True,
            "pending_open_recovery": True,
            "paired_replacement_sell_dependency": True,
            "same_announcement_blocker_recovery": True,
        },
    }
    body["summary_sha256"] = _canonical_hash(body)
    summary = output_dir / "acceptance_summary.json"
    summary.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary = run(Path(args.output_dir).expanduser().resolve())
    print({"status": "DETERMINISTIC_ECONOMIC_ORACLE_REPLAY_PASS", "summary_path": str(summary), "summary_sha256": _sha(summary)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
