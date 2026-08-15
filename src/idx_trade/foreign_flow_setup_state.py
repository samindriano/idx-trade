"""Outcome-blind descriptive Foreign Flow setup-state classifier.

This module deliberately keeps current participation separate from historical
abnormality. It consumes only accepted Foreign Flow V2 representation fields
and produces deterministic descriptive states for prospective use.

It is not an alpha model and must not consume labels or protected outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Mapping


class ParticipationIntensity(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    INDETERMINATE = "INDETERMINATE"


class FlowDirection(StrEnum):
    DISTRIBUTION = "DISTRIBUTION"
    FLAT = "FLAT"
    ACCUMULATION = "ACCUMULATION"
    INDETERMINATE = "INDETERMINATE"


class HistoricalAbnormality(StrEnum):
    EXTREME_DISTRIBUTION = "EXTREME_DISTRIBUTION"
    DISTRIBUTION = "DISTRIBUTION"
    NORMAL = "NORMAL"
    ACCUMULATION = "ACCUMULATION"
    EXTREME_ACCUMULATION = "EXTREME_ACCUMULATION"
    INDETERMINATE = "INDETERMINATE"


class PersistenceState(StrEnum):
    DISTRIBUTION = "DISTRIBUTION"
    MIXED = "MIXED"
    ACCUMULATION = "ACCUMULATION"
    INDETERMINATE = "INDETERMINATE"


class CrossSectionalPressure(StrEnum):
    LOW = "LOW"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    INDETERMINATE = "INDETERMINATE"


class DivergenceState(StrEnum):
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"
    INDETERMINATE = "INDETERMINATE"


class SetupLabel(StrEnum):
    HIGH_PARTICIPATION_ROUTINE_FLOW = "HIGH_PARTICIPATION_ROUTINE_FLOW"
    ABNORMAL_ACCUMULATION = "ABNORMAL_ACCUMULATION"
    PERSISTENT_ACCUMULATION = "PERSISTENT_ACCUMULATION"
    STEALTH_ACCUMULATION_CANDIDATE = "STEALTH_ACCUMULATION_CANDIDATE"
    DISTRIBUTION_PRESSURE = "DISTRIBUTION_PRESSURE"
    NEUTRAL_OR_MIXED = "NEUTRAL_OR_MIXED"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class SetupThresholds:
    """Coarse descriptive bands frozen without outcome optimization."""

    participation_normal_floor: float = 0.05
    participation_high_floor: float = 0.20
    abnormal_distribution_ceiling: float = 0.20
    extreme_distribution_ceiling: float = 0.05
    abnormal_accumulation_floor: float = 0.80
    extreme_accumulation_floor: float = 0.95
    persistence_floor: float = 0.50
    xs_elevated_floor: float = 0.50
    xs_high_floor: float = 0.80
    divergence_threshold: float = 0.20

    def __post_init__(self) -> None:
        values = self.__dict__
        if any(not isfinite(float(value)) for value in values.values()):
            raise ValueError("setup thresholds must be finite")
        if not 0.0 <= self.participation_normal_floor < self.participation_high_floor:
            raise ValueError("invalid participation thresholds")
        if not (
            0.0
            <= self.extreme_distribution_ceiling
            < self.abnormal_distribution_ceiling
            < self.abnormal_accumulation_floor
            < self.extreme_accumulation_floor
            <= 1.0
        ):
            raise ValueError("invalid historical abnormality thresholds")
        if not 0.0 <= self.persistence_floor <= 1.0:
            raise ValueError("invalid persistence threshold")
        if not 0.0 <= self.xs_elevated_floor < self.xs_high_floor <= 1.0:
            raise ValueError("invalid cross-sectional thresholds")
        if not 0.0 <= self.divergence_threshold <= 1.0:
            raise ValueError("invalid divergence threshold")


DEFAULT_THRESHOLDS = SetupThresholds()

REQUIRED_FIELDS = (
    "foreign_participation_1",
    "foreign_flow_shock_percentile_120",
    "xs_rank_foreign_flow_shock_mean_5",
    "xs_rank_foreign_flow_shock_mean_20",
    "foreign_weighted_persistence_5",
    "foreign_weighted_persistence_20",
    "foreign_flow_acceleration_5_20",
    "foreign_flow_price_divergence_5",
    "foreign_flow_price_divergence_20",
)

FORBIDDEN_KEY_TOKENS = (
    "binary_target",
    "label_status",
    "outcome",
    "tp_first",
    "sl_first",
    "realized",
)


@dataclass(frozen=True)
class ForeignFlowSetupState:
    participation_intensity: ParticipationIntensity
    participation_direction: FlowDirection
    historical_abnormality: HistoricalAbnormality
    persistence: PersistenceState
    cross_sectional_pressure: CrossSectionalPressure
    divergence: DivergenceState
    acceleration_direction: FlowDirection
    setup_label: SetupLabel
    missing_fields: tuple[str, ...] = ()


def _assert_outcome_blind(row: Mapping[str, object]) -> None:
    forbidden = sorted(
        str(key)
        for key in row
        if any(token in str(key).lower() for token in FORBIDDEN_KEY_TOKENS)
    )
    if forbidden:
        raise ValueError(f"setup-state input must be outcome-blind: {forbidden}")


def _finite_value(row: Mapping[str, object], field: str) -> float | None:
    value = row.get(field)
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) else None


def _direction(value: float, *, zero_band: float = 0.0) -> FlowDirection:
    if value > zero_band:
        return FlowDirection.ACCUMULATION
    if value < -zero_band:
        return FlowDirection.DISTRIBUTION
    return FlowDirection.FLAT


def _participation_intensity(value: float, thresholds: SetupThresholds) -> ParticipationIntensity:
    magnitude = abs(value)
    if magnitude >= thresholds.participation_high_floor:
        return ParticipationIntensity.HIGH
    if magnitude >= thresholds.participation_normal_floor:
        return ParticipationIntensity.NORMAL
    return ParticipationIntensity.LOW


def _historical_abnormality(
    percentile: float, thresholds: SetupThresholds
) -> HistoricalAbnormality:
    if not 0.0 <= percentile <= 1.0:
        return HistoricalAbnormality.INDETERMINATE
    if percentile <= thresholds.extreme_distribution_ceiling:
        return HistoricalAbnormality.EXTREME_DISTRIBUTION
    if percentile <= thresholds.abnormal_distribution_ceiling:
        return HistoricalAbnormality.DISTRIBUTION
    if percentile >= thresholds.extreme_accumulation_floor:
        return HistoricalAbnormality.EXTREME_ACCUMULATION
    if percentile >= thresholds.abnormal_accumulation_floor:
        return HistoricalAbnormality.ACCUMULATION
    return HistoricalAbnormality.NORMAL


def _persistence(
    persistence_5: float,
    persistence_20: float,
    thresholds: SetupThresholds,
) -> PersistenceState:
    floor = thresholds.persistence_floor
    if persistence_20 >= floor and persistence_5 >= 0.0:
        return PersistenceState.ACCUMULATION
    if persistence_20 <= -floor and persistence_5 <= 0.0:
        return PersistenceState.DISTRIBUTION
    return PersistenceState.MIXED


def _xs_pressure(rank_5: float, rank_20: float, thresholds: SetupThresholds) -> CrossSectionalPressure:
    if not (0.0 <= rank_5 <= 1.0 and 0.0 <= rank_20 <= 1.0):
        return CrossSectionalPressure.INDETERMINATE
    strongest = max(rank_5, rank_20)
    if strongest >= thresholds.xs_high_floor:
        return CrossSectionalPressure.HIGH
    if strongest >= thresholds.xs_elevated_floor:
        return CrossSectionalPressure.ELEVATED
    return CrossSectionalPressure.LOW


def _divergence(div_5: float, div_20: float, thresholds: SetupThresholds) -> DivergenceState:
    threshold = thresholds.divergence_threshold
    if max(div_5, div_20) >= threshold:
        return DivergenceState.POSITIVE
    if min(div_5, div_20) <= -threshold:
        return DivergenceState.NEGATIVE
    return DivergenceState.NEUTRAL


def _setup_label(
    *,
    participation: ParticipationIntensity,
    abnormality: HistoricalAbnormality,
    persistence: PersistenceState,
    xs_pressure: CrossSectionalPressure,
    divergence: DivergenceState,
) -> SetupLabel:
    accumulation_abnormality = {
        HistoricalAbnormality.ACCUMULATION,
        HistoricalAbnormality.EXTREME_ACCUMULATION,
    }
    distribution_abnormality = {
        HistoricalAbnormality.DISTRIBUTION,
        HistoricalAbnormality.EXTREME_DISTRIBUTION,
    }

    if abnormality in accumulation_abnormality:
        if (
            persistence is PersistenceState.ACCUMULATION
            and xs_pressure is CrossSectionalPressure.HIGH
            and divergence is DivergenceState.POSITIVE
        ):
            return SetupLabel.STEALTH_ACCUMULATION_CANDIDATE
        if persistence is PersistenceState.ACCUMULATION:
            return SetupLabel.PERSISTENT_ACCUMULATION
        return SetupLabel.ABNORMAL_ACCUMULATION

    if abnormality in distribution_abnormality or persistence is PersistenceState.DISTRIBUTION:
        return SetupLabel.DISTRIBUTION_PRESSURE

    if participation is ParticipationIntensity.HIGH and abnormality is HistoricalAbnormality.NORMAL:
        return SetupLabel.HIGH_PARTICIPATION_ROUTINE_FLOW

    return SetupLabel.NEUTRAL_OR_MIXED


def classify_foreign_flow_setup(
    row: Mapping[str, object],
    *,
    thresholds: SetupThresholds = DEFAULT_THRESHOLDS,
) -> ForeignFlowSetupState:
    """Classify one accepted V2 representation row into descriptive states.

    Missing required inputs fail closed to INDETERMINATE. Inputs carrying
    outcome/label keys are rejected even though this classifier would not use
    those columns. The function performs no fitting, forward fill, or
    retrospective optimization.
    """

    _assert_outcome_blind(row)
    values = {field: _finite_value(row, field) for field in REQUIRED_FIELDS}
    missing = tuple(field for field, value in values.items() if value is None)
    if missing:
        return ForeignFlowSetupState(
            participation_intensity=ParticipationIntensity.INDETERMINATE,
            participation_direction=FlowDirection.INDETERMINATE,
            historical_abnormality=HistoricalAbnormality.INDETERMINATE,
            persistence=PersistenceState.INDETERMINATE,
            cross_sectional_pressure=CrossSectionalPressure.INDETERMINATE,
            divergence=DivergenceState.INDETERMINATE,
            acceleration_direction=FlowDirection.INDETERMINATE,
            setup_label=SetupLabel.INDETERMINATE,
            missing_fields=missing,
        )

    participation = float(values["foreign_participation_1"])
    percentile = float(values["foreign_flow_shock_percentile_120"])
    rank_5 = float(values["xs_rank_foreign_flow_shock_mean_5"])
    rank_20 = float(values["xs_rank_foreign_flow_shock_mean_20"])
    persistence_5 = float(values["foreign_weighted_persistence_5"])
    persistence_20 = float(values["foreign_weighted_persistence_20"])
    acceleration = float(values["foreign_flow_acceleration_5_20"])
    divergence_5 = float(values["foreign_flow_price_divergence_5"])
    divergence_20 = float(values["foreign_flow_price_divergence_20"])

    historical_abnormality = _historical_abnormality(percentile, thresholds)
    cross_sectional_pressure = _xs_pressure(rank_5, rank_20, thresholds)
    if (
        historical_abnormality is HistoricalAbnormality.INDETERMINATE
        or cross_sectional_pressure is CrossSectionalPressure.INDETERMINATE
    ):
        return ForeignFlowSetupState(
            participation_intensity=_participation_intensity(participation, thresholds),
            participation_direction=_direction(participation),
            historical_abnormality=historical_abnormality,
            persistence=PersistenceState.INDETERMINATE,
            cross_sectional_pressure=cross_sectional_pressure,
            divergence=DivergenceState.INDETERMINATE,
            acceleration_direction=_direction(acceleration),
            setup_label=SetupLabel.INDETERMINATE,
            missing_fields=(),
        )

    persistence = _persistence(persistence_5, persistence_20, thresholds)
    divergence = _divergence(divergence_5, divergence_20, thresholds)
    participation_intensity = _participation_intensity(participation, thresholds)

    return ForeignFlowSetupState(
        participation_intensity=participation_intensity,
        participation_direction=_direction(participation),
        historical_abnormality=historical_abnormality,
        persistence=persistence,
        cross_sectional_pressure=cross_sectional_pressure,
        divergence=divergence,
        acceleration_direction=_direction(acceleration),
        setup_label=_setup_label(
            participation=participation_intensity,
            abnormality=historical_abnormality,
            persistence=persistence,
            xs_pressure=cross_sectional_pressure,
            divergence=divergence,
        ),
        missing_fields=(),
    )
