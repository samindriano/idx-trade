from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from idx_trade.ranking_v4_3_ca_admission import (
    V43CAAdmissionError,
    verify_v4_3_ca_admission_inputs,
)


RIGHTS_SHA = "5af9284d88a7621f3b400fe7f9a28e104459ae6e710e47bf765974c940daaa91"
RUNTIME_SHA = "cf6f1b0c859dd21b1c0f377f45d62ecdc98165ff6e0975b852a85b11cfbcaac6"
PER_DATE_SHA = "c84210982a0945dea1b6609e120f8768592ad8b558ad4d12d4bcb29e3dafdfee"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixture(
    tmp_path: Path,
    *,
    min_rate: float = 0.91,
    target_loaded: bool = False,
    rights_transition: str = "2024-04-17",
    model_fit_guardrail: bool = False,
    unresolved: int = 9,
):
    pit = tmp_path / "pit"
    execution = tmp_path / "execution"
    ca = tmp_path / "ca"
    pit.mkdir()
    execution.mkdir()
    ca.mkdir()

    pit_manifest = pit / "manifest.json"
    _write_json(pit_manifest, {"status": "PIT_SUPPORT_ACCEPTED"})

    execution_manifest = execution / "v4_3_execution_code_manifest.json"
    _write_json(
        execution_manifest,
        {
            "schema_version": "ranking_v4_3_execution_code_manifest_v1",
            "status": "V4_3_EXECUTION_CODE_IDENTITY_CAPTURED_NO_HISTORICAL_TARGET_ACCESS",
            "outcome_blind": True,
            "historical_target_loaded": target_loaded,
            "historical_model_fit": False,
            "historical_prediction_generated": False,
            "historical_performance_computed": False,
            "provider_calls": False,
            "runtime": {
                "accepted_manifest_sha256": RUNTIME_SHA,
                "exact_match": True,
            },
            "canonical_git_source_sha256": {
                f"source_{i}": f"sha_{i}" for i in range(16)
            },
        },
    )

    replay = ca / "final_continuity_611_fren_ksei_exact"
    replay.mkdir(parents=True)
    ledger = replay / "v4_frozen_continuity_ledger_event_window.csv"
    ledger.write_text("ticker,signal_date,horizon,continuity_status\n", encoding="utf-8")

    summary = replay / "summary.json"
    _write_json(
        summary,
        {
            "verdict": "V4_CA_EVENT_WINDOW_CONTINUITY_CERTIFIED",
            "corporate_action_continuity_certified": True,
            "coverage_certified_tickers": 602,
            "coverage_unresolved_tickers": unresolved,
            "cross_source_conflict_tickers": [],
            "frozen_dates": 600,
            "frozen_rows": 345394,
            "frozen_tickers": 611,
            "per_date": {
                "h5_gate_dates": 600,
                "h5_min_rate": min_rate,
                "h10_gate_dates": 600,
                "h10_min_rate": min_rate,
                "consensus_gate_dates": 600,
                "consensus_min_rate": min_rate,
            },
            "output_hashes": {"per_date": PER_DATE_SHA},
        },
    )

    overlay = ca / "fren_ksei_exact_overlay.json"
    _write_json(
        overlay,
        {
            "schema_version": "v4_ca_fren_ksei_exact_replay_v1",
            "status": "V4_CA_FREN_KSEI_EXACT_REPLAY_COMPLETE",
            "outcome_blind": True,
            "offline_replay": True,
            "provider_calls": False,
            "model_fit": model_fit_guardrail,
            "performance_computed": False,
            "prediction_generated": False,
            "target_or_rank_materialized": False,
            "protected_forward_accessed": False,
            "price_inference": False,
            "record_date_inference": False,
            "excl_price_stitching": False,
            "rights_pdf_sha256": RIGHTS_SHA,
            "rights_transition_date": rights_transition,
            "merger_transition_date": "2025-04-16",
        },
    )

    ca_manifest = ca / "MANIFEST.json"
    _write_json(
        ca_manifest,
        {
            "schema_version": "v4_ca_fren_ksei_exact_manifest_v1",
            "status": "V4_CA_FREN_KSEI_EXACT_REPLAY_COMPLETE",
            "outcome_blind": True,
            "offline_replay": True,
            "overlay_sha256": _sha(overlay),
            "continuity_summary_sha256": _sha(summary),
            "continuity_window_sha256": _sha(ledger),
        },
    )

    contract = {
        "schema_version": "ranking_v4_3_ca_admission_v1",
        "status": "V4_3_CA_ADMISSION_FROZEN_PRE_TARGET_ACCESS",
        "outcome_blind": True,
        "scientific_config_mutable": False,
        "historical_target_access_before_pass": False,
        "historical_model_fit_before_pass": False,
        "historical_performance_access_before_pass": False,
        "parents": {
            "v4_3_prefit_runtime_manifest_sha256": RUNTIME_SHA,
            "v4_3_pit_support_manifest_sha256": _sha(pit_manifest),
            "v4_3_execution_code_manifest_sha256": _sha(execution_manifest),
            "v4_ca_final_manifest_sha256": _sha(ca_manifest),
            "v4_ca_final_continuity_summary_sha256": _sha(summary),
            "v4_ca_final_continuity_ledger_sha256": _sha(ledger),
            "v4_ca_final_per_date_sha256": PER_DATE_SHA,
        },
        "ca_gate": {
            "required_verdict": "V4_CA_EVENT_WINDOW_CONTINUITY_CERTIFIED",
            "required_corporate_action_continuity_certified": True,
            "required_frozen_dates": 600,
            "required_frozen_rows": 345394,
            "required_frozen_tickers": 611,
            "minimum_per_date_rate": 0.9,
            "required_gate_dates": {"h5": 600, "h10": 600, "consensus": 600},
            "required_cross_source_conflict_tickers": 0,
            "expected_coverage_certified_tickers": 602,
            "expected_coverage_unresolved_tickers": 9,
            "remaining_unresolved_outside_material_six_is_allowed": True,
        },
        "required_guardrails": {
            "outcome_blind": True,
            "model_fit": False,
            "performance_computed": False,
            "prediction_generated": False,
            "target_or_rank_materialized": False,
            "protected_forward_accessed": False,
            "provider_calls": False,
            "price_inference": False,
            "record_date_inference": False,
            "excl_price_stitching": False,
        },
        "authorization_on_pass": {
            "historical_target_materialization": True,
            "historical_target_rank_materialization": True,
            "historical_model_fit": True,
            "historical_prediction_generation": True,
            "historical_frozen_evaluation": True,
            "scientific_config_changes": False,
            "post_result_rescue": False,
            "new_provider_calls": False,
            "protected_forward_access": False,
        },
    }
    return contract, ca, pit, execution


