import hashlib
import random
from pathlib import Path

import pytest

from idx_trade.v4_x1_decision_v1_contract import DecisionPlan, DecisionV1Error, TradeIntent
from idx_trade.v4_x1_sizing_v1 import VerifiedDecisionPlan, _VERIFIED_DECISION_PLAN_TOKEN
from idx_trade.v4_x1_execution_v1_verify import (
    VerifiedCorporateActionAttestation, VerifiedEODExecutionInputs, VerifiedOpenExecutionInputs,
    _CA_ATTESTATION_TOKEN, _EOD_INPUT_TOKEN, _OPEN_INPUT_TOKEN,
)
from idx_trade.v4_x1_execution_v1 import (
    PaperPortfolioState, PaperPosition, prepare_execution_v1, execute_open_v1,
    verify_execution_v1_config,
)


def _decision(target=(), buys=(), sells=(), current=(), date="2026-08-21"):
    plan = DecisionPlan(
        date, "OFFICIAL_OPEN_T_PLUS_1", tuple(current), tuple(target),
        tuple(TradeIntent("BUY_INTENT", t, r, reason, peer) for t,r,reason,peer in buys),
        tuple(TradeIntent("SELL_INTENT", t, r, reason, peer) for t,r,reason,peer in sells),
        tuple(t for t in target if t in current), 0,
    )
    return VerifiedDecisionPlan(
        plan, plan.decision_session_date, "synthetic-score-sha",
        _verification_token=_VERIFIED_DECISION_PLAN_TOKEN,
    )


def _state(cash, positions, date="2026-08-21", pending_buys=(), pending_sells=()):
    return PaperPortfolioState(
        date, cash, tuple(PaperPosition(t,s) for t,s in positions.items()),
        tuple(pending_buys), tuple(pending_sells),
    )


def _eod(date, next_date, closes, values=None):
    values = values or {t: 1e12 for t in closes}
    return VerifiedEODExecutionInputs(
        date, next_date, closes, values, Path("eod.parquet"), "a"*64,
        Path("model.parquet"), "b"*64, Path("calendar.csv"), "c"*64,
        _verification_token=_EOD_INPUT_TOKEN,
    )


def _open(date, prices):
    return VerifiedOpenExecutionInputs(
        date, prices, frozenset(prices), Path("open.parquet"), "d"*64,
        _verification_token=_OPEN_INPUT_TOKEN,
    )


def _ca(from_date, through_date, tickers):
    return VerifiedCorporateActionAttestation(
        from_date, through_date, frozenset(tickers), "NO_RELEVANT_EVENTS",
        Path("ca.json"), "e"*64, Path("source.csv"), "f"*64,
        _verification_token=_CA_ATTESTATION_TOKEN,
    )


def test_config_hash():
    path = Path(__file__).parents[1] / "config" / "v4_x1_execution_v1.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "9f90b6c846689796f63948a758e0cef8d8a6aac0e119a22806f7b6fb41cbf096"
    verify_execution_v1_config(path)


def test_joint_allocator_removes_old_bootstrap_cash_drag():
    tickers = tuple(f"T{i:02d}" for i in range(1,11))
    decision = _decision(tickers, buys=tuple(
        (t,i,"FILL_VACANCY_TOP10",None) for i,t in enumerate(tickers,1)
    ))
    state = _state(50_000_000,{})
    order = prepare_execution_v1(
        decision, state, eod_inputs=_eod("2026-08-21","2026-08-24",{t:1000 for t in tickers})
    )
    result = execute_open_v1(
        order, state, open_inputs=_open("2026-08-24",{t:1000 for t in tickers}),
        ca_attestation=_ca("2026-08-21","2026-08-24",tickers),
    )
    shares = sorted(x.shares for x in result.state_after.positions)
    assert shares.count(5000) == 8
    assert shares.count(4900) == 2
    assert result.state_after.cash_idr < 100_000
    assert [row.ticker for row in result.state_after.pending_buys] == ["T09", "T10"]
    assert {
        row.canonical_ticker
        for row in result.state_after.obligations
        if row.status == "PARTIAL"
    } == {"T09", "T10"}


def test_positive_partial_buy_is_durable_and_retry_completes_remainder():
    decision = _decision(("AAA",), buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),))
    state = _state(50_000_000, {})
    order = prepare_execution_v1(
        decision,
        state,
        eod_inputs=_eod(
            "2026-08-21",
            "2026-08-24",
            {"AAA": 1000},
            {"AAA": 250_000_000},
        ),
    )
    first = execute_open_v1(
        order,
        state,
        open_inputs=_open("2026-08-24", {"AAA": 1000}),
        ca_attestation=_ca("2026-08-21", "2026-08-24", ["AAA"]),
    )

    assert [row.shares for row in first.state_after.positions] == [2400]
    assert [row.ticker for row in first.state_after.pending_buys] == ["AAA"]
    obligation = first.state_after.obligations[0]
    assert obligation.planned_shares == 5000
    assert obligation.filled_shares == 2400
    assert obligation.remaining_shares == 2600

    retry_decision = _decision(
        ("AAA",),
        current=("AAA",),
        date="2026-08-24",
    )
    retry_order = prepare_execution_v1(
        retry_decision,
        first.state_after,
        eod_inputs=_eod(
            "2026-08-24",
            "2026-08-25",
            {"AAA": 1000},
            {"AAA": 300_000_000},
        ),
    )
    second = execute_open_v1(
        retry_order,
        first.state_after,
        open_inputs=_open("2026-08-25", {"AAA": 1000}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ["AAA"]),
    )

    assert [row.shares for row in second.state_after.positions] == [5000]
    assert not second.state_after.pending_buys
    assert second.state_after.obligations[0].status == "FILLED"
    assert second.state_after.obligations[0].remaining_shares == 0


