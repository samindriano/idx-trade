from pathlib import Path

import pandas as pd
import pytest

from idx_trade.history_preflight import (
    plan_history_expansion,
    stock_summary_cache_coverage,
    trailing_session_window,
    write_history_expansion_preflight,
)


def test_trailing_session_window_requires_sufficient_official_history():
    sessions = pd.date_range("2026-01-01", periods=5, freq="D")
    assert trailing_session_window(sessions, 3).tolist() == sessions[-3:].tolist()
    with pytest.raises(ValueError, match="Insufficient official calendar history"):
        trailing_session_window(sessions, 6)


def test_expansion_plan_uses_exact_backward_delta_and_suffix_baseline(tmp_path):
    sessions = pd.date_range("2024-01-01", periods=10, freq="D")
    baseline = sessions[-4:]

    plan = plan_history_expansion(
        sessions,
        target_horizon=10,
        certified_baseline_sessions=baseline,
    )

    assert plan["target_sessions"] == 10
    assert plan["baseline_sessions"] == 4
    assert plan["additional_sessions"] == 6
    assert plan["additional_session_dates"] == [
        value.date().isoformat() for value in sessions[:6]
    ]
    assert plan["network_fetch_sessions_if_cache_reused"] == 10

    write_history_expansion_preflight(plan, tmp_path)
    assert (tmp_path / "history_expansion_preflight.json").exists()
    additional = pd.read_csv(tmp_path / "history_expansion_additional_sessions.csv")
    assert additional["date"].tolist() == plan["additional_session_dates"]


def test_expansion_plan_rejects_baseline_from_different_calendar_tail():
    sessions = pd.date_range("2024-01-01", periods=10, freq="D")
    wrong_baseline = sessions[-5:-1]

    with pytest.raises(ValueError, match="exact trailing suffix"):
        plan_history_expansion(
            sessions,
            target_horizon=10,
            certified_baseline_sessions=wrong_baseline,
        )


def test_stock_summary_cache_requires_parquet_and_metadata_pair(tmp_path: Path):
    sessions = pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-06"])

    (tmp_path / "2026-01-02.parquet").touch()
    (tmp_path / "2026-01-02.meta.json").write_text("{}", encoding="utf-8")
    (tmp_path / "2026-01-05.parquet").touch()

    audit = stock_summary_cache_coverage(tmp_path, sessions)

    assert audit["requested_sessions"] == 3
    assert audit["cached_sessions"] == 1
    assert audit["missing_sessions"] == 2
    assert audit["partial_cache_sessions"] == 1
    assert audit["cached_session_dates"] == ["2026-01-02"]
    assert audit["partial_cache_session_dates"] == ["2026-01-05"]
    assert audit["missing_session_dates"] == ["2026-01-05", "2026-01-06"]


def test_1260_plan_from_certified_504_requires_exactly_756_older_sessions():
    sessions = pd.date_range("2021-01-01", periods=1260, freq="D")
    baseline_504 = sessions[-504:]

    plan = plan_history_expansion(
        sessions,
        target_horizon=1260,
        certified_baseline_sessions=baseline_504,
    )

    assert plan["target_horizon"] == 1260
    assert plan["baseline_sessions"] == 504
    assert plan["additional_sessions"] == 756
    assert plan["baseline_window_end"] == plan["target_window_end"]
