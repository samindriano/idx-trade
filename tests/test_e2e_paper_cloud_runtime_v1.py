from __future__ import annotations

from datetime import date, datetime, timedelta
import io
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from idx_trade.e2e_paper_cloud_runtime_v1 import (
    CONTRACT_VERSION,
    INPUT_SCHEMA_VERSION,
    CloudInputBundle,
    CloudPaperArchive,
    CloudPaperRuntimeError,
    LocalConditionalStore,
    OFFICIAL_OPEN_EXECUTION_END,
    build_runtime_snapshot,
    canonical_json_bytes,
    load_schedule_from_bundle,
    materialize_official_open_from_cloud,
    restore_runtime_snapshot,
    sha256_bytes,
)
from scripts import run_e2e_paper_cloud_v1 as cloud_runner
from idx_trade.official_open_evidence_v1 import (
    AUTHORITY,
    FIELD_SEMANTICS,
    TRANSPORT_POLICY,
    UPSTREAM_PATH,
)
from idx_trade.official_open_cloud_archive_v1 import (
    EXECUTION_ADMISSION as OPEN_CLOUD_EXECUTION_ADMISSION,
    SCHEMA_VERSION as OPEN_CLOUD_SCHEMA_VERSION,
    SLOT_TIMES as OPEN_CLOUD_SLOT_TIMES,
)


