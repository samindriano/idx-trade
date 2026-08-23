from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from scripts.run_stockbit_stream_capture_v2 import _EnvelopeAwareResponse
from idx_trade.stockbit_stream_archive import QuotaSnapshot
from idx_trade.stockbit_stream_capture_v2 import LocalLeanArchive, RuntimeUniverse, build_runtime_universe, capture_stream_v2


class Response:
    def __init__(self, body: dict, status: int = 200):
        self.status_code = status
        self._body = body
        self.content = json.dumps(body).encode()
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._body


class Session:
    def get(self, url, params, headers, timeout):
        assert params["date"] == "2026-08-20"
        rows = [
            {"StockCode": "BBCA", "Date": "2026-08-20T00:00:00", "Value": 300, "NonRegularValue": 0},
            {"StockCode": "BBRI", "Date": "2026-08-20T00:00:00", "Value": 500, "NonRegularValue": 0},
            {"StockCode": "AADI", "Date": "2026-08-20T00:00:00", "Value": 1000, "NonRegularValue": 950},
        ]
        return Response({"provider": "idx", "dataset": "stock-summary", "data": rows})


class WeekendCaptureSession:
    """A weekend capture may use the latest completed Friday session."""

    def get(self, url, params, headers, timeout):
        requested = params["date"]
        if requested == "2026-08-22":
            return Response({"provider": "idx", "dataset": "stock-summary", "data": []})
        assert requested == "2026-08-21"
        rows = [
            {"StockCode": "BBCA", "Date": "2026-08-21T00:00:00", "Value": 300, "NonRegularValue": 0},
            {"StockCode": "BBRI", "Date": "2026-08-21T00:00:00", "Value": 500, "NonRegularValue": 0},
            {"StockCode": "AADI", "Date": "2026-08-21T00:00:00", "Value": 1000, "NonRegularValue": 950},
        ]
        return Response({"provider": "idx", "dataset": "stock-summary", "data": rows})


def test_envelope_aware_response_exposes_inner_idx_payload():
    response = Response(
        {
            "project": "finance:idx",
            "timestamp": "2026-08-21T00:00:00Z",
            "data": {"provider": "idx", "dataset": "stock-summary", "data": []},
        }
    )
    assert _EnvelopeAwareResponse(response).json() == {
        "provider": "idx",
        "dataset": "stock-summary",
        "data": [],
    }


