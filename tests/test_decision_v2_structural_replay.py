from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v2_minimal import DecisionV2Intent, DecisionV2Plan
from idx_trade.decision_v2_structural_replay import (
    EXPECTED_NAIVE_TOP10_REPLACEMENTS,
    EXPECTED_SCORE_ROWS,
    EXPECTED_SCORE_SESSIONS,
    EXPECTED_SOURCE_MANIFEST_SHA256,
    EXPECTED_SOURCE_SCORE_SHA256,
    EXPECTED_V1_REPLACEMENTS,
    GATE_LIMITS,
    PinnedReplaySource,
    DecisionV2StructuralReplayError,
    _replacement_count,
    evaluate_gates,
    replay_once,
)
from idx_trade.v4_x1_decision_v2_minimal import (
    V4_X1_DECISION_V2_MINIMAL_PROFILE_V1,
)


def _synthetic_source(*, sessions: int = 600) -> PinnedReplaySource:
    tickers = [f"T{i:02d}" for i in range(30)]
    rows: list[dict[str, object]] = []
    dates = pd.date_range("2020-01-01", periods=sessions, freq="D")

    for index, date in enumerate(dates):
        order = list(tickers)
        # The first session of fold 2 gives incumbent T00 one bad observation.
        # It returns immediately on the next session. Continuous state must
        # therefore show EXIT_PENDING_1 at the fold boundary, never bootstrap.
        if index == 100:
            order.remove("T00")
            order.insert(24, "T00")
        for rank, ticker in enumerate(order, start=1):
            alpha = float(31 - rank)
            rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "fold": f"F{index // 100 + 1}",
                    "mode": "validation",
                    "alpha_h5": alpha,
                    "alpha_h10": alpha,
                    "alpha_consensus": alpha,
                    "rank_consensus": rank,
                }
            )

    return PinnedReplaySource(
        frame=pd.DataFrame(rows),
        manifest_path=Path("dummy_MANIFEST.json"),
        score_path=Path("dummy_scores.parquet"),
    )


def _passing_metrics() -> dict[str, object]:
    return {
        "turnover_churn": {
            "replacement_distribution": {"mean": 2.0},
            "transition_distribution": {"share_ge3": 0.30},
            "turnover_ratio_vs_naive_exact_daily_top10": 0.45,
        },
        "holding_persistence": {
            "completed_duration_sessions": {"median": 3.0},
            "one_session_holding_share": 0.30,
        },
        "rank_quality": {
            "mean_current_top10_overlap_full_target": 6.1,
            "mean_target_rank": 11.9,
        },
        "capacity": {
            "mean_target_size": 9.1,
            "share_target_size_10": 0.71,
            "share_target_size_le8": 0.09,
        },
        "correctness": {
            "no_target_size_gt10": True,
            "no_duplicate_target_ticker": True,
            "unqualified_nonbootstrap_entrant_violations": 0,
            "one_observation_gt20_exit_violations": 0,
            "confirmed_gt20_incumbent_retained_violations": 0,
            "soft_replacement_gap_violations": 0,
            "stale_state_violations": 0,
            "deterministic_second_pass_match": True,
        },
    }


def test_machine_contract_matches_frozen_runner_constants() -> None:
    payload = json.loads(
        Path(
            "docs/specs/decision_v2_minimal_structural_replay_contract_v1.json"
        ).read_text(encoding="utf-8")
    )

    assert payload["status"] == "FROZEN_BEFORE_FIRST_REPLAY"
    assert payload["source"]["manifest_sha256"] == EXPECTED_SOURCE_MANIFEST_SHA256
    assert payload["source"]["score_sha256"] == EXPECTED_SOURCE_SCORE_SHA256
    assert payload["source"]["score_sessions"] == EXPECTED_SCORE_SESSIONS
    assert payload["source"]["score_rows"] == EXPECTED_SCORE_ROWS
    assert (
        payload["comparators"]["naive_exact_daily_top10_replacements"]
        == EXPECTED_NAIVE_TOP10_REPLACEMENTS
    )
    assert (
        payload["comparators"]["frozen_decision_v1_replacements"]
        == EXPECTED_V1_REPLACEMENTS
    )
    assert (
        payload["hard_gates"]["B_churn_reduction"]
        ["mean_replacements_per_transition_max"]
        == GATE_LIMITS["mean_replacements_per_transition_max"]
    )
    assert (
        payload["hard_gates"]["D_rank_quality_preservation"]
        ["mean_target_rank_max"]
        == GATE_LIMITS["mean_target_rank_max"]
    )
    assert payload["runtime_invariants"]["exact_adjacent_t_minus_1_t_iteration"] is True
    assert payload["runtime_invariants"]["no_fold_reset"] is True
    assert payload["forbidden"]["historical_pnl"] is True
    assert payload["forbidden"]["decision_parameter_sweep"] is True


def test_replacement_metric_is_conservative_under_underfill() -> None:
    sells = tuple(
        DecisionV2Intent("SELL_INTENT", f"S{i}", 30 + i, "UNIVERSE_EXIT")
        for i in range(2)
    )
    buys = (
        DecisionV2Intent("BUY_INTENT", "B1", 3, "QUALIFIED_VACANCY_FILL"),
    )
    plan = DecisionV2Plan(
        decision_session_date="2026-01-03",
        current_shadow_positions=tuple(f"A{i}" for i in range(10)),
        target_positions=tuple(f"A{i}" for i in range(8)) + ("B1",),
        buy_intents=buys,
        sell_intents=sells,
        hold_tickers=tuple(f"A{i}" for i in range(8)),
        incumbent_observations=(),
        challenger_observations=(),
        unfilled_slots=1,
        capacity_state="UNFILLED_NO_QUALIFIED_CHALLENGER",
        rule_id=V4_X1_DECISION_V2_MINIMAL_PROFILE_V1.rule_id,
        bootstrap=False,
    )

    assert _replacement_count(plan) == 2


def test_replay_keeps_continuous_state_across_fold_boundary() -> None:
    source = _synthetic_source()
    first = replay_once(source)
    second = replay_once(source)

    assert len(first.session_ledger) == 600
    assert int(first.session_ledger["bootstrap"].sum()) == 1
    assert first.plan_digest == second.plan_digest

    boundary_session = first.session_ledger.loc[
        first.session_ledger["index"].eq(100)
    ].iloc[0]
    assert boundary_session["fold"] == "F2"
    assert bool(boundary_session["bootstrap"]) is False

    t00 = first.state_ledger.loc[
        first.state_ledger["index"].eq(100)
        & first.state_ledger["kind"].eq("INCUMBENT")
        & first.state_ledger["ticker"].eq("T00")
    ].iloc[0]
    assert t00["state"] == "EXIT_PENDING_1"

    boundary = first.fold_boundaries.loc[
        first.fold_boundaries["to_index"].eq(100)
    ].iloc[0]
    assert boundary["from_fold"] == "F1"
    assert boundary["to_fold"] == "F2"


def test_replay_fails_closed_if_session_count_changes() -> None:
    with pytest.raises(
        DecisionV2StructuralReplayError,
        match="SESSION_LEDGER_CHANGED",
    ):
        replay_once(_synthetic_source(sessions=599))


def test_all_hard_gates_must_pass_and_single_miss_rejects_group() -> None:
    metrics = _passing_metrics()
    gates = evaluate_gates(metrics)
    assert all(group["pass"] for group in gates.values())

    metrics["capacity"]["mean_target_size"] = 8.99
    gates = evaluate_gates(metrics)
    assert gates["E_capacity"]["pass"] is False
    assert gates["E_capacity"]["conditions"]["mean_target_size"] is False
