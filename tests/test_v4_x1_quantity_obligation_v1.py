from __future__ import annotations

import pytest

from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_decision_seat_policy_v1 import (
    DecisionSeatClosePolicyV1,
    SEAT_POLICY_SCHEMA,
)
from idx_trade.v4_x1_execution_v1_contract import (
    PaperPortfolioState,
    PaperPosition,
    PendingPaperIntent,
    close_obligation_explicitly,
    normalize_state,
    paper_state_hash,
    pending_intents_from_obligations,
)
from idx_trade.v4_x1_quantity_obligation_v1 import (
    apply_fill,
    cancel_remaining,
    mark_blocked,
    mark_retry,
    obligation_from_payload,
    obligation_hash,
    obligation_payload,
    plan_obligation,
)


def _planned():
    return plan_obligation(
        obligation_id="BUY-BBCA-2026-09-20-01",
        ticker="BBCA.JK",
        side="BUY",
        planned_shares=5_000,
        session_date="2026-09-20",
        replacement_group_id="REPLACE-AAA-BBCA-01",
        parent_state_sha256="a" * 64,
    )


def _seat_policy(*extra_reasons: str) -> DecisionSeatClosePolicyV1:
    return DecisionSeatClosePolicyV1(
        schema_version=SEAT_POLICY_SCHEMA,
        policy_id="synthetic-seat-close-policy",
        authorization_ref="synthetic-test-authority",
        allowed_close_statuses=("CANCELED", "RELINQUISHED"),
        allowed_close_reasons=tuple(sorted({
            "EXPLICIT_DECISION_REVERSAL_CLOSE",
            "EXPLICIT_RELINQUISH",
            "TARGET_REVERSAL",
            *extra_reasons,
        })),
    )


def test_positive_partial_fill_preserves_conserved_remainder_and_event_history():
    obligation = apply_fill(
        _planned(),
        event_id="FILL-1",
        session_date="2026-09-21",
        filled_shares=2_400,
        reason="OPEN_CAPACITY_PARTIAL",
        parent_state_sha256="b" * 64,
    )

    assert obligation.canonical_ticker == "BBCA"
    assert obligation.status == "PARTIAL"
    assert obligation.filled_shares == 2_400
    assert obligation.remaining_shares == 2_600
    assert obligation.relinquished_shares == 0
    assert obligation.planned_shares == (
        obligation.filled_shares
        + obligation.remaining_shares
        + obligation.relinquished_shares
    )
    assert obligation.attempt_count == 1
    assert obligation.event_history[-1].reason == "OPEN_CAPACITY_PARTIAL"


def test_duplicate_fill_event_is_idempotent_but_conflicting_replay_fails():
    one = apply_fill(
        _planned(),
        event_id="FILL-1",
        session_date="2026-09-21",
        filled_shares=2_400,
        reason="OPEN_CAPACITY_PARTIAL",
    )
    duplicate = apply_fill(
        one,
        event_id="FILL-1",
        session_date="2026-09-21",
        filled_shares=2_400,
        reason="OPEN_CAPACITY_PARTIAL",
    )
    assert duplicate == one
    advanced = apply_fill(
        one,
        event_id="FILL-2",
        session_date="2026-09-22",
        filled_shares=1_000,
        reason="RETRY",
    )
    assert apply_fill(
        advanced,
        event_id="FILL-1",
        session_date="2026-09-21",
        filled_shares=2_400,
        reason="OPEN_CAPACITY_PARTIAL",
    ) == advanced

    with pytest.raises(DecisionV1Error, match="EVENT_CONFLICT"):
        apply_fill(
            one,
            event_id="FILL-1",
            session_date="2026-09-21",
            filled_shares=2_500,
            reason="CONFLICTING_REPLAY",
        )


