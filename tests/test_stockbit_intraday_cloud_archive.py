from __future__ import annotations

from pathlib import Path

import pytest

from idx_trade.stockbit_intraday_cloud_archive import (
    StockbitIntradayCloudArchive,
    StockbitIntradayCloudError,
)
from idx_trade.stockbit_intraday_cloud_storage import LocalConditionalStore
from idx_trade.stockbit_stream_archive import StorageImmutabilityConflict


SESSION = "2026-08-26"


def _archive(tmp_path: Path) -> StockbitIntradayCloudArchive:
    return StockbitIntradayCloudArchive(LocalConditionalStore(tmp_path / "cloud"))


def _result(status: str) -> dict[str, object]:
    return {"status": status, "summary": {"complete": status == "ADMISSIBLE_COMPLETE"}}


def test_slot_commit_is_write_last_readback_verified_and_idempotent(tmp_path: Path):
    archive = _archive(tmp_path)
    first = archive.commit_slot(
        session_date=SESSION,
        slot="1830",
        status="WAITING_RECOVERY_RETRY",
        snapshot_bytes=b"snapshot-one",
        result_payload=_result("WAITING_RECOVERY_RETRY"),
        code_identity={"repo": "samindriano/idx-trade", "commit": "a" * 40},
        eod_manifest_sha256="b" * 64,
        session_manifest_sha256=None,
    )
    assert first.status == "WAITING_RECOVERY_RETRY"
    assert first.payload["commit_state"] == "COMMITTED"
    assert archive.existing_slot(SESSION, "1830") == first

    second = archive.commit_slot(
        session_date=SESSION,
        slot="1830",
        status="WAITING_RECOVERY_RETRY",
        snapshot_bytes=b"snapshot-one",
        result_payload=_result("WAITING_RECOVERY_RETRY"),
        code_identity={"repo": "samindriano/idx-trade", "commit": "a" * 40},
        eod_manifest_sha256="b" * 64,
        session_manifest_sha256=None,
    )
    assert second.commit_sha256 == first.commit_sha256


def test_divergent_same_slot_recomputation_fails_closed(tmp_path: Path):
    archive = _archive(tmp_path)
    archive.commit_slot(
        session_date=SESSION,
        slot="1830",
        status="WAITING_RECOVERY_RETRY",
        snapshot_bytes=b"snapshot-one",
        result_payload=_result("WAITING_RECOVERY_RETRY"),
        code_identity={"commit": "a" * 40},
        eod_manifest_sha256="b" * 64,
        session_manifest_sha256=None,
    )
    with pytest.raises(StockbitIntradayCloudError, match="EXISTING_IDENTITY_CONFLICT"):
        archive.commit_slot(
            session_date=SESSION,
            slot="1830",
            status="ADMISSIBLE_COMPLETE",
            snapshot_bytes=b"different-snapshot",
            result_payload=_result("ADMISSIBLE_COMPLETE"),
            code_identity={"commit": "a" * 40},
            eod_manifest_sha256="b" * 64,
            session_manifest_sha256="c" * 64,
        )


def test_known_slot_order_works_without_bucket_listing(tmp_path: Path):
    archive = _archive(tmp_path)
    archive.commit_slot(
        session_date=SESSION,
        slot="1930",
        status="WAITING_RECOVERY_RETRY",
        snapshot_bytes=b"s1",
        result_payload=_result("WAITING_RECOVERY_RETRY"),
        code_identity={"commit": "a" * 40},
        eod_manifest_sha256="b" * 64,
        session_manifest_sha256=None,
    )
    assert archive.latest_committed_slot_before(SESSION, "1830") is None
    assert archive.latest_committed_slot_before(SESSION, "1930") is None
    assert archive.latest_committed_slot_before(SESSION, "2030").slot == "1930"
    assert archive.later_committed_slot_after(SESSION, "1830").slot == "1930"
    assert archive.later_committed_slot_after(SESSION, "1930") is None


def test_slot_read_fails_closed_when_snapshot_is_tampered(tmp_path: Path):
    store = LocalConditionalStore(tmp_path / "cloud")
    archive = StockbitIntradayCloudArchive(store)
    commit = archive.commit_slot(
        session_date=SESSION,
        slot="1830",
        status="WAITING_RECOVERY_RETRY",
        snapshot_bytes=b"snapshot-one",
        result_payload=_result("WAITING_RECOVERY_RETRY"),
        code_identity={"commit": "a" * 40},
        eod_manifest_sha256="b" * 64,
        session_manifest_sha256=None,
    )
    path = store._path(commit.snapshot_key)
    path.write_bytes(b"tampered")
    with pytest.raises(StockbitIntradayCloudError, match="SNAPSHOT_INVALID"):
        archive.existing_slot(SESSION, "1830")


def test_policy_checkpoint_is_immutable_and_latest_known_date_wins(tmp_path: Path):
    archive = _archive(tmp_path)
    p1 = {"mode": "SHADOW", "history": [{"session_date": "2026-08-25"}]}
    p2 = {"mode": "ENFORCE", "history": [{"session_date": SESSION}]}
    archive.commit_policy_checkpoint(
        session_date="2026-08-25",
        session_manifest_sha256="1" * 64,
        policy=p1,
    )
    archive.commit_policy_checkpoint(
        session_date=SESSION,
        session_manifest_sha256="2" * 64,
        policy=p2,
    )
    latest = archive.latest_policy_checkpoint(
        ["2026-08-25", SESSION, "2026-08-27"],
        before_or_equal=SESSION,
    )
    assert latest["policy"] == p2

    replay = archive.commit_policy_checkpoint(
        session_date=SESSION,
        session_manifest_sha256="2" * 64,
        policy=p2,
    )
    assert replay["policy"] == p2

    with pytest.raises(StorageImmutabilityConflict):
        archive.commit_policy_checkpoint(
            session_date=SESSION,
            session_manifest_sha256="3" * 64,
            policy={"mode": "SHADOW", "history": []},
        )


def test_invalid_slot_fails_before_storage_access(tmp_path: Path):
    archive = _archive(tmp_path)
    with pytest.raises(StockbitIntradayCloudError, match="SLOT_INVALID"):
        archive.existing_slot(SESSION, "1845")
