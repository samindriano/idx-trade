import hashlib
import random
from pathlib import Path

import pytest

from idx_trade.v4_x1_decision_v1_contract import DecisionPlan, TradeIntent, DecisionV1Error
from idx_trade.v4_x1_execution_v1 import (
    EXPECTED_EXECUTION_CONFIG_SHA256,
    PaperPortfolioState,
    PaperPosition,
    execute_open_v1,
    prepare_execution_v1,
    verify_execution_v1_config,
)


def _decision(current=(), target=(), buys=(), sells=()):
    return DecisionPlan(
        "2026-08-21",
        "OFFICIAL_OPEN_T_PLUS_1",
        tuple(current),
        tuple(target),
        tuple(TradeIntent("BUY_INTENT", t, r, reason, peer) for t, r, reason, peer in buys),
        tuple(TradeIntent("SELL_INTENT", t, r, reason, peer) for t, r, reason, peer in sells),
        tuple(t for t in target if t in current),
        0,
    )


def _state(cash, positions):
    return PaperPortfolioState(
        "2026-08-21",
        cash,
        tuple(PaperPosition(ticker, shares) for ticker, shares in positions.items()),
    )


def test_config_hash():
    path = Path(__file__).parents[1] / "config" / "v4_x1_execution_v1.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_EXECUTION_CONFIG_SHA256
    verify_execution_v1_config(path)


def test_bootstrap_close_size_then_open_execute():
    targets = tuple(f"T{i}" for i in range(1, 11))
    buys = tuple((ticker, i, "FILL_VACANCY_TOP10", None) for i, ticker in enumerate(targets, 1))
    decision = _decision(target=targets, buys=buys)
    state = _state(50_000_000, {})
    closes = {ticker: 1000 for ticker in targets}
    plan = prepare_execution_v1(
        decision, state, next_session_date="2026-08-24", raw_close_prices_t=closes
    )
    assert all(entry.lots == 50 for entry in plan.sizing_plan.entries)
    result = execute_open_v1(
        plan,
        state,
        execution_session_date="2026-08-24",
        raw_open_prices_t1=closes,
        tradable_tickers=set(targets),
        corporate_action_continuity_ok=True,
    )
    assert all(position.shares == 4900 for position in result.state_after.positions)
    assert result.state_after.cash_idr >= 0
    assert result.stamp_duty_idr == 10_000
    assert not result.reconciliation_required


def test_gap_down_never_increases_above_sizing_lots():
    decision = _decision(target=("AAA",), buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),))
    state = _state(50_000_000, {})
    plan = prepare_execution_v1(
        decision, state, next_session_date="2026-08-24", raw_close_prices_t={"AAA": 1000}
    )
    planned = plan.sizing_plan.entries[0].shares
    result = execute_open_v1(
        plan,
        state,
        execution_session_date="2026-08-24",
        raw_open_prices_t1={"AAA": 500},
        tradable_tickers={"AAA"},
        corporate_action_continuity_ok=True,
    )
    fill = next(row for row in result.fills if row.side == "BUY")
    assert fill.filled_shares <= planned


def test_gap_up_reduces_lots_and_respects_15pct_cap():
    decision = _decision(target=("AAA",), buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),))
    state = _state(50_000_000, {})
    plan = prepare_execution_v1(
        decision, state, next_session_date="2026-08-24", raw_close_prices_t={"AAA": 1000}
    )
    result = execute_open_v1(
        plan,
        state,
        execution_session_date="2026-08-24",
        raw_open_prices_t1={"AAA": 1500},
        tradable_tickers={"AAA"},
        corporate_action_continuity_ok=True,
    )
    fill = next(row for row in result.fills if row.side == "BUY")
    assert fill.gross_notional <= 0.15 * plan.eod_nav_idr + 1e-6