def test_retry_block_and_explicit_cancel_preserve_conservation():
    partial = apply_fill(
        _planned(),
        event_id="FILL-1",
        session_date="2026-09-21",
        filled_shares=2_400,
        reason="CAPACITY_PARTIAL",
    )
    blocked = mark_blocked(
        partial,
        event_id="BLOCK-1",
        session_date="2026-09-22",
        reason="ZERO_CAPACITY",
    )
    retried = mark_retry(
        blocked,
        event_id="RETRY-1",
        session_date="2026-09-23",
        reason="CAPACITY_REOPENED",
    )
    canceled = cancel_remaining(
        retried,
        event_id="CANCEL-1",
        session_date="2026-09-24",
        reason="TARGET_REVERSAL",
        seat_policy=_seat_policy(),
    )
    replayed_cancel = cancel_remaining(
        canceled,
        event_id="CANCEL-1",
        session_date="2026-09-24",
        reason="TARGET_REVERSAL",
        seat_policy=_seat_policy(),
    )
    with pytest.raises(DecisionV1Error, match="EVENT_CONFLICT"):
        cancel_remaining(
            canceled,
            event_id="CANCEL-1",
            session_date="2026-09-24",
            reason="TARGET_REVERSAL",
            seat_policy=_seat_policy("DIFFERENT_AUTHORIZED_REASON"),
        )

    assert blocked.status == "BLOCKED"
    assert retried.status == "PARTIAL"
    assert canceled.status == "CANCELED"
    assert canceled.remaining_shares == 0
    assert canceled.relinquished_shares == 2_600
    assert replayed_cancel == canceled
    assert canceled.planned_shares == (
        canceled.filled_shares
        + canceled.remaining_shares
        + canceled.relinquished_shares
    )
    assert canceled.attempt_count == 3
    assert [row.event_id for row in canceled.event_history] == [
        "BUY-BBCA-2026-09-20-01:PLANNED",
        "FILL-1",
        "BLOCK-1",
        "RETRY-1",
        "CANCEL-1",
    ]


def test_state_level_explicit_close_rebuilds_projection_and_binds_parent_hash():
    partial = apply_fill(
        _planned(),
        event_id="FILL-STATE-CLOSE",
        session_date="2026-09-21",
        filled_shares=2_400,
        reason="CAPACITY_PARTIAL",
    )
    pending_buys, pending_sells = pending_intents_from_obligations((partial,))
    state = PaperPortfolioState(
        as_of_session_date="2026-09-21",
        cash_idr=50_000_000,
        positions=(PaperPosition("BBCA", 2_400),),
        pending_buys=pending_buys,
        pending_sells=pending_sells,
        obligations=(partial,),
    )
    before_hash = paper_state_hash(state)

    closed = close_obligation_explicitly(
        state,
        obligation_id=partial.obligation_id,
        event_id="CLOSE-STATE-CLOSE",
        session_date="2026-09-21",
        reason="EXPLICIT_DECISION_REVERSAL_CLOSE",
        status="RELINQUISHED",
        parent_state_sha256=before_hash,
        seat_policy=_seat_policy(),
    )

    assert closed.obligations[0].status == "RELINQUISHED"
    assert closed.obligations[0].remaining_shares == 0
    assert closed.obligations[0].event_history[-1].parent_state_sha256 == before_hash
    assert closed.obligations[0].event_history[-1].policy_sha256 == (
        _seat_policy().payload()["policy_sha256"]
    )
    assert closed.pending_buys == ()
    assert closed.pending_sells == ()
    assert paper_state_hash(closed) != before_hash

    replayed = close_obligation_explicitly(
        closed,
        obligation_id=partial.obligation_id,
        event_id="CLOSE-STATE-CLOSE",
        session_date="2026-09-21",
        reason="EXPLICIT_DECISION_REVERSAL_CLOSE",
        status="RELINQUISHED",
        parent_state_sha256=before_hash,
        seat_policy=_seat_policy(),
    )
    assert replayed == closed

    with pytest.raises(DecisionV1Error, match="EVENT_CONFLICT"):
        close_obligation_explicitly(
            closed,
            obligation_id=partial.obligation_id,
            event_id="CLOSE-STATE-CLOSE",
            session_date="2026-09-21",
            reason="ALTERED_CLOSE_REASON",
            status="RELINQUISHED",
            parent_state_sha256=before_hash,
            seat_policy=_seat_policy("ALTERED_CLOSE_REASON"),
        )

    with pytest.raises(DecisionV1Error, match="CLOSE_PARENT_MISMATCH"):
        close_obligation_explicitly(
            state,
            obligation_id=partial.obligation_id,
            event_id="CLOSE-STATE-CLOSE-2",
            session_date="2026-09-21",
            reason="EXPLICIT_DECISION_REVERSAL_CLOSE",
            parent_state_sha256="0" * 64,
            seat_policy=_seat_policy(),
        )


