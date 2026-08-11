from __future__ import annotations

from enum import StrEnum

import pandas as pd

from .security_master import normalise_ticker


class OwnershipDimension(StrEnum):
    RESIDENCY = "RESIDENCY"
    INVESTOR_TYPE = "INVESTOR_TYPE"
    HOLDER_BAND = "HOLDER_BAND"
    NAMED_HOLDER = "NAMED_HOLDER"
    FREE_FLOAT = "FREE_FLOAT"


class OwnershipMetric(StrEnum):
    SHARES = "SHARES"
    PERCENT = "PERCENT"
    HOLDER_COUNT = "HOLDER_COUNT"


SNAPSHOT_COLUMNS = (
    "snapshot_id",
    "ticker",
    "as_of_date",
    "published_at",
    "knowledge_at",
    "source",
    "source_ref",
    "source_url",
    "source_sha256",
)

FACT_COLUMNS = (
    "snapshot_id",
    "dimension_type",
    "dimension_value",
    "metric",
    "value",
    "unit",
)

_METRIC_UNIT = {
    OwnershipMetric.SHARES.value: "SHARES",
    OwnershipMetric.PERCENT.value: "PERCENT",
    OwnershipMetric.HOLDER_COUNT.value: "COUNT",
}


def _clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _utc_series(series: pd.Series, *, field: str) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce", utc=False)
    if values.isna().any():
        raise ValueError(f"Ownership snapshot has invalid {field}")
    if not all(getattr(value, "tzinfo", None) is not None for value in values):
        raise ValueError(f"Ownership snapshot {field} must be timezone-aware")
    return values.map(lambda value: pd.Timestamp(value).tz_convert("UTC"))


