from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

_ENDPOINT_CLASSES = (
    "PORTFOLIO_SUMMARY",
    "CASH",
    "EQUITY",
    "MUTUAL_FUND",
    "BOND",
    "OTHER",
)
_DETAIL_CLASSES = _ENDPOINT_CLASSES[1:]


def parse_aware_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO-8601 string")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 date-time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include an explicit timezone offset")
    return parsed


def validate_endpoint_evidence_values(
    *,
    succeeded: bool,
    observed_rows: int,
    accepted_rows: int,
    rejected_rows: int,
    failure_code: str | None,
) -> None:
    if not isinstance(succeeded, bool):
        raise ValueError("succeeded must be boolean")
    for field_name, value in (
        ("observed_rows", observed_rows),
        ("accepted_rows", accepted_rows),
        ("rejected_rows", rejected_rows),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer")

    if succeeded:
        if observed_rows != accepted_rows + rejected_rows:
            raise ValueError("successful endpoint row accounting must satisfy observed=accepted+rejected")
        if rejected_rows == 0 and failure_code is not None:
            raise ValueError("successful fully validated endpoint must not have failure_code")
        if rejected_rows > 0 and failure_code is None:
            raise ValueError("rejected endpoint rows require a sanitized failure_code")
        return

    if failure_code is None:
        raise ValueError("failed endpoint requires a sanitized failure_code")
    if observed_rows != 0 or accepted_rows != 0 or rejected_rows != 0:
        raise ValueError("failed endpoint must report zero observed, accepted, and rejected rows")


def _position_identity(item: Mapping[str, Any]) -> tuple[Any, ...]:
    security = item.get("security")
    if not isinstance(security, Mapping):
        raise ValueError("position.security must be an object")
    return (
        security.get("symbol"),
        security.get("security_code"),
        item.get("asset_class"),
        item.get("currency"),
        item.get("broker_or_custodian"),
        item.get("subaccount_ref"),
    )


def _cash_identity(item: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        item.get("currency"),
        item.get("bank_or_custodian"),
        item.get("subaccount_ref"),
    )


def _reject_duplicate_payload_rows(rows: Sequence[Any], *, label: str) -> None:
    seen: set[tuple[Any, ...]] = set()
    identity = _position_identity if label == "portfolio position" else _cash_identity
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError(f"{label} rows must be objects")
        key = identity(row)
        if key in seen:
            raise ValueError(f"duplicate {label} identity is not allowed")
        seen.add(key)


def _expected_detail_counts(payload: Mapping[str, Any]) -> dict[str, int]:
    positions = payload.get("positions")
    cash_balances = payload.get("cash_balances")
    if not isinstance(positions, Sequence) or isinstance(positions, (str, bytes, bytearray)):
        raise ValueError("positions must be an array")
    if not isinstance(cash_balances, Sequence) or isinstance(cash_balances, (str, bytes, bytearray)):
        raise ValueError("cash_balances must be an array")

    counts = {endpoint: 0 for endpoint in _DETAIL_CLASSES}
    counts["CASH"] = len(cash_balances)
    for item in positions:
        if not isinstance(item, Mapping):
            raise ValueError("position rows must be objects")
        asset_class = item.get("asset_class")
        if asset_class not in counts or asset_class == "CASH":
            raise ValueError(f"unsupported canonical position asset_class: {asset_class}")
        counts[str(asset_class)] += 1
    return counts


def expected_summary_rows(payload: Mapping[str, Any]) -> int:
    """V1 summary semantics: one aggregate row per represented asset class.

    The reviewed unofficial clients expose the summary as category aggregates rather
    than security-level rows. Until one bounded sanitized real response proves a
    different invariant, V1 fails closed to the number of non-empty canonical asset
    classes. A provider shape that always includes zero-value categories requires a
    reviewed contract revision rather than silent acceptance.
    """

    detail_counts = _expected_detail_counts(payload)
    return sum(count > 0 for count in detail_counts.values())


def validate_snapshot_semantics(payload: Mapping[str, Any]) -> None:
    """Authoritative cross-field validation for canonical snapshot payloads."""

    snapshot_at = parse_aware_datetime(payload.get("snapshot_at"), "snapshot_at")
    fetched_at = parse_aware_datetime(payload.get("fetched_at"), "fetched_at")
    if fetched_at < snapshot_at:
        raise ValueError("fetched_at must be >= snapshot_at")

    positions = payload.get("positions")
    cash_balances = payload.get("cash_balances")
    evidence = payload.get("endpoint_evidence")
    if not isinstance(positions, Sequence) or isinstance(positions, (str, bytes, bytearray)):
        raise ValueError("positions must be an array")
    if not isinstance(cash_balances, Sequence) or isinstance(cash_balances, (str, bytes, bytearray)):
        raise ValueError("cash_balances must be an array")
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes, bytearray)):
        raise ValueError("endpoint_evidence must be an array")

    _reject_duplicate_payload_rows(positions, label="portfolio position")
    _reject_duplicate_payload_rows(cash_balances, label="cash balance")

    if len(evidence) != len(_ENDPOINT_CLASSES):
        raise ValueError("endpoint_evidence must contain every required endpoint exactly once")

    evidence_by_class: dict[str, Mapping[str, Any]] = {}
    for expected_class, item in zip(_ENDPOINT_CLASSES, evidence, strict=True):
        if not isinstance(item, Mapping):
            raise ValueError("endpoint_evidence rows must be objects")
        endpoint_class = item.get("endpoint_class")
        if endpoint_class != expected_class:
            raise ValueError("endpoint_evidence must use canonical required endpoint order")
        failure_code = item.get("failure_code")
        validate_endpoint_evidence_values(
            succeeded=item.get("succeeded"),
            observed_rows=item.get("observed_rows"),
            accepted_rows=item.get("accepted_rows"),
            rejected_rows=item.get("rejected_rows"),
            failure_code=str(failure_code) if failure_code is not None else None,
        )
        evidence_by_class[expected_class] = item

    expected_detail = _expected_detail_counts(payload)
    for endpoint_class, canonical_count in expected_detail.items():
        accepted_rows = evidence_by_class[endpoint_class].get("accepted_rows")
        if accepted_rows != canonical_count:
            raise ValueError(
                f"{endpoint_class} accepted_rows={accepted_rows} does not match canonical rows={canonical_count}"
            )

    expected_summary = expected_summary_rows(payload)
    summary_accepted = evidence_by_class["PORTFOLIO_SUMMARY"].get("accepted_rows")
    if summary_accepted != expected_summary:
        raise ValueError(
            "PORTFOLIO_SUMMARY accepted_rows="
            f"{summary_accepted} does not match represented asset-class summaries={expected_summary}"
        )

    completeness = payload.get("completeness")
    incomplete = [
        item
        for item in evidence_by_class.values()
        if (not item.get("succeeded")) or item.get("rejected_rows", 0) > 0
    ]
    if completeness == "COMPLETE" and incomplete:
        raise ValueError("COMPLETE requires every required endpoint to succeed with zero rejected rows")
    if completeness == "PARTIAL" and not incomplete:
        raise ValueError("PARTIAL requires explicit endpoint failure or rejected rows")
