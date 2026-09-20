"""Versioned, quantity-bearing execution evidence and structural replay."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any

from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_execution_v1_contract import (
    ExecutionOrderPlan,
    ExecutionResult,
    FillRecord,
    LOT_SIZE_SHARES,
    PaperPortfolioState,
    normalize_state,
    paper_state_hash,
)
from .v4_x1_quantity_obligation_v1 import obligations_payload


EXECUTION_EVIDENCE_SCHEMA = "idx_trade_execution_evidence_v2"


def _canonical_hash(value: object) -> str:
    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _state_payload(state: PaperPortfolioState) -> dict[str, Any]:
    cash, positions, pending_buys, pending_sells = normalize_state(state)

    def pending_payload(rows: dict[str, object]) -> list[dict[str, object]]:
        return [
            {
                "side": row.side,
                "ticker": row.ticker,
                "rank_consensus": row.rank_consensus,
                "reason": row.reason,
                "replacement_peer": row.replacement_peer,
            }
            for row in sorted(rows.values(), key=lambda item: item.ticker)
        ]

    return {
        "as_of_session_date": state.as_of_session_date,
        "cash_idr": round(cash, 6),
        "positions": [
            {"ticker": ticker, "shares": shares}
            for ticker, shares in sorted(positions.items())
        ],
        "pending_buys": pending_payload(pending_buys),
        "pending_sells": pending_payload(pending_sells),
        "reconciliation_required": bool(state.reconciliation_required),
        "source": state.source,
        "obligations": obligations_payload(state.obligations),
    }


@dataclass(frozen=True)
class ExecutionEvidenceV2:
    schema_version: str
    decision_session_date: str
    execution_session_date: str
    order_plan_state_hash: str
    state_before_hash: str
    state_after_hash: str
    state_after: PaperPortfolioState
    fills: tuple[FillRecord, ...]
    gross_turnover_idr: float
    stamp_duty_idr: float
    pending_transition_count: int
    reconciliation_required: bool
    rule_id: str

    def payload(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": self.schema_version,
            "decision_session_date": self.decision_session_date,
            "execution_session_date": self.execution_session_date,
            "order_plan_state_hash": self.order_plan_state_hash,
            "state_before_hash": self.state_before_hash,
            "state_after_hash": self.state_after_hash,
            "state_after": _state_payload(self.state_after),
            "fills": [asdict(row) for row in self.fills],
            "gross_turnover_idr": self.gross_turnover_idr,
            "stamp_duty_idr": self.stamp_duty_idr,
            "pending_transition_count": self.pending_transition_count,
            "reconciliation_required": self.reconciliation_required,
            "rule_id": self.rule_id,
        }
        body["payload_sha256"] = _canonical_hash(body)
        return body


@dataclass(frozen=True)
class ExecutionEvidenceEvaluation:
    schema_version: str
    status: str
    checks: tuple[str, ...]
    errors: tuple[str, ...]


def evaluate_execution_evidence_v2(
    evidence: ExecutionEvidenceV2,
    *,
    expected_order_plan: ExecutionOrderPlan | None = None,
    expected_state_before: PaperPortfolioState | None = None,
) -> ExecutionEvidenceEvaluation:
    checks: list[str] = []
    errors: list[str] = []

    if not isinstance(evidence, ExecutionEvidenceV2):
        return ExecutionEvidenceEvaluation(
            schema_version=EXECUTION_EVIDENCE_SCHEMA,
            status="FAIL",
            checks=(),
            errors=("EXECUTION_EVIDENCE_V2_REQUIRED",),
        )
    if evidence.schema_version != EXECUTION_EVIDENCE_SCHEMA:
        errors.append("EXECUTION_EVIDENCE_V2_SCHEMA_MISMATCH")
    else:
        checks.append("schema")
    if evidence.rule_id != "V4_X1_EXECUTION_V1":
        errors.append("EXECUTION_EVIDENCE_V2_RULE_MISMATCH")

    try:
        normalize_state(evidence.state_after)
    except DecisionV1Error as exc:
        errors.append(str(exc))
    else:
        checks.append("state_after_normalizes")
        if paper_state_hash(evidence.state_after) != evidence.state_after_hash:
            errors.append("EXECUTION_EVIDENCE_V2_STATE_AFTER_HASH_MISMATCH")
        else:
            checks.append("state_after_hash")

    if evidence.state_before_hash != evidence.order_plan_state_hash:
        errors.append("EXECUTION_EVIDENCE_V2_PARENT_HASH_MISMATCH")
    else:
        checks.append("state_before_parent")
    if expected_order_plan is not None:
        if evidence.order_plan_state_hash != expected_order_plan.state_hash:
            errors.append("EXECUTION_EVIDENCE_V2_ORDER_PLAN_HASH_MISMATCH")
        if evidence.decision_session_date != expected_order_plan.decision_session_date:
            errors.append("EXECUTION_EVIDENCE_V2_DECISION_SESSION_MISMATCH")
        if evidence.execution_session_date != expected_order_plan.execution_session_date:
            errors.append("EXECUTION_EVIDENCE_V2_EXECUTION_SESSION_MISMATCH")
        if evidence.order_plan_state_hash == expected_order_plan.state_hash:
            checks.append("order_plan_parent")
    if expected_state_before is not None:
        if paper_state_hash(expected_state_before) != evidence.state_before_hash:
            errors.append("EXECUTION_EVIDENCE_V2_STATE_BEFORE_HASH_MISMATCH")
        else:
            checks.append("state_before_hash")

    gross_turnover = 0.0
    expected_cash_after = None
    expected_positions_after: dict[str, int] | None = None
    if expected_state_before is not None:
        before_cash, before_positions, _, _ = normalize_state(expected_state_before)
        expected_cash_after = before_cash - evidence.stamp_duty_idr
        expected_positions_after = dict(before_positions)
        for fill in evidence.fills:
            if fill.side == "BUY":
                next_shares = (
                    expected_positions_after.get(fill.ticker, 0)
                    + fill.filled_shares
                )
                if next_shares:
                    expected_positions_after[fill.ticker] = next_shares
            elif fill.side == "SELL":
                remaining = expected_positions_after.get(fill.ticker, 0) - fill.filled_shares
                if remaining < 0:
                    errors.append("EXECUTION_EVIDENCE_V2_SELL_EXCEEDS_POSITION")
                elif remaining == 0:
                    expected_positions_after.pop(fill.ticker, None)
                else:
                    expected_positions_after[fill.ticker] = remaining
            expected_cash_after += fill.cash_effect_idr

    for index, fill in enumerate(evidence.fills):
        prefix = f"EXECUTION_EVIDENCE_V2_FILL_{index}"
        if fill.side not in {"BUY", "SELL"}:
            errors.append(f"{prefix}_SIDE_INVALID")
        if fill.planned_shares < 0 or fill.filled_shares < 0:
            errors.append(f"{prefix}_NEGATIVE_QUANTITY")
        if fill.planned_shares % LOT_SIZE_SHARES or fill.filled_shares % LOT_SIZE_SHARES:
            errors.append(f"{prefix}_NOT_WHOLE_LOT")
        if fill.filled_shares > fill.planned_shares:
            errors.append(f"{prefix}_FILL_EXCEEDS_PLAN")
        if not math.isfinite(fill.gross_notional) or fill.gross_notional < 0:
            errors.append(f"{prefix}_GROSS_INVALID")
        if not math.isfinite(fill.fee_idr) or fill.fee_idr < 0:
            errors.append(f"{prefix}_FEE_INVALID")
        if not math.isfinite(fill.cash_effect_idr):
            errors.append(f"{prefix}_CASH_EFFECT_INVALID")
        if fill.filled_shares == 0 and any(
            value != 0.0
            for value in (fill.gross_notional, fill.fee_idr, fill.cash_effect_idr)
        ):
            errors.append(f"{prefix}_ZERO_FILL_HAS_CASH_EFFECT")
        gross_turnover += fill.gross_notional
    if expected_cash_after is not None:
        if math.isclose(
            expected_cash_after,
            evidence.state_after.cash_idr,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            checks.append("cash_transition")
        else:
            errors.append("EXECUTION_EVIDENCE_V2_CASH_TRANSITION_MISMATCH")
        _, actual_positions_after, _, _ = normalize_state(evidence.state_after)
        if actual_positions_after == expected_positions_after:
            checks.append("position_transition")
        else:
            errors.append("EXECUTION_EVIDENCE_V2_POSITION_TRANSITION_MISMATCH")
    if math.isclose(
        gross_turnover,
        evidence.gross_turnover_idr,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        checks.append("gross_turnover_sum")
    else:
        errors.append("EXECUTION_EVIDENCE_V2_GROSS_TURNOVER_MISMATCH")

    if evidence.pending_transition_count == (
        len(evidence.state_after.pending_buys)
        + len(evidence.state_after.pending_sells)
    ):
        checks.append("pending_transition_count")
    else:
        errors.append("EXECUTION_EVIDENCE_V2_PENDING_COUNT_MISMATCH")
    if evidence.reconciliation_required == evidence.state_after.reconciliation_required:
        checks.append("reconciliation_flag")
    else:
        errors.append("EXECUTION_EVIDENCE_V2_RECONCILIATION_FLAG_MISMATCH")

    return ExecutionEvidenceEvaluation(
        schema_version=EXECUTION_EVIDENCE_SCHEMA,
        status="PASS" if not errors else "FAIL",
        checks=tuple(checks),
        errors=tuple(errors),
    )


def build_execution_evidence_v2(
    order_plan: ExecutionOrderPlan,
    result: ExecutionResult,
) -> ExecutionEvidenceV2:
    if not isinstance(order_plan, ExecutionOrderPlan):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_ORDER_PLAN_REQUIRED")
    if not isinstance(result, ExecutionResult):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_EXECUTION_RESULT_REQUIRED")
    evidence = ExecutionEvidenceV2(
        schema_version=EXECUTION_EVIDENCE_SCHEMA,
        decision_session_date=order_plan.decision_session_date,
        execution_session_date=result.execution_session_date,
        order_plan_state_hash=order_plan.state_hash,
        state_before_hash=result.state_before_hash,
        state_after_hash=paper_state_hash(result.state_after),
        state_after=result.state_after,
        fills=result.fills,
        gross_turnover_idr=float(result.gross_turnover_idr),
        stamp_duty_idr=float(result.stamp_duty_idr),
        pending_transition_count=int(result.pending_transition_count),
        reconciliation_required=bool(result.reconciliation_required),
        rule_id=result.rule_id,
    )
    evaluation = evaluate_execution_evidence_v2(
        evidence,
        expected_order_plan=order_plan,
    )
    if evaluation.status != "PASS":
        raise DecisionV1Error(
            "EXECUTION_EVIDENCE_V2_INVALID:" + ",".join(evaluation.errors)
        )
    return evidence


__all__ = [
    "EXECUTION_EVIDENCE_SCHEMA",
    "ExecutionEvidenceV2",
    "ExecutionEvidenceEvaluation",
    "build_execution_evidence_v2",
    "evaluate_execution_evidence_v2",
]