def _verify(fixture):
    contract, ca, pit, execution = fixture
    return verify_v4_3_ca_admission_inputs(
        contract=contract,
        ca_root=ca,
        pit_support_root=pit,
        execution_code_root=execution,
    )


def test_ca_admission_happy_path(tmp_path: Path):
    result = _verify(_fixture(tmp_path))
    assert result["frozen_dates"] == 600
    assert result["coverage_certified_tickers"] == 602
    assert result["coverage_unresolved_tickers"] == 9
    assert result["ca_per_date_min_rates"] == {
        "h5": 0.91,
        "h10": 0.91,
        "consensus": 0.91,
    }
    assert result["authorization_on_pass"]["historical_model_fit"] is True


def test_ca_admission_rejects_below_90_percent(tmp_path: Path):
    with pytest.raises(V43CAAdmissionError, match="CA_H5_MIN_RATE_FAILED"):
        _verify(_fixture(tmp_path, min_rate=0.899999))


def test_ca_admission_rejects_prior_target_access(tmp_path: Path):
    with pytest.raises(V43CAAdmissionError, match="HISTORICAL_TARGET_LOADED_MISMATCH"):
        _verify(_fixture(tmp_path, target_loaded=True))


def test_ca_admission_rejects_fren_transition_change(tmp_path: Path):
    with pytest.raises(V43CAAdmissionError, match="FREN_RIGHTS_TRANSITION_CHANGED"):
        _verify(_fixture(tmp_path, rights_transition="2024-04-18"))


def test_ca_admission_rejects_guardrail_flip(tmp_path: Path):
    with pytest.raises(V43CAAdmissionError, match="CA_GUARDRAIL_MODEL_FIT_MISMATCH"):
        _verify(_fixture(tmp_path, model_fit_guardrail=True))


def test_ca_admission_requires_exact_unresolved_count(tmp_path: Path):
    with pytest.raises(V43CAAdmissionError, match="COVERAGE_UNRESOLVED_TICKERS_MISMATCH"):
        _verify(_fixture(tmp_path, unresolved=10))


def test_ca_admission_rejects_byte_tamper_before_semantics(tmp_path: Path):
    contract, ca, pit, execution = _fixture(tmp_path)
    ledger = (
        ca
        / "final_continuity_611_fren_ksei_exact"
        / "v4_frozen_continuity_ledger_event_window.csv"
    )
    ledger.write_text(ledger.read_text(encoding="utf-8") + "TAMPER\n", encoding="utf-8")
    with pytest.raises(V43CAAdmissionError, match="CA_FINAL_CONTINUITY_LEDGER_SHA_MISMATCH"):
        verify_v4_3_ca_admission_inputs(
            contract=contract,
            ca_root=ca,
            pit_support_root=pit,
            execution_code_root=execution,
        )
