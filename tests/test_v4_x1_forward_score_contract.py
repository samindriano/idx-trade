from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.ranking_v4_3_preregistration import (
    build_session_geometry_features,
    normalized_percentile_rank,
)
from idx_trade.v4_x1_forward_score import (
    CHALLENGER_FEATURES,
    CONTROL_FEATURES,
    MODEL_ID,
    _score_one,
)


ROOT = Path(__file__).resolve().parents[1]
SCORER = ROOT / "src" / "idx_trade" / "v4_x1_forward_score.py"
RUNNER = ROOT / "scripts" / "run_v4_x1_forward_score.py"
FEATURES = ROOT / "src" / "idx_trade" / "ranking_v4_3_features.py"
PREREG = ROOT / "src" / "idx_trade" / "ranking_v4_3_preregistration.py"


def _git_blob(path: Path) -> str:
    return subprocess.run(
        ["git", "hash-object", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_frozen_v4_science_modules_are_byte_identical_to_research_parent() -> None:
    assert _git_blob(FEATURES) == "59ad05f815870ae00480dc7945fe18371d8eff9c"
    assert _git_blob(PREREG) == "cc1308feb51bbed16606bf7bded1ca0111644326"


def test_v4_x1_feature_contract_is_exact_25_plus_geometry3() -> None:
    assert MODEL_ID == "V4_X1_GEOMETRY3_PROSPECTIVE"
    assert len(CONTROL_FEATURES) == 25
    assert len(CHALLENGER_FEATURES) == 28
    assert CHALLENGER_FEATURES[-3:] == (
        "session_open_position_range",
        "session_body_signed_range",
        "session_log_high_low_range",
    )


def test_geometry3_formula_matches_frozen_contract() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["TEST"],
            "date": [pd.Timestamp("2026-08-19")],
            "open": [110.0],
            "high": [120.0],
            "low": [100.0],
            "close": [115.0],
        }
    )
    result = build_session_geometry_features(frame).iloc[0]
    assert result["session_open_position_range"] == 0.5
    assert result["session_body_signed_range"] == 0.25
    assert np.isclose(result["session_log_high_low_range"], np.log(1.2))


def test_model_output_rank_is_frozen_zero_to_one_percentile() -> None:
    class DummyModel:
        def predict(self, frame: pd.DataFrame) -> np.ndarray:
            return np.array([30.0, 10.0, 20.0])

    frame = pd.DataFrame({"ticker": ["A", "B", "C"]})
    raw, alpha = _score_one(DummyModel(), frame)
    assert raw.tolist() == [30.0, 10.0, 20.0]
    assert alpha.tolist() == [1.0, 0.0, 0.5]
    assert normalized_percentile_rank(pd.Series([30.0, 10.0, 20.0])).tolist() == alpha.tolist()


def test_scorer_is_outcome_blind_and_provider_call_free_by_contract() -> None:
    source = SCORER.read_text(encoding="utf-8")
    for forbidden in (
        "fetch_stock_summary_snapshot",
        "fetch_index_summary_snapshot",
        "download_daily",
        "run_exchange_session_backfill",
        "materialize_v4_target_ledger",
        "target_rank_h5",
        "target_rank_h10",
        "r5",
        "r10",
    ):
        assert forbidden not in source
    assert '"provider_calls": False' in source
    assert '"protected_outcome_accessed": False' in source
    assert '"realized_forward_outcome_loaded": False' in source
    assert '"model_refit": False' in source
    assert '"model_retuned": False' in source


def test_scorer_enforces_clean_freshness_and_chronological_next_session() -> None:
    source = SCORER.read_text(encoding="utf-8")
    assert "SESSION_EOD_PREDATES_MODEL_FREEZE" in source
    assert "V4_X1_SESSION_NOT_NEXT_CLEAN_PROSPECTIVE" in source
    assert "V4_X1_CANONICAL_HISTORY_GAP" in source
    assert "completed <= observed_by" in source
    assert "eod <= observed_by" in source
    assert "ignored_post_freeze_backfills" in source


def test_scorer_uses_snapshots_only_for_history_and_exact_ohlcv_for_candidate() -> None:
    source = SCORER.read_text(encoding="utf-8")
    assert "require_ohlcv_exact=day == candidate" in source
    assert "NOT_REQUIRED_FOR_FORWARD_FEATURE_HISTORY" in source
    assert "LEGACY_OPEN_ENRICHMENT_NOT_REQUIRED" in source
    assert "return snapshot, None, evidence" in source
    assert "EXACT_HLCV_REQUIRED_FOR_FRESH_GEOMETRY3_CANDIDATE" in source
    assert "compare_volume=True" in source
    assert "candidate_ohlcv_exact_hlcv_match" in source
    assert "V4_X1_CANDIDATE_OHLCV_NOT_VERIFIED" in source


def test_scorer_writes_one_bundle_artifact_with_both_control_and_challenger() -> None:
    source = SCORER.read_text(encoding="utf-8")
    for column in (
        "alpha_control_h5",
        "alpha_control_h10",
        "alpha_control_consensus",
        "alpha_h5",
        "alpha_h10",
        "alpha_consensus",
        "rank_consensus",
    ):
        assert column in source
    assert "0.5 * artifact[\"alpha_h5\"] + 0.5 * artifact[\"alpha_h10\"]" in source
    assert "_immutable_bytes(artifact_path, artifact_bytes)" in source
    assert "_immutable_bytes(manifest_path, manifest_bytes)" in source
    assert "V4_X1_SCORE_ALREADY_DONE_VERIFIED" in source


def test_new_python_files_parse() -> None:
    ast.parse(SCORER.read_text(encoding="utf-8"))
    ast.parse(RUNNER.read_text(encoding="utf-8"))
