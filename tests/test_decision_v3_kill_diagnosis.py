from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v3_kill_diagnosis import (
    EXPECTED_PREREG_NORMALIZED_SHA256,
    DecisionV3KillDiagnosisError,
    DecisionV3KillDiagnosisResult,
    _fresh_summary,
    _supply_counts,
    normalized_text_sha256,
    previous_rank_bin,
    verify_kill_diagnosis_prereg,
    write_kill_diagnosis_artifacts,
)
from idx_trade.decision_v3_kill_source import (
    ALLOWED_KILL_DIAGNOSIS_SCORE_COLUMNS,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_prereg_normalized_hash_is_frozen() -> None:
    path = verify_kill_diagnosis_prereg(REPO_ROOT)
    assert normalized_text_sha256(path) == EXPECTED_PREREG_NORMALIZED_SHA256


def test_previous_rank_bins_are_reporting_strata() -> None:
    assert previous_rank_bin(None) == "ABSENT"
    assert previous_rank_bin(1) == "LE20"
    assert previous_rank_bin(20) == "LE20"
    assert previous_rank_bin(21) == "21_30"
    assert previous_rank_bin(30) == "21_30"
    assert previous_rank_bin(31) == "31_50"
    assert previous_rank_bin(50) == "31_50"
    assert previous_rank_bin(51) == "51_100"
    assert previous_rank_bin(100) == "51_100"
    assert previous_rank_bin(101) == "101_200"
    assert previous_rank_bin(200) == "101_200"
    assert previous_rank_bin(201) == "GT200"


def test_supply_counts_excludes_held_and_uses_previous_rank() -> None:
    top10 = {1: ("A", "B", "C", "D", "E")}
    held = {1: {"A"}}
    ranks = {
        (0, "A"): 5,
        (0, "B"): 18,
        (0, "C"): 25,
        (0, "D"): 45,
        (0, "E"): 120,
    }
    counts = _supply_counts(
        1,
        top10_by_index=top10,
        held_start=held,
        rank_lookup=ranks,
    )
    assert counts["LE20"] == 1
    assert counts["21_30"] == 1
    assert counts["31_50"] == 1
    assert counts["101_200"] == 1
    assert sum(counts.values()) == 4


def test_terminal_rows_are_excluded_from_next_session_denominator() -> None:
    frame = pd.DataFrame(
        [
            {
                "previous_rank_bin": "21_30",
                "next_evaluable": True,
                "next_top10": True,
                "next_top20": True,
                "next_present": True,
                "next_rank": 8,
            },
            {
                "previous_rank_bin": "21_30",
                "next_evaluable": False,
                "next_top10": False,
                "next_top20": False,
                "next_present": False,
                "next_rank": None,
            },
        ]
    )
    summary = _fresh_summary(frame)["by_previous_rank_bin"]["21_30"]
    assert summary["n"] == 2
    assert summary["eligible_next_session"] == 1
    assert summary["next_top10_rate"] == 1.0
    assert summary["next_top20_rate"] == 1.0


def test_consensus_only_loader_contract_excludes_heads() -> None:
    assert "alpha_consensus" in ALLOWED_KILL_DIAGNOSIS_SCORE_COLUMNS
    assert "alpha_h5" not in ALLOWED_KILL_DIAGNOSIS_SCORE_COLUMNS
    assert "alpha_h10" not in ALLOWED_KILL_DIAGNOSIS_SCORE_COLUMNS
    assert "return" not in " ".join(ALLOWED_KILL_DIAGNOSIS_SCORE_COLUMNS).lower()


def test_output_writer_refuses_existing_destination(tmp_path: Path) -> None:
    destination = tmp_path / "result"
    destination.mkdir()
    result = DecisionV3KillDiagnosisResult(
        summary={
            "status": "COMPLETE_OUTCOME_BLIND_DECISION_V3_KILL_DIAGNOSIS",
            "source": {},
            "guards": {},
        },
        global_fresh=pd.DataFrame(),
        severe_context=pd.DataFrame(),
        underfill_supply=pd.DataFrame(),
        block_summary=pd.DataFrame(),
    )
    with pytest.raises(
        DecisionV3KillDiagnosisError,
        match="DECISION_V3_KILL_DIAGNOSIS_OUTPUT_EXISTS",
    ):
        write_kill_diagnosis_artifacts(result, destination)


def test_runner_script_uses_safe_execution_path() -> None:
    text = (
        REPO_ROOT / "scripts/run_v4_x1_decision_v3_kill_diagnosis.py"
    ).read_text(encoding="utf-8")
    assert "run_kill_diagnosis_safe" in text
    assert "result = run_kill_diagnosis(" not in text
