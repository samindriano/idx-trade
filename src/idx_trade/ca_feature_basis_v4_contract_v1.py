from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .ca_feature_basis_gate_v1 import evaluate_feature_basis_admission
from .ca_feature_basis_v1 import (
    FeatureDependency,
    REVERSE_SPLIT,
    STOCK_SPLIT,
    V4_PRICE_FEATURE_DEPENDENCIES,
)


# Frozen V4 relative_volume_20 is volume / rolling_median(volume, 20), so its
# observed-row dependency is t-19..t.  Raw share volume is preserved by the
# historical ingestion path.  A stock split/reverse split changes the share
# unit itself, therefore this feature must not bridge those transitions.
#
# Do not generalize this to rights/bonus/conversion merely because outstanding
# shares can change.  V1 requires event-family-specific evidence before a
# non-price field is classified as basis-incompatible.
V4_SPLIT_VOLUME_DEPENDENCIES: tuple[FeatureDependency, ...] = (
    FeatureDependency("relative_volume_20", tuple(range(-19, 1))),
)

V4_CA_BASIS_DIRECT_SOURCE_FEATURES: tuple[str, ...] = (
    *(dependency.feature for dependency in V4_PRICE_FEATURE_DEPENDENCIES),
    "relative_volume_20",
)

_SPLIT_VOLUME_FAMILIES = {STOCK_SPLIT, REVERSE_SPLIT}


def _split_volume_events(events: pd.DataFrame) -> pd.DataFrame:
    """Retain only source-certified event families that redefine share units."""

    if "event_family" not in events.columns:
        raise ValueError("basis event ledger missing event_family")
    family = events["event_family"].astype(str).str.upper().str.strip()
    return events.loc[family.isin(_SPLIT_VOLUME_FAMILIES)].copy()


def evaluate_v4_feature_basis_admission(
    identities: pd.DataFrame,
    events: pd.DataFrame,
    coverage: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Apply the frozen V4 field-specific CA dependency contract outcome-blind.

    H/L/C-derived dependencies use the generic price-basis contract and see all
    admitted structural event families.  Raw-volume rolling semantics are added
    separately and see only split/reverse-split transitions, because those
    events mechanically redefine the share unit.

    Coverage remains the global fail-closed CA coverage ledger.  This function
    does not infer event dates, adjust values, recompute cross-sectional
    transforms, access outcomes, or authorize model fitting.
    """

    price = evaluate_feature_basis_admission(
        identities,
        events,
        coverage,
        official_sessions,
        dependencies=V4_PRICE_FEATURE_DEPENDENCIES,
    )
    volume = evaluate_feature_basis_admission(
        identities,
        _split_volume_events(events),
        coverage,
        official_sessions,
        dependencies=V4_SPLIT_VOLUME_DEPENDENCIES,
    )

    combined = pd.concat([price, volume], ignore_index=True, sort=False)
    if combined.duplicated(["ticker", "date", "feature"]).any():
        raise ValueError("V4 CA feature-basis admission contains duplicate identity")
    return combined.sort_values(
        ["date", "ticker", "feature"], kind="mergesort"
    ).reset_index(drop=True)
