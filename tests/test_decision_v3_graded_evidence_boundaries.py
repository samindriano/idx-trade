from __future__ import annotations

import pytest

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
UNIVERSE = list(HELD) + ["Z"] + [f"X{i:03d}" for i in range(1, 71)]


def _session(day: str, assignments: dict[str, int]) -> RankSession:
    assert len(set(assignments.values())) == len(assignments)
    by_rank = {rank: ticker for ticker, rank in assignments.items()}
    remaining = [ticker for ticker in UNIVERSE if ticker not in assignments]
    rows = []
    cursor = 0
    for rank in range(1, len(UNIVERSE) + 1):
        ticker = by_rank.get(rank)
        if ticker is None:
            ticker = remaining[cursor]
            cursor += 1
        rows.append(RankObservation(ticker=ticker, rank=rank))
    return RankSession(day, tuple(rows))


def _previous(extra_rank: int | None = None) -> RankSession:
    assignments = {ticker: rank for rank, ticker in enumerate(HELD, start=1)}
    if extra_rank is not None:
        assignments["Z"] = extra_rank
    return _session("2026-01-02", assignments)


def _state() -> DecisionV3ShadowState:
    return DecisionV3ShadowState(
        as_of_session_date="2026-01-02",
        positions=HELD,
        rule_id=PROFILE.rule_id,
    )


@pytest.mark.parametrize(
    ("previous_rank", "expected_tier"),
    [
        (20, "A_CORE"),
        (21, "B_NEAR"),
        (50, "B_NEAR"),
        (51, "C_DISTANT"),
    ],
)
def test_challenger_exact_previous_rank_boundaries(
    previous_rank: int, expected_tier: str
) -> None:
    previous = _previous(previous_rank)
    current = _session(
        "2026-01-03",
        {
            "Z": 1,
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
    observation = next(x for x in plan.challenger_observations if x.ticker == "Z")
    assert observation.state == expected_tier


@pytest.mark.parametrize(
    ("current_rank", "previous_rank", "expected_state"),
    [
        (10, 10, "STRONG_HOLD"),
        (11, 10, "ACCEPTABLE_HOLD"),
        (20, 10, "ACCEPTABLE_HOLD"),
        (21, 20, "MILD_DETERIORATION_PENDING_1"),
        (50, 20, "MILD_DETERIORATION_PENDING_1"),
        (21, 21, "CONFIRMED_MILD_DETERIORATION_EXIT"),
        (50, 50, "CONFIRMED_MILD_DETERIORATION_EXIT"),
        (51, 20, "SEVERE_DETERIORATION_EXIT"),
    ],
)
def test_incumbent_exact_rank_boundaries(
    current_rank: int, previous_rank: int, expected_state: str
) -> None:
    previous_assignments = {
        ticker: rank for rank, ticker in enumerate(HELD[1:], start=1)
    }
    previous_assignments["A1"] = previous_rank
    previous = _session("2026-01-02", previous_assignments)

    current_assignments = {
        ticker: rank for rank, ticker in enumerate(HELD[1:], start=1)
    }
    # Move conflicting automatically assigned rank out of the way when needed.
    conflicting = next(
        (ticker for ticker, rank in current_assignments.items() if rank == current_rank),
        None,
    )
    if conflicting is not None:
        current_assignments[conflicting] = 60
    current_assignments["A1"] = current_rank
    current = _session("2026-01-03", current_assignments)

    state = DecisionV3ShadowState(
        as_of_session_date="2026-01-02",
        positions=HELD,
        rule_id=PROFILE.rule_id,
    )
    plan = plan_decision_v3_graded_evidence(current, previous, state, PROFILE)
    observation = next(x for x in plan.incumbent_observations if x.ticker == "A1")
    assert observation.state == expected_state
