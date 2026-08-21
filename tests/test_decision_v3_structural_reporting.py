from __future__ import annotations

from pathlib import Path

import pandas as pd

from idx_trade.decision_v3_structural_replay import ReplayTrace, StructuralReplayResult
from idx_trade.decision_v3_structural_reporting import enrich_structural_replay_reporting
from idx_trade.decision_v3_structural_source import REPLAY_CONTRACT_RELATIVE_PATH


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_reporting_enrichment_cannot_change_gates_or_verdict() -> None:
    trace = ReplayTrace(
        session_ledger=pd.DataFrame(
            [
                {
                    "session_index": 0,
                    "target_rank_gt20_count": 0,
                    "target_rank_gt50_count": 0,
                },
                {
                    "session_index": 1,
                    "target_rank_gt20_count": 2,
                    "target_rank_gt50_count": 1,
                },
            ]
        ),
        membership_ledger=pd.DataFrame(
            {"rank_consensus": [1, 5, 21, 60]}
        ),
        intent_ledger=pd.DataFrame(),
        state_ledger=pd.DataFrame(),
        holding_spells=pd.DataFrame(),
        fold_boundaries=pd.DataFrame(),
        plan_digest="x",
        correctness={},
    )
    original_gates = {"A": {"pass": False}}
    result = StructuralReplayResult(
        primary=trace,
        summary={
            "status": "DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_REJECT",
            "verdict": "DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_REJECT",
            "gates": original_gates,
        },
    )
    enriched = enrich_structural_replay_reporting(
        result, REPO_ROOT / REPLAY_CONTRACT_RELATIVE_PATH
    )
    assert enriched.summary["gates"] == original_gates
    assert enriched.summary["verdict"] == result.summary["verdict"]
    assert enriched.summary["reporting"]["gate_values_changed"] is False
    assert enriched.summary["reporting"]["target_rank_gt20_distribution"]["count"] == 2
    assert enriched.summary["reporting"]["target_rank_gt50_distribution"]["count"] == 1
