"""Outcome-blind audit harness for migrating legacy execution artifacts.

This module is deliberately not imported by the production runtime.  It uses
synthetic payloads shaped like the current transaction/snapshot artifacts and
answers one narrow question: which quantity obligations are recoverable from
retained evidence, and which must remain unknown?

The harness never fabricates a remainder from a snapshot position alone.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Mapping


CLASS_COMPLETE = "COMPLETE_HISTORICAL_FILL"
CLASS_RECOVERABLE_PARTIAL = "RECOVERABLE_PARTIAL_WITH_FILL_VECTOR"
CLASS_EXPLICIT_PENDING = "EXPLICIT_ZERO_LOT_PENDING"
CLASS_ORPHANED_PARTIAL = "UNKNOWN_ORPHANED_PARTIAL"
CLASS_RECONCILIATION = "REQUIRES_RECONCILIATION"
CLASS_NO_QUANTITY = "UNKNOWN_NO_QUANTITY_AUTHORITY"


class ArtifactMigrationAuditError(ValueError):
    """Raised when the retained artifact shape cannot be audited safely."""


@dataclass(frozen=True)
class MigrationRecord:
    obligation_id: str
    artifact_session_date: str
    ticker: str
    side: str
    planned_shares: int | None
    filled_shares: int | None
    remaining_shares: int | None
    observed_position_shares: int | None
    classification: str
    evidence: tuple[str, ...]

    def as_payload(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence"] = list(self.evidence)
        return value


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ArtifactMigrationAuditError(f"{label}_NOT_OBJECT")
    return value


def _rows(value: object, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise ArtifactMigrationAuditError(f"{label}_NOT_LIST")
    result: list[Mapping[str, Any]] = []
    for index, row in enumerate(value):
        result.append(_mapping(row, f"{label}_{index}"))
    return result


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise ArtifactMigrationAuditError(f"{label}_NOT_INTEGER")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float) and value.is_integer():
        parsed = int(value)
    else:
        raise ArtifactMigrationAuditError(f"{label}_NOT_INTEGER")
    if parsed < 0:
        raise ArtifactMigrationAuditError(f"{label}_NEGATIVE")
    return parsed


def _artifact_parts(
    payload: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any], str]:
    """Read the current transaction shape without importing runtime code."""
    execution = payload.get("execution_body")
    if execution is None and "fills" in payload:
        execution = payload
    execution_body = _mapping(execution, "EXECUTION_BODY") if execution is not None else {}

    snapshot = payload.get("snapshot_payload")
    if snapshot is None and "state" in payload:
        snapshot = payload
    snapshot_payload = _mapping(snapshot, "SNAPSHOT_PAYLOAD") if snapshot is not None else {}

    session = (
        execution_body.get("execution_session_date")
        or payload.get("execution_session_date")
        or snapshot_payload.get("session_date")
        or "UNKNOWN_SESSION"
    )
    return execution_body, snapshot_payload, str(session)


def _snapshot_observations(
    snapshot_payload: Mapping[str, Any],
) -> tuple[dict[str, int], set[tuple[str, str]]]:
    if not snapshot_payload:
        return {}, set()
    state = _mapping(snapshot_payload.get("state", snapshot_payload), "SNAPSHOT_STATE")
    base = _mapping(state.get("base_paper_state", state), "BASE_PAPER_STATE")
    positions = _rows(base.get("positions", []), "POSITIONS")
    pending_buys = _rows(base.get("pending_buys", []), "PENDING_BUYS")
    pending_sells = _rows(base.get("pending_sells", []), "PENDING_SELLS")

    position_map: dict[str, int] = {}
    for row in positions:
        ticker = str(row.get("ticker", ""))
        if not ticker:
            raise ArtifactMigrationAuditError("POSITION_TICKER_MISSING")
        position_map[ticker] = _nonnegative_int(row.get("shares"), "POSITION_SHARES")

    pending: set[tuple[str, str]] = set()
    for side, rows in (("BUY", pending_buys), ("SELL", pending_sells)):
        for row in rows:
            ticker = str(row.get("ticker", ""))
            if not ticker:
                raise ArtifactMigrationAuditError("PENDING_TICKER_MISSING")
            pending.add((side, ticker))
    return position_map, pending


def _record(
    *, session: str, index: int, ticker: str, side: str,
    planned: int | None, filled: int | None, remaining: int | None,
    observed_position: int | None, classification: str,
    evidence: tuple[str, ...],
) -> MigrationRecord:
    identity_ticker = ticker or "UNKNOWN_TICKER"
    identity_side = side or "UNKNOWN_SIDE"
    obligation_id = f"LEGACY_EXECUTION::{session}::{identity_ticker}::{identity_side}::{index}"
    return MigrationRecord(
        obligation_id=obligation_id,
        artifact_session_date=session,
        ticker=identity_ticker,
        side=identity_side,
        planned_shares=planned,
        filled_shares=filled,
        remaining_shares=remaining,
        observed_position_shares=observed_position,
        classification=classification,
        evidence=evidence,
    )


def audit_legacy_artifact(payload: Mapping[str, Any]) -> tuple[MigrationRecord, ...]:
    """Classify retained quantity evidence without inventing missing state."""
    root = _mapping(payload, "ARTIFACT")
    execution_body, snapshot_payload, session = _artifact_parts(root)
    positions, pending = _snapshot_observations(snapshot_payload)
    raw_fills = execution_body.get("fills", [])
    fills = _rows(raw_fills, "FILLS")

    if not fills:
        records: list[MigrationRecord] = []
        for index, (ticker, shares) in enumerate(sorted(positions.items())):
            if shares <= 0:
                continue
            records.append(_record(
                session=session, index=index, ticker=ticker, side="UNKNOWN",
                planned=None, filled=None, remaining=None,
                observed_position=shares, classification=CLASS_ORPHANED_PARTIAL,
                evidence=(
                    "snapshot.positions.shares_present",
                    "execution.fills.absent",
                    "planned_quantity_absent",
                ),
            ))
        if records:
            return tuple(records)
        pending_tickers = sorted(pending)
        for index, (side, ticker) in enumerate(pending_tickers):
            records.append(_record(
                session=session, index=index, ticker=ticker, side=side,
                planned=None, filled=None, remaining=None,
                observed_position=positions.get(ticker), classification=CLASS_NO_QUANTITY,
                evidence=(
                    "snapshot.pending_intent_present",
                    "execution.fills.absent",
                    "planned_quantity_absent",
                ),
            ))
        return tuple(records)

    records = []
    for index, row in enumerate(fills):
        ticker = str(row.get("ticker", ""))
        side = str(row.get("side", "UNKNOWN"))
        status = str(row.get("status", ""))
        observed_position = positions.get(ticker)
        planned_raw = row.get("planned_shares")
        filled_raw = row.get("filled_shares")
        if planned_raw is None or filled_raw is None:
            records.append(_record(
                session=session, index=index, ticker=ticker, side=side,
                planned=None, filled=None, remaining=None,
                observed_position=observed_position, classification=CLASS_RECONCILIATION,
                evidence=("execution.fills.quantity_field_missing",),
            ))
            continue

        planned = _nonnegative_int(planned_raw, "PLANNED_SHARES")
        filled = _nonnegative_int(filled_raw, "FILLED_SHARES")
        if filled > planned:
            records.append(_record(
                session=session, index=index, ticker=ticker, side=side,
                planned=planned, filled=filled, remaining=None,
                observed_position=observed_position, classification=CLASS_RECONCILIATION,
                evidence=("execution.fills.filled_exceeds_planned",),
            ))
            continue

        if planned == filled:
            classification = CLASS_COMPLETE
            remaining = 0
            evidence = ("execution.fills.planned_shares", "execution.fills.filled_shares")
        elif filled == 0:
            pending_evidence = (side, ticker) in pending or status.endswith("_PENDING")
            if pending_evidence:
                classification = CLASS_EXPLICIT_PENDING
                remaining = planned
                evidence = (
                    "execution.fills.planned_shares",
                    "execution.fills.filled_shares_zero",
                    "pending_intent_or_pending_status",
                )
            else:
                classification = CLASS_RECONCILIATION
                remaining = None
                evidence = (
                    "execution.fills.filled_shares_zero",
                    "pending_evidence_absent",
                )
        else:
            classification = CLASS_RECOVERABLE_PARTIAL
            remaining = planned - filled
            evidence = (
                "execution.fills.planned_shares",
                "execution.fills.filled_shares",
                "remaining_derived_only_from_preserved_fill_vector",
            )
        records.append(_record(
            session=session, index=index, ticker=ticker, side=side,
            planned=planned, filled=filled, remaining=remaining,
            observed_position=observed_position, classification=classification,
            evidence=evidence,
        ))
    return tuple(records)


def audit_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    records = audit_legacy_artifact(payload)
    return {
        "record_count": len(records),
        "records": [record.as_payload() for record in records],
        "all_fail_closed": all(
            record.classification != CLASS_RECONCILIATION for record in records
        ),
    }


if __name__ == "__main__":
    print(json.dumps(audit_payload({"snapshot_payload": {"state": {
        "base_paper_state": {
            "positions": [{"ticker": "BBCA", "shares": 2_400}],
            "pending_buys": [], "pending_sells": [],
        },
    }}}), indent=2, sort_keys=True))
