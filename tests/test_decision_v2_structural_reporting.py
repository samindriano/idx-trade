from __future__ import annotations

import pandas as pd

from idx_trade.decision_v2_structural_replay import ReplayPass, StructuralReplayResult
from idx_trade.decision_v2_structural_reporting import enrich_structural_replay_reporting
from idx_trade.decision_v2_structural_source import (
    EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256,
)


def test_reporting_adds_required_gt20_distribution_without_changing_gate_verdict() -> None:
    memberships = pd.DataFrame(
        [
            {"ticker": "A", "rank_consensus": 5},
            {"ticker": "B", "rank_consensus": 21},
            {"ticker": "B", "rank_consensus": 40},
            {"ticker": "C", "rank_consensus": 60},
        ]
    )
    sessions = pd.DataFrame(
        [
            {"target_rank_gt20_count": 0},
            {"target_rank_gt20_count": 1},
            {"target_rank_gt20_count": 2},
        ]
    )
    replay = ReplayPass(
        session_ledger=sessions,
        membership_ledger=memberships,
        intent_ledger=pd.DataFrame(),
        state_ledger=pd.DataFrame(),
        holding_spells=pd.DataFrame(),
        fold_boundaries=pd.DataFrame(),
        plan_digest="abc",
    )
    summary = {
        "status": "DECISION_V2_MINIMAL_STRUCTURAL_ACCEPT",
        "source": {"score_sha256": "x"},
        "metrics": {
            "rank_quality": {
                "target_rank_gt20_name_days": 3,
                "sessions_with_target_rank_gt20": 2,
            }
        },
        "gates": {"A": {"pass": True}},
    }
    result = StructuralReplayResult(primary=replay, summary=summary)

    enriched = enrich_structural_replay_reporting(result)

    assert enriched.summary["status"] == summary["status"]
    assert enriched.summary["gates"] == summary["gates"]
    rank_quality = enriched.summary["metrics"]["rank_quality"]
    assert rank_quality["target_rank_gt20_unique_tickers"] == 2
    assert rank_quality["target_rank_gt20_rank_distribution"]["median"] == 40.0
    assert rank_quality["target_rank_gt20_rank_distribution"]["max"] == 60.0
    assert (
        rank_quality["target_rank_gt20_count_per_session_distribution"]["max"]
        == 2.0
    )
    assert (
        enriched.summary["source"]["replay_contract_canonical_sha256"]
        == EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256
    )
    assert enriched.summary["reporting"]["gate_values_changed"] is False
