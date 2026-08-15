"""Prospective sidecar materialization for Foreign Flow Setup State V1.

The sidecar consumes only accepted Foreign Flow V2 representation rows and
emits deterministic descriptive states plus the raw causal evidence needed to
interpret them. It does not consume labels, outcomes, or model scores.
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
EVIDENCE_COLUMNS = (
    "foreign_participation_1",
    "foreign_flow_shock_1",
    "foreign_flow_shock_mean_5",
    "foreign_flow_shock_mean_20",
    "foreign_flow_shock_percentile_120",
    "xs_rank_foreign_flow_shock_1",
    "xs_rank_foreign_flow_shock_mean_5",
    "xs_rank_foreign_flow_shock_mean_20",
    "foreign_weighted_persistence_5",
    "foreign_weighted_persistence_20",
    "foreign_flow_acceleration_5_20",
    "foreign_flow_price_divergence_5",
    "foreign_flow_price_divergence_20",
)
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

    The sidecar intentionally retains both current participation and historical
    abnormality evidence. This allows, for example, a 5% participation row to
    remain visibly more abnormal than a 50% row when the former is much larger
    relative to its ticker's own prior baseline.

    Outcome or label columns are rejected by the row classifier. Duplicate
    ``(ticker, feature_session)`` keys fail closed when those keys are present.
    """

    required = set(KEY_COLUMNS) | set(REQUIRED_FIELDS) | set(EVIDENCE_COLUMNS)
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"setup-state frame missing columns: {missing}")

    present_keys = list(KEY_COLUMNS)
    if frame.loc[:, list(KEY_COLUMNS)].isna().any().any():
        raise ValueError("setup-state frame has null identity keys")
    if frame["ticker"].astype(str).str.strip().eq("").any():
        raise ValueError("setup-state frame has empty ticker identity")
    if frame.duplicated(list(KEY_COLUMNS)).any() or frame.duplicated(
        ["ticker", "feature_session"]
    ).any():
        raise ValueError("setup-state frame has duplicate ticker/feature_session rows")

    records: list[dict[str, object]] = []
    for row in frame.to_dict(orient="records"):
        state = classify_foreign_flow_setup(row, thresholds=thresholds)
        record = {column: row[column] for column in present_keys}
        record.update({column: row[column] for column in EVIDENCE_COLUMNS})
        raw_evidence_missing = tuple(
            column
            for column in EVIDENCE_COLUMNS
            if row[column] is None or pd.isna(row[column])
        )
        missing_fields = tuple(sorted(set(state.missing_fields) | set(raw_evidence_missing)))
        indeterminate = raw_evidence_missing or bool(state.missing_fields)
        record.update(
            {
                "participation_intensity": (
                    "INDETERMINATE" if indeterminate else state.participation_intensity.value
                ),
                "participation_direction": (
                    "INDETERMINATE" if indeterminate else state.participation_direction.value
                ),
                "historical_abnormality": (
                    "INDETERMINATE" if indeterminate else state.historical_abnormality.value
                ),
                "persistence_state": (
                    "INDETERMINATE" if indeterminate else state.persistence.value
                ),
                "cross_sectional_pressure": (
                    "INDETERMINATE" if indeterminate else state.cross_sectional_pressure.value
                ),
                "divergence_state": (
                    "INDETERMINATE" if indeterminate else state.divergence.value
                ),
                "acceleration_direction": (
                    "INDETERMINATE" if indeterminate else state.acceleration_direction.value
                ),
                "setup_label": (
                    "INDETERMINATE"
                    if raw_evidence_missing
                    else state.setup_label.value
                ),
                "missing_fields": "|".join(missing_fields),
                "state_contract_version": STATE_CONTRACT_VERSION,
                "source_representation_version": SOURCE_REPRESENTATION_VERSION,
            }
        )
        records.append(record)

    return pd.DataFrame(
        records,
        columns=[*present_keys, *EVIDENCE_COLUMNS, *STATE_COLUMNS],
    )
