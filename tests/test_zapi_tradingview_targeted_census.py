from __future__ import annotations

import pandas as pd

from idx_trade.zapi_tradingview_targeted_census import (
    FORBIDDEN_ERROR_TICKERS,
    _audit_input_from_residual,
    _exact_coverage,
    _metrics,
    build_network_tickers,
)
from idx_trade.zapi_alt_open_audit import _empty_provider_frame


def _residual(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "census_id": f"RES-{index:05d}",
                "ticker": ticker,
                "date": pd.Timestamp(date),
                "problem_class": problem,
                "panel_high": 10.0,
                "panel_low": 1.0,
                "panel_close": 5.0,
                "yahoo_raw_high": 11.0,
                "yahoo_raw_low": 1.0,
                "yahoo_raw_close": 5.0,
            }
            for index, (ticker, date, problem) in enumerate(rows, 1)
        ]
    )


def test_network_tickers_exclude_preserved_success_and_forbidden_errors() -> None:
    detail = _residual([("DONE", "2024-01-02", "NO_PROVIDER_ROW"), ("NEW", "2024-01-02", "NO_PROVIDER_ROW"), ("FREN", "2024-01-02", "PROVIDER_ERROR_OR_SYMBOL_RESOLUTION_FAILURE")])
    status = pd.DataFrame({"ticker": ["DONE", *sorted(FORBIDDEN_ERROR_TICKERS)], "status": ["SUCCESS", *(["REQUEST_ERROR"] * len(FORBIDDEN_ERROR_TICKERS))]})
    requested, metadata = build_network_tickers(detail, status)
    assert requested == ["NEW"]
    assert metadata["prior_success_tickers_refetched"] == 0


def test_exact_coverage_is_ticker_date_exact() -> None:
    detail = _residual([("A", "2024-01-02", "NO_PROVIDER_ROW"), ("A", "2024-01-03", "NO_PROVIDER_ROW")])
    provider = pd.DataFrame({"ticker": ["A"], "date": [pd.Timestamp("2024-01-02")], "raw_open": [2.0], "raw_high": [10.0], "raw_low": [1.0], "raw_close": [5.0]})
    coverage = _exact_coverage(detail, provider)
    assert coverage.tolist() == [True, False]


def test_audit_input_marks_all_census_rows_as_missing_open() -> None:
    data = _residual([("A", "2024-01-02", "NO_PROVIDER_ROW")])
    audit_input = _audit_input_from_residual(data)
    assert audit_input.loc[0, "sample_role"] == "AUTHORIZED_NON_CA_RESIDUAL"
    assert pd.isna(audit_input.loc[0, "panel_open"])


def test_empty_provider_is_supported_for_offline_reuse() -> None:
    assert _empty_provider_frame().empty


def test_unresolved_breakdown_is_aggregated_by_reason_class_and_year() -> None:
    detail = _residual(
        [
            ("A", "2021-01-02", "NO_PROVIDER_ROW"),
            ("B", "2022-01-03", "NO_PROVIDER_ROW"),
        ]
    )
    detail["residual_reason"] = "NO_PROVIDER_ROW"
    audit = pd.DataFrame(
        {
            "sample_id": detail["census_id"],
            "provider_class": ["TV_HLC_DISAGREEMENT", "TV_HISTORY_WINDOW_UNAVAILABLE"],
            "diagnostic": ["HLC_MISMATCH_HIGH", "NO_PROVIDER_ROW"],
            "hlc_exact": [False, False],
            "provider_hlc_matches_yahoo": [False, False],
        }
    )
    metrics = _metrics(detail, audit, pd.DataFrame({"ticker": ["A", "B"], "status": ["SUCCESS", "SUCCESS"]}))
    assert all("year" in row and "date_y" not in row for row in metrics["unresolved_by_reason_class_year"])
