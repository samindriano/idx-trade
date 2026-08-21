from __future__ import annotations

from dataclasses import replace

import pytest

from idx_trade.decision_v3_graded_evidence import (
    DecisionV3Error,
    DecisionV3Profile,
    DecisionV3ShadowState,
    RankObservation,
    RankSession,
    plan_decision_v3_graded_evidence,
)


PROFILE = DecisionV3Profile(
    rule_id="TEST_DECISION_V3_GRADED_EVIDENCE_V2",
    target_count_max=10,
    strong_zone_max_rank=10,
    retention_zone_max_rank=20,
    mild_deterioration_max_rank=50,
    soft_replacement_min_rank_advantage=5,
)

HELD = tuple(f"A{i}" for i in range(1, 11))
BASE_UNIVERSE = list(HELD) + ["ZA", "ZB", "ZC", "ZD"] + [
    f"X{i:03d}" for i in range(1, 67)
]


def _session(
    day: str,
    assignments: dict[str, int],
    *,
    exclude: set[str] | None = None,
) -> RankSession:
    exclude = exclude or set()
    universe = [ticker for ticker in BASE_UNIVERSE if ticker not in exclude]
    for ticker in assignments:
        if ticker not in universe:
            universe.append(ticker)
    ranks = list(assignments.values())
    assert len(set(ranks)) == len(ranks)
    assert min(ranks, default=1) >= 1
    assert max(ranks, default=1) <= len(universe)

    by_rank = {rank: ticker for ticker, rank in assignments.items()}
    remaining = [ticker for ticker in universe if ticker not in assignments]
    rows: list[RankObservation] = []
    cursor = 0
    for rank in range(1, len(universe) + 1):
        ticker = by_rank.get(rank)
        if ticker is None:
            ticker = remaining[cursor]
            cursor += 1
        rows.append(RankObservation(ticker=ticker, rank=rank))
    return RankSession(session_date=day, rows=tuple(rows))


def _held_previous(day: str = "2026-01-02", **extra: int) -> RankSession:
    assignments = {ticker: rank for rank, ticker in enumerate(HELD, start=1)}
    assignments.update(extra)
    return _session(day, assignments)


def _state(day: str = "2026-01-02", *positions: str) -> DecisionV3ShadowState:
    positions = positions or HELD
    return DecisionV3ShadowState(as_of_session_date=day, positions=tuple(positions))


def _obs(plan, ticker: str):
    return next(item for item in plan.incumbent_observations if item.ticker == ticker)


def _challenger(plan, ticker: str):
    return next(item for item in plan.challenger_observations if item.ticker == ticker)


def test_bootstrap_is_exact_top10_and_preroll_is_forbidden() -> None:
    current = _session(
        "2026-01-02", {ticker: rank for rank, ticker in enumerate(HELD, start=1)}
    )
    plan = plan_decision_v3_graded_evidence(
        current, None, DecisionV3ShadowState.empty(), PROFILE
    )
    assert plan.bootstrap is True
    assert plan.target_positions == HELD
    assert {intent.reason for intent in plan.buy_intents} == {"BOOTSTRAP_TOP10"}
    assert plan.capacity_state == "FULL"

    with pytest.raises(DecisionV3Error, match="BOOTSTRAP_PREROLL_FORBIDDEN"):
        plan_decision_v3_graded_evidence(
            current, _held_previous("2026-01-01"), DecisionV3ShadowState.empty(), PROFILE
        )


@pytest.mark.parametrize("current_rank", [21, 35, 50])
def test_first_mild_deterioration_gets_exactly_one_grace(current_rank: int) -> None:
    previous = _held_previous()
    current_assignments = {ticker: rank for rank, ticker in enumerate(HELD[1:], start=1)}
    current_assignments["A1"] = current_rank
    current = _session("2026-01-03", current_assignments)
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    assert _obs(plan, "A1").state == "MILD_DETERIORATION_PENDING_1"
    assert "A1" in plan.target_positions
    assert not any(intent.ticker == "A1" for intent in plan.sell_intents)


@pytest.mark.parametrize("current_rank", [21, 35, 50])
def test_second_consecutive_mild_deterioration_exits(current_rank: int) -> None:
    previous_assignments = {ticker: rank for rank, ticker in enumerate(HELD[1:], start=1)}
    previous_assignments["A1"] = 25
    previous = _session("2026-01-02", previous_assignments)
    current_assignments = {ticker: rank for rank, ticker in enumerate(HELD[1:], start=1)}
    current_assignments["A1"] = current_rank
    current = _session("2026-01-03", current_assignments)
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    assert _obs(plan, "A1").state == "CONFIRMED_MILD_DETERIORATION_EXIT"
    assert any(
        intent.ticker == "A1" and intent.reason == "CONFIRMED_MILD_DETERIORATION_EXIT"
        for intent in plan.sell_intents
    )
    assert "A1" not in plan.target_positions