def _write_schedule(tmp_path: Path) -> tuple[bytes, str]:
    source = tmp_path / "official-source.pdf"
    source.write_bytes(b"official source")
    holidays = ["2026-08-25"]
    sessions = ["2026-08-24", "2026-08-26"]
    body = {
        "schema_version": "idx_official_trading_schedule_v1",
        "authority": "IDX",
        "semantics": "PLANNED_OFFICIAL_TRADING_SCHEDULE",
        "derivation": "WEEKDAYS_MINUS_PUBLISHED_BURSA_HOLIDAYS",
        "source_reference": "official-test-source",
        "source_document_path": source.name,
        "source_document_sha256": sha256_bytes(source.read_bytes()),
        "coverage_start": "2026-08-24",
        "coverage_end": "2026-08-26",
        "holiday_dates": holidays,
        "session_dates": sessions,
    }
    payload = dict(body)
    payload["payload_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return canonical_json_bytes(payload), payload["payload_sha256"]


def _input_manifest(store: LocalConditionalStore, tmp_path: Path) -> tuple[str, dict[str, Path]]:
    schedule_bytes, _ = _write_schedule(tmp_path)
    files = [
        ("execution_schedule", "schedule.json", schedule_bytes),
        ("execution_schedule_source", "official-source.pdf", b"official source"),
        ("clean_panel", "panel.parquet", b"panel"),
        ("clean_security_master", "security_master.csv", b"ticker,listed_from,listed_to\nAAA,2020-01-01,\n"),
        ("model_manifest", "model/MANIFEST.json", b"{}"),
        ("model_control_h5", "model/v4_x1_clean_control_h5_final.joblib", b"control-h5"),
        ("model_control_h10", "model/v4_x1_clean_control_h10_final.joblib", b"control-h10"),
        ("model_challenger_h5", "model/v4_x1_clean_challenger_h5_final.joblib", b"challenger-h5"),
        ("model_challenger_h10", "model/v4_x1_clean_challenger_h10_final.joblib", b"challenger-h10"),
        ("model_fit_log", "model/v4_x1_clean_final_refit_log.json", b"[]"),
    ]
    refs = []
    roles = {}
    for role, relative, payload in files:
        key = "inputs/" + relative.replace("\\", "/")
        store.put_if_absent(key, payload, "application/octet-stream")
        refs.append(
            {
                "role": role,
                "key": key,
                "relative_path": relative,
                "sha256": sha256_bytes(payload),
                "content_type": "application/octet-stream",
            }
        )
        roles[role] = relative
    body = {
        "schema_version": INPUT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "execution_schedule_sha256": refs[0]["sha256"],
        "files": refs,
        "roles": roles,
    }
    body["manifest_payload_sha256"] = sha256_bytes(
        canonical_json_bytes({k: v for k, v in body.items() if k != "manifest_payload_sha256"})
    )
    raw = canonical_json_bytes(body)
    store.put_if_absent("inputs/manifest.json", raw, "application/json")
    manifest = CloudInputBundle.load(store, "inputs/manifest.json")
    return manifest.manifest_sha256, manifest.materialize(store, tmp_path / "materialized")


def _write_official_open_cloud_slot(
    store: LocalConditionalStore,
    *,
    session: str = "2026-08-24",
    slot: str = "0912",
    capture_at: datetime | None = None,
    commit_overrides: dict[str, object] | None = None,
    source_overrides: dict[str, object] | None = None,
    corrupt_child: str | None = None,
) -> dict[str, object]:
    raw = b"{}\n"
    open_prices = b"parquet-placeholder"
    if capture_at is None:
        capture_at = datetime.fromisoformat(f"{session}T09:13:00+07:00")
    source = {
        "session_date": session,
        "authority": AUTHORITY,
        "upstream_path": UPSTREAM_PATH,
        "field_semantics": FIELD_SEMANTICS,
        "transport": "DIRECT_IDX",
        "transport_policy": TRANSPORT_POLICY,
        "execution_grade": True,
        "raw_artifact_path": "raw_response.json",
        "normalized_artifact_path": "open_prices.parquet",
        "raw_artifact_sha256": sha256_bytes(raw),
        "normalized_artifact_sha256": sha256_bytes(open_prices),
        "capture_timestamp_jakarta": capture_at.isoformat(),
    }
    source.update(source_overrides or {})
    source_bytes = canonical_json_bytes(source)
    capture_root = f"session_date={session}/slot={slot}/captures/c1"
    artifacts: dict[str, dict[str, object]] = {}
    for name, payload in (
        ("raw_response", raw),
        ("open_prices", open_prices),
        ("source_manifest", source_bytes),
    ):
        key = f"{capture_root}/{name}.bin"
        store.put_if_absent(key, payload, "application/octet-stream")
        artifacts[name] = {"key": key, "sha256": sha256_bytes(payload)}
    if corrupt_child is not None:
        store._path(str(artifacts[corrupt_child]["key"])).write_bytes(b"corrupt")
    scheduled = datetime.combine(
        date.fromisoformat(session), OPEN_CLOUD_SLOT_TIMES[slot], tzinfo=cloud_runner.JAKARTA
    )
    commit: dict[str, object] = {
        "schema_version": OPEN_CLOUD_SCHEMA_VERSION,
        "commit_state": "COMMITTED",
        "session_date": session,
        "slot": slot,
        "capture_id": "20260824T091300Z-c1",
        "scheduled_capture_timestamp_jakarta": scheduled.isoformat(),
        "source_capture_timestamp_jakarta": capture_at.isoformat(),
        "capture_lag_seconds": (capture_at - scheduled).total_seconds(),
        "authority": AUTHORITY,
        "upstream_path": UPSTREAM_PATH,
        "field_semantics": FIELD_SEMANTICS,
        "source_transport": "DIRECT_IDX",
        "source_transport_policy": TRANSPORT_POLICY,
        "source_execution_grade": True,
        "execution_admission": OPEN_CLOUD_EXECUTION_ADMISSION,
        "artifacts": artifacts,
        "runner_provenance": {
            "runner": "GITHUB_ACTIONS",
            "github_event_name": "schedule",
        },
        "guards": {
            "model_accessed": False,
            "outcome_accessed": False,
            "paper_state_mutated": False,
            "forward_counter_mutated": False,
            "order_created": False,
            "fill_created": False,
            "retroactive_execution_authorized": False,
        },
    }
    commit.update(commit_overrides or {})
    key = f"session_date={session}/slot={slot}/slot_manifest.json"
    store.put_if_absent(key, canonical_json_bytes(commit), "application/json")
    return commit


def test_local_conditional_store_is_create_only(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    first = store.put_if_absent("a/b.bin", b"one", "application/octet-stream")
    second = store.put_if_absent("a/b.bin", b"one", "application/octet-stream")
    assert first.created is True
    assert second.created is False
    with pytest.raises(Exception):
        store.put_if_absent("a/b.bin", b"two", "application/octet-stream")


def test_input_bundle_requires_hashes_and_materializes_roles(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    manifest_sha, paths = _input_manifest(store, tmp_path)
    assert len(manifest_sha) == 64
    assert paths["execution_schedule"].is_file()
    bundle = CloudInputBundle.load(store, "inputs/manifest.json")
    schedule = load_schedule_from_bundle(bundle, paths)
    assert schedule.session_dates == ("2026-08-24", "2026-08-26")

    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    manifest["files"][1]["sha256"] = "0" * 64
    manifest["manifest_payload_sha256"] = sha256_bytes(
        canonical_json_bytes(
            {k: v for k, v in manifest.items() if k != "manifest_payload_sha256"}
        )
    )
    store.put_if_absent("bad.json", canonical_json_bytes(manifest), "application/json")
    bad = CloudInputBundle.load(store, "bad.json")
    with pytest.raises(CloudPaperRuntimeError, match="ARTIFACT_SHA_MISMATCH"):
        bad.materialize(store, tmp_path / "bad-materialized")


def test_input_bundle_requires_every_model_child_artifact(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    manifest["files"] = [
        item for item in manifest["files"] if item["role"] != "model_control_h5"
    ]
    manifest["roles"].pop("model_control_h5")
    manifest["manifest_payload_sha256"] = sha256_bytes(
        canonical_json_bytes(
            {k: v for k, v in manifest.items() if k != "manifest_payload_sha256"}
        )
    )
    store.put_if_absent("inputs/missing-model.json", canonical_json_bytes(manifest), "application/json")
    with pytest.raises(CloudPaperRuntimeError, match="REQUIRED_ROLE_MISSING"):
        CloudInputBundle.load(store, "inputs/missing-model.json")


def test_snapshot_is_deterministic_and_restore_is_fail_closed(tmp_path: Path) -> None:
    paper = tmp_path / "paper"
    forward = tmp_path / "forward"
    paper.mkdir()
    forward.mkdir()
    (paper / "state.json").write_text("state", encoding="utf-8")
    (forward / "calendar.csv").write_text("date\n2026-08-24\n", encoding="utf-8")
    roots = {"paper": paper, "forward": forward}
    first, first_sha, metadata = build_runtime_snapshot(roots)
    second, second_sha, _ = build_runtime_snapshot(roots)
    assert first == second
    assert first_sha == second_sha
    target_paper = tmp_path / "restored-paper"
    target_forward = tmp_path / "restored-forward"
    counts = restore_runtime_snapshot(
        first,
        {"paper": target_paper, "forward": target_forward},
        expected_sha256=first_sha,
    )
    assert counts == {"paper": 1, "forward": 1}
    assert (target_paper / "state.json").read_text(encoding="utf-8") == "state"
    with pytest.raises(CloudPaperRuntimeError):
        restore_runtime_snapshot(b"bad", {"paper": target_paper}, expected_sha256=first_sha)
    assert metadata["file_count"] == 2


def test_stage_commit_is_idempotent_and_replay_verifies_children(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    archive = CloudPaperArchive(store)
    snapshot, snapshot_sha, metadata = build_runtime_snapshot({"paper": tmp_path / "empty"})
    result = {
        "observed_started_at_utc": "2026-08-24T11:00:00+00:00",
        "observed_finished_at_utc": "2026-08-24T11:01:00+00:00",
        "controller_status": "POST_EOD_PREPARED",
    }
    commit = archive.commit_stage(
        session_date="2026-08-24",
        stage="POST_EOD",
        status="POST_EOD_PREPARED",
        run_id="run-1",
        snapshot_bytes=snapshot,
        snapshot_sha256=snapshot_sha,
        snapshot_metadata=metadata,
        result_payload=result,
        schedule_attestation_sha256="1" * 64,
        input_manifest_sha256="2" * 64,
        code_identity={"commit": "3" * 40},
    )
    replay = archive.existing_commit("2026-08-24", "POST_EOD")
    assert replay is not None
    assert replay.commit_sha256 == commit.commit_sha256
    result_path = store._path(replay.result_key)
    result_path.write_bytes(b"tampered")
    with pytest.raises(CloudPaperRuntimeError, match="RESULT_INVALID"):
        archive.existing_commit("2026-08-24", "POST_EOD")


def test_stage_commit_rejects_existing_schedule_or_input_identity_conflict(
    tmp_path: Path,
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    archive = CloudPaperArchive(store)
    snapshot, snapshot_sha, metadata = build_runtime_snapshot({"paper": tmp_path / "empty"})
    common = {
        "session_date": "2026-08-24",
        "stage": "POST_EOD",
        "status": "POST_EOD_PREPARED",
        "snapshot_bytes": snapshot,
        "snapshot_sha256": snapshot_sha,
        "snapshot_metadata": metadata,
        "result_payload": {
            "observed_started_at_utc": "2026-08-24T11:00:00+00:00",
            "observed_finished_at_utc": "2026-08-24T11:01:00+00:00",
        },
        "schedule_attestation_sha256": "1" * 64,
        "input_manifest_sha256": "2" * 64,
        "code_identity": {"commit": "3" * 40},
    }
    archive.commit_stage(run_id="run-1", **common)
    with pytest.raises(CloudPaperRuntimeError, match="SCHEDULE_IDENTITY_CONFLICT"):
        archive.commit_stage(
            run_id="run-2",
            **{**common, "schedule_attestation_sha256": "4" * 64},
        )
    with pytest.raises(CloudPaperRuntimeError, match="INPUT_IDENTITY_CONFLICT"):
        archive.commit_stage(
            run_id="run-3",
            **{**common, "input_manifest_sha256": "5" * 64},
        )


def test_latest_snapshot_prefers_later_post_eod_state_for_next_preopen_restore(
    tmp_path: Path,
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    archive = CloudPaperArchive(store)
    common = {
        "schedule_attestation_sha256": "1" * 64,
        "input_manifest_sha256": "2" * 64,
        "code_identity": {"commit": "3" * 40},
    }
    snapshots: dict[str, tuple[bytes, str]] = {}

    def commit_snapshot(stage: str, marker: str) -> str:
        root = tmp_path / marker
        root.mkdir()
        (root / "state.txt").write_text(marker, encoding="utf-8")
        snapshot, snapshot_sha, metadata = build_runtime_snapshot({"paper": root})
        committed = archive.commit_stage(
            session_date="2026-08-24",
            stage=stage,
            status="EXECUTION_COMPLETE" if stage == "PREOPEN" else "POST_EOD_PREPARED",
            run_id=marker,
            snapshot_bytes=snapshot,
            snapshot_sha256=snapshot_sha,
            snapshot_metadata=metadata,
            result_payload={
                "observed_started_at_utc": "2026-08-24T02:00:00+00:00",
                "observed_finished_at_utc": "2026-08-24T02:01:00+00:00",
            },
            **common,
        )
        snapshots[stage] = (snapshot, snapshot_sha)
        return committed.snapshot_sha256 or ""

    pre_sha = commit_snapshot("PREOPEN", "d0-preopen")
    post_sha = commit_snapshot("POST_EOD", "d0-post-eod")
    replay = archive.commit_stage(
        session_date="2026-08-24",
        stage="POST_EOD",
        status="POST_EOD_PREPARED",
        run_id="d0-post-eod-retry",
        snapshot_bytes=snapshots["POST_EOD"][0],
        snapshot_sha256=snapshots["POST_EOD"][1],
        snapshot_metadata={},
        result_payload={
            "observed_started_at_utc": "2026-08-24T02:00:00+00:00",
            "observed_finished_at_utc": "2026-08-24T02:01:00+00:00",
        },
        **common,
    )
    assert replay.snapshot_sha256 == post_sha
    assert post_sha != pre_sha

    # This is the D+1 PREOPEN restore point: D1 has no committed state yet,
    # so D0 POST_EOD must be the newest lifecycle state.
    restored = archive.latest_snapshot(
        ["2026-08-24", "2026-08-25"], before_or_equal="2026-08-25"
    )
    assert restored is not None
    restored_bytes, restored_sha, _ = restored
    assert restored_sha == post_sha
    with zipfile.ZipFile(io.BytesIO(restored_bytes)) as bundle:
        names = bundle.namelist()
        assert any(name.endswith("state.txt") for name in names)
        state_name = next(name for name in names if name.endswith("state.txt"))
        assert bundle.read(state_name) == b"d0-post-eod"


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("wrong_schema", "ADMISSION_INVALID:schema_version"),
        ("wrong_admission", "ADMISSION_INVALID:execution_admission"),
        ("missing_guards", "ADMISSION_GUARDS_INVALID"),
        ("source_session_mismatch", "SOURCE_MANIFEST_INVALID"),
        ("malformed_capture_timestamp", "SOURCE_CAPTURE_TIMESTAMP_INVALID"),
        ("outside_window", "OUTSIDE_PROSPECTIVE_WINDOW"),
        ("corrupt_child", "ARTIFACT_SHA_MISMATCH:open_prices"),
        ("manual_capture", "MANUAL_CAPTURE_FORBIDDEN"),
        ("future_capture", "FUTURE_CAPTURE"),
    ],
)
def test_official_open_cloud_admission_rejects_invalid_outer_or_timing_contract(
    tmp_path: Path, kind: str, expected: str
) -> None:
    store = LocalConditionalStore(tmp_path / "official")
    overrides: dict[str, object] = {}
    source_overrides: dict[str, object] = {}
    capture_at = datetime.fromisoformat("2026-08-24T09:13:00+07:00")
    now = datetime.fromisoformat("2026-08-24T09:14:00+07:00")
    corrupt_child = None
    if kind == "wrong_schema":
        overrides["schema_version"] = "wrong-schema"
    elif kind == "wrong_admission":
        overrides["execution_admission"] = "EXECUTION_ADMITTED"
    elif kind == "missing_guards":
        overrides["guards"] = {}
    elif kind == "source_session_mismatch":
        source_overrides["session_date"] = "2026-08-23"
    elif kind == "malformed_capture_timestamp":
        source_overrides["capture_timestamp_jakarta"] = "not-a-timestamp"
    elif kind == "outside_window":
        capture_at = datetime.fromisoformat("2026-08-24T09:23:00+07:00")
        overrides["slot"] = "0922"
    elif kind == "corrupt_child":
        corrupt_child = "open_prices"
    elif kind == "manual_capture":
        overrides["runner_provenance"] = {
            "runner": "GITHUB_ACTIONS",
            "github_event_name": "workflow_dispatch",
        }
    elif kind == "future_capture":
        now = datetime.fromisoformat("2026-08-24T09:12:30+07:00")

    _write_official_open_cloud_slot(
        store,
        slot=str(overrides.pop("slot", "0912")),
        capture_at=capture_at,
        commit_overrides=overrides,
        source_overrides=source_overrides,
        corrupt_child=corrupt_child,
    )
    with pytest.raises(CloudPaperRuntimeError, match=expected):
        materialize_official_open_from_cloud(
            store,
            session_date="2026-08-24",
            target_root=tmp_path / "local-open",
            eligibility_now=now,
        )


def test_old_1800_capture_is_not_execution_admissible(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "official")
    _write_official_open_cloud_slot(
        store,
        capture_at=datetime.fromisoformat("2026-08-24T18:00:00+07:00"),
    )
    with pytest.raises(CloudPaperRuntimeError, match="EXECUTION_WINDOW_CLOSED"):
        materialize_official_open_from_cloud(
            store,
            session_date="2026-08-24",
            target_root=tmp_path / "local-open",
            eligibility_now=datetime.fromisoformat("2026-08-24T18:01:00+07:00"),
        )


def test_valid_scheduled_official_open_cloud_capture_is_admitted(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "official")
    _write_official_open_cloud_slot(store)
    result = materialize_official_open_from_cloud(
        store,
        session_date="2026-08-24",
        target_root=tmp_path / "local-open",
        eligibility_now=datetime.fromisoformat("2026-08-24T09:14:00+07:00"),
    )
    assert result is not None
    assert result["execution_admitted"] is True


def test_official_open_cloud_materialization_verifies_referenced_artifacts(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "official")
    commit = _write_official_open_cloud_slot(store)
    artifacts = commit["artifacts"]
    assert isinstance(artifacts, dict)
    slot = "0912"
    result = materialize_official_open_from_cloud(
        store,
        session_date="2026-08-24",
        target_root=tmp_path / "local-open",
        eligibility_now=datetime.fromisoformat("2026-08-24T09:14:00+07:00"),
    )
    assert result is not None
    assert result["slot"] == slot
    assert (tmp_path / "local-open" / "2026-08-24" / "manifest.json").is_file()

    store._path(artifacts["open_prices"]["key"]).write_bytes(b"changed")
    with pytest.raises(CloudPaperRuntimeError, match="ARTIFACT_SHA_MISMATCH"):
        materialize_official_open_from_cloud(
            store,
            session_date="2026-08-24",
            target_root=tmp_path / "other-open",
            eligibility_now=datetime.fromisoformat("2026-08-24T09:14:00+07:00"),
        )


def test_holiday_commits_noop_without_invoking_existing_engines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_MANIFEST_KEY", "inputs/manifest.json")
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(cloud_runner, "run_clean_eod_pipeline", lambda *a, **k: (_ for _ in ()).throw(AssertionError("engine invoked")))
    monkeypatch.setattr(cloud_runner, "run_operational_cycle_v2", lambda *a, **k: (_ for _ in ()).throw(AssertionError("controller invoked")))
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 25, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )

    first = cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-25")
    second = cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-25")
    assert first["status"] == "COMMITTED"
    assert first["controller_status"] == "WEEKEND_OR_HOLIDAY_NOOP"
    assert second["status"] == "ALREADY_COMMITTED"


def test_waiting_upstream_does_not_create_terminal_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(cloud_runner, "run_clean_eod_pipeline", lambda *a, **k: None)
    monkeypatch.setattr(
        cloud_runner,
        "_controller_config",
        lambda **kwargs: SimpleNamespace(base=object()),
    )
    monkeypatch.setattr(cloud_runner, "_config_missing", lambda config: None)
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 24, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )
    monkeypatch.setattr(
        cloud_runner,
        "run_operational_cycle_v2",
        lambda *a, **k: {"controller_status": "WAITING_UPSTREAM_EOD_SCORE"},
    )

    result = cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-24")
    assert result["status"] == "WAITING"
    assert CloudPaperArchive(store).existing_commit("2026-08-24", "POST_EOD") is None


def test_open_unavailable_keeps_preopen_outcome_uncommitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setenv("E2E_CLOUD_OFFICIAL_OPEN_PREFIX", "official-open-v1")
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(cloud_runner, "build_cloud_store_from_env", lambda *a, **k: store)
    monkeypatch.setattr(cloud_runner, "materialize_official_open_from_cloud", lambda *a, **k: None)
    monkeypatch.setattr(cloud_runner, "wait_for_official_open_from_cloud", lambda *a, **k: None)
    monkeypatch.setattr(
        cloud_runner,
        "_controller_config",
        lambda **kwargs: SimpleNamespace(base=object()),
    )
    monkeypatch.setattr(cloud_runner, "_config_missing", lambda config: None)
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 24, 9, 12, tzinfo=cloud_runner.JAKARTA),
    )
    monkeypatch.setattr(
        cloud_runner,
        "run_operational_cycle_v2",
        lambda *a, **k: {"controller_status": "WAITING_OFFICIAL_OPEN"},
    )

    result = cloud_runner.run_once(phase="PREOPEN", session_date="2026-08-24")
    assert result["status"] == "WAITING"
    assert CloudPaperArchive(store).existing_commit("2026-08-24", "PREOPEN") is None


def test_runner_rejects_retroactive_explicit_session_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 26, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )
    with pytest.raises(CloudPaperRuntimeError, match="RETROACTIVE_SESSION_FORBIDDEN"):
        cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-25")


