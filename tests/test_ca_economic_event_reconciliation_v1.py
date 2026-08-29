import pytest

from idx_trade.ca_economic_event_reconciliation_v1 import (
    EconomicReconciliationError,
    provisional_economic_family,
    reconcile_economic_events,
)


SHA = "a" * 64


def _row(event_id, source_kind, family, label=""):
    return {
        "source_event_id": event_id,
        "source_kind": source_kind,
        "event_family": family,
        "source_native_label": label,
    }


def _link(left, right, sha=SHA):
    return {
        "left_source_event_id": left,
        "right_source_event_id": right,
        "relation": "PROVEN_SAME_ECONOMIC_EVENT",
        "authority_source_ref": f"OFFICIAL:{left}:{right}",
        "authority_evidence_sha256": sha,
    }


def _adjudication(event_id, family, basis_effect, sha=SHA):
    return {
        "source_event_id": event_id,
        "adjudication_status": "PROVEN",
        "economic_family": family,
        "basis_effect": basis_effect,
        "authority_source_ref": f"OFFICIAL:{event_id}",
        "authority_evidence_sha256": sha,
    }


def _transition(event_id, day="2024-01-08", semantic="REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE", sha=SHA):
    return {
        "source_event_id": event_id,
        "transition_status": "RESOLVED",
        "transition_semantic": semantic,
        "transition_date": day,
        "authority_source_ref": f"OFFICIAL-SCHEDULE:{event_id}",
        "authority_evidence_sha256": sha,
    }


def test_ksei_operational_conversion_labels_do_not_auto_promote():
    mandatory = _row(
        "KSEI-M",
        "KSEI_REGISTERED_SECURITY_HISTORY",
        "MANDATORY_CONVERSION",
        "Mandatory Conversion",
    )
    voluntary = _row(
        "KSEI-V",
        "KSEI_REGISTERED_SECURITY_HISTORY",
        "VOLUNTARY_CONVERSION",
        "Voluntary Conversion",
    )
    assert provisional_economic_family(mandatory) == "UNRESOLVED_OPERATIONAL_LABEL"
    assert provisional_economic_family(voluntary) == "UNRESOLVED_OPERATIONAL_LABEL"

    result = reconcile_economic_events([mandatory, voluntary])
    assert result["economic_event_count"] == 2
    assert result["resolved_transitions"] == 0
    assert result["unresolved_transitions"] == 2
    assert {row["economic_family"] for row in result["economic_events"]} == {
        "UNRESOLVED_OPERATIONAL_LABEL"
    }


def test_source_bound_linkage_collapses_ksei_mandatory_representation_into_stock_split():
    rows = [
        _row("IDX-SPLIT", "IDX_GET_ISSUED_HISTORY", "STOCK_SPLIT", "stockSplit"),
        _row(
            "KSEI-MCONV",
            "KSEI_REGISTERED_SECURITY_HISTORY",
            "MANDATORY_CONVERSION",
            "Mandatory Conversion",
        ),
    ]
    result = reconcile_economic_events(rows, linkages=[_link("IDX-SPLIT", "KSEI-MCONV")])
    assert result["source_evidence_rows"] == 2
    assert result["economic_event_count"] == 1
    assert result["cross_source_collapses"] == 1
    assert result["same_source_collapses"] == 0
    event = result["economic_events"][0]
    assert event["economic_family"] == "STOCK_SPLIT"
    assert event["basis_effect"] == "BASIS_CHANGING"
    assert event["transition_status"] == "UNRESOLVED"
    assert event["source_event_ids"] == ["IDX-SPLIT", "KSEI-MCONV"]


def test_bad_linkage_provenance_fails_closed():
    rows = [
        _row("A", "IDX_GET_ISSUED_HISTORY", "STOCK_SPLIT"),
        _row("B", "KSEI_REGISTERED_SECURITY_HISTORY", "MANDATORY_CONVERSION", "Mandatory Conversion"),
    ]
    with pytest.raises(EconomicReconciliationError, match="lacks source-bound provenance"):
        reconcile_economic_events(rows, linkages=[_link("A", "B", sha="bad")])


