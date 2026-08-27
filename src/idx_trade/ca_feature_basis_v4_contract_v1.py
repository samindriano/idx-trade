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


def _normalize_identity(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    required = {"ticker", "date"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {sorted(missing)}")
    out = frame[["ticker", "date"]].copy()
    out["ticker"] = (
        out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if out["ticker"].eq("").any() or out["date"].isna().any():
        raise ValueError(f"{label} contains invalid ticker/date")
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError(f"{label} contains duplicate ticker/date")
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


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
    """Low-level V4 field-specific CA dependency evaluation.

    ``identities`` must be the same full PIT listing-admitted observation stream
    on which the frozen pandas shift/rolling formulas operate.  Historical
    application code should normally call
    ``evaluate_v4_application_feature_basis_admission`` instead, so sparse
    candidate/final-fit identities cannot redefine observed-row offsets.

    H/L/C-derived dependencies see all admitted structural event families.
    Raw-volume rolling semantics see only split/reverse-split transitions,
    because those events mechanically redefine the share unit.
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


def evaluate_v4_application_feature_basis_admission(
    full_observation_identities: pd.DataFrame,
    application_scope_identities: pd.DataFrame,
    events: pd.DataFrame,
    coverage: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Safe historical-application entry point preserving frozen row geometry.

    Dependency positions are first computed on the complete PIT listing-admitted
    ticker observation stream.  Only after that computation is the result
    restricted to candidate/final-fit/application identities.  This prevents a
    sparse application set from silently changing pandas ``shift``/``rolling``
    semantics.
    """

    full = _normalize_identity(full_observation_identities, label="full observation stream")
    scope = _normalize_identity(application_scope_identities, label="application scope")
    full_keys = set(map(tuple, full[["ticker", "date"]].to_numpy()))
    scope_keys = set(map(tuple, scope[["ticker", "date"]].to_numpy()))
    missing = scope_keys - full_keys
    if missing:
        raise ValueError(
            f"application scope contains identities outside full observation stream: {len(missing)}"
        )

    admission = evaluate_v4_feature_basis_admission(
        full,
        events,
        coverage,
        official_sessions,
    )
    scoped = admission.merge(
        scope.assign(_application_scope=True),
        on=["ticker", "date"],
        how="inner",
        validate="many_to_one",
    ).drop(columns=["_application_scope"])

    expected = len(V4_CA_BASIS_DIRECT_SOURCE_FEATURES)
    counts = scoped.groupby(["ticker", "date"], sort=False)["feature"].nunique()
    if len(counts) != len(scope) or (counts != expected).any():
        raise ValueError("application feature-basis admission is incomplete")
    return scoped.sort_values(["date", "ticker", "feature"], kind="mergesort").reset_index(drop=True)
