from __future__ import annotations

from enum import StrEnum

import numpy as np
import pandas as pd

from .security_master import normalise_ticker


class ForeignFlowUnit(StrEnum):
    SHARES = "SHARES"
    LOTS = "LOTS"
    IDR = "IDR"


FOREIGN_FLOW_COLUMNS = (
    "observation_id",
    "ticker",
    "session_date",
    "unit",
    "published_at",
    "knowledge_at",
    "foreign_buy",
    "foreign_sell",
    "foreign_net",
    "source",
    "source_ref",
    "source_url",
    "source_sha256",
)


def _clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def canonicalize_foreign_flow(frame: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize revision-aware per-security foreign flow observations.

    The contract deliberately keeps the source unit explicit. A row measured in
    shares must never be silently mixed with lots or rupiah value. Multiple
    versions of the same ticker/session/unit are allowed only at distinct
    knowledge times so historical source revisions can be preserved instead of
    overwriting what was previously knowable.
    """

    if frame.empty:
        return pd.DataFrame(columns=FOREIGN_FLOW_COLUMNS)

    data = frame.copy()
    required = {
        "ticker",
        "session_date",
        "unit",
        "knowledge_at",
        "foreign_buy",
        "foreign_sell",
        "foreign_net",
        "source",
        "source_ref",
        "source_url",
        "source_sha256",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Foreign-flow columns missing: {sorted(missing)}")

    data["ticker"] = data["ticker"].map(normalise_ticker)
    invalid_ticker = ~data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
    if invalid_ticker.any():
        bad = data.loc[invalid_ticker, "ticker"].tolist()[:10]
        raise ValueError(f"Unsupported foreign-flow ticker(s): {bad}")

    data["session_date"] = pd.to_datetime(data["session_date"], errors="coerce").dt.normalize()
    if data["session_date"].isna().any():
        raise ValueError("Foreign-flow observation missing session_date")

    data["unit"] = data["unit"].astype(str).str.upper().str.strip()
    try:
        data["unit"] = data["unit"].map(lambda value: ForeignFlowUnit(value).value)
    except ValueError as exc:
        raise ValueError("Unsupported foreign-flow unit") from exc

    if "published_at" not in data.columns:
        data["published_at"] = pd.NaT
    for column in ("published_at", "knowledge_at"):
        data[column] = pd.to_datetime(data[column], errors="coerce", utc=True)

    if data["knowledge_at"].isna().any():
        raise ValueError("Foreign-flow observation missing knowledge_at")

    invalid_publication = (
        data["published_at"].notna()
        & data["knowledge_at"].lt(data["published_at"])
    )
    if invalid_publication.any():
        raise ValueError("knowledge_at precedes published_at")

    session_utc_date = data["knowledge_at"].dt.tz_convert("Asia/Jakarta").dt.normalize().dt.tz_localize(None)
    if session_utc_date.lt(data["session_date"]).any():
        raise ValueError("Foreign-flow knowledge time precedes its trading session")

    for column in ("foreign_buy", "foreign_sell", "foreign_net"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if data[["foreign_buy", "foreign_sell", "foreign_net"]].isna().any().any():
        raise ValueError("Foreign-flow values must be numeric")
    if data["foreign_buy"].lt(0).any() or data["foreign_sell"].lt(0).any():
        raise ValueError("Foreign buy/sell values must be non-negative")

    expected_net = data["foreign_buy"] - data["foreign_sell"]
    if not np.isclose(
        data["foreign_net"].to_numpy(dtype=float),
        expected_net.to_numpy(dtype=float),
        rtol=1e-9,
        atol=1e-9,
        equal_nan=False,
    ).all():
        raise ValueError("foreign_net must equal foreign_buy - foreign_sell")

    for column in ("source", "source_ref", "source_url", "source_sha256"):
        data[column] = _clean_text(data[column])
        if data[column].eq("").any():
            raise ValueError(f"Foreign-flow observation missing provenance field: {column}")

    if (~data["source_url"].str.startswith("https://")).any():
        raise ValueError("Foreign-flow source_url must use HTTPS")
    if (~data["source_sha256"].str.fullmatch(r"[0-9a-fA-F]{64}")).any():
        raise ValueError("Foreign-flow source_sha256 must be a SHA-256 hex digest")
    data["source_sha256"] = data["source_sha256"].str.lower()

    knowledge_key = data["knowledge_at"].dt.strftime("%Y%m%dT%H%M%S%fZ")
    data["observation_id"] = (
        "IDX:FOREIGN_FLOW:"
        + data["ticker"]
        + ":"
        + data["session_date"].dt.strftime("%Y%m%d")
        + ":"
        + data["unit"]
        + ":"
        + knowledge_key
    )

    logical_version_key = ["ticker", "session_date", "unit", "knowledge_at"]
    duplicate = data.duplicated(logical_version_key, keep=False)
    if duplicate.any():
        conflicts = (
            data.loc[duplicate, logical_version_key]
            .astype(str)
            .agg("/".join, axis=1)
            .unique()
            .tolist()[:10]
        )
        raise ValueError(
            "Foreign-flow same-knowledge revision requires explicit reconciliation: "
            f"{conflicts}"
        )

    return (
        data[list(FOREIGN_FLOW_COLUMNS)]
        .sort_values(["ticker", "session_date", "unit", "knowledge_at"])
        .reset_index(drop=True)
    )


def foreign_flow_asof(frame: pd.DataFrame, decision_time: object) -> pd.DataFrame:
    """Select the latest knowable version of each ticker/session/unit observation."""

    canonical = canonicalize_foreign_flow(frame)
    if canonical.empty:
        return canonical

    decision = pd.Timestamp(decision_time)
    if decision.tzinfo is None:
        raise ValueError("decision_time must be timezone-aware")
    decision = decision.tz_convert("UTC")

    visible = canonical[canonical["knowledge_at"].le(decision)].copy()
    if visible.empty:
        return visible

    keys = ["ticker", "session_date", "unit"]
    latest_idx = visible.groupby(keys, sort=False)["knowledge_at"].idxmax()
    return (
        visible.loc[latest_idx]
        .sort_values(["ticker", "session_date", "unit"])
        .reset_index(drop=True)
    )
