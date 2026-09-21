from __future__ import annotations

from copy import deepcopy

import pytest

from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_migration_compatibility_v1 import (
    BLOCKED,
    LEGACY_POSITION_ONLY,
    MIGRATION_CANDIDATE,
    MIGRATION_COMPATIBILITY_SCHEMA,
    MIGRATABLE,
    RECOVERABLE_COMPLETE,
    RECOVERABLE_PARTIAL,
    RECOVERABLE_ZERO_FILL_PENDING,
    REQUIRES_RECONCILIATION,
    UNKNOWN_ORPHANED_PARTIAL,
    classify_legacy_evidence,
    verify_compatibility_result,
)


def _evidence(**overrides):
    value = {
        "schema_version": MIGRATION_COMPATIBILITY_SCHEMA,
        "session_date": "2026-09-20",
        "ticker": "BBCA.JK",
        "side": "BUY",
        "planned_shares": 10_000,
        "fill_vector": [10_000],
        "position_shares": 10_000,
        "pending": False,
        "event_payload_sha256": [
            {"event_id": "evt-1", "payload_sha256": "a" * 64}
        ],
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize(
    ("overrides", "classification", "disposition"),
    [
        ({}, RECOVERABLE_COMPLETE, MIGRATABLE),
        (
            {"fill_vector": None, "pending": True, "position_shares": 0},
            RECOVERABLE_ZERO_FILL_PENDING,
            MIGRATABLE,
        ),
        (
            {"fill_vector": [2_400, 1_600], "position_shares": 4_000, "pending": True},
            RECOVERABLE_PARTIAL,
            MIGRATION_CANDIDATE,
        ),
        (
            {"planned_shares": None, "fill_vector": None, "position_shares": 2_400},
            UNKNOWN_ORPHANED_PARTIAL,
            BLOCKED,
        ),
        (
            {"planned_shares": None, "fill_vector": None, "position_shares": None},
            LEGACY_POSITION_ONLY,
            BLOCKED,
        ),
        (
            {
                "fill_vector": [10_000],
                "event_payload_sha256": [
                    {"event_id": "evt-1", "payload_sha256": "a" * 64},
                    {"event_id": "evt-1", "payload_sha256": "b" * 64},
                ],
            },
            REQUIRES_RECONCILIATION,
            BLOCKED,
        ),
        (
            {"fill_vector": [12_000], "position_shares": 12_000},
            REQUIRES_RECONCILIATION,
            BLOCKED,
        ),
        (
            {"fill_vector": [2_400], "position_shares": 2_400, "pending": False},
            REQUIRES_RECONCILIATION,
            BLOCKED,
        ),
    ],
)
def test_classifies_each_compatibility_shape(overrides, classification, disposition):
    result = classify_legacy_evidence(_evidence(**overrides))
    assert result.classification == classification
    assert result.disposition == disposition
    assert result.payload()["source_payload_sha256"]
    verify_compatibility_result(result.payload())


def test_rejects_payload_shape_and_never_normalizes_unknown_fields():
    value = _evidence()
    value["unexpected"] = "do-not-ignore"
    with pytest.raises(DecisionV1Error, match="PAYLOAD_NOT_CANONICAL"):
        classify_legacy_evidence(value)


def test_rejects_non_lot_or_negative_quantities():
    for field in ("planned_shares", "position_shares"):
        value = _evidence(**{field: -100})
        with pytest.raises(DecisionV1Error):
            classify_legacy_evidence(value)
    value = _evidence(fill_vector=[101])
    with pytest.raises(DecisionV1Error):
        classify_legacy_evidence(value)


def test_result_hash_detects_tamper():
    result = classify_legacy_evidence(_evidence()).payload()
    tampered = deepcopy(result)
    tampered["classification"] = RECOVERABLE_PARTIAL
    with pytest.raises(DecisionV1Error, match="HASH_MISMATCH"):
        verify_compatibility_result(tampered)
