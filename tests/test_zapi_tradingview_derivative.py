from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.zapi_tradingview_derivative import apply_tradingview_candidates


def _inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    panel = pd.DataFrame(
        [
            {"ticker": "AAA", "date": "2024-01-02", "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 100},
            {"ticker": "AAA", "date": "2024-01-03", "open": None, "high": 13.0, "low": 10.0, "close": 12.0, "volume": 110},
        ]
    )
    provenance = pd.DataFrame(
        [
            {"ticker": "AAA", "date": "2024-01-02", "open_source": "YAHOO_YFINANCE", "open_evidence_class": "DIRECT_RAW_HLC_EXACT", "validation_status": "ACCEPTED", "source_cache_ref": "yahoo.parquet"},
            {"ticker": "AAA", "date": "2024-01-03", "open_source": None, "open_evidence_class": None, "validation_status": "UNRESOLVED", "source_cache_ref": None},
        ]
    )
    candidates = pd.DataFrame(
        [
            {
                "sample_id": "RES-00001",
                "ticker": "AAA",
                "date": "2024-01-03",
                "tradingview_open": 11.0,
                "tradingview_high": 13.0,
                "tradingview_low": 10.0,
                "tradingview_close": 12.0,
                "tradingview_provenance": "TARGETED_CENSUS",
                "tradingview_source_ref": "zapi://tradingview/chart/IDX:AAA",
                "provider_class": "TV_RECOVERY_CANDIDATE",
                "residual_problem_class": "NO_PROVIDER_ROW",
            }
        ]
    )
    return panel, provenance, candidates


def test_application_fills_only_null_open_and_adds_tradingview_provenance() -> None:
    panel, provenance, candidates = _inputs()
    derivative, derivative_provenance, summary = apply_tradingview_candidates(
        panel, provenance, candidates, expected_candidate_count=1
    )
    assert derivative.loc[0, "open"] == 10.0
    assert derivative.loc[1, "open"] == 11.0
    assert summary["additional_null_open_values_filled"] == 1
    assert summary["existing_non_null_open_overwrites"] == 0
    assert derivative_provenance.loc[0, "open_source"] == "YAHOO_YFINANCE"
    assert derivative_provenance.loc[1, "open_source"] == "ZAPI_TRADINGVIEW"
    assert derivative_provenance.loc[1, "tradingview_provenance"] == "TARGETED_CENSUS"


def test_application_rejects_candidate_that_would_overwrite_existing_open() -> None:
    panel, provenance, candidates = _inputs()
    candidates = candidates.copy()
    candidates["date"] = pd.Timestamp("2024-01-02")
    with pytest.raises(RuntimeError, match="overwrite"):
        apply_tradingview_candidates(panel, provenance, candidates)


def test_application_rejects_duplicate_candidate_keys() -> None:
    panel, provenance, candidates = _inputs()
    candidates = pd.concat([candidates, candidates], ignore_index=True)
    with pytest.raises(RuntimeError, match="one-to-one"):
        apply_tradingview_candidates(panel, provenance, candidates)
