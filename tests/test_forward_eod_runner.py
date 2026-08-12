from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from idx_trade import forward_eod_runner as runner


def test_runner_is_fail_closed_before_eod_cutoff(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "_now_jakarta",
        lambda: datetime(2026, 8, 12, 17, 59, tzinfo=ZoneInfo("Asia/Jakarta")),
    )

    result = runner.run_eod_catchup(tmp_path)

    assert result["status"] == "BEFORE_EOD_CUTOFF"
    assert result["capture_hour_jakarta"] == 18
    assert result["captured_sessions"] == []
    assert (tmp_path / "forward_monitoring" / "eod_automation" / "latest.json").exists()


def test_runner_catches_up_after_missed_schedule_and_records_date_validation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "_now_jakarta",
        lambda: datetime(2026, 8, 12, 19, 2, tzinfo=ZoneInfo("Asia/Jakarta")),
    )
    monkeypatch.setattr(runner.base, "_closed_through_date", lambda: pd.Timestamp("2026-08-12"))
    monkeypatch.setattr(
        runner.runtime,
        "sync_forward_calendar",
        lambda paths, through=None: pd.DatetimeIndex(["2026-08-11", "2026-08-12"]),
    )
    monkeypatch.setattr(
        runner.runtime,
        "_load_forward_calendar",
        lambda paths: pd.DatetimeIndex(["2026-08-11", "2026-08-12"]),
    )
    missing = iter([pd.Timestamp("2026-08-11"), None])
    monkeypatch.setattr(runner.base, "_earliest_missing", lambda paths, sessions: next(missing))
    monkeypatch.setattr(
        runner.runtime,
        "capture_session",
        lambda *args, **kwargs: {"status": "DATA_READY", "session_date": "2026-08-11"},
    )
    result = runner.run_eod_catchup(tmp_path)

    assert result["status"] == "NO_MISSING_SESSION"
    assert result["closed_through_session"] == "2026-08-12"
    assert result["official_calendar_validation"] == "PASS_EXACT_IDX_SESSION_CALENDAR"
    assert result["captured_sessions"][0]["session_date_validation"] == "PASS_CALENDAR_AND_EXACT_SOURCE_DATE"


def test_runner_stops_on_first_capture_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "_now_jakarta",
        lambda: datetime(2026, 8, 12, 18, 5, tzinfo=ZoneInfo("Asia/Jakarta")),
    )
    monkeypatch.setattr(
        runner.runtime,
        "sync_forward_calendar",
        lambda paths, through=None: pd.DatetimeIndex(["2026-08-11"]),
    )
    monkeypatch.setattr(
        runner.runtime,
        "_load_forward_calendar",
        lambda paths: pd.DatetimeIndex(["2026-08-11"]),
    )
    monkeypatch.setattr(
        runner.base,
        "_earliest_missing",
        lambda paths, sessions: pd.Timestamp("2026-08-11"),
    )

    def fail_capture(*args, **kwargs):
        raise RuntimeError("synthetic capture failure")

    monkeypatch.setattr(runner.runtime, "capture_session", fail_capture)

    try:
        runner.run_eod_catchup(tmp_path)
    except RuntimeError as error:
        assert str(error) == "synthetic capture failure"
    else:
        raise AssertionError("runner should propagate the first capture failure")

    latest = (tmp_path / "forward_monitoring" / "eod_automation" / "latest.json").read_text()
    assert "DATA_FAILED" in latest
    assert "stopped_on_first_failure" in latest
