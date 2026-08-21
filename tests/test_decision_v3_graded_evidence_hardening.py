from __future__ import annotations

from idx_trade.decision_v3_graded_evidence import (
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
UNIVERSE = list(HELD) + ["ZA", "ZB", "ZC", "ZD"] + [
    f"X{i:03d}" for i in range(1, 67)
]


def _session(
    day: str,
    assignments: dict[str, int],
    *,
    exclude: set[str] | None = None,
) -> RankSession:
    exclude = exclude or set()
    universe = [ticker for ticker in UNIVERSE if ticker not in exclude]
    for ticker in assignments:
        if ticker not in universe:
            universe.append(ticker)
    assert len(set(assignments.values())) == len(assignments)
    by_rank = {rank: ticker for ticker, rank in assignments.items()}
    remaining = [ticker for ticker in universe if ticker not in assignments]
    rows = []
    cursor = 0
    for rank in range(1, len(universe) + 1):
        ticker = by_rank.get(rank)
        if ticker is None:
            ticker = remaining[cursor]
            cursor += 1
        rows.append(RankObservation(ticker=ticker, rank=rank))
    return RankSession(day, tuple(rows))


def _state(day: str = "2026-01-02", positions: tuple[str, ...] = HELD):
    return DecisionV3ShadowState(as_of_session_date=day, positions=positions)


def _held_previous(**extra: int) -> RankSession:
    ranks = {ticker: rank for rank, ticker in enumerate(HELD, start=1)}
    ranks.update(extra)
    return _session("2026-01-02", ranks)


def test_two_vacancies_use_A_then_B_and_leave_C_unused() -> None:
    previous = _held_previous(ZA=15, ZB=30, ZC=60)
    current = _session(
        "2026-01-03",
        {
            "ZA": 1,
            "ZB": 2,
            "ZC": 3,
            "A3": 4,
            "A4": 5,
            "A5": 6,
            "A6": 7,
            "A7": 8,
            "A8": 9,
            "A9": 10,
            "A10": 11,
            "A1": 51,
            "A2": 52,
        },
    )
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    reasons = {intent.ticker: intent.reason for intent in plan.buy_intents}
    assert reasons == {
        "ZA": "TIER_A_VACANCY_FILL",
        "ZB": "TIER_B_VACANCY_FILL",
    }
    assert "ZC" not in plan.target_positions


def test_soft_replacement_gap5_is_inclusive_but_gap4_does_not_replace() -> None:
    previous = _held_previous(ZA=15)
    current_gap5 = _session(
        "2026-01-03",
        {
            "A2": 1,
            "A3": 2,
            "A4": 3,
            "A5": 4,
            "ZA": 5,
            "A6": 6,
            "A7": 7,
            "A8": 8,
            "A9": 9,
            "A10": 10,
            "A1": 10 + 0,
        },
    )
    # Avoid duplicate rank 10: build an equivalent exact-gap case with
    # challenger rank 10 and incumbent rank 15.
    current_gap5 = _session(
        "2026-01-03",
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
            "ZA": 10,
            "A1": 15,
        },
    )
    plan5 = plan_decision_v3_graded_evidence(current_gap5, previous, _state(), PROFILE)
    assert any(x.ticker == "ZA" and x.reason == "SOFT_RANK_GAP_REPLACEMENT" for x in plan5.buy_intents)

    current_gap4 = _session(
        "2026-01-03",
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
            "ZA": 10,
            "A1": 14,
        },
    )
    plan4 = plan_decision_v3_graded_evidence(current_gap4, previous, _state(), PROFILE)
    assert not plan4.buy_intents
    assert not plan4.sell_intents
    assert "A1" in plan4.target_positions


def test_no_history_candidate_cannot_soft_replace_full_portfolio() -> None:
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
            "A1": 15,
        },
    )
    plan = plan_decision_v3_graded_evidence(current, previous, _state(), PROFILE)
    assert not plan.buy_intents
    assert not plan.sell_intents
    assert "ZD" not in plan.target_positions
    assert "A1" in plan.target_positions


def test_tier_c_entry_that_turns_severe_next_session_exits_without_grace() -> None:
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
    assert any(x.ticker == "ZC" and x.reason == "TIER_C_RESIDUAL_VACANCY_FILL" for x in entry_plan.buy_intents)

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
            "ZC": 51,
        },
    )
    next_plan = plan_decision_v3_graded_evidence(
        next_session,
        entry_session,
        DecisionV3ShadowState.from_plan(entry_plan),
        PROFILE,
    )
    zc = next(obs for obs in next_plan.incumbent_observations if obs.ticker == "ZC")
    assert zc.state == "SEVERE_DETERIORATION_EXIT"
    assert any(x.ticker == "ZC" and x.reason == "SEVERE_DETERIORATION_EXIT" for x in next_plan.sell_intents)
    assert "ZC" not in next_plan.target_positions
