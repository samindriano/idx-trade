from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v3_a_soft_vacancy_diagnosis import (
    ASoftVacancyDiagnosisResult,
    _bucket_current_rank,
    _bucket_previous_rank,
    _bucket_run,
    _bucket_severe,
    _bucket_top10_overlap,
    _bucket_top20_overlap,
    consecutive_rank_run,
    verify_a_soft_vacancy_contract,
    verify_quality_supply_manifest,
    write_a_soft_vacancy_artifacts,
)
from idx_trade.decision_v3_failure_diagnosis import DecisionV3FailureDiagnosisError


def test_frozen_contract_canonical_hash_matches_repository() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path = verify_a_soft_vacancy_contract(repo_root)
    assert path.name == "decision_v3_a_soft_vacancy_diagnosis_v1.json"


def test_reporting_buckets_are_exactly_frozen_boundaries() -> None:
    assert [_bucket_current_rank(x) for x in (1, 3, 4, 6, 7, 10)] == [
        "1-3",
        "1-3",
        "4-6",
        "4-6",
        "7-10",
        "7-10",
    ]
    assert [_bucket_previous_rank(x) for x in (1, 10, 11, 20)] == [
        "1-10",
        "1-10",
        "11-20",
        "11-20",
    ]
    assert [_bucket_run(x) for x in (1, 2, 3, 8)] == ["1", "2", ">=3", ">=3"]
    assert [_bucket_severe(x) for x in (0, 1, 2, 3, 9)] == [
        "0",
        "1",
        "2",
        ">=3",
        ">=3",
    ]
    assert [_bucket_top10_overlap(x) for x in (0, 3, 4, 6, 7, 10)] == [
        "0-3",
        "0-3",
        "4-6",
        "4-6",
        "7-10",
        "7-10",
    ]
    assert [_bucket_top20_overlap(x) for x in (0, 9, 10, 14, 15, 20)] == [
        "0-9",
        "0-9",
        "10-14",
        "10-14",
        "15-20",
        "15-20",
    ]


def test_consecutive_rank_run_stops_on_first_nonqualifying_or_missing() -> None:
    rank_maps = {
        0: {"AAA": 8},
        1: {"AAA": 6},
        2: {"AAA": 12},
        3: {"AAA": 7},
        4: {"AAA": 5},
    }
    assert consecutive_rank_run(
        ticker="AAA", entry_index=4, max_rank=10, rank_maps=rank_maps
    ) == 2
    assert consecutive_rank_run(
        ticker="AAA", entry_index=4, max_rank=20, rank_maps=rank_maps
    ) == 5
    assert consecutive_rank_run(
        ticker="BBB", entry_index=4, max_rank=20, rank_maps=rank_maps
    ) == 0


def test_quality_supply_parent_manifest_is_hash_guarded(tmp_path: Path) -> None:
    (tmp_path / "MANIFEST.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(
        DecisionV3FailureDiagnosisError,
        match="QUALITY_SUPPLY_PARENT_MANIFEST_SHA_CHANGED",
    ):
        verify_quality_supply_manifest(tmp_path)


def test_output_writer_is_fail_closed_on_existing_directory(tmp_path: Path) -> None:
    result = ASoftVacancyDiagnosisResult(
        summary={
            "status": "COMPLETE_OUTCOME_BLIND_DECISION_V3_A_SOFT_VACANCY_DIAGNOSIS",
            "scientific_boundary": {
                "decision_v4_implemented_or_replayed": False,
                "alternative_rule_or_wait_policy_simulated": False,
                "hypothetical_portfolio_or_pnl_computed": False,
                "returns_or_outcomes_accessed": False,
                "protected_or_fresh_forward_accessed": False,
                "model_refit_or_retune": False,
                "provider_or_network_called": False,
            },
        },
        entry_diagnosis=pd.DataFrame([{"ticker": "AAA"}]),
        stratified_next_severe=pd.DataFrame([{"dimension": "current_rank"}]),
        session_context_summary=pd.DataFrame([{"population": "ALL"}]),
    )
    out = tmp_path / "result"
    manifest = write_a_soft_vacancy_artifacts(result, out)
    assert manifest.is_file()
    with pytest.raises(DecisionV3FailureDiagnosisError, match="A_DIAGNOSIS_OUTPUT_EXISTS"):
        write_a_soft_vacancy_artifacts(result, out)
