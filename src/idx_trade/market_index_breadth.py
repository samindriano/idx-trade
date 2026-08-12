"""Official IDX market/index context contracts for the bounded V1 audit.

This module deliberately stops short of feature engineering.  It provides:

* a small HTTP provider for the official IDX ``/primary`` endpoints used by
  the IDX frontend;
* canonical validation for index summary and stock summary records; and
* an explicitly derived stock-summary change bucket audit.

IDX does not expose an explicit advance/decline/unchanged aggregate in the
audited endpoints.  Therefore the derived bucket output is never labelled as
official breadth and is not PIT-ready without a separate publication-time
contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping, Sequence
import re

import pandas as pd
import requests


OFFICIAL_IDX_PRIMARY_BASE = "https://block.idx.id/primary"
INDEX_ENDPOINT = "TradingSummary/GetIndexSummary"
STOCK_ENDPOINT = "TradingSummary/GetStockSummary"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

INDEX_FIELDS = (
    "Date",
    "IndexCode",
    "Previous",
    "Highest",
    "Lowest",
    "Close",
    "Change",
    "Volume",
    "Value",
    "Frequency",
    "MarketCapital",
    "NumberOfStock",
)
STOCK_FIELDS = ("Date", "StockCode", "Change", "Volume", "Value", "Frequency")


def _rows(payload: Any) -> list[Mapping[str, Any]]:
    """Extract rows from an IDX response or a row sequence."""

    if isinstance(payload, pd.DataFrame):
        return payload.to_dict(orient="records")
    if isinstance(payload, Mapping):
        data = payload.get("data")
        if isinstance(data, Mapping):
            data = data.get("data")
        if isinstance(data, list):
            payload = data
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        if all(isinstance(row, Mapping) for row in payload):
            return list(payload)
    raise ValueError("IDX payload must contain a list of mapping rows")


def _source_metadata(
    *,
    source_ref: str,
    source_url: str | None,
    source_sha256: str,
    retrieved_at: str | pd.Timestamp | None,
) -> dict[str, Any]:
    if not str(source_ref).strip():
        raise ValueError("source_ref is required")
    digest = str(source_sha256).lower().strip()
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError("source_sha256 must be a lowercase 64-character SHA-256")
    retrieved = pd.NaT if retrieved_at is None else pd.to_datetime(retrieved_at, utc=True)
    return {
        "source": "IDX_OFFICIAL",
        "source_ref": str(source_ref),
        "source_url": source_url,
        "source_sha256": digest,
        "source_retrieved_at": retrieved,
        # Neither endpoint exposes first-publication time.  Access time is not
        # a safe replacement for knowledge_at.
        "knowledge_at": pd.NaT,
        "pit_timing_status": "UNRESOLVED_NO_PUBLICATION_TIMESTAMP",
    }


def _normalise_date(series: pd.Series, name: str = "Date") -> pd.Series:
    values = pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None).dt.normalize()
    if values.isna().any():
        raise ValueError(f"{name} contains invalid dates")
    return values


def _numeric(data: pd.DataFrame, columns: Sequence[str]) -> None:
    for column in columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].isna().any():
            raise ValueError(f"{column} contains non-numeric or missing values")


def canonicalize_idx_index_summary(
    payload: Any,
    *,
    source_ref: str,
    source_url: str | None,
    source_sha256: str,
    retrieved_at: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Validate official IDX index-summary rows without assigning PIT time."""

    data = pd.DataFrame(_rows(payload)).copy()
    missing = set(INDEX_FIELDS) - set(data.columns)
    if missing:
        raise ValueError(f"IDX index summary fields missing: {sorted(missing)}")
    data["session_date"] = _normalise_date(data["Date"])
    data["index_code"] = data["IndexCode"].astype(str).str.strip().str.upper()
    if data["index_code"].eq("").any():
        raise ValueError("IndexCode contains an empty value")
    numeric = [
        "Previous", "Highest", "Lowest", "Close", "Change", "Volume",
        "Value", "Frequency", "MarketCapital", "NumberOfStock",
    ]
    _numeric(data, numeric)
    if data.duplicated(["session_date", "index_code"]).any():
        raise ValueError("Duplicate IDX index summary session/index rows")
    if (data[["Previous", "Highest", "Lowest", "Close"]] < 0).any().any():
        raise ValueError("Index prices cannot be negative")
    if (data["Highest"] < data[["Lowest", "Close"]].max(axis=1)).any():
        raise ValueError("Index High is below Low or Close")
    if (data["Lowest"] > data[["Highest", "Close"]].min(axis=1)).any():
        raise ValueError("Index Low is above High or Close")
    if (data[["Volume", "Value", "Frequency", "MarketCapital", "NumberOfStock"]] < 0).any().any():
        raise ValueError("Index aggregate fields cannot be negative")
    if not (data["NumberOfStock"] % 1 == 0).all():
        raise ValueError("NumberOfStock must be an integer-valued field")

    metadata = _source_metadata(
        source_ref=source_ref,
        source_url=source_url,
        source_sha256=source_sha256,
        retrieved_at=retrieved_at,
    )
    result = pd.DataFrame(
        {
            "session_date": data["session_date"],
            "index_code": data["index_code"],
            "previous": data["Previous"].astype(float),
            "high": data["Highest"].astype(float),
            "low": data["Lowest"].astype(float),
            "close": data["Close"].astype(float),
            "change": data["Change"].astype(float),
            "volume": data["Volume"].astype(float),
            "trading_value_idr": data["Value"].astype(float),
            "frequency": data["Frequency"].astype(float),
            "market_capital_idr": data["MarketCapital"].astype(float),
            "number_of_stock": data["NumberOfStock"].astype(int),
        }
    )
    for key, value in metadata.items():
        result[key] = value
    return result.sort_values(["session_date", "index_code"]).reset_index(drop=True)


