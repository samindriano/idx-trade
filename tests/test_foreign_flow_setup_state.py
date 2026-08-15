from __future__ import annotations

import math

import pytest

from idx_trade.foreign_flow_setup_state import (
    CrossSectionalPressure,
    DivergenceState,
    HistoricalAbnormality,
    ParticipationIntensity,
    PersistenceState,
    SetupLabel,
    SetupThresholds,
    classify_foreign_flow_setup,
)


def _row(**overrides: float) -> dict[str, float]:
    row = {
        "foreign_participation_1": 0.10,
        "foreign_flow_shock_percentile_120": 0.50,
        "xs_rank_foreign_flow_shock_mean_5": 0.50,
        "xs_rank_foreign_flow_shock_mean_20": 0.50,
        "foreign_weighted_persistence_5": 0.0,
        "foreign_weighted_persistence_20": 0.0,
        "foreign_flow_acceleration_5_20": 0.0,
        "foreign_flow_price_divergence_5": 0.0,
        "foreign_flow_price_divergence_20": 0.0,
    }
    row.update(overrides)
    return row


def test_high_participation_can_be_routine_while_low_participation_is_extreme_accumulation() -> None:
    high_participation_routine = classify_foreign_flow_setup(
        _row(
            foreign_participation_1=0.50,
            foreign_flow_shock_percentile_120=0.65,
            xs_rank_foreign_flow_shock_mean_5=0.55,
            xs_rank_foreign_flow_shock_mean_20=0.60,
            foreign_weighted_persistence_5=0.10,
            foreign_weighted_persistence_20=0.15,
        )
    )
    low_participation_extreme = classify_foreign_flow_setup(
        _row(
            foreign_participation_1=0.05,
            foreign_flow_shock_percentile_120=0.99,
            xs_rank_foreign_flow_shock_mean_5=0.95,
            xs_rank_foreign_flow_shock_mean_20=0.93,
            foreign_weighted_persistence_5=0.80,
            foreign_weighted_persistence_20=0.75,
            foreign_flow_acceleration_5_20=0.12,
            foreign_flow_price_divergence_5=0.30,
            foreign_flow_price_divergence_20=0.25,
        )
    )

    assert high_participation_routine.participation_intensity is ParticipationIntensity.HIGH
    assert high_participation_routine.historical_abnormality is HistoricalAbnormality.NORMAL
    assert high_participation_routine.setup_label is SetupLabel.HIGH_PARTICIPATION_ROUTINE_FLOW

    assert low_participation_extreme.participation_intensity is ParticipationIntensity.NORMAL
    assert (
        low_participation_extreme.historical_abnormality
        is HistoricalAbnormality.EXTREME_ACCUMULATION
    )
    assert low_participation_extreme.persistence is PersistenceState.ACCUMULATION
    assert low_participation_extreme.cross_sectional_pressure is CrossSectionalPressure.HIGH
    assert low_participation_extreme.divergence is DivergenceState.POSITIVE
    assert low_participation_extreme.setup_label is SetupLabel.STEALTH_ACCUMULATION_CANDIDATE


def test_high_participation_does_not_force_accumulation_label() -> None:
    state = classify_foreign_flow_setup(
        _row(
            foreign_participation_1=0.80,
            foreign_flow_shock_percentile_120=0.55,
            xs_rank_foreign_flow_shock_mean_5=0.45,
            xs_rank_foreign_flow_shock_mean_20=0.48,
        )
    )
    assert state.participation_intensity is ParticipationIntensity.HIGH
    assert state.historical_abnormality is HistoricalAbnormality.NORMAL
    assert state.setup_label is SetupLabel.HIGH_PARTICIPATION_ROUTINE_FLOW


def test_extreme_accumulation_can_be_detected_without_high_current_participation() -> None:
    state = classify_foreign_flow_setup(
        _row(
            foreign_participation_1=0.02,
            foreign_flow_shock_percentile_120=0.97,
            xs_rank_foreign_flow_shock_mean_5=0.85,
            xs_rank_foreign_flow_shock_mean_20=0.88,
            foreign_weighted_persistence_5=0.70,
            foreign_weighted_persistence_20=0.65,
            foreign_flow_price_divergence_5=0.24,
            foreign_flow_price_divergence_20=0.22,
        )
    )
    assert state.participation_intensity is ParticipationIntensity.LOW
    assert state.historical_abnormality is HistoricalAbnormality.EXTREME_ACCUMULATION
    assert state.setup_label is SetupLabel.STEALTH_ACCUMULATION_CANDIDATE


def test_distribution_pressure_is_symmetric() -> None:
    state = classify_foreign_flow_setup(
        _row(
            foreign_participation_1=-0.12,
            foreign_flow_shock_percentile_120=0.03,
            xs_rank_foreign_flow_shock_mean_5=0.10,
            xs_rank_foreign_flow_shock_mean_20=0.15,
            foreign_weighted_persistence_5=-0.80,
            foreign_weighted_persistence_20=-0.75,
            foreign_flow_acceleration_5_20=-0.15,
            foreign_flow_price_divergence_5=-0.25,
            foreign_flow_price_divergence_20=-0.30,
        )
    )
    assert state.historical_abnormality is HistoricalAbnormality.EXTREME_DISTRIBUTION
    assert state.persistence is PersistenceState.DISTRIBUTION
    assert state.divergence is DivergenceState.NEGATIVE
    assert state.setup_label is SetupLabel.DISTRIBUTION_PRESSURE


def test_missing_required_fields_fail_closed() -> None:
    row = _row()
    row["foreign_flow_shock_percentile_120"] = math.nan
    state = classify_foreign_flow_setup(row)
    assert state.setup_label is SetupLabel.INDETERMINATE
    assert "foreign_flow_shock_percentile_120" in state.missing_fields


def test_out_of_range_rank_fails_closed() -> None:
    state = classify_foreign_flow_setup(
        _row(xs_rank_foreign_flow_shock_mean_5=1.2)
    )
    assert state.cross_sectional_pressure is CrossSectionalPressure.INDETERMINATE
    assert state.setup_label is SetupLabel.INDETERMINATE


def test_threshold_contract_rejects_invalid_ordering() -> None:
    with pytest.raises(ValueError, match="historical abnormality"):
        SetupThresholds(
            abnormal_distribution_ceiling=0.85,
            abnormal_accumulation_floor=0.80,
        )
