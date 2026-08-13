from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from idx_trade.personal_portfolio import PERSONAL_PORTFOLIO_SNAPSHOT_SCHEMA_V1, validate_snapshot_payload
from test_snapshot_hardening import snap


def payload():
    return snap().canonical_dict()


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
    with pytest.raises(ValueError, match="observed=accepted\+rejected"):
        validate_snapshot_payload(candidate)


def test_direct_payload_rejects_failed_endpoint_with_nonzero_rows():
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
    with pytest.raises(ValueError, match="zero observed, accepted, and rejected"):
        validate_snapshot_payload(candidate)


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
