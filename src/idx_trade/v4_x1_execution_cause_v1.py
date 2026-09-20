"""Structured exposure/cash cause records for paper execution transitions."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Any

from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_execution_v1_contract import (
    ExecutionResult,
    FillRecord,
    PaperPortfolioState,
    normalize_state,
)
from .v4_x1_quantity_obligation_v1 import canonical_security_identity


EXECUTION_CAUSE_SCHEMA = "idx_trade_execution_cause_v1"


@dataclass(frozen=True)
class ExecutionCauseV1:
    cause_id: str
    schema_version: str
    side: str
    ticker: str
    cause_code: str
    planned_shares: int
    filled_shares: int
    remaining_shares: int
    position_before_shares: int | None
    position_after_shares: int | None
    exposure_delta_shares: int | None
    cash_before_idr: float | None
    cash_after_idr: float
    next_action: str
    fill_status: str

    def payload(self) -> dict[str, Any]:
        return asdict(self)


def _cause_code(fill: FillRecord) -> str:
    status = fill.status.upper()
    if "MARKET_ENTRY_UNAVAILABLE" in status:
        return "MARKET_ENTRY_UNAVAILABLE"
    if "MARKET_EXIT_UNAVAILABLE" in status:
        return "MARKET_EXIT_UNAVAILABLE"
    if "BLOCKED_BY_UNRESOLVED_PAIRED_SELL" in status:
        return "PAIRED_SELL_UNRESOLVED"
    if "CASH" in status or "CASH_GAP" in status:
        return "CASH_CONSTRAINT"
    if "CAPACITY" in status or "REFERENCE_DAY" in status:
        return "REFERENCE_DAY_CAPACITY"
    if fill.filled_shares == 0:
        return "NO_FILL_REASON_RECORDED"
    if fill.filled_shares < fill.planned_shares:
        return "PARTIAL_FILL"
    return "FILLED"


def derive_execution_causes(
    result: ExecutionResult,
    *,
    state_before: PaperPortfolioState | None = None,
) -> tuple[ExecutionCauseV1, ...]:
    if not isinstance(result, ExecutionResult):
        raise DecisionV1Error("EXECUTION_CAUSE_V1_EXECUTION_RESULT_REQUIRED")
    before_positions: dict[str, int] = {}
    before_cash: float | None = None
    if state_before is not None:
        before_cash, before_positions, _, _ = normalize_state(state_before)
    _, after_positions, _, _ = normalize_state(result.state_after)
    causes: list[ExecutionCauseV1] = []
    for index, fill in enumerate(result.fills):
        ticker = canonical_security_identity(fill.ticker)
        before_shares = before_positions.get(ticker) if state_before is not None else None
        after_shares = after_positions.get(ticker)
        delta = (
            None
            if before_shares is None
            else (after_shares or 0) - before_shares
        )
        remaining = max(0, int(fill.planned_shares) - int(fill.filled_shares))
        next_action = "RETRY" if remaining > 0 else "NONE"
        identity = {
            "schema_version": EXECUTION_CAUSE_SCHEMA,
            "execution_session_date": result.execution_session_date,
            "fill_index": index,
            "side": fill.side,
            "ticker": ticker,
            "planned_shares": fill.planned_shares,
            "filled_shares": fill.filled_shares,
            "cause_code": _cause_code(fill),
        }
        cause_id = hashlib.sha256(
            (json.dumps(identity, sort_keys=True, separators=(",", ":")) + "\n").encode()
        ).hexdigest()
        causes.append(
            ExecutionCauseV1(
                cause_id=cause_id,
                schema_version=EXECUTION_CAUSE_SCHEMA,
                side=fill.side,
                ticker=ticker,
                cause_code=identity["cause_code"],
                planned_shares=fill.planned_shares,
                filled_shares=fill.filled_shares,
                remaining_shares=remaining,
                position_before_shares=before_shares,
                position_after_shares=after_shares,
                exposure_delta_shares=delta,
                cash_before_idr=before_cash,
                cash_after_idr=float(result.state_after.cash_idr),
                next_action=next_action,
                fill_status=fill.status,
            )
        )
    return tuple(causes)


__all__ = [
    "EXECUTION_CAUSE_SCHEMA",
    "ExecutionCauseV1",
    "derive_execution_causes",
]
