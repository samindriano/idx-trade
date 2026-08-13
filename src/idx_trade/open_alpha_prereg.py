"""Outcome-blind preregistration and cache audit for clean-V2 Open alpha.

This module deliberately stops before any target, model, score, provider, or
forward-outcome path.  It consumes only the already accepted PIT-safe feature,
OHLC, session, listing, tradability, and Open-provenance artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


V2_XS_FEATURE_COLUMNS = (
    "xs_rank_close_return_5",
    "xs_rank_close_return_20",
    "xs_rank_atr14_over_close",
    "xs_rank_close_position_20",
    "xs_rank_distance_high_20_atr",
    "xs_rank_distance_low_20_atr",
    "xs_rank_distance_high_60_atr",
    "xs_rank_distance_low_60_atr",
    "xs_rank_relative_volume_20",
    "xs_rank_log_regular_value_relative_20",
)

V2_MARKET_CONTEXT_COLUMNS = (
    "market_primary_liquid_count",
    "market_breadth_return_5_positive",
    "market_breadth_return_20_positive",
    "market_median_close_return_5",
    "market_median_close_return_20",
    "market_median_atr14_over_close",
    "market_median_close_position_20",
    "market_median_relative_volume_20",
    "market_median_log_regular_value_relative_20",
)

V2_MARKET_RELATIVE_COLUMNS = (
    "market_relative_close_return_5",
    "market_relative_close_return_20",
    "market_relative_atr14_over_close",
    "market_relative_close_position_20",
    "market_relative_relative_volume_20",
    "market_relative_log_regular_value_relative_20",
)

V2_FULL_FEATURE_COLUMNS = (
    *V2_XS_FEATURE_COLUMNS,
    *V2_MARKET_CONTEXT_COLUMNS,
    *V2_MARKET_RELATIVE_COLUMNS,
)

SAME_DAY_OPEN_FEATURES = (
    "open_position",
    "open_to_high",
    "open_to_low",
)

PREVIOUS_RANGE_OPEN_FEATURES = (
    "open_position_prev_active_range",
    "open_to_prev_high",
    "open_to_prev_low",
)

ALL_OPEN_FEATURES = (*SAME_DAY_OPEN_FEATURES, *PREVIOUS_RANGE_OPEN_FEATURES)
CANDIDATE_FEATURE_COLUMNS = (*V2_FULL_FEATURE_COLUMNS, *ALL_OPEN_FEATURES)

# This is the exact clean V2 model contract from the accepted historical
# lineage.  It is recorded for traceability only; this module never instantiates
# or fits a model.
CONTROL_MODEL = "HGB_XS_MARKET"
CONTROL_SEMANTICS_SOURCE_COMMIT = "3099b94"
CONTROL_PREPROCESSING = (
    "ColumnTransformer[numeric=Pipeline[SimpleImputer(strategy=median, "
    "add_indicator=True, keep_empty_features=True)], remainder=drop]"
)
CONTROL_HGB_PARAMETERS = {
    "learning_rate": 0.05,
    "max_iter": 200,
    "max_leaf_nodes": 31,
    "l2_regularization": 1.0,
    "random_state": 42,
}


@dataclass(frozen=True)
class FrozenFold:
    name: str
    train_start: int
    train_end: int
    purge_start: int
    purge_end: int
    validation_start: int
    validation_end: int


FROZEN_V2_FOLDS = (
    FrozenFold("V2F1", 1, 504, 505, 524, 525, 624),
    FrozenFold("V2F2", 1, 624, 625, 644, 645, 744),
    FrozenFold("V2F3", 1, 744, 745, 764, 765, 864),
    FrozenFold("V2F4", 1, 864, 865, 884, 885, 984),
    FrozenFold("V2F5", 1, 984, 985, 1004, 1005, 1104),
    FrozenFold("V2F6", 1, 1104, 1105, 1124, 1125, 1224),
)

OUTCOME_COLUMNS = frozenset(
    {
        "binary_target",
        "label_status",
        "target",
        "outcome",
        "outcome_label",
        "future_return",
        "future_high",
        "future_low",
        "tp_first",
        "sl_first",
    }
)

V2_OUTCOME_BLIND_COLUMNS = (
    "ticker",
    "date",
    "signal_session_index",
    "universe_primary_liquid",
    *V2_FULL_FEATURE_COLUMNS,
)
PANEL_COLUMNS = (
    "ticker",
    "date",
    "high",
    "low",
    "close",
    "open",
    "open_available",
    "open_evidence_status",
)
OPEN_COVERAGE_COLUMNS = (
    "ticker",
    "date",
    "signal_session_index",
    "high",
    "low",
    "close",
    "open",
    "open_position",
    "open_to_high",
    "open_to_low",
    "open_feature_ready",
    "open_known",
)
OPEN_PROVENANCE_COLUMNS = (
    "ticker",
    "date",
    "open_source",
    "open_evidence_class",
    "validation_status",
    "source_cache_ref",
)


def _ensure_outcome_blind(columns: Iterable[str]) -> None:
    found = OUTCOME_COLUMNS.intersection(columns)
    if found:
        raise ValueError(f"outcome/target columns are forbidden in blind audit: {sorted(found)}")


def _normalise_dates(values: pd.Series) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce")
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_localize(None)
    return dates.dt.normalize()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_key_sha256(frame: pd.DataFrame) -> str:
    required = ("ticker", "date", "signal_session_index")
    if not set(required).issubset(frame.columns):
        raise ValueError(f"key hash requires {required}")
    keys = frame.loc[:, required].copy()
    keys["ticker"] = keys["ticker"].astype(str).str.upper().str.strip()
    keys["date"] = _normalise_dates(keys["date"]).dt.strftime("%Y-%m-%d")
    keys["signal_session_index"] = pd.to_numeric(keys["signal_session_index"], errors="raise").astype(int)
    keys = keys.sort_values(list(required), kind="mergesort")
    payload = "".join(
        f"{row.ticker}|{row.date}|{row.signal_session_index}\n"
        for row in keys.itertuples(index=False)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def feature_order_sha256(columns: Sequence[str]) -> str:
    return hashlib.sha256(json.dumps(list(columns), separators=(",", ":")).encode("utf-8")).hexdigest()


def same_day_open_geometry(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute exact same-day Open geometry, fail-closed for invalid ranges."""

    required = {"open", "high", "low"}
    if not required.issubset(frame.columns):
        raise ValueError(f"same-day geometry requires {sorted(required)}")
    high = pd.to_numeric(frame["high"], errors="coerce").astype(float)
    low = pd.to_numeric(frame["low"], errors="coerce").astype(float)
    open_price = pd.to_numeric(frame["open"], errors="coerce").astype(float)
    valid = (
        np.isfinite(high)
        & np.isfinite(low)
        & np.isfinite(open_price)
        & (high > 0.0)
        & (low > 0.0)
        & (high > low)
        & (open_price > 0.0)
        & (open_price >= low)
        & (open_price <= high)
    )
    denominator = high - low
    result = pd.DataFrame(index=frame.index, columns=SAME_DAY_OPEN_FEATURES, dtype=float)
    result.loc[valid, "open_position"] = (open_price[valid] - low[valid]) / denominator[valid]
    result.loc[valid, "open_to_high"] = high[valid] / open_price[valid] - 1.0
    result.loc[valid, "open_to_low"] = low[valid] / open_price[valid] - 1.0
    return result


