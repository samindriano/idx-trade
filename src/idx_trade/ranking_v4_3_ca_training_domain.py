"""Outcome-blind V4-3 Corporate Action training-domain semantics.

This module closes a pre-target admission gap: the accepted V4-3 CA replay
certified the frozen 600 validation dates, while the preregistered walk-forward
models train on earlier target-eligible dates as well.  The helpers here never
compute a return, target rank, prediction, model fit, or performance metric.
They only materialize exact official-session target windows, combine previously
admitted price-observability booleans with CA continuity booleans, and freeze
the date identities that are legally available to each training fold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


GATE_RATE = 0.90
HORIZONS = (5, 10)
RESOLVED = "RESOLVED_NO_MECHANICAL_DISCONTINUITY"


@dataclass(frozen=True)
class TrainingDomainDiagnostics:
    decision_rows: int
    decision_dates: int
    decision_tickers: int
    window_rows: int
    coverage_missing_tickers: int
    coverage_missing_rows: int


def _dates(values: Iterable[object]) -> pd.DatetimeIndex:
    result = (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .tz_localize(None)
        .normalize()
        .dropna()
        .unique()
        .sort_values()
    )
    if not len(result):
        raise ValueError("official sessions must not be empty")
    return result


def normalize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", "session_index"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"decision frame missing columns: {sorted(missing)}")
    out = frame.copy()
    out["ticker"] = (
        out["ticker"]
        .astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )
    out["date"] = (
        pd.to_datetime(out["date"], errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    out["session_index"] = pd.to_numeric(
        out["session_index"], errors="raise"
    ).astype(int)
    if out["ticker"].eq("").any() or out["date"].isna().any():
        raise ValueError("decision frame contains invalid identity")
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError("decision frame contains duplicate ticker/date")
    return out


def build_window_skeleton(
    decision_rows: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    max_signal_session_index: int,
) -> pd.DataFrame:
    """Build exact t+1/t+5/t+10 windows without reading price outcomes."""

    sessions = _dates(official_sessions)
    decision = normalize_identity(decision_rows)
    decision = decision[
        decision["session_index"].le(int(max_signal_session_index))
    ].copy()
    if decision.empty:
        raise ValueError("training-domain decision frame is empty")

    rows: list[dict[str, object]] = []
    for row in decision.itertuples(index=False):
        signal_index = int(row.session_index)
        entry_index = signal_index + 1
        if entry_index >= len(sessions):
            raise RuntimeError("training-domain entry index outside official calendar")
        for horizon in HORIZONS:
            terminal_index = signal_index + horizon
            if terminal_index >= len(sessions):
                raise RuntimeError(
                    "training-domain terminal index outside official calendar"
                )
            rows.append(
                {
                    "ticker": str(row.ticker),
                    "signal_date": pd.Timestamp(row.date),
                    "signal_session_index": signal_index,
                    "horizon": int(horizon),
                    "entry_date": pd.Timestamp(sessions[entry_index]),
                    "terminal_date": pd.Timestamp(sessions[terminal_index]),
                }
            )
    result = pd.DataFrame(rows).sort_values(
        ["signal_session_index", "ticker", "horizon"], kind="mergesort"
    ).reset_index(drop=True)
    if result.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise RuntimeError("training-domain window identity duplicated")
    return result


def attach_continuity(
    windows: pd.DataFrame,
    continuity: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "ticker",
        "signal_date",
        "horizon",
        "continuity_status",
        "continuity_reason",
    }
    missing = required - set(continuity.columns)
    if missing:
        raise ValueError(f"continuity frame missing columns: {sorted(missing)}")
    right = continuity.copy()
    right["ticker"] = (
        right["ticker"]
        .astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )
    right["signal_date"] = (
        pd.to_datetime(right["signal_date"], errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    right["horizon"] = pd.to_numeric(right["horizon"], errors="raise").astype(int)
    if right.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise ValueError("continuity frame contains duplicate identity")

    merged = windows.merge(
        right[
            [
                "ticker",
                "signal_date",
                "horizon",
                "continuity_status",
                "continuity_reason",
            ]
        ],
        on=["ticker", "signal_date", "horizon"],
        how="left",
        validate="one_to_one",
    )
    # Missing continuity is always unresolved.  This is particularly important
    # for historical-only tickers that were absent from the frozen 611-ticker
    # validation census.
    merged["continuity_status"] = merged["continuity_status"].fillna(
        "PRICE_CONTINUITY_UNRESOLVED_COVERAGE"
    )
    merged["continuity_reason"] = merged["continuity_reason"].fillna(
        "NO_CA_COVERAGE_FOR_TRAINING_DOMAIN_IDENTITY"
    )
    merged["ca_resolved"] = merged["continuity_status"].eq(RESOLVED)
    return merged


def combine_target_support(
    decision_support: pd.DataFrame,
    continuity_windows: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Combine binary market/price support with CA continuity, still no target."""

    required = {
        "ticker",
        "date",
        "session_index",
        "entry_open_support",
        "h5_close_support",
        "h10_close_support",
    }
    missing = required - set(decision_support.columns)
    if missing:
        raise ValueError(f"decision support missing columns: {sorted(missing)}")
    decision = normalize_identity(decision_support)
    for column in (
        "entry_open_support",
        "h5_close_support",
        "h10_close_support",
    ):
        decision[column] = decision[column].fillna(False).astype(bool)

    ca = continuity_windows[
        ["ticker", "signal_date", "horizon", "ca_resolved"]
    ].copy()
    ca["signal_date"] = pd.to_datetime(ca["signal_date"]).dt.normalize()
    wide = ca.pivot(
        index=["ticker", "signal_date"],
        columns="horizon",
        values="ca_resolved",
    ).reset_index()
    if 5 not in wide.columns or 10 not in wide.columns:
        raise RuntimeError("CA continuity does not contain both horizons")
    wide = wide.rename(
        columns={"signal_date": "date", 5: "ca_h5_resolved", 10: "ca_h10_resolved"}
    )
    merged = decision.merge(
        wide,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    merged["ca_h5_resolved"] = merged["ca_h5_resolved"].fillna(False).astype(bool)
    merged["ca_h10_resolved"] = merged["ca_h10_resolved"].fillna(False).astype(bool)
    merged["h5_full_target_support"] = (
        merged["entry_open_support"]
        & merged["h5_close_support"]
        & merged["ca_h5_resolved"]
    )
    merged["h10_full_target_support"] = (
        merged["entry_open_support"]
        & merged["h10_close_support"]
        & merged["ca_h10_resolved"]
    )
    merged["consensus_full_target_support"] = (
        merged["h5_full_target_support"] & merged["h10_full_target_support"]
    )

    per_date = (
        merged.groupby(["session_index", "date"], sort=True)
        .agg(
            decision_rows=("ticker", "size"),
            h5_supported_rows=("h5_full_target_support", "sum"),
            h10_supported_rows=("h10_full_target_support", "sum"),
            consensus_supported_rows=("consensus_full_target_support", "sum"),
        )
        .reset_index()
    )
    for prefix in ("h5", "h10", "consensus"):
        per_date[f"{prefix}_rate"] = np.where(
            per_date["decision_rows"].gt(0),
            per_date[f"{prefix}_supported_rows"] / per_date["decision_rows"],
            np.nan,
        )
        per_date[f"{prefix}_eligible"] = (
            per_date["decision_rows"].gt(0)
            & per_date[f"{prefix}_rate"].ge(GATE_RATE)
        )
    return merged, per_date


def build_training_date_sets(
    per_date: pd.DataFrame,
    validation_folds: pd.DataFrame,
) -> pd.DataFrame:
    """Freeze all prior head-eligible dates before each fold purge boundary."""

    required_folds = {"fold", "max_training_signal_session_index"}
    missing = required_folds - set(validation_folds.columns)
    if missing:
        raise ValueError(f"validation folds missing columns: {sorted(missing)}")
    folds = validation_folds.copy()
    folds["fold"] = pd.to_numeric(folds["fold"], errors="raise").astype(int)
    folds["max_training_signal_session_index"] = pd.to_numeric(
        folds["max_training_signal_session_index"], errors="raise"
    ).astype(int)
    boundaries = (
        folds.groupby("fold", sort=True)["max_training_signal_session_index"]
        .agg(lambda values: tuple(sorted(set(int(v) for v in values))))
    )
    bad = boundaries[boundaries.map(len).ne(1)]
    if len(bad):
        raise ValueError("fold has non-unique purge boundary")

    rows: list[dict[str, object]] = []
    for fold, values in boundaries.items():
        maximum = int(values[0])
        for head in ("H5", "H10"):
            eligible_col = f"{head.lower()}_eligible"
            eligible = per_date[
                per_date["session_index"].le(maximum)
                & per_date[eligible_col].astype(bool)
            ]
            for row in eligible.itertuples(index=False):
                rows.append(
                    {
                        "fold": int(fold),
                        "head": head,
                        "session_index": int(row.session_index),
                        "date": pd.Timestamp(row.date),
                        "max_training_signal_session_index": maximum,
                    }
                )
    result = pd.DataFrame(rows)
    if result.empty:
        raise RuntimeError("no CA-admitted training dates")
    if result.duplicated(["fold", "head", "session_index"]).any():
        raise RuntimeError("training date identity duplicated")
    return result.sort_values(
        ["fold", "head", "session_index"], kind="mergesort"
    ).reset_index(drop=True)


def validate_frozen_tail(
    per_date: pd.DataFrame,
    validation_folds: pd.DataFrame,
) -> dict[str, object]:
    frozen = validation_folds[["session_index", "date"]].copy()
    frozen["session_index"] = pd.to_numeric(
        frozen["session_index"], errors="raise"
    ).astype(int)
    frozen["date"] = pd.to_datetime(frozen["date"], errors="coerce").dt.normalize()
    if len(frozen) != 600 or frozen["date"].isna().any():
        raise ValueError("frozen validation identity must contain exactly 600 dates")
    frozen = frozen.sort_values("session_index", kind="mergesort").reset_index(drop=True)

    merged = frozen.merge(
        per_date[
            [
                "session_index",
                "date",
                "h5_rate",
                "h10_rate",
                "consensus_rate",
                "h5_eligible",
                "h10_eligible",
                "consensus_eligible",
            ]
        ],
        on=["session_index", "date"],
        how="left",
        validate="one_to_one",
    )
    all_frozen = bool(
        merged[["h5_eligible", "h10_eligible", "consensus_eligible"]]
        .fillna(False)
        .all(axis=None)
    )
    eligible = per_date[per_date["consensus_eligible"].astype(bool)][
        ["session_index", "date"]
    ].sort_values("session_index", kind="mergesort").reset_index(drop=True)
    tail = eligible.tail(600).reset_index(drop=True) if len(eligible) >= 600 else eligible
    expected = frozen[["session_index", "date"]]
    tail_same = bool(len(tail) == 600 and tail.equals(expected))
    after_end = int((eligible["session_index"] > int(frozen["session_index"].max())).sum())
    return {
        "all_frozen_600_full_target_eligible": all_frozen,
        "tail_600_identity_unchanged": tail_same,
        "eligible_sessions_after_frozen_end": after_end,
        "frozen_h5_min_rate": float(merged["h5_rate"].min()),
        "frozen_h10_min_rate": float(merged["h10_rate"].min()),
        "frozen_consensus_min_rate": float(merged["consensus_rate"].min()),
    }
