from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from idx_trade.personal_portfolio import (
    AssetClass,
    CashBalance,
    EndpointClass,
    EndpointEvidence,
    EndpointFailureCode,
    PERSONAL_PORTFOLIO_SNAPSHOT_SCHEMA_V1,
    PortfolioPosition,
    PortfolioProvenance,
    PortfolioSnapshot,
    REQUIRED_ENDPOINT_CLASSES,
    REQUIRED_SOURCE_COMMIT_PINS,
    SecurityIdentity,
    SnapshotCompleteness,
    derive_subaccount_ref,
    validate_snapshot_payload,
)

TZ = timezone(timedelta(hours=7))
SCOPE = "ps_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
KEY = b"semantic-gate-synthetic-key-material-32-bytes!!"
SUB = derive_subaccount_ref("SYNTHETIC-SEMANTIC-REFERENCE", KEY)


def _evidence() -> tuple[EndpointEvidence, ...]:
    counts = {
        EndpointClass.PORTFOLIO_SUMMARY: 2,
        EndpointClass.CASH: 1,
        EndpointClass.EQUITY: 1,
        EndpointClass.MUTUAL_FUND: 0,
        EndpointClass.BOND: 0,
        EndpointClass.OTHER: 0,
    }
    return tuple(
        EndpointEvidence(endpoint, True, counts[endpoint], counts[endpoint], 0)
        for endpoint in REQUIRED_ENDPOINT_CLASSES
    )


def payload():
    observed = datetime(2026, 8, 13, 12, 0, tzinfo=TZ)
    snapshot = PortfolioSnapshot(
        observed,
        observed + timedelta(seconds=2),
        SCOPE,
        (
            PortfolioPosition(
                SecurityIdentity("TESTA", "Synthetic Equity A", "IDTESTA"),
                AssetClass.EQUITY,
                Decimal("1200"),
                "IDR",
                "BROKER_SYNTHETIC",
                SUB,
            ),
        ),
        (CashBalance("IDR", Decimal("2500000"), "BANK_SYNTHETIC", SUB),),
        PortfolioProvenance(
            "AKSES_KSEI_PERSONAL",
            "skeleton-v1",
            "a" * 64,
            REQUIRED_ENDPOINT_CLASSES,
            dict(REQUIRED_SOURCE_COMMIT_PINS),
        ),
        SnapshotCompleteness.COMPLETE,
        _evidence(),
    )
    return snapshot.canonical_dict()


def test_checked_schema_itself_rejects_naive_timestamps():
    candidate = payload()
    candidate["snapshot_at"] = "2026-08-13T12:00:00"
    validator = Draft202012Validator(
        PERSONAL_PORTFOLIO_SNAPSHOT_SCHEMA_V1,
        format_checker=FormatChecker(),
    )
    errors = list(validator.iter_errors(candidate))
    assert any(list(error.absolute_path) == ["snapshot_at"] for error in errors)


def test_direct_payload_rejects_endpoint_arithmetic_mismatch():
    candidate = payload()
    candidate["endpoint_evidence"][2]["observed_rows"] = 3
    with pytest.raises(ValueError, match=r"observed=accepted\+rejected"):
        validate_snapshot_payload(candidate)


def test_failed_endpoint_rows_rejected_in_schema_and_object_contract():
    candidate = payload()
    row = candidate["endpoint_evidence"][4]
    row.update(
        succeeded=False,
        observed_rows=1,
        accepted_rows=0,
        rejected_rows=0,
        failure_code="PROVIDER_UNAVAILABLE",
    )
    candidate["completeness"] = "PARTIAL"
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_snapshot_payload(candidate)

    with pytest.raises(ValueError, match="zero observed, accepted, and rejected"):
        EndpointEvidence(
            EndpointClass.BOND,
            False,
            1,
            0,
            0,
            EndpointFailureCode.PROVIDER_UNAVAILABLE,
        )


def test_direct_payload_rejects_duplicate_positions_and_cash():
    candidate = payload()
    candidate["positions"].append(deepcopy(candidate["positions"][0]))
    candidate["endpoint_evidence"][2]["observed_rows"] = 2
    candidate["endpoint_evidence"][2]["accepted_rows"] = 2
    with pytest.raises(ValueError, match="duplicate portfolio position"):
        validate_snapshot_payload(candidate)

    candidate = payload()
    candidate["cash_balances"].append(deepcopy(candidate["cash_balances"][0]))
    candidate["endpoint_evidence"][1]["observed_rows"] = 2
    candidate["endpoint_evidence"][1]["accepted_rows"] = 2
    with pytest.raises(ValueError, match="duplicate cash balance"):
        validate_snapshot_payload(candidate)


def test_direct_payload_rejects_detail_count_mismatch():
    candidate = payload()
    candidate["endpoint_evidence"][2]["observed_rows"] = 2
    candidate["endpoint_evidence"][2]["accepted_rows"] = 2
    with pytest.raises(ValueError, match="EQUITY accepted_rows=2 does not match canonical rows=1"):
        validate_snapshot_payload(candidate)


def test_summary_is_reconciled_to_represented_asset_classes():
    candidate = payload()
    summary = candidate["endpoint_evidence"][0]
    summary["observed_rows"] = 999
    summary["accepted_rows"] = 999
    with pytest.raises(ValueError, match="represented asset-class summaries=2"):
        validate_snapshot_payload(candidate)


def test_timezone_ordering_is_shared_semantics_not_constructor_only():
    candidate = payload()
    candidate["fetched_at"] = "2026-08-13T11:59:59+07:00"
    with pytest.raises(ValueError, match="fetched_at must be >= snapshot_at"):
        validate_snapshot_payload(candidate)
