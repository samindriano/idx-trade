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
from idx_trade.v4_x1_execution_v1 import PaperPortfolioState, prepare_execution_v1, execute_open_v1


def _decision(tickers):
    plan = DecisionPlan(
        "2026-08-21",
        "OFFICIAL_OPEN_T_PLUS_1",
        (),
        tuple(tickers),
        tuple(
            TradeIntent("BUY_INTENT", ticker, rank, "FILL_VACANCY_TOP10")
            for rank, ticker in enumerate(tickers, 1)
        ),
        (),
        (),
        0,
    )
    return VerifiedDecisionPlan(
        plan,
        plan.decision_session_date,
        "synthetic-score-sha",
        _verification_token=_VERIFIED_DECISION_PLAN_TOKEN,
    )


def test_low_price_fee_pressure_does_not_zero_entire_batch():
    tickers = tuple(f"L{i:02d}" for i in range(1, 11))
    decision = _decision(tickers)
    state = PaperPortfolioState("2026-08-21", 50_000_000, ())
    closes = {ticker: 50.0 for ticker in tickers}
    values = {ticker: 1_000_000_000_000.0 for ticker in tickers}
    eod = VerifiedEODExecutionInputs(
        "2026-08-21", "2026-08-24", closes, values,
        Path("eod.parquet"), "a" * 64,
        Path("model.parquet"), "b" * 64,
        Path("calendar.csv"), "c" * 64,
        _verification_token=_EOD_INPUT_TOKEN,
    )
    order = prepare_execution_v1(decision, state, eod_inputs=eod)
    open_inputs = VerifiedOpenExecutionInputs(
        "2026-08-24", closes, frozenset(tickers),
        Path("open.parquet"), "d" * 64,
        _verification_token=_OPEN_INPUT_TOKEN,
    )
    ca = VerifiedCorporateActionAttestation(
        "2026-08-21", "2026-08-24", frozenset(tickers), "NO_RELEVANT_EVENTS",
        Path("ca.json"), "e" * 64,
        Path("source.csv"), "f" * 64,
        _verification_token=_CA_ATTESTATION_TOKEN,
    )
    result = execute_open_v1(order, state, open_inputs=open_inputs, ca_attestation=ca)
    assert len(result.state_after.positions) == 10
    assert all(position.shares > 0 for position in result.state_after.positions)
    assert result.state_after.cash_idr < 100_000
    assert not result.state_after.pending_buys
