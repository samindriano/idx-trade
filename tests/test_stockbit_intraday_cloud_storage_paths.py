from __future__ import annotations

import io
from pathlib import Path
import zipfile

import pytest

from idx_trade.stockbit_intraday_cloud_storage import (
    IntradayCloudStorageError,
    _safe_key,
    _safe_relative,
    restore_runtime_snapshot,
    sha256_bytes,
)


def test_cloud_keys_reject_segments_that_pathlib_would_normalize_away():
    assert _safe_key("sessions/2026-08-26/commit.json") == "sessions/2026-08-26/commit.json"
    assert _safe_relative("intraday/attempts", label="TEST") == "intraday/attempts"
    for value in (
        "sessions/./commit.json",
        "sessions//commit.json",
        "sessions/../commit.json",
        "/sessions/commit.json",
        "sessions/commit.json/",
    ):
        with pytest.raises(IntradayCloudStorageError):
            _safe_key(value)
        with pytest.raises(IntradayCloudStorageError):
            _safe_relative(value, label="TEST")


def test_snapshot_restore_rejects_noncanonical_zip_entry_before_write(tmp_path: Path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("intraday/./status.json", b"{}\n")
    payload = buffer.getvalue()
    with pytest.raises(IntradayCloudStorageError, match="SNAPSHOT_ENTRY_PATH_INVALID"):
        restore_runtime_snapshot(
            payload,
            {"intraday": tmp_path / "restore"},
            expected_sha256=sha256_bytes(payload),
        )
    assert not (tmp_path / "restore" / "status.json").exists()
