from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_v4_x1_forward_readiness.py"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_readiness_script_is_read_only_and_pins_x1_manifest() -> None:
    source = _source()
    assert "3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094" in source
    assert "V4_X1_FINAL_REFIT_FROZEN_READY_FOR_FRESH_PROSPECTIVE_SCORING" in source
    assert "provider_calls\": False" in source
    assert "protected_outcome_accessed\": False" in source
    assert "model_scored\": False" in source
    assert "registry_mutated\": False" in source
    assert "sync_forward_calendar" not in source
    assert "fetch_stock_summary_snapshot" not in source
    assert "fetch_index_summary_snapshot" not in source
    assert "download_daily" not in source


def test_readiness_requires_exact_four_model_hashes() -> None:
    source = _source()
    for key in (
        "model_control_h5",
        "model_control_h10",
        "model_challenger_h5",
        "model_challenger_h10",
    ):
        assert key in source
    assert "V4_X1_MODEL_FILE_SHA_MISMATCH" in source


def test_readiness_checks_canonical_data_ready_history_and_candidate_ohlcv() -> None:
    source = _source()
    assert "FROM session_snapshots" in source
    assert 'row.get("state") == "DATA_READY"' in source
    assert "V4_X1_FORWARD_READYNESS_BLOCKED_CANONICAL_HISTORY_GAP" in source
    assert '"session_ohlcv.parquet"' in source
    assert "validate_ohlcv_against_model_input" in source
    assert "completed <= observed_by" in source


def test_readiness_does_not_require_legacy_open_for_feature_history() -> None:
    source = _source()
    assert "require_ohlcv_exact=normalized == candidate" in source
    assert "NOT_REQUIRED_FOR_FORWARD_FEATURE_HISTORY" in source
    assert "LEGACY_OPEN_ENRICHMENT_NOT_REQUIRED" in source
    assert "if not require_ohlcv_exact:" in source
    assert "return evidence" in source


def test_readiness_requires_exact_hlcv_for_fresh_candidate() -> None:
    source = _source()
    assert "EXACT_HLCV_REQUIRED_FOR_FRESH_GEOMETRY3_CANDIDATE" in source
    assert "compare_volume=True" in source
    assert "candidate_ohlcv_exact_hlcv_match" in source
    assert "V4_X1_CANDIDATE_SESSION_OHLCV_MISSING" in source


def test_readiness_rejects_old_sessions_backfilled_after_freeze() -> None:
    source = _source()
    assert "CANONICAL_EOD_CAPTURE_HOUR_JAKARTA = 18" in source
    assert "_session_eod_available_at_utc" in source
    assert "session_eod <= observed_by" in source
    assert "SESSION_EOD_PREDATES_MODEL_FREEZE" in source
    assert "ignored_post_freeze_backfills" in source
    assert "CANONICAL_SESSION_EOD_AND_DATA_READY_COMPLETION_BOTH_STRICTLY_AFTER_MODEL_FREEZE" in source


def test_script_parses() -> None:
    ast.parse(_source())