import pandas as pd

from idx_trade.yahoo_open_census import (
    apply_verified_split_reconstruction,
    build_cache_manifest,
    build_derivative_candidate,
    build_full_direct_audit,
    fetch_ticker_cached,
)


def _panel():
    return pd.DataFrame(
        [
            {"ticker": "AAA", "date": "2022-01-03", "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0, "volume": 1000},
            {"ticker": "AAA", "date": "2022-01-04", "open": None, "high": 120.0, "low": 100.0, "close": 115.0, "volume": 1100},
            {"ticker": "BBB", "date": "2022-01-03", "open": None, "high": 220.0, "low": 180.0, "close": 210.0, "volume": 900},
            {"ticker": "CCC", "date": "2022-01-03", "open": None, "high": 330.0, "low": 270.0, "close": 315.0, "volume": 800},
        ]
    )


def _provider():
    return pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "date": pd.Timestamp("2022-01-03"),
                "raw_open": 100.0,
                "raw_high": 110.0,
                "raw_low": 90.0,
                "raw_close": 105.0,
                "raw_volume": 1000.0,
                "vendor_adj_close": 1.0,
                "stock_splits": 0.0,
                "dividends": 50.0,
            },
            {
                "ticker": "AAA",
                "date": pd.Timestamp("2022-01-04"),
                "raw_open": 110.0,
                "raw_high": 120.0,
                "raw_low": 100.0,
                "raw_close": 115.0,
                "raw_volume": 1100.0,
                "vendor_adj_close": 2.0,
                "stock_splits": 0.0,
                "dividends": 0.0,
            },
            {
                "ticker": "BBB",
                "date": pd.Timestamp("2022-01-03"),
                "raw_open": 100.0,
                "raw_high": 110.0,
                "raw_low": 90.0,
                "raw_close": 105.0,
                "raw_volume": 900.0,
                "vendor_adj_close": 105.0,
                "stock_splits": 0.0,
                "dividends": 0.0,
            },
            {
                "ticker": "CCC",
                "date": pd.Timestamp("2022-01-03"),
                "raw_open": 300.0,
                "raw_high": 331.0,
                "raw_low": 270.0,
                "raw_close": 315.0,
                "raw_volume": 800.0,
                "vendor_adj_close": 315.0,
                "stock_splits": 0.0,
                "dividends": 0.0,
            },
        ]
    )


def _actions():
    return pd.DataFrame(
        [
            {
                "ticker": "BBB",
                "action": "stockSplit",
                "effective_date": pd.Timestamp("2023-01-01"),
                "ratio": 2.0,
            }
        ]
    )


def test_direct_gate_uses_raw_hlc_and_ignores_adjusted_dividend_fields():
    audit, summary = build_full_direct_audit(_panel(), _provider())
    known = audit[(audit["ticker"] == "AAA") & (audit["date"] == pd.Timestamp("2022-01-03"))].iloc[0]
    direct = audit[(audit["ticker"] == "AAA") & (audit["date"] == pd.Timestamp("2022-01-04"))].iloc[0]
    mismatch = audit[audit["ticker"] == "CCC"].iloc[0]
    assert bool(known["known_open_exact"])
    assert known["direct_diagnostic"] == "EXISTING_OPEN_PRESERVED_EXACT"
    assert bool(direct["direct_admissible"])
    assert direct["direct_candidate_open"] == 110.0
    assert not bool(mismatch["direct_admissible"])
    assert mismatch["direct_diagnostic"] == "HLC_MISMATCH_HIGH"
    assert summary["direct_missing_open_accepted"] == 1


def test_verified_split_factor_recovers_only_exact_transformed_hlc():
    direct, _ = build_full_direct_audit(_panel(), _provider())
    audit, summary = apply_verified_split_reconstruction(direct, _actions())
    bbb = audit[audit["ticker"] == "BBB"].iloc[0]
    ccc = audit[audit["ticker"] == "CCC"].iloc[0]
    assert bbb["split_factor"] == 2.0
    assert bool(bbb["split_reconstructed_hlc_exact"])
    assert bool(bbb["split_admissible"])
    assert bbb["split_reconstructed_open"] == 200.0
    assert not bool(ccc["split_admissible"])
    assert summary["reconstructed_missing_open_accepted"] == 1


