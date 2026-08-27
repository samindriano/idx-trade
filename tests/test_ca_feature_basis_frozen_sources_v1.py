from __future__ import annotations

import pandas as pd

from idx_trade.ca_feature_basis_frozen_sources_v1 import (
    frozen_event_semantics_to_basis_inputs,
    ksei_ticker_coverage_to_basis_coverage,
)
from idx_trade.ca_feature_basis_gate_v1 import (
    CA_COVERAGE_CERTIFIED,
    CA_COVERAGE_UNKNOWN,
)
from idx_trade.ca_feature_basis_v1 import RESOLVED, RIGHTS_HMETD, STOCK_DIVIDEND


SEMANTIC_SHA = "a" * 64
COVERAGE_SHA = "b" * 64
RAW_SHA = "c" * 64


def sessions(n: int = 12) -> pd.DatetimeIndex:
    return pd.bdate_range("2024-07-01", periods=n)


def semantic_row(
    *,
    event_id: str,
    ticker: str,
    family: str,
    semantic_class: str,
    transition_date: object = "",
    transition_source: str = "",
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "ticker": ticker,
        "family": family,
        "semantic_class": semantic_class,
        "transition_date": transition_date,
        "transition_source": transition_source,
        "reason": "fixture",
        "source_dates": "2024-07-08|2024-07-10",
    }


def test_exact_right_and_stock_dividend_are_promoted_only_from_pinned_semantics() -> None:
    days = sessions()
    semantics = pd.DataFrame(
        [
            semantic_row(
                event_id="R1",
                ticker="AGRS",
                family="RIGHT_DISTRIBUTION",
                semantic_class="EXACT_TRANSITION",
                transition_date=days[6],
                transition_source="KSEI_STATIC_CUM_NEXT_OFFICIAL_SESSION",
            ),
            semantic_row(
                event_id="D1",
                ticker="KKGI",
                family="STOCK_DIVIDEND",
                semantic_class="EXACT_TRANSITION",
                transition_date=days[7],
                transition_source="KSEI_STATIC_CUM_NEXT_OFFICIAL_SESSION",
            ),
        ]
    )

    ledger, blocked = frozen_event_semantics_to_basis_inputs(
        semantics,
        days,
        semantic_artifact_sha256=SEMANTIC_SHA,
        semantic_source_ref="frozen://event-semantics",
    )

    assert blocked == set()
    rows = ledger.set_index("event_identity")
    assert rows.loc["R1", "event_family"] == RIGHTS_HMETD
    assert rows.loc["D1", "event_family"] == STOCK_DIVIDEND
    assert set(ledger["effective_transition_state"]) == {RESOLVED}
    assert ledger["event_semantics_certified"].all()
    assert set(ledger["semantic_evidence_sha256"]) == {SEMANTIC_SHA}


def test_schedule_required_and_unknown_exact_family_force_ticker_unknown() -> None:
    days = sessions()
    semantics = pd.DataFrame(
        [
            semantic_row(
                event_id="M1",
                ticker="CUAN",
                family="MANDATORY_CONVERSION",
                semantic_class="SCHEDULE_REQUIRED",
            ),
            semantic_row(
                event_id="X1",
                ticker="MIXD",
                family="MIXED_STOCK_DIVIDEND",
                semantic_class="EXACT_TRANSITION",
                transition_date=days[5],
                transition_source="fixture",
            ),
        ]
    )

    ledger, blocked = frozen_event_semantics_to_basis_inputs(
        semantics,
        days,
        semantic_artifact_sha256=SEMANTIC_SHA,
        semantic_source_ref="frozen://event-semantics",
    )

    assert ledger.empty
    assert blocked == {"CUAN", "MIXD"}


def test_exact_transition_off_calendar_is_not_silently_shifted() -> None:
    days = sessions()
    semantics = pd.DataFrame(
        [
            semantic_row(
                event_id="R1",
                ticker="AGRS",
                family="RIGHT_DISTRIBUTION",
                semantic_class="EXACT_TRANSITION",
                transition_date=pd.Timestamp("2024-07-06"),
                transition_source="fixture",
            )
        ]
    )
    ledger, blocked = frozen_event_semantics_to_basis_inputs(
        semantics,
        days,
        semantic_artifact_sha256=SEMANTIC_SHA,
        semantic_source_ref="frozen://event-semantics",
    )
    assert ledger.empty
    assert blocked == {"AGRS"}


def coverage_row(
    ticker: str,
    *,
    status: str = "COVERAGE_CERTIFIED",
    certified: object = True,
    source_sha: str = RAW_SHA,
    failure_reason: str = "",
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "coverage_status": status,
        "coverage_certified": certified,
        "source_url": f"https://example.invalid/{ticker}",
        "source_sha256": source_sha,
        "failure_reason": failure_reason,
    }


def test_ksei_coverage_certifies_only_agreeing_unblocked_ticker() -> None:
    days = sessions()
    census = pd.DataFrame(
        [
            coverage_row("SAFE"),
            coverage_row("SCHEDULED"),
            coverage_row(
                "FAILED",
                status="COVERAGE_UNRESOLVED",
                certified=False,
                source_sha="",
                failure_reason="THREE_ATTEMPTS_FAILED",
            ),
        ]
    )

    coverage = ksei_ticker_coverage_to_basis_coverage(
        census,
        days,
        start_session=days[2],
        end_session=days[5],
        coverage_artifact_sha256=COVERAGE_SHA,
        coverage_source_ref="frozen://ticker-coverage",
        forced_unknown_tickers={"SCHEDULED"},
    )

    states = coverage.groupby("ticker")["coverage_state"].unique().to_dict()
    assert states["SAFE"].tolist() == [CA_COVERAGE_CERTIFIED]
    assert states["SCHEDULED"].tolist() == [CA_COVERAGE_UNKNOWN]
    assert states["FAILED"].tolist() == [CA_COVERAGE_UNKNOWN]
    assert coverage.groupby("ticker").size().to_dict() == {
        "FAILED": 4,
        "SAFE": 4,
        "SCHEDULED": 4,
    }


def test_coverage_field_disagreement_fails_closed_instead_of_certifying() -> None:
    days = sessions()
    census = pd.DataFrame([coverage_row("TEST", certified=False)])
    coverage = ksei_ticker_coverage_to_basis_coverage(
        census,
        days,
        start_session=days[1],
        end_session=days[2],
        coverage_artifact_sha256=COVERAGE_SHA,
        coverage_source_ref="frozen://ticker-coverage",
    )
    assert set(coverage["coverage_state"]) == {CA_COVERAGE_UNKNOWN}
    assert set(coverage["coverage_reason"]) == {"KSEI_COVERAGE_FIELDS_DISAGREE"}


def test_forced_unknown_wins_even_when_raw_ksei_coverage_is_certified() -> None:
    days = sessions()
    census = pd.DataFrame([coverage_row("ISAT")])
    coverage = ksei_ticker_coverage_to_basis_coverage(
        census,
        days,
        start_session=days[0],
        end_session=days[1],
        coverage_artifact_sha256=COVERAGE_SHA,
        coverage_source_ref="frozen://ticker-coverage",
        forced_unknown_tickers={"ISAT"},
    )
    assert set(coverage["coverage_state"]) == {CA_COVERAGE_UNKNOWN}
    assert set(coverage["evidence_sha256"]) == {COVERAGE_SHA}
