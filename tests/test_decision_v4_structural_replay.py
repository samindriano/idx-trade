from __future__ import annotations

from dataclasses import replace

import pandas as pd

from idx_trade.decision_v3_graded_evidence import (
    DecisionV3Intent,
    DecisionV3ShadowState,
    RankObservation,
    RankSession,
)
from idx_trade.decision_v4_structural_replay import (
    _empty_correctness_v4,
    _validate_plan_permissions_v4,
    _v4_descriptive_diagnostics,
)
from idx_trade.v4_x1_decision_v4_refill_decoupling import (
    V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1,
)
from idx_trade.decision_v4_refill_decoupling import (
    plan_decision_v4_refill_decoupling,
)


PROFILE = V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1
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
    by_rank = {rank: ticker for ticker, rank in assignments.items()}
    assert len(by_rank) == len(assignments)
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


def _frame(session: RankSession) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime([session.session_date] * len(session.rows)),
            "ticker": [row.ticker for row in session.rows],
            "rank_consensus": [row.rank for row in session.rows],
        }
    )


def _severe_fixture():
    previous_assignments = {ticker: rank for rank, ticker in enumerate(HELD, start=1)}
    previous_assignments.update({"ZA": 15, "ZB": 35, "ZC": 60})
    previous = _session("2026-01-02", previous_assignments)
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
    state = DecisionV3ShadowState(
        as_of_session_date="2026-01-02",
        positions=HELD,
        rule_id=PROFILE.rule_id,
    )
    plan = plan_decision_v4_refill_decoupling(
        current,
        previous,
        state,
        PROFILE,
    )
    return previous, current, plan


def test_independent_validator_accepts_severe_a_only_refill_and_counts_blocked_seats() -> None:
    previous, current, plan = _severe_fixture()
    correctness = _empty_correctness_v4()
    severe, diagnostic = _validate_plan_permissions_v4(
        plan=plan,
        index=1,
        current_block=_frame(current),
        previous_block=_frame(previous),
        start_positions=HELD,
        shuffled_plan=plan,
        correctness=correctness,
    )
    assert severe is True
    assert diagnostic["vacancies_before_refill"] == 3
    assert diagnostic["tier_b_candidates_blocked"] == 1
    assert diagnostic["tier_c_candidates_blocked"] == 1
    assert all(value == 0 for value in correctness.values())


def test_independent_validator_detects_noncore_refill_on_severe_session() -> None:
    previous, current, plan = _severe_fixture()
    tampered_b = DecisionV3Intent(
        side="BUY_INTENT",
        ticker="ZB",
        rank_consensus=2,
        reason="TIER_B_VACANCY_FILL",
    )
    tampered = replace(plan, buy_intents=plan.buy_intents + (tampered_b,))
    correctness = _empty_correctness_v4()
    severe, _ = _validate_plan_permissions_v4(
        plan=tampered,
        index=1,
        current_block=_frame(current),
        previous_block=_frame(previous),
        start_positions=HELD,
        shuffled_plan=tampered,
        correctness=correctness,
    )
    assert severe is True
    assert correctness["severe_session_noncore_refill_violation_count"] > 0
    assert correctness["tier_b_priority_or_permission_violation_count"] > 0


def test_v4_descriptive_diagnostics_use_severe_rows_and_preserve_block_summary() -> None:
    from idx_trade.decision_v3_structural_replay import ReplayTrace

    sessions = pd.DataFrame(
        [
            {
                "session_index": 0,
                "severe_exit_session": False,
                "tier_a_vacancy_fill_count": 0,
                "tier_b_candidates_blocked": 0,
                "tier_c_candidates_blocked": 0,
                "target_size": 10,
                "unfilled_slots": 0,
            },
            {
                "session_index": 1,
                "severe_exit_session": True,
                "tier_a_vacancy_fill_count": 1,
                "tier_b_candidates_blocked": 1,
                "tier_c_candidates_blocked": 1,
                "target_size": 8,
                "unfilled_slots": 2,
            },
            {
                "session_index": 2,
                "severe_exit_session": True,
                "tier_a_vacancy_fill_count": 2,
                "tier_b_candidates_blocked": 1,
                "tier_c_candidates_blocked": 0,
                "target_size": 9,
                "unfilled_slots": 1,
            },
        ]
    )
    trace = ReplayTrace(
        session_ledger=sessions,
        membership_ledger=pd.DataFrame(),
        intent_ledger=pd.DataFrame(),
        state_ledger=pd.DataFrame(),
        holding_spells=pd.DataFrame(),
        fold_boundaries=pd.DataFrame(),
        plan_digest="diagnostic",
        correctness={},
    )
    block_summary = {"block_1": {"sessions": 3}}
    diagnostic = _v4_descriptive_diagnostics(trace, block_summary)
    assert diagnostic["severe_exit_session_count"] == 2
    assert diagnostic["tier_a_vacancy_fills_on_severe_sessions"] == 3
    assert diagnostic["tier_b_candidates_blocked_on_severe_sessions"] == 2
    assert diagnostic["tier_c_candidates_blocked_on_severe_sessions"] == 1
    assert diagnostic["underfilled_sessions_after_severity_conditioned_refill"] == 2
    assert diagnostic["vacancy_days_after_severity_conditioned_refill"] == 3
    assert diagnostic["block_1_to_6_churn_quality_capacity_summary"] == block_summary