def test_derivative_preserves_existing_open_and_records_provenance():
    direct, _ = build_full_direct_audit(_panel(), _provider())
    audit, _ = apply_verified_split_reconstruction(direct, _actions())
    derivative, provenance, summary = build_derivative_candidate(audit)
    aaa_known = derivative[(derivative["ticker"] == "AAA") & (derivative["date"] == pd.Timestamp("2022-01-03"))].iloc[0]
    aaa_missing = derivative[(derivative["ticker"] == "AAA") & (derivative["date"] == pd.Timestamp("2022-01-04"))].iloc[0]
    bbb = derivative[derivative["ticker"] == "BBB"].iloc[0]
    assert aaa_known["open"] == 100.0
    assert aaa_missing["open"] == 110.0
    assert bbb["open"] == 200.0
    assert summary == {"direct_fills": 1, "split_fills": 1, "total_fills": 2, "initial_null_open": 3, "final_null_open": 1}
    classes = provenance.set_index(["ticker", "date"])["open_evidence_class"]
    assert classes.loc[("AAA", pd.Timestamp("2022-01-03"))] == "EXISTING_IMMUTABLE"
    assert classes.loc[("AAA", pd.Timestamp("2022-01-04"))] == "DIRECT_RAW_HLC_EXACT"
    assert classes.loc[("BBB", pd.Timestamp("2022-01-03"))] == "SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE"


def _canonical_frame(ticker="AAA"):
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2022-01-03"),
                "ticker": ticker,
                "raw_open": 100.0,
                "raw_high": 110.0,
                "raw_low": 90.0,
                "raw_close": 105.0,
                "raw_volume": 1000.0,
                "vendor_adj_close": 1.0,
                "vendor_total_return_factor": 0.01,
                "vendor_adjustment_change": False,
                "explicit_split_event": False,
                "explicit_dividend_event": False,
                "explicit_corporate_action": False,
                "corporate_action_recent": False,
                "dividends": 0.0,
                "stock_splits": 0.0,
            }
        ]
    )


def test_cache_resume_is_idempotent(tmp_path):
    calls = []

    def fake_download(tickers, start, end, threads):
        calls.append((tickers, start, end, threads))
        return {"AAA": _canonical_frame()}

    first = fetch_ticker_cached(
        "AAA",
        start="2021-04-29",
        end_inclusive="2026-07-31",
        cache_root=tmp_path,
        download_fn=fake_download,
        max_attempts=1,
        backoff_seconds=0,
    )
    second = fetch_ticker_cached(
        "AAA",
        start="2021-04-29",
        end_inclusive="2026-07-31",
        cache_root=tmp_path,
        download_fn=fake_download,
        max_attempts=1,
        backoff_seconds=0,
    )
    assert first["status"] == "SUCCESS"
    assert not first["cache_hit"]
    assert second["cache_hit"]
    assert len(calls) == 1
    pd.testing.assert_frame_equal(first["frame"], second["frame"])


def test_provider_error_is_preserved_and_not_cached_as_success(tmp_path):
    calls = []

    def failing_download(tickers, start, end, threads):
        calls.append(1)
        raise RuntimeError("provider unavailable")

    result = fetch_ticker_cached(
        "ERR",
        start="2021-04-29",
        end_inclusive="2026-07-31",
        cache_root=tmp_path,
        download_fn=failing_download,
        max_attempts=2,
        backoff_seconds=0,
    )
    assert result["status"] == "ERROR"
    assert result["network_attempts"] == 2
    assert result["retries"] == 1
    assert len(calls) == 2
    assert "provider unavailable" in " ".join(result["metadata"]["provider_errors"])


def test_cache_manifest_is_ticker_sorted(tmp_path):
    for ticker in ("BBB", "AAA"):
        (tmp_path / f"{ticker}.json").write_text("{}", encoding="utf-8")
    statuses = pd.DataFrame(
        [
            {"ticker": "BBB", "status": "ERROR", "parquet_sha256": None},
            {"ticker": "AAA", "status": "NO_DATA_COMPLETE", "parquet_sha256": None},
        ]
    )
    manifest = build_cache_manifest(tmp_path, statuses)
    assert [entry["ticker"] for entry in manifest["entries"]] == ["AAA", "BBB"]
