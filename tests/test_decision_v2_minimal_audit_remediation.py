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


def _session(day: str, order: list[str]) -> RankSession:
    return RankSession(
        session_date=day,
        rows=tuple(
            RankObservation(ticker=ticker, rank=index)
            for index, ticker in enumerate(order, start=1)
        ),
    )


def _universe(*preferred: str, n: int = 30) -> list[str]:
    seen = set(preferred)
    fillers = [f"X{i:02d}" for i in range(1, n + 1) if f"X{i:02d}" not in seen]
    return list(preferred) + fillers[: n - len(preferred)]


def test_capacity_state_is_full_when_target_is_full() -> None:
    first = _session("2026-01-02", _universe(*[f"A{i}" for i in range(1, 11)]))
    plan = plan_decision_v2_minimal(first, None, DecisionV2ShadowState.empty(), PROFILE)

    assert plan.unfilled_slots == 0
    assert plan.capacity_state == "FULL"


def test_underfill_records_explicit_no_qualified_challenger_state() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session(
        "2026-01-02",
        _universe(
            "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10",
            "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "X11",
            "A1", "X12", "X13", "X14", "Z",
        ),
    )
    current = _session(
        "2026-01-03",
        _universe(
            "Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10",
            "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "A1",
        ),
    )
    state = DecisionV2ShadowState(
        as_of_session_date="2026-01-02",
        positions=tuple(held),
        rule_id=PROFILE.rule_id,
    )

    plan = plan_decision_v2_minimal(current, previous, state, PROFILE)

    assert len(plan.target_positions) == 9
    assert plan.unfilled_slots == 1
    assert plan.capacity_state == "UNFILLED_NO_QUALIFIED_CHALLENGER"
    assert not plan.buy_intents


def test_shadow_state_from_plan_binds_rule_identity() -> None:
    first = _session("2026-01-02", _universe(*[f"A{i}" for i in range(1, 11)]))
    plan = plan_decision_v2_minimal(first, None, DecisionV2ShadowState.empty(), PROFILE)

    state = DecisionV2ShadowState.from_plan(plan)

    assert state.as_of_session_date == plan.decision_session_date
    assert state.positions == plan.target_positions
    assert state.rule_id == PROFILE.rule_id


def test_bound_shadow_state_cannot_cross_profiles() -> None:
    first = _session("2026-01-02", _universe(*[f"A{i}" for i in range(1, 11)]))
    first_plan = plan_decision_v2_minimal(first, None, DecisionV2ShadowState.empty(), PROFILE)
    state = DecisionV2ShadowState.from_plan(first_plan)

    second = _session("2026-01-03", _universe(*[f"A{i}" for i in range(1, 11)]))
    other_profile = replace(PROFILE, rule_id="OTHER_DECISION_PROFILE")

    with pytest.raises(DecisionV2Error, match="SHADOW_RULE_ID_MISMATCH"):
        plan_decision_v2_minimal(second, first, state, other_profile)


def test_legacy_unbound_state_remains_generic_compatible() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    previous = _session("2026-01-02", _universe(*held))
    current = _session("2026-01-03", _universe(*held))
    legacy_state = DecisionV2ShadowState(
        as_of_session_date="2026-01-02",
        positions=tuple(held),
    )

    plan = plan_decision_v2_minimal(current, previous, legacy_state, PROFILE)

    assert plan.target_positions == tuple(held)
    assert plan.capacity_state == "FULL"