@pytest.mark.parametrize("current_rank", [51, 75, 80])
def test_severe_deterioration_exits_immediately(current_rank: int) -> None:
    previous = _held_previous()
    current_assignments = {ticker: rank for rank, ticker in enumerate(HELD[1:], start=1)}
    current_assignments["A1"] = current_rank
    current = _session("2026-01-03", current_assignments)
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    assert _obs(plan, "A1").state == "SEVERE_DETERIORATION_EXIT"
    assert any(
        intent.ticker == "A1" and intent.reason == "SEVERE_DETERIORATION_EXIT"
        for intent in plan.sell_intents
    )
    assert "A1" not in plan.target_positions


def test_vacancy_fill_priority_is_A_then_B_then_C() -> None:
    previous = _held_previous(ZA=15, ZB=30, ZC=60)
    current = _session(
        "2026-01-03",
        {
            "ZA": 1,
            "ZB": 2,
            "ZC": 3,
            "A4": 4,
            "A5": 5,
            "A6": 6,
            "A7": 7,
            "A8": 8,
            "A9": 9,
            "A10": 10,
            "A1": 51,
            "A2": 52,
            "A3": 53,
        },
    )
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    reasons = {intent.ticker: intent.reason for intent in plan.buy_intents}
    assert reasons["ZA"] == "TIER_A_VACANCY_FILL"
    assert reasons["ZB"] == "TIER_B_VACANCY_FILL"
    assert reasons["ZC"] == "TIER_C_RESIDUAL_VACANCY_FILL"
    assert _challenger(plan, "ZA").state == "A_CORE"
    assert _challenger(plan, "ZB").state == "B_NEAR"
    assert _challenger(plan, "ZC").state == "C_DISTANT"
    assert len(plan.target_positions) == 10


def test_one_vacancy_consumes_A_before_B_or_C() -> None:
    previous = _held_previous(ZA=15, ZB=30, ZC=60)
    current = _session(
        "2026-01-03",
        {
            "ZA": 1,
            "ZB": 2,
            "ZC": 3,
            "A2": 4,
            "A3": 5,
            "A4": 6,
            "A5": 7,
            "A6": 8,
            "A7": 9,
            "A8": 10,
            "A9": 11,
            "A10": 12,
            "A1": 51,
        },
    )
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    buys = {intent.ticker: intent.reason for intent in plan.buy_intents}
    assert buys == {"ZA": "TIER_A_VACANCY_FILL"}
    assert "ZB" not in plan.target_positions
    assert "ZC" not in plan.target_positions


@pytest.mark.parametrize(
    ("candidate", "previous_rank", "expected_state"),
    [("ZB", 30, "B_NEAR"), ("ZC", 60, "C_DISTANT")],
)
def test_noncore_tiers_cannot_soft_replace(
    candidate: str, previous_rank: int, expected_state: str
) -> None:
    previous = _held_previous(**{candidate: previous_rank})
    current = _session(
        "2026-01-03",
        {
            candidate: 1,
            "A2": 2,
            "A3": 3,
            "A4": 4,
            "A5": 5,
            "A6": 6,
            "A7": 7,
            "A8": 8,
            "A9": 9,
            "A10": 10,
            "A1": 15,
        },
    )
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    assert _challenger(plan, candidate).state == expected_state
    assert candidate not in plan.target_positions
    assert "A1" in plan.target_positions
    assert not plan.buy_intents
    assert not plan.sell_intents


def test_core_can_soft_replace_only_with_gap5() -> None:
    previous = _held_previous(ZA=15)
    current = _session(
        "2026-01-03",
        {
            "ZA": 1,
            "A2": 2,
            "A3": 3,
            "A4": 4,
            "A5": 5,
            "A6": 6,
            "A7": 7,
            "A8": 8,
            "A9": 9,
            "A10": 10,
            "A1": 15,
        },
    )
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    assert any(
        x.ticker == "ZA" and x.reason == "SOFT_RANK_GAP_REPLACEMENT"
        for x in plan.buy_intents
    )
    assert any(
        x.ticker == "A1" and x.reason == "SOFT_RANK_GAP_REPLACEMENT"
        for x in plan.sell_intents
    )
    assert "ZA" in plan.target_positions
    assert "A1" not in plan.target_positions


