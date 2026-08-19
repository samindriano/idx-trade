from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from idx_trade import forward_eod_runner as runner


JAKARTA = ZoneInfo("Asia/Jakarta")


def _no_legacy_rows(monkeypatch) -> None:
    monkeypatch.setattr(runner.base, "_session_states", lambda paths: {})


def test_runner_before_eod_can_catch_prior_session_but_not_today(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_now_jakarta",
        lambda: datetime(2026, 8, 12, 9, 0, tzinfo=JAKARTA),
    )
    monkeypatch.setattr(
        runner.base,
        "_closed_through_date",
        lambda now=None: pd.Timestamp("2026-08-11"),
    )
    monkeypatch.setattr(
        runner.runtime,
        "sync_forward_calendar",
        lambda paths, through=None: pd.DatetimeIndex(["2026-08-11"]),
    )
    monkeypatch.setattr(
        runner.runtime,
        "_load_forward_calendar",
        lambda paths: pd.DatetimeIndex(["2026-08-11", "2026-08-12"]),
    )
    _no_legacy_rows(monkeypatch)
    missing = iter([pd.Timestamp("2026-08-11"), None])
    monkeypatch.setattr(
        runner.base,
        "_earliest_missing",
        lambda paths, sessions: next(missing),
    )
    monkeypatch.setattr(
        runner.runtime,
        "capture_session",
        lambda *args, **kwargs: {
            "status": "DATA_READY",
            "session_date": "2026-08-11",
        },
    )

    result = runner.run_eod_catchup(tmp_path)

    assert result["status"] == "NO_MISSING_SESSION"
    assert result["today_capture_allowed"] is False
    assert result["pre_eod_prior_session_catchup_allowed"] is True
    assert result["closed_through_session"] == "2026-08-11"
    assert result["captured_sessions"][0]["session_date"] == "2026-08-11"
    assert result["captured_sessions"][0]["session_date_validation"] == (
        "PASS_CALENDAR_EXACT_SOURCE_DATE_AND_CLOSED_THROUGH_BOUND"
    )


def test_closed_through_stays_previous_day_between_17_and_18(monkeypatch) -> None:
    monkeypatch.setattr(
        runner.base,
        "_closed_through_date",
        lambda now=None: pd.Timestamp("2026-08-12"),
    )
    now = datetime(2026, 8, 12, 17, 59, tzinfo=JAKARTA)
    assert runner._closed_through_for_run(now) == pd.Timestamp("2026-08-11")


def test_runner_catches_up_after_missed_schedule_and_records_date_validation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_now_jakarta",
        lambda: datetime(2026, 8, 12, 19, 2, tzinfo=JAKARTA),
    )
    monkeypatch.setattr(
        runner.base,
        "_closed_through_date",
        lambda now=None: pd.Timestamp("2026-08-12"),
    )
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
    _no_legacy_rows(monkeypatch)
    missing = iter([pd.Timestamp("2026-08-11"), None])
    monkeypatch.setattr(
        runner.base,
        "_earliest_missing",
        lambda paths, sessions: next(missing),
    )
    monkeypatch.setattr(
        runner.runtime,
        "capture_session",
        lambda *args, **kwargs: {
            "status": "DATA_READY",
            "session_date": "2026-08-11",
        },
    )
    result = runner.run_eod_catchup(tmp_path)

    assert result["status"] == "NO_MISSING_SESSION"
    assert result["today_capture_allowed"] is True
    assert result["closed_through_session"] == "2026-08-12"
    assert result["official_calendar_validation"] == "PASS_EXACT_IDX_SESSION_CALENDAR"
    assert result["captured_sessions"][0]["session_date_validation"] == (
        "PASS_CALENDAR_EXACT_SOURCE_DATE_AND_CLOSED_THROUGH_BOUND"
    )


def test_runner_stops_on_first_capture_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "_now_jakarta",
        lambda: datetime(2026, 8, 12, 18, 5, tzinfo=JAKARTA),
    )
    monkeypatch.setattr(
        runner.base,
        "_closed_through_date",
        lambda now=None: pd.Timestamp("2026-08-12"),
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
    _no_legacy_rows(monkeypatch)
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

    latest = (
        tmp_path / "forward_monitoring" / "eod_automation" / "latest.json"
    ).read_text()
    assert "DATA_FAILED" in latest
    assert "stopped_on_first_failure" in latest


def test_runner_rejects_data_ready_result_for_wrong_session(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "_now_jakarta",
        lambda: datetime(2026, 8, 12, 18, 5, tzinfo=JAKARTA),
    )
    monkeypatch.setattr(
        runner.base,
        "_closed_through_date",
        lambda now=None: pd.Timestamp("2026-08-12"),
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
    _no_legacy_rows(monkeypatch)
    monkeypatch.setattr(
        runner.base,
        "_earliest_missing",
        lambda paths, sessions: pd.Timestamp("2026-08-11"),
    )
    monkeypatch.setattr(
        runner.runtime,
        "capture_session",
        lambda *args, **kwargs: {"status": "DATA_READY", "session_date": "2026-08-12"},
    )

    try:
        runner.run_eod_catchup(tmp_path)
    except RuntimeError as error:
        assert "different session" in str(error)
    else:
        raise AssertionError("runner must reject a mismatched DATA_READY session")

    latest = (tmp_path / "forward_monitoring" / "eod_automation" / "latest.json").read_text()
    assert "DATA_FAILED" in latest
    assert "PASS_CALENDAR_EXACT_SOURCE_DATE_AND_CLOSED_THROUGH_BOUND" not in latest


def test_runner_stops_if_data_ready_capture_makes_no_progress(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "_now_jakarta",
        lambda: datetime(2026, 8, 12, 18, 5, tzinfo=JAKARTA),
    )
    monkeypatch.setattr(
        runner.base,
        "_closed_through_date",
        lambda now=None: pd.Timestamp("2026-08-12"),
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
    _no_legacy_rows(monkeypatch)
    monkeypatch.setattr(
        runner.base,
        "_earliest_missing",
        lambda paths, sessions: pd.Timestamp("2026-08-11"),
    )
    calls: list[str] = []

    def capture(*args, **kwargs):
        calls.append("2026-08-11")
        return {"status": "DATA_READY", "session_date": "2026-08-11"}

    monkeypatch.setattr(runner.runtime, "capture_session", capture)

    try:
        runner.run_eod_catchup(tmp_path)
    except RuntimeError as error:
        assert "no chronological progress" in str(error)
    else:
        raise AssertionError("runner must not loop forever on an unchanged earliest session")

    assert calls == ["2026-08-11"]
