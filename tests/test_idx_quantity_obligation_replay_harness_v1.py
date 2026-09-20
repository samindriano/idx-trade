from research.idx_quantity_obligation_replay_harness_v1 import (
    ObligationContractError,
    ReplayState,
    apply_fill,
    legacy_quantity_classification,
    plan_obligation,
    run_spec_scenario,
)


def test_spec_scenario_preserves_quantity_ca_and_reversal_invariants():
    result = run_spec_scenario()

    assert result["after_first_fill"]["filled"] == 2_400
    assert result["after_first_fill"]["remaining"] == 2_600
    assert result["duplicate_fill_idempotent"] is True
    assert result["after_retry"]["filled"] == 3_400
    assert result["after_retry"]["remaining"] == 1_600
    assert result["ca_entitlement_shares"] == 3_400
    assert result["ca_payment_idr"] == 85_000.0
    assert result["after_reversal"]["remaining"] == 0
    assert result["after_reversal"]["relinquished"] == 1_600
    assert result["duplicate_cancel_idempotent"] is True


def test_legacy_positive_partial_without_plan_is_unknown_not_inferred():
    assert legacy_quantity_classification(
        planned_shares=None, filled_shares=2_400,
    ) == "UNKNOWN_ORPHANED_PARTIAL"


def test_planned_quantity_conservation_rejects_fabricated_state():
    obligation = plan_obligation(
        obligation_id="O1", ticker="AAA", side="BUY", planned_shares=5_000,
        session_date="2026-08-21",
    )
    state = run_spec_scenario()
    assert obligation.planned_shares == 5_000
    assert state["after_reversal"]["filled"] + state["after_reversal"]["relinquished"] == 5_000

    try:
        apply_fill(
            ReplayState(
                session_date="2026-08-21",
                cash_idr=1_000_000.0,
                position_shares=0,
                obligation=obligation,
            ),
            event_id="FILL-BAD", session_date="2026-08-22",
            filled_shares=5_100, reason="OVERFILL",
        )
    except ObligationContractError as exc:
        assert str(exc) == "FILL_EXCEEDS_REMAINING"
    else:
        raise AssertionError("overfill was accepted")
