from __future__ import annotations

import pandas as pd

from research.alpha_candidate_score_separation_v1 import (
    CANDIDATES,
    TOP_K,
    daily_separation,
    summarize,
)


def _fixture() -> pd.DataFrame:
    rows = []
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"])
    for date_index, date in enumerate(dates):
        for ticker_index in range(32):
            ticker = f"T{ticker_index:02d}"
            row = {
                "ticker": ticker,
                "date": date,
                "eligible_decision_universe": True,
            }
            for candidate_index, column in enumerate(CANDIDATES.values()):
                value = 100.0 - ticker_index + date_index * (candidate_index + 1) * 0.01
                if candidate_index == 0 and ticker_index == 30 and date_index == 0:
                    value = 1.0
                row[column] = value
                row[f"rank_{column}"] = float(32 - ticker_index)
            rows.append(row)
    return pd.DataFrame(rows)


def test_daily_separation_has_boundary_and_exact_tie_fields() -> None:
    frame = _fixture()
    sessions = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"])
    session_index = {date: index for index, date in enumerate(sessions)}
    metrics, selections = daily_separation(frame, "C1", TOP_K, session_index)
    assert len(metrics) == 3
    assert len(selections) == 3
    assert metrics["boundary_gap"].iloc[0] > 0
    assert metrics["normalized_boundary_gap"].iloc[0] > 0
    assert metrics["boundary_exact_tie"].eq(False).all()
    assert metrics["next_turnover"].iloc[0] == 0.0


def test_summarize_is_structural_only_and_has_year_summary() -> None:
    frame = _fixture()
    result = summarize(frame, pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]))
    assert result["status"] == "PASS_STRUCTURAL_SCORE_SEPARATION"
    assert result["admission"]["protected_boundary"] == "CLOSED"
    assert result["admission"]["candidate_status_changed"] is False
    assert result["candidates"]["C1"]["overall"]["usable_dates"] == 3
    assert result["candidates"]["C1"]["by_year"]["2025"]["usable_dates"] == 3
    assert "separation_vs_next_turnover" in result["candidates"]["C4"]["overall"]