def test_state_level_explicit_close_requires_hash_bound_policy() -> None:
    partial = apply_fill(
        _planned(),
        event_id="FILL-POLICY-REQUIRED",
        session_date="2026-09-21",
        filled_shares=2_400,
        reason="CAPACITY_PARTIAL",
    )
    pending_buys, pending_sells = pending_intents_from_obligations((partial,))
    state = PaperPortfolioState(
        as_of_session_date="2026-09-21",
        cash_idr=50_000_000,
        positions=(PaperPosition("BBCA", 2_400),),
        pending_buys=pending_buys,
        pending_sells=pending_sells,
        obligations=(partial,),
    )

    with pytest.raises(DecisionV1Error, match="SEAT_POLICY_REQUIRED"):
        close_obligation_explicitly(
            state,
            obligation_id=partial.obligation_id,
            event_id="CLOSE-POLICY-REQUIRED",
            session_date="2026-09-21",
            reason="EXPLICIT_DECISION_REVERSAL_CLOSE",
        )


def test_payload_round_trip_preserves_hash_and_lineage():
    obligation = cancel_remaining(
        apply_fill(
            _planned(),
            event_id="FILL-1",
            session_date="2026-09-21",
            filled_shares=2_400,
            reason="PARTIAL",
        ),
        event_id="CANCEL-1",
        session_date="2026-09-22",
        reason="EXPLICIT_RELINQUISH",
        status="RELINQUISHED",
        seat_policy=_seat_policy(),
    )
    reloaded = obligation_from_payload(obligation_payload(obligation))

    assert reloaded == obligation
    assert obligation_hash(reloaded) == obligation_hash(obligation)


def test_persisted_close_policy_envelope_is_restart_verifiable():
    obligation = cancel_remaining(
        apply_fill(
            _planned(),
            event_id="FILL-POLICY-REPLAY",
            session_date="2026-09-21",
            filled_shares=2_400,
            reason="PARTIAL",
        ),
        event_id="CANCEL-POLICY-REPLAY",
        session_date="2026-09-22",
        reason="EXPLICIT_RELINQUISH",
        status="RELINQUISHED",
        seat_policy=_seat_policy(),
    )

    tampered = obligation_payload(obligation)
    tampered["event_history"][-1]["policy_payload"] = _seat_policy(
        "OTHER_REASON"
    ).payload()
    with pytest.raises(
        DecisionV1Error,
        match="QUANTITY_OBLIGATION_CLOSE_POLICY_HASH_MISMATCH",
    ):
        obligation_from_payload(tampered)

    missing = obligation_payload(obligation)
    missing["event_history"][-1].pop("policy_payload")
    with pytest.raises(
        DecisionV1Error,
        match="QUANTITY_OBLIGATION_CLOSE_POLICY_PAYLOAD_REQUIRED",
    ):
        obligation_from_payload(missing)


def test_hash_valid_noncanonical_obligation_payload_fails_closed():
    payload = obligation_payload(_planned())
    payload["unexpected_extension"] = "accepted-by-hash-only"

    with pytest.raises(DecisionV1Error, match="PAYLOAD_NOT_CANONICAL"):
        obligation_from_payload(payload)