def test_runner_preflights_operational_dependencies_before_eod_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 24, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )
    monkeypatch.setattr(
        cloud_runner,
        "_controller_config",
        lambda **kwargs: SimpleNamespace(base=object()),
    )
    monkeypatch.setattr(
        cloud_runner,
        "_config_missing",
        lambda config: "MISSING_OPERATIONAL_CONFIG:provider_checkout",
    )
    monkeypatch.setattr(
        cloud_runner,
        "run_clean_eod_pipeline",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("EOD engine must not run before preflight")
        ),
    )
    with pytest.raises(CloudPaperRuntimeError, match="OPERATIONAL_PREREQUISITE"):
        cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-24")


def test_controller_failure_does_not_create_terminal_stage_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 24, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )
    monkeypatch.setattr(cloud_runner, "run_clean_eod_pipeline", lambda *a, **k: None)
    monkeypatch.setattr(
        cloud_runner,
        "_controller_config",
        lambda **kwargs: SimpleNamespace(base=object()),
    )
    monkeypatch.setattr(cloud_runner, "_config_missing", lambda config: None)
    monkeypatch.setattr(
        cloud_runner,
        "run_operational_cycle_v2",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("controller crash")),
    )
    with pytest.raises(RuntimeError, match="controller crash"):
        cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-24")
    assert CloudPaperArchive(store).existing_commit("2026-08-24", "POST_EOD") is None


