from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

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
    SqlitePortfolioSnapshotStore,
    assert_minimized_canonical_payload,
    derive_subaccount_ref,
    validate_snapshot_payload,
)

PINS = dict(REQUIRED_SOURCE_COMMIT_PINS)
KEY = b"synthetic-test-key-material-32-bytes-minimum!!"
SUB = derive_subaccount_ref("SYNTHETIC-REFERENCE-ONLY", KEY)
SCOPE = "ps_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
TZ = timezone(timedelta(hours=7))


def evidence(*, equity: int = 1, cash: int = 1):
    counts = {
        EndpointClass.PORTFOLIO_SUMMARY: equity + cash,
        EndpointClass.CASH: cash,
        EndpointClass.EQUITY: equity,
        EndpointClass.MUTUAL_FUND: 0,
        EndpointClass.BOND: 0,
        EndpointClass.OTHER: 0,
    }
    return tuple(EndpointEvidence(x, True, counts[x], counts[x], 0) for x in REQUIRED_ENDPOINT_CLASSES)


def snap(*, quantity=Decimal("1200"), fetched=2, offset=0, completeness=SnapshotCompleteness.COMPLETE, rows=None, raw="a" * 64, cash_amount=Decimal("2500000")):
    observed = datetime(2026, 8, 13, 12, 0, tzinfo=TZ) + timedelta(seconds=offset)
    return PortfolioSnapshot(
        observed,
        observed + timedelta(seconds=fetched),
        SCOPE,
        (PortfolioPosition(SecurityIdentity("TESTA", "Synthetic Equity A", "IDTESTA"), AssetClass.EQUITY, quantity, "IDR", "BROKER_SYNTHETIC", SUB),),
        (CashBalance("IDR", cash_amount, "BANK_SYNTHETIC", SUB),),
        PortfolioProvenance("AKSES_KSEI_PERSONAL", "skeleton-v1", raw, REQUIRED_ENDPOINT_CLASSES, PINS),
        completeness,
        rows or evidence(),
    )


def test_complete_requires_endpoint_evidence_and_balanced_rows():
    rows = list(evidence())
    rows[2] = EndpointEvidence(EndpointClass.EQUITY, True, 2, 1, 1, EndpointFailureCode.ROW_VALIDATION_FAILED)
    with pytest.raises(ValueError, match="COMPLETE requires"):
        snap(rows=tuple(rows))
    assert snap(completeness=SnapshotCompleteness.PARTIAL, rows=tuple(rows)).completeness is SnapshotCompleteness.PARTIAL


def test_required_endpoint_set_and_canonical_row_accounting():
    with pytest.raises(ValueError, match="every required endpoint"):
        snap(rows=evidence()[:-1])
    rows = list(evidence())
    rows[2] = EndpointEvidence(EndpointClass.EQUITY, True, 2, 2, 0)
    with pytest.raises(ValueError, match="canonical rows"):
        snap(rows=tuple(rows))


def test_source_pins_are_exact_and_immutable():
    provenance = snap().provenance
    with pytest.raises(TypeError):
        provenance.source_commit_pins["nichsedge/ksei-mcp"] = "0" * 40  # type: ignore[index]
    bad = dict(PINS)
    bad["nichsedge/ksei-mcp"] = "0" * 40
    with pytest.raises(ValueError, match="exactly match"):
        PortfolioProvenance("AKSES_KSEI_PERSONAL", "skeleton-v1", "a" * 64, REQUIRED_ENDPOINT_CLASSES, bad)


def test_opaque_subreference_and_sensitive_value_guards():
    assert SUB.startswith("ksa_") and len(SUB) == 68
    with pytest.raises(ValueError, match="keyed-HMAC"):
        CashBalance("IDR", Decimal("1"), subaccount_ref="1234" * 4)
    samples = (
        "Bea" + "rer " + "synthetic-value-123",
        "person" + "@example.com",
        "+62" + "81234567890",
        "3201" * 4,
    )
    for value in samples:
        with pytest.raises(ValueError):
            assert_minimized_canonical_payload({"label": value})


def test_duplicate_rows_are_rejected():
    base = snap()
    with pytest.raises(ValueError, match="duplicate portfolio position"):
        PortfolioSnapshot(base.snapshot_at, base.fetched_at, base.scope_ref, base.positions * 2, base.cash_balances, base.provenance, base.completeness, evidence(equity=2))
    with pytest.raises(ValueError, match="duplicate cash balance"):
        PortfolioSnapshot(base.snapshot_at, base.fetched_at, base.scope_ref, base.positions, base.cash_balances * 2, base.provenance, base.completeness, evidence(cash=2))


def test_decimal_scale_and_large_monetary_values_are_canonical():
    a = snap(quantity=Decimal("1200.0"), cash_amount=Decimal("25000000.00"))
    b = snap(quantity=Decimal("1200.00"), cash_amount=Decimal("25000000"))
    payload = a.canonical_dict()
    assert payload["positions"][0]["quantity"] == "1200"
    assert payload["cash_balances"][0]["amount"] == "25000000"
    assert a.history_dedup_key() == b.history_dedup_key()
    assert a.snapshot_id() == b.snapshot_id()
    assert snap(quantity=Decimal("-0.00")).canonical_dict()["positions"][0]["quantity"] == "0"


def test_schema_artifact_runtime_parity_and_timezone_format():
    checked = json.loads((Path(__file__).parents[1] / "schemas" / "personal_portfolio_snapshot_v1.schema.json").read_text())
    assert checked == PERSONAL_PORTFOLIO_SNAPSHOT_SCHEMA_V1
    payload = snap().canonical_dict()
    payload["snapshot_at"] = "2026-08-13T12:00:00"
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_snapshot_payload(payload)


def test_roundtrip_and_retry_dedup():
    first = snap(fetched=2)
    retry = snap(fetched=8)
    assert first.history_dedup_key() == retry.history_dedup_key()
    assert first.snapshot_id() != retry.snapshot_id()
    assert PortfolioSnapshot.from_canonical_json(first.canonical_json()).canonical_dict() == first.canonical_dict()


def test_append_store_is_atomic_and_partial_does_not_replace_last_good():
    store = SqlitePortfolioSnapshotStore.in_memory()
    first, retry = snap(fetched=2), snap(fetched=8)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(store.append_if_new, (first, retry)))
    assert sum(x.inserted for x in results) == 1

    rows = list(evidence())
    rows[4] = EndpointEvidence(EndpointClass.BOND, False, 0, 0, 0, EndpointFailureCode.PROVIDER_UNAVAILABLE)
    partial = snap(offset=10, raw="c" * 64, completeness=SnapshotCompleteness.PARTIAL, rows=tuple(rows))
    assert store.append_if_new(partial).inserted
    assert store.latest_observation(SCOPE).completeness is SnapshotCompleteness.PARTIAL
    assert store.latest_complete(SCOPE).completeness is SnapshotCompleteness.COMPLETE


def test_append_store_rejects_mutation_and_deletion():
    connection = sqlite3.connect(":memory:")
    store = SqlitePortfolioSnapshotStore(connection)
    store.append_if_new(snap())
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connection.execute("UPDATE personal_portfolio_snapshots SET completeness='PARTIAL' WHERE scope_ref=?", (SCOPE,))
    connection.rollback()
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connection.execute("DELETE FROM personal_portfolio_snapshots WHERE scope_ref=?", (SCOPE,))
