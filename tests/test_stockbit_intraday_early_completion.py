from __future__ import annotations

from argparse import Namespace
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

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


def _complete_archive(tmp_path: Path, slot: str = "1930") -> tuple[Path, StockbitIntradayCloudArchive]:
    root = tmp_path / "cloud"
    archive = StockbitIntradayCloudArchive(LocalConditionalStore(root))
    claim = archive.claim_slot(
        session_date=SESSION,
        slot=slot,
        claimed_at_utc=datetime(2026, 8, 26, 19, 30, tzinfo=JAKARTA).isoformat(),
        code_identity=CODE,
        claim_id="claim-1",
    )
    archive.commit_slot(
        session_date=SESSION,
        slot=slot,
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


def test_clean_preflight_imports_without_provider_dependencies(tmp_path: Path):
    """The same-job gate must run before package/provider bootstrap on a clean runner."""

    guard = tmp_path / "import-guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        """import builtins

_real_import = builtins.__import__
_blocked = {\"boto3\", \"requests\"}

def _guarded_import(name, *args, **kwargs):
    if name.split(\".\", 1)[0] in _blocked:
        raise AssertionError(f\"unexpected third-party import during completion preflight: {name}\")
    return _real_import(name, *args, **kwargs)

builtins.__import__ = _guarded_import
""",
        encoding="utf-8",
    )
    empty_root = tmp_path / "empty"
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_stockbit_intraday_completion.py"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(guard), str(script.parents[1] / "src")]
    )
    completed = subprocess.run(
        [sys.executable, str(script), "--slot", "1930", "--local-root", str(empty_root)],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout) == {
        "status": "NOT_COMPLETE",
        "capture_complete": False,
        "provider_calls": 0,
    }


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


@pytest.mark.parametrize("requested_slot", ["1930", "2030"])
def test_earlier_admissible_complete_slot_completes_later_recovery_objective(tmp_path: Path, requested_slot: str):
    root, _ = _complete_archive(tmp_path, slot="1830")
    result = validate_completion(
        _reader(root, tmp_path),
        session=SESSION,
        slot=requested_slot,
    )
    assert result["status"] == "COMPLETE"
    assert result["capture_complete"] is True
    assert result["requested_slot"] == requested_slot
    assert result["completion_slot"] == "1830"


def test_earlier_waiting_commit_does_not_suppress_later_recovery(tmp_path: Path):
    root = tmp_path / "cloud"
    archive = StockbitIntradayCloudArchive(LocalConditionalStore(root))
    archive.commit_slot(
        session_date=SESSION,
        slot="1830",
        status="WAITING_RECOVERY_RETRY",
        snapshot_bytes=b"waiting",
        result_payload={"summary": {"complete": False}},
        code_identity=CODE,
        eod_manifest_sha256="c" * 64,
        session_manifest_sha256=None,
    )
    result = validate_completion(_reader(root, tmp_path), session=SESSION, slot="1930")
    assert result == {"status": "NOT_COMPLETE", "capture_complete": False, "provider_calls": 0}


def test_malformed_earlier_completion_fails_closed(tmp_path: Path):
    root, archive = _complete_archive(tmp_path, slot="1830")
    commit = archive.existing_slot(SESSION, "1830")
    assert commit is not None
    (root / archive.result_key(SESSION, "1830", commit.result_sha256)).write_bytes(b"tampered")
    with pytest.raises(CompletionProbeError, match="SLOT_RESULT_INVALID"):
        validate_completion(_reader(root, tmp_path), session=SESSION, slot="1930")


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
