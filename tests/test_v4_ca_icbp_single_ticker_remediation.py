from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.v4_ca_icbp_single_ticker_remediation import (
    EXPECTED_OUTPUT_UNRESOLVED,
    EXPECTED_PARENT_UNRESOLVED,
    TARGET_TICKER,
    build_certified_target_row,
    normalize_parent_coverage,
    parsed_history_stats,
    validate_output_coverage,
    validate_parent_history,
)


def _coverage() -> pd.DataFrame:
    tickers = sorted(EXPECTED_PARENT_UNRESOLVED) + [f"Z{i:03d}" for i in range(598)]
    assert len(tickers) == 610
    rows = []
    for ticker in tickers:
        certified = ticker not in EXPECTED_PARENT_UNRESOLVED
        rows.append(
            {
                "ticker": ticker,
                "coverage_status": "COVERAGE_CERTIFIED" if certified else "COVERAGE_UNRESOLVED",
                "coverage_certified": str(certified).lower(),
                "attempt_count": 1,
                "final_http_status": 200 if certified else 404,
                "source_url": "https://example.test" if certified else "",
                "source_sha256": "a" * 64 if certified else "",
                "ca_rows": 1 if certified else 0,
                "active_ca_rows": 0,
                "active_mechanical_rows": 0,
                "active_unknown_rows": 0,
                "earliest_ca_date": "2025-01-01" if certified else "",
                "latest_ca_date": "2025-01-01" if certified else "",
                "failure_reason": "" if certified else "HTTP_NON_200_OR_EMPTY",
            }
        )
    return pd.DataFrame(rows)


def _parsed_rows():
    return [
        {
            "ticker": TARGET_TICKER,
            "event_family_source": "Cash Dividend",
            "event_family": "CASH_DIVIDEND",
            "cum_date": "2025-07-15",
            "record_date": "2025-07-17",
            "distribution_date": "2025-07-24",
            "status": "Active",
            "source_url": "https://web.ksei.co.id/example/ICBP",
            "source_sha256": "b" * 64,
        },
        {
            "ticker": TARGET_TICKER,
            "event_family_source": "Proxy Voting",
            "event_family": "PROXY_VOTING",
            "cum_date": None,
            "record_date": "2025-04-01",
            "distribution_date": None,
            "status": "Active",
            "source_url": "https://web.ksei.co.id/example/ICBP",
            "source_sha256": "b" * 64,
        },
    ]


def test_parent_state_is_exact_598_of_610_with_frozen_12():
    frame = normalize_parent_coverage(_coverage())
    assert int(frame["coverage_certified"].sum()) == 598
    assert set(frame.loc[~frame["coverage_certified"], "ticker"]) == set(EXPECTED_PARENT_UNRESOLVED)


def test_parent_state_rejects_changed_unresolved_identity():
    frame = _coverage()
    frame.loc[frame["ticker"].eq("AVIA"), "coverage_certified"] = "true"
    with pytest.raises(RuntimeError, match="PARENT_CERTIFIED_COUNT_CHANGED"):
        normalize_parent_coverage(frame)


def test_parent_history_must_not_already_contain_icbp():
    validate_parent_history([{"ticker": "BBCA"}])
    with pytest.raises(RuntimeError, match="ALREADY_CONTAINS_TARGET"):
        validate_parent_history([{"ticker": TARGET_TICKER}])


def test_strict_parsed_rows_are_summarized_without_semantic_rescue():
    stats = parsed_history_stats(_parsed_rows())
    assert stats["ca_rows"] == 2
    assert stats["active_mechanical_rows"] == 0
    assert stats["active_unknown_rows"] == 0
    assert stats["event_families"] == ["CASH_DIVIDEND", "PROXY_VOTING"]
    assert stats["earliest_ca_date"] == "2025-04-01"
    assert stats["latest_ca_date"] == "2025-07-24"


def test_strict_parsed_rows_reject_wrong_ticker():
    rows = _parsed_rows()
    rows[0] = dict(rows[0], ticker="XXXX")
    with pytest.raises(RuntimeError, match="TICKER_MISMATCH"):
        parsed_history_stats(rows)


def test_replacement_row_requires_exact_success_and_two_attempt_bound():
    parent = normalize_parent_coverage(_coverage())
    row = parent[parent["ticker"].eq(TARGET_TICKER)].iloc[0].to_dict()
    stats = parsed_history_stats(_parsed_rows())
    success = {
        "status_code": 200,
        "final_url": "https://web.ksei.co.id/services/registered-securities/shares/lc/ICBP?setLocale=en-US",
        "sha256": "b" * 64,
    }
    replacement = build_certified_target_row(
        row,
        success_record=success,
        security_attempt_count=1,
        stats=stats,
    )
    assert replacement["ticker"] == TARGET_TICKER
    assert replacement["coverage_certified"] is True
    assert replacement["active_mechanical_rows"] == 0
    with pytest.raises(RuntimeError, match="ATTEMPT_COUNT_OUT_OF_BOUNDS"):
        build_certified_target_row(
            row,
            success_record=success,
            security_attempt_count=3,
            stats=stats,
        )


def test_output_state_is_exact_599_of_610_with_only_icbp_removed_from_gap():
    parent = normalize_parent_coverage(_coverage())
    output = parent.copy()
    mask = output["ticker"].eq(TARGET_TICKER)
    output.loc[mask, "coverage_status"] = "COVERAGE_CERTIFIED"
    output.loc[mask, "coverage_certified"] = True
    result = validate_output_coverage(output)
    assert int(result["coverage_certified"].sum()) == 599
    assert set(result.loc[~result["coverage_certified"], "ticker"]) == set(EXPECTED_OUTPUT_UNRESOLVED)
