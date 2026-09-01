from __future__ import annotations

from argparse import Namespace
from datetime import datetime
from pathlib import Path

import pytest

from idx_trade.stockbit_intraday_cloud_archive import StockbitIntradayCloudArchive
from idx_trade.stockbit_intraday_cloud_storage import LocalConditionalStore
from idx_trade.stockbit_intraday_runtime import JAKARTA
from scripts.check_stockbit_intraday_completion import (
    CompletionProbeError,
    ObjectReader,
    PREFIX,
    validate_completion,
)


SESSION = "2026-08-26"
CODE = {"commit": "a" * 40}


def _reader(root: Path, tmp_path: Path) -> ObjectReader:
    return ObjectReader(
        Namespace(local_root=str(root), storage_prefix=PREFIX, aws_exe=None),
        tmp_path / "probe-tmp",
    )


def _complete_archive(tmp_path: Path) -> tuple[Path, StockbitIntradayCloudArchive]:
    root = tmp_path / "cloud"
    archive = StockbitIntradayCloudArchive(LocalConditionalStore(root))
    claim = archive.claim_slot(
        session_date=SESSION,
        slot="1930",
        claimed_at_utc=datetime(2026, 8, 26, 19, 30, tzinfo=JAKARTA).isoformat(),
        code_identity=CODE,
        claim_id="claim-1",
    )
    archive.commit_slot(
        session_date=SESSION,
        slot="1930",
        status="ADMISSIBLE_COMPLETE",
        snapshot_bytes=b"snapshot",
        result_payload={"session_manifest_sha256": "b" * 64},
        code_identity=CODE,
        eod_manifest_sha256="c" * 64,
        session_manifest_sha256="b" * 64,
        claim_sha256=claim,
    )
    return root, archive


def test_missing_commit_is_not_complete_and_never_requests_provider_work(tmp_path: Path):
    result = validate_completion(
        _reader(tmp_path / "empty", tmp_path),
        session=SESSION,
        slot="1930",
        expected_code_ref=CODE["commit"],
    )
    assert result == {"status": "NOT_COMPLETE", "capture_complete": False, "provider_calls": 0}


def test_intermediate_archive_is_not_completion(tmp_path: Path):
    root = tmp_path / "cloud"
    archive = StockbitIntradayCloudArchive(LocalConditionalStore(root))
    archive.commit_slot(
        session_date=SESSION,
        slot="1930",
        status="WAITING_RECOVERY_RETRY",
        snapshot_bytes=b"snapshot",
        result_payload={"summary": {"complete": False}},
        code_identity=CODE,
        eod_manifest_sha256="c" * 64,
        session_manifest_sha256=None,
    )
    result = validate_completion(
        _reader(root, tmp_path),
        session=SESSION,
        slot="1930",
    )
    assert result == {"status": "NOT_COMPLETE", "capture_complete": False, "provider_calls": 0}


def test_valid_archive_is_complete_before_capture_runtime_or_provider(tmp_path: Path):
    root, _ = _complete_archive(tmp_path)
    result = validate_completion(
        _reader(root, tmp_path),
        session=SESSION,
        slot="1930",
        expected_code_ref=CODE["commit"],
    )
    assert result["status"] == "COMPLETE"
    assert result["capture_complete"] is True
    assert result["completion_grain"] == "session_recovery_objective"
    assert result["provider_calls"] == 0


def test_changed_child_bytes_block_completion_instead_of_becoming_false_green(tmp_path: Path):
    root, archive = _complete_archive(tmp_path)
    result_path = root / archive.result_key(SESSION, "1930", archive.existing_slot(SESSION, "1930").result_sha256)
    result_path.write_bytes(b"changed")
    with pytest.raises(CompletionProbeError, match="SLOT_RESULT_INVALID"):
        validate_completion(
            _reader(root, tmp_path),
            session=SESSION,
            slot="1930",
            expected_code_ref=CODE["commit"],
        )


def test_valid_completion_is_not_invalidated_by_a_later_workflow_sha(tmp_path: Path):
    root, _ = _complete_archive(tmp_path)
    result = validate_completion(
        _reader(root, tmp_path),
        session=SESSION,
        slot="1930",
        expected_code_ref="d" * 40,
    )
    assert result["status"] == "COMPLETE"
