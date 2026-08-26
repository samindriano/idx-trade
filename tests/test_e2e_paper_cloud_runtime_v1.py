from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from idx_trade.e2e_paper_cloud_runtime_v1 import (
    CONTRACT_VERSION,
    INPUT_SCHEMA_VERSION,
    CloudInputBundle,
    CloudPaperArchive,
    CloudPaperRuntimeError,
    LocalConditionalStore,
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


def test_official_open_cloud_materialization_verifies_referenced_artifacts(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "official")
    raw = b"{}\n"
    open_prices = b"parquet-placeholder"
    source_manifest = canonical_json_bytes(
        {
            "session_date": "2026-08-24",
            "authority": AUTHORITY,
            "upstream_path": UPSTREAM_PATH,
            "field_semantics": FIELD_SEMANTICS,
            "transport_policy": TRANSPORT_POLICY,
            "execution_grade": True,
            "raw_artifact_path": "raw_response.json",
            "normalized_artifact_path": "open_prices.parquet",
            "raw_artifact_sha256": sha256_bytes(raw),
            "normalized_artifact_sha256": sha256_bytes(open_prices),
            "capture_timestamp_jakarta": "2026-08-24T18:00:00+07:00",
        }
    )
    artifacts = {}
    slot = "0912"
    for name, payload in (
        ("raw_response", raw),
        ("open_prices", open_prices),
        ("source_manifest", source_manifest),
    ):
        key = f"session_date=2026-08-24/slot={slot}/captures/c1/{name}.bin"
        store.put_if_absent(key, payload, "application/octet-stream")
        artifacts[name] = {"key": key, "sha256": sha256_bytes(payload)}
    commit = {
        "commit_state": "COMMITTED",
        "session_date": "2026-08-24",
        "slot": slot,
        "artifacts": artifacts,
    }
    store.put_if_absent(
        f"session_date=2026-08-24/slot={slot}/slot_manifest.json",
        canonical_json_bytes(commit),
        "application/json",
    )
    result = materialize_official_open_from_cloud(
        store, session_date="2026-08-24", target_root=tmp_path / "local-open"
    )
    assert result is not None
    assert result["slot"] == slot
    assert (tmp_path / "local-open" / "2026-08-24" / "manifest.json").is_file()

    store._path(artifacts["open_prices"]["key"]).write_bytes(b"changed")
    with pytest.raises(CloudPaperRuntimeError, match="ARTIFACT_SHA_MISMATCH"):
        materialize_official_open_from_cloud(
            store, session_date="2026-08-24", target_root=tmp_path / "other-open"
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
