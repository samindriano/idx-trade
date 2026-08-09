import pandas as pd
import pytest

from idx_trade.research_validation import (
    FROZEN_FOLDS,
    assert_fold_contract,
    assert_label_path_precedes_validation,
    assert_no_holdout_access,
    chronological_fit_calibration_split,
    normalize_calendar,
)


def _segment(start, end, count):
    return pd.DatetimeIndex(pd.date_range(start, end, periods=count)).normalize()


def _frozen_calendar():
    anchors = [
        (1, "2021-04-29"),
        (504, "2023-05-23"),
        (525, "2023-06-23"),
        (650, "2023-12-27"),
        (671, "2024-01-26"),
        (796, "2024-08-15"),
        (817, "2024-09-13"),
        (942, "2025-03-20"),
        (1008, "2025-07-14"),
        (1009, "2025-07-15"),
        (1260, "2026-07-31"),
    ]
    values = []
    for i, ((idx0, date0), (idx1, date1)) in enumerate(zip(anchors[:-1], anchors[1:])):
        count = idx1 - idx0 + 1
        segment = list(_segment(date0, date1, count))
        if i:
            segment = segment[1:]
        values.extend(segment)
    assert len(values) == 1260
    return pd.DatetimeIndex(values)


def test_frozen_calendar_and_fold_contract_accept_expected_boundaries():
    calendar = _frozen_calendar()
    normalized = normalize_calendar(calendar)
    assert len(normalized) == 1260
    assert_fold_contract(normalized)
    assert [fold.name for fold in FROZEN_FOLDS] == ["F1", "F2", "F3"]


def test_internal_calibration_split_has_twenty_session_maturity_gap():
    dates = pd.bdate_range("2024-01-02", periods=100)
    split = chronological_fit_calibration_split(dates, fit_fraction=0.8, h_max=20)
    assert len(split["gap"]) == 20
    assert split["model_fit"].max() < split["gap"].min()
    assert split["gap"].max() < split["calibration"].min()


def test_holdout_rows_are_hard_rejected():
    calendar = _frozen_calendar()
    frame = pd.DataFrame({"date": [calendar[1008]]})
    with pytest.raises(RuntimeError, match="locked holdout access rejected"):
        assert_no_holdout_access(frame, calendar)


def test_overlap_guard_rejects_training_label_that_reaches_validation():
    with pytest.raises(RuntimeError, match="overlap validation"):
        assert_label_path_precedes_validation([500, 505], validation_start_index=525, horizon=20)