def test_preopen_wait_accepts_producer_commit_after_consumer_starts(
    tmp_path: Path,
) -> None:
    current = [datetime.fromisoformat("2026-08-24T09:12:00+07:00")]
    calls = {"materialize": 0}

    def now() -> datetime:
        return current[0]

    def sleep(seconds: float) -> None:
        current[0] += timedelta(seconds=seconds)

    def materialize(*args: object, **kwargs: object) -> dict[str, object] | None:
        del args, kwargs
        calls["materialize"] += 1
        if calls["materialize"] == 1:
            return None
        return {"execution_admitted": True}

    original = cloud_runner.materialize_official_open_from_cloud
    cloud_runner.materialize_official_open_from_cloud = materialize  # type: ignore[assignment]
    try:
        result = cloud_runner.wait_for_official_open_from_cloud(
            LocalConditionalStore(tmp_path / "store"),
            session_date="2026-08-24",
            target_root=tmp_path / "open",
            now_fn=now,
            sleep_fn=sleep,
            poll_interval_seconds=5,
            max_wait_seconds=30,
        )
    finally:
        cloud_runner.materialize_official_open_from_cloud = original
    assert result == {"execution_admitted": True}
    assert calls["materialize"] == 2
    assert current[0] == datetime.fromisoformat("2026-08-24T09:12:05+07:00")


