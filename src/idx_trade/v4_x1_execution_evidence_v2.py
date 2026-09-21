"""Versioned, quantity-bearing execution evidence and structural replay."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date
import hashlib
import json
import math
from typing import Any

from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_execution_cause_v1 import (
    ExecutionCauseV1,
    derive_execution_causes,
)
from .v4_x1_transition_binding_v1 import (
    build_cause_obligation_binding_v1,
    verify_cause_obligation_binding_v1,
)
from .v4_x1_execution_v1_contract import (
    ExecutionOrderPlan,
    ExecutionResult,
    FillRecord,
    PAPER_STATE_SOURCE,
    LOT_SIZE_SHARES,
    PaperPortfolioState,
    PaperPosition,
    PendingPaperIntent,
    normalize_state,
    paper_state_hash,
)
from .v4_x1_quantity_obligation_v1 import (
    obligation_from_payload,
    obligations_payload,
)


EXECUTION_EVIDENCE_SCHEMA = "idx_trade_execution_evidence_v2"
_EVIDENCE_KEYS = frozenset(
    {
        "schema_version",
        "decision_session_date",
        "execution_session_date",
        "order_plan_state_hash",
        "state_before_hash",
        "state_after_hash",
        "state_after",
        "fills",
        "gross_turnover_idr",
        "stamp_duty_idr",
        "pending_transition_count",
        "reconciliation_required",
        "rule_id",
        "causes",
        "cause_obligation_binding",
    }
)
_STATE_KEYS = frozenset(
    {
        "as_of_session_date",
        "cash_idr",
        "positions",
        "pending_buys",
        "pending_sells",
        "reconciliation_required",
        "source",
        "obligations",
    }
)
_PENDING_KEYS = frozenset(
    {"side", "ticker", "rank_consensus", "reason", "replacement_peer"}
)
_POSITION_KEYS = frozenset({"ticker", "shares"})
_FILL_KEYS = frozenset(
    {
        "side",
        "ticker",
        "planned_shares",
        "filled_shares",
        "raw_open",
        "effective_price",
        "gross_notional",
        "fee_idr",
        "cash_effect_idr",
        "status",
        "replacement_peer",
    }
)


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
    causes: tuple[ExecutionCauseV1, ...] = ()
    cause_obligation_binding: dict[str, Any] | None = None

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
            "causes": [row.payload() for row in self.causes],
            "cause_obligation_binding": self.cause_obligation_binding,
        }
        body["payload_sha256"] = _canonical_hash(body)
        return body


@dataclass(frozen=True)
class ExecutionEvidenceEvaluation:
    schema_version: str
    status: str
    checks: tuple[str, ...]
    errors: tuple[str, ...]


def _state_from_payload(value: object) -> PaperPortfolioState:
    if not isinstance(value, dict) or set(value) != _STATE_KEYS:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_STATE_NOT_CANONICAL")
    session = value["as_of_session_date"]
    if not isinstance(session, str):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_STATE_DATE_INVALID")
    try:
        parsed_session = date.fromisoformat(session)
    except ValueError as exc:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_STATE_DATE_INVALID") from exc
    if parsed_session.isoformat() != session:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_STATE_DATE_INVALID")
    if value["source"] != PAPER_STATE_SOURCE:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_STATE_SOURCE_INVALID")
    if type(value["reconciliation_required"]) is not bool:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_STATE_FLAG_INVALID")
    positions_raw = value["positions"]
    pending_buys_raw = value["pending_buys"]
    pending_sells_raw = value["pending_sells"]
    obligations_raw = value["obligations"]
    if not all(
        isinstance(rows, list)
        for rows in (
            positions_raw,
            pending_buys_raw,
            pending_sells_raw,
            obligations_raw,
        )
    ):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_STATE_ROWS_INVALID")
    try:
        positions = tuple(
            PaperPosition(row["ticker"], row["shares"])
            for row in positions_raw
            if isinstance(row, dict) and set(row) == _POSITION_KEYS
        )
        pending_buys = tuple(
            PendingPaperIntent(**row)
            for row in pending_buys_raw
            if isinstance(row, dict) and set(row) == _PENDING_KEYS
        )
        pending_sells = tuple(
            PendingPaperIntent(**row)
            for row in pending_sells_raw
            if isinstance(row, dict) and set(row) == _PENDING_KEYS
        )
        obligations = tuple(
            obligation_from_payload(row) for row in obligations_raw
        )
    except (DecisionV1Error, KeyError, TypeError, ValueError) as exc:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_STATE_ROW_INVALID") from exc
    if (
        len(positions) != len(positions_raw)
        or len(pending_buys) != len(pending_buys_raw)
        or len(pending_sells) != len(pending_sells_raw)
    ):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_STATE_ROW_INVALID")
    state = PaperPortfolioState(
        as_of_session_date=session,
        cash_idr=value["cash_idr"],
        positions=positions,
        pending_buys=pending_buys,
        pending_sells=pending_sells,
        reconciliation_required=value["reconciliation_required"],
        source=PAPER_STATE_SOURCE,
        obligations=obligations,
    )
    normalize_state(state)
    if _state_payload(state) != value:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_STATE_NOT_CANONICAL")
    return state


def parse_execution_evidence_v2_payload(value: object) -> ExecutionEvidenceV2:
    """Parse and canonically validate persisted execution evidence."""

    if not isinstance(value, dict):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_PAYLOAD_REQUIRED")
    raw = dict(value)
    declared = raw.get("payload_sha256")
    if (
        not isinstance(declared, str)
        or declared != declared.lower()
        or len(declared) != 64
        or any(char not in "0123456789abcdef" for char in declared)
    ):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_PAYLOAD_HASH_MISMATCH")
    body = dict(raw)
    body.pop("payload_sha256")
    if _canonical_hash(body) != declared:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_PAYLOAD_HASH_MISMATCH")
    if set(body) != _EVIDENCE_KEYS:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_PAYLOAD_NOT_CANONICAL")
    if body["schema_version"] != EXECUTION_EVIDENCE_SCHEMA:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_SCHEMA_MISMATCH")
    for key in ("decision_session_date", "execution_session_date"):
        candidate = body[key]
        if not isinstance(candidate, str):
            raise DecisionV1Error("EXECUTION_EVIDENCE_V2_DATE_INVALID")
        try:
            parsed = date.fromisoformat(candidate)
        except ValueError as exc:
            raise DecisionV1Error("EXECUTION_EVIDENCE_V2_DATE_INVALID") from exc
        if parsed.isoformat() != candidate:
            raise DecisionV1Error("EXECUTION_EVIDENCE_V2_DATE_INVALID")
    for key in ("order_plan_state_hash", "state_before_hash", "state_after_hash"):
        candidate = body[key]
        if (
            not isinstance(candidate, str)
            or candidate != candidate.lower()
            or len(candidate) != 64
            or any(char not in "0123456789abcdef" for char in candidate)
        ):
            raise DecisionV1Error("EXECUTION_EVIDENCE_V2_HASH_INVALID")
    if body["rule_id"] != "V4_X1_EXECUTION_V1":
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_RULE_MISMATCH")
    if type(body["reconciliation_required"]) is not bool:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_FLAG_INVALID")
    if (
        isinstance(body["pending_transition_count"], bool)
        or not isinstance(body["pending_transition_count"], int)
        or body["pending_transition_count"] < 0
    ):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_PENDING_COUNT_INVALID")
    for key in ("gross_turnover_idr", "stamp_duty_idr"):
        candidate = body[key]
        if (
            isinstance(candidate, bool)
            or not isinstance(candidate, (int, float))
            or not math.isfinite(float(candidate))
            or float(candidate) < 0
        ):
            raise DecisionV1Error("EXECUTION_EVIDENCE_V2_AMOUNT_INVALID")
    state_after = _state_from_payload(body["state_after"])
    fills_raw = body["fills"]
    causes_raw = body["causes"]
    if not isinstance(fills_raw, list) or not isinstance(causes_raw, list):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_ROWS_INVALID")
    try:
        fills = tuple(FillRecord(**row) for row in fills_raw)
        causes = tuple(ExecutionCauseV1(**row) for row in causes_raw)
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_ROW_INVALID") from exc
    for row, raw_row in zip(fills, fills_raw):
        if not isinstance(raw_row, dict) or set(raw_row) != _FILL_KEYS:
            raise DecisionV1Error("EXECUTION_EVIDENCE_V2_FILL_NOT_CANONICAL")
        if (
            not isinstance(row.side, str)
            or not isinstance(row.ticker, str)
            or not row.ticker
            or not isinstance(row.status, str)
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in (row.planned_shares, row.filled_shares)
            )
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in (
                    row.gross_notional,
                    row.fee_idr,
                    row.cash_effect_idr,
                )
            )
            or (
                row.raw_open is not None
                and (
                    isinstance(row.raw_open, bool)
                    or not isinstance(row.raw_open, (int, float))
                    or not math.isfinite(float(row.raw_open))
                )
            )
            or (
                row.effective_price is not None
                and (
                    isinstance(row.effective_price, bool)
                    or not isinstance(row.effective_price, (int, float))
                    or not math.isfinite(float(row.effective_price))
                )
            )
            or asdict(row) != raw_row
        ):
            raise DecisionV1Error("EXECUTION_EVIDENCE_V2_FILL_NOT_CANONICAL")
    if any(asdict(row) != raw_row for row, raw_row in zip(causes, causes_raw)):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_CAUSE_NOT_CANONICAL")
    if len(fills) != len(fills_raw) or len(causes) != len(causes_raw):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_ROW_INVALID")
    binding = body["cause_obligation_binding"]
    if binding is not None and not isinstance(binding, dict):
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_BINDING_INVALID")
    try:
        evidence = ExecutionEvidenceV2(
            schema_version=body["schema_version"],
            decision_session_date=body["decision_session_date"],
            execution_session_date=body["execution_session_date"],
            order_plan_state_hash=body["order_plan_state_hash"],
            state_before_hash=body["state_before_hash"],
            state_after_hash=body["state_after_hash"],
            state_after=state_after,
            fills=fills,
            gross_turnover_idr=body["gross_turnover_idr"],
            stamp_duty_idr=body["stamp_duty_idr"],
            pending_transition_count=body["pending_transition_count"],
            reconciliation_required=body["reconciliation_required"],
            rule_id=body["rule_id"],
            causes=causes,
            cause_obligation_binding=binding,
        )
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_PAYLOAD_INVALID") from exc
    if evidence.payload() != raw:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_PAYLOAD_NOT_CANONICAL")
    # Cause rows and their binding are replayed by the orchestration layer
    # with the session/parent context.  Intrinsic evidence arithmetic is safe
    # to check here without preempting those more specific binding errors.
    try:
        evaluation = evaluate_execution_evidence_v2(
            replace(evidence, causes=(), cause_obligation_binding=None)
        )
    except (DecisionV1Error, TypeError, ValueError) as exc:
        raise DecisionV1Error("EXECUTION_EVIDENCE_V2_PAYLOAD_INVALID") from exc
    if evaluation.status != "PASS":
        raise DecisionV1Error(
            "EXECUTION_EVIDENCE_V2_INVALID:" + ",".join(evaluation.errors)
        )
    return evidence


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
    if evidence.cause_obligation_binding is None:
        if evidence.causes:
            errors.append("EXECUTION_EVIDENCE_V2_CAUSE_OBLIGATION_BINDING_MISSING")
    else:
        try:
            verify_cause_obligation_binding_v1(
                evidence.cause_obligation_binding,
                execution_session_date=evidence.execution_session_date,
                causes=evidence.causes,
                obligations=evidence.state_after.obligations,
            )
            checks.append("cause_obligation_binding")
        except DecisionV1Error as exc:
            errors.append(str(exc))

    return ExecutionEvidenceEvaluation(
        schema_version=EXECUTION_EVIDENCE_SCHEMA,
        status="PASS" if not errors else "FAIL",
        checks=tuple(checks),
        errors=tuple(errors),
    )


def build_execution_evidence_v2(
    order_plan: ExecutionOrderPlan,
    result: ExecutionResult,
    *,
    state_before: PaperPortfolioState | None = None,
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
        causes=derive_execution_causes(result, state_before=state_before),
    )
    evidence = replace(
        evidence,
        cause_obligation_binding=build_cause_obligation_binding_v1(
            result,
            evidence.causes,
        ),
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
    "parse_execution_evidence_v2_payload",
]
