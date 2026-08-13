import pandas as pd
import pytest

from idx_trade.tradingview_admission import (
    evaluate_frozen_verdict,
    quarantine_corporate_action_rows,
    verify_input_hashes,
)


GATES = {
    "preferred_years": [2021, 2022, 2023, 2024, 2025, 2026],
    "fallback_years": [2022, 2023, 2024, 2025, 2026],
    "symbol_resolution_min": 0.95,
    "target_window_availability_min": 0.90,
    "target_window_availability_year_min": 0.85,
    "deep_reach_2021_min": 0.90,
    "certified_session_coverage_min": 0.90,
    "hlc_exact_overall_min": 0.95,
    "hlc_exact_year_min": 0.90,
    "volume_within_5pct_overall_min": 0.90,
    "volume_within_5pct_year_min": 0.80,
    "minimum_year_matched_rows": 10,
    "tv1d_reference_exact_min": 0.90,
    "tv1d_reference_year_min": 0.80,
    "tv60_open_exact_full_ohlcv_min": 0.90,
    "open_deterministic_convention_explained": False,
}


def metrics(*, open_rate=0.95, coverage_2021=0.95):
    years = [2021, 2022, 2023, 2024, 2025, 2026]
    coverage = {str(year): (coverage_2021 if year == 2021 else 0.95) for year in years}
    return {
        "deep_reach_2021_rate": 1.0,
        "structural_integrity": True,
        "target_window_availability_by_year": coverage,
        "certified_session_coverage_by_year": coverage,
        "hlc_exact_by_year": coverage,
        "tv1d_reference_exact_by_year": coverage,
        "volume_within_5pct_by_year": {str(year): {"matched_rows": 20, "rate": 0.90} for year in years},
        "ranges": {
            "2021_2026": {
                "symbol_resolution_rate": 0.99,
                "target_window_availability_rate": 0.95,
                "certified_session_coverage_rate": 0.95,
                "hlc_exact_rate": 0.96,
                "volume_within_5pct_rate": 0.92,
                "tv1d_reference_exact_rate": 0.95,
                "tv60_open_vs_tv1d_exact_rate": open_rate,
            },
            "2022_2026": {
                "symbol_resolution_rate": 0.99,
                "target_window_availability_rate": 0.95,
                "certified_session_coverage_rate": 0.95,
                "hlc_exact_rate": 0.96,
                "volume_within_5pct_rate": 0.92,
                "tv1d_reference_exact_rate": 0.95,
                "tv60_open_vs_tv1d_exact_rate": open_rate,
            },
        },
    }


def test_full_ohlcv_verdict_requires_open_gate():
    result = evaluate_frozen_verdict(metrics(open_rate=0.95), {"gates": GATES})
    assert result["verdict"] == "TRADINGVIEW_INTRADAY_ADMIT_2021_2026_FULL_OHLCV"


def test_path_only_verdict_preserves_open_blocker():
    result = evaluate_frozen_verdict(metrics(open_rate=0.62), {"gates": GATES})
    assert result["verdict"] == "TRADINGVIEW_INTRADAY_ADMIT_2021_2026_PRICE_PATH_ONLY"
    assert not result["open_full_ohlcv"]


def test_fallback_is_allowed_only_when_2021_is_the_failed_year():
    result = evaluate_frozen_verdict(metrics(open_rate=0.62, coverage_2021=0.50), {"gates": GATES})
    assert result["only_2021_failure"]
    assert result["verdict"] == "TRADINGVIEW_INTRADAY_ADMIT_2022_2026_PRICE_PATH_ONLY_2021_BLOCKED"


def test_non_2021_gate_failure_rejects_instead_of_rescuing():
    values = metrics()
    values["target_window_availability_by_year"]["2024"] = 0.50
    result = evaluate_frozen_verdict(values, {"gates": GATES})
    assert result["verdict"] == "TRADINGVIEW_INTRADAY_ADMISSION_REJECTED"


def test_volume_year_gate_uses_sufficient_rows_threshold():
    values = metrics()
    values["volume_within_5pct_by_year"]["2023"] = {"matched_rows": 5, "rate": 0.0}
    result = evaluate_frozen_verdict(values, {"gates": GATES})
    assert result["preferred_gate_pass"]


def test_corporate_action_quarantine_requires_external_key():
    frame = pd.DataFrame({"ticker": ["DSSA", "DSSA"], "session_date": ["2024-07-01", "2024-07-02"], "volume_ratio": [1.0, 0.5]})
    result = quarantine_corporate_action_rows(frame, {("DSSA", "2024-07-01")})
    assert result["corporate_action_quarantined"].tolist() == [True, False]


def test_input_hashes_fail_closed():
    with pytest.raises(ValueError, match="input hash mismatch"):
        verify_input_hashes({"panel": "expected"}, {"panel": "observed"})
