from __future__ import annotations

from idx_trade.decision_v2_minimal import DecisionV2Intent, DecisionV2Plan
from idx_trade.v4_x1_execution_cause_v1 import derive_execution_causes
from idx_trade.v4_x1_execution_v1_contract import (
    ExecutionResult,
    FillRecord,
    PaperPortfolioState,
    PaperPosition,
    paper_state_hash,
    pending_intents_from_obligations,
)
from idx_trade.v4_x1_identity_contract_v1 import SecurityIdentityV1
from idx_trade.v4_x1_quantity_obligation_v1 import apply_fill, plan_obligation
from idx_trade.v4_x1_transition_binding_v1 import (
    build_cause_obligation_binding_v1,
    build_decision_identity_binding_v1,
    verify_decision_identity_binding_v1,
)


def _identity(ticker: str = "BBCA") -> SecurityIdentityV1:
    return SecurityIdentityV1(
        canonical_security_id=f"ISSUER-{ticker}",
        ticker=ticker,
        instrument_class="COMMON_SHARE",
        effective_from="2026-01-01",
        effective_to=None,
        identity_revision="R1",
        source_ref=f"idx://identity/{ticker}",
        source_evidence_sha256="a" * 64,
    )


def test_decision_identity_binding_is_persisted_and_revalidated() -> None:
    plan = DecisionV2Plan(
        decision_session_date="2026-09-01",
        current_shadow_positions=(),
        target_positions=("BBCA",),
        buy_intents=(DecisionV2Intent("BUY_INTENT", "BBCA", 1, "TEST"),),
        sell_intents=(),
        hold_tickers=(),
        incumbent_observations=(),
        challenger_observations=(),
        unfilled_slots=0,
        capacity_state="FULL",
        rule_id="TEST_RULE",
    )
    binding = build_decision_identity_binding_v1(plan, (_identity(),))
    verified = verify_decision_identity_binding_v1(binding, (_identity(),))
    assert verified["binding_type"] == "DECISION_IDENTITY"
    assert verified["resolutions"][0]["canonical_security_id"] == "ISSUER-BBCA"


def test_cause_binding_exposes_retry_transition_for_partial_obligation() -> None:
    before = PaperPortfolioState("2026-09-01", 1_000_000.0, ())
    obligation = plan_obligation(
        obligation_id="2026-09-02:BUY:BBCA:test",
        ticker="BBCA",
        side="BUY",
        planned_shares=200,
        session_date="2026-09-01",
        parent_state_sha256=paper_state_hash(before),
    )
    obligation = apply_fill(
        obligation,
        event_id="2026-09-02:BUY:BBCA:test:FILL",
        session_date="2026-09-02",
        filled_shares=100,
        reason="PARTIAL_CAPACITY",
        parent_state_sha256=paper_state_hash(before),
    )
    pending_buys, pending_sells = pending_intents_from_obligations((obligation,))
    after = PaperPortfolioState(
        "2026-09-02",
        998_998.5,
        (PaperPosition("BBCA", 100),),
        pending_buys=pending_buys,
        pending_sells=pending_sells,
        obligations=(obligation,),
    )
    result = ExecutionResult(
        execution_session_date="2026-09-02",
        state_before_hash=paper_state_hash(before),
        state_after=after,
        fills=(
            FillRecord(
                "BUY", "BBCA", 200, 100, 10_000.0, 10_000.0,
                1_000.0, 1.5, -1_001.5, "SIMULATED_PARTIAL", None,
            ),
        ),
        stamp_duty_idr=0.0,
        gross_turnover_idr=1_000.0,
        pending_transition_count=1,
        reconciliation_required=False,
    )
    causes = derive_execution_causes(result, state_before=before)
    binding = build_cause_obligation_binding_v1(result, causes)
    assert binding["joins"][0]["obligation_id"] == obligation.obligation_id
    assert binding["joins"][0]["next_decision_action"] == "RETRY_OBLIGATION"