def test_preopen_final_slot_wait_accepts_commit_before_hard_deadline(
    tmp_path: Path,
) -> None:
    current = [datetime.fromisoformat("2026-08-24T09:22:55+07:00")]
    calls = {"materialize": 0}

    def now() -> datetime:
        return current[0]

    def sleep(seconds: float) -> None:
        current[0] += timedelta(seconds=seconds)

    def materialize(*args: object, **kwargs: object) -> dict[str, object] | None:
        del args, kwargs
        calls["materialize"] += 1
        return None if calls["materialize"] == 1 else {"execution_admitted": True}

    original = cloud_runner.materialize_official_open_from_cloud
    cloud_runner.materialize_official_open_from_cloud = materialize  # type: ignore[assignment]
    try:
        result = cloud_runner.wait_for_official_open_from_cloud(
            LocalConditionalStore(tmp_path / "store"),
            session_date="2026-08-24",
            target_root=tmp_path / "open",
            now_fn=now,
            sleep_fn=sleep,
            poll_interval_seconds=5,
            max_wait_seconds=30,
        )
    finally:
        cloud_runner.materialize_official_open_from_cloud = original
    assert result == {"execution_admitted": True}
    assert current[0] == datetime.fromisoformat("2026-08-24T09:22:59+07:00")