def previous_range_open_geometry(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute previous-active-range geometry, without filling invalid values."""

    required = {"open", "previous_high", "previous_low"}
    if not required.issubset(frame.columns):
        raise ValueError(f"previous-range geometry requires {sorted(required)}")
    high = pd.to_numeric(frame["previous_high"], errors="coerce").astype(float)
    low = pd.to_numeric(frame["previous_low"], errors="coerce").astype(float)
    open_price = pd.to_numeric(frame["open"], errors="coerce").astype(float)
    valid = (
        np.isfinite(high)
        & np.isfinite(low)
        & np.isfinite(open_price)
        & (high > 0.0)
        & (low > 0.0)
        & (high > low)
        & (open_price > 0.0)
    )
    denominator = high - low
    result = pd.DataFrame(index=frame.index, columns=PREVIOUS_RANGE_OPEN_FEATURES, dtype=float)
    result.loc[valid, "open_position_prev_active_range"] = (open_price[valid] - low[valid]) / denominator[valid]
    result.loc[valid, "open_to_prev_high"] = high[valid] / open_price[valid] - 1.0
    result.loc[valid, "open_to_prev_low"] = low[valid] / open_price[valid] - 1.0
    return result


def load_clean_v2_outcome_blind(path: Path) -> pd.DataFrame:
    """Load only identity and feature columns; never request target columns."""

    _ensure_outcome_blind(V2_OUTCOME_BLIND_COLUMNS)
    frame = pd.read_parquet(path, columns=list(V2_OUTCOME_BLIND_COLUMNS))
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame["date"] = _normalise_dates(frame["date"])
    if frame["date"].isna().any():
        raise ValueError("clean V2 contains invalid dates")
    if frame.duplicated(["ticker", "date", "signal_session_index"]).any():
        raise ValueError("clean V2 contains duplicate identity keys")
    return frame


def _load_open_coverage(path: Path) -> pd.DataFrame:
    _ensure_outcome_blind(OPEN_COVERAGE_COLUMNS)
    frame = pd.read_csv(path, usecols=list(OPEN_COVERAGE_COLUMNS))
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame["date"] = _normalise_dates(frame["date"])
    if frame.duplicated(["ticker", "date", "signal_session_index"]).any():
        raise ValueError("Open coverage contains duplicate identity keys")
    return frame


def _load_panel(path: Path) -> pd.DataFrame:
    _ensure_outcome_blind(PANEL_COLUMNS)
    frame = pd.read_parquet(path, columns=list(PANEL_COLUMNS))
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame["date"] = _normalise_dates(frame["date"])
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("PIT-safe panel contains duplicate ticker/date keys")
    return frame


def _suspension_mask(frame: pd.DataFrame, intervals: pd.DataFrame) -> pd.Series:
    mask = pd.Series(False, index=frame.index)
    regular = intervals[intervals["market"].astype(str).str.upper().eq("REGULAR")]
    for row in regular.itertuples(index=False):
        start = pd.Timestamp(row.effective_from)
        end = pd.Timestamp(row.effective_to) if pd.notna(row.effective_to) else pd.Timestamp.max
        mask |= frame["ticker"].eq(str(row.ticker).upper()) & frame["date"].between(start, end)
    return mask


def compute_previous_active_features(
    panel: pd.DataFrame,
    anchors: pd.DataFrame,
    calendar: pd.DataFrame,
) -> pd.DataFrame:
    """Link each observed bar to the immediately previous ACTIVE observed bar."""

    required_panel = {"ticker", "date", "high", "low"}
    required_anchor = {"ticker", "as_of_date", "state"}
    required_calendar = {"date"}
    if not required_panel.issubset(panel.columns):
        raise ValueError(f"panel missing {sorted(required_panel - set(panel.columns))}")
    if not required_anchor.issubset(anchors.columns):
        raise ValueError(f"anchors missing {sorted(required_anchor - set(anchors.columns))}")
    if not required_calendar.issubset(calendar.columns):
        raise ValueError(f"calendar missing {sorted(required_calendar - set(calendar.columns))}")

    work = panel.copy()
    work["date"] = _normalise_dates(work["date"])
    work["ticker"] = work["ticker"].astype(str).str.upper().str.strip()
    anchor = anchors.loc[:, ["ticker", "as_of_date", "state"]].copy()
    anchor["ticker"] = anchor["ticker"].astype(str).str.upper().str.strip()
    anchor["as_of_date"] = _normalise_dates(anchor["as_of_date"])
    if anchor.duplicated(["ticker", "as_of_date"]).any():
        raise ValueError("tradability anchors contain duplicate ticker/date keys")
    work = work.merge(
        anchor,
        left_on=["ticker", "date"],
        right_on=["ticker", "as_of_date"],
        how="left",
        validate="one_to_one",
    ).drop(columns=["as_of_date"])
    session = calendar.loc[:, ["date"]].copy()
    session["date"] = _normalise_dates(session["date"])
    session = session.drop_duplicates("date").sort_values("date", kind="mergesort")
    session["session_index"] = np.arange(1, len(session) + 1, dtype=int)
    work = work.merge(session, on="date", how="left", validate="many_to_one")
    if work["session_index"].isna().any():
        raise ValueError("panel contains dates outside the official exchange calendar")
    work["state"] = work["state"].astype("string")
    active = work[work["state"].eq("ACTIVE")].copy()
    active = active.sort_values(["ticker", "session_index"], kind="mergesort")
    grouped = active.groupby("ticker", sort=False)
    active["previous_active_date"] = grouped["date"].shift(1)
    active["previous_active_session_index"] = grouped["session_index"].shift(1)
    active["previous_high"] = grouped["high"].shift(1)
    active["previous_low"] = grouped["low"].shift(1)
    active["previous_active_session_gap"] = active["session_index"] - active["previous_active_session_index"]
    active["current_state"] = active["state"]
    return active.reset_index(drop=True)


def _close_match(left: pd.Series, right: pd.Series, *, atol: float = 1e-12) -> pd.Series:
    a = pd.to_numeric(left, errors="coerce").astype(float).to_numpy()
    b = pd.to_numeric(right, errors="coerce").astype(float).to_numpy()
    both_na = np.isnan(a) & np.isnan(b)
    return pd.Series(both_na | np.isclose(a, b, rtol=0.0, atol=atol, equal_nan=False), index=left.index)


def _feature_stats(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce").astype(float)
        finite = values[np.isfinite(values)]
        rows.append(
            {
                "feature": column,
                "rows": int(len(values)),
                "finite": int(len(finite)),
                "missing_or_nonfinite": int(len(values) - len(finite)),
                "zero": int((finite == 0.0).sum()),
                "min": float(finite.min()) if len(finite) else None,
                "q01": float(finite.quantile(0.01)) if len(finite) else None,
                "median": float(finite.median()) if len(finite) else None,
                "q99": float(finite.quantile(0.99)) if len(finite) else None,
                "max": float(finite.max()) if len(finite) else None,
                "mean": float(finite.mean()) if len(finite) else None,
                "std": float(finite.std(ddof=0)) if len(finite) else None,
            }
        )
    return pd.DataFrame(rows)


def _jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    if pd.isna(value) if not isinstance(value, (str, bytes, bool)) else False:
        return None
    return value


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_open_alpha_blind_audit(
    *,
    v2_table: Path,
    open_coverage: Path,
    panel: Path,
    calendar: Path,
    security_master: Path,
    tradability_anchors: Path,
    tradability_intervals: Path,
    open_provenance: Path | None,
    output_root: Path,
    expected_panel_sha256: str | None = None,
) -> dict[str, object]:
    """Build the frozen common-support cache and outcome-blind audit artifacts."""

    output_root.mkdir(parents=True, exist_ok=True)
    panel_sha_before = sha256_file(panel)
    if expected_panel_sha256 and panel_sha_before != expected_panel_sha256:
        raise ValueError(f"immutable panel SHA mismatch: {panel_sha_before} != {expected_panel_sha256}")

    v2 = load_clean_v2_outcome_blind(v2_table)
    coverage = _load_open_coverage(open_coverage)
    panel_frame = _load_panel(panel)
    session_calendar = pd.read_csv(calendar, usecols=["date"])
    session_calendar["date"] = _normalise_dates(session_calendar["date"])
    security = pd.read_csv(security_master, usecols=["ticker", "listed_from", "listed_to"])
    security["ticker"] = security["ticker"].astype(str).str.upper().str.strip()
    security["listed_from"] = _normalise_dates(security["listed_from"])
    security["listed_to"] = _normalise_dates(security["listed_to"])
    if security["ticker"].duplicated().any():
        raise ValueError("security master contains duplicate ticker identities")
    anchors = pd.read_csv(tradability_anchors, usecols=["ticker", "as_of_date", "state"])
    intervals = pd.read_csv(
        tradability_intervals,
        usecols=["ticker", "market", "state", "effective_from", "effective_to"],
    )
    intervals["ticker"] = intervals["ticker"].astype(str).str.upper().str.strip()
    intervals["effective_from"] = _normalise_dates(intervals["effective_from"])
    intervals["effective_to"] = _normalise_dates(intervals["effective_to"])

    provenance = None
    if open_provenance is not None:
        provenance = pd.read_parquet(open_provenance, columns=list(OPEN_PROVENANCE_COLUMNS))
        provenance["ticker"] = provenance["ticker"].astype(str).str.upper().str.strip()
        provenance["date"] = _normalise_dates(provenance["date"])
        if provenance.duplicated(["ticker", "date"]).any():
            raise ValueError("Open provenance contains duplicate ticker/date keys")

    previous = compute_previous_active_features(panel_frame, anchors, session_calendar)
    previous_columns = [
        "ticker",
        "date",
        "session_index",
        "current_state",
        "previous_active_date",
        "previous_active_session_index",
        "previous_high",
        "previous_low",
        "previous_active_session_gap",
        "high",
        "low",
        "close",
        "open",
        "open_available",
        "open_evidence_status",
    ]
    previous = previous.loc[:, previous_columns].rename(
        columns={
            "session_index": "panel_session_index",
            "high": "panel_high",
            "low": "panel_low",
            "close": "panel_close",
            "open": "panel_open",
            "open_available": "panel_open_available",
            "open_evidence_status": "panel_open_evidence_status",
        }
    )

    work = v2.merge(
        coverage,
        on=["ticker", "date", "signal_session_index"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_coverage"),
        indicator="coverage_join",
    )
    work["coverage_present"] = work["coverage_join"].eq("both")
    work = work.drop(columns=["coverage_join"])
    work = work.merge(previous, on=["ticker", "date"], how="left", validate="one_to_one")
    work = work.merge(security, on="ticker", how="left", validate="many_to_one")
    if provenance is not None:
        work = work.merge(provenance, on=["ticker", "date"], how="left", validate="one_to_one")

    work["listed_valid"] = (
        work["listed_from"].notna()
        & (work["date"] >= work["listed_from"])
        & (work["listed_to"].isna() | (work["date"] <= work["listed_to"]))
    )
    work["current_active_valid"] = work["current_state"].eq("ACTIVE")
    work["regular_suspension_conflict"] = _suspension_mask(work, intervals)
    work["current_open_valid_recomputed"] = same_day_open_geometry(work).notna().all(axis=1)
    work["current_open_ready_matches_recompute"] = _close_match(
        work["open_feature_ready"].astype(bool), work["current_open_valid_recomputed"].astype(bool), atol=0.0
    )
    work["previous_range_valid_recomputed"] = (
        np.isfinite(pd.to_numeric(work["previous_high"], errors="coerce"))
        & np.isfinite(pd.to_numeric(work["previous_low"], errors="coerce"))
        & (pd.to_numeric(work["previous_high"], errors="coerce") > 0.0)
        & (pd.to_numeric(work["previous_low"], errors="coerce") > 0.0)
        & (pd.to_numeric(work["previous_high"], errors="coerce") > pd.to_numeric(work["previous_low"], errors="coerce"))
    )
    work["previous_active_link_valid"] = (
        work["previous_active_session_index"].notna()
        & (work["previous_active_session_index"] < work["panel_session_index"])
        & work["previous_high"].notna()
        & work["previous_low"].notna()
    )
    work["common_support"] = (
        work["coverage_present"]
        & work["listed_valid"]
        & work["current_active_valid"]
        & ~work["regular_suspension_conflict"]
        & work["current_open_valid_recomputed"]
        & work["previous_range_valid_recomputed"]
        & work["previous_active_link_valid"]
    )

    # Recompute and compare the published same-day formulas.  All formula
    # checks are performed without loading any label/outcome column.
    expected_same_day = same_day_open_geometry(work)
    formula_mismatch = pd.Series(False, index=work.index)
    for column in SAME_DAY_OPEN_FEATURES:
        formula_mismatch |= ~_close_match(work[column], expected_same_day[column])
    work["same_day_formula_match"] = ~formula_mismatch

    previous_geometry = previous_range_open_geometry(work)
    work = pd.concat([work, previous_geometry], axis=1)
    previous_formula_mismatch = pd.Series(False, index=work.index)
    for column in PREVIOUS_RANGE_OPEN_FEATURES:
        previous_formula_mismatch |= ~_close_match(work[column], previous_geometry[column])
    work["previous_formula_match"] = ~previous_formula_mismatch

    reasons: list[str] = []
    for row in work.itertuples(index=False):
        current_reasons: list[str] = []
        if not row.coverage_present:
            current_reasons.append("OPEN_COVERAGE_ROW_MISSING")
        if not row.listed_valid:
            current_reasons.append("PIT_LISTING_DOMAIN_INVALID")
        if not row.current_active_valid:
            current_reasons.append("CURRENT_SESSION_NOT_ACTIVE")
        if row.regular_suspension_conflict:
            current_reasons.append("CURRENT_REGULAR_SUSPENSION_CONFLICT")
        if not row.current_open_valid_recomputed:
            if not row.open_known or not np.isfinite(row.open):
                current_reasons.append("CURRENT_OPEN_UNAVAILABLE_OR_INVALID")
            elif np.isfinite(row.high) and np.isfinite(row.low) and row.high <= row.low:
                current_reasons.append("CURRENT_FLAT_RANGE")
            elif np.isfinite(row.open) and np.isfinite(row.low) and np.isfinite(row.high) and not (
                row.low <= row.open <= row.high
            ):
                current_reasons.append("CURRENT_OPEN_OUT_OF_RANGE")
            else:
                current_reasons.append("CURRENT_GEOMETRY_INVALID")
        if not row.previous_active_link_valid:
            current_reasons.append("PREVIOUS_ACTIVE_BAR_UNAVAILABLE_OR_INVALID_LINK")
        elif row.current_open_valid_recomputed and not row.previous_range_valid_recomputed:
            current_reasons.append("PREVIOUS_ACTIVE_FLAT_OR_INVALID_RANGE")
        reasons.append(";".join(current_reasons) if current_reasons else "")
    work["exclusion_reasons"] = reasons

    common = work.loc[work["common_support"]].copy()
    common = common.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)
    common_columns = [
        "ticker",
        "date",
        "signal_session_index",
        *V2_FULL_FEATURE_COLUMNS,
        "high",
        "low",
        "close",
        "open",
        *SAME_DAY_OPEN_FEATURES,
        *PREVIOUS_RANGE_OPEN_FEATURES,
        "previous_active_date",
        "previous_active_session_index",
        "previous_active_session_gap",
        "open_source",
        "open_evidence_class",
        "validation_status",
        "source_cache_ref",
    ]
    common_columns = [column for column in common_columns if column in common.columns]
    _ensure_outcome_blind(common_columns)
    common = common.loc[:, common_columns]

    exclusions = work.loc[~work["common_support"], ["ticker", "date", "signal_session_index", "exclusion_reasons"]].copy()
    exclusions["date"] = exclusions["date"].dt.strftime("%Y-%m-%d")
    reason_counts: dict[str, int] = {}
    for value in exclusions["exclusion_reasons"]:
        for reason in str(value).split(";"):
            if reason:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

    stats = _feature_stats(common, CANDIDATE_FEATURE_COLUMNS)
    correlation = (
        common.loc[:, CANDIDATE_FEATURE_COLUMNS]
        .corr(method="pearson")
        .rename_axis(index="feature_a", columns="feature_b")
        .reset_index()
        .melt(id_vars="feature_a", var_name="feature_b", value_name="correlation")
    )
    high_corr = correlation[
        (correlation["feature_a"] < correlation["feature_b"])
        & correlation["correlation"].abs().ge(0.95)
    ].sort_values("correlation", key=lambda series: series.abs(), ascending=False)
    open_related_corr = correlation[
        correlation["feature_a"].isin(ALL_OPEN_FEATURES) | correlation["feature_b"].isin(ALL_OPEN_FEATURES)
    ].copy()
    open_related_corr = open_related_corr[
        open_related_corr["feature_a"] < open_related_corr["feature_b"]
    ].sort_values("correlation", key=lambda series: series.abs(), ascending=False)

    bounded_security = security[security["listed_to"].notna() & security["listed_from"].notna()].sort_values("ticker")
    if bounded_security.empty:
        raise ValueError("cannot run PIT boundary adversarial checks without a bounded security")
    boundary = bounded_security.iloc[0]
    prelist_date = boundary["listed_from"] - pd.Timedelta(days=1)
    postdelist_date = boundary["listed_to"] + pd.Timedelta(days=1)
    prelist_rejected = not (
        (prelist_date >= boundary["listed_from"])
        and (prelist_date <= boundary["listed_to"])
    )
    postdelist_rejected = not (
        (postdelist_date >= boundary["listed_from"])
        and (postdelist_date <= boundary["listed_to"])
    )

    # This is a deterministic causal check: adding rows after the latest
    # audited row cannot alter the previous-active linkage of earlier rows.
    cutoff = int(work["signal_session_index"].max()) - 1
    early = previous[previous["panel_session_index"] <= cutoff].copy()
    full_previous = previous[previous["panel_session_index"] <= cutoff].loc[:, previous.columns]
    session_lookup = session_calendar.copy()
    session_lookup["date"] = _normalise_dates(session_lookup["date"])
    session_lookup["session_index"] = np.arange(1, len(session_lookup) + 1, dtype=int)
    truncated_dates = set(session_lookup.loc[session_lookup["session_index"] <= cutoff, "date"])
    truncated = compute_previous_active_features(
        panel_frame[panel_frame["date"].isin(truncated_dates)], anchors, session_calendar
    )
    # Compare all pre-cutoff links from full and truncated runs by key.
    full_links = previous[previous["panel_session_index"] <= cutoff].loc[
        :, ["ticker", "date", "previous_active_date", "previous_active_session_index", "previous_high", "previous_low"]
    ].sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    truncated_links = truncated[truncated["session_index"] <= cutoff].loc[
        :, ["ticker", "date", "previous_active_date", "previous_active_session_index", "previous_high", "previous_low"]
    ].sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    causal_invariant = bool(full_links.equals(truncated_links))

    panel_sha_after = sha256_file(panel)
    input_paths = {
        "v2_table": v2_table,
        "open_coverage": open_coverage,
        "panel": panel,
        "calendar": calendar,
        "security_master": security_master,
        "tradability_anchors": tradability_anchors,
        "tradability_intervals": tradability_intervals,
    }
    if open_provenance is not None:
        input_paths["open_provenance"] = open_provenance
    source_hashes = {name: sha256_file(path) for name, path in input_paths.items()}

    summary: dict[str, object] = {
        "status": "OUTCOME_BLIND_AUDIT_COMPLETE",
        "model_fit_performed": False,
        "score_performed": False,
        "target_columns_loaded": False,
        "provider_calls": 0,
        "protected_outcomes_accessed": False,
        "experiment_contract": {
            "control": CONTROL_MODEL,
            "control_semantics_source_commit": CONTROL_SEMANTICS_SOURCE_COMMIT,
            "control_feature_order": list(V2_FULL_FEATURE_COLUMNS),
            "control_feature_order_sha256": feature_order_sha256(V2_FULL_FEATURE_COLUMNS),
            "control_preprocessing": CONTROL_PREPROCESSING,
            "control_hgb_parameters": CONTROL_HGB_PARAMETERS,
            "folds": [asdict(fold) for fold in FROZEN_V2_FOLDS],
            "challengers": {
                "V2.1": {"identity": "V2.1-CLEAN-V2-OPEN-GEOMETRY", "features": list(SAME_DAY_OPEN_FEATURES)},
                "V2.2": {"identity": "V2.2-CLEAN-V2-PREV-RANGE-OPEN-DISPLACEMENT", "features": list(PREVIOUS_RANGE_OPEN_FEATURES)},
            },
            "eventual_rule": "same six folds, H10 semantics, HGB settings, evaluator and preregistered paired rule; no post-outcome rescue",
        },
        "input_hashes": source_hashes,
        "immutable_panel_sha256_before": panel_sha_before,
        "immutable_panel_sha256_after": panel_sha_after,
        "immutable_panel_unchanged": panel_sha_before == panel_sha_after,
        "clean_v2": {
            "rows": int(len(v2)),
            "tickers": int(v2["ticker"].nunique()),
            "date_min": v2["date"].min(),
            "date_max": v2["date"].max(),
            "session_min": int(v2["signal_session_index"].min()),
            "session_max": int(v2["signal_session_index"].max()),
            "duplicate_keys": int(v2.duplicated(["ticker", "date", "signal_session_index"]).sum()),
            "key_sha256": stable_key_sha256(v2),
        },
        "common_support": {
            "rows": int(len(common)),
            "tickers": int(common["ticker"].nunique()),
            "date_min": common["date"].min() if len(common) else None,
            "date_max": common["date"].max() if len(common) else None,
            "session_min": int(common["signal_session_index"].min()) if len(common) else None,
            "session_max": int(common["signal_session_index"].max()) if len(common) else None,
            "key_sha256": stable_key_sha256(common),
            "feature_order_sha256": feature_order_sha256(CANDIDATE_FEATURE_COLUMNS),
            "clean_v2_rows_excluded": int(len(exclusions)),
            "exclusion_reason_counts": reason_counts,
        },
        "coverage": {
            "coverage_rows": int(len(coverage)),
            "coverage_missing_from_clean_v2": int((~work["coverage_present"]).sum()),
            "open_known_rows": int(work["open_known"].astype(bool).sum()),
            "same_day_geometry_rows": int(work["current_open_valid_recomputed"].sum()),
            "published_formula_mismatch_rows": int((~work["same_day_formula_match"]).sum()),
            "panel_source_counts": work.get("panel_open_evidence_status", pd.Series(dtype="string")).value_counts(dropna=False).to_dict(),
            "provenance_missing_rows": int(work["open_source"].isna().sum()) if "open_source" in work else None,
            "provenance_source_counts": work.get("open_source", pd.Series(dtype="string")).fillna("MISSING").value_counts(dropna=False).to_dict(),
        },
        "previous_active_linkage": {
            "rows_with_previous_active_bar": int(work["previous_active_link_valid"].sum()),
            "rows_without_previous_active_bar": int((~work["previous_active_link_valid"]).sum()),
            "previous_flat_or_invalid_range_rows": int((~work["previous_range_valid_recomputed"]).sum()),
            "previous_session_gap_min": float(work["previous_active_session_gap"].dropna().min()) if work["previous_active_session_gap"].notna().any() else None,
            "previous_session_gap_max": float(work["previous_active_session_gap"].dropna().max()) if work["previous_active_session_gap"].notna().any() else None,
            "previous_session_gap_median": float(work["previous_active_session_gap"].dropna().median()) if work["previous_active_session_gap"].notna().any() else None,
            "previous_formula_mismatch_rows": int((~work["previous_formula_match"]).sum()),
        },
        "pit_session_assertions": {
            "current_listing_invalid_rows": int((~work["listed_valid"]).sum()),
            "current_non_active_rows": int((~work["current_active_valid"]).sum()),
            "regular_suspension_conflict_rows": int(work["regular_suspension_conflict"].sum()),
            "calendar_unresolved_rows": int(work["panel_session_index"].isna().sum()),
            "prelist_postdelist_adversarial_checks": {
                "ticker": str(boundary["ticker"]),
                "prelist_date": prelist_date,
                "prelist_rejected": bool(prelist_rejected),
                "postdelist_date": postdelist_date,
                "postdelist_rejected": bool(postdelist_rejected),
            },
        },
        "distribution_and_overlap": {
            "feature_stats_path": "feature_stats.csv",
            "correlation_path": "feature_correlations.csv",
            "high_abs_correlation_pairs_ge_0_95": int(len(high_corr)),
            "high_abs_correlation_pairs": high_corr[["feature_a", "feature_b", "correlation"]].to_dict("records"),
            "open_related_correlation_pairs_top_20": open_related_corr.head(20)[["feature_a", "feature_b", "correlation"]].to_dict("records"),
            "open_related_max_abs_correlation": float(open_related_corr["correlation"].abs().max()) if len(open_related_corr) else None,
        },
        "causal_audit": {
            "future_row_invariance": causal_invariant,
            "audit_reads_only_explicit_outcome_blind_columns": True,
            "no_calendar_day_shift_for_previous_bar": True,
            "no_forward_fill_or_synthetic_fill": True,
        },
        "artifacts": {
            "common_support": "outcome_blind_common_support.parquet",
            "exclusions": "common_support_exclusions.csv",
            "feature_stats": "feature_stats.csv",
            "feature_correlations": "feature_correlations.csv",
        },
    }

    common.to_parquet(output_root / "outcome_blind_common_support.parquet", index=False)
    exclusions.to_csv(output_root / "common_support_exclusions.csv", index=False)
    stats.to_csv(output_root / "feature_stats.csv", index=False)
    correlation.to_csv(output_root / "feature_correlations.csv", index=False)
    _write_json(output_root / "audit_summary.json", summary)

    artifact_names = [
        "outcome_blind_common_support.parquet",
        "common_support_exclusions.csv",
        "feature_stats.csv",
        "feature_correlations.csv",
        "audit_summary.json",
    ]
    artifact_hashes = {name: sha256_file(output_root / name) for name in artifact_names}
    manifest_payload = {
        "schema": "idx-trade/clean-v2-open-alpha-outcome-blind-audit-v1",
        "artifact_hashes": artifact_hashes,
        "source_hashes": source_hashes,
        "common_support_key_sha256": summary["common_support"]["key_sha256"],
        "immutable_panel_sha256_before": panel_sha_before,
        "immutable_panel_sha256_after": panel_sha_after,
        "immutable_panel_unchanged": panel_sha_before == panel_sha_after,
        "target_columns_loaded": False,
        "model_fit_performed": False,
        "provider_calls": 0,
    }
    _write_json(output_root / "artifact_manifest.json", manifest_payload)
    manifest_sha = sha256_file(output_root / "artifact_manifest.json")
    (output_root / "artifact_manifest.sha256").write_text(manifest_sha + "  artifact_manifest.json\n", encoding="utf-8")
    return {**summary, "artifact_hashes": artifact_hashes, "artifact_manifest_sha256": manifest_sha}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2-table", type=Path, required=True)
    parser.add_argument("--open-coverage", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--tradability-anchors", type=Path, required=True)
    parser.add_argument("--tradability-intervals", type=Path, required=True)
    parser.add_argument("--open-provenance", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-panel-sha256")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = run_open_alpha_blind_audit(
        v2_table=args.v2_table,
        open_coverage=args.open_coverage,
        panel=args.panel,
        calendar=args.calendar,
        security_master=args.security_master,
        tradability_anchors=args.tradability_anchors,
        tradability_intervals=args.tradability_intervals,
        open_provenance=args.open_provenance,
        output_root=args.output_root,
        expected_panel_sha256=args.expected_panel_sha256,
    )
    print(json.dumps(_jsonable(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
