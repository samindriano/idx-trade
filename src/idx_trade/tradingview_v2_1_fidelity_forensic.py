"""Offline forensics for the TradingView V2.1 historical-fidelity anomaly.

Pure helpers only.  No provider/network access lives in this module.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd


HLC_FIELDS = ("high", "low", "close")
CONTROL_TICKERS = ("BBCA", "BBRI", "BMRI", "TLKM", "ASII")


def normalize_ticker(value: object) -> str:
    return str(value).upper().replace(".JK", "").strip()


def add_hlc_comparisons(
    frame: pd.DataFrame,
    *,
    left_prefix: str,
    right_prefix: str,
    result_prefix: str,
) -> pd.DataFrame:
    """Add exact H/L/C field flags and a joint exact flag."""
    result = frame.copy()
    field_flags: list[str] = []
    for field in HLC_FIELDS:
        left = pd.to_numeric(result[f"{left_prefix}{field}"], errors="coerce")
        right = pd.to_numeric(result[f"{right_prefix}{field}"], errors="coerce")
        flag = f"{result_prefix}_{field}_exact"
        result[flag] = left.notna() & right.notna() & left.eq(right)
        field_flags.append(flag)
    result[f"{result_prefix}_hlc_exact"] = result[field_flags].all(axis=1)
    return result


def hlc_mismatch_pattern(
    frame: pd.DataFrame,
    *,
    left_prefix: str,
    right_prefix: str,
) -> pd.Series:
    """Return NONE/H/L/C/HL/HC/LC/HLC or INCOMPLETE for each row."""
    labels: list[str] = []
    for row in frame.itertuples(index=False):
        missing = False
        mismatched: list[str] = []
        for field, token in (("high", "H"), ("low", "L"), ("close", "C")):
            left = getattr(row, f"{left_prefix}{field}", None)
            right = getattr(row, f"{right_prefix}{field}", None)
            if pd.isna(left) or pd.isna(right):
                missing = True
                break
            if float(left) != float(right):
                mismatched.append(token)
        labels.append("INCOMPLETE" if missing else ("".join(mismatched) or "NONE"))
    return pd.Series(labels, index=frame.index, dtype="string")


def three_way_classification(frame: pd.DataFrame) -> pd.Series:
    """Classify TradingView/canonical/official-IDX HLC agreement."""
    required = [
        *(f"tv_{field}" for field in HLC_FIELDS),
        *(f"canonical_{field}" for field in HLC_FIELDS),
        *(f"idx_{field}" for field in HLC_FIELDS),
    ]
    missing_columns = [column for column in required if column not in frame]
    if missing_columns:
        raise ValueError(f"missing three-way columns: {missing_columns}")

    labels: list[str] = []
    for row in frame.itertuples(index=False):
        values: dict[str, tuple[float, float, float] | None] = {}
        for source in ("tv", "canonical", "idx"):
            raw = tuple(getattr(row, f"{source}_{field}") for field in HLC_FIELDS)
            if any(pd.isna(value) for value in raw):
                values[source] = None
            else:
                values[source] = tuple(float(value) for value in raw)  # type: ignore[assignment]
        tv, canonical, idx = values["tv"], values["canonical"], values["idx"]
        if tv is None or canonical is None or idx is None:
            labels.append("INSUFFICIENT_THREE_WAY_SUPPORT")
        elif tv == canonical == idx:
            labels.append("ALL_AGREE")
        elif tv == idx and tv != canonical:
            labels.append("TV_IDX_AGREE_CANONICAL_DIFF")
        elif canonical == idx and tv != canonical:
            labels.append("CANONICAL_IDX_AGREE_TV_DIFF")
        elif tv == canonical and tv != idx:
            labels.append("TV_CANONICAL_AGREE_IDX_DIFF")
        else:
            labels.append("ALL_DIFFER")
    return pd.Series(labels, index=frame.index, dtype="string")


def end_cohort(required_end: object, listed_to: object, window_end: str = "2026-07-31") -> str:
    """Describe whether a request was anchored to the full window or historical end."""
    window = pd.Timestamp(window_end)
    req = pd.to_datetime(required_end, errors="coerce")
    listed = pd.to_datetime(listed_to, errors="coerce")
    if pd.notna(req) and pd.Timestamp(req).normalize() >= window.normalize():
        return "WINDOW_END"
    boundary = listed if pd.notna(listed) else req
    if pd.isna(boundary):
        return "END_UNKNOWN"
    year = int(pd.Timestamp(boundary).year)
    if year <= 2022:
        return "HISTORICAL_END_2022_OR_EARLIER"
    if year <= 2024:
        return "HISTORICAL_END_2023_2024"
    return "HISTORICAL_END_2025_2026"


def concentration_table(
    frame: pd.DataFrame,
    *,
    mismatch_column: str,
    group_column: str = "ticker",
) -> pd.DataFrame:
    """Ticker concentration of mismatch rows plus cumulative mismatch share."""
    if frame.empty:
        return pd.DataFrame(columns=[group_column, "rows", "mismatch_rows", "mismatch_rate", "mismatch_share", "cumulative_mismatch_share"])
    work = frame.copy()
    work[mismatch_column] = work[mismatch_column].fillna(False).astype(bool)
    grouped = (
        work.groupby(group_column, sort=False)
        .agg(rows=(mismatch_column, "size"), mismatch_rows=(mismatch_column, "sum"))
        .reset_index()
    )
    grouped["mismatch_rate"] = grouped["mismatch_rows"] / grouped["rows"].clip(lower=1)
    total = int(grouped["mismatch_rows"].sum())
    grouped = grouped.sort_values(["mismatch_rows", "rows", group_column], ascending=[False, False, True]).reset_index(drop=True)
    grouped["mismatch_share"] = grouped["mismatch_rows"] / total if total else 0.0
    grouped["cumulative_mismatch_share"] = grouped["mismatch_share"].cumsum()
    return grouped


def yearly_fidelity_summary(frame: pd.DataFrame, *, source_pair_prefix: str) -> pd.DataFrame:
    """Summarize exact HLC fidelity by calendar year."""
    if frame.empty:
        return pd.DataFrame(columns=["year", "rows", "hlc_exact_rows", "hlc_exact_rate"])
    work = frame.copy()
    work["year"] = pd.to_datetime(work["session_date"], errors="coerce").dt.year
    flag = f"{source_pair_prefix}_hlc_exact"
    if flag not in work:
        raise ValueError(f"missing fidelity flag: {flag}")
    return (
        work.dropna(subset=["year"])
        .groupby("year", sort=True)
        .agg(rows=(flag, "size"), hlc_exact_rows=(flag, "sum"), hlc_exact_rate=(flag, "mean"))
        .reset_index()
    )


def bar_count_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "bar_count" not in frame:
        return pd.DataFrame(columns=["year", "rows", "min", "p10", "median", "p90", "max"])
    work = frame.copy()
    work["year"] = pd.to_datetime(work["session_date"], errors="coerce").dt.year
    rows: list[dict[str, Any]] = []
    for year, group in work.dropna(subset=["year"]).groupby("year", sort=True):
        values = pd.to_numeric(group["bar_count"], errors="coerce").dropna()
        rows.append(
            {
                "year": int(year),
                "rows": int(len(values)),
                "min": float(values.min()) if len(values) else None,
                "p10": float(values.quantile(0.10)) if len(values) else None,
                "median": float(values.median()) if len(values) else None,
                "p90": float(values.quantile(0.90)) if len(values) else None,
                "max": float(values.max()) if len(values) else None,
            }
        )
    return pd.DataFrame(rows)


def adjudicate_2022(
    controls: pd.DataFrame,
    legacy_2022: pd.DataFrame,
) -> dict[str, Any]:
    """Conservative evidence summary; never authorizes acquisition/modeling."""
    result: dict[str, Any] = {
        "verdict": "2022_ANOMALY_MIXED_UNRESOLVED",
        "controls_2022_rows": 0,
        "controls_2022_tv_vs_canonical": None,
        "controls_2022_tv_vs_idx": None,
        "legacy_2022_rows": int(len(legacy_2022)),
        "legacy_historical_end_mismatch_rate": None,
        "legacy_window_end_mismatch_rate": None,
        "legacy_three_way_counts": {},
        "interpretation": [],
    }
    if not controls.empty:
        work = controls.copy()
        work["year"] = pd.to_datetime(work["session_date"], errors="coerce").dt.year
        c22 = work[work["year"].eq(2022)]
        result["controls_2022_rows"] = int(len(c22))
        if len(c22):
            if "tv_canonical_hlc_exact" in c22:
                result["controls_2022_tv_vs_canonical"] = float(c22["tv_canonical_hlc_exact"].mean())
            if "tv_idx_hlc_exact" in c22:
                supported = c22[c22["three_way_class"].ne("INSUFFICIENT_THREE_WAY_SUPPORT")] if "three_way_class" in c22 else c22
                if len(supported):
                    result["controls_2022_tv_vs_idx"] = float(supported["tv_idx_hlc_exact"].mean())

    if not legacy_2022.empty:
        mismatch = ~legacy_2022["tv_canonical_hlc_exact"].fillna(False)
        hist = legacy_2022["end_cohort"].astype(str).str.startswith("HISTORICAL_END")
        if hist.any():
            result["legacy_historical_end_mismatch_rate"] = float(mismatch[hist].mean())
        if (~hist).any():
            result["legacy_window_end_mismatch_rate"] = float(mismatch[~hist].mean())
        if "three_way_class" in legacy_2022:
            result["legacy_three_way_counts"] = {
                str(key): int(value)
                for key, value in legacy_2022["three_way_class"].value_counts(dropna=False).items()
            }

    c_can = result["controls_2022_tv_vs_canonical"]
    c_idx = result["controls_2022_tv_vs_idx"]
    hist_rate = result["legacy_historical_end_mismatch_rate"]
    live_rate = result["legacy_window_end_mismatch_rate"]
    counts = result["legacy_three_way_counts"]
    resolved_three_way = sum(value for key, value in counts.items() if key != "INSUFFICIENT_THREE_WAY_SUPPORT")
    canonical_conflicts = int(counts.get("TV_IDX_AGREE_CANONICAL_DIFF", 0))
    tv_conflicts = int(counts.get("CANONICAL_IDX_AGREE_TV_DIFF", 0))

    controls_clean = c_can is not None and c_idx is not None and c_can >= 0.95 and c_idx >= 0.95
    selection_signal = hist_rate is not None and live_rate is not None and hist_rate > live_rate + 0.10
    canonical_signal = resolved_three_way > 0 and canonical_conflicts / resolved_three_way >= 0.50
    tv_signal = resolved_three_way > 0 and tv_conflicts / resolved_three_way >= 0.50

    if controls_clean and canonical_signal:
        result["verdict"] = "2022_APPARENT_ANOMALY_CANONICAL_ORACLE_CONFLICT_SUPPORTED"
        result["interpretation"].append("Long-lived controls clear the frozen 95% HLC reference level while legacy mismatches predominantly agree with official IDX against the canonical comparator.")
    elif controls_clean and selection_signal:
        result["verdict"] = "2022_APPARENT_ANOMALY_SUPPORT_SELECTION_SUPPORTED"
        result["interpretation"].append("Long-lived controls are clean while historical-end requests have materially higher legacy mismatch rates than window-end requests.")
    elif c_idx is not None and c_idx < 0.90 and tv_signal:
        result["verdict"] = "2022_TRADINGVIEW_YEAR_SPECIFIC_FIDELITY_RISK"
        result["interpretation"].append("Same-ticker controls disagree with official IDX in 2022 and legacy three-way rows predominantly support the canonical/IDX side.")
    else:
        result["interpretation"].append("Evidence does not isolate one dominant root cause; preserve all competing hypotheses.")

    result["network_calls"] = 0
    result["modeling_authorized"] = False
    result["path_risk_authorized"] = False
    result["protected_outcomes_accessed"] = False
    return result


def ensure_controls(values: Iterable[object]) -> tuple[str, ...]:
    normalized = tuple(normalize_ticker(value) for value in values)
    if normalized != CONTROL_TICKERS:
        raise ValueError(f"expected exact frozen controls {CONTROL_TICKERS}, got {normalized}")
    return normalized