def test_preopen_wait_does_not_poll_after_hard_deadline(tmp_path: Path) -> None:
    current = [datetime.fromisoformat("2026-08-24T09:22:58+07:00")]
    calls = {"materialize": 0}

    def now() -> datetime:
        return current[0]

    def sleep(seconds: float) -> None:
        current[0] += timedelta(seconds=seconds)

    def materialize(*args: object, **kwargs: object) -> None:
        del args, kwargs
        calls["materialize"] += 1
        return None

    original = cloud_runner.materialize_official_open_from_cloud
    cloud_runner.materialize_official_open_from_cloud = materialize  # type: ignore[assignment]
    try:
        result = cloud_runner.wait_for_official_open_from_cloud(
            LocalConditionalStore(tmp_path / "store"),
            session_date="2026-08-24",
            target_root=tmp_path / "open",
            now_fn=now,
            sleep_fn=sleep,
            poll_interval_seconds=5,
            max_wait_seconds=30,
        )
    finally:
        cloud_runner.materialize_official_open_from_cloud = original
    assert result is None
    assert calls["materialize"] == 2
    assert current[0].time().isoformat() == OFFICIAL_OPEN_EXECUTION_END.isoformat()


def test_producer_commit_after_hard_deadline_is_not_consumed(tmp_path: Path) -> None:
    current = [datetime.fromisoformat("2026-08-24T09:23:00+07:00")]
    calls = {"materialize": 0}

    def now() -> datetime:
        return current[0]

    def materialize(*args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        calls["materialize"] += 1
        return {"execution_admitted": True}

    original = cloud_runner.materialize_official_open_from_cloud
    cloud_runner.materialize_official_open_from_cloud = materialize  # type: ignore[assignment]
    try:
        result = cloud_runner.wait_for_official_open_from_cloud(
            LocalConditionalStore(tmp_path / "store"),
            session_date="2026-08-24",
            target_root=tmp_path / "open",
            now_fn=now,
            sleep_fn=lambda _: None,
        )
    finally:
        cloud_runner.materialize_official_open_from_cloud = original
    assert result is None
    assert calls["materialize"] == 0


def test_preopen_wait_stops_when_producer_never_commits(tmp_path: Path) -> None:
    current = [datetime.fromisoformat("2026-08-24T09:13:00+07:00")]
    calls = {"materialize": 0}

    def now() -> datetime:
        return current[0]

    def sleep(seconds: float) -> None:
        current[0] += timedelta(seconds=seconds)

    def materialize(*args: object, **kwargs: object) -> None:
        del args, kwargs
        calls["materialize"] += 1
        return None

    original = cloud_runner.materialize_official_open_from_cloud
    cloud_runner.materialize_official_open_from_cloud = materialize  # type: ignore[assignment]
    try:
        result = cloud_runner.wait_for_official_open_from_cloud(
            LocalConditionalStore(tmp_path / "store"),
            session_date="2026-08-24",
            target_root=tmp_path / "open",
            now_fn=now,
            sleep_fn=sleep,
            poll_interval_seconds=5,
            max_wait_seconds=10,
        )
    finally:
        cloud_runner.materialize_official_open_from_cloud = original
    assert result is None
    assert calls["materialize"] == 3
    assert current[0] == datetime.fromisoformat("2026-08-24T09:13:10+07:00")
