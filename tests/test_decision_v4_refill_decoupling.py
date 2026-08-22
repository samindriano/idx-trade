from __future__ import annotations

from dataclasses import replace

from idx_trade.decision_v3_graded_evidence import (
    DecisionV3Profile,
    DecisionV3ShadowState,
    RankObservation,
    RankSession,
    plan_decision_v3_graded_evidence,
)
from idx_trade.decision_v4_refill_decoupling import (
    plan_decision_v4_refill_decoupling,
)


V3_PROFILE = DecisionV3Profile(
    rule_id="TEST_DECISION_V3_GRADED_EVIDENCE_V2",
    target_count_max=10,
    strong_zone_max_rank=10,
    retention_zone_max_rank=20,
    mild_deterioration_max_rank=50,
    soft_replacement_min_rank_advantage=5,
)
V4_PROFILE = replace(
    V3_PROFILE,
    rule_id="V4_X1_DECISION_V4_REFILL_DECOUPLING_V1",
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


def _previous(
    day: str = "2026-01-02",
    *,
    exclude: set[str] | None = None,
    **overrides: int,
) -> RankSession:
    assignments = {ticker: rank for rank, ticker in enumerate(HELD, start=1)}
    assignments.update(overrides)
    return _session(day, assignments, exclude=exclude)


def _state(
    rule_id: str,
    day: str = "2026-01-02",
    positions: tuple[str, ...] = HELD,
) -> DecisionV3ShadowState:
    return DecisionV3ShadowState(
        as_of_session_date=day,
        positions=positions,
        rule_id=rule_id,
    )


def _v4(
    current: RankSession,
    previous: RankSession,
    positions: tuple[str, ...] = HELD,
):
    return plan_decision_v4_refill_decoupling(
        current,
        previous,
        _state(V4_PROFILE.rule_id, positions=positions),
        V4_PROFILE,
    )


def _v3(
    current: RankSession,
    previous: RankSession,
    positions: tuple[str, ...] = HELD,
):
    return plan_decision_v3_graded_evidence(
        current,
        previous,
        _state(V3_PROFILE.rule_id, positions=positions),
        V3_PROFILE,
    )


def _normalized_to_v3(plan):
    return replace(plan, rule_id=V3_PROFILE.rule_id)


def test_bootstrap_is_exact_v3_parity_except_rule_id() -> None:
    current = _session(
        "2026-01-02",
        {ticker: rank for rank, ticker in enumerate(HELD, start=1)},
    )
    v3 = plan_decision_v3_graded_evidence(
        current,
        None,
        DecisionV3ShadowState.empty(),
        V3_PROFILE,
    )
    v4 = plan_decision_v4_refill_decoupling(
        current,
        None,
        DecisionV3ShadowState.empty(),
        V4_PROFILE,
    )
    assert _normalized_to_v3(v4) == v3
    assert v4.rule_id == "V4_X1_DECISION_V4_REFILL_DECOUPLING_V1"


def test_nonsevere_session_is_exact_v3_parity() -> None:
    previous = _previous(A1=25, A2=30, A3=40, ZA=15, ZB=35, ZC=60)
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
            "A1": 21,
            "A2": 22,
            "A3": 23,
        },
    )
    v3 = _v3(current, previous)
    v4 = _v4(current, previous)

    assert not any(
        obs.state == "SEVERE_DETERIORATION_EXIT"
        for obs in v4.incumbent_observations
    )
    assert _normalized_to_v3(v4) == v3
    assert {intent.ticker: intent.reason for intent in v4.buy_intents} == {
        "ZA": "TIER_A_VACANCY_FILL",
        "ZB": "TIER_B_VACANCY_FILL",
        "ZC": "TIER_C_RESIDUAL_VACANCY_FILL",
    }


def test_severe_session_blocks_b_and_c_for_all_vacancy_origins() -> None:
    previous = _previous(A2=25, ZA=15, ZB=35, ZC=60)
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
            "A2": 30,
            "A1": 51,
        },
        exclude={"A3"},
    )
    v4 = _v4(current, previous)

    states = {obs.ticker: obs.state for obs in v4.incumbent_observations}
    assert states["A1"] == "SEVERE_DETERIORATION_EXIT"
    assert states["A2"] == "CONFIRMED_MILD_DETERIORATION_EXIT"
    assert states["A3"] == "UNIVERSE_EXIT"

    buys = {intent.ticker: intent.reason for intent in v4.buy_intents}
    assert buys == {"ZA": "TIER_A_VACANCY_FILL"}
    assert "ZB" not in v4.target_positions
    assert "ZC" not in v4.target_positions
    assert v4.unfilled_slots == 2
    assert v4.capacity_state == "UNFILLED_NO_QUALIFIED_CHALLENGER"


