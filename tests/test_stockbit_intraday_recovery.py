from __future__ import annotations

from datetime import date

import pytest

from idx_trade.stockbit_intraday_recovery import (
    SKIPPED_IDX_NO_ACTIVITY,
    SUCCESS,
    apply_policy_event_once,
    build_recovery_plan,
    completion_state,
)


def test_request_error_is_retried_but_success_is_not():
    tickers = ["BBCA", "BBRI", "BMRI"]
    statuses = {
        "BBCA": {"status": SUCCESS},
        "BBRI": {"status": "REQUEST_ERROR"},
    }

    plan = build_recovery_plan(tickers, statuses)

    assert plan.admissible_terminal == ("BBCA",)
    assert plan.retry == ("BBRI",)
    assert plan.missing == ("BMRI",)
    assert plan.pending == ("BMRI", "BBRI")


def test_gate_skip_is_terminal_and_never_retried():
    tickers = ["BBCA", "ZERO"]
    statuses = {
        "BBCA": SUCCESS,
        "ZERO": SKIPPED_IDX_NO_ACTIVITY,
    }

    plan = build_recovery_plan(tickers, statuses)
    state = completion_state(tickers, statuses)

    assert plan.retry == ()
    assert plan.pending == ()
    assert plan.admissible_terminal == ("BBCA", "ZERO")
    assert state.admissible_complete is True


def test_attempted_everywhere_is_not_complete_when_request_error_exists():
    tickers = ["BBCA", "BBRI"]
    statuses = {
        "BBCA": SUCCESS,
        "BBRI": "REQUEST_ERROR",
    }

    state = completion_state(tickers, statuses)

    assert state.observed_count == 2
    assert state.all_observed is True
    assert state.retryable_count == 1
    assert state.all_terminal is False
    assert state.admissible_complete is False


def test_blocking_payload_error_is_terminal_but_not_admissible():
    tickers = ["BBCA", "BBRI"]
    statuses = {
        "BBCA": SUCCESS,
        "BBRI": "TRADING_DATE_METADATA_MISMATCH",
    }

    plan = build_recovery_plan(tickers, statuses)
    state = completion_state(tickers, statuses)

    assert plan.pending == ()
    assert plan.blocking_terminal == ("BBRI",)
    assert state.all_observed is True
    assert state.all_terminal is True
    assert state.blocking_count == 1
    assert state.admissible_complete is False


def test_unknown_status_fails_closed_and_is_not_silently_retried():
    tickers = ["BBCA"]
    plan = build_recovery_plan(tickers, {"BBCA": "SOMETHING_NEW"})
    state = completion_state(tickers, {"BBCA": "SOMETHING_NEW"})

    assert plan.pending == ()
    assert plan.unknown_blocking == ("BBCA",)
    assert state.blocking_count == 1
    assert state.admissible_complete is False


def test_duplicate_universe_identity_is_rejected():
    with pytest.raises(ValueError, match="duplicate ticker"):
        build_recovery_plan(["BBCA", "BBCA"], {})


def _policy() -> dict:
    return {
        "mode": "SHADOW",
        "consecutive_zero_fn_shadow_sessions": 0,
        "enforced_sessions_since_recheck": 0,
        "history": [],
    }


def test_identical_policy_event_replay_is_noop_not_double_count():
    first, applied = apply_policy_event_once(
        _policy(),
        session_date=date(2026, 8, 27),
        run_mode="SHADOW",
        complete=True,
        false_negative=0,
        certification_eligible=True,
        manifest_sha256="a" * 64,
    )
    assert applied is True
    assert first["consecutive_zero_fn_shadow_sessions"] == 1
    assert len(first["history"]) == 1

    replay, replay_applied = apply_policy_event_once(
        first,
        session_date=date(2026, 8, 27),
        run_mode="SHADOW",
        complete=True,
        false_negative=0,
        certification_eligible=True,
        manifest_sha256="a" * 64,
    )

    assert replay_applied is False
    assert replay["consecutive_zero_fn_shadow_sessions"] == 1
    assert len(replay["history"]) == 1


def test_same_session_with_different_manifest_is_conflict():
    first, _ = apply_policy_event_once(
        _policy(),
        session_date=date(2026, 8, 27),
        run_mode="SHADOW",
        complete=True,
        false_negative=0,
        certification_eligible=True,
        manifest_sha256="a" * 64,
    )

    with pytest.raises(ValueError, match="conflicting Stockbit intraday policy event"):
        apply_policy_event_once(
            first,
            session_date=date(2026, 8, 27),
            run_mode="SHADOW",
            complete=True,
            false_negative=0,
            certification_eligible=True,
            manifest_sha256="b" * 64,
        )


def test_same_manifest_but_different_event_is_conflict():
    first, _ = apply_policy_event_once(
        _policy(),
        session_date=date(2026, 8, 27),
        run_mode="SHADOW",
        complete=True,
        false_negative=0,
        certification_eligible=True,
        manifest_sha256="a" * 64,
    )

    with pytest.raises(ValueError, match="conflicting Stockbit intraday policy event"):
        apply_policy_event_once(
            first,
            session_date=date(2026, 8, 27),
            run_mode="SHADOW",
            complete=True,
            false_negative=1,
            certification_eligible=True,
            manifest_sha256="a" * 64,
        )


def test_three_distinct_zero_fn_sessions_promote_only_after_three_dates():
    policy = _policy()
    for day in (27, 28, 31):
        policy, applied = apply_policy_event_once(
            policy,
            session_date=date(2026, 8, day),
            run_mode="SHADOW",
            complete=True,
            false_negative=0,
            certification_eligible=True,
            manifest_sha256=(str(day) * 32)[:64],
        )
        assert applied is True

    assert policy["mode"] == "ENFORCE"
    assert policy["consecutive_zero_fn_shadow_sessions"] == 3
    assert len(policy["history"]) == 3
