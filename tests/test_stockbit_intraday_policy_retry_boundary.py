from __future__ import annotations

from datetime import date

from idx_trade.stockbit_intraday_recovery import apply_policy_event_once


def test_incomplete_retry_slot_does_not_consume_policy_session_date():
    policy = {
        "mode": "SHADOW",
        "consecutive_zero_fn_shadow_sessions": 0,
        "enforced_sessions_since_recheck": 0,
        "history": [],
    }
    interim, applied = apply_policy_event_once(
        policy,
        session_date=date(2026, 8, 26),
        run_mode="SHADOW",
        complete=False,
        false_negative=None,
        certification_eligible=None,
        manifest_sha256="",
    )
    assert applied is False
    assert interim["history"] == []
    assert interim["consecutive_zero_fn_shadow_sessions"] == 0

    final, final_applied = apply_policy_event_once(
        interim,
        session_date=date(2026, 8, 26),
        run_mode="SHADOW",
        complete=True,
        false_negative=0,
        certification_eligible=True,
        manifest_sha256="a" * 64,
    )
    assert final_applied is True
    assert len(final["history"]) == 1
    assert final["consecutive_zero_fn_shadow_sessions"] == 1
