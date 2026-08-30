from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


RAW_COLUMNS = ("open", "high", "low", "close", "volume")
OPTIONAL_VENDOR_COLUMNS = ("adj_close", "dividends", "stock_splits")


def _normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data.columns = [str(column).strip().lower().replace(" ", "_") for column in data.columns]
    aliases = {
        "adj_close": "adj_close",
        "adjclose": "adj_close",
        "stock_splits": "stock_splits",
        "stocksplits": "stock_splits",
    }
    return data.rename(columns={column: aliases.get(column, column) for column in data.columns})


def canonicalize_ohlcv(frame: pd.DataFrame, ticker: str | None = None) -> pd.DataFrame:
    """Validate and canonicalize daily provider data without inventing missing prices.

    Critical semantics:
    - raw observed OHLC stays raw and is used for execution;
    - rows are sorted before any sequential/corporate-action calculation;
    - vendor adjusted close is stored separately and never overwrites raw OHLC;
    - a vendor adjustment-factor change is *not* assumed to be a stock split.
    """

    data = _normalise_columns(frame)
    if "date" not in data.columns:
        data = data.reset_index().rename(columns={data.index.name or "index": "date"})
        data = _normalise_columns(data)

    missing = {"date", *RAW_COLUMNS} - set(data.columns)
    if missing:
        raise ValueError(f"OHLCV columns missing: {sorted(missing)}")

    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    numeric = [*RAW_COLUMNS, *[column for column in OPTIONAL_VENDOR_COLUMNS if column in data.columns]]
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    duplicate_identity_columns = [
        *RAW_COLUMNS,
        *[column for column in OPTIONAL_VENDOR_COLUMNS if column in data.columns],
    ]
    duplicate_dates = data["date"].notna() & data["date"].duplicated(keep=False)
    if duplicate_dates.any():
        conflicting = (
            data.loc[duplicate_dates]
            .groupby("date", sort=False)[duplicate_identity_columns]
            .nunique(dropna=False)
            .gt(1)
            .any(axis=1)
        )
        if conflicting.any():
            dates = [pd.Timestamp(value).date().isoformat() for value in conflicting[conflicting].index]
            raise ValueError(f"Conflicting OHLCV observations for date(s): {dates}")

    # Sort before dedupe and before any pct_change/rolling operation. V1 did this too late.
    data = data.dropna(subset=["date", *RAW_COLUMNS]).sort_values("date", kind="mergesort")
    data = data.drop_duplicates(subset=["date"], keep="first").reset_index(drop=True)

    valid_ohlc = (
        (data[["open", "high", "low", "close"]] > 0).all(axis=1)
        & (data["high"] >= data[["open", "close", "low"]].max(axis=1))
        & (data["low"] <= data[["open", "close", "high"]].min(axis=1))
        & data["volume"].ge(0)
    )
    data = data.loc[valid_ohlc].reset_index(drop=True)

    # Execution layer: immutable aliases make downstream intent explicit.
    for column in ("open", "high", "low", "close"):
        data[f"raw_{column}"] = data[column].astype(float)
    data["raw_volume"] = data["volume"].astype(float)

    if "adj_close" in data.columns:
        data["vendor_adj_close"] = data["adj_close"].astype(float)
        data["vendor_total_return_factor"] = (
            data["vendor_adj_close"].div(data["raw_close"]).replace([np.inf, -np.inf], np.nan)
        )
        data["vendor_adjustment_change"] = data["vendor_total_return_factor"].pct_change().abs().gt(0.01)
    else:
        data["vendor_adj_close"] = np.nan
        data["vendor_total_return_factor"] = np.nan
        data["vendor_adjustment_change"] = False

    split = data.get("stock_splits", pd.Series(0.0, index=data.index)).fillna(0.0)
    dividend = data.get("dividends", pd.Series(0.0, index=data.index)).fillna(0.0)
    data["explicit_split_event"] = split.ne(0)
    data["explicit_dividend_event"] = dividend.ne(0)
    data["explicit_corporate_action"] = data["explicit_split_event"] | data["explicit_dividend_event"]

    # Causal flag only: signal day and prior two observations; never future-centered.
    data["corporate_action_recent"] = (
        data["explicit_corporate_action"].rolling(3, min_periods=1).max().astype(bool)
    )

    if ticker is not None:
        data["ticker"] = str(ticker).upper().replace(".JK", "").strip()

    keep_first = ["date", "ticker"] if "ticker" in data.columns else ["date"]
    keep = keep_first + [
        "raw_open", "raw_high", "raw_low", "raw_close", "raw_volume",
        "vendor_adj_close", "vendor_total_return_factor", "vendor_adjustment_change",
        "explicit_split_event", "explicit_dividend_event", "explicit_corporate_action",
        "corporate_action_recent",
    ]
    optional = [column for column in ("dividends", "stock_splits") if column in data.columns]
    return data[keep + optional].copy()


def raw_execution_prices(frame: pd.DataFrame) -> pd.DataFrame:
    """Return only execution-safe raw price columns."""

    required = {"date", "raw_open", "raw_high", "raw_low", "raw_close", "raw_volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Canonical raw execution columns missing: {sorted(missing)}")
    columns = ["date"] + (["ticker"] if "ticker" in frame.columns else []) + [
        "raw_open", "raw_high", "raw_low", "raw_close", "raw_volume"
    ]
    return frame[columns].copy()


def data_fingerprint_payload(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Stable JSON-compatible rows for external hashing/manifests."""

    if frame.empty:
        return []
    data = frame.sort_values([column for column in ("ticker", "date") if column in frame.columns]).copy()
    records: list[dict[str, Any]] = []
    for row in data.to_dict(orient="records"):
        records.append({
            key: (pd.Timestamp(value).isoformat() if isinstance(value, pd.Timestamp) else value)
            for key, value in row.items()
        })
    return records