def identity_csv(path: Path):
    fields = ["ticker", "company_name", "listed_from", "listed_to", "capture_broad", "capture_high", "activity_rank", "activity_median_regular_value_60", "universe_source"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for ticker in ["BBCA", "BBRI", "AADI"]:
            w.writerow({"ticker": ticker, "company_name": ticker, "listed_from": "2000-01-01", "listed_to": "", "capture_broad": "1", "capture_high": "0", "activity_rank": "", "activity_median_regular_value_60": "", "universe_source": "TEST"})


def test_runtime_universe_uses_prior_session_regular_value(tmp_path: Path):
    path = tmp_path / "identity.csv"
    identity_csv(path)
    universe = build_runtime_universe(api_key="x", identity_csv=path, capture_date="2026-08-21", top_n=2, session=Session())
    assert universe.source_session == "2026-08-20"
    assert [row["ticker"] for row in universe.rows] == ["BBRI", "BBCA"]
    assert [row["activity_rank"] for row in universe.rows] == [1, 2]


def test_runtime_universe_continues_past_weekend_for_calendar_day_capture(tmp_path: Path):
    path = tmp_path / "identity.csv"
    identity_csv(path)
    universe = build_runtime_universe(
        api_key="x",
        identity_csv=path,
        capture_date="2026-08-23",
        top_n=2,
        session=WeekendCaptureSession(),
    )
    assert universe.capture_date == "2026-08-23"
    assert universe.source_session == "2026-08-21"
    assert [row["ticker"] for row in universe.rows] == ["BBRI", "BBCA"]


class StreamResponse:
    status_code = 200
    headers = {"content-type": "application/json"}


class Client:
    def __init__(self):
        self.calls = []

    def get_usage(self):
        return QuotaSnapshot("pro", 1, 25000, 24999, None, "TEST")

    def stream(self, symbol):
        self.calls.append(symbol)
        item = {"id": f"{symbol}-1", "createdAt": "2026-08-21 12:00:00", "content": f"watch ${symbol}", "userId": "u", "likes": 1}
        raw = json.dumps({"data": {"count": 1, "items": [item], "symbol": symbol}}).encode()
        return StreamResponse(), raw, datetime(2026, 8, 21, 5, tzinfo=timezone.utc)


class PartialClient(Client):
    def stream(self, symbol):
        if symbol == "BBCA":
            self.calls.append(symbol)
            return StreamResponse503(), b'{"error":"temporary"}', datetime(2026, 8, 21, 5, tzinfo=timezone.utc)
        return super().stream(symbol)


class TransientRecoveryClient(Client):
    def __init__(self):
        super().__init__()
        self.attempts = {}

    def stream(self, symbol):
        self.attempts[symbol] = self.attempts.get(symbol, 0) + 1
        if symbol == "BBCA" and self.attempts[symbol] == 1:
            self.calls.append(symbol)
            return StreamResponse503(), b'{"error":"temporary"}', datetime(2026, 8, 21, 5, tzinfo=timezone.utc)
        return super().stream(symbol)


class StreamResponse503:
    status_code = 503
    headers = {"content-type": "application/json"}


class PostQuotaTimeoutClient(Client):
    def __init__(self):
        super().__init__()
        self.usage_calls = 0

    def get_usage(self):
        self.usage_calls += 1
        if self.usage_calls == 2:
            raise requests.ReadTimeout("quota telemetry timeout")
        return super().get_usage()


def test_capture_v2_avoids_per_post_hot_path_objects(tmp_path: Path):
    rows = [
        {"ticker": "BBRI", "company_name": "BBRI", "listed_from": "2000", "source_session": "2026-08-20", "regular_value": 500.0, "activity_rank": 1},
        {"ticker": "BBCA", "company_name": "BBCA", "listed_from": "2000", "source_session": "2026-08-20", "regular_value": 300.0, "activity_rank": 2},
    ]
    universe = RuntimeUniverse("2026-08-21", "2026-08-20", rows, b'{"provider":"idx"}', "a" * 64, "b" * 64)
    client = Client()
    result = capture_stream_v2(client=client, archive=LocalLeanArchive(tmp_path), universe=universe, slot="midday", hmac_salt="salt", monthly_reserve=1)
    assert result["status"] == "DATA_READY"
    assert client.calls == ["BBRI", "BBCA"]
    assert result["normalized_post_rows"] == 2
    assert not (tmp_path / "posts").exists()
    assert len(list((tmp_path / "raw").rglob("*.json"))) == 2
    assert len(list((tmp_path / "normalized").rglob("*.jsonl"))) == 2
    assert len(list((tmp_path / "manifests").rglob("*.json"))) == 1


def test_capture_v2_marks_partial_stream_failures_not_data_ready(tmp_path: Path):
    rows = [
        {"ticker": "BBRI", "company_name": "BBRI", "listed_from": "2000", "source_session": "2026-08-20", "regular_value": 500.0, "activity_rank": 1},
        {"ticker": "BBCA", "company_name": "BBCA", "listed_from": "2000", "source_session": "2026-08-20", "regular_value": 300.0, "activity_rank": 2},
    ]
    universe = RuntimeUniverse("2026-08-21", "2026-08-20", rows, b'{"provider":"idx"}', "a" * 64, "b" * 64)
    result = capture_stream_v2(client=PartialClient(), archive=LocalLeanArchive(tmp_path), universe=universe, slot="midday", hmac_salt="salt", monthly_reserve=1)
    assert result["status"] == "PARTIAL_FAILURE"
    assert result["completed_calls"] == 2
    assert result["successful_responses"] == 1
    assert result["response_classification_counts"] == {"OK": 1, "HTTP_503": 1}


def test_capture_v2_retries_transient_5xx_once_and_recovers(tmp_path: Path):
    rows = [
        {"ticker": "BBCA", "company_name": "BBCA", "listed_from": "2000", "source_session": "2026-08-20", "regular_value": 500.0, "activity_rank": 1},
        {"ticker": "BBRI", "company_name": "BBRI", "listed_from": "2000", "source_session": "2026-08-20", "regular_value": 300.0, "activity_rank": 2},
    ]
    universe = RuntimeUniverse("2026-08-21", "2026-08-20", rows, b'{"provider":"idx"}', "a" * 64, "b" * 64)
    client = TransientRecoveryClient()
    result = capture_stream_v2(client=client, archive=LocalLeanArchive(tmp_path), universe=universe, slot="midday", hmac_salt="salt", monthly_reserve=1)
    assert result["status"] == "DATA_READY"
    assert result["provider_calls"] == 3
    assert client.calls == ["BBCA", "BBCA", "BBRI"]
    bbca = next(record for record in result["request_records"] if record["ticker"] == "BBCA")
    assert bbca["retry_recovered"] is True
    assert [attempt["http_status"] for attempt in bbca["provider_attempts"]] == [503, 200]


def test_capture_v2_preserves_ready_run_when_post_quota_telemetry_times_out(tmp_path: Path):
    rows = [
        {"ticker": "BBRI", "company_name": "BBRI", "listed_from": "2000", "source_session": "2026-08-20", "regular_value": 500.0, "activity_rank": 1},
    ]
    universe = RuntimeUniverse("2026-08-21", "2026-08-20", rows, b'{"provider":"idx"}', "a" * 64, "c" * 64)
    result = capture_stream_v2(client=PostQuotaTimeoutClient(), archive=LocalLeanArchive(tmp_path), universe=universe, slot="midday", hmac_salt="salt", monthly_reserve=1)
    assert result["status"] == "DATA_READY"
    assert result["quota_after"] == {
        "status": "UNAVAILABLE",
        "source": "MCP_GET_USAGE",
        "detail": "quota telemetry timeout",
    }


def test_capture_v2_run_namespace_includes_source_response_digest(tmp_path: Path):
    rows = [
        {"ticker": "BBRI", "company_name": "BBRI", "listed_from": "2000", "source_session": "2026-08-20", "regular_value": 500.0, "activity_rank": 1},
    ]
    first = RuntimeUniverse("2026-08-21", "2026-08-20", rows, b"first", "a" * 64, "c" * 64)
    second = RuntimeUniverse("2026-08-21", "2026-08-20", rows, b"second", "b" * 64, "c" * 64)
    first_result = capture_stream_v2(client=Client(), archive=LocalLeanArchive(tmp_path / "first"), universe=first, slot="midday", hmac_salt="salt", monthly_reserve=1)
    second_result = capture_stream_v2(client=Client(), archive=LocalLeanArchive(tmp_path / "second"), universe=second, slot="midday", hmac_salt="salt", monthly_reserve=1)
    assert first_result["run_id"] != second_result["run_id"]
    assert "a" * 16 in first_result["run_id"]
    assert "b" * 16 in second_result["run_id"]
