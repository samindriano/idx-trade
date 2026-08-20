"""Outcome-blind exact V4-X training-support identity selection helpers."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


ALLOWED_TARGET_STATE_COLUMNS = (
    "ticker",
    "date",
    "target_state_h5",
    "target_state_h10",
)
FORBIDDEN_TARGET_COLUMNS = frozenset(
    {
        "r5",
        "r10",
        "target_rank_h5",
        "target_rank_h10",
        "realized_consensus",
    }
)
KNOWN_TARGET_STATES = frozenset(
    {
        "TARGET_H5_AVAILABLE",
        "TARGET_H10_AVAILABLE",
        "TARGET_BOTH_AVAILABLE",
        "NO_FUTURE_SESSION",
        "MARKET_ENTRY_UNAVAILABLE",
        "TARGET_DATA_UNOBSERVABLE",
        "PRICE_CONTINUITY_UNRESOLVED",
        "TRADING_MECHANISM_REFERENCE_UNRESOLVED",
    }
)


def verify_target_projection(columns: Iterable[str]) -> None:
    actual = tuple(columns)
    if actual != ALLOWED_TARGET_STATE_COLUMNS:
        raise ValueError(
            "target-state projection must be exactly authorized columns: "
            f"{actual!r}"
        )
    if FORBIDDEN_TARGET_COLUMNS.intersection(actual):
        raise ValueError("forbidden numeric target column projected")


def verify_target_schema(columns: Iterable[str]) -> tuple[str, ...]:
    names = tuple(columns)
    missing = set(ALLOWED_TARGET_STATE_COLUMNS) - set(names)
    if missing:
        raise ValueError(f"target-state artifact missing columns: {sorted(missing)}")
    return tuple(sorted(FORBIDDEN_TARGET_COLUMNS.intersection(names)))


def _normalize_keys(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    required = {"ticker", "date"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing identity columns: {sorted(missing)}")
    out = frame.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if out["date"].isna().any() or (out["ticker"] == "").any():
        raise ValueError(f"{label} contains invalid identity")
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError(f"{label} contains duplicate ticker/date identities")
    return out


def normalize_target_states(frame: pd.DataFrame) -> pd.DataFrame:
    verify_target_projection(tuple(frame.columns))
    out = _normalize_keys(frame, label="target-state projection")
    for column in ("target_state_h5", "target_state_h10"):
        if out[column].isna().any():
            raise ValueError(f"{column} contains null state")
        states = set(out[column].astype(str))
        if not states.issubset(KNOWN_TARGET_STATES):
            raise ValueError(f"{column} contains unexpected states: {sorted(states - KNOWN_TARGET_STATES)}")
        out[column] = out[column].astype(str)
    return out.loc[:, ALLOWED_TARGET_STATE_COLUMNS].sort_values(
        ["date", "ticker"], kind="mergesort"
    ).reset_index(drop=True)


def normalize_per_date_support(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"session_index", "date", "h5_eligible", "h10_eligible"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"per-date support missing columns: {sorted(missing)}")
    out = frame.loc[:, sorted(required)].copy()
    out["session_index"] = pd.to_numeric(out["session_index"], errors="raise").astype(int)
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if (
        out["date"].isna().any()
        or out.duplicated(["session_index", "date"]).any()
        or out.duplicated(["date"]).any()
    ):
        raise ValueError("per-date support contains invalid or duplicate identities")
    for column in ("h5_eligible", "h10_eligible"):
        values = out[column]
        if values.dtype == bool:
            out[column] = values
            continue
        normalized = values.astype(str).str.lower().str.strip()
        if not set(normalized).issubset({"true", "false"}):
            raise ValueError(f"{column} contains non-boolean values")
        out[column] = normalized.eq("true")
    return out.sort_values(["session_index", "date"], kind="mergesort").reset_index(drop=True)


def select_exact_head_support(
    target_states: pd.DataFrame,
    per_date: pd.DataFrame,
    *,
    head: str,
    expected_eligible_dates: int,
) -> pd.DataFrame:
    if head not in {"h5", "h10"}:
        raise ValueError(f"unsupported head: {head}")
    states = normalize_target_states(target_states)
    dates = normalize_per_date_support(per_date)
    eligible_column = f"{head}_eligible"
    state_column = f"target_state_{head}"
    available_state = f"TARGET_{head.upper()}_AVAILABLE"
    eligible_dates = set(dates.loc[dates[eligible_column], "date"])
    if len(eligible_dates) != expected_eligible_dates:
        raise ValueError(
            f"{head} eligible-date count mismatch: {len(eligible_dates)} != {expected_eligible_dates}"
        )
    selected = states.loc[
        states["date"].isin(eligible_dates) & states[state_column].eq(available_state),
        ["ticker", "date"],
    ].copy()
    if not set(selected["date"]).issubset(eligible_dates):
        raise ValueError(f"{head} support contains date outside frozen eligible set")
    return selected.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def intersect_affected(
    affected: pd.DataFrame,
    support: pd.DataFrame,
    *,
    impact_type: str | None = None,
) -> pd.DataFrame:
    required = {"ticker", "date", "impact_type"}
    missing = required - set(affected.columns)
    if missing:
        raise ValueError(f"affected representation missing columns: {sorted(missing)}")
    source = affected if impact_type is None else affected.loc[affected["impact_type"].eq(impact_type)]
    source = _normalize_keys(source.loc[:, ["ticker", "date", "impact_type"]], label="affected representation")
    support_keys = _normalize_keys(support.loc[:, ["ticker", "date"]], label="support")
    return source.merge(support_keys, on=["ticker", "date"], how="inner", validate="many_to_one").sort_values(
        ["date", "ticker", "impact_type"], kind="mergesort"
    ).reset_index(drop=True)


def summarize_intersection(frame: pd.DataFrame) -> dict[str, object]:
    if frame.empty:
        return {"rows": 0, "tickers": 0, "dates": 0, "first_date": None, "last_date": None}
    return {
        "rows": int(len(frame)),
        "tickers": int(frame["ticker"].nunique()),
        "dates": int(frame["date"].nunique()),
        "first_date": str(frame["date"].min().date()),
        "last_date": str(frame["date"].max().date()),
    }


def union_intersections(*frames: pd.DataFrame) -> pd.DataFrame:
    pieces = [frame.loc[:, ["ticker", "date", "impact_type"]] for frame in frames if not frame.empty]
    if not pieces:
        return pd.DataFrame(columns=["ticker", "date", "impact_type"])
    out = pd.concat(pieces, ignore_index=True).drop_duplicates(
        ["ticker", "date", "impact_type"]
    )
    return out.sort_values(["date", "ticker", "impact_type"], kind="mergesort").reset_index(drop=True)
