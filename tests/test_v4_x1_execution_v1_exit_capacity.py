from pathlib import Path

from idx_trade.v4_x1_decision_v1_contract import DecisionPlan, TradeIntent
from idx_trade.v4_x1_sizing_v1 import VerifiedDecisionPlan, _VERIFIED_DECISION_PLAN_TOKEN
from idx_trade.v4_x1_execution_v1_verify import (
    VerifiedCorporateActionAttestation,
    VerifiedEODExecutionInputs,
    VerifiedOpenExecutionInputs,
    _CA_ATTESTATION_TOKEN,
    _EOD_INPUT_TOKEN,
    _OPEN_INPUT_TOKEN,
)
from idx_trade.v4_x1_execution_v1 import PaperPortfolioState, PaperPosition, prepare_execution_v1, execute_open_v1


def test_sell_capacity_can_partial_fill_and_blocks_paired_buy():
    plan = DecisionPlan(
        "2026-08-21",
        "OFFICIAL_OPEN_T_PLUS_1",
        ("AAA",),
        ("BBB",),
        (TradeIntent("BUY_INTENT", "BBB", 1, "RANK_GAP_REPLACEMENT", "AAA"),),
        (TradeIntent("SELL_INTENT", "AAA", 21, "RANK_GAP_REPLACEMENT", "BBB"),),
        (),
        0,
    )
    decision = VerifiedDecisionPlan(
        plan, plan.decision_session_date, "synthetic-score-sha",
        _verification_token=_VERIFIED_DECISION_PLAN_TOKEN,
    )
    state = PaperPortfolioState(
        "2026-08-21", 45_000_000, (PaperPosition("AAA", 5000),)
    )
    eod = VerifiedEODExecutionInputs(
        "2026-08-21", "2026-08-24",
        {"AAA": 1000.0, "BBB": 1000.0},
        {"AAA": 100_000_000.0, "BBB": 1_000_000_000_000.0},
        Path("eod.parquet"), "a" * 64,
        Path("model.parquet"), "b" * 64,
        Path("calendar.csv"), "c" * 64,
        _verification_token=_EOD_INPUT_TOKEN,
    )
    order = prepare_execution_v1(decision, state, eod_inputs=eod)
    open_inputs = VerifiedOpenExecutionInputs(
        "2026-08-24",
        {"AAA": 1000.0, "BBB": 1000.0},
        frozenset({"AAA", "BBB"}),
        Path("open.parquet"), "d" * 64,
        _verification_token=_OPEN_INPUT_TOKEN,
    )
    ca = VerifiedCorporateActionAttestation(
        "2026-08-21", "2026-08-24", frozenset({"AAA", "BBB"}),
        "NO_RELEVANT_EVENTS", Path("ca.json"), "e" * 64,
        Path("source.csv"), "f" * 64,
        _verification_token=_CA_ATTESTATION_TOKEN,
    )
    result = execute_open_v1(order, state, open_inputs=open_inputs, ca_attestation=ca)
    sell = next(fill for fill in result.fills if fill.side == "SELL")
    buy = next(fill for fill in result.fills if fill.side == "BUY")

    assert 0 < sell.filled_shares < sell.planned_shares
    assert sell.gross_notional <= 1_000_000 + 1e-6
    assert sell.status == "SIMULATED_PARTIAL_EXIT_CAPACITY_FILL_PENDING"
    assert buy.filled_shares == 0
    assert "BLOCKED_BY_UNRESOLVED_PAIRED_SELL" in buy.status
    assert [row.ticker for row in result.state_after.pending_sells] == ["AAA"]
    assert [row.ticker for row in result.state_after.pending_buys] == ["BBB"]
    assert {position.ticker for position in result.state_after.positions} == {"AAA"}
