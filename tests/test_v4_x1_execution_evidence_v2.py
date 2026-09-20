from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from idx_trade import forward_dividend_execution_v1_1 as dividend_execution
from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_reconciliation_result_v1 import (
    build_reconciliation_result_v1,
    verify_reconciliation_result_payload,
)
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
from idx_trade.v4_x1_quantity_obligation_v1 import apply_fill, plan_obligation
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
    obligation = plan_obligation(
        obligation_id="2026-09-02:BUY:BBCA:test",
        ticker="BBCA",
        side="BUY",
        planned_shares=100,
        session_date="2026-09-01",
        parent_state_sha256=paper_state_hash(before),
    )
    obligation = apply_fill(
        obligation,
        event_id="2026-09-02:BUY:BBCA:test:FILL",
        session_date="2026-09-02",
        filled_shares=100,
        reason="SIMULATED_FILLED",
        parent_state_sha256=paper_state_hash(before),
    )
    after = PaperPortfolioState(
        "2026-09-02",
        998_998.5,
        (PaperPosition("BBCA", 100),),
        obligations=(obligation,),
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

    evidence = build_execution_evidence_v2(plan, result, state_before=before)
    evaluation = evaluate_execution_evidence_v2(
        evidence,
        expected_order_plan=plan,
        expected_state_before=before,
    )

    assert evaluation.status == "PASS"
    assert "state_before_parent" in evaluation.checks
    assert evidence.payload()["schema_version"] == EXECUTION_EVIDENCE_SCHEMA
    assert evidence.payload()["fills"][0]["filled_shares"] == 100
    assert evidence.payload()["causes"][0]["cause_code"] == "FILLED"
    assert evidence.payload()["causes"][0]["next_action"] == "NONE"


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


def test_reconciliation_result_v1_records_internal_detector_provenance() -> None:
    before = PaperPortfolioState("2026-09-01", 1_000_000.0, ())
    after = PaperPortfolioState("2026-09-02", 1_000_000.0, ())
    plan = _plan(before)
    execution = ExecutionResult(
        execution_session_date="2026-09-02",
        state_before_hash=paper_state_hash(before),
        state_after=after,
        fills=(),
        stamp_duty_idr=0.0,
        gross_turnover_idr=0.0,
        pending_transition_count=0,
        reconciliation_required=False,
    )
    evidence = build_execution_evidence_v2(plan, execution)
    evaluation = evaluate_execution_evidence_v2(
        evidence,
        expected_order_plan=plan,
        expected_state_before=before,
    )
    reconciliation = dividend_execution.VerifiedDividendCAReconciliation(
        from_session_date="2026-09-01",
        through_session_date="2026-09-02",
        covered_tickers=frozenset({"BBCA"}),
        original_status="NO_RELEVANT_EVENTS",
        relevant_tickers=frozenset(),
        certified_events=(),
        legacy_attestation=object(),
        attestation_path=Path("attestation.json"),
        attestation_sha256="a" * 64,
        source_path=Path("source.json"),
        source_sha256="b" * 64,
        _verification_token=dividend_execution._DIVIDEND_RECONCILIATION_TOKEN,
    )

    result = build_reconciliation_result_v1(
        plan,
        evidence,
        evaluation,
        reconciliation,
        required_tickers=("BBCA",),
    )

    assert result.status == "PASS_INTERNAL_PAPER"
    assert result.external_reconciliation == "NOT_PERFORMED"
    verified = verify_reconciliation_result_payload(result.payload())
    assert verified["detector_id"] == "IDX_TRADE_INTERNAL_PAPER_RECONCILIATION_V1"


def test_reconciliation_result_v1_fails_closed_on_ca_coverage_gap() -> None:
    before = PaperPortfolioState("2026-09-01", 1_000_000.0, ())
    after = PaperPortfolioState("2026-09-02", 1_000_000.0, ())
    plan = _plan(before)
    execution = ExecutionResult(
        execution_session_date="2026-09-02",
        state_before_hash=paper_state_hash(before),
        state_after=after,
        fills=(),
        stamp_duty_idr=0.0,
        gross_turnover_idr=0.0,
        pending_transition_count=0,
        reconciliation_required=False,
    )
    evidence = build_execution_evidence_v2(plan, execution)
    evaluation = evaluate_execution_evidence_v2(evidence, expected_order_plan=plan)
    reconciliation = dividend_execution.VerifiedDividendCAReconciliation(
        from_session_date="2026-09-01",
        through_session_date="2026-09-02",
        covered_tickers=frozenset(),
        original_status="NO_RELEVANT_EVENTS",
        relevant_tickers=frozenset(),
        certified_events=(),
        legacy_attestation=object(),
        attestation_path=Path("attestation.json"),
        attestation_sha256="a" * 64,
        source_path=Path("source.json"),
        source_sha256="b" * 64,
        _verification_token=dividend_execution._DIVIDEND_RECONCILIATION_TOKEN,
    )

    result = build_reconciliation_result_v1(
        plan,
        evidence,
        evaluation,
        reconciliation,
        required_tickers=("BBCA",),
    )

    assert result.status == "FAIL"
    assert result.mismatches[0].code == "RECONCILIATION_RESULT_V1_CA_COVERAGE_INCOMPLETE"


def test_reconciliation_result_v1_rejects_hash_valid_incomplete_provenance() -> None:
    before = PaperPortfolioState("2026-09-01", 1_000_000.0, ())
    after = PaperPortfolioState("2026-09-02", 1_000_000.0, ())
    plan = _plan(before)
    execution = ExecutionResult(
        execution_session_date="2026-09-02",
        state_before_hash=paper_state_hash(before),
        state_after=after,
        fills=(),
        stamp_duty_idr=0.0,
        gross_turnover_idr=0.0,
        pending_transition_count=0,
        reconciliation_required=False,
    )
    evidence = build_execution_evidence_v2(plan, execution)
    evaluation = evaluate_execution_evidence_v2(evidence, expected_order_plan=plan)
    reconciliation = dividend_execution.VerifiedDividendCAReconciliation(
        from_session_date="2026-09-01",
        through_session_date="2026-09-02",
        covered_tickers=frozenset({"BBCA"}),
        original_status="NO_RELEVANT_EVENTS",
        relevant_tickers=frozenset(),
        certified_events=(),
        legacy_attestation=object(),
        attestation_path=Path("attestation.json"),
        attestation_sha256="a" * 64,
        source_path=Path("source.json"),
        source_sha256="b" * 64,
        _verification_token=dividend_execution._DIVIDEND_RECONCILIATION_TOKEN,
    )
    payload = build_reconciliation_result_v1(
        plan,
        evidence,
        evaluation,
        reconciliation,
        required_tickers=("BBCA",),
    ).payload()
    payload["execution_evidence_sha256"] = "not-a-sha"
    body = dict(payload)
    body.pop("payload_sha256")
    payload["payload_sha256"] = hashlib.sha256(
        (
            json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode()
    ).hexdigest()

    with pytest.raises(
        DecisionV1Error,
        match="FIELD_INVALID:execution_evidence_sha256",
    ):
        verify_reconciliation_result_payload(payload)
