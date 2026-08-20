from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_a_structural_replay.py"
CONFIG_PATH = REPO_ROOT / "config" / "ranking_v4_x1_clean_phase_a_structural_replay_v1.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("v4_x1_clean_phase_a_runner_test", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = load_runner()


def test_config_preserves_outcome_blind_guards() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert cfg["schema_version"] == "ranking_v4_x1_clean_phase_a_structural_replay_v1"
    assert cfg["ca80_gate_rate"] == 0.8
    guards = cfg["hard_guards"]
    assert guards["old_support_must_exactly_match_stage_c_oracle"] is True
    assert guards["all_frozen_600_clean_dates_must_pass_ca80_before_phase_b_review"] is True
    for key in (
        "provider_calls_authorized",
        "network_calls_authorized",
        "numeric_target_access_authorized",
        "target_return_access_authorized",
        "target_rank_access_authorized",
        "model_fit_authorized",
        "model_scoring_authorized",
        "historical_prediction_authorized",
        "historical_performance_authorized",
        "protected_forward_access_authorized",
        "fresh_forward_access_authorized",
        "forward_counter_mutation_authorized",
        "data_mutation_authorized",
        "ca_semantics_change_authorized",
        "session_semantics_change_authorized",
        "v4_x2_reuse_authorized",
        "tuning_or_rescue_authorized",
        "phase_b_refit_authorized",
    ):
        assert guards[key] is False


def test_support_delta_reports_add_drop_without_numeric_targets() -> None:
    old = pd.DataFrame(
        {"ticker": ["AAA", "BBB"], "date": ["2024-01-02", "2024-01-02"]}
    )
    clean = pd.DataFrame(
        {"ticker": ["BBB", "CCC"], "date": ["2024-01-02", "2024-01-02"]}
    )
    delta, summary = runner.support_delta(old, clean, head="H5")
    assert summary == {
        "old_rows": 2,
        "clean_rows": 2,
        "shared_rows": 1,
        "added_rows": 1,
        "dropped_rows": 1,
        "added_tickers": 1,
        "dropped_tickers": 1,
        "added_dates": 1,
        "dropped_dates": 1,
    }
    assert set(delta["change"]) == {"ADD", "DROP"}
    assert set(delta["ticker"]) == {"AAA", "CCC"}


def test_assert_same_identity_is_order_insensitive() -> None:
    left = pd.DataFrame(
        {"ticker": ["BBB", "AAA"], "date": ["2024-01-03", "2024-01-02"]}
    )
    right = pd.DataFrame(
        {"ticker": ["AAA", "BBB"], "date": ["2024-01-02", "2024-01-03"]}
    )
    runner.assert_same_identity(left, right, label="TEST")


def test_assert_same_identity_fails_closed_on_difference() -> None:
    left = pd.DataFrame({"ticker": ["AAA"], "date": ["2024-01-02"]})
    right = pd.DataFrame({"ticker": ["BBB"], "date": ["2024-01-02"]})
    with pytest.raises(RuntimeError, match="OLD_H5_ORACLE_MISMATCH"):
        runner.assert_same_identity(left, right, label="OLD_H5_ORACLE")


def test_feature_delta_summary_tracks_missingness_and_primary_identity() -> None:
    features = [*runner.V4_CONTROL_FEATURE_COLUMNS, *runner.SESSION_GEOMETRY_FEATURE_COLUMNS]
    old_row = {"ticker": "AAA", "date": pd.Timestamp("2024-01-02")}
    clean_row = {"ticker": "AAA", "date": pd.Timestamp("2024-01-02")}
    for name in features:
        old_row[name] = 1.0
        clean_row[name] = 1.0
    clean_row[features[0]] = 2.0
    clean_row[features[1]] = np.nan
    old = pd.DataFrame([old_row, {**old_row, "ticker": "DROP"}])
    clean = pd.DataFrame([clean_row, {**clean_row, "ticker": "ADD"}])

    feature_summary, missing, identity_delta, primary = runner.feature_delta_summary(old, clean)
    first = feature_summary.set_index("feature").loc[features[0]]
    second = missing.set_index("feature").loc[features[1]]
    assert int(first["finite_value_changed_exact"]) == 1
    assert int(second["finite_to_missing"]) == 1
    assert set(identity_delta["change"]) == {"PRIMARY_ADD", "PRIMARY_DROP"}
    assert primary["shared_primary_rows"] == 1
    assert primary["primary_added_rows"] == 1
    assert primary["primary_dropped_rows"] == 1


