from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ranking_v4_3_ca_training_ksei_overlay import merge_coverage_and_history


COLUMNS = [
    "ticker",
    "coverage_status",
    "coverage_certified",
    "attempt_count",
    "final_http_status",
    "source_url",
    "source_sha256",
    "ca_rows",
    "active_ca_rows",
    "active_mechanical_rows",
    "active_unknown_rows",
    "earliest_ca_date",
    "latest_ca_date",
    "failure_reason",
]


def row(ticker: str, certified: bool) -> dict[str, object]:
    return {
        "ticker": ticker,
        "coverage_status": "COVERAGE_CERTIFIED" if certified else "COVERAGE_UNRESOLVED",
        "coverage_certified": certified,
        "attempt_count": 1,
        "final_http_status": 200 if certified else 0,
        "source_url": f"https://example.test/{ticker}",
        "source_sha256": "a" * 64 if certified else "",
        "ca_rows": 1 if certified else 0,
        "active_ca_rows": 1 if certified else 0,
        "active_mechanical_rows": 1 if certified else 0,
        "active_unknown_rows": 0,
        "earliest_ca_date": "2024-01-01" if certified else "",
        "latest_ca_date": "2024-01-01" if certified else "",
        "failure_reason": "" if certified else "HTTP_NON_200_OR_EMPTY",
    }


def test_overlay_keeps_unresolved_delta_fail_closed() -> None:
    parent = pd.DataFrame([row("AAAA", True)], columns=COLUMNS)
    delta = pd.DataFrame([row("BBBB", True), row("CCCC", False)], columns=COLUMNS)
    merged, history, diag = merge_coverage_and_history(
        parent_coverage=parent,
        parent_history=[{"ticker": "AAAA", "event": "parent"}],
        delta_coverage=delta,
        delta_history=[{"ticker": "BBBB", "event": "delta"}],
        expected_delta_tickers=2,
        expected_delta_certified=1,
        expected_delta_unresolved=1,
    )
    assert merged["ticker"].tolist() == ["AAAA", "BBBB", "CCCC"]
    assert bool(merged.loc[merged["ticker"].eq("CCCC"), "coverage_certified"].iloc[0]) is False
    assert len(history) == 2
    assert diag["delta_certified_tickers"] == 1
    assert diag["delta_unresolved_tickers"] == 1
    assert diag["unresolved_delta_tickers"] == ["CCCC"]


def test_overlay_rejects_parent_delta_ticker_overlap() -> None:
    parent = pd.DataFrame([row("AAAA", True)], columns=COLUMNS)
    delta = pd.DataFrame([row("AAAA", True)], columns=COLUMNS)
    with pytest.raises(RuntimeError, match="PARENT_DELTA_TICKER_OVERLAP"):
        merge_coverage_and_history(
            parent_coverage=parent,
            parent_history=[],
            delta_coverage=delta,
            delta_history=[],
            expected_delta_tickers=1,
            expected_delta_certified=1,
            expected_delta_unresolved=0,
        )


def test_overlay_rejects_history_for_unresolved_delta_ticker() -> None:
    parent = pd.DataFrame([row("AAAA", True)], columns=COLUMNS)
    delta = pd.DataFrame([row("BBBB", False)], columns=COLUMNS)
    with pytest.raises(RuntimeError, match="DELTA_HISTORY_FOR_UNRESOLVED_TICKER"):
        merge_coverage_and_history(
            parent_coverage=parent,
            parent_history=[],
            delta_coverage=delta,
            delta_history=[{"ticker": "BBBB", "event": "should-not-exist"}],
            expected_delta_tickers=1,
            expected_delta_certified=0,
            expected_delta_unresolved=1,
        )


def test_overlay_rejects_delta_count_drift() -> None:
    parent = pd.DataFrame([row("AAAA", True)], columns=COLUMNS)
    delta = pd.DataFrame([row("BBBB", True)], columns=COLUMNS)
    with pytest.raises(RuntimeError, match="DELTA_TICKER_COUNT_CHANGED"):
        merge_coverage_and_history(
            parent_coverage=parent,
            parent_history=[],
            delta_coverage=delta,
            delta_history=[],
            expected_delta_tickers=2,
            expected_delta_certified=1,
            expected_delta_unresolved=1,
        )
