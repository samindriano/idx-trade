import json
from datetime import datetime
from zoneinfo import ZoneInfo

from idx_trade.official_open_capture_runtime_v1 import (
    STATUS_ALREADY_CAPTURED,
    STATUS_CAPTURED,
    STATUS_CAPTURE_FAIL_CLOSED,
    STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED,
    STATUS_SOURCE_NOT_READY_OR_NO_SESSION,
    STATUS_TOO_EARLY,
    STATUS_WEEKEND_NO_SESSION,
    run_same_session_official_open_capture,
)
from idx_trade.official_open_evidence_v1 import (
    DIRECT_TRANSPORT,
    TRANSPORT_POLICY,
    UPSTREAM_PATH,
    ZAPI_RAW_TRANSPORT,
)


JAKARTA = ZoneInfo("Asia/Jakarta")


def _payload(rows, **extra):
    return json.dumps(
        {
            "data": rows,
            "recordsTotal": len(rows),
            "recordsFiltered": len(rows),
            **extra,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _zapi_payload(rows):
    return _payload(rows, provider="idx", path=UPSTREAM_PATH)


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
    assert first["transport"] == DIRECT_TRANSPORT
    assert first["transport_policy"] == TRANSPORT_POLICY
    assert calls == 1
    manifest = tmp_path / "official_open" / "2026-08-24" / "manifest.json"
    assert manifest.is_file()

    second = run_same_session_official_open_capture(
        runtime_root=tmp_path, now=now, get=fake_get
    )
    assert second["status"] == STATUS_ALREADY_CAPTURED
    assert second["transport"] == DIRECT_TRANSPORT
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
        zapi_api_key=None,
    )
    assert result["status"] == STATUS_SOURCE_NOT_READY_OR_NO_SESSION
    assert not (tmp_path / "official_open" / "2026-08-24" / "manifest.json").exists()


def test_runtime_direct_403_without_zapi_key_fails_closed_but_remains_retryable(tmp_path):
    def fake_get(url, *, params, headers, timeout):
        return _Response(b"forbidden", status_code=403)

    result = run_same_session_official_open_capture(
        runtime_root=tmp_path,
        now=datetime(2026, 8, 24, 9, 7, tzinfo=JAKARTA),
        get=fake_get,
        zapi_api_key="",
    )
    assert result["status"] == STATUS_CAPTURE_FAIL_CLOSED
    assert "DIRECT=OFFICIAL_OPEN_DIRECT_IDX_HTTP_403" in result["provider_error"]
    assert "ZAPI=NOT_CONFIGURED" in result["provider_error"]
    assert not (tmp_path / "official_open" / "2026-08-24").exists()
    latest = json.loads((tmp_path / "official_open" / "latest_capture.json").read_text())
    assert latest["status"] == STATUS_CAPTURE_FAIL_CLOSED


def test_runtime_direct_403_falls_back_to_zapi_raw_and_certifies_same_session(tmp_path):
    direct_calls = 0
    zapi_calls = 0

    def direct_get(url, *, params, headers, timeout):
        nonlocal direct_calls
        direct_calls += 1
        return _Response(b"forbidden", status_code=403)

    def zapi_get(url, *, params, headers, timeout):
        nonlocal zapi_calls
        zapi_calls += 1
        assert params["path"] == UPSTREAM_PATH
        assert params["query"] == "date=20260824&start=0&length=9999"
        assert "code" not in params["query"]
        return _Response(_zapi_payload(_rows()))

    result = run_same_session_official_open_capture(
        runtime_root=tmp_path,
        now=datetime(2026, 8, 24, 9, 7, tzinfo=JAKARTA),
        get=direct_get,
        zapi_get=zapi_get,
        zapi_api_key="test-key",
    )
    assert result["status"] == STATUS_CAPTURED
    assert result["transport"] == ZAPI_RAW_TRANSPORT
    assert result["transport_policy"] == TRANSPORT_POLICY
    assert direct_calls == 1
    assert zapi_calls == 1

    manifest = json.loads(
        (tmp_path / "official_open" / "2026-08-24" / "manifest.json").read_text()
    )
    assert manifest["transport"] == ZAPI_RAW_TRANSPORT
    assert manifest["authority"] == "IDX"
    assert manifest["upstream_path"] == UPSTREAM_PATH
    assert manifest["fallback_policy"] == "NONE"
    assert manifest["transport_metadata"]["primary_transport_error"] == "OFFICIAL_OPEN_DIRECT_IDX_HTTP_403"


def test_runtime_both_transports_fail_closed(tmp_path):
    def direct_get(url, *, params, headers, timeout):
        return _Response(b"forbidden", status_code=403)

    def zapi_get(url, *, params, headers, timeout):
        return _Response(b"bad gateway", status_code=502)

    result = run_same_session_official_open_capture(
        runtime_root=tmp_path,
        now=datetime(2026, 8, 24, 9, 12, tzinfo=JAKARTA),
        get=direct_get,
        zapi_get=zapi_get,
        zapi_api_key="test-key",
    )
    assert result["status"] == STATUS_CAPTURE_FAIL_CLOSED
    assert "DIRECT=OFFICIAL_OPEN_DIRECT_IDX_HTTP_403" in result["provider_error"]
    assert "ZAPI=OFFICIAL_OPEN_ZAPI_RAW_HTTP_502" in result["provider_error"]
    assert not (tmp_path / "official_open" / "2026-08-24").exists()


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
