from __future__ import annotations

import pandas as pd

from idx_trade.v4_ca_event_windows import event_identity
from idx_trade.v4_ca_voluntary_conversion_forensic import (
    VERDICT_CONFIRMED_REPORTING_UNDERCOUNT,
    VERDICT_INCONSISTENT,
    VERDICT_ZERO_RECLASS_IDENTITY,
    compare_per_date_outputs,
    replay_parent_relevant_events,
)


def sessions():
    return [pd.Timestamp("2026-04-13"), pd.Timestamp("2026-04-14")]


def history_row(**updates):
    row = {
        "ticker": "TEST",
        "row_index": 1,
        "event_family_source": "Voluntary Conversion",
        "event_family": "MANDATORY_CONVERSION",
        "cum_date": None,
        "record_date": "2026-04-13",
        "distribution_date": None,
        "status": "Active",
        "ratio_raw": "(1 TEST : 100 IDR)",
        "ratio_parse_status": "PARSED_SOURCE_TEXT_ONLY",
        "ratio_left_value": "1",
        "ratio_left_security": "TEST",
        "ratio_right_value": "100",
        "ratio_right_security": "IDR",
        "source_url": "https://web.ksei.co.id/example",
        "source_sha256": "a" * 64,
    }
    row.update(updates)
    return row


def audit_row(row, *, family="VOLUNTARY_CONVERSION", semantic_class="SCHEDULE_REQUIRED"):
    return {
        "event_id": event_identity(row),
        "ticker": row["ticker"],
        "source_type": row["event_family_source"],
        "family": family,
        "semantic_class": semantic_class,
        "transition_date": "",
        "transition_source": "",
        "reason": "ACTIVE_EVENT_REQUIRES_EXACT_OFFICIAL_SCHEDULE",
        "source_dates": "2026-04-13",
    }


def test_removed_strict_cash_event_is_confirmed_reporting_undercount():
    row = history_row()
    parent = pd.DataFrame([audit_row(row)])
    remediation = pd.DataFrame(columns=parent.columns)

    side, voluntary, diff, summary = replay_parent_relevant_events(
        history_rows=[row],
        official_sessions=sessions(),
        parent_audit=parent,
        remediation_audit=remediation,
    )

    assert len(side) == 1
    assert len(voluntary) == 1
    assert len(diff) == 1
    assert summary["strict_cash_predicate_count"] == 1
    assert summary["reclassified_to_nonblocking_count"] == 1
    assert summary["removed_event_count"] == 1
    assert summary["removed_ids_equal_reclassified_nonblocking_ids"] is True
    assert summary["all_removed_ids_are_strict_voluntary_cash"] is True
    assert summary["verdict"] == VERDICT_CONFIRMED_REPORTING_UNDERCOUNT


def test_zero_reclassification_requires_identical_event_set():
    row = history_row(
        ratio_raw="(1 TEST : 2 ABCD)",
        ratio_right_value="2",
        ratio_right_security="ABCD",
    )
    audit = pd.DataFrame([audit_row(row)])

    _, voluntary, diff, summary = replay_parent_relevant_events(
        history_rows=[row],
        official_sessions=sessions(),
        parent_audit=audit,
        remediation_audit=audit.copy(),
    )

    assert len(voluntary) == 1
    assert diff.empty
    assert summary["reclassified_to_nonblocking_count"] == 0
    assert summary["zero_reclassification_event_identity_invariant"] is True
    assert summary["verdict"] == VERDICT_ZERO_RECLASS_IDENTITY


def test_unexplained_removed_event_fails_closed():
    row = history_row(
        ratio_raw="(1 TEST : 2 ABCD)",
        ratio_right_value="2",
        ratio_right_security="ABCD",
    )
    parent = pd.DataFrame([audit_row(row)])
    remediation = pd.DataFrame(columns=parent.columns)

    _, _, _, summary = replay_parent_relevant_events(
        history_rows=[row],
        official_sessions=sessions(),
        parent_audit=parent,
        remediation_audit=remediation,
    )

    assert summary["reclassified_to_nonblocking_count"] == 0
    assert summary["removed_event_count"] == 1
    assert summary["zero_reclassification_event_identity_invariant"] is False
    assert summary["verdict"] == VERDICT_INCONSISTENT


def test_left_security_identity_mismatch_remains_fail_closed():
    row = history_row(
        ratio_raw="(1 OTHER : 100 IDR)",
        ratio_left_security="OTHER",
    )
    audit = pd.DataFrame([audit_row(row)])

    side, _, _, summary = replay_parent_relevant_events(
        history_rows=[row],
        official_sessions=sessions(),
        parent_audit=audit,
        remediation_audit=audit.copy(),
    )

    assert bool(side.iloc[0]["strict_security_to_currency_predicate"]) is False
    assert side.iloc[0]["remediation_semantic_class"] == "SCHEDULE_REQUIRED"
    assert summary["reclassified_to_nonblocking_count"] == 0


def test_unparsed_ratio_remains_fail_closed():
    row = history_row(
        ratio_parse_status="UNRESOLVED_SOURCE_TEXT",
        ratio_left_security=None,
        ratio_right_security=None,
    )
    audit = pd.DataFrame([audit_row(row)])

    side, _, _, summary = replay_parent_relevant_events(
        history_rows=[row],
        official_sessions=sessions(),
        parent_audit=audit,
        remediation_audit=audit.copy(),
    )
    assert bool(side.iloc[0]["strict_security_to_currency_predicate"]) is False
    assert summary["reclassified_to_nonblocking_count"] == 0


def per_date(rate: float, resolved: int):
    return pd.DataFrame(
        [
            {
                "date": "2026-04-13",
                "h5_decision_rows": 100,
                "h5_resolved_rows": resolved,
                "h5_rate": rate,
                "h5_gate": rate >= 0.9,
                "h10_decision_rows": 100,
                "h10_resolved_rows": resolved,
                "h10_rate": rate,
                "h10_gate": rate >= 0.9,
                "consensus_resolved_rows": resolved,
                "consensus_rate": rate,
                "consensus_gate": rate >= 0.9,
            }
        ]
    )


def test_zero_reclassification_continuity_change_fails_invariant():
    _, summary = compare_per_date_outputs(
        per_date(0.75, 75), per_date(0.79, 79), reclassified_count=0
    )
    assert summary["changed_date_rows"] == 1
    assert summary["zero_reclassification_continuity_identity_invariant"] is False
    assert summary["verdict"] == VERDICT_INCONSISTENT


def test_nonzero_reclassification_allows_continuity_change_but_records_it():
    _, summary = compare_per_date_outputs(
        per_date(0.75, 75), per_date(0.79, 79), reclassified_count=4
    )
    assert summary["changed_date_rows"] == 1
    assert summary["zero_reclassification_continuity_identity_invariant"] is None
    assert "verdict" not in summary
