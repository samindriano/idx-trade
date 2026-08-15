"""Prospective sidecar materialization for Foreign Flow Setup State V1.

The sidecar consumes only accepted Foreign Flow V2 representation rows and
emits deterministic descriptive states. It does not consume labels, outcomes,
or model scores.
"""
from __future__ import annotations

import pandas as pd

from .foreign_flow_setup_state import (
    DEFAULT_THRESHOLDS,
    REQUIRED_FIELDS,
    SetupThresholds,
    classify_foreign_flow_setup,
)

STATE_CONTRACT_VERSION = "FOREIGN_FLOW_SETUP_STATE_V1"
SOURCE_REPRESENTATION_VERSION = "FOREIGN_FLOW_REPRESENTATION_V2"

KEY_COLUMNS = ("ticker", "feature_session", "flow_through_session")
STATE_COLUMNS = (
    "participation_intensity",
    "participation_direction",
    "historical_abnormality",
    "persistence_state",
    "cross_sectional_pressure",
    "divergence_state",
    "acceleration_direction",
    "setup_label",
    "missing_fields",
    "state_contract_version",
    "source_representation_version",
)


def build_foreign_flow_setup_sidecar(
    frame: pd.DataFrame,
    *,
    thresholds: SetupThresholds = DEFAULT_THRESHOLDS,
) -> pd.DataFrame:
    """Build a deterministic setup-state sidecar from accepted V2 rows.

    The input must contain the V2 fields required by the classifier. Outcome or
    label columns are rejected by the row classifier. Duplicate
    ``(ticker, feature_session)`` keys fail closed when those keys are present.
    """

    missing = sorted(set(REQUIRED_FIELDS) - set(frame.columns))
    if missing:
        raise ValueError(f"setup-state frame missing columns: {missing}")

    present_keys = [column for column in KEY_COLUMNS if column in frame.columns]
    if {"ticker", "feature_session"}.issubset(frame.columns) and frame.duplicated(
        ["ticker", "feature_session"]
    ).any():
        raise ValueError("setup-state frame has duplicate ticker/feature_session rows")

    records: list[dict[str, object]] = []
    for row in frame.to_dict(orient="records"):
        state = classify_foreign_flow_setup(row, thresholds=thresholds)
        record = {column: row[column] for column in present_keys}
        record.update(
            {
                "participation_intensity": state.participation_intensity.value,
                "participation_direction": state.participation_direction.value,
                "historical_abnormality": state.historical_abnormality.value,
                "persistence_state": state.persistence.value,
                "cross_sectional_pressure": state.cross_sectional_pressure.value,
                "divergence_state": state.divergence.value,
                "acceleration_direction": state.acceleration_direction.value,
                "setup_label": state.setup_label.value,
                "missing_fields": "|".join(state.missing_fields),
                "state_contract_version": STATE_CONTRACT_VERSION,
                "source_representation_version": SOURCE_REPRESENTATION_VERSION,
            }
        )
        records.append(record)

    return pd.DataFrame(records, columns=[*present_keys, *STATE_COLUMNS])
