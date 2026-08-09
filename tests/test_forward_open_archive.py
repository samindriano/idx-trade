from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from idx_trade.forward_open_archive import (
    STATUS_ALREADY_ARCHIVED,
    STATUS_ARCHIVED,
    STATUS_BLOCKED_SOURCE,
    archive_one_session,
    run_forward_archive,
    validate_snapshot,
)


def _snapshot(session="2026-08-10"):
    return pd.DataFrame(
        {
            "ticker": ["BBCA", "BBRI"],
            "date": [session, session],
            "open": [8000, 4100],
            "high": [8100, 4200],
            "low": [7900, 4050],
            "close": [8050, 4150],
            "volume": [100, 200],
        }
    )


def test_validate_snapshot_accepts_complete_session():
    result = validate_snapshot(_snapshot(), pd.Timestamp("2026-08-10"))
    assert result["ticker"].tolist() == ["BBCA", "BBRI"]
    assert result["open"].tolist() == [8000, 4100]


def test_validate_snapshot_rejects_open_outside_envelope():
    frame = _snapshot()
    frame.loc[0, "open"] = 8200
    with pytest.raises(ValueError, match="OHLC envelope"):
        validate_snapshot(frame, pd.Timestamp("2026-08-10"))


def test_validate_snapshot_rejects_wrong_session():
    frame = _snapshot()
    frame.loc[0, "date"] = "2026-08-09"
    with pytest.raises(ValueError, match="outside the requested session"):
        validate_snapshot(frame, pd.Timestamp("2026-08-10"))


def test_archive_one_session_is_immutable_and_idempotent(tmp_path):
    calls = []

    def fetcher(session):
        calls.append(session)
        return _snapshot(session.date().isoformat()), {"source_ref": "test://snapshot"}

    first = archive_one_session(
        pd.Timestamp("2026-08-10"),
        data_root=tmp_path,
        fetcher=fetcher,
        provider_id="TEST",
    )
    assert first.status == STATUS_ARCHIVED
    assert first.rows == 2
    assert len(calls) == 1

    second = archive_one_session(
        pd.Timestamp("2026-08-10"),
        data_root=tmp_path,
        fetcher=fetcher,
        provider_id="TEST",
    )
    assert second.status == STATUS_ALREADY_ARCHIVED
    assert second.snapshot_sha256 == first.snapshot_sha256
    assert len(calls) == 1


def test_run_without_frozen_provider_fails_closed_and_records_status(tmp_path):
    result = run_forward_archive(
        data_root=tmp_path,
        provider_module="",
        now=datetime(2026, 8, 10, 22, 0, tzinfo=ZoneInfo("Asia/Jakarta")),
    )
    assert result["status"] == STATUS_BLOCKED_SOURCE
    assert (tmp_path / "forward_open_archive" / "latest_run.json").is_file()
