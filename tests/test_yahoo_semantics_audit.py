import pandas as pd

from idx_trade.tier2_open_audit import audit_provider_rows
from idx_trade.yahoo_semantics_audit import (
    authoritative_cumulative_split_factor,
    reconstruct_split_scale_rows,
    select_yahoo_semantics_sample,
    yahoo_sample_manifest_sha256,
)


def _broad_candidates():
    rows = []
    split_tickers = [f"S{index:03d}" for index in range(52)]
    non_split_tickers = [f"N{index:03d}" for index in range(100)]
    for ticker in [*split_tickers, *non_split_tickers]:
        split = ticker.startswith("S")
        for offset, role in enumerate(
            ("KNOWN_EXISTING_OPEN", "MISSING_OPEN_WILDAN_ROW", "MISSING_OPEN_WILDAN_NO_ROW")
        ):
            rows.append(
                {
                    "sample_id": "",
                    "sample_role": role,
                    "ticker": ticker,
                    "date": pd.Timestamp("2022-01-03") + pd.Timedelta(days=offset * 700),
                    "panel_open": 100.0 if role == "KNOWN_EXISTING_OPEN" else None,
                    "panel_high": 110.0,
                    "panel_low": 90.0,
                    "panel_close": 105.0,
                    "wildan_diagnostic": (
                        "SECONDARY_ROW_UNAVAILABLE"
                        if role == "MISSING_OPEN_WILDAN_NO_ROW"
                        else "SECONDARY_OHLC_INVALID"
                        if role != "KNOWN_EXISTING_OPEN"
                        else None
                    ),
                    "edge_case_tags": "",
                    "split_stratum": "SPLIT_EVIDENCE" if split else "NON_SPLIT",
                    "split_factor_verified": split,
                    "date_stratum": ("EARLY", "MID", "LATE")[offset],
                }
            )
    return pd.DataFrame(rows)


def _actions(tickers=("S000",)):
    return pd.DataFrame(
        {
            "ticker": list(tickers),
            "action": ["stockSplit"] * len(tickers),
            "effective_date": [pd.Timestamp("2023-01-01")] * len(tickers),
            "ratio": [2.0] * len(tickers),
        }
    )


def test_broad_sample_is_deterministic_and_preserves_required_strata():
    candidates = _broad_candidates()
    first = select_yahoo_semantics_sample(
        candidates,
        _actions(tuple(f"S{index:03d}" for index in range(52))),
        target_size=300,
        minimum_unique_tickers=120,
        minimum_split_tickers=30,
        minimum_non_split_tickers=80,
        minimum_existing=100,
        minimum_wildan_row=100,
        minimum_wildan_no_row=25,
    )
    second = select_yahoo_semantics_sample(
        candidates,
        _actions(tuple(f"S{index:03d}" for index in range(52))),
        target_size=300,
        minimum_unique_tickers=120,
        minimum_split_tickers=30,
        minimum_non_split_tickers=80,
        minimum_existing=100,
        minimum_wildan_row=100,
        minimum_wildan_no_row=25,
    )
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 300
    assert first["ticker"].nunique() >= 120
    assert first.loc[first["split_stratum"].eq("SPLIT_EVIDENCE"), "ticker"].nunique() >= 30
    assert first.loc[first["split_stratum"].eq("NON_SPLIT"), "ticker"].nunique() >= 80
    assert first["date_stratum"].value_counts().to_dict().keys() >= {"EARLY", "MID", "LATE"}
    assert yahoo_sample_manifest_sha256(first) == yahoo_sample_manifest_sha256(second)


def _split_sample():
    return pd.DataFrame(
        [
            {
                "sample_id": "YH-0001",
                "sample_role": "MISSING_OPEN_WILDAN_ROW",
                "ticker": "S000",
                "date": pd.Timestamp("2022-01-03"),
                "panel_open": None,
                "panel_high": 220.0,
                "panel_low": 180.0,
                "panel_close": 210.0,
                "wildan_diagnostic": "SECONDARY_OHLC_INVALID",
                "edge_case_tags": "",
                "split_stratum": "SPLIT_EVIDENCE",
                "split_factor_verified": True,
                "date_stratum": "EARLY",
            }
        ]
    )


def _split_provider():
    return pd.DataFrame(
        [
            {
                "ticker": "S000",
                "date": pd.Timestamp("2022-01-03"),
                "raw_open": 100.0,
                "raw_high": 110.0,
                "raw_low": 90.0,
                "raw_close": 105.0,
                "raw_volume": 1000.0,
            }
        ]
    )


def test_only_independent_factor_can_reconstruct_all_hlc_and_open():
    sample = _split_sample()
    provider_audit, _ = audit_provider_rows(sample, _split_provider(), "YAHOO")
    audit, summary = reconstruct_split_scale_rows(sample, provider_audit, _actions())
    assert authoritative_cumulative_split_factor("S000", "2022-01-03", _actions()) == (
        2.0,
        "OFFICIAL_CUMULATIVE_FACTOR",
    )
    assert bool(audit.loc[0, "reconstructed_hlc_exact"])
    assert audit.loc[0, "reconstructed_admission_status"] == "SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE"
    assert summary["reconstructed_missing_open_admissible_count"] == 1


def test_mismatch_without_verified_factor_stays_rejected():
    sample = _split_sample().assign(ticker="UNKNOWN")
    provider = _split_provider().assign(ticker="UNKNOWN")
    provider_audit, _ = audit_provider_rows(sample, provider, "YAHOO")
    audit, summary = reconstruct_split_scale_rows(sample, provider_audit, pd.DataFrame(columns=["ticker", "effective_date", "ratio"]))
    assert not bool(audit.loc[0, "reconstructed_hlc_exact"])
    assert audit.loc[0, "reconstructed_admission_status"] == "REJECTED"
    assert summary["reconstructed_missing_open_admissible_count"] == 0