def test_conservation_and_closed_state_are_fail_closed():
    with pytest.raises(DecisionV1Error, match="CONSERVATION_FAILED"):
        obligation_from_payload(
            {
                "schema_version": "idx_trade_quantity_obligation_v1",
                "obligation_id": "BAD",
                "canonical_ticker": "BBCA",
                "side": "BUY",
                "planned_shares": 5_000,
                "filled_shares": 2_400,
                "remaining_shares": 2_500,
                "relinquished_shares": 0,
                "status": "PARTIAL",
                "created_session_date": "2026-09-20",
                "latest_attempt_session_date": "2026-09-21",
                "attempt_count": 1,
                "replacement_group_id": None,
                "parent_state_sha256": None,
                "event_history": [],
            }
        )

    with pytest.raises(DecisionV1Error, match="CLOSED_WITH_REMAINDER"):
        obligation_from_payload(
            {
                "schema_version": "idx_trade_quantity_obligation_v1",
                "obligation_id": "BAD-CLOSED",
                "canonical_ticker": "BBCA",
                "side": "BUY",
                "planned_shares": 5_000,
                "filled_shares": 2_400,
                "remaining_shares": 2_600,
                "relinquished_shares": 0,
                "status": "FILLED",
                "created_session_date": "2026-09-20",
                "latest_attempt_session_date": "2026-09-21",
                "attempt_count": 0,
                "replacement_group_id": None,
                "parent_state_sha256": None,
                "event_history": [],
            }
        )


def test_partial_buy_projects_pending_remainder_even_when_position_exists():
    partial = apply_fill(
        _planned(),
        event_id="FILL-1",
        session_date="2026-09-21",
        filled_shares=2_400,
        reason="OPEN_CAPACITY_PARTIAL",
    )
    pending_buys, pending_sells = pending_intents_from_obligations((partial,))
    state = PaperPortfolioState(
        as_of_session_date="2026-09-21",
        cash_idr=1_000_000.0,
        positions=(PaperPosition("BBCA", 2_400),),
        pending_buys=pending_buys,
        pending_sells=pending_sells,
        obligations=(partial,),
    )

    normalize_state(state)
    assert pending_buys == (
        PendingPaperIntent(
            side="BUY",
            ticker="BBCA",
            rank_consensus=None,
            reason="OPEN_CAPACITY_PARTIAL",
            replacement_peer="REPLACE-AAA-BBCA-01",
        ),
    )
    assert pending_sells == ()

    with pytest.raises(DecisionV1Error, match="PROJECTION_MISMATCH"):
        normalize_state(
            PaperPortfolioState(
                as_of_session_date=state.as_of_session_date,
                cash_idr=state.cash_idr,
                positions=state.positions,
                pending_buys=(),
                obligations=state.obligations,
            )
        )


@pytest.mark.parametrize("shares", [100.9, True])
def test_normalize_state_rejects_non_integer_position_shares(shares: object) -> None:
    with pytest.raises(DecisionV1Error, match="POSITION_NOT_WHOLE_LOT"):
        normalize_state(
            PaperPortfolioState(
                as_of_session_date="2026-09-21",
                cash_idr=1_000_000.0,
                positions=(PaperPosition("BBCA", shares),),
            )
        )


@pytest.mark.parametrize("rank", [1.9, True, 0])
def test_normalize_state_rejects_invalid_pending_rank(rank: object) -> None:
    with pytest.raises(DecisionV1Error, match="PENDING_RANK_INVALID"):
        normalize_state(
            PaperPortfolioState(
                as_of_session_date="2026-09-21",
                cash_idr=1_000_000.0,
                positions=(),
                pending_buys=(PendingPaperIntent("BUY", "BBCA", rank, "RETRY"),),
            )
        )


def test_legacy_hash_shape_is_unchanged_and_obligation_hash_is_additive():
    legacy = PaperPortfolioState(
        as_of_session_date="2026-09-20",
        cash_idr=1_000_000.0,
        positions=(),
    )
    partial = apply_fill(
        _planned(),
        event_id="FILL-1",
        session_date="2026-09-21",
        filled_shares=2_400,
        reason="OPEN_CAPACITY_PARTIAL",
    )
    buys, sells = pending_intents_from_obligations((partial,))
    modern = PaperPortfolioState(
        as_of_session_date=legacy.as_of_session_date,
        cash_idr=legacy.cash_idr,
        positions=(PaperPosition("BBCA", 2_400),),
        pending_buys=buys,
        pending_sells=sells,
        obligations=(partial,),
    )

    assert paper_state_hash(legacy) != paper_state_hash(modern)
