from __future__ import annotations

from dataclasses import replace

import pytest

from idx_trade.decision_v2_minimal import (
    DecisionV2Error,
    DecisionV2Profile,
    DecisionV2ShadowState,
    RankObservation,
    RankSession,
    plan_decision_v2_minimal,
)


PROFILE = DecisionV2Profile(
    rule_id="TEST_DECISION_V2_MINIMAL",
    target_count_max=10,
    strong_zone_max_rank=10,
    retention_zone_max_rank=20,
    soft_replacement_min_rank_advantage=5,
    entry_confirmation_previous_rank_max=20,
)


def _session(day: str, tickers_in_rank_order: list[str]) -> RankSession:
    return RankSession(
        session_date=day,
        rows=tuple(
            RankObservation(ticker=ticker, rank=index)
            for index, ticker in enumerate(tickers_in_rank_order, start=1)
        ),
    )


def _universe(*preferred: str, n: int = 30) -> list[str]:
    seen = set(preferred)
    fillers = [f"X{i:02d}" for i in range(1, n + 1) if f"X{i:02d}" not in seen]
    return list(preferred) + fillers[: n - len(preferred)]


def _state(day: str, *positions: str) -> DecisionV2ShadowState:
    return DecisionV2ShadowState(as_of_session_date=day, positions=tuple(positions))


def test_bootstrap_is_exact_top10_once_without_preroll() -> None:
    current = _session("2026-01-02", _universe(*[f"A{i}" for i in range(1, 11)]))
    plan = plan_decision_v2_minimal(current, None, DecisionV2ShadowState.empty(), PROFILE)

    assert plan.bootstrap is True
    assert plan.target_positions == tuple(f"A{i}" for i in range(1, 11))
    assert len(plan.buy_intents) == 10
    assert {intent.reason for intent in plan.buy_intents} == {"BOOTSTRAP_TOP10"}
    assert plan.unfilled_slots == 0

    previous = _session("2026-01-01", _universe(*[f"A{i}" for i in range(1, 11)]))
    with pytest.raises(DecisionV2Error, match="BOOTSTRAP_PREROLL_FORBIDDEN"):
        plan_decision_v2_minimal(current, previous, DecisionV2ShadowState.empty(), PROFILE)


