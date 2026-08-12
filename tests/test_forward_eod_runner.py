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
        lambda: datetime(2026, 8, 12, 16, 59, tzinfo=ZoneInfo("Asia/Jakarta")),
    )

    result = runner.run_eod_catchup(tmp_path)

    assert result["status"] == "BEFORE_EOD_CUTOFF"
    assert result["captured_sessions"] == []
    assert (tmp_path / "forward_monitoring" / "eod_automation" / "latest.json").exists()


def test_runner_stops_on_first_capture_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "_now_jakarta",
        lambda: datetime(2026, 8, 12, 17, 5, tzinfo=ZoneInfo("Asia/Jakarta")),
    )
    monkeypatch.setattr(
        runner.runtime,
        "sync_forward_calendar",
        lambda paths: pd.DatetimeIndex(["2026-08-11"]),
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