def canonicalize_idx_stock_summary(
    payload: Any,
    *,
    source_ref: str,
    source_url: str | None,
    source_sha256: str,
    retrieved_at: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Validate stock-summary rows used only for market-context diagnostics.

    ``OpenPrice`` is intentionally not required or copied.  This lane does not
    adjudicate execution-price provenance; the existing project decision keeps
    OPEN on its separate source lane.
    """

    data = pd.DataFrame(_rows(payload)).copy()
    missing = set(STOCK_FIELDS) - set(data.columns)
    if missing:
        raise ValueError(f"IDX stock summary fields missing: {sorted(missing)}")
    data["session_date"] = _normalise_date(data["Date"])
    data["ticker"] = data["StockCode"].astype(str).str.strip().str.upper()
    if data["ticker"].eq("").any():
        raise ValueError("StockCode contains an empty value")
    _numeric(data, ["Change", "Volume", "Value", "Frequency"])
    optional = [
        "NonRegularVolume", "NonRegularValue", "NonRegularFrequency",
        "ListedShares", "ForeignBuy", "ForeignSell",
    ]
    present_optional = [column for column in optional if column in data.columns]
    _numeric(data, present_optional)
    if data.duplicated(["session_date", "ticker"]).any():
        raise ValueError("Duplicate IDX stock summary session/ticker rows")
    if (data[["Volume", "Value", "Frequency"]] < 0).any().any():
        raise ValueError("Stock summary regular-market fields cannot be negative")
    if present_optional and (data[present_optional] < 0).any().any():
        raise ValueError("Stock summary optional quantity fields cannot be negative")

    metadata = _source_metadata(
        source_ref=source_ref,
        source_url=source_url,
        source_sha256=source_sha256,
        retrieved_at=retrieved_at,
    )
    result = pd.DataFrame(
        {
            "session_date": data["session_date"],
            "ticker": data["ticker"],
            "price_change": data["Change"].astype(float),
            "regular_volume": data["Volume"].astype(float),
            "trading_value_idr": data["Value"].astype(float),
            "regular_frequency": data["Frequency"].astype(float),
        }
    )
    aliases = {
        "NonRegularVolume": "nonregular_volume",
        "NonRegularValue": "nonregular_value_idr",
        "NonRegularFrequency": "nonregular_frequency",
        "ListedShares": "listed_shares",
        "ForeignBuy": "foreign_buy",
        "ForeignSell": "foreign_sell",
    }
    for source, target in aliases.items():
        if source in data:
            result[target] = data[source].astype(float)
    for key, value in metadata.items():
        result[key] = value
    return result.sort_values(["session_date", "ticker"]).reset_index(drop=True)


def derive_stock_summary_breadth(stock_summary: pd.DataFrame) -> pd.DataFrame:
    """Return derived change buckets, never an official breadth aggregate.

    Only positive regular-market volume is eligible for a change bucket.  A
    zero-volume row is reported separately and is never silently counted as an
    unchanged stock.
    """

    required = {"session_date", "ticker", "price_change", "regular_volume"}
    missing = required - set(stock_summary.columns)
    if missing:
        raise ValueError(f"Canonical stock summary fields missing: {sorted(missing)}")
    data = stock_summary.copy()
    if data[["price_change", "regular_volume"]].isna().any().any():
        raise ValueError("Breadth derivation cannot use missing change/volume")
    if (data["regular_volume"] < 0).any():
        raise ValueError("Breadth derivation cannot use negative volume")
    observed = data["regular_volume"] > 0
    grouped = data.assign(_observed=observed).groupby("session_date", sort=True)
    result = grouped.agg(
        source_rows=("ticker", "size"),
        zero_volume_rows=("_observed", lambda values: int((~values).sum())),
        traded_rows=("_observed", "sum"),
    ).reset_index()
    result["advancing_rows"] = grouped["price_change"].apply(
        lambda values: int(((values > 0) & observed.loc[values.index]).sum())
    ).to_numpy()
    result["declining_rows"] = grouped["price_change"].apply(
        lambda values: int(((values < 0) & observed.loc[values.index]).sum())
    ).to_numpy()
    result["unchanged_traded_rows"] = grouped["price_change"].apply(
        lambda values: int(((values == 0) & observed.loc[values.index]).sum())
    ).to_numpy()
    result["breadth_status"] = "DERIVED_STOCK_SUMMARY_CHANGE_BUCKETS_NOT_OFFICIAL_BREADTH"
    result["official_breadth_field_present"] = False
    return result


def reconcile_index_stock_aggregates(
    index_summary: pd.DataFrame,
    stock_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Audit COMPOSITE totals against regular + non-regular stock rows."""

    required_index = {"session_date", "index_code", "volume", "trading_value_idr", "frequency"}
    required_stock = {"session_date", "regular_volume", "trading_value_idr", "regular_frequency"}
    if not required_index.issubset(index_summary.columns):
        raise ValueError("Canonical index summary fields missing for reconciliation")
    if not required_stock.issubset(stock_summary.columns):
        raise ValueError("Canonical stock summary fields missing for reconciliation")
    stocks = stock_summary.copy()
    for column in ("nonregular_volume", "nonregular_value_idr", "nonregular_frequency"):
        if column not in stocks:
            stocks[column] = 0.0
    totals = stocks.groupby("session_date", as_index=False).agg(
        regular_volume=("regular_volume", "sum"),
        regular_trading_value_idr=("trading_value_idr", "sum"),
        regular_frequency=("regular_frequency", "sum"),
        nonregular_volume=("nonregular_volume", "sum"),
        nonregular_value_idr=("nonregular_value_idr", "sum"),
        nonregular_frequency=("nonregular_frequency", "sum"),
    )
    indices = index_summary[index_summary["index_code"].eq("COMPOSITE")].copy()
    merged = indices.merge(totals, on="session_date", how="left", validate="one_to_one")
    merged["volume_delta"] = merged["volume"] - merged["regular_volume"] - merged["nonregular_volume"]
    merged["trading_value_delta"] = merged["trading_value_idr"] - merged["regular_trading_value_idr"] - merged["nonregular_value_idr"]
    merged["frequency_delta"] = merged["frequency"] - merged["regular_frequency"] - merged["nonregular_frequency"]
    merged["exact_reconciliation"] = merged[["volume_delta", "trading_value_delta", "frequency_delta"]].eq(0).all(axis=1)
    return merged[["session_date", "volume_delta", "trading_value_delta", "frequency_delta", "exact_reconciliation"]]


@dataclass
class OfficialIDXMarketContextProvider:
    """Small provider for direct official IDX market-context endpoints."""

    base_url: str = OFFICIAL_IDX_PRIMARY_BASE
    timeout_seconds: float = 45.0
    session: requests.Session = field(default_factory=requests.Session)

    def _get(self, endpoint: str, params: Mapping[str, Any]) -> Any:
        response = self.session.get(
            f"{self.base_url.rstrip('/')}/{endpoint}",
            params=dict(params),
            headers={"Accept": "application/json"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def fetch_index_summary(self, session_date: date | str) -> Any:
        value = pd.Timestamp(session_date).date().isoformat()
        return self._get(INDEX_ENDPOINT, {"length": 100, "start": 0, "date": value})

    def fetch_stock_summary(self, session_date: date | str) -> Any:
        value = pd.Timestamp(session_date).date().isoformat()
        return self._get(STOCK_ENDPOINT, {"length": 100, "start": 0, "date": value})


def pit_timing_ready(frame: pd.DataFrame) -> bool:
    """Return true only when an explicit publication/knowledge time exists."""

    required = {"knowledge_at", "pit_timing_status"}
    if frame.empty or not required.issubset(frame.columns):
        return False
    values = pd.to_datetime(frame["knowledge_at"], errors="coerce", utc=True)
    return bool(values.notna().all() and frame["pit_timing_status"].eq("RESOLVED").all())
