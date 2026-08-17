from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


PRIMARY_LIQUIDITY_LOOKBACK = 60
PRIMARY_MIN_ACTIVE_OBSERVATIONS = 20
PRIMARY_VALUE_THRESHOLD_IDR = 1_000_000_000.0

VALIDATION_FOLDS = 6
VALIDATION_FOLD_SIZE = 100
VALIDATION_REQUIRED_SESSIONS = VALIDATION_FOLDS * VALIDATION_FOLD_SIZE
PURGE_OFFICIAL_SESSIONS = 10

SESSION_GEOMETRY_FEATURE_COLUMNS = (
    "session_open_position_range",
    "session_body_signed_range",
    "session_log_high_low_range",
)


def normalize_sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .tz_localize(None)
        .normalize()
        .dropna()
        .unique()
        .sort_values()
    )
    if not len(sessions):
        raise ValueError("official_sessions must not be empty")
    return sessions


def normalized_percentile_rank(values: pd.Series) -> pd.Series:
    """Average-tie rank on finite values, normalized exactly to [0, 1]."""

    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    finite = numeric.where(np.isfinite(numeric))
    result = pd.Series(np.nan, index=values.index, dtype=float)
    valid = finite.dropna()
    n = len(valid)
    if n == 0:
        return result
    if n == 1:
        result.loc[valid.index] = 0.5
        return result
    ranks = valid.rank(method="average", ascending=True)
    result.loc[valid.index] = (ranks - 1.0) / float(n - 1)
    return result


