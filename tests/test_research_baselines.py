import numpy as np
import pandas as pd
import pytest

from idx_trade.research_baselines import run_development_fold
from idx_trade.research_features import BASELINE_FEATURE_COLUMNS


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
        segment = list(_segment(date0, date1, idx1 - idx0 + 1))
        if i:
            segment = segment[1:]
        values.extend(segment)
    return pd.DatetimeIndex(values)


def _model_table(calendar):
    dates = calendar[:942]
    frames = []
    for ticker_offset, ticker in enumerate(("AAA", "BBB")):
        n = len(dates)
        x = np.arange(n, dtype=float) + ticker_offset
        frame = pd.DataFrame(
            {
                "ticker": ticker,
                "date": dates,
                "binary_target": ((np.arange(n) + ticker_offset) % 3 == 0).astype(int),
                "universe_primary_liquid": True,
            }
        )
        for j, column in enumerate(BASELINE_FEATURE_COLUMNS):
            if column == "security_age_left_censored":
                frame[column] = bool(ticker_offset)
            elif column == "observed_session_count":
                frame[column] = np.arange(1, n + 1, dtype=float)
            elif column == "security_age_sessions_observed":
                frame[column] = np.arange(1, n + 1, dtype=float)
            else:
                frame[column] = np.sin((x + j) / 17.0) + (frame["binary_target"] * 0.05)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def test_runner_produces_all_frozen_baselines_without_holdout():
    calendar = _frozen_calendar()
    table = _model_table(calendar)
    results = run_development_fold(table, calendar, fold_name="F1", include_tree=True)
    assert [result.model_name for result in results] == [
        "base_rate",
        "momentum_20",
        "logistic_compact",
        "hist_gradient_boosting",
    ]
    for result in results:
        assert result.fold == "F1"
        assert 0.0 <= result.metrics["pr_auc"] <= 1.0
        assert 0.0 <= result.metrics["brier"] <= 1.0
        assert result.predictions["date"].max() < calendar[1008]


def test_runner_rejects_a_table_that_contains_any_locked_holdout_row():
    calendar = _frozen_calendar()
    table = _model_table(calendar)
    extra = table.iloc[[0]].copy()
    extra["date"] = calendar[1008]
    table = pd.concat([table, extra], ignore_index=True)
    with pytest.raises(RuntimeError, match="locked-holdout rows"):
        run_development_fold(table, calendar, fold_name="F1")