def test_previous_absent_top10_cannot_fill_even_real_vacancy() -> None:
    previous = _session(
        "2026-01-02",
        {ticker: rank for rank, ticker in enumerate(HELD, start=1)},
        exclude={"ZD"},
    )
    current = _session(
        "2026-01-03",
        {
            "ZD": 1,
            "A2": 2,
            "A3": 3,
            "A4": 4,
            "A5": 5,
            "A6": 6,
            "A7": 7,
            "A8": 8,
            "A9": 9,
            "A10": 10,
            "A1": 51,
        },
    )
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    assert _challenger(plan, "ZD").state == "D_NO_HISTORY"
    assert "ZD" not in plan.target_positions
    assert len(plan.target_positions) == 9
    assert plan.unfilled_slots == 1
    assert plan.capacity_state == "UNFILLED_NO_QUALIFIED_CHALLENGER"


def test_tier_c_entry_becomes_normal_incumbent_next_session_without_hidden_tier_rule() -> None:
    previous = _held_previous(ZC=60)
    entry_session = _session(
        "2026-01-03",
        {
            "ZC": 1,
            "A2": 2,
            "A3": 3,
            "A4": 4,
            "A5": 5,
            "A6": 6,
            "A7": 7,
            "A8": 8,
            "A9": 9,
            "A10": 10,
            "A1": 51,
        },
    )
    entry_plan = plan_decision_v3_graded_evidence(
        entry_session, previous, _state(), PROFILE
    )
    assert any(
        intent.ticker == "ZC" and intent.reason == "TIER_C_RESIDUAL_VACANCY_FILL"
        for intent in entry_plan.buy_intents
    )

    next_session = _session(
        "2026-01-04",
        {
            "A2": 1,
            "A3": 2,
            "A4": 3,
            "A5": 4,
            "A6": 5,
            "A7": 6,
            "A8": 7,
            "A9": 8,
            "A10": 9,
            "ZC": 30,
        },
    )
    next_plan = plan_decision_v3_graded_evidence(
        next_session,
        entry_session,
        DecisionV3ShadowState.from_plan(entry_plan),
        PROFILE,
    )
    assert _obs(next_plan, "ZC").state == "MILD_DETERIORATION_PENDING_1"
    assert "ZC" in next_plan.target_positions


def test_universe_disappearance_exits_immediately() -> None:
    previous = _held_previous()
    current = _session(
        "2026-01-03",
        {ticker: rank for rank, ticker in enumerate(HELD[1:], start=1)},
        exclude={"A1"},
    )
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    assert _obs(plan, "A1").state == "UNIVERSE_EXIT"
    assert any(
        intent.ticker == "A1" and intent.reason == "UNIVERSE_EXIT"
        for intent in plan.sell_intents
    )
    assert "A1" not in plan.target_positions


def test_result_is_deterministic_under_row_and_state_order_permutation() -> None:
    previous = _held_previous(ZA=15, ZB=30, ZC=60)
    current = _session(
        "2026-01-03",
        {
            "ZA": 1,
            "ZB": 2,
            "ZC": 3,
            "A4": 4,
            "A5": 5,
            "A6": 6,
            "A7": 7,
            "A8": 8,
            "A9": 9,
            "A10": 10,
            "A1": 51,
            "A2": 52,
            "A3": 53,
        },
    )
    state = _state()
    shuffled_state = DecisionV3ShadowState(
        as_of_session_date="2026-01-02", positions=tuple(reversed(HELD))
    )
    a = plan_decision_v3_graded_evidence(current, previous, state, PROFILE)
    b = plan_decision_v3_graded_evidence(
        replace(current, rows=tuple(reversed(current.rows))),
        replace(previous, rows=tuple(reversed(previous.rows))),
        shuffled_state,
        PROFILE,
    )
    assert a == b


def test_rule_bound_shadow_state_rejects_other_profile() -> None:
    previous = _held_previous()
    current = _session(
        "2026-01-03", {ticker: rank for rank, ticker in enumerate(HELD, start=1)}
    )
    state = DecisionV3ShadowState(
        as_of_session_date="2026-01-02",
        positions=HELD,
        rule_id="OTHER_RULE",
    )
    with pytest.raises(DecisionV3Error, match="SHADOW_RULE_ID_MISMATCH"):
        plan_decision_v3_graded_evidence(current, previous, state, PROFILE)


def test_shadow_state_from_plan_binds_rule_id() -> None:
    current = _session(
        "2026-01-02", {ticker: rank for rank, ticker in enumerate(HELD, start=1)}
    )
    plan = plan_decision_v3_graded_evidence(
        current, None, DecisionV3ShadowState.empty(), PROFILE
    )
    state = DecisionV3ShadowState.from_plan(plan)
    assert state.rule_id == PROFILE.rule_id
    assert state.as_of_session_date == plan.decision_session_date
    assert state.positions == plan.target_positions