def build_primary_liquid_state(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Materialize the frozen V4-3 primary-liquid state without future data."""

    required = {"ticker", "date", "regular_market_value"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"primary-liquid input missing columns: {sorted(missing)}")

    sessions = normalize_sessions(official_sessions)
    index_by_date = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    work = panel[["ticker", "date", "regular_market_value"]].copy()
    work["ticker"] = (
        work["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if work["date"].isna().any():
        raise ValueError("primary-liquid input contains invalid dates")
    work["session_index"] = work["date"].map(index_by_date)
    if work["session_index"].isna().any():
        raise ValueError("primary-liquid input contains dates outside official calendar")
    if work.duplicated(["ticker", "date"]).any():
        raise ValueError("primary-liquid input contains duplicate ticker/date rows")
    work["session_index"] = work["session_index"].astype(int)
    work["regular_market_value"] = pd.to_numeric(
        work["regular_market_value"], errors="coerce"
    ).astype(float)

    pieces: list[pd.DataFrame] = []
    for _, group in work.groupby("ticker", sort=True):
        frame = group.sort_values("session_index", kind="mergesort").copy()
        indices = frame["session_index"].to_numpy(dtype=int)
        values = frame["regular_market_value"].to_numpy(dtype=float)
        counts: list[int] = []
        medians: list[float] = []
        left = 0
        for right, current in enumerate(indices):
            minimum = int(current) - (PRIMARY_LIQUIDITY_LOOKBACK - 1)
            while left <= right and indices[left] < minimum:
                left += 1
            window = values[left : right + 1]
            finite = window[np.isfinite(window)]
            counts.append(int(len(finite)))
            medians.append(float(np.median(finite)) if len(finite) else np.nan)
        frame["liquidity_active_observations_60"] = counts
        frame["median_regular_value_60"] = medians
        frame["universe_history_qualified"] = (
            frame["liquidity_active_observations_60"] >= PRIMARY_MIN_ACTIVE_OBSERVATIONS
        ) & frame["median_regular_value_60"].notna()
        frame["universe_primary_liquid"] = frame["universe_history_qualified"] & (
            frame["median_regular_value_60"] >= PRIMARY_VALUE_THRESHOLD_IDR
        )
        pieces.append(frame)

    result = pd.concat(pieces, ignore_index=True, sort=False)
    return result.sort_values(["session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def build_session_geometry_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the frozen non-redundant EOD-t geometry challenger block."""

    required = {"ticker", "date", "open", "high", "low", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"session-geometry input missing columns: {sorted(missing)}")

    result = frame[["ticker", "date"]].copy()
    op = pd.to_numeric(frame["open"], errors="coerce").astype(float)
    hi = pd.to_numeric(frame["high"], errors="coerce").astype(float)
    lo = pd.to_numeric(frame["low"], errors="coerce").astype(float)
    cl = pd.to_numeric(frame["close"], errors="coerce").astype(float)

    finite_hlc = np.isfinite(hi) & np.isfinite(lo) & np.isfinite(cl)
    valid_hlc = finite_hlc & (hi > 0.0) & (lo > 0.0) & (cl > 0.0)
    valid_hlc &= hi >= lo
    valid_hlc &= hi >= cl
    valid_hlc &= lo <= cl

    finite_open = np.isfinite(op) & (op > 0.0)
    valid_open = valid_hlc & finite_open & (op >= lo) & (op <= hi)
    nonflat = valid_hlc & (hi > lo)
    width = hi - lo

    open_position = pd.Series(np.nan, index=frame.index, dtype=float)
    body = pd.Series(np.nan, index=frame.index, dtype=float)
    pos_mask = valid_open & nonflat
    open_position.loc[pos_mask] = ((op - lo) / width).loc[pos_mask]
    body.loc[pos_mask] = ((cl - op) / width).loc[pos_mask]

    log_range = pd.Series(np.nan, index=frame.index, dtype=float)
    range_mask = valid_hlc & (hi >= lo)
    log_range.loc[range_mask] = np.log((hi / lo).loc[range_mask])

    result["session_open_position_range"] = open_position.to_numpy()
    result["session_body_signed_range"] = body.to_numpy()
    result["session_log_high_low_range"] = log_range.to_numpy()
    return result


def equal_date_sample_weights(dates: pd.Series) -> pd.Series:
    """Equalize total learner weight per training date while keeping mean weight 1."""

    normalized = pd.to_datetime(dates, errors="coerce").dt.tz_localize(None).dt.normalize()
    if normalized.isna().any() or len(normalized) == 0:
        raise ValueError("training dates must be non-empty and valid")
    counts = normalized.value_counts(sort=False)
    n_rows = float(len(normalized))
    n_dates = float(len(counts))
    weights = normalized.map(lambda value: n_rows / (n_dates * float(counts.loc[value])))
    weights = pd.to_numeric(weights, errors="raise").astype(float)
    if not np.isfinite(weights).all() or (weights <= 0).any():
        raise RuntimeError("date weights must be finite and positive")
    return weights


@dataclass(frozen=True)
class FoldPosition:
    fold: int
    eligible_start_position: int
    eligible_end_position: int


def validation_fold_positions(eligible_count: int) -> tuple[FoldPosition, ...]:
    """Select the frozen tail-600 sequence and split it into six 100-date folds."""

    if eligible_count < VALIDATION_REQUIRED_SESSIONS:
        raise ValueError(
            f"need >= {VALIDATION_REQUIRED_SESSIONS} eligible sessions, got {eligible_count}"
        )
    first = int(eligible_count) - VALIDATION_REQUIRED_SESSIONS
    folds = []
    for offset in range(VALIDATION_FOLDS):
        start = first + offset * VALIDATION_FOLD_SIZE
        folds.append(
            FoldPosition(
                fold=offset + 1,
                eligible_start_position=start,
                eligible_end_position=start + VALIDATION_FOLD_SIZE - 1,
            )
        )
    return tuple(folds)


def purge_max_training_session_index(validation_start_official_index: int) -> int:
    return int(validation_start_official_index) - PURGE_OFFICIAL_SESSIONS - 1


def materialize_validation_folds(eligible_sessions: pd.DataFrame) -> pd.DataFrame:
    required = {"session_index", "date"}
    missing = required - set(eligible_sessions.columns)
    if missing:
        raise ValueError(f"eligible-session input missing columns: {sorted(missing)}")
    work = eligible_sessions.loc[:, ["session_index", "date"]].copy().reset_index(drop=True)
    work["session_index"] = pd.to_numeric(work["session_index"], errors="raise").astype(int)
    work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if work["date"].isna().any():
        raise ValueError("eligible-session input contains invalid date")
    if work["session_index"].duplicated().any() or work["date"].duplicated().any():
        raise ValueError("eligible-session identities must be unique")
    if len(work) > 1 and np.any(np.diff(work["session_index"].to_numpy(dtype=int)) <= 0):
        raise ValueError("eligible-session identities must be strictly chronological")

    rows: list[dict[str, object]] = []
    for spec in validation_fold_positions(len(work)):
        block = work.iloc[spec.eligible_start_position : spec.eligible_end_position + 1]
        start_official = int(block["session_index"].iloc[0])
        max_train = purge_max_training_session_index(start_official)
        for within_fold, (_, row) in enumerate(block.iterrows(), start=1):
            rows.append(
                {
                    "fold": spec.fold,
                    "validation_position": within_fold,
                    "eligible_sequence_position_zero_based": (
                        spec.eligible_start_position + within_fold - 1
                    ),
                    "session_index": int(row["session_index"]),
                    "date": pd.Timestamp(row["date"]),
                    "purge_length_official_sessions": PURGE_OFFICIAL_SESSIONS,
                    "max_training_signal_session_index": max_train,
                }
            )
    result = pd.DataFrame(rows)
    if len(result) != VALIDATION_REQUIRED_SESSIONS:
        raise RuntimeError("fold materialization did not produce exactly 600 rows")
    return result
