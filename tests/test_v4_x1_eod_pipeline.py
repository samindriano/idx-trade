from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from idx_trade import v4_x1_eod_pipeline as pipeline


JAKARTA = ZoneInfo("Asia/Jakarta")


def test_same_day_filter_rejects_old_pending_and_late_completion() -> None:
    now = datetime(2026, 8, 20, 20, 0, tzinfo=JAKARTA)
    pending = [
        (
            pd.Timestamp("2026-08-19"),
            {"completed_at": "2026-08-19T13:00:00+00:00"},
        ),
        (
            pd.Timestamp("2026-08-20"),
            {"completed_at": "2026-08-20T13:00:00+00:00"},
        ),
    ]

    eligible, ignored = pipeline._filter_same_day_pending(pending, now=now)

    assert [day.date().isoformat() for day, _ in eligible] == ["2026-08-20"]
    assert ignored == [
        {
            "session_date": "2026-08-19",
            "completed_at": "2026-08-19T13:00:00+00:00",
            "reason": "X1_SCORE_WINDOW_EXPIRED_NOT_SAME_JAKARTA_DATE",
            "prospective_counter_eligible": False,
            "continuity_history_eligible": True,
        }
    ]


def test_same_day_filter_rejects_data_ready_completed_next_day() -> None:
    now = datetime(2026, 8, 20, 20, 0, tzinfo=JAKARTA)
    pending = [
        (
            pd.Timestamp("2026-08-20"),
            {"completed_at": "2026-08-20T18:30:00+00:00"},
        )
    ]

    eligible, ignored = pipeline._filter_same_day_pending(pending, now=now)

    assert eligible == []
    assert ignored[0]["reason"] == "X1_DATA_READY_COMPLETED_AFTER_SESSION_DATE"


def test_pre_eod_pipeline_is_catchup_only(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        pipeline,
        "run_eod_catchup",
        lambda *args, **kwargs: {
            "status": "NO_MISSING_SESSION",
            "today_capture_allowed": False,
        },
    )
    monkeypatch.setattr(pipeline, "_persist", lambda *args, **kwargs: None)

    def must_not_score(*args, **kwargs):
        raise AssertionError("X1 scorer must not run before EOD")

    monkeypatch.setattr(pipeline.x1, "score_v4_x1_session", must_not_score)

    result = pipeline.run_eod_v4_x1_pipeline(
        tmp_path,
        tmp_path,
        repo_root=tmp_path,
        now=datetime(2026, 8, 20, 9, 0, tzinfo=JAKARTA),
    )

    assert result["status"] == "PIPELINE_OK_PRIOR_SESSION_CATCHUP_ONLY_BEFORE_EOD"
    assert result["x1_score_attempted"] is False


def test_eod_failure_short_circuits_x1(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        pipeline,
        "run_eod_catchup",
        lambda *args, **kwargs: {
            "status": "DATA_FAILED",
            "today_capture_allowed": True,
        },
    )
    monkeypatch.setattr(pipeline, "_persist", lambda *args, **kwargs: None)

    def must_not_score(*args, **kwargs):
        raise AssertionError("X1 scorer must not run after EOD failure")

    monkeypatch.setattr(pipeline.x1, "score_v4_x1_session", must_not_score)

    result = pipeline.run_eod_v4_x1_pipeline(
        tmp_path,
        tmp_path,
        repo_root=tmp_path,
        now=datetime(2026, 8, 20, 20, 0, tzinfo=JAKARTA),
    )

    assert result["status"] == "EOD_FAILED_X1_NOT_RUN"


def test_successful_eod_commits_new_x1_score(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        pipeline,
        "run_eod_catchup",
        lambda *args, **kwargs: {
            "status": "NO_MISSING_SESSION",
            "today_capture_allowed": True,
        },
    )
    monkeypatch.setattr(pipeline, "_persist", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        pipeline.x1,
        "score_v4_x1_session",
        lambda *args, **kwargs: {
            "status": "V4_X1_PROSPECTIVE_SCORE_DONE",
            "session_date": "2026-08-20",
            "provider_calls": False,
            "protected_outcome_accessed": False,
            "model_refit": False,
            "model_retuned": False,
        },
    )

    result = pipeline.run_eod_v4_x1_pipeline(
        tmp_path,
        tmp_path,
        repo_root=tmp_path,
        now=datetime(2026, 8, 20, 20, 0, tzinfo=JAKARTA),
    )

    assert result["status"] == "PIPELINE_OK_X1_NEW_SCORE_COMMITTED"
    assert result["x1_score"]["session_date"] == "2026-08-20"
    assert result["protected_outcome_accessed"] is False


def test_pipeline_source_has_no_outcome_or_provider_entrypoint() -> None:
    source = Path(pipeline.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "fetch_stock_summary_snapshot",
        "fetch_index_summary_snapshot",
        "download_daily",
        "materialize_v4_target_ledger",
        "target_rank_h5",
        "target_rank_h10",
    ):
        assert forbidden not in source
    assert '"protected_outcome_accessed": False' in source
    assert '"provider_calls_from_x1": False' in source
    assert "CONTINUITY_ONLY_NOT_X1_COUNTER" in source
