"""Explicit payment-timing evidence for projected CA sizing boundaries."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import hashlib
import json
from typing import Any, Sequence

from . import forward_dividend_v1 as dividend
from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_execution_v1_contract import paper_state_hash


CA_TIMING_MATRIX_SCHEMA = "idx_trade_ca_timing_matrix_v1"
_MATRIX_KEYS = frozenset(
    {
        "schema_version",
        "decision_session_date",
        "execution_session_date",
        "raw_state_hash",
        "raw_base_state_hash",
        "sizing_state_hash",
        "sizing_base_state_hash",
        "rows",
        "restart_policy",
    }
)
_ROW_KEYS = frozenset(
    {
        "event_id",
        "ticker",
        "payment_date",
        "timing_class",
        "execution_boundary_action",
        "raw_settled",
        "sizing_settled",
    }
)


def _canonical_hash(value: object) -> str:
    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _day(value: object, code: str) -> date:
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(code) from exc
    return parsed


def _same_trade_state(
    raw: dividend.DividendAwarePaperState,
    projected: dividend.DividendAwarePaperState,
) -> bool:
    projected_base = replace(
        projected.base_state,
        cash_idr=raw.base_state.cash_idr,
    )
    return projected_base == raw.base_state


def _settled_ids(state: dividend.DividendAwarePaperState) -> set[str]:
    return {row.event_id for row in state.dividend_ledger.settlements}


def _verify_settlement_parent(
    event: dividend.CertifiedCashDividend,
    state: dividend.DividendAwarePaperState,
) -> None:
    for settlement in state.dividend_ledger.settlements:
        if settlement.event_id != event.event_id:
            continue
        if (
            settlement.ticker != event.ticker
            or settlement.payment_date != event.payment_date
            or settlement.source_evidence_sha256 != event.source_evidence_sha256
        ):
            raise DecisionV1Error("CA_TIMING_SETTLEMENT_PARENT_MISMATCH")


def _timing(payment: date, decision: date, execution: date) -> tuple[str, str]:
    if payment < decision:
        return "PAYMENT_BEFORE_DECISION", "ALREADY_SETTLED_IN_RAW_STATE"
    if payment == decision:
        return "PAYMENT_ON_DECISION", "SETTLED_IN_SIZING_PROJECTION"
    if payment == execution:
        return "PAYMENT_ON_EXECUTION", "SETTLE_AT_EXECUTION_BOUNDARY"
    return "PAYMENT_AFTER_EXECUTION", "WAIT_FOR_PAYMENT_DATE"


def build_ca_timing_matrix_v1(
    events: Sequence[dividend.CertifiedCashDividend],
    *,
    decision_session_date: str,
    execution_session_date: str,
    raw_state: dividend.DividendAwarePaperState,
    sizing_state: dividend.DividendAwarePaperState,
) -> dict[str, Any]:
    """Check all certified events against the raw/projected sizing boundary."""

    if not isinstance(raw_state, dividend.DividendAwarePaperState):
        raise DecisionV1Error("CA_TIMING_RAW_STATE_REQUIRED")
    if not isinstance(sizing_state, dividend.DividendAwarePaperState):
        raise DecisionV1Error("CA_TIMING_SIZING_STATE_REQUIRED")
    decision = _day(decision_session_date, "CA_TIMING_DECISION_DATE_INVALID")
    execution = _day(execution_session_date, "CA_TIMING_EXECUTION_DATE_INVALID")
    if execution <= decision:
        raise DecisionV1Error("CA_TIMING_EXECUTION_NOT_AFTER_DECISION")
    if raw_state.base_state.as_of_session_date != decision_session_date:
        raise DecisionV1Error("CA_TIMING_RAW_STATE_SESSION_MISMATCH")
    if sizing_state.base_state.as_of_session_date != decision_session_date:
        raise DecisionV1Error("CA_TIMING_SIZING_STATE_SESSION_MISMATCH")
    if not _same_trade_state(raw_state, sizing_state):
        raise DecisionV1Error("CA_TIMING_TRADE_STATE_CHANGED")

    raw_settled = _settled_ids(raw_state)
    sizing_settled = _settled_ids(sizing_state)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in sorted(events, key=lambda row: row.event_id):
        if not isinstance(event, dividend.CertifiedCashDividend):
            raise DecisionV1Error("CA_TIMING_EVENT_INVALID")
        if event.event_id in seen:
            raise DecisionV1Error("CA_TIMING_DUPLICATE_EVENT")
        seen.add(event.event_id)
        timing, action = _timing(
            _day(event.payment_date, "CA_TIMING_PAYMENT_DATE_INVALID"),
            decision,
            execution,
        )
        _verify_settlement_parent(event, raw_state)
        _verify_settlement_parent(event, sizing_state)
        is_raw_settled = event.event_id in raw_settled
        is_sizing_settled = event.event_id in sizing_settled
        if timing == "PAYMENT_BEFORE_DECISION" and not (
            is_raw_settled and is_sizing_settled
        ):
            raise DecisionV1Error("CA_TIMING_BEFORE_DECISION_NOT_SETTLED")
        if timing == "PAYMENT_ON_DECISION" and (
            is_raw_settled or not is_sizing_settled
        ):
            raise DecisionV1Error("CA_TIMING_ON_DECISION_PROJECTION_MISMATCH")
        if timing in {"PAYMENT_ON_EXECUTION", "PAYMENT_AFTER_EXECUTION"} and (
            is_raw_settled or is_sizing_settled
        ):
            raise DecisionV1Error("CA_TIMING_POST_DECISION_SETTLEMENT_TOO_EARLY")
        rows.append(
            {
                "event_id": event.event_id,
                "ticker": event.ticker,
                "payment_date": event.payment_date,
                "timing_class": timing,
                "execution_boundary_action": action,
                "raw_settled": is_raw_settled,
                "sizing_settled": is_sizing_settled,
            }
        )
    body: dict[str, Any] = {
        "schema_version": CA_TIMING_MATRIX_SCHEMA,
        "decision_session_date": decision_session_date,
        "execution_session_date": execution_session_date,
        "raw_state_hash": dividend.dividend_aware_state_hash(raw_state),
        "raw_base_state_hash": paper_state_hash(raw_state.base_state),
        "sizing_state_hash": dividend.dividend_aware_state_hash(sizing_state),
        "sizing_base_state_hash": paper_state_hash(sizing_state.base_state),
        "rows": rows,
        "restart_policy": "REPLAY_SAME_MATRIX_BYTES_OR_FAIL",
    }
    body["payload_sha256"] = _canonical_hash(body)
    return body


def verify_ca_timing_matrix_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionV1Error("CA_TIMING_MATRIX_PAYLOAD_REQUIRED")
    raw_declared = value.get("payload_sha256")
    if (
        not isinstance(raw_declared, str)
        or raw_declared != raw_declared.lower()
        or len(raw_declared) != 64
        or any(char not in "0123456789abcdef" for char in raw_declared)
    ):
        raise DecisionV1Error("CA_TIMING_MATRIX_PAYLOAD_HASH_MISMATCH")
    payload = dict(value)
    declared = payload.pop("payload_sha256")
    if _canonical_hash(payload) != declared:
        raise DecisionV1Error("CA_TIMING_MATRIX_PAYLOAD_HASH_MISMATCH")
    if set(payload) != _MATRIX_KEYS:
        raise DecisionV1Error("CA_TIMING_MATRIX_PAYLOAD_NOT_CANONICAL")
    if payload["schema_version"] != CA_TIMING_MATRIX_SCHEMA:
        raise DecisionV1Error("CA_TIMING_MATRIX_SCHEMA_MISMATCH")
    decision_text = payload["decision_session_date"]
    execution_text = payload["execution_session_date"]
    if not isinstance(decision_text, str) or not isinstance(execution_text, str):
        raise DecisionV1Error("CA_TIMING_MATRIX_DATE_INVALID")
    decision = _day(decision_text, "CA_TIMING_MATRIX_DATE_INVALID")
    execution = _day(execution_text, "CA_TIMING_MATRIX_DATE_INVALID")
    if decision.isoformat() != decision_text or execution.isoformat() != execution_text:
        raise DecisionV1Error("CA_TIMING_MATRIX_DATE_INVALID")
    if execution <= decision:
        raise DecisionV1Error("CA_TIMING_MATRIX_EXECUTION_NOT_AFTER_DECISION")
    for key in (
        "raw_state_hash",
        "raw_base_state_hash",
        "sizing_state_hash",
        "sizing_base_state_hash",
    ):
        candidate = payload[key]
        if (
            not isinstance(candidate, str)
            or candidate != candidate.lower()
            or len(candidate) != 64
            or any(char not in "0123456789abcdef" for char in candidate)
        ):
            raise DecisionV1Error("CA_TIMING_MATRIX_HASH_INVALID")
    if payload["restart_policy"] != "REPLAY_SAME_MATRIX_BYTES_OR_FAIL":
        raise DecisionV1Error("CA_TIMING_MATRIX_RESTART_POLICY_INVALID")
    rows = payload["rows"]
    if not isinstance(rows, list):
        raise DecisionV1Error("CA_TIMING_MATRIX_ROWS_INVALID")
    previous_event_id: str | None = None
    for row in rows:
        if not isinstance(row, dict) or set(row) != _ROW_KEYS:
            raise DecisionV1Error("CA_TIMING_MATRIX_ROW_NOT_CANONICAL")
        event_id = row["event_id"]
        ticker = row["ticker"]
        payment_text = row["payment_date"]
        if (
            not isinstance(event_id, str)
            or not event_id
            or (previous_event_id is not None and event_id <= previous_event_id)
            or not isinstance(ticker, str)
            or not ticker
            or not isinstance(payment_text, str)
        ):
            raise DecisionV1Error("CA_TIMING_MATRIX_ROW_NOT_CANONICAL")
        payment = _day(payment_text, "CA_TIMING_MATRIX_PAYMENT_DATE_INVALID")
        if payment.isoformat() != payment_text:
            raise DecisionV1Error("CA_TIMING_MATRIX_PAYMENT_DATE_INVALID")
        expected_timing, expected_action = _timing(payment, decision, execution)
        if (
            row["timing_class"] != expected_timing
            or row["execution_boundary_action"] != expected_action
            or type(row["raw_settled"]) is not bool
            or type(row["sizing_settled"]) is not bool
        ):
            raise DecisionV1Error("CA_TIMING_MATRIX_ROW_SEMANTICS_MISMATCH")
        previous_event_id = event_id
    payload["payload_sha256"] = declared
    return payload


def verify_ca_timing_matrix_extension(
    parent: object,
    current: object,
) -> dict[str, Any]:
    """Allow only an evidence-backed CA extension of a prepared matrix."""

    parent_payload = verify_ca_timing_matrix_payload(parent)
    current_payload = verify_ca_timing_matrix_payload(current)
    for key in (
        "decision_session_date",
        "execution_session_date",
        "raw_state_hash",
        "raw_base_state_hash",
    ):
        if parent_payload.get(key) != current_payload.get(key):
            raise DecisionV1Error("CA_TIMING_MATRIX_PARENT_CONTEXT_CHANGED")
    parent_rows = {
        str(row.get("event_id")): row
        for row in parent_payload["rows"]
        if isinstance(row, dict)
    }
    current_rows = {
        str(row.get("event_id")): row
        for row in current_payload["rows"]
        if isinstance(row, dict)
    }
    if set(parent_rows) - set(current_rows):
        raise DecisionV1Error("CA_TIMING_MATRIX_PARENT_EVENT_REMOVED")
    for event_id, row in parent_rows.items():
        if current_rows[event_id] != row:
            raise DecisionV1Error("CA_TIMING_MATRIX_PARENT_EVENT_CHANGED")
    return current_payload


__all__ = [
    "CA_TIMING_MATRIX_SCHEMA",
    "build_ca_timing_matrix_v1",
    "verify_ca_timing_matrix_extension",
    "verify_ca_timing_matrix_payload",
]
