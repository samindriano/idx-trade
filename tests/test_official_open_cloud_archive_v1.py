from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from idx_trade.official_open_cloud_archive_v1 import (
    EXECUTION_ADMISSION,
    OfficialOpenCloudArchiveError,
    build_official_open_store_from_env,
    capture_and_archive_official_open,
)
from idx_trade.official_open_evidence_v1 import (
    AUTHORITY,
    DIRECT_TRANSPORT,
    FIELD_SEMANTICS,
    TRANSPORT_POLICY,
    UPSTREAM_PATH,
)
from idx_trade.stockbit_stream_archive import LocalImmutableStore


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fake_capture_factory(*, bad_raw_sha: bool = False):
    calls = {"count": 0}

    def capture(session_date: str, *, output_root: Path, **_: object) -> Path:
        calls["count"] += 1
        folder = Path(output_root) / "official_open" / session_date
        folder.mkdir(parents=True)
        raw = b'{"data": []}\n'
        normalized = b"PARQUET-WITNESS"
        raw_path = folder / "raw_response.json"
        normalized_path = folder / "open_prices.parquet"
        raw_path.write_bytes(raw)
        normalized_path.write_bytes(normalized)
        manifest = {
            "schema_version": "idx_official_open_evidence_v1_1",
            "session_date": session_date,
            "authority": AUTHORITY,
            "upstream_path": UPSTREAM_PATH,
            "transport": DIRECT_TRANSPORT,
            "transport_policy": TRANSPORT_POLICY,
            "field_semantics": FIELD_SEMANTICS,
            "raw_artifact_path": raw_path.name,
            "raw_artifact_sha256": "0" * 64 if bad_raw_sha else _sha(raw),
            "normalized_artifact_path": normalized_path.name,
            "normalized_artifact_sha256": _sha(normalized),
            "capture_timestamp_jakarta": "2026-08-26T09:03:30+07:00",
            "execution_grade": True,
        }
        manifest_path = folder / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True), encoding="utf-8"
        )
        return manifest_path

    return calls, capture


def test_capture_archives_bundle_and_commits_slot_last(tmp_path: Path) -> None:
    store = LocalImmutableStore(tmp_path / "store")
    calls, capture = _fake_capture_factory()

    result = capture_and_archive_official_open(
        session_date="2026-08-26",
        slot="0902",
        store=store,
        zapi_api_key=None,
        capture_fn=capture,
        runner_provenance={"github_sha": "abc123"},
    )

    assert result["status"] == "CAPTURED"
    assert result["capture_lag_seconds"] == 90.0
    assert result["execution_admission"] == EXECUTION_ADMISSION
    assert calls["count"] == 1

    commit_key = "session_date=2026-08-26/slot=0902/slot_manifest.json"
    committed = json.loads((store.read(commit_key) or b"{}").decode("utf-8"))
    assert committed["commit_state"] == "COMMITTED"
    assert committed["source_transport"] == DIRECT_TRANSPORT
    assert committed["execution_admission"] == EXECUTION_ADMISSION
    assert committed["runner_provenance"]["github_sha"] == "abc123"
    assert committed["guards"] == {
        "model_accessed": False,
        "outcome_accessed": False,
        "paper_state_mutated": False,
        "forward_counter_mutated": False,
        "order_created": False,
        "fill_created": False,
        "retroactive_execution_authorized": False,
    }
    for artifact in committed["artifacts"].values():
        payload = store.read(artifact["key"])
        assert payload is not None
        assert _sha(payload) == artifact["sha256"]


def test_existing_commit_prevents_second_provider_call(tmp_path: Path) -> None:
    store = LocalImmutableStore(tmp_path / "store")
    calls, capture = _fake_capture_factory()
    first = capture_and_archive_official_open(
        session_date="2026-08-26",
        slot="0912",
        store=store,
        zapi_api_key=None,
        capture_fn=capture,
    )
    assert first["status"] == "CAPTURED"

    def should_not_run(*args: object, **kwargs: object) -> Path:
        raise AssertionError("provider capture must not run after a committed slot")

    second = capture_and_archive_official_open(
        session_date="2026-08-26",
        slot="0912",
        store=store,
        zapi_api_key=None,
        capture_fn=should_not_run,
    )
    assert second["status"] == "ALREADY_CAPTURED"
    assert second["capture_id"] == first["capture_id"]
    assert calls["count"] == 1


def test_source_hash_mismatch_fails_before_commit(tmp_path: Path) -> None:
    store = LocalImmutableStore(tmp_path / "store")
    _, capture = _fake_capture_factory(bad_raw_sha=True)

    with pytest.raises(
        OfficialOpenCloudArchiveError,
        match="OFFICIAL_OPEN_SOURCE_RAW_SHA_MISMATCH",
    ):
        capture_and_archive_official_open(
            session_date="2026-08-26",
            slot="0922",
            store=store,
            zapi_api_key=None,
            capture_fn=capture,
        )

    assert store.read("session_date=2026-08-26/slot=0922/slot_manifest.json") is None


def test_invalid_slot_fails_closed_before_provider_call(tmp_path: Path) -> None:
    store = LocalImmutableStore(tmp_path / "store")
    calls, capture = _fake_capture_factory()
    with pytest.raises(OfficialOpenCloudArchiveError, match="SLOT_INVALID"):
        capture_and_archive_official_open(
            session_date="2026-08-26",
            slot="0905",
            store=store,
            zapi_api_key=None,
            capture_fn=capture,
        )
    assert calls["count"] == 0


def test_local_store_env_is_dedicated_to_official_open(tmp_path: Path) -> None:
    store = build_official_open_store_from_env(
        {
            "OFFICIAL_OPEN_STORAGE_BACKEND": "local",
            "OFFICIAL_OPEN_LOCAL_ROOT": str(tmp_path / "official-open"),
        }
    )
    assert isinstance(store, LocalImmutableStore)
