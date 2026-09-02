from __future__ import annotations

from pathlib import Path

import pytest

import idx_trade.e2e_paper_operational_controller_v1 as controller_v1
from idx_trade import v4_x1_clean_forward_score as clean_x1
from idx_trade.e2e_official_open_admission_v2 import (
    materialize_official_open_from_cloud_v2,
)
from scripts import run_e2e_paper_cloud_v1 as v1
from scripts import run_e2e_paper_cloud_v2 as v2
from scripts import run_e2e_paper_cloud_v3 as v3
from scripts import run_e2e_paper_cloud_v4 as v4


def test_split_observation_clock_preserves_runtime_now_and_freezes_downstream(monkeypatch):
    seen: dict[str, object] = {}
    runtime_now = "2026-09-02T12:40:52+00:00"

    def fake_with_runtime(original_pipeline, runtime_root, model_root, **kwargs):
        seen["outer_observed_by"] = kwargs.get("observed_by")
        return original_pipeline(runtime_root, model_root, **kwargs)

    def downstream(runtime_root, model_root, **kwargs):
        seen["inner_observed_by"] = kwargs.get("observed_by")
        return {"status": "PIPELINE_OK_TEST"}

    monkeypatch.setattr(v4, "_ORIGINAL_WITH_RUNTIME_SECURITY_MASTER", fake_with_runtime)
    result = v4._with_split_observation_clock(
        downstream,
        "runtime",
        "models",
        observed_by=runtime_now,
        population_input_manifest_sha256="a" * 64,
    )

    assert result == {"status": "PIPELINE_OK_TEST"}
    assert seen["outer_observed_by"] == runtime_now
    assert seen["inner_observed_by"] == clean_x1.DEFAULT_OBSERVED_BY


def _no_eligible_score(**overrides):
    score = {
        "status": "V4_X1_NO_ELIGIBLE_SAME_DAY_SCORE",
        "reason": "V4_X1_NO_GENUINELY_FRESH_DATA_READY_SESSION",
        "provider_calls": False,
        "protected_outcome_accessed": False,
        "model_refit": False,
        "model_retuned": False,
    }
    score.update(overrides)
    return score


def test_no_eligible_score_is_semantic_waiting_evidence_without_manifest_path():
    score = _no_eligible_score()
    result = v4._verify_score_pointer_semantic_first(
        {"x1_score": score},
        "2026-09-02",
        expected_forward_root=Path("/does/not/matter"),
    )
    assert result is score
    assert "manifest_path" not in score


def test_no_eligible_score_requires_known_reason():
    with pytest.raises(
        controller_v1.E2EOperationalGuardError,
        match="E2E_OPERATIONAL_NO_ELIGIBLE_SCORE_REASON_INVALID",
    ):
        v4._verify_score_pointer_semantic_first(
            {"x1_score": _no_eligible_score(reason="UNKNOWN_REASON")},
            "2026-09-02",
        )


def test_no_eligible_score_requires_false_guards():
    with pytest.raises(
        controller_v1.E2EOperationalGuardError,
        match="E2E_OPERATIONAL_NO_ELIGIBLE_SCORE_GUARDS_INVALID",
    ):
        v4._verify_score_pointer_semantic_first(
            {"x1_score": _no_eligible_score(provider_calls=True)},
            "2026-09-02",
        )


def test_unknown_score_status_fails_before_path_resolution():
    with pytest.raises(
        controller_v1.E2EOperationalGuardError,
        match="E2E_OPERATIONAL_SCORE_STATUS_INVALID",
    ):
        v4._verify_score_pointer_semantic_first(
            {"x1_score": {"status": "UNKNOWN"}},
            "2026-09-02",
            expected_forward_root=Path("/tmp/forward"),
        )


def test_real_score_status_delegates_to_existing_strict_verifier(monkeypatch):
    captured: dict[str, object] = {}
    expected = {"status": "VERIFIED_SENTINEL"}

    def fake_verify(pointer, session, *, expected_forward_root=None):
        captured["pointer"] = pointer
        captured["session"] = session
        captured["expected_forward_root"] = expected_forward_root
        return expected

    monkeypatch.setattr(v4, "_ORIGINAL_VERIFY_SCORE_POINTER", fake_verify)
    pointer = {"x1_score": {"status": "V4_X1_PROSPECTIVE_SCORE_DONE"}}
    root = Path("/tmp/forward")
    result = v4._verify_score_pointer_semantic_first(
        pointer,
        "2026-09-02",
        expected_forward_root=root,
    )

    assert result is expected
    assert captured == {
        "pointer": pointer,
        "session": "2026-09-02",
        "expected_forward_root": root,
    }


def test_run_once_applies_and_restores_v3_contract_patches(monkeypatch):
    original_runtime = v2._with_runtime_security_master
    original_verify = controller_v1._verify_score_pointer
    original_materialize = v1.materialize_official_open_from_cloud
    seen: dict[str, bool] = {}

    def fake_v3_run_once(*, phase=None, session_date=None):
        seen["runtime_patch_active"] = (
            v2._with_runtime_security_master is v4._with_split_observation_clock
        )
        seen["score_patch_active"] = (
            controller_v1._verify_score_pointer
            is v4._verify_score_pointer_semantic_first
        )
        seen["open_patch_active"] = (
            v1.materialize_official_open_from_cloud
            is materialize_official_open_from_cloud_v2
        )
        return {"status": "WAITING", "phase": phase, "session_date": session_date}

    monkeypatch.setattr(v3, "run_once", fake_v3_run_once)
    result = v4.run_once(phase="POST_EOD", session_date="2026-09-02")

    assert result["status"] == "WAITING"
    assert seen == {
        "runtime_patch_active": True,
        "score_patch_active": True,
        "open_patch_active": True,
    }
    assert v2._with_runtime_security_master is original_runtime
    assert controller_v1._verify_score_pointer is original_verify
    assert v1.materialize_official_open_from_cloud is original_materialize


def test_operational_contracts_restore_even_when_v3_raises(monkeypatch):
    original_runtime = v2._with_runtime_security_master
    original_verify = controller_v1._verify_score_pointer
    original_materialize = v1.materialize_official_open_from_cloud

    def boom(*, phase=None, session_date=None):
        assert v1.materialize_official_open_from_cloud is materialize_official_open_from_cloud_v2
        raise RuntimeError("sentinel")

    monkeypatch.setattr(v3, "run_once", boom)
    with pytest.raises(RuntimeError, match="sentinel"):
        v4.run_once(phase="PREOPEN", session_date="2026-09-02")

    assert v2._with_runtime_security_master is original_runtime
    assert controller_v1._verify_score_pointer is original_verify
    assert v1.materialize_official_open_from_cloud is original_materialize
