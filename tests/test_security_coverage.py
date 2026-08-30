import pandas as pd
import pytest

import idx_trade.security_master as security_master_module
from idx_trade.coverage import security_coverage
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
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


def _complete_window():
    return canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "market": ["REGULAR"],
                "effective_from": ["2025-01-01"],
                "effective_to": ["2025-12-31"],
                "source": ["IDX_RECONSTRUCTION"],
                "is_complete": [True],
                "discovery_basis": ["IDX_PUBLIC_DISCOVERY_AUDIT"],
                "left_boundary_basis": ["IDX_ARCHIVE_START_AUDIT"],
            }
        )
    )


def _active_anchor(date: str = "2025-01-01"):
    return canonicalize_tradability_anchors(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "as_of_date": [date],
                "state": ["ACTIVE"],
                "source": ["IDX_OFFICIAL_STATUS"],
                "source_ref": ["idx://active-test"],
                "evidence_type": ["OFFICIAL_ACTIVE_STATUS"],
            }
        )
    )


def _cache_safe_window():
    return canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "market": ["REGULAR"],
                "effective_from": ["2026-01-01"],
                "effective_to": ["2026-01-20"],
                "source": ["IDX_RECONSTRUCTION"],
                "is_complete": [True],
                "discovery_basis": ["IDX_PUBLIC_DISCOVERY_AUDIT"],
                "left_boundary_basis": ["IDX_ARCHIVE_START_AUDIT"],
            }
        )
    )


def _clear_security_master_caches() -> None:
    for store in (
        security_master_module._INTERVAL_SCOPE_CACHE,
        security_master_module._ANCHOR_SCOPE_CACHE,
        security_master_module._ANCHOR_STATE_CACHE,
    ):
        store.clear()


def test_absence_of_tradability_history_fails_closed_to_unknown():
    master = _master()
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    windows = canonicalize_coverage_windows(pd.DataFrame())
    assert existence_state(master, "TEST", pd.Timestamp("2025-01-03")) is ExistenceState.LISTED
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2025-01-03")) is TradabilityState.UNKNOWN


def test_complete_discovery_window_without_ticker_anchor_stays_unknown():
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    assert tradability_state(
        intervals,
        _complete_window(),
        "TEST",
        pd.Timestamp("2025-01-03"),
    ) is TradabilityState.UNKNOWN


def test_future_active_anchor_never_classifies_earlier_session():
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    future_anchor = _active_anchor("2025-01-10")
    assert tradability_state(
        intervals,
        _complete_window(),
        "TEST",
        pd.Timestamp("2025-01-09"),
        anchors=future_anchor,
    ) is TradabilityState.UNKNOWN
    assert tradability_state(
        intervals,
        _complete_window(),
        "TEST",
        pd.Timestamp("2025-01-10"),
        anchors=future_anchor,
    ) is TradabilityState.ACTIVE


def test_active_anchor_allows_forward_complement_but_suspension_overrides():
    intervals = canonicalize_tradability_intervals(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["ALL"],
                "state": ["SUSPENDED"],
                "effective_from": ["2025-01-06"],
                "effective_to": ["2025-01-07"],
                "announced_at": ["2025-01-05"],
                "source": ["IDX"],
                "source_ref": ["announcement-1"],
            }
        )
    )
    anchors = _active_anchor()
    assert tradability_state(
        intervals,
        _complete_window(),
        "TEST",
        pd.Timestamp("2025-01-03"),
        anchors=anchors,
    ) is TradabilityState.ACTIVE
    assert tradability_state(
        intervals,
        _complete_window(),
        "TEST",
        pd.Timestamp("2025-01-06"),
        anchors=anchors,
    ) is TradabilityState.SUSPENDED


