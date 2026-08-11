import pandas as pd

from idx_trade.zapi_tradingview_resume import (
    EXPECTED_PANEL_SHA256,
    _merge_rows,
    _plan_from_headers,
    _selected_resume_tickers,
    _ticker_hash,
    _arbitration,
    _parse_payload,
)


def test_resume_selection_is_exactly_rate_limited_and_deterministic():
    status = pd.DataFrame({"ticker": ["BBCA", "MAIN", "FREN", "MASA"], "status": ["SUCCESS", "RATE_LIMITED", "REQUEST_ERROR", "RATE_LIMITED"]})
    selected = _selected_resume_tickers(status)
    assert selected == ["MAIN", "MASA"]
    assert _ticker_hash(selected) == _ticker_hash(["MAIN", "MASA"])


def test_pro_quota_fingerprint_is_not_ultra_or_free():
    assert _plan_from_headers({"rate_limit_month": "25000", "rate_limit_minute": "2000"}) == "PRO"
    assert _plan_from_headers({"rate_limit_month": "200000", "rate_limit_minute": "5000"}) == "ULTRA"


def test_tradingview_payload_requires_exact_identity_and_preserves_contract():
    frame, status = _parse_payload(
        "BBCA",
        {"content": {"symbol": "IDX:BBCA", "exchange": "IDX", "market": "indonesia", "candles": [{"date": "2026-06-22T02:00:00Z", "open": 6400, "high": 6500, "low": 6300, "close": 6450}]}},
        "PRO_RESUME",
    )
    assert status["status"] == "SUCCESS"
    assert frame.iloc[0]["date"] == pd.Timestamp("2026-06-22")
    assert frame.iloc[0]["provenance"] == "PRO_RESUME"


def test_tradingview_payload_rejects_wrong_symbol():
    frame, status = _parse_payload(
        "BBCA",
        {"content": {"symbol": "IDX:BBRI", "exchange": "IDX", "market": "indonesia", "candles": []}},
        "PRO_RESUME",
    )
    assert frame.empty
    assert status["status"] == "IDENTITY_OR_PAYLOAD_ERROR"


def test_combined_rows_deduplicate_by_provider_ticker_date_keep_original():
    prior = pd.DataFrame({"ticker": ["BBCA"], "date": [pd.Timestamp("2026-06-22")], "raw_open": [1], "provenance": ["ORIGINAL_RUN"]})
    resume = pd.DataFrame({"ticker": ["BBCA", "MAIN"], "date": [pd.Timestamp("2026-06-22"), pd.Timestamp("2026-06-22")], "raw_open": [2, 3], "provenance": ["PRO_RESUME", "PRO_RESUME"]})
    combined = _merge_rows(prior, resume)
    assert len(combined) == 2
    assert combined.loc[combined.ticker.eq("BBCA"), "raw_open"].iloc[0] == 1


def test_arbitration_uses_canonical_yahoo_columns_without_suffix_assumptions():
    sample = pd.DataFrame({"sample_id": ["Z2-001"], "yahoo_raw_high": [2], "yahoo_raw_low": [1], "yahoo_raw_close": [2]})
    audit = pd.DataFrame({"sample_id": ["Z2-001"], "diagnostic": ["OK"], "hlc_exact": [True], "raw_high": [2], "raw_low": [1], "raw_close": [2]})
    assert _arbitration(sample, audit) == {"SUPPORTS_CERTIFIED_PANEL_AND_YAHOO": 1}


def test_immutable_panel_hash_constant_is_frozen():
    assert EXPECTED_PANEL_SHA256 == "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