def test_replacement_sell_first_then_buy():
    state = _state(45_000_000, {"AAA": 5000})
    decision = _decision(
        current=("AAA",),
        target=("BBB",),
        buys=(("BBB", 1, "RANK_GAP_REPLACEMENT", "AAA"),),
        sells=(("AAA", 21, "RANK_GAP_REPLACEMENT", "BBB"),),
    )
    closes = {"AAA": 1000, "BBB": 1000}
    plan = prepare_execution_v1(
        decision, state, next_session_date="2026-08-24", raw_close_prices_t=closes
    )
    result = execute_open_v1(
        plan,
        state,
        execution_session_date="2026-08-24",
        raw_open_prices_t1=closes,
        tradable_tickers={"AAA", "BBB"},
        corporate_action_continuity_ok=True,
    )
    assert next(row for row in result.fills if row.side == "SELL").status == "FILLED"
    assert next(row for row in result.fills if row.side == "BUY").status == "FILLED"
    assert {position.ticker for position in result.state_after.positions} == {"BBB"}


def test_unavailable_sell_blocks_paired_buy():
    state = _state(45_000_000, {"AAA": 5000})
    decision = _decision(
        current=("AAA",),
        target=("BBB",),
        buys=(("BBB", 1, "RANK_GAP_REPLACEMENT", "AAA"),),
        sells=(("AAA", 21, "RANK_GAP_REPLACEMENT", "BBB"),),
    )
    plan = prepare_execution_v1(
        decision,
        state,
        next_session_date="2026-08-24",
        raw_close_prices_t={"AAA": 1000, "BBB": 1000},
    )
    result = execute_open_v1(
        plan,
        state,
        execution_session_date="2026-08-24",
        raw_open_prices_t1={"BBB": 1000},
        tradable_tickers={"BBB"},
        corporate_action_continuity_ok=True,
    )
    assert any(row.status == "MARKET_EXIT_UNAVAILABLE" for row in result.fills)
    assert any(row.status == "BLOCKED_BY_UNRESOLVED_PAIRED_SELL" for row in result.fills)
    assert result.reconciliation_required
    assert {position.ticker for position in result.state_after.positions} == {"AAA"}


def test_missing_buy_open_is_no_fill():
    decision = _decision(target=("AAA",), buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),))
    state = _state(50_000_000, {})
    plan = prepare_execution_v1(
        decision, state, next_session_date="2026-08-24", raw_close_prices_t={"AAA": 1000}
    )
    result = execute_open_v1(
        plan,
        state,
        execution_session_date="2026-08-24",
        raw_open_prices_t1={},
        tradable_tickers=set(),
        corporate_action_continuity_ok=True,
    )
    assert any(row.status == "MARKET_ENTRY_UNAVAILABLE" for row in result.fills)
    assert result.reconciliation_required
    assert not result.state_after.positions


def test_ca_gate_aborts_before_mutation():
    decision = _decision(target=("AAA",), buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),))
    state = _state(50_000_000, {})
    plan = prepare_execution_v1(
        decision, state, next_session_date="2026-08-24", raw_close_prices_t={"AAA": 1000}
    )
    with pytest.raises(DecisionV1Error, match="CA_CONTINUITY_REQUIRED"):
        execute_open_v1(
            plan,
            state,
            execution_session_date="2026-08-24",
            raw_open_prices_t1={"AAA": 1000},
            tradable_tickers={"AAA"},
            corporate_action_continuity_ok=False,
        )
    assert state.cash_idr == 50_000_000


def test_state_hash_prevents_wrong_state_execution():
    decision = _decision(target=("AAA",), buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),))
    state = _state(50_000_000, {})
    plan = prepare_execution_v1(
        decision, state, next_session_date="2026-08-24", raw_close_prices_t={"AAA": 1000}
    )
    other = _state(49_000_000, {})
    with pytest.raises(DecisionV1Error, match="STATE_HASH_MISMATCH"):
        execute_open_v1(
            plan,
            other,
            execution_session_date="2026-08-24",
            raw_open_prices_t1={"AAA": 1000},
            tradable_tickers={"AAA"},
            corporate_action_continuity_ok=True,
        )


