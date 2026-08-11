from datetime import date, datetime, time as dt_time

import pandas as pd
import pytest

from idx_trade.stockbit_intraday_capture import (
    JAKARTA,
    _request_chart,
    capture_state,
    load_tickers,
    parse_chart_payload,
    validate_request_budget,
)


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, *, params, headers, timeout):
        self.calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return self.response


def _payload(symbol="BBCA", trading_date="11 Aug 2026"):
    return {
        "symbol": symbol,
        "provider": "stockbit",
        "interval": "intraday",
        "timeframe": "today",
        "tradingDate": trading_date,
        "previousClose": 6400,
        "items": [
            {"time": "2026-08-11 09:00:00", "price": 6425, "change": 25, "changePercent": 0.39},
            {"time": "2026-08-11 09:01:00", "price": 6450, "change": 50, "changePercent": 0.78},
        ],
    }


def test_load_tickers_normalizes_deduplicates_and_accepts_commas():
    assert load_tickers(["bbca, BBRI", "BBCA"]) == ["BBCA", "BBRI"]


def test_parse_chart_payload_accepts_exact_current_session_without_synthesis():
    frame, status = parse_chart_payload(
        "BBCA",
        _payload(),
        expected_date=date(2026, 8, 11),
        capture_state="SESSION_COMPLETE_WINDOW",
    )
    assert status["status"] == "SUCCESS"
    assert status["points"] == 2
    assert frame["ticker"].tolist() == ["BBCA", "BBCA"]
    assert frame["price"].tolist() == [6425.0, 6450.0]
    assert frame["session_date"].nunique() == 1
    assert frame["capture_state"].eq("SESSION_COMPLETE_WINDOW").all()


def test_parse_chart_payload_marks_explicit_partial_capture():
    _, status = parse_chart_payload(
        "BBCA",
        _payload(),
        expected_date=date(2026, 8, 11),
        capture_state="PARTIAL_SESSION",
    )
    assert status["status"] == "PARTIAL_SESSION"


def test_parse_chart_payload_rejects_stale_provider_session():
    payload = _payload(trading_date="10 Aug 2026")
    payload["items"] = [{"time": "2026-08-10 16:00:00", "price": 6400, "change": 0, "changePercent": 0}]
    frame, status = parse_chart_payload(
        "BBCA",
        payload,
        expected_date=date(2026, 8, 11),
        capture_state="SESSION_COMPLETE_WINDOW",
    )
    assert frame.empty
    assert status["status"] == "NON_CURRENT_SESSION"
    assert status["provider_session_date"] == "2026-08-10"


def test_parse_chart_payload_rejects_wrong_identity_contract():
    frame, status = parse_chart_payload(
        "BBCA",
        _payload(symbol="BBRI"),
        expected_date=date(2026, 8, 11),
        capture_state="SESSION_COMPLETE_WINDOW",
    )
    assert frame.empty
    assert status["status"] == "IDENTITY_OR_PAYLOAD_ERROR"


def test_parse_chart_payload_rejects_conflicting_duplicate_timestamp():
    payload = _payload()
    payload["items"].append(
        {"time": "2026-08-11 09:01:00", "price": 6475, "change": 75, "changePercent": 1.17}
    )
    frame, status = parse_chart_payload(
        "BBCA",
        payload,
        expected_date=date(2026, 8, 11),
        capture_state="SESSION_COMPLETE_WINDOW",
    )
    assert frame.empty
    assert status["status"] == "DUPLICATE_TIMESTAMP_CONFLICT"


def test_capture_state_is_fail_closed_before_close_gate():
    before = datetime(2026, 8, 11, 15, 0, tzinfo=JAKARTA)
    after = datetime(2026, 8, 11, 17, 0, tzinfo=JAKARTA)
    assert capture_state(before, dt_time(16, 15), False) == "BLOCKED_BEFORE_CLOSE"
    assert capture_state(before, dt_time(16, 15), True) == "PARTIAL_SESSION"
    assert capture_state(after, dt_time(16, 15), False) == "SESSION_COMPLETE_WINDOW"


def test_request_budget_blocks_accidental_large_universe():
    with pytest.raises(ValueError):
        validate_request_budget(["A", "B", "C"], 2)
    validate_request_budget(["A", "B"], 2)


def test_chart_request_omits_count_to_request_whole_session():
    response = FakeResponse(
        _payload(),
        headers={
            "X-RateLimit-Limit-Month": "25000",
            "X-RateLimit-Remaining-Month": "24000",
        },
    )
    session = FakeSession(response)
    payload, meta = _request_chart(session, "BBCA", "zpi_secret_test_key")
    assert payload is not None
    assert meta["attempts"] == 1
    assert len(session.calls) == 1
    assert session.calls[0]["params"] == {"symbol": "BBCA"}
    assert "count" not in session.calls[0]["params"]
    assert meta["safe_headers"]["remaining_month"] == "24000"
