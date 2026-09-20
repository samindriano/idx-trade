"""Internal paper reconciliation result with explicit detector provenance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from .forward_dividend_execution_v1_1 import (
    VerifiedDividendCAReconciliation,
    _DIVIDEND_RECONCILIATION_TOKEN,
)
from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_execution_evidence_v2 import (
    ExecutionEvidenceEvaluation,
    ExecutionEvidenceV2,
)
from .v4_x1_execution_v1_contract import ExecutionOrderPlan


RECONCILIATION_RESULT_SCHEMA = "idx_trade_reconciliation_result_v1"
DETECTOR_ID = "IDX_TRADE_INTERNAL_PAPER_RECONCILIATION_V1"
EXTERNAL_RECONCILIATION_NOT_PERFORMED = "NOT_PERFORMED"


def _canonical_hash(value: object) -> str:
    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ReconciliationMismatchV1:
    code: str
    expected: str
    observed: str


@dataclass(frozen=True)
class ReconciliationResultV1:
    schema_version: str
    detector_id: str
    status: str
    external_reconciliation: str
    decision_session_date: str
    execution_session_date: str
    required_tickers: tuple[str, ...]
    covered_tickers: tuple[str, ...]
    relevant_tickers: tuple[str, ...]
    order_plan_state_hash: str
    evidence_state_before_hash: str
    evidence_state_after_hash: str
    execution_evidence_sha256: str
    ca_attestation_sha256: str
    ca_source_sha256: str
    ca_journal_sha256: str | None
    mismatches: tuple[ReconciliationMismatchV1, ...]

    def payload(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": self.schema_version,
            "detector_id": self.detector_id,
            "status": self.status,
            "external_reconciliation": self.external_reconciliation,
            "decision_session_date": self.decision_session_date,
            "execution_session_date": self.execution_session_date,
            "required_tickers": list(self.required_tickers),
            "covered_tickers": list(self.covered_tickers),
            "relevant_tickers": list(self.relevant_tickers),
            "order_plan_state_hash": self.order_plan_state_hash,
            "evidence_state_before_hash": self.evidence_state_before_hash,
            "evidence_state_after_hash": self.evidence_state_after_hash,
            "execution_evidence_sha256": self.execution_evidence_sha256,
            "ca_attestation_sha256": self.ca_attestation_sha256,
            "ca_source_sha256": self.ca_source_sha256,
            "ca_journal_sha256": self.ca_journal_sha256,
            "mismatches": [asdict(row) for row in self.mismatches],
        }
        body["payload_sha256"] = _canonical_hash(body)
        return body


def build_reconciliation_result_v1(
    order_plan: ExecutionOrderPlan,
    evidence: ExecutionEvidenceV2,
    evidence_evaluation: ExecutionEvidenceEvaluation,
    reconciliation: VerifiedDividendCAReconciliation,
    *,
    required_tickers: Sequence[str],
) -> ReconciliationResultV1:
    if not isinstance(order_plan, ExecutionOrderPlan):
        raise DecisionV1Error("RECONCILIATION_RESULT_V1_ORDER_PLAN_REQUIRED")
    if not isinstance(evidence, ExecutionEvidenceV2):
        raise DecisionV1Error("RECONCILIATION_RESULT_V1_EVIDENCE_REQUIRED")
    if not isinstance(evidence_evaluation, ExecutionEvidenceEvaluation):
        raise DecisionV1Error("RECONCILIATION_RESULT_V1_EVALUATION_REQUIRED")
    if (
        not isinstance(reconciliation, VerifiedDividendCAReconciliation)
        or reconciliation._verification_token is not _DIVIDEND_RECONCILIATION_TOKEN
    ):
        raise DecisionV1Error("RECONCILIATION_RESULT_V1_CA_RECONCILIATION_REQUIRED")

    required = tuple(sorted({str(value).strip().upper() for value in required_tickers}))
    covered = tuple(sorted(reconciliation.covered_tickers))
    relevant = tuple(sorted(reconciliation.relevant_tickers))
    mismatches: list[ReconciliationMismatchV1] = []

    if evidence_evaluation.status != "PASS":
        for error in evidence_evaluation.errors:
            mismatches.append(ReconciliationMismatchV1(error, "PASS", "FAIL"))
    if evidence.order_plan_state_hash != order_plan.state_hash:
        mismatches.append(
            ReconciliationMismatchV1(
                "RECONCILIATION_RESULT_V1_ORDER_PLAN_PARENT_MISMATCH",
                order_plan.state_hash,
                evidence.order_plan_state_hash,
            )
        )
    if evidence.decision_session_date != order_plan.decision_session_date:
        mismatches.append(
            ReconciliationMismatchV1(
                "RECONCILIATION_RESULT_V1_DECISION_SESSION_MISMATCH",
                order_plan.decision_session_date,
                evidence.decision_session_date,
            )
        )
    if evidence.execution_session_date != order_plan.execution_session_date:
        mismatches.append(
            ReconciliationMismatchV1(
                "RECONCILIATION_RESULT_V1_EXECUTION_SESSION_MISMATCH",
                order_plan.execution_session_date,
                evidence.execution_session_date,
            )
        )
    if reconciliation.from_session_date != order_plan.decision_session_date:
        mismatches.append(
            ReconciliationMismatchV1(
                "RECONCILIATION_RESULT_V1_CA_FROM_DATE_MISMATCH",
                order_plan.decision_session_date,
                reconciliation.from_session_date,
            )
        )
    if reconciliation.through_session_date != order_plan.execution_session_date:
        mismatches.append(
            ReconciliationMismatchV1(
                "RECONCILIATION_RESULT_V1_CA_THROUGH_DATE_MISMATCH",
                order_plan.execution_session_date,
                reconciliation.through_session_date,
            )
        )
    missing = sorted(set(required) - set(reconciliation.covered_tickers))
    if missing:
        mismatches.append(
            ReconciliationMismatchV1(
                "RECONCILIATION_RESULT_V1_CA_COVERAGE_INCOMPLETE",
                "covered",
                ",".join(missing),
            )
        )

    return ReconciliationResultV1(
        schema_version=RECONCILIATION_RESULT_SCHEMA,
        detector_id=DETECTOR_ID,
        status="PASS_INTERNAL_PAPER" if not mismatches else "FAIL",
        external_reconciliation=EXTERNAL_RECONCILIATION_NOT_PERFORMED,
        decision_session_date=order_plan.decision_session_date,
        execution_session_date=order_plan.execution_session_date,
        required_tickers=required,
        covered_tickers=covered,
        relevant_tickers=relevant,
        order_plan_state_hash=order_plan.state_hash,
        evidence_state_before_hash=evidence.state_before_hash,
        evidence_state_after_hash=evidence.state_after_hash,
        execution_evidence_sha256=_canonical_hash(evidence.payload()),
        ca_attestation_sha256=reconciliation.attestation_sha256,
        ca_source_sha256=reconciliation.source_sha256,
        ca_journal_sha256=reconciliation.v12_journal_sha256,
        mismatches=tuple(mismatches),
    )


def verify_reconciliation_result_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    if payload.get("schema_version") != RECONCILIATION_RESULT_SCHEMA:
        raise DecisionV1Error("RECONCILIATION_RESULT_V1_SCHEMA_MISMATCH")
    if payload.get("detector_id") != DETECTOR_ID:
        raise DecisionV1Error("RECONCILIATION_RESULT_V1_DETECTOR_MISMATCH")
    if payload.get("external_reconciliation") != EXTERNAL_RECONCILIATION_NOT_PERFORMED:
        raise DecisionV1Error("RECONCILIATION_RESULT_V1_EXTERNAL_SCOPE_CHANGED")
    declared = str(payload.pop("payload_sha256") or "")
    if not declared or _canonical_hash(payload) != declared:
        raise DecisionV1Error("RECONCILIATION_RESULT_V1_PAYLOAD_HASH_MISMATCH")
    if payload.get("status") != "PASS_INTERNAL_PAPER":
        raise DecisionV1Error("RECONCILIATION_RESULT_V1_NOT_PASS")
    if payload.get("mismatches"):
        raise DecisionV1Error("RECONCILIATION_RESULT_V1_PASS_WITH_MISMATCHES")
    payload["payload_sha256"] = declared
    return payload


__all__ = [
    "RECONCILIATION_RESULT_SCHEMA",
    "DETECTOR_ID",
    "EXTERNAL_RECONCILIATION_NOT_PERFORMED",
    "ReconciliationMismatchV1",
    "ReconciliationResultV1",
    "build_reconciliation_result_v1",
    "verify_reconciliation_result_payload",
]
