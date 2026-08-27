from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ca_feature_basis_family_coverage_v1 import (
    FAMILY_COVERAGE_CERTIFIED,
    FAMILY_COVERAGE_UNKNOWN,
)
from idx_trade.ca_feature_basis_frozen_sources_v1 import (
    KSEI_PROVEN_COVERAGE_FAMILIES,
    compare_ksei_population_to_identities,
    frozen_event_semantics_to_basis_inputs,
    ksei_ticker_coverage_to_basis_coverage,
    ksei_ticker_coverage_to_family_coverage,
)
from idx_trade.ca_feature_basis_v1 import (
    BONUS_SHARES,
    CAPITAL_RESTRUCTURING,
    MANDATORY_CONVERSION,
    RESOLVED,
    RIGHTS_HMETD,
    STOCK_DIVIDEND,
    STOCK_SPLIT,
)


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


def test_exact_entitlement_transitions_are_promoted_from_pinned_semantics() -> None:
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
            semantic_row(
                event_id="B1",
                ticker="BONU",
                family="SHARE_BONUS",
                semantic_class="EXACT_TRANSITION",
                transition_date=days[8],
                transition_source="KSEI_STATIC_CUM_NEXT_OFFICIAL_SESSION",
            ),
            semantic_row(
                event_id="MD1",
                ticker="MIXD",
                family="MIXED_STOCK_DIVIDEND",
                semantic_class="EXACT_TRANSITION",
                transition_date=days[9],
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
    assert rows.loc["B1", "event_family"] == BONUS_SHARES
    assert rows.loc["MD1", "event_family"] == STOCK_DIVIDEND
    assert set(ledger["effective_transition_state"]) == {RESOLVED}
    assert ledger["event_semantics_certified"].all()
    assert set(ledger["semantic_evidence_sha256"]) == {SEMANTIC_SHA}


def test_exact_schedule_resolved_split_or_mandatory_conversion_can_create_epoch_only() -> None:
    days = sessions()
    semantics = pd.DataFrame(
        [
            semantic_row(
                event_id="S1",
                ticker="SPLT",
                family="STOCK_SPLIT",
                semantic_class="EXACT_TRANSITION",
                transition_date=days[5],
                transition_source="OFFICIAL_KSEI_SCHEDULE",
            ),
            semantic_row(
                event_id="C1",
                ticker="CONV",
                family="MANDATORY_CONVERSION",
                semantic_class="EXACT_TRANSITION",
                transition_date=days[6],
                transition_source="OFFICIAL_KSEI_SCHEDULE",
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
    assert rows.loc["S1", "event_family"] == STOCK_SPLIT
    assert rows.loc["C1", "event_family"] == MANDATORY_CONVERSION
    # No adjustment factor is created by this adapter; only a boundary.
    assert "adjustment_factor" not in ledger.columns


def test_exact_source_bound_merger_alias_can_create_restructuring_epoch_only() -> None:
    days = sessions()
    semantics = pd.DataFrame(
        [
            semantic_row(
                event_id="MRG1",
                ticker="JARR",
                family="MERGER_OR_RESTRUCTURING",
                semantic_class="EXACT_TRANSITION",
                transition_date=days[5],
                transition_source="OFFICIAL_KSEI_SCHEDULE",
            )
        ]
    )

    ledger, blocked = frozen_event_semantics_to_basis_inputs(
        semantics,
        days,
        semantic_artifact_sha256=SEMANTIC_SHA,
        semantic_source_ref="frozen://event-semantics",
    )

    assert blocked == set()
    assert ledger.iloc[0]["event_family"] == CAPITAL_RESTRUCTURING
    assert ledger.iloc[0]["effective_transition_state"] == RESOLVED
    assert "adjustment_factor" not in ledger.columns


def test_schedule_required_and_unsupported_exact_family_force_ticker_unknown() -> None:
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
                event_id="V1",
                ticker="VOLC",
                family="VOLUNTARY_CONVERSION",
                semantic_class="EXACT_TRANSITION",
                transition_date=days[5],
                transition_source="OFFICIAL_KSEI_SCHEDULE",
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
    assert blocked == {"CUAN", "VOLC"}


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
    scope_start: object = "2024-07-01",
    scope_end: object = "2024-07-16",
    observed_at: object = "2024-07-17T12:00:00+07:00",
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "coverage_status": status,
        "coverage_certified": certified,
        "source_url": f"https://example.invalid/{ticker}",
        "source_sha256": source_sha,
        "failure_reason": failure_reason,
        "coverage_start_session": scope_start,
        "coverage_end_session": scope_end,
        "coverage_observed_at": observed_at,
    }


def test_ksei_coverage_is_family_scoped_and_forced_unknown_wins() -> None:
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

    coverage = ksei_ticker_coverage_to_family_coverage(
        census,
        days,
        start_session=days[2],
        end_session=days[5],
        coverage_artifact_sha256=COVERAGE_SHA,
        coverage_source_ref="frozen://ticker-coverage",
        forced_unknown_tickers={"SCHEDULED"},
    )

    assert set(coverage["event_family"]) == set(KSEI_PROVEN_COVERAGE_FAMILIES)
    states = coverage.groupby("ticker")["coverage_state"].unique().to_dict()
    assert states["SAFE"].tolist() == [FAMILY_COVERAGE_CERTIFIED]
    assert states["SCHEDULED"].tolist() == [FAMILY_COVERAGE_UNKNOWN]
    assert states["FAILED"].tolist() == [FAMILY_COVERAGE_UNKNOWN]
    assert coverage.groupby(["ticker", "event_family"]).size().eq(4).all()


def test_ksei_temporal_scope_cannot_be_extended_by_caller() -> None:
    days = sessions()
    census = pd.DataFrame(
        [coverage_row("TEST", scope_start=days[2], scope_end=days[5], observed_at=days[6])]
    )

    coverage = ksei_ticker_coverage_to_family_coverage(
        census,
        days,
        start_session=days[1],
        end_session=days[5],
        coverage_artifact_sha256=COVERAGE_SHA,
        coverage_source_ref="frozen://ticker-coverage",
    )

    assert set(coverage["coverage_state"]) == {FAMILY_COVERAGE_UNKNOWN}
    assert set(coverage["coverage_reason"]) == {
        "REQUESTED_INTERVAL_EXCEEDS_KSEI_CERTIFIED_HISTORY_SCOPE"
    }


def test_legacy_ksei_census_without_temporal_attestation_is_rejected() -> None:
    days = sessions()
    census = pd.DataFrame([coverage_row("TEST")]).drop(columns=["coverage_observed_at"])

    with pytest.raises(ValueError, match="missing columns"):
        ksei_ticker_coverage_to_family_coverage(
            census,
            days,
            start_session=days[2],
            end_session=days[5],
            coverage_artifact_sha256=COVERAGE_SHA,
            coverage_source_ref="frozen://ticker-coverage",
        )


def test_blank_temporal_scope_fails_closed_instead_of_certifying() -> None:
    days = sessions()
    census = pd.DataFrame(
        [coverage_row("TEST", scope_start="", scope_end="", observed_at="")]
    )

    coverage = ksei_ticker_coverage_to_family_coverage(
        census,
        days,
        start_session=days[2],
        end_session=days[5],
        coverage_artifact_sha256=COVERAGE_SHA,
        coverage_source_ref="frozen://ticker-coverage",
    )

    assert set(coverage["coverage_state"]) == {FAMILY_COVERAGE_UNKNOWN}
    assert set(coverage["coverage_reason"]) == {
        "REQUESTED_INTERVAL_EXCEEDS_KSEI_CERTIFIED_HISTORY_SCOPE"
    }


def test_ksei_observed_at_cannot_predate_certified_history_end() -> None:
    days = sessions()
    census = pd.DataFrame(
        [coverage_row("TEST", scope_start=days[0], scope_end=days[5], observed_at=days[4])]
    )

    with pytest.raises(ValueError, match="coverage_observed_at predates certified history end"):
        ksei_ticker_coverage_to_family_coverage(
            census,
            days,
            start_session=days[2],
            end_session=days[5],
            coverage_artifact_sha256=COVERAGE_SHA,
            coverage_source_ref="frozen://ticker-coverage",
        )


def test_ksei_population_comparison_reports_exact_missing_and_extra_tickers() -> None:
    identities = pd.DataFrame(
        {
            "ticker": ["AAAA.JK", "BBBB", "AAAA"],
            "date": ["2024-07-01", "2024-07-02", "2024-07-03"],
        }
    )
    census = pd.DataFrame([coverage_row("BBBB"), coverage_row("CCCC")])

    result = compare_ksei_population_to_identities(identities, census)

    assert result["application_ticker_count"] == 2
    assert result["coverage_ticker_count"] == 2
    assert result["coverage_contains_application_population"] is False
    assert result["missing_application_tickers"] == ["AAAA"]
    assert result["extra_coverage_tickers"] == ["CCCC"]


def test_ksei_contract_refuses_to_certify_unproven_split_family() -> None:
    days = sessions()
    census = pd.DataFrame([coverage_row("TEST")])
    with pytest.raises(ValueError, match="cannot certify unproven event families"):
        ksei_ticker_coverage_to_family_coverage(
            census,
            days,
            start_session=days[1],
            end_session=days[2],
            coverage_artifact_sha256=COVERAGE_SHA,
            coverage_source_ref="frozen://ticker-coverage",
            covered_event_families=[STOCK_SPLIT],
        )


def test_coverage_field_disagreement_fails_closed_per_family() -> None:
    days = sessions()
    census = pd.DataFrame([coverage_row("TEST", certified=False)])
    coverage = ksei_ticker_coverage_to_family_coverage(
        census,
        days,
        start_session=days[1],
        end_session=days[2],
        coverage_artifact_sha256=COVERAGE_SHA,
        coverage_source_ref="frozen://ticker-coverage",
    )
    assert set(coverage["coverage_state"]) == {FAMILY_COVERAGE_UNKNOWN}
    assert set(coverage["coverage_reason"]) == {"KSEI_COVERAGE_FIELDS_DISAGREE"}


def test_direct_ksei_to_global_coverage_path_is_forbidden() -> None:
    with pytest.raises(RuntimeError, match="DIRECT_KSEI_TO_GLOBAL_CA_COVERAGE_FORBIDDEN"):
        ksei_ticker_coverage_to_basis_coverage()