def test_zero_lot_is_pending_and_retried_without_shadow_change():
    decision = _decision(("AAA",), buys=(("AAA",1,"FILL_VACANCY_TOP10",None),))
    state = _state(50_000_000,{})
    order = prepare_execution_v1(
        decision, state, eod_inputs=_eod("2026-08-21","2026-08-24",{"AAA":100_000})
    )
    result = execute_open_v1(
        order, state, open_inputs=_open("2026-08-24",{"AAA":100_000}),
        ca_attestation=_ca("2026-08-21","2026-08-24",["AAA"]),
    )
    assert [x.ticker for x in result.state_after.pending_buys] == ["AAA"]
    assert not result.reconciliation_required

    next_decision = _decision(("AAA",), current=("AAA",), date="2026-08-24")
    order2 = prepare_execution_v1(
        next_decision, result.state_after,
        eod_inputs=_eod("2026-08-24","2026-08-25",{"AAA":50_000}),
    )
    assert [x.ticker for x in order2.effective_buy_intents] == ["AAA"]


def test_failed_sell_blocks_pair_and_persists_both_transitions():
    state = _state(45_000_000,{"AAA":5000})
    decision = _decision(
        ("BBB",),
        buys=(("BBB",1,"RANK_GAP_REPLACEMENT","AAA"),),
        sells=(("AAA",21,"RANK_GAP_REPLACEMENT","BBB"),),
        current=("AAA",),
    )
    order = prepare_execution_v1(
        decision,state,eod_inputs=_eod("2026-08-21","2026-08-24",{"AAA":1000,"BBB":1000})
    )
    result = execute_open_v1(
        order,state,open_inputs=_open("2026-08-24",{"BBB":1000}),
        ca_attestation=_ca("2026-08-21","2026-08-24",["AAA","BBB"]),
    )
    assert [x.ticker for x in result.state_after.pending_sells] == ["AAA"]
    assert [x.ticker for x in result.state_after.pending_buys] == ["BBB"]
    assert {x.ticker for x in result.state_after.positions} == {"AAA"}


def test_capacity_guard_limits_new_buy_to_one_percent_reference_day_value():
    decision = _decision(("AAA",), buys=(("AAA",1,"FILL_VACANCY_TOP10",None),))
    state = _state(50_000_000,{})
    order = prepare_execution_v1(
        decision,state,eod_inputs=_eod(
            "2026-08-21","2026-08-24",{"AAA":1000},{"AAA":100_000_000}
        )
    )
    result = execute_open_v1(
        order,state,open_inputs=_open("2026-08-24",{"AAA":1000}),
        ca_attestation=_ca("2026-08-21","2026-08-24",["AAA"]),
    )
    fill = next(x for x in result.fills if x.side == "BUY")
    assert fill.gross_notional <= 1_000_000 + 1e-6


def test_plain_ca_boolean_is_rejected():
    decision = _decision(("AAA",), buys=(("AAA",1,"FILL_VACANCY_TOP10",None),))
    state = _state(50_000_000,{})
    order = prepare_execution_v1(
        decision,state,eod_inputs=_eod("2026-08-21","2026-08-24",{"AAA":1000})
    )
    with pytest.raises(DecisionV1Error, match="VERIFIED_CA"):
        execute_open_v1(order,state,open_inputs=_open("2026-08-24",{"AAA":1000}),
                        ca_attestation=True)


def test_unexplained_shadow_paper_divergence_fails_closed():
    decision = _decision(("AAA",), current=("AAA",))
    with pytest.raises(DecisionV1Error, match="UNEXPLAINED_SHADOW_PAPER_DIVERGENCE"):
        prepare_execution_v1(
            decision,_state(50_000_000,{}),
            eod_inputs=_eod("2026-08-21","2026-08-24",{"AAA":1000}),
        )


def test_random_cash_lot_and_capacity_invariants():
    rng = random.Random(20260821)
    for _ in range(2000):
        count = rng.randint(1,6)
        tickers = tuple(f"T{i}" for i in range(count))
        decision = _decision(tickers, buys=tuple(
            (t,i+1,"FILL_VACANCY_TOP10",None) for i,t in enumerate(tickers)
        ))
        nav = rng.choice([25_000_000,50_000_000,100_000_000])
        state = _state(nav,{})
        closes = {t:rng.uniform(200,20_000) for t in tickers}
        opens = {t:closes[t]*rng.uniform(.8,1.2) for t in tickers}
        values = {t:rng.uniform(50_000_000,5_000_000_000) for t in tickers}
        order = prepare_execution_v1(
            decision,state,eod_inputs=_eod("2026-08-21","2026-08-24",closes,values)
        )
        result = execute_open_v1(
            order,state,open_inputs=_open("2026-08-24",opens),
            ca_attestation=_ca("2026-08-21","2026-08-24",tickers),
        )
        assert result.state_after.cash_idr >= -1e-6
        assert all(x.shares % 100 == 0 for x in result.state_after.positions)
        for fill in (x for x in result.fills if x.side=="BUY" and x.filled_shares):
            assert fill.gross_notional <= .15*order.eod_nav_idr + 1e-6
            assert fill.gross_notional <= .01*values[fill.ticker] + 1e-6
