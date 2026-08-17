from __future__ import annotations

import pandas as pd

from scripts.run_v4_ca_continuity_gate import (
    build_continuity_ledger,
    classify_ksei_event,
    event_reason,
)


def test_ksei_cash_and_proxy_events_are_not_mechanical_continuity_evidence() -> None:
    assert classify_ksei_event("Cash Dividend") is None
    assert classify_ksei_event("Proxy Voting") is None
    assert classify_ksei_event("Stock Dividend") == "STOCK_DIVIDEND"
    assert classify_ksei_event("Right Distribution") == "RIGHTS_HMETD"
    assert classify_ksei_event("Mandatory Conversion") == "MANDATORY_CONVERSION"


def test_unresolved_effective_date_fails_closed() -> None:
    assert (
        event_reason("STOCK_SPLIT", effective_date_proven=False)
        == "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE"
    )


def test_missing_event_coverage_does_not_become_no_event_pass() -> None:
    frozen = pd.DataFrame(
        {"ticker": ["AAA"], "date": [pd.Timestamp("2024-01-02")]}
    )
    validation = pd.DataFrame(
        {"session_index": [1], "date": [pd.Timestamp("2024-01-02")]}
    )
    calendar = pd.DataFrame(
        {
            "session_index": range(12),
            "date": pd.date_range("2024-01-02", periods=12, freq="B"),
        }
    )
    evidence = pd.DataFrame(
        columns=[
            "ticker",
            "event_family",
            "candidate_date",
            "continuity_status",
            "evidence_id",
        ]
    )
    ledger, coverage = build_continuity_ledger(
        frozen, validation, calendar, evidence
    )
    assert set(ledger["continuity_status"]) == {
        "PRICE_CONTINUITY_UNRESOLVED_COVERAGE"
    }
    assert not bool(coverage.loc[0, "consensus_continuity_gate"])
