from datetime import date, datetime, timezone

import pandas as pd

from idx_trade.investing_admission import (
    PILOT_TICKERS,
    PilotWindow,
    aggregate_daily,
    compare_daily,
    epoch_bounds_for_local_window,
    normalize_history_payload,
)


def _payload(*, epoch=1782871200, open_value=100.0):
    return {"s": "ok", "t": [epoch, epoch + 3600], "o": [open_value, 101.0],
            "h": [102.0, 103.0], "l": [99.0, 100.0], "c": [101.0, 102.0], "v": [10.0, 20.0]}


def test_sample_is_fixed_and_unique():
    assert len(PILOT_TICKERS) == 50
    assert len(set(PILOT_TICKERS)) == 50
    assert PILOT_TICKERS[:3] == ("BBCA", "BBRI", "BMRI")


def test_local_request_bounds_include_wib_opening_boundary():
    window = PilotWindow("x", date(2026, 7, 1), date(2026, 7, 1))
    start, end = epoch_bounds_for_local_window(window)
    assert datetime.fromtimestamp(start, timezone.utc).isoformat() == "2026-06-30T17:00:00+00:00"
    assert datetime.fromtimestamp(end, timezone.utc).isoformat() == "2026-07-01T16:59:59+00:00"


def test_normalization_rejects_off_session_and_duplicate_without_shifting():
    # 2026-07-01 09:00 WIB; the second row is an exact duplicate timestamp.
    payload = _payload(epoch=1782871200)
    payload["t"] = [1782871200, 1782871200]
    frame, diag = normalize_history_payload(payload, ticker="BBCA", pair_id="1", window=PilotWindow("x", date(2026, 7, 1), date(2026, 7, 1)), session_dates={date(2026, 7, 1)})
    assert len(frame) == 1
    assert diag["duplicate_rows"] == 1
    assert frame.iloc[0]["raw_epoch"] == 1782871200
    assert "09:00:00+07:00" in frame.iloc[0]["timestamp_wib"]


def test_normalization_rejects_malformed_and_invalid_ohlcv():
    payload = {"s": "ok", "t": [1782871200], "o": [0], "h": [1], "l": [2], "c": [1], "v": [1]}
    frame, diag = normalize_history_payload(payload, ticker="X", pair_id="1", window=PilotWindow("x", date(2026, 7, 1), date(2026, 7, 1)), session_dates={date(2026, 7, 1)})
    assert frame.empty
    assert diag["invalid_ohlcv_rows"] == 1


def test_aggregate_and_compare_daily_are_non_mutating():
    payload = _payload()
    frame, _ = normalize_history_payload(payload, ticker="BBCA", pair_id="1", window=PilotWindow("x", date(2026, 7, 1), date(2026, 7, 1)), session_dates={date(2026, 7, 1)})
    daily = aggregate_daily(frame)
    canonical = pd.DataFrame({"ticker": ["BBCA"], "date": ["2026-07-01"], "open": [100.0], "high": [103.0], "low": [99.0], "close": [102.0], "volume": [30.0]})
    result = compare_daily(daily, canonical)
    assert result.iloc[0]["hlc_exact"]
    assert result.iloc[0]["volume_exact"]
    assert result.iloc[0]["open_exact"]
    assert daily.iloc[0]["volume"] == 30.0


def test_non_ok_provider_status_is_explicit():
    frame, diag = normalize_history_payload({"s": "no_data"}, ticker="X", pair_id="1", window=PilotWindow("x", date(2026, 7, 1), date(2026, 7, 1)), session_dates={date(2026, 7, 1)})
    assert frame.empty
    assert diag["provider_status"] == "no_data"


def test_non_object_provider_payload_is_quarantined_not_crashing():
    frame, diag = normalize_history_payload(403, ticker="X", pair_id="1", window=PilotWindow("x", date(2026, 7, 1), date(2026, 7, 1)), session_dates={date(2026, 7, 1)})
    assert frame.empty
    assert diag["provider_status"] == "invalid_payload"
    assert diag["malformed_rows"] == 1