def test_negotiated_only_unsuspension_does_not_make_regular_market_active():
    intervals = canonicalize_tradability_intervals(
        pd.DataFrame(
            {
                "ticker": ["TEST", "TEST"],
                "market": ["ALL", "NEGOTIATED"],
                "state": ["SUSPENDED", "ACTIVE"],
                "effective_from": ["2025-07-17", "2025-07-17"],
                "effective_to": ["2025-07-17", "2025-07-17"],
                "announced_at": ["2025-07-17", "2025-07-17"],
                "source": ["IDX", "IDX"],
                "source_ref": ["suspend-all", "negotiated-only-window"],
            }
        )
    )
    empty_windows = canonicalize_coverage_windows(pd.DataFrame())
    session = pd.Timestamp("2025-07-17")
    assert tradability_state(intervals, empty_windows, "TEST", session, market="REGULAR") is TradabilityState.SUSPENDED
    assert tradability_state(intervals, empty_windows, "TEST", session, market="NEGOTIATED") is TradabilityState.ACTIVE


def test_coverage_does_not_pass_merely_because_many_rows_exist():
    master = _master()
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    sessions = pd.bdate_range("2025-01-01", periods=100)
    observed = sessions[:60]
    report = security_coverage(
        "TEST",
        sessions,
        observed,
        master,
        intervals,
        _complete_window(),
        tradability_anchors=_active_anchor(),
    )
    assert report.observed_active_sessions == 60
    assert report.missing_expected_sessions == 40
    assert report.coverage_ratio == 0.60
    assert report.complete is False


def test_complete_claim_without_boundary_basis_stays_unknown():
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    claimed = canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "market": ["REGULAR"],
                "effective_from": ["2025-01-01"],
                "effective_to": ["2025-12-31"],
                "source": ["UNSUPPORTED_CLAIM"],
                "is_complete": [True],
            }
        )
    )
    assert bool(claimed.loc[0, "is_complete"]) is False
    assert tradability_state(
        intervals,
        claimed,
        "TEST",
        pd.Timestamp("2025-01-03"),
        anchors=_active_anchor(),
    ) is TradabilityState.UNKNOWN


def test_suspended_sessions_are_not_expected_as_price_rows():
    master = _master()
    intervals = canonicalize_tradability_intervals(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "state": ["SUSPENDED"],
                "effective_from": ["2025-01-06"],
                "effective_to": ["2025-01-07"],
                "announced_at": ["2025-01-05"],
                "source": ["IDX"],
                "source_ref": ["announcement-1"],
            }
        )
    )
    sessions = pd.bdate_range("2025-01-01", "2025-01-10")
    observed = sessions.difference(pd.to_datetime(["2025-01-06", "2025-01-07"]))
    report = security_coverage(
        "TEST",
        sessions,
        observed,
        master,
        intervals,
        _complete_window(),
        tradability_anchors=_active_anchor(),
    )
    assert report.missing_expected_sessions == 0
    assert report.unknown_tradability_sessions == 0
    assert report.complete is True


def test_conflicting_anchor_and_reconstructed_state_fails_hard():
    intervals = canonicalize_tradability_intervals(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "state": ["SUSPENDED"],
                "effective_from": ["2025-01-06"],
                "effective_to": ["2025-01-07"],
                "source": ["IDX"],
            }
        )
    )
    conflicting = canonicalize_tradability_anchors(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "as_of_date": ["2025-01-06"],
                "state": ["ACTIVE"],
                "source": ["IDX_STATUS"],
                "source_ref": ["idx://conflict"],
                "evidence_type": ["OFFICIAL_ACTIVE_STATUS"],
            }
        )
    )
    with pytest.raises(ValueError, match="conflicts with reconstructed"):
        tradability_state(
            intervals,
            _complete_window(),
            "TEST",
            pd.Timestamp("2025-01-08"),
            anchors=conflicting,
        )


def test_ipo_warmup_is_explicit_eligibility_state():
    master = _master()
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    anchors = _active_anchor()
    early = model_eligibility(
        master,
        intervals,
        _complete_window(),
        "TEST",
        pd.Timestamp("2025-02-01"),
        20,
        60,
        tradability_anchors=anchors,
    )
    mature = model_eligibility(
        master,
        intervals,
        _complete_window(),
        "TEST",
        pd.Timestamp("2025-04-01"),
        60,
        60,
        tradability_anchors=anchors,
    )
    assert not early.eligible and early.reason == "IPO_WARMUP"
    assert mature.eligible and mature.reason == "ELIGIBLE"