def test_clean_price_evidence_uses_clean_panel_open_and_fails_closed_missing() -> None:
    panel = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "date": ["2024-01-02", "2024-01-03"],
            "open": [100.0, np.nan],
            "close": [101.0, 102.0],
        }
    )
    calendar = pd.DataFrame(
        {"date": pd.to_datetime(["2024-01-02", "2024-01-03"]), "session_index": [0, 1]}
    )
    anchors = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "as_of_date": ["2024-01-02", "2024-01-03"],
            "market": ["REGULAR", "REGULAR"],
            "state": ["ACTIVE", "ACTIVE"],
        }
    )
    intervals = pd.DataFrame(
        columns=["ticker", "effective_from", "effective_to", "market", "state"]
    )
    price, stats = runner.build_clean_price_evidence(panel, calendar, anchors, intervals)
    assert price["open_admitted"].tolist() == [True, False]
    assert stats["final_open_admitted"] == 1
    assert price.loc[0, "accepted_open"] == 100.0
    assert pd.isna(price.loc[1, "accepted_open"])


def test_old_price_evidence_prefers_derivative_and_uses_overlay_fallback() -> None:
    panel = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "date": ["2024-01-02", "2024-01-03"],
            "close": [101.0, 102.0],
        }
    )
    derivative = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "date": ["2024-01-02", "2024-01-03"],
            "open": [100.0, np.nan],
        }
    )
    overlay = pd.DataFrame(
        {"ticker": ["AAA"], "date": ["2024-01-03"], "recovered_open": [99.0]}
    )
    calendar = pd.DataFrame(
        {"date": pd.to_datetime(["2024-01-02", "2024-01-03"]), "session_index": [0, 1]}
    )
    anchors = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "as_of_date": ["2024-01-02", "2024-01-03"],
            "market": ["REGULAR", "REGULAR"],
            "state": ["ACTIVE", "ACTIVE"],
        }
    )
    intervals = pd.DataFrame(
        columns=["ticker", "effective_from", "effective_to", "market", "state"]
    )
    price, stats = runner.build_old_price_evidence(
        panel, calendar, derivative, overlay, anchors, intervals
    )
    assert price["accepted_open"].tolist() == [100.0, 99.0]
    assert price["open_admitted"].tolist() == [True, True]
    assert stats["final_open_admitted"] == 2


def test_old_price_evidence_rejects_conflicting_derivative_and_overlay() -> None:
    panel = pd.DataFrame({"ticker": ["AAA"], "date": ["2024-01-02"], "close": [101.0]})
    derivative = pd.DataFrame({"ticker": ["AAA"], "date": ["2024-01-02"], "open": [100.0]})
    overlay = pd.DataFrame({"ticker": ["AAA"], "date": ["2024-01-02"], "recovered_open": [99.0]})
    calendar = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"]), "session_index": [0]})
    anchors = pd.DataFrame(
        {"ticker": ["AAA"], "as_of_date": ["2024-01-02"], "market": ["REGULAR"], "state": ["ACTIVE"]}
    )
    intervals = pd.DataFrame(columns=["ticker", "effective_from", "effective_to", "market", "state"])
    with pytest.raises(RuntimeError, match="DERIVATIVE_OVERLAY_CONFLICT"):
        runner.build_old_price_evidence(panel, calendar, derivative, overlay, anchors, intervals)


def test_verify_execution_lock_rejects_any_model_fit_flag(tmp_path: Path) -> None:
    manifest = {
        "status": "V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK_CAPTURED_REPLAY_NOT_RUN",
        "runtime": {"exact_match": True},
        "provider_calls": False,
        "network_calls": False,
        "numeric_target_accessed": False,
        "model_fit": True,
        "model_scoring": False,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "protected_forward_outcomes_accessed": False,
        "forward_counter_mutated": False,
        "phase_a_replay_run": False,
    }
    path = tmp_path / "lock.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    cfg = {"accepted_execution_lock": {"manifest_sha256": runner.sha256_file(path)}}
    with pytest.raises(RuntimeError, match="GUARD_CHANGED:model_fit"):
        runner.verify_execution_lock(path, cfg)


def test_json_safe_removes_nonfinite_values() -> None:
    payload = runner.json_safe({"x": np.nan, "y": np.float64(2.0)})
    assert payload == {"x": None, "y": 2.0}
