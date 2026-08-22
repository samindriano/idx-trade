import dataclasses
import hashlib
import random
from pathlib import Path

import pytest

from decision_v1_helpers import _state, _verified_direct
from idx_trade.v4_x1_decision_v1 import plan_decision_v1
from idx_trade.v4_x1_decision_v1_contract import DecisionPlan, DecisionV1Error, TradeIntent
from idx_trade.v4_x1_sizing_v1 import (
    SUPPORTED_DECISION_RULES,
    VerifiedDecisionPlan,
    _VERIFIED_DECISION_PLAN_TOKEN,
    size_decision_v1_entries,
    verify_decision_plan_for_downstream,
    verify_sizing_v1_config,
)


def _synthetic_plan(buys):
    intents = tuple(TradeIntent("BUY_INTENT", ticker, rank, "TEST") for ticker, rank in buys)
    plan = DecisionPlan(
        "2026-08-21", "OFFICIAL_OPEN_T_PLUS_1", (),
        tuple(ticker for ticker, _ in buys), intents, (), (), 0,
    )
    return VerifiedDecisionPlan(
        plan, plan.decision_session_date, "synthetic-score-sha",
        _verification_token=_VERIFIED_DECISION_PLAN_TOKEN,
    )


def test_config_hash():
    path = Path(__file__).parents[1] / "config" / "v4_x1_sizing_v1.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "7bf8e43aba9153b8d01d4ba932970e2aa437f1427a6d6f4f862063ff75a3c704"
    assert SUPPORTED_DECISION_RULES == (
        "V4_X1_DECISION_V1",
        "V4_X1_DECISION_V2_MINIMAL_V1",
    )
    verify_sizing_v1_config(path)


def test_real_decision_output_can_be_verified_for_downstream():
    verified = _verified_direct()
    shadow = _state([])
    decision = plan_decision_v1(verified, shadow)
    wrapped = verify_decision_plan_for_downstream(decision, verified, shadow)
    assert wrapped.plan == decision
    forged = dataclasses.replace(decision, target_positions=tuple(reversed(decision.target_positions)))
    with pytest.raises(DecisionV1Error, match="PROVENANCE_MISMATCH"):
        verify_decision_plan_for_downstream(forged, verified, shadow)


def test_raw_unverified_decision_is_rejected():
    raw = DecisionPlan(
        "2026-08-21", "OFFICIAL_OPEN_T_PLUS_1", (), ("AAA",),
        (TradeIntent("BUY_INTENT", "AAA", 1, "TEST"),), (), (), 0,
    )
    with pytest.raises(DecisionV1Error, match="VERIFIED_DECISION"):
        size_decision_v1_entries(raw, nav_idr=50_000_000, available_cash_idr=50_000_000,
                                 reference_prices={"AAA": 1000})


def test_bootstrap_equal_prices_exact():
    plan = _synthetic_plan([(f"T{i}", i) for i in range(1, 11)])
    out = size_decision_v1_entries(
        plan, nav_idr=50_000_000, available_cash_idr=50_000_000,
        reference_prices={f"T{i}": 1000 for i in range(1, 11)},
    )
    assert [x.lots for x in out.entries] == [50] * 10


def test_exact_lot_tie_prefers_better_rank_not_ticker():
    plan = _synthetic_plan([(f"T{i:02d}", i) for i in range(1, 11)])
    out = size_decision_v1_entries(
        plan, nav_idr=50_000_000, available_cash_idr=50_000_000,
        reference_prices={f"T{i:02d}": 52_000 for i in range(1, 11)},
    )
    zero = [x for x in out.entries if x.lots == 0]
    assert len(zero) == 1
    assert zero[0].rank_consensus == 10


def test_no_buy_no_rebalance():
    plan = _synthetic_plan([])
    out = size_decision_v1_entries(plan, nav_idr=50_000_000, available_cash_idr=3_000_000,
                                   reference_prices={})
    assert out.entries == ()
    assert out.residual_cash_after_sizing_reference == 3_000_000


def test_random_invariants():
    rng = random.Random(20260821)
    for _ in range(5000):
        count = rng.randint(0, 10)
        plan = _synthetic_plan([(f"T{i}", i + 1) for i in range(count)])
        nav = rng.choice([10_000_000, 25_000_000, 50_000_000, 100_000_000])
        cash = rng.uniform(0, nav)
        prices = {f"T{i}": rng.uniform(50, 100_000) for i in range(count)}
        out = size_decision_v1_entries(plan, nav_idr=nav, available_cash_idr=cash,
                                       reference_prices=prices)
        assert out.total_sized_notional <= cash + 1e-6
        assert all(x.shares % 100 == 0 for x in out.entries)
        assert all(x.sized_weight <= 0.15 + 1e-12 for x in out.entries)
        assert out.residual_cash_after_sizing_reference >= -1e-6
