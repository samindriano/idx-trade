import json
from datetime import datetime
from zoneinfo import ZoneInfo

from idx_trade.official_open_capture_runtime_v1 import (
    STATUS_ALREADY_CAPTURED,
    STATUS_CAPTURED,
    STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED,
    STATUS_SOURCE_NOT_READY_OR_NO_SESSION,
    STATUS_TOO_EARLY,
    STATUS_WEEKEND_NO_SESSION,
    run_same_session_official_open_capture,
)


JAKARTA = ZoneInfo("Asia/Jakarta")


def _payload(rows):
    return json.dumps(
        {
            "data": rows,
            "recordsTotal": len(rows),
            "recordsFiltered": len(rows),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _rows(date="2026-08-24"):
    stamp = f"{date}T00:00:00"
    return [
        {"StockCode": "AAA", "Date": stamp, "OpenPrice": 1000, "FirstTrade": 1010},
        {"StockCode": "BBB", "Date": stamp, "OpenPrice": 0, "FirstTrade": 2000},
    ]


class _Response:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


def test_runtime_does_not_call_network_before_0902(tmp_path):
    called = False

    def fake_get(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network must not be called")

    result = run_same_session_official_open_capture(
        runtime_root=tmp_path,
        now=datetime(2026, 8, 24, 9, 1, tzinfo=JAKARTA),
        get=fake_get,
    )
    assert result["status"] == STATUS_TOO_EARLY
    assert called is False


def test_runtime_does_not_call_network_on_weekend(tmp_path):
    called = False

    def fake_get(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network must not be called")

    result = run_same_session_official_open_capture(
        runtime_root=tmp_path,
        now=datetime(2026, 8, 22, 9, 7, tzinfo=JAKARTA),
        get=fake_get,
    )
    assert result["status"] == STATUS_WEEKEND_NO_SESSION
    assert called is False


def test_runtime_captures_only_current_session_and_is_idempotent(tmp_path):
    calls = 0

    def fake_get(url, *, params, headers, timeout):
        nonlocal calls
        calls += 1
        assert params["date"] == "20260824"
        assert "code" not in params
        return _Response(_payload(_rows()))

    now = datetime(2026, 8, 24, 9, 7, tzinfo=JAKARTA)
    first = run_same_session_official_open_capture(
        runtime_root=tmp_path, now=now, get=fake_get
    )
    assert first["status"] == STATUS_CAPTURED
    assert calls == 1
    manifest = tmp_path / "official_open" / "2026-08-24" / "manifest.json"
    assert manifest.is_file()

    second = run_same_session_official_open_capture(
        runtime_root=tmp_path, now=now, get=fake_get
    )
    assert second["status"] == STATUS_ALREADY_CAPTURED
    assert calls == 1


def test_runtime_treats_empty_source_as_retryable_not_ready(tmp_path):
    def fake_get(url, *, params, headers, timeout):
        return _Response(
            json.dumps({"data": [], "recordsTotal": 0, "recordsFiltered": 0}).encode()
        )

    result = run_same_session_official_open_capture(
        runtime_root=tmp_path,
        now=datetime(2026, 8, 24, 9, 2, tzinfo=JAKARTA),
        get=fake_get,
    )
    assert result["status"] == STATUS_SOURCE_NOT_READY_OR_NO_SESSION
    assert not (tmp_path / "official_open" / "2026-08-24" / "manifest.json").exists()


def test_runtime_refuses_partial_final_evidence_folder(tmp_path):
    folder = tmp_path / "official_open" / "2026-08-24"
    folder.mkdir(parents=True)
    (folder / "raw_response.json").write_text("partial", encoding="utf-8")
    called = False

    def fake_get(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network must not be called over partial evidence")

    result = run_same_session_official_open_capture(
        runtime_root=tmp_path,
        now=datetime(2026, 8, 24, 9, 12, tzinfo=JAKARTA),
        get=fake_get,
    )
    assert result["status"] == STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED
    assert called is False


def test_runtime_never_backfills_previous_session(tmp_path):
    observed_date = None

    def fake_get(url, *, params, headers, timeout):
        nonlocal observed_date
        observed_date = params["date"]
        return _Response(_payload(_rows("2026-08-25")))

    result = run_same_session_official_open_capture(
        runtime_root=tmp_path,
        now=datetime(2026, 8, 25, 14, 0, tzinfo=JAKARTA),
        get=fake_get,
    )
    assert result["status"] == STATUS_CAPTURED
    assert observed_date == "20260825"
    assert (tmp_path / "official_open" / "2026-08-25" / "manifest.json").is_file()
    assert not (tmp_path / "official_open" / "2026-08-24").exists()
