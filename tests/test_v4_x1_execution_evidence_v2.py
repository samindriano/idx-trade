from __future__ import annotations

from dataclasses import replace

from idx_trade.v4_x1_execution_evidence_v2 import (
    EXECUTION_EVIDENCE_SCHEMA,
    build_execution_evidence_v2,
    evaluate_execution_evidence_v2,
)
from idx_trade.v4_x1_execution_v1_contract import (
    ExecutionOrderPlan,
    ExecutionResult,
    FillRecord,
    PaperPortfolioState,
    PaperPosition,
    paper_state_hash,
)
from idx_trade.v4_x1_sizing_v1 import SizingPlan, _SIZING_PLAN_TOKEN


def _plan(state: PaperPortfolioState) -> ExecutionOrderPlan:
    sizing = SizingPlan(
        decision_session_date="2026-09-01",
        nav_idr=1_000_000.0,
        available_cash_idr=1_000_000.0,
        target_weight_per_name=0.10,
        max_entry_weight_per_name=0.15,
        entries=(),
        total_sized_notional=0.0,
        residual_cash_after_sizing_reference=1_000_000.0,
        _verification_token=_SIZING_PLAN_TOKEN,
    )
    return ExecutionOrderPlan(
        decision_session_date="2026-09-01",
        execution_session_date="2026-09-02",
        state_hash=paper_state_hash(state),
        eod_nav_idr=1_000_000.0,
        projected_cash_for_sizing_idr=1_000_000.0,
        sizing_plan=sizing,
        sells=(),
        effective_buy_intents=(),
        target_positions=(),
        regular_market_values_t={},
        eod_ohlcv_sha256="a" * 64,
        eod_model_input_sha256="b" * 64,
        official_calendar_sha256="c" * 64,
    )


def test_execution_evidence_v2_replays_quantity_and_parent_state() -> None:
    before = PaperPortfolioState("2026-09-01", 1_000_000.0, ())
    after = PaperPortfolioState(
        "2026-09-02",
        998_998.5,
        (PaperPosition("BBCA", 100),),
    )
    plan = _plan(before)
    result = ExecutionResult(
        execution_session_date="2026-09-02",
        state_before_hash=paper_state_hash(before),
        state_after=after,
        fills=(
            FillRecord(
                "BUY", "BBCA", 100, 100, 10_000.0, 10_000.0,
                1_000.0, 1.5, -1_001.5,
                "SIMULATED_FILLED",
            ),
        ),
        stamp_duty_idr=0.0,
        gross_turnover_idr=1_000.0,
        pending_transition_count=0,
        reconciliation_required=False,
    )

    evidence = build_execution_evidence_v2(plan, result)
    evaluation = evaluate_execution_evidence_v2(
        evidence,
        expected_order_plan=plan,
        expected_state_before=before,
    )

    assert evaluation.status == "PASS"
    assert "state_before_parent" in evaluation.checks
    assert evidence.payload()["schema_version"] == EXECUTION_EVIDENCE_SCHEMA
    assert evidence.payload()["fills"][0]["filled_shares"] == 100


def test_execution_evidence_v2_rejects_tampered_aggregate() -> None:
    before = PaperPortfolioState("2026-09-01", 1_000_000.0, ())
    after = PaperPortfolioState("2026-09-02", 1_000_000.0, ())
    plan = _plan(before)
    result = ExecutionResult(
        execution_session_date="2026-09-02",
        state_before_hash=paper_state_hash(before),
        state_after=after,
        fills=(),
        stamp_duty_idr=0.0,
        gross_turnover_idr=0.0,
        pending_transition_count=0,
        reconciliation_required=False,
    )
    evidence = build_execution_evidence_v2(plan, result)
    tampered = replace(evidence, gross_turnover_idr=1.0)

    evaluation = evaluate_execution_evidence_v2(tampered, expected_order_plan=plan)

    assert evaluation.status == "FAIL"
    assert "EXECUTION_EVIDENCE_V2_GROSS_TURNOVER_MISMATCH" in evaluation.errors
