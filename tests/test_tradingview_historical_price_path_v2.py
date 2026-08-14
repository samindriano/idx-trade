from __future__ import annotations

from pathlib import Path

import pandas as pd

from idx_trade.tradingview_price_path_v2 import (
    build_expected_sessions,
    build_request_manifest,
    classify_official_activity,
    evaluate_gates,
    normalize_response,
)


def _universe() -> pd.DataFrame:
    return pd.DataFrame([{"security_id": "IDX:AAA:20200101", "ticker": "AAA", "company_name": "A", "listed_from": pd.Timestamp("2020-01-01"), "listed_to": pd.NaT, "source": "test", "scope": "COMMON_STOCK"}])


def test_expected_sessions_respect_listing_boundary() -> None:
    sessions = pd.DataFrame({"date": pd.to_datetime(["2019-12-31", "2020-01-02"])})
    result = build_expected_sessions(_universe(), sessions)
    assert result["session_date"].tolist() == ["2020-01-02"]


def test_official_activity_does_not_turn_missing_into_no_trade(tmp_path: Path) -> None:
    expected = pd.DataFrame([{"ticker": "AAA", "session_date": "2020-01-02"}, {"ticker": "BBB", "session_date": "2020-01-02"}])
    session = tmp_path / "sessions" / "2020-01-02"
    session.mkdir(parents=True)
    (session / "stock_summary.raw.json").write_text('{"data":[{"StockCode":"AAA","Volume":0,"Value":0,"Frequency":0}]}', encoding="utf-8")
    result = classify_official_activity(expected, tmp_path)
    assert result.set_index("ticker").loc["AAA", "activity_state"] == "NO_TRADE"
    assert result.set_index("ticker").loc["BBB", "activity_state"] == "UNKNOWN"


def test_positive_any_regular_activity_is_active(tmp_path: Path) -> None:
    expected = pd.DataFrame([{"ticker": "AAA", "session_date": "2020-01-02"}])
    session = tmp_path / "sessions" / "2020-01-02"
    session.mkdir(parents=True)
    (session / "stock_summary.raw.json").write_text('{"data":[{"StockCode":"AAA","Volume":0,"Value":2,"Frequency":0}]}', encoding="utf-8")
    assert classify_official_activity(expected, tmp_path).iloc[0]["activity_state"] == "ACTIVE"


def test_normalize_rejects_duplicate_and_preopen_inside_window() -> None:
    request = {"ticker": "AAA", "security_id": "x", "request_index": 1, "session": "regular", "required_start": "2020-01-02", "required_end": "2020-01-02"}
    epoch = int(pd.Timestamp("2020-01-02 01:00:00+00:00").timestamp())
    period = {"time": epoch, "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1}
    frame, diag = normalize_response({"periods": [period, period]}, request, {"2020-01-02"})
    assert len(frame) == 1
    assert diag["duplicate_rows"] == 1
    assert diag["extended_preopen_contamination_rows"] == 1
    assert not frame.iloc[0]["session_admissible"]


def test_normalize_preserves_raw_values_and_admits_regular_bar() -> None:
    request = {"ticker": "AAA", "security_id": "x", "request_index": 1, "session": "regular", "required_start": "2020-01-02", "required_end": "2020-01-02"}
    epoch = int(pd.Timestamp("2020-01-02 03:00:00+00:00").timestamp())
    frame, diag = normalize_response({"periods": [{"time": epoch, "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 4}]}, request, {"2020-01-02"})
    assert diag["invalid_ohlcv_rows"] == 0
    assert frame.iloc[0]["open"] == 10
    assert frame.iloc[0]["session_admissible"]


def test_request_manifest_is_deterministic_and_frozen_contract() -> None:
    sessions = pd.DataFrame({"date": pd.to_datetime(["2020-01-02"])})
    config = {"window": {"start": "2020-01-01", "end": "2020-01-03"}, "provider": {"server": "prodata", "timeframe": "60", "session": "regular", "adjustment": "none"}, "acquisition": {"initial_range": 500, "fetch_more_steps": 10, "fetch_more_batch": 5, "fetch_more_wait_ms": 8000, "timeout_ms": 25000}}
    first = build_request_manifest(_universe(), sessions, config)
    second = build_request_manifest(_universe(), sessions, config)
    pd.testing.assert_frame_equal(first, second)
    assert first.iloc[0]["symbol"] == "IDX:AAA"
    assert first.iloc[0]["server"] == "prodata"


def test_gate_requires_zero_unknown_and_provider_miss() -> None:
    expected = pd.DataFrame([{"ticker": "AAA", "session_date": "2020-01-02"}])
    activity = pd.DataFrame([{"ticker": "AAA", "session_date": "2020-01-02", "activity_state": "ACTIVE"}])
    bars = pd.DataFrame(columns=["ticker", "session_date", "session_admissible"])
    diagnostics = pd.DataFrame([{"malformed_rows": 0, "duplicate_rows": 0, "session_date_leakage_rows": 0, "extended_preopen_contamination_rows": 0}])
    config = {"gates": {"active_coverage_overall": 0.98, "active_coverage_year": 0.95, "unknown_activity_rate_max": 0.005, "hlc_exact_overall": 0.95, "hlc_exact_year": 0.90, "volume_within_5_overall": 0.90, "volume_within_5_year": 0.80}}
    result = evaluate_gates(expected, activity, bars, diagnostics, {"hlc_exact_rate": 1.0, "volume_within_5_rate": 1.0, "by_year": {"2020": {"hlc_exact_rate": 1.0, "volume_within_5_rate": 1.0}}}, config)
    assert result["true_provider_misses"] == 1
    assert result["all_gates_pass"] is False
