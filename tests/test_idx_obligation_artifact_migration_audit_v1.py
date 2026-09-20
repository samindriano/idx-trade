from research.idx_obligation_artifact_migration_audit_v1 import (
    CLASS_COMPLETE,
    CLASS_EXPLICIT_PENDING,
    CLASS_ORPHANED_PARTIAL,
    CLASS_RECONCILIATION,
    CLASS_RECOVERABLE_PARTIAL,
    audit_legacy_artifact,
)


def _snapshot(*, positions=(), pending_buys=(), pending_sells=()):
    return {
        "session_date": "2026-09-20",
        "state": {"base_paper_state": {
            "positions": [
                {"ticker": ticker, "shares": shares}
                for ticker, shares in positions
            ],
            "pending_buys": [
                {"side": "BUY", "ticker": ticker, "rank_consensus": 1,
                 "reason": "CAPACITY", "replacement_peer": None}
                for ticker in pending_buys
            ],
            "pending_sells": [
                {"side": "SELL", "ticker": ticker, "rank_consensus": 1,
                 "reason": "CAPACITY", "replacement_peer": None}
                for ticker in pending_sells
            ],
        }},
    }


def _artifact(*, fill=None, snapshot=None):
    payload = {"snapshot_payload": snapshot or _snapshot()}
    if fill is not None:
        payload["execution_body"] = {
            "execution_session_date": "2026-09-20",
            "fills": [fill],
        }
    return payload


def test_complete_historical_fill_has_zero_remainder():
    rows = audit_legacy_artifact(_artifact(fill={
        "side": "BUY", "ticker": "BBCA", "planned_shares": 5_000,
        "filled_shares": 5_000, "status": "SIMULATED_FILLED",
    }, snapshot=_snapshot(positions=(("BBCA", 5_000),))))

    assert rows[0].classification == CLASS_COMPLETE
    assert rows[0].remaining_shares == 0


def test_positive_partial_is_recoverable_only_from_preserved_fill_vector():
    rows = audit_legacy_artifact(_artifact(fill={
        "side": "BUY", "ticker": "BBCA", "planned_shares": 5_000,
        "filled_shares": 2_400, "status": "SIMULATED_FILLED",
    }, snapshot=_snapshot(positions=(("BBCA", 2_400),))))

    assert rows[0].classification == CLASS_RECOVERABLE_PARTIAL
    assert rows[0].remaining_shares == 2_600
    assert "remaining_derived_only_from_preserved_fill_vector" in rows[0].evidence


def test_zero_lot_pending_preserves_explicit_remainder():
    rows = audit_legacy_artifact(_artifact(fill={
        "side": "BUY", "ticker": "BBCA", "planned_shares": 5_000,
        "filled_shares": 0, "status": "REFERENCE_DAY_CAPACITY_ZERO_PENDING",
    }, snapshot=_snapshot(pending_buys=("BBCA",))))

    assert rows[0].classification == CLASS_EXPLICIT_PENDING
    assert rows[0].remaining_shares == 5_000


def test_snapshot_only_positive_position_is_unknown_and_has_no_remainder():
    rows = audit_legacy_artifact(_artifact(
        snapshot=_snapshot(positions=(("BBCA", 2_400),)),
    ))

    assert rows[0].classification == CLASS_ORPHANED_PARTIAL
    assert rows[0].planned_shares is None
    assert rows[0].filled_shares is None
    assert rows[0].remaining_shares is None


def test_quantity_inversion_is_fail_closed():
    rows = audit_legacy_artifact(_artifact(fill={
        "side": "BUY", "ticker": "BBCA", "planned_shares": 2_400,
        "filled_shares": 5_000, "status": "SIMULATED_FILLED",
    }, snapshot=_snapshot(positions=(("BBCA", 5_000),))))

    assert rows[0].classification == CLASS_RECONCILIATION
    assert rows[0].remaining_shares is None


def test_remainder_is_never_inferred_from_position_only():
    rows = audit_legacy_artifact(_artifact(
        snapshot=_snapshot(positions=(("BBCA", 2_400),)),
    ))
    assert rows[0].remaining_shares is None
