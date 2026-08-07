import pandas as pd

from idx_trade.coverage import security_coverage
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_intervals,
    existence_state,
    model_eligibility,
    tradability_state,
)
from idx_trade.states import ExistenceState, TradabilityState


def _master():
    active = pd.DataFrame(
        {
            "ticker": ["TEST"],
            "company_name": ["Test Tbk"],
            "listed_from": ["2025-01-01"],
            "listed_to": [None],
            "source": ["IDX"],
        }
    )
    return build_security_master(active, pd.DataFrame())


def test_absence_of_tradability_history_fails_closed_to_unknown():
    master = _master()
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    windows = canonicalize_coverage_windows(pd.DataFrame())
    assert existence_state(master, "TEST", pd.Timestamp("2025-01-03")) is ExistenceState.LISTED
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2025-01-03")) is TradabilityState.UNKNOWN


def test_complete_reconstruction_window_allows_active_complement_but_suspension_overrides():
    intervals = canonicalize_tradability_intervals(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "state": ["SUSPENDED"],
                "effective_from": ["2025-01-06"],
                "effective_to": ["2025-01-07"],
                "announced_at": ["2025-01-05"],
                "source": ["IDX"],
                "source_ref": ["announcement-1"],
            }
        )
    )
    windows = canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "effective_from": ["2025-01-01"],
                "effective_to": ["2025-12-31"],
                "source": ["IDX_RECONSTRUCTION"],
                "is_complete": [True],
            }
        )
    )
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2025-01-03")) is TradabilityState.ACTIVE
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2025-01-06")) is TradabilityState.SUSPENDED


def test_coverage_does_not_pass_merely_because_many_rows_exist():
    master = _master()
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    windows = canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "effective_from": ["2025-01-01"],
                "effective_to": ["2025-12-31"],
                "source": ["IDX_RECONSTRUCTION"],
                "is_complete": [True],
            }
        )
    )
    sessions = pd.bdate_range("2025-01-01", periods=100)
    # 60 rows would have passed V1's row-count gate; V2 must expose the 40 missing sessions.
    observed = sessions[:60]
    report = security_coverage("TEST", sessions, observed, master, intervals, windows)
    assert report.observed_active_sessions == 60
    assert report.missing_expected_sessions == 40
    assert report.coverage_ratio == 0.60
    assert report.complete is False


def test_suspended_sessions_are_not_expected_as_price_rows():
    master = _master()
    intervals = canonicalize_tradability_intervals(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "state": ["SUSPENDED"],
                "effective_from": ["2025-01-06"],
                "effective_to": ["2025-01-07"],
                "announced_at": ["2025-01-05"],
                "source": ["IDX"],
                "source_ref": ["announcement-1"],
            }
        )
    )
    windows = canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "effective_from": ["2025-01-01"],
                "effective_to": ["2025-01-31"],
                "source": ["IDX_RECONSTRUCTION"],
                "is_complete": [True],
            }
        )
    )
    sessions = pd.bdate_range("2025-01-01", "2025-01-10")
    observed = sessions.difference(pd.to_datetime(["2025-01-06", "2025-01-07"]))
    report = security_coverage("TEST", sessions, observed, master, intervals, windows)
    assert report.missing_expected_sessions == 0
    assert report.unknown_tradability_sessions == 0
    assert report.complete is True


def test_ipo_warmup_is_explicit_eligibility_state():
    master = _master()
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    windows = canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "effective_from": ["2025-01-01"],
                "effective_to": ["2025-12-31"],
                "source": ["IDX_RECONSTRUCTION"],
                "is_complete": [True],
            }
        )
    )
    early = model_eligibility(master, intervals, windows, "TEST", pd.Timestamp("2025-02-01"), 20, 60)
    mature = model_eligibility(master, intervals, windows, "TEST", pd.Timestamp("2025-04-01"), 60, 60)
    assert not early.eligible and early.reason == "IPO_WARMUP"
    assert mature.eligible and mature.reason == "ELIGIBLE"
