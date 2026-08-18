"""Outcome-blind helpers for the V4 primary-liquid 740 -> CA-support 610 audit."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd


def normalize_ticker(values: pd.Series) -> pd.Series:
    return (
        values.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def normalize_date(values: pd.Series, label: str) -> pd.Series:
    out = pd.to_datetime(values, errors="coerce")
    if out.isna().any():
        raise RuntimeError(f"INVALID_DATE_COLUMN:{label}")
    return out.dt.tz_localize(None).dt.normalize()


def latest_regular_anchor(anchors: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "market", "as_of_date", "state"}
    missing = required - set(anchors.columns)
    if missing:
        raise RuntimeError(f"TRADABILITY_ANCHOR_COLUMNS_MISSING:{sorted(missing)}")
    work = anchors.loc[:, list(required)].copy()
    work["ticker"] = normalize_ticker(work["ticker"])
    work["market"] = work["market"].astype(str).str.upper().str.strip()
    work["state"] = work["state"].astype(str).str.upper().str.strip()
    work["as_of_date"] = pd.to_datetime(work["as_of_date"], errors="coerce")
    work = work[work["market"].eq("REGULAR") & work["as_of_date"].notna()].copy()
    work["as_of_date"] = work["as_of_date"].dt.tz_localize(None).dt.normalize()
    if work.empty:
        return pd.DataFrame(columns=["ticker", "latest_anchor_date", "latest_anchor_state"])

    latest_date = work.groupby("ticker", sort=True)["as_of_date"].max().rename("latest_anchor_date")
    merged = work.merge(latest_date, left_on=["ticker", "as_of_date"], right_on=["ticker", "latest_anchor_date"])
    states = (
        merged.groupby(["ticker", "latest_anchor_date"], sort=True)["state"]
        .agg(lambda values: tuple(sorted(set(values))))
        .reset_index()
    )
    states["latest_anchor_state"] = states["state"].map(
        lambda values: values[0] if len(values) == 1 else "AMBIGUOUS"
    )
    return states[["ticker", "latest_anchor_date", "latest_anchor_state"]]


def _first_matching_column(columns: list[str], exact: tuple[str, ...], contains: tuple[str, ...]) -> str | None:
    lower = {column.lower(): column for column in columns}
    for candidate in exact:
        if candidate in lower:
            return lower[candidate]
    for column in columns:
        key = column.lower()
        if all(token in key for token in contains):
            return column
    return None


def security_master_overlay(master: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if "ticker" not in master.columns:
        raise RuntimeError("SECURITY_MASTER_TICKER_COLUMN_MISSING")
    work = master.copy()
    work["ticker"] = normalize_ticker(work["ticker"])
    if work["ticker"].duplicated().any():
        # Preserve fail-closed semantics. A non-unique master cannot silently pick a row.
        dupes = sorted(work.loc[work["ticker"].duplicated(keep=False), "ticker"].unique().tolist())
        raise RuntimeError(f"SECURITY_MASTER_DUPLICATE_TICKER:{dupes[:20]}")

    columns = list(work.columns)
    listing_col = _first_matching_column(
        columns,
        ("listing_date", "listed_date", "first_listing_date", "first_listed_date"),
        ("list", "date"),
    )
    delist_col = _first_matching_column(
        columns,
        ("delisting_date", "delisted_date", "delist_date"),
        ("delist",),
    )
    status_col = _first_matching_column(
        columns,
        ("listing_status", "security_status", "status"),
        ("status",),
    )

    result = pd.DataFrame({"ticker": work["ticker"]})
    if listing_col:
        result["security_master_listing_date"] = pd.to_datetime(work[listing_col], errors="coerce").dt.tz_localize(None).dt.normalize()
    else:
        result["security_master_listing_date"] = pd.NaT
    if delist_col:
        result["security_master_delisting_date"] = pd.to_datetime(work[delist_col], errors="coerce").dt.tz_localize(None).dt.normalize()
    else:
        result["security_master_delisting_date"] = pd.NaT
    if status_col:
        result["security_master_status"] = work[status_col].astype(str).str.upper().str.strip()
    else:
        result["security_master_status"] = ""

    # Keep a compact raw record for later forensic inspection without guessing semantics.
    result["security_master_record_json"] = work.apply(
        lambda row: json.dumps(
            {str(key): (None if pd.isna(value) else str(value)) for key, value in row.items()},
            sort_keys=True,
            ensure_ascii=False,
        ),
        axis=1,
    )
    metadata = {
        "columns": columns,
        "detected_listing_date_column": listing_col,
        "detected_delisting_date_column": delist_col,
        "detected_status_column": status_col,
    }
    return result, metadata


def classify_presence(row: pd.Series, frozen_end: pd.Timestamp) -> str:
    delist = row.get("security_master_delisting_date")
    status = str(row.get("security_master_status") or "").upper()
    anchor_state = str(row.get("latest_anchor_state") or "").upper()
    anchor_date = pd.to_datetime(row.get("latest_anchor_date"), errors="coerce")
    panel_rows_2026 = int(row.get("panel_rows_2026") or 0)

    if pd.notna(delist) and pd.Timestamp(delist).normalize() <= frozen_end:
        return "DELISTED_BY_FROZEN_END"
    if "DELIST" in status:
        return "DELISTED_STATUS_IN_SECURITY_MASTER"
    if pd.notna(anchor_date) and pd.Timestamp(anchor_date).year == 2026 and anchor_state == "ACTIVE":
        return "ACTIVE_2026_EXACT_TRADABILITY_ANCHOR"
    if any(token in status for token in ("ACTIVE", "LISTED")) and "DELIST" not in status:
        return "ACTIVE_OR_LISTED_SECURITY_MASTER_STATUS"
    if panel_rows_2026 > 0:
        return "PRESENT_IN_2026_SIGNAL_PANEL_STATUS_UNPROVEN"
    return "HISTORICAL_ONLY_NO_2026_PANEL_ROWS"


def classify_ca_absence(row: pd.Series) -> str:
    validation_rows = int(row.get("primary_rows_validation_600") or 0)
    if validation_rows > 0:
        return "POTENTIAL_CA_SUPPORT_DATA_GAP"
    if int(row.get("primary_rows_2026") or 0) > 0:
        return "PRIMARY_LIQUID_2026_OUTSIDE_FROZEN_VALIDATION_DATES"
    if int(row.get("panel_rows_2026") or 0) > 0:
        return "ACTIVE_OR_PRESENT_2026_BUT_NOT_PRIMARY_LIQUID_ON_VALIDATION"
    return "HISTORICAL_PRIMARY_LIQUID_ONLY_BEFORE_2026"


def liquidity_band(value: Any) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "UNKNOWN"
    number = float(numeric)
    if number >= 100_000_000_000:
        return "VERY_HIGH_LIQUIDITY_100B_PLUS"
    if number >= 25_000_000_000:
        return "HIGH_LIQUIDITY_25B_PLUS"
    if number >= 5_000_000_000:
        return "MATERIAL_LIQUIDITY_5B_PLUS"
    if number >= 1_000_000_000:
        return "PRIMARY_THRESHOLD_1B_PLUS"
    return "BELOW_PRIMARY_THRESHOLD"


def build_diff_audit(
    *,
    primary_state: pd.DataFrame,
    panel: pd.DataFrame,
    ca_tickers: set[str],
    validation_dates: set[pd.Timestamp],
    anchors: pd.DataFrame,
    security_master: pd.DataFrame,
    frozen_end: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    primary = primary_state.copy()
    primary["ticker"] = normalize_ticker(primary["ticker"])
    primary["date"] = normalize_date(primary["date"], "primary.date")
    primary["universe_primary_liquid"] = primary["universe_primary_liquid"].astype(bool)
    primary_true = primary[primary["universe_primary_liquid"]].copy()
    primary_tickers = set(primary_true["ticker"].unique())
    missing = sorted(primary_tickers - set(ca_tickers))

    panel_work = panel.copy()
    panel_work["ticker"] = normalize_ticker(panel_work["ticker"])
    panel_work["date"] = normalize_date(panel_work["date"], "panel.date")

    latest_all = (
        primary.sort_values(["ticker", "date"], kind="mergesort")
        .groupby("ticker", sort=True)
        .tail(1)
        .set_index("ticker")
    )
    records: list[dict[str, Any]] = []
    for ticker in missing:
        p_all = primary[primary["ticker"].eq(ticker)]
        p_true = primary_true[primary_true["ticker"].eq(ticker)]
        raw = panel_work[panel_work["ticker"].eq(ticker)]
        val_true = p_true[p_true["date"].isin(validation_dates)]
        p2026 = p_true[p_true["date"].dt.year.eq(2026)]
        raw2026 = raw[raw["date"].dt.year.eq(2026)]
        latest = latest_all.loc[ticker]
        records.append(
            {
                "ticker": ticker,
                "primary_rows_total": int(len(p_true)),
                "primary_first_date": p_true["date"].min(),
                "primary_last_date": p_true["date"].max(),
                "primary_rows_validation_600": int(len(val_true)),
                "primary_rows_2026": int(len(p2026)),
                "panel_first_date": raw["date"].min(),
                "panel_last_date": raw["date"].max(),
                "panel_rows_2026": int(len(raw2026)),
                "latest_universe_primary_liquid": bool(latest["universe_primary_liquid"]),
                "latest_median_regular_value_60": float(latest["median_regular_value_60"])
                if pd.notna(latest["median_regular_value_60"]) else np.nan,
                "peak_median_regular_value_60": float(pd.to_numeric(p_all["median_regular_value_60"], errors="coerce").max()),
            }
        )
    audit = pd.DataFrame(records)

    anchor = latest_regular_anchor(anchors)
    master, master_meta = security_master_overlay(security_master)
    audit = audit.merge(anchor, on="ticker", how="left", validate="one_to_one")
    audit = audit.merge(master, on="ticker", how="left", validate="one_to_one")
    audit["presence_class"] = audit.apply(lambda row: classify_presence(row, frozen_end), axis=1)
    audit["ca_absence_class"] = audit.apply(classify_ca_absence, axis=1)
    audit["latest_liquidity_band"] = audit["latest_median_regular_value_60"].map(liquidity_band)
    audit["peak_liquidity_band"] = audit["peak_median_regular_value_60"].map(liquidity_band)
    audit["needs_manual_priority_review"] = (
        audit["ca_absence_class"].eq("POTENTIAL_CA_SUPPORT_DATA_GAP")
        | audit["presence_class"].str.startswith("ACTIVE_2026", na=False)
        | audit["latest_liquidity_band"].isin(
            ["VERY_HIGH_LIQUIDITY_100B_PLUS", "HIGH_LIQUIDITY_25B_PLUS", "MATERIAL_LIQUIDITY_5B_PLUS"]
        )
    )
    audit = audit.sort_values(
        ["needs_manual_priority_review", "latest_median_regular_value_60", "ticker"],
        ascending=[False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    return audit, master_meta