def canonicalize_ownership_snapshots(frame: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize immutable, publication-aware ownership snapshots.

    ``as_of_date`` describes the ownership state represented by the source.
    ``published_at``/``knowledge_at`` describe when that state became usable by
    the research system. A later source revision must be a new snapshot rather
    than silently overwriting the earlier version.
    """

    if frame.empty:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)

    data = frame.copy()
    required = {
        "ticker",
        "as_of_date",
        "published_at",
        "source",
        "source_ref",
        "source_url",
        "source_sha256",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Ownership snapshot columns missing: {sorted(missing)}")

    data["ticker"] = data["ticker"].map(normalise_ticker)
    invalid_ticker = ~data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
    if invalid_ticker.any():
        raise ValueError("Ownership snapshot has unsupported ticker")

    data["as_of_date"] = pd.to_datetime(data["as_of_date"], errors="coerce").dt.normalize()
    if data["as_of_date"].isna().any():
        raise ValueError("Ownership snapshot has invalid as_of_date")

    data["published_at"] = _utc_series(data["published_at"], field="published_at")
    if "knowledge_at" not in data.columns:
        data["knowledge_at"] = data["published_at"]
    else:
        missing_knowledge = data["knowledge_at"].isna()
        data.loc[missing_knowledge, "knowledge_at"] = data.loc[missing_knowledge, "published_at"]
        data["knowledge_at"] = _utc_series(data["knowledge_at"], field="knowledge_at")

    if data["knowledge_at"].lt(data["published_at"]).any():
        raise ValueError("Ownership snapshot knowledge_at precedes published_at")

    for column in ("source", "source_ref", "source_url", "source_sha256"):
        data[column] = _clean_text(data[column])
        if data[column].eq("").any():
            raise ValueError(f"Ownership snapshot missing provenance field: {column}")

    if (~data["source_url"].str.startswith("https://")).any():
        raise ValueError("Ownership source_url must use HTTPS")
    if (~data["source_sha256"].str.fullmatch(r"[0-9a-fA-F]{64}")).any():
        raise ValueError("Ownership source_sha256 must be a SHA-256 hex digest")
    data["source_sha256"] = data["source_sha256"].str.lower()

    same_knowledge = data.duplicated(["ticker", "as_of_date", "knowledge_at"], keep=False)
    if same_knowledge.any():
        groups = data.loc[same_knowledge].groupby(["ticker", "as_of_date", "knowledge_at"])
        if any(group["source_sha256"].nunique() > 1 for _, group in groups):
            raise ValueError("Conflicting ownership revisions share the same knowledge time")
        data = data.drop_duplicates(
            ["ticker", "as_of_date", "knowledge_at", "source_sha256"], keep="first"
        )

    data["snapshot_id"] = (
        "IDX:OWN:"
        + data["ticker"]
        + ":"
        + data["as_of_date"].dt.strftime("%Y%m%d")
        + ":"
        + data["source_sha256"].str[:16]
    )

    if data["snapshot_id"].duplicated().any():
        raise ValueError("Duplicate ownership snapshot requires explicit reconciliation")

    return (
        data[list(SNAPSHOT_COLUMNS)]
        .sort_values(["ticker", "as_of_date", "knowledge_at"])
        .reset_index(drop=True)
    )


def canonicalize_ownership_facts(
    frame: pd.DataFrame,
    snapshots: pd.DataFrame,
) -> pd.DataFrame:
    """Validate long-form ownership facts bound to immutable snapshots."""

    if frame.empty:
        return pd.DataFrame(columns=FACT_COLUMNS)

    required = {"snapshot_id", "dimension_type", "dimension_value", "metric", "value", "unit"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Ownership fact columns missing: {sorted(missing)}")

    valid_snapshot_ids = set(snapshots["snapshot_id"].astype(str))
    data = frame.copy()
    data["snapshot_id"] = _clean_text(data["snapshot_id"])
    if (~data["snapshot_id"].isin(valid_snapshot_ids)).any():
        raise ValueError("Ownership fact references unknown snapshot_id")

    data["dimension_type"] = data["dimension_type"].map(
        lambda value: OwnershipDimension(str(value).upper().strip()).value
    )
    data["dimension_value"] = _clean_text(data["dimension_value"])
    if data["dimension_value"].eq("").any():
        raise ValueError("Ownership fact missing dimension_value")

    data["metric"] = data["metric"].map(
        lambda value: OwnershipMetric(str(value).upper().strip()).value
    )
    data["unit"] = _clean_text(data["unit"]).str.upper()
    expected_unit = data["metric"].map(_METRIC_UNIT)
    if (~data["unit"].eq(expected_unit)).any():
        raise ValueError("Ownership fact metric/unit mismatch")

    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    if data["value"].isna().any() or data["value"].lt(0).any():
        raise ValueError("Ownership fact has invalid numeric value")
    percent = data["metric"].eq(OwnershipMetric.PERCENT.value)
    if (percent & data["value"].gt(100)).any():
        raise ValueError("Ownership percent exceeds 100")

    duplicate = data.duplicated(
        ["snapshot_id", "dimension_type", "dimension_value", "metric"], keep=False
    )
    if duplicate.any():
        raise ValueError("Duplicate ownership fact requires explicit reconciliation")

    return data[list(FACT_COLUMNS)].sort_values(
        ["snapshot_id", "dimension_type", "dimension_value", "metric"]
    ).reset_index(drop=True)


def ownership_snapshots_asof(snapshots: pd.DataFrame, asof: object) -> pd.DataFrame:
    """Select the latest knowable revision of each ticker/as-of-date snapshot."""

    if snapshots.empty:
        return snapshots.copy()

    timestamp = pd.Timestamp(asof)
    if timestamp.tzinfo is None:
        raise ValueError("ownership as-of timestamp must be timezone-aware")
    timestamp = timestamp.tz_convert("UTC")

    visible = snapshots[snapshots["knowledge_at"].le(timestamp)].copy()
    if visible.empty:
        return visible

    visible = visible.sort_values(["ticker", "as_of_date", "knowledge_at"])
    return visible.groupby(["ticker", "as_of_date"], as_index=False).tail(1).reset_index(drop=True)


def ownership_facts_asof(
    snapshots: pd.DataFrame,
    facts: pd.DataFrame,
    asof: object,
) -> pd.DataFrame:
    """Expose only facts belonging to ownership snapshot versions visible as-of t."""

    selected = ownership_snapshots_asof(snapshots, asof)
    if selected.empty or facts.empty:
        return facts.iloc[0:0].copy()
    return facts[facts["snapshot_id"].isin(set(selected["snapshot_id"]))].reset_index(drop=True)