def test_market_interval_precedence_is_date_applicable_and_cache_order_independent():
    intervals = canonicalize_tradability_intervals(
        pd.DataFrame(
            [
                {
                    "ticker": "TEST",
                    "market": "ALL",
                    "state": "ACTIVE",
                    "effective_from": "2026-01-05",
                    "effective_to": "2026-01-20",
                    "source": "IDX",
                    "source_ref": "all",
                },
                {
                    "ticker": "TEST",
                    "market": "REGULAR",
                    "state": "NO_TRADE",
                    "effective_from": "2026-01-10",
                    "effective_to": "2026-01-15",
                    "source": "IDX",
                    "source_ref": "regular",
                },
            ]
        )
    )
    windows = _cache_safe_window()

    _clear_security_master_caches()
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2026-01-10")) is TradabilityState.NO_TRADE
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2026-01-06")) is TradabilityState.ACTIVE

    _clear_security_master_caches()
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2026-01-06")) is TradabilityState.ACTIVE
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2026-01-10")) is TradabilityState.NO_TRADE


def test_market_anchor_precedence_is_date_applicable_and_cache_order_independent():
    anchors = canonicalize_tradability_anchors(
        pd.DataFrame(
            [
                {
                    "ticker": "TEST",
                    "market": "ALL",
                    "as_of_date": "2026-01-05",
                    "state": "ACTIVE",
                    "source": "IDX",
                    "source_ref": "all",
                    "evidence_type": "POINT",
                },
                {
                    "ticker": "TEST",
                    "market": "REGULAR",
                    "as_of_date": "2026-01-10",
                    "state": "SUSPENDED",
                    "source": "IDX",
                    "source_ref": "regular",
                    "evidence_type": "POINT",
                },
            ]
        )
    )
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    windows = _cache_safe_window()

    _clear_security_master_caches()
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2026-01-10"), anchors=anchors) is TradabilityState.SUSPENDED
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2026-01-06"), anchors=anchors) is TradabilityState.ACTIVE

    _clear_security_master_caches()
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2026-01-06"), anchors=anchors) is TradabilityState.ACTIVE
    assert tradability_state(intervals, windows, "TEST", pd.Timestamp("2026-01-10"), anchors=anchors) is TradabilityState.SUSPENDED


@pytest.mark.parametrize("value", ["no", "garbage", " ", None, float("nan"), 1, 0])
def test_coverage_is_complete_rejects_non_boolean_tokens(value):
    with pytest.raises(ValueError, match="strict boolean"):
        canonicalize_coverage_windows(
            pd.DataFrame(
                {
                    "market": ["REGULAR"],
                    "effective_from": ["2026-01-01"],
                    "effective_to": ["2026-01-20"],
                    "source": ["TEST"],
                    "is_complete": [value],
                    "discovery_basis": ["D"],
                    "left_boundary_basis": ["L"],
                }
            )
        )


@pytest.mark.parametrize("value, expected", [("False", False), ("false", False), ("True", True), ("true", True)])
def test_coverage_is_complete_accepts_only_explicit_boolean_tokens(value, expected):
    result = canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "market": ["REGULAR"],
                "effective_from": ["2026-01-01"],
                "effective_to": ["2026-01-20"],
                "source": ["TEST"],
                "is_complete": [value],
                "discovery_basis": ["D"],
                "left_boundary_basis": ["L"],
            }
        )
    )
    assert bool(result.loc[0, "is_complete"]) is expected


@pytest.mark.parametrize("source_ref", [None, "", "   "])
def test_authoritative_anchor_requires_non_empty_source_ref(source_ref):
    row = {
        "ticker": "TEST",
        "market": "REGULAR",
        "as_of_date": "2026-01-01",
        "state": "ACTIVE",
        "source": "IDX",
        "evidence_type": "POINT",
    }
    if source_ref is not None:
        row["source_ref"] = source_ref
    expected = "columns missing" if source_ref is None else "source_ref must be non-empty"
    with pytest.raises(ValueError, match=expected):
        canonicalize_tradability_anchors(pd.DataFrame([row]))
