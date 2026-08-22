from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import requests

from idx_trade.stockbit_stream_archive import StreamArchiveError
from idx_trade.stockbit_stream_capture_v2 import build_runtime_universe
from idx_trade.stockbit_stream_http import BoundedRetrySession


class Response:
    def __init__(self, body: dict, status: int = 200):
        self.status_code = status
        self._body = body
        self.content = json.dumps(body).encode()
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._body


class SequenceSession:
    def __init__(self, events):
        self.events = list(events)
        self.calls = 0

    def get(self, url, params, headers, timeout):
        del url, params, headers, timeout
        self.calls += 1
        if not self.events:
            raise AssertionError("unexpected extra HTTP attempt")
        event = self.events.pop(0)
        if isinstance(event, BaseException):
            raise event
        return event


def valid_body():
    rows = [
        {"StockCode": "BBCA", "Date": "2026-08-20T00:00:00", "Value": 300, "NonRegularValue": 0},
        {"StockCode": "BBRI", "Date": "2026-08-20T00:00:00", "Value": 500, "NonRegularValue": 0},
        {"StockCode": "AADI", "Date": "2026-08-20T00:00:00", "Value": 1000, "NonRegularValue": 950},
    ]
    return {
        "provider": "idx",
        "dataset": "stock-summary",
        "recordsTotal": 3,
        "recordsFiltered": 3,
        "start": 0,
        "length": 3,
        "data": rows,
    }


def identity_csv(path: Path):
    fields = [
        "ticker",
        "company_name",
        "listed_from",
        "listed_to",
        "capture_broad",
        "capture_high",
        "activity_rank",
        "activity_median_regular_value_60",
        "universe_source",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for ticker in ("BBCA", "BBRI", "AADI"):
            writer.writerow(
                {
                    "ticker": ticker,
                    "company_name": ticker,
                    "listed_from": "2000-01-01",
                    "listed_to": "",
                    "capture_broad": "1",
                    "capture_high": "0",
                    "activity_rank": "",
                    "activity_median_regular_value_60": "",
                    "universe_source": "TEST",
                }
            )


def retry_session(events):
    underlying = SequenceSession(events)
    wrapper = BoundedRetrySession(
        session=underlying,
        max_attempts=3,
        timeout_seconds=30,
        backoff_seconds=(),
    )
    return underlying, wrapper


def test_transient_read_timeout_retries_same_candidate_then_succeeds(tmp_path: Path):
    path = tmp_path / "identity.csv"
    identity_csv(path)
    underlying, wrapper = retry_session(
        [requests.ReadTimeout("transient"), Response(valid_body())]
    )

    universe = build_runtime_universe(
        api_key="x",
        identity_csv=path,
        capture_date="2026-08-21",
        top_n=2,
        session=wrapper,
    )

    assert universe.source_session == "2026-08-20"
    assert [row["ticker"] for row in universe.rows] == ["BBRI", "BBCA"]
    assert wrapper.attempts == 2
    assert underlying.calls == 2
    assert wrapper.transient_events == [
        {"attempt": 1, "kind": "ReadTimeout", "status_code": None}
    ]


def test_transient_503_retries_same_candidate_then_succeeds(tmp_path: Path):
    path = tmp_path / "identity.csv"
    identity_csv(path)
    underlying, wrapper = retry_session(
        [Response({"error": "temporary"}, status=503), Response(valid_body())]
    )

    universe = build_runtime_universe(
        api_key="x",
        identity_csv=path,
        capture_date="2026-08-21",
        top_n=2,
        session=wrapper,
    )

    assert universe.source_session == "2026-08-20"
    assert wrapper.attempts == 2
    assert underlying.calls == 2
    assert wrapper.transient_events == [
        {"attempt": 1, "kind": "HTTP_5XX", "status_code": 503}
    ]


def test_all_transport_attempts_exhaust_fail_closed(tmp_path: Path):
    path = tmp_path / "identity.csv"
    identity_csv(path)
    underlying, wrapper = retry_session(
        [
            requests.ReadTimeout("one"),
            requests.ReadTimeout("two"),
            requests.ReadTimeout("three"),
        ]
    )

    with pytest.raises(requests.ReadTimeout):
        build_runtime_universe(
            api_key="x",
            identity_csv=path,
            capture_date="2026-08-21",
            top_n=2,
            session=wrapper,
        )

    assert wrapper.attempts == 3
    assert underlying.calls == 3
    assert len(wrapper.transient_events) == 3


@pytest.mark.parametrize("status", [401, 403, 429])
def test_auth_and_quota_statuses_are_never_retried(tmp_path: Path, status: int):
    path = tmp_path / "identity.csv"
    identity_csv(path)
    underlying, wrapper = retry_session([Response({"error": "blocked"}, status=status)])

    with pytest.raises(StreamArchiveError, match=f"HTTP {status}"):
        build_runtime_universe(
            api_key="x",
            identity_csv=path,
            capture_date="2026-08-21",
            top_n=2,
            session=wrapper,
        )

    assert wrapper.attempts == 1
    assert underlying.calls == 1
    assert wrapper.transient_events == []


def test_final_5xx_is_returned_after_three_attempts_without_fourth_call():
    underlying, wrapper = retry_session(
        [
            Response({"error": "temporary"}, status=503),
            Response({"error": "temporary"}, status=503),
            Response({"error": "temporary"}, status=503),
        ]
    )

    response = wrapper.get(
        "https://example.invalid",
        params={},
        headers={},
        timeout=30,
    )

    assert response.status_code == 503
    assert wrapper.attempts == 3
    assert underlying.calls == 3
    assert wrapper.transient_events == [
        {"attempt": 1, "kind": "HTTP_5XX", "status_code": 503},
        {"attempt": 2, "kind": "HTTP_5XX", "status_code": 503},
    ]
