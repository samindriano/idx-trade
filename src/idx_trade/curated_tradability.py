from __future__ import annotations

from pathlib import Path

import pandas as pd

from .security_master import canonicalize_tradability_intervals


CURATED_SOURCE = "IDX_EXCHANGE_ANNOUNCEMENT"
_REQUIRED_COLUMNS = {
    "ticker",
    "market",
    "state",
    "effective_from",
    "source",
    "source_ref",
}


def load_curated_tradability_intervals(path: str | Path) -> pd.DataFrame:
    """Load narrowly curated official legal-state evidence.

    This registry is for cases where an authoritative IDX announcement is known
    but the automatic announcement-discovery/parser path has not reconstructed
    the interval yet. It is not a manual escape hatch: every row must retain an
    official IDX announcement reference and is canonicalized through the same
    tradability interval contract as automatically parsed evidence.
    """

    frame = pd.read_csv(path)
    missing = _REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Curated tradability columns missing: {sorted(missing)}")

    data = frame.copy()
    data["source"] = data["source"].fillna("").astype(str).str.strip()
    data["source_ref"] = data["source_ref"].fillna("").astype(str).str.strip()
    if not data["source"].eq(CURATED_SOURCE).all():
        raise ValueError("Curated tradability evidence must come from IDX exchange announcements")
    if data["source_ref"].eq("").any():
        raise ValueError("Curated tradability evidence requires an explicit source_ref")

    if "evidence_id" in data.columns:
        evidence_id = data["evidence_id"].fillna("").astype(str).str.strip()
        if evidence_id.eq("").any() or evidence_id.duplicated().any():
            raise ValueError("Curated tradability evidence_id values must be non-empty and unique")

    return canonicalize_tradability_intervals(data)


def merge_curated_tradability_intervals(
    reconstructed: pd.DataFrame,
    curated: pd.DataFrame,
) -> pd.DataFrame:
    """Merge curated official evidence without bypassing conflict validation."""

    if reconstructed.empty:
        combined = curated.copy()
    elif curated.empty:
        combined = reconstructed.copy()
    else:
        combined = pd.concat([reconstructed, curated], ignore_index=True)
    return canonicalize_tradability_intervals(combined)
