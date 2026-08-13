from datetime import date

import pandas as pd

from idx_trade.tradingview_remediation import (
    classify_observation,
    listing_aware_denominators,
    pagination_boundary,
    three_way_reconciliation,
    volume_ratio_diagnostics,
)


def test_status_classification_keeps_empty_completion_distinct_from_timeout():
    assert classify_observation(periods=0, event_trace=["series_completed"]) == "SERIES_COMPLETED_EMPTY"
    assert classify_observation(periods=0, event_trace=[], timed_out=True) == "TRANSPORT_TIMEOUT"
    assert classify_observation(periods=0, event_trace=["update_empty"], timed_out=True) == "UNCLASSIFIED_NO_DATA"
    assert classify_observation(periods=0, event_trace=["symbol_error"], errors=["invalid symbol"]) == "SYMBOL_ERROR"


def test_listing_aware_denominator_does_not_count_pre_listing_pair():
    requests = pd.DataFrame([
        {"ticker": "NEW", "year": 2018, "start": "2018-07-02", "end": "2018-07-06"},
        {"ticker": "NEW", "year": 2026, "start": "2026-07-01", "end": "2026-07-07"},
    ])
    master = pd.DataFrame([{"ticker": "NEW", "listed_from": "2025-01-01", "listed_to": None}])
    result = listing_aware_denominators(requests, master, None)
    assert result == {
        "requested_ticker_era_pairs": 2,
        "known_listed_ticker_era_pairs": 1,
        "certified_session_ticker_era_pairs": None,
    }


def test_volume_diagnostics_exposes_tolerance_without_rescaling():
    result = volume_ratio_diagnostics([0.99, 1.0, 1.01, 0.1, 10.0])
    assert result["count"] == 5
    assert result["within_tolerance_counts"]["within_0.010"] == 3
    assert result["multiplicative_cluster_counts"]["0.1"] == 1
    assert result["multiplicative_cluster_counts"]["10.0"] == 1


def test_three_way_reconciliation_preserves_source_disagreement():
    keys = {"ticker": ["AAA"], "session_date": ["2026-07-01"]}
    tv60 = pd.DataFrame({**keys, "open": [10], "high": [12], "low": [9], "close": [11], "volume": [100]})
    tv1d = pd.DataFrame({"ticker": ["AAA"], "session_date": ["2026-07-01"], "open": [10], "high": [12], "low": [9], "close": [11], "volume": [101]})
    canonical = pd.DataFrame({**keys, "open": [10], "high": [12], "low": [9], "close": [11], "volume": [100]})
    result = three_way_reconciliation(tv60, tv1d, canonical, tolerance=0.05)
    assert result.loc[0, "three_way_class"] == "TV60_APPROX_TV1D_APPROX_CANONICAL"


def test_three_way_reconciliation_deduplicates_sources_and_ignores_unrelated_panel_rows():
    keys = {"ticker": ["AAA", "AAA"], "session_date": ["2026-07-01", "2026-07-01"]}
    tv60 = pd.DataFrame({**keys, "open": [10, 10], "high": [12, 12], "low": [9, 9], "close": [11, 11], "volume": [100, 100]})
    tv1d = pd.DataFrame({"ticker": ["AAA"], "session_date": ["2026-07-01"], "open": [10], "high": [12], "low": [9], "close": [11], "volume": [101]})
    canonical = pd.DataFrame({
        "ticker": ["AAA", "UNRELATED"], "date": ["2026-07-01", "2026-07-01"],
        "open": [10, 99], "high": [12, 100], "low": [9, 98], "close": [11, 99], "volume": [100, 99],
    })
    result = three_way_reconciliation(tv60, tv1d, canonical, tolerance=0.05)
    assert len(result) == 1
    assert result.loc[0, "ticker"] == "AAA"


def test_three_way_reconciliation_does_not_call_missing_tv1d_a_mismatch():
    provider = pd.DataFrame({"ticker": ["AAA"], "session_date": ["2026-07-01"], "open": [10], "high": [12], "low": [9], "close": [11], "volume": [100]})
    canonical = pd.DataFrame({"ticker": ["AAA"], "date": ["2026-07-01"], "open": [10], "high": [12], "low": [9], "close": [11], "volume": [100]})
    result = three_way_reconciliation(provider, pd.DataFrame(), canonical)
    assert result.loc[0, "three_way_class"] == "TV1D_NO_ROW"


def test_pagination_boundary_requires_observable_stop_reason():
    assert pagination_boundary({"steps": [{"extended": True, "reason": "extended"}], "completion_reason": "max_steps"})["deterministic_stop"]
    assert not pagination_boundary({"steps": [], "completion_reason": None})["deterministic_stop"]
