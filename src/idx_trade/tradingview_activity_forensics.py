"""Offline activity-aware diagnostics for the frozen TradingView admission pilot.

This module never changes the frozen admission verdict.  It asks a narrower
forensic question: when an expected listed ticker-session has no admitted
TradingView 60-minute bar, does the immutable canonical daily panel show
positive trading activity, zero-volume inactivity, or insufficient evidence?
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

import math
import pandas as pd


ACTIVE = "ACTIVE_POSITIVE_VOLUME"
INACTIVE = "INACTIVE_ZERO_VOLUME_FLAT"
UNCERTAIN_ZERO_VOLUME = "UNCERTAIN_ZERO_VOLUME_NONFLAT"
UNCERTAIN_VOLUME = "UNCERTAIN_VOLUME_MISSING"
UNCERTAIN_ROW = "UNCERTAIN_CANONICAL_ROW_MISSING"

TRUE_MISS = "TRUE_TV_MISS_ACTIVE"
EXPLAINED_INACTIVE = "EXPLAINED_NO_TRADE"
UNCERTAIN_MISSING = "UNCERTAIN_MISSING_ACTIVITY"
TV_PRESENT = "TV_PRESENT"

FROZEN_ADMISSION_VERDICT = "TRADINGVIEW_INTRADAY_ADMISSION_REJECTED"


def listing_active(record: Mapping[str, Any], session_date: date) -> bool:
    listed_from = pd.to_datetime(record.get("listed_from"), errors="coerce")
    listed_to = pd.to_datetime(record.get("listed_to"), errors="coerce")
    if pd.isna(listed_from) or listed_from.date() > session_date:
        return False
    return bool(pd.isna(listed_to) or listed_to.date() >= session_date)


def expected_listed_sessions(sample_manifest: Mapping[str, Any]) -> pd.DataFrame:
    """Expand the frozen sample into listed ticker x certified-session rows."""
    records = {str(row["ticker"]).upper(): row for row in sample_manifest["sample_records"]}
    rows: list[dict[str, Any]] = []
    for window in sample_manifest["yearly_windows"]:
        year = int(window["year"])
        for value in window["official_session_dates"]:
            session = date.fromisoformat(str(value))
            for ticker, record in records.items():
                if listing_active(record, session):
                    rows.append({
                        "ticker": ticker,
                        "year": year,
                        "session_date": session.isoformat(),
                        "sample_role": record.get("sample_role"),
                    })
    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(columns=["ticker", "year", "session_date", "sample_role"])
    if result.duplicated(["ticker", "session_date"]).any():
        raise ValueError("duplicate expected ticker-session keys")
    return result.sort_values(["year", "session_date", "ticker"]).reset_index(drop=True)


def canonical_activity_class(row: Mapping[str, Any] | None) -> str:
    """Classify canonical daily activity without imputation or rescaling."""
    if row is None:
        return UNCERTAIN_ROW
    volume = pd.to_numeric(pd.Series([row.get("volume")]), errors="coerce").iloc[0]
    if pd.isna(volume) or not math.isfinite(float(volume)):
        return UNCERTAIN_VOLUME
    if float(volume) > 0:
        return ACTIVE
    if float(volume) < 0:
        return UNCERTAIN_VOLUME

    values = []
    for field in ("high", "low", "close"):
        value = pd.to_numeric(pd.Series([row.get(field)]), errors="coerce").iloc[0]
        if not pd.isna(value) and math.isfinite(float(value)):
            values.append(float(value))
    if len(values) >= 2 and max(values) == min(values):
        return INACTIVE
    return UNCERTAIN_ZERO_VOLUME


def build_activity_forensics(
    expected: pd.DataFrame,
    tv_bars: pd.DataFrame,
    canonical: pd.DataFrame,
) -> pd.DataFrame:
    """Classify every frozen expected ticker-session against immutable evidence."""
    if expected.empty:
        return expected.copy()

    bars = tv_bars.copy()
    if not bars.empty:
        bars["ticker"] = bars["ticker"].astype(str).str.upper()
        bars["session_date"] = bars["session_date"].astype(str)
        if "phase" in bars.columns:
            bars = bars[bars["phase"].eq("fixed_60m")]
        if "in_requested_window" in bars.columns:
            bars = bars[bars["in_requested_window"].astype(bool)]
        if "session_admissible" in bars.columns:
            bars = bars[bars["session_admissible"].astype(bool)]
        tv_keys = set(zip(bars["ticker"], bars["session_date"]))
    else:
        tv_keys = set()

    canon = canonical.copy()
    canon["ticker"] = canon["ticker"].astype(str).str.upper()
    if "date" in canon.columns:
        canon["session_date"] = pd.to_datetime(canon["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        canon["session_date"] = canon["session_date"].astype(str)
    keys = ["ticker", "session_date"]
    if canon.duplicated(keys).any():
        duplicates = canon.loc[canon.duplicated(keys, keep=False), keys].drop_duplicates().head(10).to_dict(orient="records")
        raise ValueError(f"duplicate canonical ticker-session keys: {duplicates}")
    canonical_map = {
        (row.ticker, row.session_date): row._asdict()
        for row in canon[keys + ["open", "high", "low", "close", "volume"]].itertuples(index=False)
    }

    rows: list[dict[str, Any]] = []
    for item in expected.itertuples(index=False):
        key = (str(item.ticker).upper(), str(item.session_date))
        tv_present = key in tv_keys
        activity = canonical_activity_class(canonical_map.get(key))
        if tv_present:
            forensic_class = TV_PRESENT
        elif activity == ACTIVE:
            forensic_class = TRUE_MISS
        elif activity == INACTIVE:
            forensic_class = EXPLAINED_INACTIVE
        else:
            forensic_class = UNCERTAIN_MISSING
        rows.append({
            "ticker": key[0],
            "year": int(item.year),
            "session_date": key[1],
            "sample_role": getattr(item, "sample_role", None),
            "tv_present": tv_present,
            "canonical_activity": activity,
            "forensic_class": forensic_class,
            "tradable_expected": activity == ACTIVE,
            "activity_aware_covered": bool(activity == ACTIVE and tv_present),
            "uncertain_activity": activity in {UNCERTAIN_ZERO_VOLUME, UNCERTAIN_VOLUME, UNCERTAIN_ROW},
        })
    return pd.DataFrame(rows).sort_values(["year", "session_date", "ticker"]).reset_index(drop=True)


def _coverage_row(frame: pd.DataFrame) -> dict[str, Any]:
    active = int(frame["tradable_expected"].sum())
    covered = int(frame["activity_aware_covered"].sum())
    uncertain_missing = int(((~frame["tv_present"]) & frame["uncertain_activity"]).sum())
    explained = int((frame["forensic_class"] == EXPLAINED_INACTIVE).sum())
    true_miss = int((frame["forensic_class"] == TRUE_MISS).sum())
    point = covered / active if active else None
    conservative_denom = active + uncertain_missing
    lower = covered / conservative_denom if conservative_denom else None
    return {
        "listed_certified_sessions": int(len(frame)),
        "canonical_active_sessions": active,
        "tv_covered_active_sessions": covered,
        "true_tv_miss_active": true_miss,
        "explained_no_trade": explained,
        "uncertain_missing_activity": uncertain_missing,
        "activity_aware_coverage": point,
        "conservative_lower_bound": lower,
    }


def activity_aware_summary(forensics: pd.DataFrame, *, threshold: float = 0.90) -> dict[str, Any]:
    """Summarize the diagnostic while keeping the admission verdict immutable."""
    overall = _coverage_row(forensics) if not forensics.empty else _coverage_row(pd.DataFrame({
        "tradable_expected": pd.Series(dtype=bool),
        "activity_aware_covered": pd.Series(dtype=bool),
        "tv_present": pd.Series(dtype=bool),
        "uncertain_activity": pd.Series(dtype=bool),
        "forensic_class": pd.Series(dtype=str),
    }))
    by_year = {str(int(year)): _coverage_row(group) for year, group in forensics.groupby("year", sort=True)} if not forensics.empty else {}

    point_pass = (
        overall["activity_aware_coverage"] is not None
        and overall["activity_aware_coverage"] >= threshold
        and all(value["activity_aware_coverage"] is not None and value["activity_aware_coverage"] >= threshold for value in by_year.values())
    )
    conservative_pass = (
        overall["conservative_lower_bound"] is not None
        and overall["conservative_lower_bound"] >= threshold
        and all(value["conservative_lower_bound"] is not None and value["conservative_lower_bound"] >= threshold for value in by_year.values())
    )
    if conservative_pass:
        interpretation = "ACTIVITY_AWARE_COVERAGE_STRONGLY_EXPLAINS_PILOT_FAILURE"
    elif point_pass:
        interpretation = "ACTIVITY_AWARE_COVERAGE_INCONCLUSIVE_DUE_TO_UNCERTAIN_ACTIVITY"
    else:
        interpretation = "ACTIVITY_AWARE_COVERAGE_DOES_NOT_EXPLAIN_PILOT_FAILURE"

    return {
        "frozen_admission_verdict": FROZEN_ADMISSION_VERDICT,
        "frozen_admission_verdict_changed": False,
        "diagnostic_threshold": threshold,
        "overall": overall,
        "by_year": by_year,
        "forensic_class_counts": forensics["forensic_class"].value_counts().to_dict() if not forensics.empty else {},
        "canonical_activity_counts": forensics["canonical_activity"].value_counts().to_dict() if not forensics.empty else {},
        "point_threshold_pass": point_pass,
        "conservative_threshold_pass": conservative_pass,
        "interpretation": interpretation,
    }
