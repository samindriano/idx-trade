from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.ranking_v4_3_preregistration import (
    PRIMARY_MIN_ACTIVE_OBSERVATIONS,
    PRIMARY_VALUE_THRESHOLD_IDR,
    build_primary_liquid_state,
    build_session_geometry_features,
    equal_date_sample_weights,
    materialize_validation_folds,
    normalized_percentile_rank,
    validation_fold_positions,
)


ROOT = Path(__file__).resolve().parents[1]


def test_normalized_percentile_rank_has_exact_endpoints_and_average_ties() -> None:
    values = pd.Series([10.0, 20.0, 20.0, 30.0, np.nan])
    ranked = normalized_percentile_rank(values)
    assert ranked.iloc[:4].tolist() == [0.0, 0.5, 0.5, 1.0]
    assert np.isnan(ranked.iloc[4])
    singleton = normalized_percentile_rank(pd.Series([7.0]))
    assert singleton.iloc[0] == 0.5


def test_primary_liquid_state_uses_official_session_window_not_observed_row_window() -> None:
    sessions = pd.date_range("2024-01-01", periods=71, freq="D")
    dates = list(sessions[:20]) + [sessions[70]]
    panel = pd.DataFrame(
        {
            "ticker": ["AAA"] * len(dates),
            "date": dates,
            "regular_market_value": [PRIMARY_VALUE_THRESHOLD_IDR * 1.1] * len(dates),
        }
    )
    state = build_primary_liquid_state(panel, sessions)
    at_19 = state.loc[state["session_index"].eq(19)].iloc[0]
    at_70 = state.loc[state["session_index"].eq(70)].iloc[0]
    assert at_19["liquidity_active_observations_60"] == PRIMARY_MIN_ACTIVE_OBSERVATIONS
    assert bool(at_19["universe_primary_liquid"])
    assert at_70["liquidity_active_observations_60"] == 10
    assert not bool(at_70["universe_primary_liquid"])


def test_session_geometry_is_nonredundant_and_fails_closed_on_flat_or_missing_open() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "date": ["2024-01-02"] * 3,
            "open": [2.0, 1.0, np.nan],
            "high": [3.0, 1.0, 3.0],
            "low": [1.0, 1.0, 1.0],
            "close": [2.5, 1.0, 2.0],
        }
    )
    result = build_session_geometry_features(frame)
    assert np.isclose(result.loc[0, "session_open_position_range"], 0.5)
    assert np.isclose(result.loc[0, "session_body_signed_range"], 0.25)
    assert np.isclose(result.loc[0, "session_log_high_low_range"], np.log(3.0))
    assert np.isnan(result.loc[1, "session_open_position_range"])
    assert np.isnan(result.loc[1, "session_body_signed_range"])
    assert result.loc[1, "session_log_high_low_range"] == 0.0
    assert np.isnan(result.loc[2, "session_open_position_range"])
    assert np.isnan(result.loc[2, "session_body_signed_range"])
    assert np.isfinite(result.loc[2, "session_log_high_low_range"])


def test_equal_date_weights_equalize_each_date_and_keep_mean_one() -> None:
    dates = pd.Series(["2024-01-02"] * 2 + ["2024-01-03"] * 4)
    weights = equal_date_sample_weights(dates)
    normalized = pd.to_datetime(dates)
    totals = weights.groupby(normalized).sum()
    assert np.isclose(totals.iloc[0], totals.iloc[1])
    assert np.isclose(weights.mean(), 1.0)


def test_tail_600_fold_rule_and_official_session_purge_are_frozen() -> None:
    positions = validation_fold_positions(815)
    assert len(positions) == 6
    assert positions[0].eligible_start_position == 215
    assert positions[0].eligible_end_position == 314
    assert positions[-1].eligible_start_position == 715
    assert positions[-1].eligible_end_position == 814

    eligible = pd.DataFrame(
        {
            "session_index": np.arange(100, 915, dtype=int),
            "date": pd.date_range("2022-01-01", periods=815, freq="D"),
        }
    )
    folds = materialize_validation_folds(eligible)
    assert len(folds) == 600
    assert folds["fold"].value_counts().sort_index().tolist() == [100] * 6
    first = folds.iloc[0]
    assert first["session_index"] == 315
    assert first["max_training_signal_session_index"] == 304
    assert folds.iloc[-1]["session_index"] == 914


def test_machine_readable_preregistration_is_locked_and_provenance_exact() -> None:
    config_path = ROOT / "config" / "ranking_v4_3_preregistration.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["outcome_blind"] is True
    assert config["status"] == "V4_3_SCIENTIFIC_CONFIG_LOCKED_PRIMARY_LIQUID_SUPPORT_AND_FOLD_BYTES_PENDING"
    assert config["decision_universe"]["minimum_median_regular_market_value_idr"] == 1_000_000_000.0
    assert config["validation"]["shared_validation_calendar"] == "CONSENSUS_ELIGIBLE_PRIMARY_LIQUID"
    assert config["validation"]["selection_rule"] == "last 600 chronologically ordered consensus-eligible sessions"
    assert config["learner"]["hyperparameter_search"] is False
    assert config["learner"]["parameters"]["early_stopping"] is False
    assert config["control"]["feature_count"] == 25
    assert len(config["control"]["features"]) == 25
    assert config["challenger"]["added_feature_count"] == 3
    assert config["challenger"]["id"] == "V4_CHALLENGER_SESSION_GEOMETRY3"
    assert config["preprocessing"]["challenger_geometry_block"]["add_indicator"] is False
    assert config["absolute_viability_gates"]["all_gates_required"] is True
    assert config["challenger_incremental_promotion_gates"]["all_gates_required"] is True

    contract_path = ROOT / "docs" / "SIGNAL_RESEARCH_HLCV_CONTRACT.md"
    contract_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    assert contract_sha == "ffff2d21b275744a3a2b74c2f7d32be7b589f3c46cf9950c5ff45c48e5bffd73"
    assert config["provenance"]["signal_research_contract"]["git_blob_sha1"] == "4d034e628838f56a0c88b3f23e249fae51a803ac"