def test_tender_cash_adjudication_is_non_basis_and_not_a_transition_blocker():
    row = _row(
        "KSEI-V",
        "KSEI_REGISTERED_SECURITY_HISTORY",
        "VOLUNTARY_CONVERSION",
        "Voluntary Conversion",
    )
    result = reconcile_economic_events(
        [row],
        adjudications=[
            _adjudication(
                "KSEI-V",
                "TENDER_OFFER_OR_CASH_PROCESS",
                "NON_BASIS",
            )
        ],
    )
    assert result["economic_event_count"] == 1
    assert result["non_basis_excluded"] == 1
    assert result["resolved_transitions"] == 0
    assert result["unresolved_transitions"] == 0
    event = result["economic_events"][0]
    assert event["economic_family"] == "TENDER_OFFER_OR_CASH_PROCESS"
    assert event["transition_status"] == "NOT_APPLICABLE_NON_BASIS"


def test_resolved_transition_requires_explicit_accepted_semantic_and_provenance():
    row = _row("SPLIT", "IDX_GET_ISSUED_HISTORY", "STOCK_SPLIT")
    result = reconcile_economic_events(
        [row],
        transition_attestations=[_transition("SPLIT")],
    )
    assert result["resolved_transitions"] == 1
    assert result["unresolved_transitions"] == 0
    assert result["economic_events"][0]["transition_date"] == "2024-01-08"

    with pytest.raises(EconomicReconciliationError, match="unaccepted semantic"):
        reconcile_economic_events(
            [row],
            transition_attestations=[
                _transition("SPLIT", semantic="RECORD_DATE")
            ],
        )

    with pytest.raises(EconomicReconciliationError, match="lacks source-bound provenance"):
        reconcile_economic_events(
            [row],
            transition_attestations=[_transition("SPLIT", sha="")],
        )


def test_same_source_and_cross_source_collapse_arithmetic_is_exact():
    rows = [
        _row("IDX-A", "IDX_GET_ISSUED_HISTORY", "STOCK_SPLIT"),
        _row("KSEI-A", "KSEI_REGISTERED_SECURITY_HISTORY", "MANDATORY_CONVERSION", "Mandatory Conversion"),
        _row("IDX-B1", "IDX_GET_ISSUED_HISTORY", "RIGHTS_HMETD"),
        _row("IDX-B2", "IDX_GET_ISSUED_HISTORY", "RIGHTS_HMETD"),
        _row("KSEI-C", "KSEI_REGISTERED_SECURITY_HISTORY", "VOLUNTARY_CONVERSION", "Voluntary Conversion"),
    ]
    result = reconcile_economic_events(
        rows,
        linkages=[
            _link("IDX-A", "KSEI-A"),
            _link("IDX-B1", "IDX-B2"),
        ],
        adjudications=[
            _adjudication("KSEI-C", "TENDER_OFFER_OR_CASH_PROCESS", "NON_BASIS")
        ],
        transition_attestations=[_transition("IDX-A")],
    )
    assert result["source_evidence_rows"] == 5
    assert result["cross_source_collapses"] == 1
    assert result["same_source_collapses"] == 1
    assert result["economic_event_count"] == 3
    assert result["resolved_transitions"] == 1
    assert result["unresolved_transitions"] == 1
    assert result["non_basis_excluded"] == 1
    assert 5 - 1 - 1 == 3
    assert 1 + 1 + 1 == 3


def test_conflicting_proven_economic_classification_fails_closed_at_event_state():
    rows = [
        _row("A", "IDX_GET_ISSUED_HISTORY", "STOCK_SPLIT"),
        _row("B", "KSEI_REGISTERED_SECURITY_HISTORY", "MANDATORY_CONVERSION", "Mandatory Conversion"),
    ]
    result = reconcile_economic_events(
        rows,
        linkages=[_link("A", "B")],
        adjudications=[
            _adjudication("A", "STOCK_SPLIT", "BASIS_CHANGING"),
            _adjudication("B", "TRUE_SECURITY_CONVERSION", "BASIS_CHANGING"),
        ],
    )
    event = result["economic_events"][0]
    assert event["economic_family"] == "CONFLICTING_ECONOMIC_CLASSIFICATION"
    assert event["classification_conflict"] is True
    assert event["transition_status"] == "UNRESOLVED_CLASSIFICATION_CONFLICT"
    assert result["unresolved_transitions"] == 1
