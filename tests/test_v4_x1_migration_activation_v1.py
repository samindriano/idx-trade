from __future__ import annotations

import json

import pytest

from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_execution_v1_contract import (
    PaperPortfolioState,
    PaperPosition,
    PendingPaperIntent,
)
from idx_trade.v4_x1_migration_activation_v1 import (
    ACTIVATION_POLICY_SCHEMA,
    ACTIVATE_COMPATIBLE,
    ACTIVATE_LEGACY_MODE,
    BLOCKED_RECONCILIATION,
    REQUIRES_AUTHORIZATION,
    MigrationActivationPolicyV1,
    authorize_migration_activation,
    load_migration_activation_decision_v1,
    write_migration_activation_decision_v1,
)
from idx_trade.v4_x1_migration_provenance_v1 import build_migration_provenance_v1
from idx_trade.v4_x1_quantity_obligation_v1 import plan_obligation


def _provenance(state: PaperPortfolioState) -> dict[str, object]:
    return build_migration_provenance_v1(
        state,
        source_artifact_sha256="a" * 64,
        source_schema_version="legacy_snapshot_v1",
        decided_at_utc="2026-09-20T10:00:00Z",
    ).payload()


def _policy(*, allow_legacy_mode: bool) -> MigrationActivationPolicyV1:
    return MigrationActivationPolicyV1(
        schema_version=ACTIVATION_POLICY_SCHEMA,
        policy_id="synthetic-migration-policy-v1",
        authorization_ref="synthetic-test-authorization",
        allow_legacy_mode=allow_legacy_mode,
    )


def test_legacy_activation_requires_explicit_policy_authorization() -> None:
    state = PaperPortfolioState(
        as_of_session_date="2026-08-20",
        cash_idr=1_000_000.0,
        positions=(),
    )
    denied = authorize_migration_activation(_provenance(state), _policy(allow_legacy_mode=False))
    assert denied.activation_status == REQUIRES_AUTHORIZATION
    allowed = authorize_migration_activation(_provenance(state), _policy(allow_legacy_mode=True))
    assert allowed.activation_status == ACTIVATE_LEGACY_MODE


def test_compatible_state_can_be_authorized_without_legacy_mode() -> None:
    obligation = plan_obligation(
        obligation_id="BUY-BBCA-ACTIVATION",
        ticker="BBCA",
        side="BUY",
        planned_shares=5_000,
        session_date="2026-08-20",
    )
    state = PaperPortfolioState(
        as_of_session_date="2026-08-20",
        cash_idr=1_000_000.0,
        positions=(),
        pending_buys=(PendingPaperIntent("BUY", "BBCA", None, "PLANNED"),),
        obligations=(obligation,),
    )
    decision = authorize_migration_activation(_provenance(state), _policy(allow_legacy_mode=False))
    assert decision.activation_status == ACTIVATE_COMPATIBLE


def test_orphaned_state_remains_blocked_even_with_legacy_policy() -> None:
    state = PaperPortfolioState(
        as_of_session_date="2026-08-20",
        cash_idr=1_000_000.0,
        positions=(PaperPosition("BBCA", 2_400),),
    )
    decision = authorize_migration_activation(_provenance(state), _policy(allow_legacy_mode=True))
    assert decision.activation_status == BLOCKED_RECONCILIATION


def test_activation_decision_is_immutable_and_hash_verified(tmp_path) -> None:
    state = PaperPortfolioState(
        as_of_session_date="2026-08-20",
        cash_idr=1_000_000.0,
        positions=(),
    )
    decision = authorize_migration_activation(_provenance(state), _policy(allow_legacy_mode=True))
    path = tmp_path / "activation.json"
    assert write_migration_activation_decision_v1(path, decision) == path.resolve()
    original = path.read_bytes()
    assert write_migration_activation_decision_v1(path, decision) == path.resolve()
    assert path.read_bytes() == original
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["reason_code"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DecisionV1Error, match="HASH_MISMATCH"):
        load_migration_activation_decision_v1(path)
