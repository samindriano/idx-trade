from __future__ import annotations

from enum import StrEnum

import pandas as pd

from .security_master import normalise_ticker


class FinancialPeriodKind(StrEnum):
    Q1 = "Q1"
    H1 = "H1"
    NINE_MONTH = "9M"
    FY = "FY"
    OTHER = "OTHER"


class StatementScope(StrEnum):
    CONSOLIDATED = "CONSOLIDATED"
    SEPARATE = "SEPARATE"


FILING_COLUMNS = (
    "filing_id",
    "ticker",
    "fiscal_period_end",
    "period_kind",
    "statement_scope",
    "currency",
    "published_at",
    "knowledge_at",
    "source",
    "source_ref",
    "source_url",
    "source_sha256",
)

FACT_COLUMNS = (
    "filing_id",
    "concept",
    "value",
    "unit",
    "period_start",
    "period_end",
    "instant_date",
)


def _clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _as_utc_naive(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_convert(None)


def canonicalize_financial_filings(frame: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize immutable filing versions for point-in-time use.

    A fiscal period may have multiple filing versions. Revisions are preserved
    as separate rows and become visible only when ``knowledge_at`` is reached.
    This function never backdates a filing to its fiscal period end.
    """

    if frame.empty:
        return pd.DataFrame(columns=FILING_COLUMNS)

    data = frame.copy()
    required = {
        "ticker",
        "fiscal_period_end",
        "period_kind",
        "statement_scope",
        "currency",
        "published_at",
        "source",
        "source_ref",
        "source_url",
        "source_sha256",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Financial filing columns missing: {sorted(missing)}")

    data["ticker"] = data["ticker"].map(normalise_ticker)
    invalid_ticker = ~data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
    if invalid_ticker.any():
        raise ValueError(
            f"Unsupported financial filing ticker(s): {data.loc[invalid_ticker, 'ticker'].tolist()[:10]}"
        )

    data["fiscal_period_end"] = pd.to_datetime(
        data["fiscal_period_end"], errors="coerce"
    ).dt.normalize()
    data["published_at"] = _as_utc_naive(data["published_at"])
    if "knowledge_at" not in data.columns:
        data["knowledge_at"] = pd.NaT
    data["knowledge_at"] = _as_utc_naive(data["knowledge_at"])
    data.loc[data["knowledge_at"].isna(), "knowledge_at"] = data.loc[
        data["knowledge_at"].isna(), "published_at"
    ]

    if data[["fiscal_period_end", "published_at", "knowledge_at"]].isna().any().any():
        raise ValueError("Financial filing has missing/invalid PIT dates")
    if (data["knowledge_at"] < data["published_at"]).any():
        raise ValueError("Financial filing knowledge_at precedes published_at")
    if (data["published_at"].dt.normalize() < data["fiscal_period_end"]).any():
        raise ValueError("Financial filing published before fiscal period end")

    data["period_kind"] = _clean_text(data["period_kind"]).str.upper()
    allowed_periods = {item.value for item in FinancialPeriodKind}
    if (~data["period_kind"].isin(allowed_periods)).any():
        raise ValueError("Unsupported financial period kind")

    data["statement_scope"] = _clean_text(data["statement_scope"]).str.upper()
    allowed_scopes = {item.value for item in StatementScope}
    if (~data["statement_scope"].isin(allowed_scopes)).any():
        raise ValueError("Financial statement scope must be explicit")

    for column in ("currency", "source", "source_ref", "source_url", "source_sha256"):
        data[column] = _clean_text(data[column])
        if data[column].eq("").any():
            raise ValueError(f"Financial filing missing provenance/identity field: {column}")

    data["currency"] = data["currency"].str.upper()
    if (~data["source_url"].str.startswith("https://")).any():
        raise ValueError("Financial filing source_url must use HTTPS")
    if (~data["source_sha256"].str.fullmatch(r"[0-9a-fA-F]{64}")).any():
        raise ValueError("Financial filing source_sha256 must be a SHA-256 hex digest")
    data["source_sha256"] = data["source_sha256"].str.lower()

    version_key = [
        "ticker",
        "fiscal_period_end",
        "period_kind",
        "statement_scope",
        "knowledge_at",
    ]
    duplicate_time = data.duplicated(version_key, keep=False)
    if duplicate_time.any():
        groups = data.loc[duplicate_time].groupby(version_key, dropna=False)["source_sha256"].nunique()
        if (groups > 1).any():
            raise ValueError("Conflicting financial filing versions share the same knowledge time")
        data = data.drop_duplicates(version_key, keep="last")

    data["filing_id"] = (
        "IDX:"
        + data["ticker"]
        + ":"
        + data["fiscal_period_end"].dt.strftime("%Y%m%d")
        + ":"
        + data["period_kind"]
        + ":"
        + data["statement_scope"]
        + ":"
        + data["knowledge_at"].dt.strftime("%Y%m%dT%H%M%S")
        + ":"
        + data["source_sha256"].str[:12]
    )

    return (
        data[list(FILING_COLUMNS)]
        .sort_values(["ticker", "fiscal_period_end", "statement_scope", "knowledge_at"])
        .reset_index(drop=True)
    )


def canonicalize_financial_facts(frame: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize filing-bound numeric facts without deriving quarter semantics."""

    if frame.empty:
        return pd.DataFrame(columns=FACT_COLUMNS)

    data = frame.copy()
    required = {"filing_id", "concept", "value", "unit"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Financial fact columns missing: {sorted(missing)}")

    for column in ("filing_id", "concept", "unit"):
        data[column] = _clean_text(data[column])
        if data[column].eq("").any():
            raise ValueError(f"Financial fact missing identity field: {column}")

    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    if data["value"].isna().any():
        raise ValueError("Financial fact value must be numeric")

    for column in ("period_start", "period_end", "instant_date"):
        if column not in data.columns:
            data[column] = pd.NaT
        data[column] = pd.to_datetime(data[column], errors="coerce").dt.normalize()

    duration = data["period_start"].notna() | data["period_end"].notna()
    invalid_duration = duration & (data["period_start"].isna() | data["period_end"].isna())
    if invalid_duration.any():
        raise ValueError("Duration financial fact requires both period_start and period_end")
    if (duration & data["instant_date"].notna()).any():
        raise ValueError("Financial fact cannot be both duration and instant")
    if (~duration & data["instant_date"].isna()).any():
        raise ValueError("Financial fact requires duration dates or instant_date")
    if (duration & (data["period_end"] < data["period_start"])).any():
        raise ValueError("Financial fact duration ends before it starts")

    duplicate = data.duplicated(
        ["filing_id", "concept", "unit", "period_start", "period_end", "instant_date"],
        keep=False,
    )
    if duplicate.any():
        conflicts = (
            data.loc[duplicate]
            .groupby(
                ["filing_id", "concept", "unit", "period_start", "period_end", "instant_date"],
                dropna=False,
            )["value"]
            .nunique()
        )
        if (conflicts > 1).any():
            raise ValueError("Conflicting duplicate financial facts within one filing")
        data = data.drop_duplicates(
            ["filing_id", "concept", "unit", "period_start", "period_end", "instant_date"],
            keep="last",
        )

    return data[list(FACT_COLUMNS)].sort_values(["filing_id", "concept"]).reset_index(drop=True)


def financial_filings_asof(filings: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Return the latest knowable filing version for each ticker/period/scope."""

    canonical = canonicalize_financial_filings(filings)
    if canonical.empty:
        return canonical

    timestamp = pd.Timestamp(as_of)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("UTC").tz_localize(None)
    visible = canonical[canonical["knowledge_at"].le(timestamp)].copy()
    if visible.empty:
        return visible

    key = ["ticker", "fiscal_period_end", "period_kind", "statement_scope"]
    latest_idx = visible.groupby(key, sort=False)["knowledge_at"].idxmax()
    return (
        visible.loc[latest_idx]
        .sort_values(["ticker", "fiscal_period_end", "statement_scope"])
        .reset_index(drop=True)
    )


def financial_facts_asof(
    filings: pd.DataFrame,
    facts: pd.DataFrame,
    as_of: pd.Timestamp,
) -> pd.DataFrame:
    """Return facts only from filing versions knowable at ``as_of``."""

    canonical_filings = canonicalize_financial_filings(filings)
    canonical_facts = canonicalize_financial_facts(facts)
    if canonical_facts.empty:
        return canonical_facts

    orphan = ~canonical_facts["filing_id"].isin(canonical_filings["filing_id"])
    if orphan.any():
        raise ValueError("Financial facts reference unknown filing_id")

    selected = financial_filings_asof(canonical_filings, as_of)
    if selected.empty:
        return canonical_facts.iloc[0:0].copy()

    return (
        canonical_facts[canonical_facts["filing_id"].isin(selected["filing_id"])]
        .merge(
            selected[[
                "filing_id",
                "ticker",
                "fiscal_period_end",
                "period_kind",
                "statement_scope",
                "published_at",
                "knowledge_at",
            ]],
            on="filing_id",
            how="left",
            validate="many_to_one",
        )
        .sort_values(["ticker", "fiscal_period_end", "concept"])
        .reset_index(drop=True)
    )
