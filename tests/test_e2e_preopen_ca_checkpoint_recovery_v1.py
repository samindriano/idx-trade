from __future__ import annotations

from pathlib import Path

from idx_trade.e2e_paper_cloud_runtime_v1 import (
    LocalConditionalStore,
    build_runtime_snapshot,
    canonical_json_bytes,
    sha256_bytes,
)
import idx_trade.e2e_paper_preopen_ca_cloud_v1 as preopen_ca


SESSION = "2026-08-28"
CODE_SHA = "a" * 40
RUNNER_SHA = "9" * 64
SCHEDULE_SHA = "b" * 64
INPUT_SHA = "c" * 64


def _guards() -> dict[str, bool]:
    return {
        "outcome_accessed": False,
        "protected_forward_accessed": False,
        "model_refit": False,
        "paper_state_mutated": False,
        "order_created": False,
        "fill_created": False,
        "retroactive_execution_authorized": False,
    }


def _result(marker: str) -> dict[str, object]:
    return {
        "schema_version": "idx_trade_e2e_paper_preopen_ca_result_v1",
        "session_date": SESSION,
        "stage": preopen_ca.CHECKPOINT_STAGE,
        "controller_status": preopen_ca.CHECKPOINT_STATUS,
        "marker": marker,
        **_guards(),
    }


def _identity() -> dict[str, str]:
    return {
        "repo": "samindriano/idx-trade",
        "commit": CODE_SHA,
        "runner_sha256": RUNNER_SHA,
    }


def _snapshot(tmp_path: Path):
    root = tmp_path / "runtime"
    root.mkdir()
    (root / "sentinel.txt").write_text("ready\n", encoding="utf-8")
    return build_runtime_snapshot({"paper": root})


def test_orphaned_result_child_does_not_poison_retry(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    snapshot, snapshot_sha, metadata = _snapshot(tmp_path)

    orphan_bytes = canonical_json_bytes(_result("orphaned-attempt"))
    orphan_sha = sha256_bytes(orphan_bytes)
    orphan_key = preopen_ca._checkpoint_result_key(SESSION, orphan_sha)
    store.put_if_absent(orphan_key, orphan_bytes, "application/json")

    # Simulate a crash after a snapshot child write as well. Content-addressing
    # must make the exact snapshot safe to reuse on the next attempt.
    snapshot_key = preopen_ca._checkpoint_snapshot_key(SESSION, snapshot_sha)
    store.put_if_absent(snapshot_key, snapshot, "application/zip")
    assert store.read(preopen_ca.checkpoint_commit_key(SESSION)) is None

    committed = preopen_ca.commit_preopen_ca_checkpoint(
        store,
        session_date=SESSION,
        snapshot_bytes=snapshot,
        snapshot_metadata=metadata,
        result_payload=_result("retry"),
        schedule_attestation_sha256=SCHEDULE_SHA,
        input_manifest_sha256=INPUT_SHA,
        code_identity=_identity(),
    )
    assert committed.snapshot_key == snapshot_key
    assert committed.result_key != orphan_key
    assert committed.payload["result"]["key"] == committed.result_key


def test_content_addressed_child_keys_are_sha_bound(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    snapshot, snapshot_sha, metadata = _snapshot(tmp_path)
    committed = preopen_ca.commit_preopen_ca_checkpoint(
        store,
        session_date=SESSION,
        snapshot_bytes=snapshot,
        snapshot_metadata=metadata,
        result_payload=_result("stable"),
        schedule_attestation_sha256=SCHEDULE_SHA,
        input_manifest_sha256=INPUT_SHA,
        code_identity=_identity(),
    )
    assert committed.snapshot_key.endswith(f"/{snapshot_sha}.zip")
    assert committed.result_key.endswith(f"/{committed.result_sha256}.json")
