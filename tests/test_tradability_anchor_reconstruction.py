import pandas as pd

from idx_trade.security_master import (
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
    tradability_state,
)
from idx_trade.tradability_anchor_reconstruction import (
    reconcile_boundary_suspension_anchors,
)


def _coverage(start: str = "2025-01-01", end: str = "2025-01-31"):
    return canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "market": ["REGULAR"],
                "effective_from": [start],
                "effective_to": [end],
                "source": ["IDX_PUBLIC_ARCHIVE"],
                "is_complete": [True],
                "discovery_basis": ["COMPLETE_PAGINATION_AUDIT"],
                "left_boundary_basis": ["ARCHIVE_BOUNDARY_AUDIT"],
            }
        )
    )


def _suspended_anchor(date: str = "2025-01-01"):
    return canonicalize_tradability_anchors(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "as_of_date": [date],
                "state": ["SUSPENDED"],
                "source": ["IDX_STATUS_SNAPSHOT"],
                "source_ref": ["idx://snapshot/suspended"],
                "evidence_type": ["OFFICIAL_SUSPENDED_STATUS"],
            }
        )
    )


def _resume_event(date: str = "2025-01-06"):
    return pd.DataFrame(
        {
            "ticker": ["TEST"],
            "market": ["REGULAR"],
            "action": ["RESUME"],
            "effective_date": [pd.Timestamp(date)],
            "source": ["IDX_EXCHANGE_ANNOUNCEMENT"],
            "source_ref": ["idx://resume"],
        }
    )


def test_suspended_boundary_anchor_closes_at_first_official_resume():
    events = _resume_event()
    compile_diagnostics = pd.DataFrame(
        {
            "ticker": ["TEST"],
            "market": ["REGULAR"],
            "effective_date": [pd.Timestamp("2025-01-06")],
            "status": ["UNMATCHED_RESUME"],
            "diagnostic": ["UNMATCHED_RESUME_NO_INITIAL_ACTIVE"],
            "inferred_state": ["UNKNOWN"],
            "source_ref": ["idx://resume"],
        }
    )
    intervals, diagnostics, anchor_diagnostics = reconcile_boundary_suspension_anchors(
        events,
        canonicalize_tradability_intervals(pd.DataFrame()),
        compile_diagnostics,
        _suspended_anchor(),
        _coverage(),
    )

    assert diagnostics.empty
    assert len(intervals) == 1
    interval = intervals.iloc[0]
    assert interval["effective_from"] == pd.Timestamp("2025-01-01")
    assert interval["effective_to"] == pd.Timestamp("2025-01-05")
    assert anchor_diagnostics.loc[0, "status"] == "RESOLVED_BY_RESUME"

    anchors = _suspended_anchor()
    coverage = _coverage()
    assert tradability_state(
        intervals, coverage, "TEST", pd.Timestamp("2025-01-03"), anchors=anchors
    ).value == "SUSPENDED"
    assert tradability_state(
        intervals, coverage, "TEST", pd.Timestamp("2025-01-06"), anchors=anchors
    ).value == "ACTIVE"


def test_suspended_anchor_without_later_transition_extends_only_to_window_end():
    intervals, diagnostics, anchor_diagnostics = reconcile_boundary_suspension_anchors(
        pd.DataFrame(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        pd.DataFrame(),
        _suspended_anchor("2025-01-10"),
        _coverage(),
    )
    assert diagnostics.empty
    assert len(intervals) == 1
    interval = intervals.iloc[0]
    assert interval["effective_from"] == pd.Timestamp("2025-01-10")
    assert interval["effective_to"] == pd.Timestamp("2025-01-31")
    assert anchor_diagnostics.loc[0, "status"] == "RESOLVED_TO_WINDOW_END"

    anchors = _suspended_anchor("2025-01-10")
    assert tradability_state(
        intervals,
        _coverage(),
        "TEST",
        pd.Timestamp("2025-01-09"),
        anchors=anchors,
    ).value == "UNKNOWN"
    assert tradability_state(
        intervals,
        _coverage(),
        "TEST",
        pd.Timestamp("2025-01-10"),
        anchors=anchors,
    ).value == "SUSPENDED"


def test_suspended_anchor_outside_complete_window_remains_unresolved():
    intervals, diagnostics, anchor_diagnostics = reconcile_boundary_suspension_anchors(
        _resume_event(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        pd.DataFrame(),
        _suspended_anchor(),
        canonicalize_coverage_windows(pd.DataFrame()),
    )
    assert intervals.empty
    assert diagnostics.empty
    assert anchor_diagnostics.loc[0, "status"] == "UNRESOLVED"
    assert (
        anchor_diagnostics.loc[0, "diagnostic"]
        == "ANCHOR_OUTSIDE_COMPLETE_DISCOVERY_WINDOW"
    )
