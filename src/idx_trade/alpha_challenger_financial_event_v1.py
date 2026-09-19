"""PIT-safe CORE3 reporting-event features for the isolated challenger lane."""
from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = frozenset(
    {
        "ticker",
        "date",
        "bundle_status",
        "bundle_reporting_version_id",
        "bundle_reporting_attachment_sha256",
        "bundle_reporting_knowledge_at_utc",
        "leverage_liabilities_to_assets__value",
        "liquidity_cash_to_assets__value",
        "margin_net_income_to_revenue__value",
        "core3_available",
        "same_bundle_violation",
        "selected_knowledge_time_violation",
        "selected_bundle_provenance_complete",
    }
)
FORBIDDEN_TOKENS = ("target", "label", "outcome", "realized", "tp_first", "sl_first")
CORE_COLUMNS = (
    "leverage_liabilities_to_assets__value",
    "liquidity_cash_to_assets__value",
    "margin_net_income_to_revenue__value",
)
FEATURE_COLUMNS = (
    "financial_update_event",
    "delta_leverage",
    "delta_liquidity",
    "delta_margin",
    "quality_delta",
)


def _validate(frame: pd.DataFrame) -> pd.DataFrame:
    forbidden = sorted(
        str(c) for c in frame.columns if any(t in str(c).lower() for t in FORBIDDEN_TOKENS)
    )
    if forbidden:
        raise ValueError(f"outcome-like columns are forbidden: {forbidden}")
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"financial event input missing columns: {sorted(missing)}")
    data = frame.copy()
    data.columns = [str(c).strip().lower() for c in data.columns]
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    data["bundle_reporting_knowledge_at_utc"] = pd.to_datetime(
        data["bundle_reporting_knowledge_at_utc"], errors="coerce", utc=True
    )
    for column in CORE_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if data[["ticker", "date"]].isna().any().any() or data.duplicated(["ticker", "date"]).any():
        raise ValueError("financial bundle has invalid or duplicate ticker/date keys")
    if data[["same_bundle_violation", "selected_knowledge_time_violation"]].astype(bool).any().any():
        raise ValueError("financial bundle contains a PIT violation")
    selected = data["bundle_status"].eq("SELECTED")
    if selected.any() and not data.loc[selected, "selected_bundle_provenance_complete"].astype(bool).all():
        raise ValueError("selected financial bundle provenance is incomplete")
    core = data["core3_available"].astype(bool)
    eligible = selected & core
    if data.loc[eligible, CORE_COLUMNS].isna().any().any():
        raise ValueError("eligible CORE3 row contains missing values")
    state_id = data["bundle_reporting_version_id"].fillna(data["bundle_reporting_attachment_sha256"])
    if state_id.loc[eligible].isna().any():
        raise ValueError("eligible CORE3 row has no reporting state identity")
    data["_eligible"] = eligible
    data["_state_id"] = state_id
    return data.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def build_financial_event_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Return one row per eligible selected CORE3 decision date.

    Deltas are computed between distinct selected reporting states, never
    between arbitrary daily rows. The first state per ticker is neutral because
    it has no prior state for a causal change.
    """

    data = _validate(frame)
    selected = data.loc[data["_eligible"]].copy()
    if selected.empty:
        return pd.DataFrame(columns=["ticker", "date", *FEATURE_COLUMNS])

    state = (
        selected.sort_values(["ticker", "date"], kind="mergesort")
        .drop_duplicates(["ticker", "_state_id"], keep="first")
        .copy()
    )
    grouped = state.groupby("ticker", sort=False)
    state["_previous_state_id"] = grouped["_state_id"].shift(1)
    for column, output in zip(
        CORE_COLUMNS,
        ("delta_leverage", "delta_liquidity", "delta_margin"),
        strict=True,
    ):
        state[output] = state.groupby("ticker", sort=False)[column].diff()
    state["quality_delta"] = -state["delta_leverage"] + state["delta_liquidity"] + state["delta_margin"]
    state["_state_key"] = list(zip(state["ticker"], state["_state_id"], strict=True))

    selected["_state_key"] = list(zip(selected["ticker"], selected["_state_id"], strict=True))
    previous_selected_state = selected.groupby("ticker", sort=False)["_state_id"].shift(1)
    selected["financial_update_event"] = (
        previous_selected_state.notna() & selected["_state_id"].ne(previous_selected_state)
    )
    merge_columns = [
        "_state_key",
        "delta_leverage",
        "delta_liquidity",
        "delta_margin",
        "quality_delta",
    ]
    result = selected[["ticker", "date", "_state_key", "financial_update_event"]].merge(
        state[merge_columns], on="_state_key", how="left", validate="many_to_one"
    )
    event = result["financial_update_event"].fillna(False).astype(bool)
    complete = result[["delta_leverage", "delta_liquidity", "delta_margin"]].notna().all(axis=1)
    result["financial_update_event"] = (event & complete).astype(float)
    result.loc[~(event & complete), ["delta_leverage", "delta_liquidity", "delta_margin", "quality_delta"]] = np.nan
    result = result.drop(columns=["_state_key"])
    for column in FEATURE_COLUMNS:
        values = pd.to_numeric(result[column], errors="coerce")
        if np.isinf(values.to_numpy(dtype=float)).any():
            raise RuntimeError(f"financial event feature contains infinity: {column}")
        result[column] = values
    return result.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


__all__ = ["CORE_COLUMNS", "FEATURE_COLUMNS", "build_financial_event_features"]