def test_sell_slippage_and_fee_direction():
    state = _state(45_000_000, {"AAA": 5000})
    decision = _decision(
        current=("AAA",), target=(), sells=(("AAA", 21, "HARD_EXIT_RANK_GT20", None),)
    )
    plan = prepare_execution_v1(
        decision, state, next_session_date="2026-08-24", raw_close_prices_t={"AAA": 1000}
    )
    result = execute_open_v1(
        plan,
        state,
        execution_session_date="2026-08-24",
        raw_open_prices_t1={"AAA": 1000},
        tradable_tickers={"AAA"},
        corporate_action_continuity_ok=True,
    )
    fill = next(row for row in result.fills if row.side == "SELL")
    assert fill.effective_price == pytest.approx(999.0)
    assert fill.fee_idr == pytest.approx(fill.gross_notional * 0.0025)


def test_random_cash_and_lot_invariants():
    rng = random.Random(20260821)
    for _ in range(2000):
        count = rng.randint(1, 5)
        tickers = [f"T{i}" for i in range(count)]
        buys = tuple((ticker, i + 1, "FILL_VACANCY_TOP10", None) for i, ticker in enumerate(tickers))
        decision = _decision(target=tuple(tickers), buys=buys)
        nav = rng.choice([25_000_000, 50_000_000, 100_000_000])
        state = _state(nav, {})
        closes = {ticker: rng.uniform(200, 50_000) for ticker in tickers}
        opens = {ticker: closes[ticker] * rng.uniform(0.85, 1.15) for ticker in tickers}
        plan = prepare_execution_v1(
            decision, state, next_session_date="2026-08-24", raw_close_prices_t=closes
        )
        result = execute_open_v1(
            plan,
            state,
            execution_session_date="2026-08-24",
            raw_open_prices_t1=opens,
            tradable_tickers=set(tickers),
            corporate_action_continuity_ok=True,
        )
        assert result.state_after.cash_idr >= -1e-6
        assert all(position.shares % 100 == 0 for position in result.state_after.positions)
        for fill in [row for row in result.fills if row.side == "BUY" and row.filled_shares]:
            planned = next(entry.shares for entry in plan.sizing_plan.entries if entry.ticker == fill.ticker)
            assert fill.filled_shares <= planned


def test_operational_failure_marks_state_for_reconciliation_and_blocks_next_prepare():
    decision = _decision(target=("AAA",), buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),))
    state = _state(50_000_000, {})
    plan = prepare_execution_v1(
        decision, state, next_session_date="2026-08-24", raw_close_prices_t={"AAA": 1000}
    )
    result = execute_open_v1(
        plan,
        state,
        execution_session_date="2026-08-24",
        raw_open_prices_t1={},
        tradable_tickers=set(),
        corporate_action_continuity_ok=True,
    )
    assert result.state_after.reconciliation_required
    next_decision = DecisionPlan(
        "2026-08-24",
        "OFFICIAL_OPEN_T_PLUS_1",
        ("AAA",),
        ("AAA",),
        (),
        (),
        ("AAA",),
        0,
    )
    with pytest.raises(DecisionV1Error, match="PRIOR_RECONCILIATION_REQUIRED"):
        prepare_execution_v1(
            next_decision,
            result.state_after,
            next_session_date="2026-08-25",
            raw_close_prices_t={"AAA": 1000},
        )


def test_next_execution_session_must_be_after_decision_date():
    decision = _decision(target=("AAA",), buys=(("AAA", 1, "FILL_VACANCY_TOP10", None),))
    state = _state(50_000_000, {})
    with pytest.raises(DecisionV1Error, match="NEXT_SESSION_NOT_AFTER_DECISION"):
        prepare_execution_v1(
            decision,
            state,
            next_session_date="2026-08-21",
            raw_close_prices_t={"AAA": 1000},
        )
