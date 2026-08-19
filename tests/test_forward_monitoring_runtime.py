from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from idx_trade import forward_monitoring as base
from idx_trade import forward_monitoring_runtime as runtime


def test_monitor_calendar_filters_prestart_sessions() -> None:
    sessions = pd.DatetimeIndex(
        [
            pd.Timestamp("2026-08-03"),
            pd.Timestamp("2026-08-07"),
            pd.Timestamp("2026-08-10"),
            pd.Timestamp("2026-08-11"),
        ]
    )

    eligible = runtime._eligible_calendar(sessions)

    assert eligible.tolist() == [
        pd.Timestamp("2026-08-10"),
        pd.Timestamp("2026-08-11"),
    ]


def test_sync_forward_calendar_starts_exactly_on_aug_10(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = base.runtime_paths(tmp_path)
    captured: dict[str, pd.Timestamp] = {}

    def fake_backfill(start, end, output_dir):
        captured["start"] = pd.Timestamp(start)
        captured["end"] = pd.Timestamp(end)
        output_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            {"date": ["2026-08-10", "2026-08-11"]}
        ).to_csv(output_dir / "exchange_sessions.csv", index=False)
        return {"complete": True}

    monkeypatch.setattr(base, "run_exchange_session_backfill", fake_backfill)

    sessions = runtime.sync_forward_calendar(paths, through=pd.Timestamp("2026-08-11"))

    assert captured["start"] == runtime.FORWARD_MONITOR_START_DATE
    assert captured["end"] == pd.Timestamp("2026-08-11")
    assert sessions.min() == pd.Timestamp("2026-08-10")


def test_capture_rejects_date_before_monitor_start(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="before the forward monitor start date"):
        runtime.capture_session(tmp_path, target_date="2026-08-07")


def test_status_ignores_prestart_registry_rows(tmp_path: Path) -> None:
    paths = base.runtime_paths(tmp_path)
    paths.calendar_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "date": [
                "2026-08-03",
                "2026-08-04",
                "2026-08-10",
                "2026-08-11",
            ]
        }
    ).to_csv(paths.calendar_root / "exchange_sessions.csv", index=False)

    connection = base._connect(paths)
    try:
        connection.execute(
            """
            INSERT INTO session_snapshots(session_date, state, updated_at)
            VALUES ('2026-08-03', 'DATA_READY', '2026-08-10T00:00:00+00:00')
            """
        )
        connection.execute(
            """
            INSERT INTO session_snapshots(session_date, state, updated_at)
            VALUES ('2026-08-10', 'DATA_READY', '2026-08-10T12:00:00+00:00')
            """
        )
    finally:
        connection.close()

    status = runtime.monitoring_status(tmp_path)

    assert status["monitor_start_date"] == "2026-08-10"
    assert status["calendar_first_session"] == "2026-08-10"
    # A registry-only DATA_READY row is not canonical completion; the
    # integrity pass fails it closed even though the prestart row is filtered.
    assert status["data_ready_sessions"] == 0
    assert [row["session_date"] for row in status["sessions"]] == [
        "2026-08-10",
        "2026-08-11",
    ]
    assert status["next_missing_session"] == "2026-08-10"


def test_legacy_aug_3_ready_does_not_block_aug_10_first_capture(tmp_path: Path) -> None:
    """Regression for the operator screenshot where Aug 3 leaked into the active monitor."""

    paths = base.runtime_paths(tmp_path)
    paths.calendar_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "date": [
                "2026-08-03",
                "2026-08-04",
                "2026-08-05",
                "2026-08-06",
                "2026-08-07",
                "2026-08-10",
            ]
        }
    ).to_csv(paths.calendar_root / "exchange_sessions.csv", index=False)

    connection = base._connect(paths)
    try:
        connection.execute(
            """
            INSERT INTO session_snapshots(session_date, state, updated_at)
            VALUES ('2026-08-03', 'DATA_READY', '2026-08-10T00:00:00+00:00')
            """
        )
    finally:
        connection.close()

    status = runtime.monitoring_status(tmp_path)

    assert status["monitor_start_date"] == "2026-08-10"
    assert status["calendar_first_session"] == "2026-08-10"
    assert status["calendar_last_session"] == "2026-08-10"
    assert status["next_missing_session"] == "2026-08-10"
    assert status["data_ready_sessions"] == 0
    assert status["sessions"] == [
        {
            "session_date": "2026-08-10",
            "state": "AVAILABLE",
            "error_code": None,
            "error_message": None,
            "completed_at": None,
        }
    ]
