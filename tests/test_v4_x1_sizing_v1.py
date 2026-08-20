import hashlib
import math
import random
from pathlib import Path

import pytest

from idx_trade.v4_x1_decision_v1_contract import DecisionPlan, DecisionV1Error, TradeIntent
from idx_trade.v4_x1_sizing_v1 import (
    EXPECTED_SIZING_CONFIG_SHA256,
    size_decision_v1_entries,
    verify_sizing_v1_config,
)


def _plan(buys):
    intents = tuple(TradeIntent("BUY_INTENT", ticker, rank, "TEST") for ticker, rank in buys)
    return DecisionPlan(
        "2026-08-21",
        "OFFICIAL_OPEN_T_PLUS_1",
        (),
        tuple(ticker for ticker, _ in buys),
        intents,
        (),
        (),
        0,
    )


def test_config_hash():
    path = Path(__file__).parents[1] / "config" / "v4_x1_sizing_v1.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_SIZING_CONFIG_SHA256
    verify_sizing_v1_config(path)


def test_bootstrap_equal_prices_exact():
    plan = _plan([(f"T{i}", i) for i in range(1, 11)])
    prices = {f"T{i}": 1000 for i in range(1, 11)}
    out = size_decision_v1_entries(
        plan,
        nav_idr=50_000_000,
        available_cash_idr=50_000_000,
        reference_prices=prices,
    )
    assert [entry.lots for entry in out.entries] == [50] * 10
    assert out.total_sized_notional == 50_000_000
    assert out.residual_cash_after_sizing_reference == 0


def test_no_buy_no_rebalance():
    out = size_decision_v1_entries(
        _plan([]),
        nav_idr=50_000_000,
        available_cash_idr=3_000_000,
        reference_prices={},
    )
    assert out.entries == ()
    assert out.residual_cash_after_sizing_reference == 3_000_000


def test_batch_cash_limit_equal_budget():
    out = size_decision_v1_entries(
        _plan([("AAA", 1), ("BBB", 2)]),
        nav_idr=50_000_000,
        available_cash_idr=6_000_000,
        reference_prices={"AAA": 1000, "BBB": 1000},
    )
    assert [entry.lots for entry in out.entries] == [30, 30]
    assert out.total_sized_notional == 6_000_000


def test_one_lot_over_15pct_is_infeasible():
    out = size_decision_v1_entries(
        _plan([("AAA", 1)]),
        nav_idr=50_000_000,
        available_cash_idr=10_000_000,
        reference_prices={"AAA": 76_000},
    )
    assert out.entries[0].lots == 0
    assert out.entries[0].status == "LOT_SIZE_INFEASIBLE_15PCT_CAP"


def test_nearest_lot_can_go_above_10pct_but_below_cap():
    out = size_decision_v1_entries(
        _plan([("AAA", 1)]),
        nav_idr=50_000_000,
        available_cash_idr=10_000_000,
        reference_prices={"AAA": 52_000},
    )
    assert out.entries[0].lots == 1
    assert out.entries[0].sized_weight == pytest.approx(0.104)


def test_ten_expensive_lots_cash_constraint_deterministic():
    plan = _plan([(f"T{i}", i) for i in range(1, 11)])
    prices = {f"T{i}": 52_000 for i in range(1, 11)}
    out = size_decision_v1_entries(
        plan,
        nav_idr=50_000_000,
        available_cash_idr=50_000_000,
        reference_prices=prices,
    )
    assert sum(entry.lots for entry in out.entries) == 9
    assert out.total_sized_notional == 46_800_000


def test_order_invariant():
    first = [("BBB", 2), ("AAA", 1), ("CCC", 3)]
    second = list(reversed(first))
    prices = {"AAA": 1234, "BBB": 2345, "CCC": 3456}
    out1 = size_decision_v1_entries(
        _plan(first), nav_idr=50_000_000, available_cash_idr=15_000_000, reference_prices=prices
    )
    out2 = size_decision_v1_entries(
        _plan(second), nav_idr=50_000_000, available_cash_idr=15_000_000, reference_prices=prices
    )
    assert [(x.ticker, x.lots) for x in out1.entries] == [(x.ticker, x.lots) for x in out2.entries]


@pytest.mark.parametrize(
    "nav,cash",
    [(0, 0), (-1, 0), (50_000_000, -1), (50_000_000, 60_000_000)],
)
def test_bad_nav_cash_rejected(nav, cash):
    with pytest.raises(DecisionV1Error):
        size_decision_v1_entries(
            _plan([("AAA", 1)]),
            nav_idr=nav,
            available_cash_idr=cash,
            reference_prices={"AAA": 1000},
        )


def test_missing_price_rejected():
    with pytest.raises(DecisionV1Error, match="REFERENCE_PRICE_MISSING"):
        size_decision_v1_entries(
            _plan([("AAA", 1)]),
            nav_idr=50_000_000,
            available_cash_idr=5_000_000,
            reference_prices={},
        )


def test_random_invariants():
    rng = random.Random(20260821)
    for _ in range(5000):
        count = rng.randint(0, 10)
        buys = [(f"T{i}", i + 1) for i in range(count)]
        nav = rng.choice([10_000_000, 25_000_000, 50_000_000, 100_000_000])
        cash = rng.uniform(0, nav)
        prices = {f"T{i}": rng.uniform(50, 100_000) for i in range(count)}
        out = size_decision_v1_entries(
            _plan(buys), nav_idr=nav, available_cash_idr=cash, reference_prices=prices
        )
        assert out.total_sized_notional <= cash + 1e-6
        assert all(entry.shares % 100 == 0 for entry in out.entries)
        assert all(entry.sized_weight <= 0.15 + 1e-12 for entry in out.entries)
        assert out.residual_cash_after_sizing_reference >= -1e-6


def test_equal_quota_floor_is_never_sacrificed_to_fund_another_name():
    nav = 1_000_000
    cash = 431_539.61507128435
    prices = {"A": 203, "B": 1302, "C": 1306, "D": 1476}
    out = size_decision_v1_entries(
        _plan([("A", 1), ("B", 2), ("C", 3), ("D", 4)]),
        nav_idr=nav,
        available_cash_idr=cash,
        reference_prices=prices,
    )
    desired = min(0.1 * nav, cash / 4)
    for entry in out.entries:
        cap_lots = math.floor(0.15 * nav / entry.lot_value + 1e-12)
        floor_lots = min(math.floor(desired / entry.lot_value + 1e-12), cap_lots)
        assert entry.lots >= floor_lots


def test_rank_labels_do_not_change_equal_quota_allocation():
    prices = {"AAA": 52_000, "BBB": 52_000, "CCC": 52_000}
    out1 = size_decision_v1_entries(
        _plan([("AAA", 1), ("BBB", 2), ("CCC", 3)]),
        nav_idr=15_000_000,
        available_cash_idr=15_000_000,
        reference_prices=prices,
    )
    out2 = size_decision_v1_entries(
        _plan([("AAA", 3), ("BBB", 1), ("CCC", 2)]),
        nav_idr=15_000_000,
        available_cash_idr=15_000_000,
        reference_prices=prices,
    )
    assert {x.ticker: x.lots for x in out1.entries} == {x.ticker: x.lots for x in out2.entries}
