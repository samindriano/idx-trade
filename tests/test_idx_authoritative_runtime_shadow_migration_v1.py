from __future__ import annotations

from pathlib import Path

import pytest

from idx_trade import forward_dividend_runtime_v1_1 as runtime
from idx_trade import forward_dividend_v1 as dividend
from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_execution_v1_contract import (
    PaperPortfolioState,
    PaperPosition,
    pending_intents_from_obligations,
    paper_state_hash,
)
from idx_trade.v4_x1_migration_activation_v1 import (
    ACTIVATION_POLICY_SCHEMA,
    ACTIVATE_COMPATIBLE,
    REQUIRES_AUTHORIZATION,
    MigrationActivationPolicyV1,
)
from idx_trade.v4_x1_quantity_obligation_v1 import (
    apply_fill,
    plan_obligation,
)


def _policy(*, allow_legacy_mode: bool) -> MigrationActivationPolicyV1:
    return MigrationActivationPolicyV1(
        schema_version=ACTIVATION_POLICY_SCHEMA,
        policy_id="SYNTHETIC-SHADOW-MIGRATION-ONLY",
        authorization_ref="LOCAL-TEST-NO-LIVE-ACTIVATION",
        allow_legacy_mode=allow_legacy_mode,
        outcome_access=False,
    )


def _runtime_state(state: PaperPortfolioState) -> dividend.DividendAwarePaperState:
    return dividend.DividendAwarePaperState(
        base_state=state,
        dividend_ledger=dividend.DividendLedger(),
    )


def test_shadow_migration_preserves_state_hash_and_replay(tmp_path: Path) -> None:
    legacy = PaperPortfolioState(
        as_of_session_date="2026-09-20",
        cash_idr=1_000_000.0,
        positions=(),
    )
    legacy_snapshot = runtime.write_runtime_snapshot(
        tmp_path / "legacy-runtime",
        _runtime_state(legacy),
    )
    legacy_decision = runtime.build_runtime_snapshot_migration_activation_decision(
        legacy_snapshot.path,
        policy=_policy(allow_legacy_mode=False),
        decided_at_utc="2026-09-21T10:00:00Z",
    )
    assert legacy_decision.activation_status == REQUIRES_AUTHORIZATION

    planned = plan_obligation(
        obligation_id="SHADOW-BUY-BBCA-01",
        ticker="BBCA",
        side="BUY",
        planned_shares=5_000,
        session_date="2026-09-20",
    )
    partial = apply_fill(
        planned,
        event_id="SHADOW-FILL-BBCA-01",
        session_date="2026-09-20",
        filled_shares=2_400,
        reason="SYNTHETIC_PARTIAL",
    )
    pending_buys, pending_sells = pending_intents_from_obligations((partial,))
    v2_state = PaperPortfolioState(
        as_of_session_date="2026-09-20",
        cash_idr=1_000_000.0,
        positions=(PaperPosition("BBCA", 2_400),),
        pending_buys=pending_buys,
        pending_sells=pending_sells,
        obligations=(partial,),
    )
    before_hash = paper_state_hash(v2_state)
    v2_snapshot = runtime.write_runtime_snapshot(
        tmp_path / "v2-runtime",
        _runtime_state(v2_state),
    )
    bytes_before = v2_snapshot.path.read_bytes()

    provenance_path = tmp_path / "migration" / "provenance.json"
    decision_path = tmp_path / "migration" / "activation.json"
    persisted = runtime.write_runtime_snapshot_migration_activation_decision(
        v2_snapshot.path,
        provenance_path,
        decision_path,
        policy=_policy(allow_legacy_mode=False),
        decided_at_utc="2026-09-21T10:00:00Z",
    )
    assert persisted == (provenance_path.resolve(), decision_path.resolve())
    assert v2_snapshot.path.read_bytes() == bytes_before

    decision = runtime.build_runtime_snapshot_migration_activation_decision(
        v2_snapshot.path,
        policy=_policy(allow_legacy_mode=False),
        decided_at_utc="2026-09-21T10:00:00Z",
    )
    assert decision.activation_status == ACTIVATE_COMPATIBLE
    reloaded = runtime.load_runtime_snapshot(v2_snapshot.path)
    assert paper_state_hash(reloaded.state.base_state) == before_hash
    assert reloaded.state.base_state.obligations == (partial,)
    assert reloaded.state.base_state.positions == v2_state.positions


def test_shadow_migration_write_failure_leaves_immutable_partial_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = PaperPortfolioState(
        as_of_session_date="2026-09-20",
        cash_idr=1_000_000.0,
        positions=(),
    )
    snapshot = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _runtime_state(state),
    )
    snapshot_bytes = snapshot.path.read_bytes()
    provenance_path = tmp_path / "migration" / "provenance.json"
    decision_path = tmp_path / "migration" / "activation.json"

    def fail_decision_write(*args, **kwargs):
        raise DecisionV1Error("SYNTHETIC_DECISION_WRITE_FAILURE")

    monkeypatch.setattr(runtime, "write_migration_activation_decision_v1", fail_decision_write)
    with pytest.raises(DecisionV1Error, match="SYNTHETIC_DECISION_WRITE_FAILURE"):
        runtime.write_runtime_snapshot_migration_activation_decision(
            snapshot.path,
            provenance_path,
            decision_path,
            policy=_policy(allow_legacy_mode=False),
            decided_at_utc="2026-09-21T10:00:00Z",
        )
    assert provenance_path.is_file()
    assert not decision_path.exists()
    assert snapshot.path.read_bytes() == snapshot_bytes