def test_fresh_top10_is_rejected_and_confirmed_exit_can_leave_underfill() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session(
        "2026-01-02",
        _universe("A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "X11", "A1", "X12", "X13", "X14", "Z"),
    )
    current = _session(
        "2026-01-03",
        _universe("Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "A1"),
    )

    plan = plan_decision_v2_minimal(current, previous, _state("2026-01-02", *held), PROFILE)

    assert {x.ticker for x in plan.sell_intents} == {"A1"}
    assert plan.sell_intents[0].reason == "CONFIRMED_EXIT_GT20_2"
    assert not plan.buy_intents
    assert "Z" not in plan.target_positions
    assert len(plan.target_positions) == 9
    assert plan.unfilled_slots == 1
    z = next(obs for obs in plan.challenger_observations if obs.ticker == "Z")
    assert z.state == "UNCONFIRMED_PREVIOUS_GT_THRESHOLD"


def test_previous_top20_current_top10_is_qualified_to_fill_vacancy() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous_order = _universe(
        "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10",
        "X01", "X02", "X03", "X04", "Z", "X05", "X06", "X07", "X08", "X09", "X10", "A1"
    )
    current_order = _universe(
        "Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10",
        "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "A1"
    )
    previous = _session("2026-01-02", previous_order)
    current = _session("2026-01-03", current_order)

    plan = plan_decision_v2_minimal(current, previous, _state("2026-01-02", *held), PROFILE)

    assert {x.ticker for x in plan.sell_intents} == {"A1"}
    assert {x.ticker for x in plan.buy_intents} == {"Z"}
    assert plan.buy_intents[0].reason == "QUALIFIED_VACANCY_FILL"
    assert len(plan.target_positions) == 10
    assert plan.unfilled_slots == 0


def test_first_outside_top20_is_exit_pending_not_sell() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session("2026-01-02", _universe(*held))
    current = _session(
        "2026-01-03",
        _universe("Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "A1"),
    )

    plan = plan_decision_v2_minimal(current, previous, _state("2026-01-02", *held), PROFILE)

    a1 = next(obs for obs in plan.incumbent_observations if obs.ticker == "A1")
    assert a1.state == "EXIT_PENDING_1"
    assert "A1" in plan.target_positions
    assert not plan.sell_intents
    assert "Z" not in plan.target_positions


def test_second_consecutive_outside_top20_is_confirmed_exit() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session(
        "2026-01-02",
        _universe("A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "Z", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "A1"),
    )
    current = _session(
        "2026-01-03",
        _universe("Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "X11", "A1"),
    )

    plan = plan_decision_v2_minimal(current, previous, _state("2026-01-02", *held), PROFILE)

    a1 = next(obs for obs in plan.incumbent_observations if obs.ticker == "A1")
    assert a1.state == "CONFIRMED_EXIT"
    assert any(x.ticker == "A1" and x.reason == "CONFIRMED_EXIT_GT20_2" for x in plan.sell_intents)
    assert "A1" not in plan.target_positions
    assert "Z" in plan.target_positions


def test_exit_pending_recovers_when_rank_returns_to_top20() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session(
        "2026-01-02",
        _universe("A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "X11", "A1"),
    )
    current = _session(
        "2026-01-03",
        _universe("A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "A1"),
    )

    plan = plan_decision_v2_minimal(current, previous, _state("2026-01-02", *held), PROFILE)

    a1 = next(obs for obs in plan.incumbent_observations if obs.ticker == "A1")
    assert a1.state == "ACCEPTABLE_HOLD"
    assert "A1" in plan.target_positions
    assert not any(x.ticker == "A1" for x in plan.sell_intents)


def test_universe_disappearance_exits_immediately() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session("2026-01-02", _universe(*held))
    current_names = _universe("Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10")
    current_names = [ticker for ticker in current_names if ticker != "A1"]
    current = _session("2026-01-03", current_names)

    plan = plan_decision_v2_minimal(current, previous, _state("2026-01-02", *held), PROFILE)

    a1 = next(obs for obs in plan.incumbent_observations if obs.ticker == "A1")
    assert a1.state == "UNIVERSE_EXIT"
    assert any(x.ticker == "A1" and x.reason == "UNIVERSE_EXIT" for x in plan.sell_intents)


def test_soft_replacement_requires_qualified_challenger_and_gap5() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session(
        "2026-01-02",
        _universe("A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "Z", "X03", "X04", "A1"),
    )
    current = _session(
        "2026-01-03",
        _universe("Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "A1"),
    )

    plan = plan_decision_v2_minimal(current, previous, _state("2026-01-02", *held), PROFILE)

    assert any(x.ticker == "A1" and x.reason == "SOFT_RANK_GAP_REPLACEMENT" for x in plan.sell_intents)
    assert any(x.ticker == "Z" and x.reason == "SOFT_RANK_GAP_REPLACEMENT" for x in plan.buy_intents)
    assert "Z" in plan.target_positions
    assert "A1" not in plan.target_positions


def test_exit_pending_is_not_soft_replaceable_by_qualified_challenger() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session(
        "2026-01-02",
        _universe("A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "Z", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "A1"),
    )
    current = _session(
        "2026-01-03",
        _universe("Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "A1"),
    )

    plan = plan_decision_v2_minimal(current, previous, _state("2026-01-02", *held), PROFILE)

    a1 = next(obs for obs in plan.incumbent_observations if obs.ticker == "A1")
    assert a1.state == "EXIT_PENDING_1"
    assert "A1" in plan.target_positions
    assert "Z" not in plan.target_positions
    assert not plan.buy_intents
    assert not plan.sell_intents


def test_unqualified_fresh_challenger_cannot_soft_replace() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session(
        "2026-01-02",
        _universe("A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "A1", "X05", "X06", "X07", "X08", "X09", "X10", "X11", "X12", "X13", "X14", "Z"),
    )
    current = _session(
        "2026-01-03",
        _universe("Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "A1"),
    )

    plan = plan_decision_v2_minimal(current, previous, _state("2026-01-02", *held), PROFILE)

    assert "A1" in plan.target_positions
    assert "Z" not in plan.target_positions
    assert not plan.buy_intents
    assert not plan.sell_intents


def test_result_is_deterministic_under_row_order_permutation() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session(
        "2026-01-02",
        _universe("A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "Z", "X03", "X04", "A1"),
    )
    current = _session(
        "2026-01-03",
        _universe("Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "A1"),
    )
    shuffled_current = replace(current, rows=tuple(reversed(current.rows)))
    shuffled_previous = replace(previous, rows=tuple(reversed(previous.rows)))
    state = _state("2026-01-02", *reversed(held))

    a = plan_decision_v2_minimal(current, previous, state, PROFILE)
    b = plan_decision_v2_minimal(shuffled_current, shuffled_previous, state, PROFILE)
    assert a == b


def test_state_must_align_exactly_to_previous_session() -> None:
    current = _session("2026-01-03", _universe(*[f"A{i}" for i in range(1, 11)]))
    previous = _session("2026-01-02", _universe(*[f"A{i}" for i in range(1, 11)]))
    bad_state = _state("2026-01-01", *[f"A{i}" for i in range(1, 11)])

    with pytest.raises(DecisionV2Error, match="STATE_PREVIOUS_SESSION_MISMATCH"):
        plan_decision_v2_minimal(current, previous, bad_state, PROFILE)


def test_rank_session_rejects_duplicate_or_noncontiguous_ranks() -> None:
    rows = tuple(RankObservation(f"A{i}", i) for i in range(1, 11))
    duplicate = RankSession("2026-01-02", rows[:-1] + (RankObservation("A10", 9),))
    with pytest.raises(DecisionV2Error):
        plan_decision_v2_minimal(duplicate, None, DecisionV2ShadowState.empty(), PROFILE)

    noncontiguous = RankSession(
        "2026-01-02",
        tuple(RankObservation(f"A{i}", i if i < 10 else 11) for i in range(1, 11)),
    )
    with pytest.raises(DecisionV2Error, match="RANKS_NOT_CONTIGUOUS"):
        plan_decision_v2_minimal(noncontiguous, None, DecisionV2ShadowState.empty(), PROFILE)