def test_severe_session_diverges_from_v3_only_at_noncore_refill_permission() -> None:
    previous = _previous(ZA=15, ZB=35, ZC=60)
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
    v3 = _v3(current, previous)
    v4 = _v4(current, previous)

    assert {intent.ticker for intent in v3.buy_intents} == {"ZA", "ZB", "ZC"}
    assert {intent.ticker for intent in v4.buy_intents} == {"ZA"}
    assert v3.sell_intents == v4.sell_intents
    assert v3.incumbent_observations == v4.incumbent_observations
    assert v3.challenger_observations == v4.challenger_observations


def test_distant_challenger_does_not_create_severe_session_flag() -> None:
    previous = _previous(A1=25, ZC=60)
    current = _session(
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
            "A1": 30,
        },
    )
    v4 = _v4(current, previous)
    assert not any(
        obs.state == "SEVERE_DETERIORATION_EXIT"
        for obs in v4.incumbent_observations
    )
    assert any(
        intent.ticker == "ZC"
        and intent.reason == "TIER_C_RESIDUAL_VACANCY_FILL"
        for intent in v4.buy_intents
    )


def test_tier_a_soft_replacement_remains_active_on_severe_session() -> None:
    previous = _previous(ZA=15, ZB=18)
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
            "ZB": 10,
            "A10": 20,
            "A1": 51,
        },
    )
    v4 = _v4(current, previous)
    buys = {intent.ticker: intent for intent in v4.buy_intents}
    sells = {intent.ticker: intent for intent in v4.sell_intents}

    assert buys["ZA"].reason == "TIER_A_VACANCY_FILL"
    assert buys["ZB"].reason == "SOFT_RANK_GAP_REPLACEMENT"
    assert buys["ZB"].replacement_peer == "A10"
    assert sells["A10"].reason == "SOFT_RANK_GAP_REPLACEMENT"
    assert sells["A10"].replacement_peer == "ZB"
    assert "ZB" in v4.target_positions
    assert "A10" not in v4.target_positions


def test_tier_d_remains_forbidden_after_bootstrap() -> None:
    previous = _previous(exclude={"ZD"})
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
    v4 = _v4(current, previous)
    challenger = next(obs for obs in v4.challenger_observations if obs.ticker == "ZD")
    assert challenger.state == "D_NO_HISTORY"
    assert "ZD" not in v4.target_positions
    assert all(intent.ticker != "ZD" for intent in v4.buy_intents)
    assert v4.unfilled_slots == 1


def test_mild_grace_and_confirmed_exit_remain_unchanged() -> None:
    previous_first = _previous()
    current_first = _session(
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
            "A1": 35,
        },
    )
    first = _v4(current_first, previous_first)
    first_obs = next(obs for obs in first.incumbent_observations if obs.ticker == "A1")
    assert first_obs.state == "MILD_DETERIORATION_PENDING_1"
    assert "A1" in first.target_positions

    previous_second = _previous(day="2026-01-03", A1=35)
    current_second = _session(
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
            "A1": 40,
        },
    )
    second = plan_decision_v4_refill_decoupling(
        current_second,
        previous_second,
        _state(V4_PROFILE.rule_id, day="2026-01-03"),
        V4_PROFILE,
    )
    second_obs = next(obs for obs in second.incumbent_observations if obs.ticker == "A1")
    assert second_obs.state == "CONFIRMED_MILD_DETERIORATION_EXIT"
    assert "A1" not in second.target_positions


def test_severe_rank_over_50_still_exits_immediately() -> None:
    previous = _previous()
    current = _session(
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
            "A1": 51,
        },
    )
    v4 = _v4(current, previous)
    obs = next(obs for obs in v4.incumbent_observations if obs.ticker == "A1")
    assert obs.state == "SEVERE_DETERIORATION_EXIT"
    assert any(
        intent.ticker == "A1" and intent.reason == "SEVERE_DETERIORATION_EXIT"
        for intent in v4.sell_intents
    )
    assert "A1" not in v4.target_positions
