from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess
import sys

import pandas as pd

from idx_trade.decision_v3_graded_evidence import (
    DecisionV3ShadowState,
    RankObservation,
    RankSession,
    plan_decision_v3_graded_evidence,
)
from idx_trade.decision_v3_structural_replay import (
    ReplayTrace,
    _empty_correctness,
    _high_churn_attribution,
    _tier_c_diagnostics,
    _validate_plan_permissions,
)
from idx_trade.v4_x1_decision_v3_graded_evidence import (
    V4_X1_DECISION_V3_GRADED_EVIDENCE_PROFILE_V2,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/run_v4_x1_decision_v3_graded_evidence_structural_replay.py"
HELD = tuple(f"A{i}" for i in range(1, 11))
UNIVERSE = list(HELD) + ["ZA", "ZB", "ZC", "ZD"] + [
    f"X{i:03d}" for i in range(1, 67)
]


def _session(day: str, assignments: dict[str, int]) -> RankSession:
    universe = list(UNIVERSE)
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


def _abc_plan():
    previous_assignments = {ticker: rank for rank, ticker in enumerate(HELD, start=1)}
    previous_assignments.update({"ZA": 15, "ZB": 30, "ZC": 60})
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
    profile = V4_X1_DECISION_V3_GRADED_EVIDENCE_PROFILE_V2
    state = DecisionV3ShadowState(
        as_of_session_date="2026-01-02",
        positions=HELD,
        rule_id=profile.rule_id,
    )
    plan = plan_decision_v3_graded_evidence(current, previous, state, profile)
    return previous, current, plan


def test_independent_permission_validator_accepts_exact_a_b_c_priority() -> None:
    previous, current, plan = _abc_plan()
    correctness = _empty_correctness()
    _validate_plan_permissions(
        plan=plan,
        index=1,
        current_block=_frame(current),
        previous_block=_frame(previous),
        start_positions=HELD,
        shuffled_plan=plan,
        correctness=correctness,
    )
    assert all(value == 0 for value in correctness.values())


def test_independent_permission_validator_detects_tier_b_soft_replacement_tamper() -> None:
    previous, current, plan = _abc_plan()
    buys = list(plan.buy_intents)
    position = next(i for i, item in enumerate(buys) if item.ticker == "ZB")
    buys[position] = replace(
        buys[position],
        reason="SOFT_RANK_GAP_REPLACEMENT",
        replacement_peer="A4",
    )
    tampered = replace(plan, buy_intents=tuple(buys))
    correctness = _empty_correctness()
    _validate_plan_permissions(
        plan=tampered,
        index=1,
        current_block=_frame(current),
        previous_block=_frame(previous),
        start_positions=HELD,
        shuffled_plan=tampered,
        correctness=correctness,
    )
    assert correctness["tier_b_c_soft_replacement_violation_count"] > 0
    assert correctness["tier_b_priority_or_permission_violation_count"] > 0
    assert correctness["soft_replacement_non_tier_a_or_gap_violation_count"] > 0


def _diagnostic_trace() -> ReplayTrace:
    sessions = pd.DataFrame(
        [
            {"session_index": 0, "replacement_count": 0},
            {"session_index": 1, "replacement_count": 1},
            {"session_index": 2, "replacement_count": 3},
        ]
    )
    intents = pd.DataFrame(
        [
            {
                "session_index": 1,
                "side": "BUY_INTENT",
                "ticker": "ZC",
                "reason": "TIER_C_RESIDUAL_VACANCY_FILL",
            },
            {
                "session_index": 2,
                "side": "SELL_INTENT",
                "ticker": "ZC",
                "reason": "SEVERE_DETERIORATION_EXIT",
            },
            {
                "session_index": 2,
                "side": "BUY_INTENT",
                "ticker": "ZA",
                "reason": "TIER_A_VACANCY_FILL",
            },
        ]
    )
    state = pd.DataFrame(
        [
            {
                "session_index": 2,
                "kind": "INCUMBENT",
                "ticker": "ZC",
                "state": "SEVERE_DETERIORATION_EXIT",
            }
        ]
    )
    spells = pd.DataFrame(
        [
            {
                "ticker": "ZC",
                "entry_reason": "TIER_C_RESIDUAL_VACANCY_FILL",
                "duration_sessions": 1,
                "completed": True,
                "right_censored": False,
            }
        ]
    )
    return ReplayTrace(
        session_ledger=sessions,
        membership_ledger=pd.DataFrame(),
        intent_ledger=intents,
        state_ledger=state,
        holding_spells=spells,
        fold_boundaries=pd.DataFrame(),
        plan_digest="diagnostic",
        correctness={},
    )


def test_tier_c_lifecycle_diagnostic_counts_next_session_severe_exit_once() -> None:
    diagnostic = _tier_c_diagnostics(_diagnostic_trace())
    assert diagnostic["tier_c_entrant_count"] == 1
    assert diagnostic["tier_c_one_session_holding_share"] == 1.0
    assert diagnostic["tier_c_next_session_severe_exit_count"] == 1
    assert diagnostic["tier_c_severe_exit_unique_sessions"] == 1
    assert (
        diagnostic[
            "replacement_seat_changes_on_tier_c_next_session_severe_exit_sessions"
        ]
        == 3
    )


def test_high_churn_attribution_is_component_reporting_not_single_label() -> None:
    attribution = _high_churn_attribution(_diagnostic_trace())
    assert attribution["high_churn_transition_count"] == 1
    assert attribution["components"]["SELL_INTENT:SEVERE_DETERIORATION_EXIT"][
        "transition_count"
    ] == 1
    assert attribution["components"]["BUY_INTENT:TIER_A_VACANCY_FILL"][
        "transition_count"
    ] == 1


def test_cli_rejects_bad_authorization_before_source_access(tmp_path: Path) -> None:
    output = tmp_path / "should-not-exist"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--authorization-token",
            "WRONG",
            "--historical-root",
            str(tmp_path / "missing-source"),
            "--output-dir",
            str(output),
            "--repo-root",
            str(REPO_ROOT),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert "DECISION_V3_REPLAY_AUTHORIZATION_TOKEN_REJECTED" in combined
    assert "DECISION_V3_REPLAY_SOURCE_MISSING" not in combined
    assert not output.exists()
