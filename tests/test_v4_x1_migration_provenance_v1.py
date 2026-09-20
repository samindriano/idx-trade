from __future__ import annotations

import hashlib
import json

import pytest

import idx_trade.forward_dividend_runtime_v1_1 as runtime
import idx_trade.forward_dividend_v1 as dividend
from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_execution_v1_contract import (
    LEGACY_POSITION_ONLY,
    OBLIGATION_V1_STATE,
    PaperPortfolioState,
    PaperPosition,
    PendingPaperIntent,
    UNKNOWN_ORPHANED_PARTIAL,
)
from idx_trade.v4_x1_quantity_obligation_v1 import plan_obligation
from idx_trade.v4_x1_migration_provenance_v1 import (
    MIGRATION_ALREADY_COMPATIBLE,
    MIGRATION_BLOCKED_RECONCILIATION,
    MIGRATION_REQUIRES_LEGACY_MODE,
    MigrationProvenanceV1,
    build_migration_provenance_v1,
    load_migration_provenance_v1,
    verify_migration_provenance_payload,
    write_migration_provenance_v1,
)


def _state(**overrides: object) -> PaperPortfolioState:
    values: dict[str, object] = {
        "as_of_session_date": "2026-08-20",
        "cash_idr": 1_000_000.0,
        "positions": (),
    }
    values.update(overrides)
    return PaperPortfolioState(**values)  # type: ignore[arg-type]


def _build(state: PaperPortfolioState):
    return build_migration_provenance_v1(
        state,
        source_artifact_sha256="a" * 64,
        source_schema_version="legacy_snapshot_v1",
        decided_at_utc="2026-09-20T10:00:00Z",
        runtime_lineage_sha256="b" * 64,
    )


def test_migration_provenance_records_legacy_mode_without_quantity_claim() -> None:
    artifact = _build(_state())
    assert artifact.classification == LEGACY_POSITION_ONLY
    assert artifact.disposition == MIGRATION_REQUIRES_LEGACY_MODE
    assert artifact.source_state_sha256
    assert artifact.payload()["runtime_lineage_sha256"] == "b" * 64
    assert verify_migration_provenance_payload(artifact.payload())["payload_sha256"]


def test_orphaned_positive_position_is_blocked_and_not_reconstructed() -> None:
    artifact = _build(_state(positions=(PaperPosition("BBCA", 2_400),)))
    assert artifact.classification == UNKNOWN_ORPHANED_PARTIAL
    assert artifact.disposition == MIGRATION_BLOCKED_RECONCILIATION
    assert artifact.reason_code == "CLASSIFIED_UNKNOWN_ORPHANED_PARTIAL"


def test_obligation_state_is_recorded_as_already_compatible() -> None:
    planned = plan_obligation(
        obligation_id="BUY-BBCA-MIGRATION",
        ticker="BBCA",
        side="BUY",
        planned_shares=5_000,
        session_date="2026-08-20",
    )
    artifact = _build(
        _state(
            pending_buys=(
                PendingPaperIntent("BUY", "BBCA", None, "PLANNED"),
            ),
            obligations=(planned,),
        )
    )
    assert artifact.classification == OBLIGATION_V1_STATE
    assert artifact.disposition == MIGRATION_ALREADY_COMPATIBLE


def test_invalid_state_is_recorded_as_reconciliation_required() -> None:
    artifact = _build(_state(positions=(PaperPosition("BBCA", -100),)))
    assert artifact.classification == "REQUIRES_RECONCILIATION"
    assert artifact.disposition == MIGRATION_BLOCKED_RECONCILIATION
    assert artifact.source_state_sha256 is None


def test_payload_tamper_is_rejected() -> None:
    payload = _build(_state()).payload()
    payload["source_artifact_sha256"] = "c" * 64
    with pytest.raises(DecisionV1Error, match="PAYLOAD_HASH_MISMATCH"):
        verify_migration_provenance_payload(payload)


def test_hash_valid_extension_is_rejected_as_noncanonical() -> None:
    payload = _build(_state()).payload()
    payload["unexpected_extension"] = True
    body = dict(payload)
    body.pop("payload_sha256")
    payload["payload_sha256"] = hashlib.sha256(
        (
            json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode()
    ).hexdigest()

    with pytest.raises(DecisionV1Error, match="PAYLOAD_NOT_CANONICAL"):
        verify_migration_provenance_payload(payload)


def test_artifact_write_is_immutable_and_idempotent(tmp_path) -> None:
    path = tmp_path / "migration" / "2026-08-20.json"
    provenance = _build(_state())
    assert write_migration_provenance_v1(path, provenance) == path.resolve()
    original = path.read_bytes()
    assert write_migration_provenance_v1(path, provenance) == path.resolve()
    assert path.read_bytes() == original
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["disposition"] = MIGRATION_BLOCKED_RECONCILIATION
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DecisionV1Error, match="PAYLOAD_HASH_MISMATCH"):
        load_migration_provenance_v1(path)


def test_artifact_write_rejects_different_same_path(tmp_path) -> None:
    path = tmp_path / "migration.json"
    write_migration_provenance_v1(path, _build(_state()))
    other = _build(_state(as_of_session_date="2026-08-21"))
    with pytest.raises(DecisionV1Error, match="IMMUTABLE_CONFLICT"):
        write_migration_provenance_v1(path, other)


def test_runtime_snapshot_consumer_binds_exact_legacy_source(tmp_path) -> None:
    state = dividend.DividendAwarePaperState(
        base_state=_state(),
        dividend_ledger=dividend.DividendLedger(),
    )
    snapshot = runtime.write_runtime_snapshot(tmp_path / "runtime", state)
    provenance = runtime.build_runtime_snapshot_migration_provenance(
        snapshot.path,
        decided_at_utc="2026-09-20T10:00:00Z",
    )
    assert provenance.source_artifact_sha256 == snapshot.file_sha256
    assert provenance.source_schema_version == runtime.RUNTIME_SCHEMA
    output = runtime.write_runtime_snapshot_migration_provenance(
        snapshot.path,
        tmp_path / "migration.json",
        decided_at_utc="2026-09-20T10:00:00Z",
    )
    assert load_migration_provenance_v1(output)["source_artifact_sha256"] == (
        snapshot.file_sha256
    )
    source_payload = json.loads(snapshot.path.read_text(encoding="utf-8"))
    source_payload["state"]["base_paper_state"]["cash_idr"] = 1_000_001.0
    snapshot.path.write_text(json.dumps(source_payload), encoding="utf-8")
    with pytest.raises(DecisionV1Error):
        runtime.build_runtime_snapshot_migration_provenance(
            snapshot.path,
            decided_at_utc="2026-09-20T10:00:00Z",
        )
