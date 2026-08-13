from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

import pandas as pd


EXPECTED_SESSION_COUNT = 1260
DEVELOPMENT_END_INDEX = 1008
HOLDOUT_START_INDEX = 1009
H_MAX = 20

EXPECTED_BOUNDARIES = {
    1: "2021-04-29",
    504: "2023-05-23",
    525: "2023-06-23",
    650: "2023-12-27",
    671: "2024-01-26",
    796: "2024-08-15",
    817: "2024-09-13",
    942: "2025-03-20",
    1008: "2025-07-14",
    1009: "2025-07-15",
    1260: "2026-07-31",
}


@dataclass(frozen=True)
class DevelopmentFold:
    name: str
    train_start: int
    train_end: int
    gap_start: int
    gap_end: int
    validation_start: int
    validation_end: int


FROZEN_FOLDS = (
    DevelopmentFold("F1", 1, 504, 505, 524, 525, 650),
    DevelopmentFold("F2", 1, 650, 651, 670, 671, 796),
    DevelopmentFold("F3", 1, 796, 797, 816, 817, 942),
)


def normalize_calendar(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .tz_localize(None)
        .normalize()
        .dropna()
        .unique()
        .sort_values()
    )
    if len(sessions) != EXPECTED_SESSION_COUNT:
        raise ValueError(f"expected exactly {EXPECTED_SESSION_COUNT} official sessions, got {len(sessions)}")
    for one_based, expected in EXPECTED_BOUNDARIES.items():
        actual = pd.Timestamp(sessions[one_based - 1]).date().isoformat()
        if actual != expected:
            raise ValueError(
                f"frozen calendar boundary mismatch at session {one_based}: expected {expected}, got {actual}"
            )
    return sessions


def split_membership(calendar: Iterable[object]) -> pd.DataFrame:
    sessions = normalize_calendar(calendar)
    frame = pd.DataFrame(
        {
            "session_index": range(1, len(sessions) + 1),
            "date": sessions,
            "region": "UNASSIGNED",
        }
    )
    frame.loc[frame["session_index"].between(1, DEVELOPMENT_END_INDEX), "region"] = "DEVELOPMENT"
    frame.loc[frame["session_index"].between(HOLDOUT_START_INDEX, EXPECTED_SESSION_COUNT), "region"] = "LOCKED_HOLDOUT"
    for fold in FROZEN_FOLDS:
        frame[f"{fold.name}_role"] = "OUTSIDE"
        frame.loc[frame["session_index"].between(fold.train_start, fold.train_end), f"{fold.name}_role"] = "TRAIN"
        frame.loc[frame["session_index"].between(fold.gap_start, fold.gap_end), f"{fold.name}_role"] = "GAP"
        frame.loc[
            frame["session_index"].between(fold.validation_start, fold.validation_end),
            f"{fold.name}_role",
        ] = "VALIDATION"
    return frame


def fold_dates(calendar: Iterable[object], fold: DevelopmentFold) -> dict[str, pd.DatetimeIndex]:
    sessions = normalize_calendar(calendar)
    return {
        "train": sessions[fold.train_start - 1 : fold.train_end],
        "gap": sessions[fold.gap_start - 1 : fold.gap_end],
        "validation": sessions[fold.validation_start - 1 : fold.validation_end],
    }


def assert_fold_contract(calendar: Iterable[object], *, h_max: int = H_MAX) -> None:
    sessions = normalize_calendar(calendar)
    for fold in FROZEN_FOLDS:
        if fold.gap_end - fold.gap_start + 1 != h_max:
            raise AssertionError(f"{fold.name} gap is not exactly H_max={h_max}")
        if fold.train_end + 1 != fold.gap_start:
            raise AssertionError(f"{fold.name} train/gap boundary is not contiguous")
        if fold.gap_end + 1 != fold.validation_start:
            raise AssertionError(f"{fold.name} gap/validation boundary is not contiguous")
        last_training_path_end = fold.train_end + h_max
        if last_training_path_end >= fold.validation_start:
            raise AssertionError(f"{fold.name} training label path can overlap validation")
        _ = sessions[fold.validation_start - 1]


def chronological_fit_calibration_split(
    train_dates: Iterable[object],
    *,
    fit_fraction: float = 0.80,
    h_max: int = H_MAX,
) -> dict[str, pd.DatetimeIndex]:
    """Split fold-training dates into model-fit, maturity gap, calibration tail.

    The nominal 80/20 cut defines the start of calibration. The final H_max
    dates before calibration are removed from model fitting so a fit-row label
    path cannot overlap calibration dates.
    """

    dates = (
        pd.DatetimeIndex(pd.to_datetime(list(train_dates), errors="coerce"))
        .tz_localize(None)
        .normalize()
        .dropna()
        .unique()
        .sort_values()
    )
    if not 0.5 <= fit_fraction < 1.0:
        raise ValueError("fit_fraction must be in [0.5, 1.0)")
    if len(dates) <= (h_max + 10):
        raise ValueError("not enough dates for chronological fit/calibration split")
    calibration_start_pos = int(len(dates) * fit_fraction)
    calibration_start_pos = min(max(calibration_start_pos, h_max + 1), len(dates) - 1)
    fit_end_pos = calibration_start_pos - h_max
    model_fit = dates[:fit_end_pos]
    maturity_gap = dates[fit_end_pos:calibration_start_pos]
    calibration = dates[calibration_start_pos:]
    if not len(model_fit) or not len(calibration):
        raise ValueError("fit/calibration split produced an empty partition")
    if len(maturity_gap) != h_max:
        raise AssertionError("internal maturity gap is not H_max sessions")
    return {"model_fit": model_fit, "gap": maturity_gap, "calibration": calibration}


def assert_no_holdout_access(
    frame: pd.DataFrame,
    calendar: Iterable[object],
    *,
    date_column: str = "date",
) -> None:
    if date_column not in frame.columns:
        raise ValueError(f"missing date column: {date_column}")
    sessions = normalize_calendar(calendar)
    holdout_start = pd.Timestamp(sessions[HOLDOUT_START_INDEX - 1])
    dates = pd.to_datetime(frame[date_column], errors="coerce").dt.tz_localize(None).dt.normalize()
    if dates.isna().any():
        raise ValueError("frame contains invalid dates")
    forbidden = dates >= holdout_start
    if forbidden.any():
        first = pd.Timestamp(dates[forbidden].min()).date().isoformat()
        raise RuntimeError(f"locked holdout access rejected; first forbidden date={first}")


def assert_label_path_precedes_validation(
    signal_indices: Iterable[int],
    *,
    validation_start_index: int,
    horizon: int,
) -> None:
    indices = [int(value) for value in signal_indices]
    offenders = [idx for idx in indices if idx + horizon >= validation_start_index]
    if offenders:
        raise RuntimeError(
            f"training label paths overlap validation start {validation_start_index}; offenders={offenders[:5]}"
        )
