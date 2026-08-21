from __future__ import annotations

from pathlib import Path

import pandas as pd

from idx_trade.decision_v3_failure_diagnosis import (
    DecisionV3FailureDiagnosisResult,
    write_failure_diagnosis_artifacts,
)
from idx_trade.decision_v3_structural_source import sha256_file


def _result() -> DecisionV3FailureDiagnosisResult:
    return DecisionV3FailureDiagnosisResult(
        summary={
            "status": "COMPLETE_OUTCOME_BLIND_DECISION_V3_FAILURE_MECHANISM_DIAGNOSIS",
            "source": {"parent_plan_digest": "x"},
            "guards": {"counterfactual_policy_simulated": False},
        },
        severe_exit_sessions=pd.DataFrame(
            [{"session_index": 1, "severe_exit_count": 1, "replacement_count": 2}]
        ),
        entry_lifecycle=pd.DataFrame(
            [{"ticker": "AAA", "entry_index": 1, "entry_tier": "A"}]
        ),
        block_summary=pd.DataFrame([{"block": 1, "severe_exit_total": 1}]),
    )


def test_identical_result_writes_identical_artifact_bytes(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    manifest1 = write_failure_diagnosis_artifacts(_result(), first)
    manifest2 = write_failure_diagnosis_artifacts(_result(), second)

    for name in (
        "summary.json",
        "severe_exit_session_diagnosis.csv",
        "entry_tier_lifecycle_diagnosis.csv",
        "block_mechanism_summary.csv",
        "MANIFEST.json",
    ):
        assert (first / name).read_bytes() == (second / name).read_bytes()
        assert sha256_file(first / name) == sha256_file(second / name)

    assert sha256_file(manifest1) == sha256_file(manifest2)
