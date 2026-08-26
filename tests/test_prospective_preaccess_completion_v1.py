from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.prospective_preaccess_completion_v1 import (
    CANONICAL_REAL_ACCESS_ROOT_ID,
    SAFE_SESSION_AUDIT_SCHEMA,
    CompletionArtifactError,
    _atomic_immutable_bytes,
    _atomic_json,
    assert_isolated_staging_root,
    build_admitted_inventory,
    build_local_composite_benchmark,
    build_prior_access_audit,
    finalize_canonical_admitted_inventory,
    project_verified_score_session,
    produce_paper_attestation_from_safe_audit,
    reconcile_runtime_counter,
    sha256_bytes,
    write_synthetic_score_session,
)


def _snapshot(path: Path, session: str, parent: tuple[Path, str, str]) -> str:
    parent_path, parent_sha, parent_session = parent
    payload = {
        "schema_version": "idx_trade_forward_dividend_runtime_state_v1_1",
        "session_date": session,
        "state": {"operational_metadata_only": True},
        "hashes": {},
        "previous_snapshot": {
            "path": str(parent_path.resolve()),
            "sha256": parent_sha,
            "session_date": parent_session,
        },
    }
    payload["snapshot_payload_sha256"] = sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    return _atomic_json(path, payload)


def _safe_bridge_fixture(tmp_path: Path, *, missed: bool = False) -> tuple[Path, list[str], str]:
    root = tmp_path / "paper-evidence"
    predecessor_session = "2026-08-20"
    predecessor = root / "paperstate" / f"{predecessor_session}.json"
    predecessor_sha = _atomic_json(
        predecessor,
        {
            "schema_version": "idx_trade_forward_dividend_runtime_state_v1_1",
            "session_date": predecessor_session,
            "state": {},
            "hashes": {},
            "previous_snapshot": None,
            "snapshot_payload_sha256": "unused-predecessor-body",
        },
    )
    dates = ["2026-08-21", "2026-08-24"]
    refs = []
    parent = (predecessor, predecessor_sha, predecessor_session)
    for position, session in enumerate(dates, start=1):
        paper = root / "paperstate" / f"{session}.json"
        paper_sha = _snapshot(paper, session, parent)
        is_missed = bool(missed and position == 2)
        if is_missed:
            terminal = root / "missed" / f"{session}.json"
            terminal_sha = _atomic_json(
                terminal,
                {
                    "schema_version": "idx_trade_e2e_paper_missed_execution_v1",
                    "status": "MISSED_EXECUTION_NO_CERTIFIED_OPEN",
                    "execution_session_date": session,
                    "prior_runtime_snapshot_path": str(parent[0].resolve()),
                    "prior_runtime_snapshot_sha256": parent[1],
                    "runtime_snapshot_path": str(paper.resolve()),
                    "runtime_snapshot_sha256": paper_sha,
                },
            )
            execution_stage = {
                "stage": "paper_execution",
                "status": "LEGITIMATE_NOOP",
                "artifact_path": str(terminal.resolve()),
                "artifact_sha256": terminal_sha,
                "observed": {"continuity_transition": "MISSED_EXECUTION_NO_CERTIFIED_OPEN"},
            }
            open_stage = {"stage": "official_open_evidence", "status": "PENDING_EXPECTED", "observed": {}}
            overall = "SESSION_MISSED_EXECUTION_NO_CERTIFIED_OPEN"
        else:
            terminal = root / "execution" / f"{session}.json"
            terminal_sha = _atomic_json(
                terminal,
                {
                    "schema_version": "idx_trade_e2e_paper_execution_v1",
                    "status": "EXECUTION_COMPLETE",
                    "execution_session_date": session,
                    "runtime_snapshot_path": str(paper.resolve()),
                    "runtime_snapshot_sha256": paper_sha,
                },
            )
            execution_stage = {
                "stage": "paper_execution",
                "status": "PASS",
                "artifact_path": str(terminal.resolve()),
                "artifact_sha256": terminal_sha,
                "observed": {},
            }
            open_stage = {"stage": "official_open_evidence", "status": "PASS", "observed": {}}
            overall = "SESSION_HEALTHY"
        ledger = root / "audit" / f"{session}.json"
        ledger_sha = _atomic_json(
            ledger,
            {
                "schema": "idx_trade_forward_session_audit_v1",
                "ledger_anchor": "execution_session_date",
                "session_date": session,
                "execution_session_date": session,
                "overall_status": overall,
                "stages": [
                    open_stage,
                    execution_stage,
                    {
                        "stage": "paperstate_continuity",
                        "status": "PASS",
                        "artifact_path": str(paper.resolve()),
                        "artifact_sha256": paper_sha,
                        "observed": {},
                    },
                ],
                "guards": {
                    "protected_outcomes_accessed": False,
                    "real_protected_loader_called": False,
                    "real_outcome_access_marker_written": False,
                    "provider_capture_triggered": False,
                    "model_changed": False,
                    "forward_counter_changed": False,
                },
            },
        )
        refs.append(
            {
                "session_date": session,
                "forward_position": position,
                "audit_path": str(ledger.resolve()),
                "audit_sha256": ledger_sha,
            }
        )
        parent = (paper, paper_sha, session)
    bridge = root / "safe_bridge.json"
    _atomic_json(
        bridge,
        {
            "schema_version": SAFE_SESSION_AUDIT_SCHEMA,
            "outcome_blind": True,
            "predecessor_session_date": predecessor_session,
            "predecessor_paperstate_path": str(predecessor.resolve()),
            "predecessor_paperstate_sha256": predecessor_sha,
            "session_ledgers": refs,
        },
    )
    return bridge, dates, predecessor_session


def test_immutable_writer_equal_race_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "artifact.bin"
    payload = b"same"

    def race_link(_src: Path, dst: Path) -> None:
        Path(dst).write_bytes(payload)
        raise FileExistsError

    monkeypatch.setattr("idx_trade.prospective_preaccess_completion_v1.os.link", race_link)
    assert _atomic_immutable_bytes(destination, payload) == hashlib.sha256(payload).hexdigest()
    assert destination.read_bytes() == payload


def test_immutable_writer_conflicting_race_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "artifact.bin"

    def race_link(_src: Path, dst: Path) -> None:
        Path(dst).write_bytes(b"other")
        raise FileExistsError

    monkeypatch.setattr("idx_trade.prospective_preaccess_completion_v1.os.link", race_link)
    with pytest.raises(CompletionArtifactError, match="IMMUTABLE_ARTIFACT_CONFLICT"):
        _atomic_immutable_bytes(destination, b"wanted")
    assert destination.read_bytes() == b"other"


def test_staging_root_rejects_source_or_repo_overlap(tmp_path: Path) -> None:
    source = tmp_path / "data" / "model_runs"
    output = source / "derived"
    with pytest.raises(CompletionArtifactError, match="OVERLAPS_SOURCE_ROOT"):
        assert_isolated_staging_root(output, source_roots=(source,))
    with pytest.raises(CompletionArtifactError, match="OVERLAPS_FORBIDDEN_ROOT"):
        assert_isolated_staging_root(tmp_path / "repo" / "stage", forbidden_roots=(tmp_path / "repo",))


def test_projection_validates_before_publish_on_bad_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "stage"
    item = write_synthetic_score_session(source, "2026-08-21", production_shape=True)
    manifest = Path(item["projected_manifest_path"])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["model_fingerprint"] = "bad"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CompletionArtifactError):
        project_verified_score_session(
            manifest,
            source_root=source,
            output_root=output,
            expected_session="2026-08-21",
        )
    assert not (output / "projected_scores" / "2026-08-21" / "score_artifact.parquet").exists()
    assert not (output / "projected_scores" / "2026-08-21" / "manifest.json").exists()


def test_real_projection_preserves_production_shape_values_and_is_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "stage"
    item = write_synthetic_score_session(source, "2026-08-21", row_count=4, production_shape=True)
    first = project_verified_score_session(
        item["projected_manifest_path"], source_root=source, output_root=output, expected_session="2026-08-21"
    )
    second = project_verified_score_session(
        item["projected_manifest_path"], source_root=source, output_root=output, expected_session="2026-08-21"
    )
    assert first["projected_artifact_sha256"] == second["projected_artifact_sha256"]
    assert first["projected_manifest_sha256"] == second["projected_manifest_sha256"]
    projected = pd.read_parquet(first["projected_artifact_path"])
    assert list(projected.columns) == ["date", "ticker", "alpha_consensus"]


def _hundred_projection_refs(tmp_path: Path) -> tuple[list[dict], list[str], Path]:
    root = tmp_path / "staging"
    dates = [value.date().isoformat() for value in pd.bdate_range("2026-01-02", periods=100)]
    refs = [write_synthetic_score_session(root, date, row_count=2, session_index=i) for i, date in enumerate(dates, 1)]
    return refs, dates, root


def test_100_rows_are_not_canonical_until_frozen_finalizer(tmp_path: Path) -> None:
    refs, dates, root = _hundred_projection_refs(tmp_path)
    inventory, partial = build_admitted_inventory(refs, official_sessions=dates, output_root=root)
    assert partial["canonical_admitted_gate_inventory_sha256"] == "NOT_AVAILABLE"
    canonical = finalize_canonical_admitted_inventory(inventory, output_root=root)
    assert len(canonical["canonical_admitted_gate_inventory_sha256"]) == 64
    assert canonical["status"] == "CANONICAL_ADMITTED_100_OF_100"


def test_child_drift_blocks_canonical_inventory(tmp_path: Path) -> None:
    refs, dates, root = _hundred_projection_refs(tmp_path)
    inventory, _ = build_admitted_inventory(refs, official_sessions=dates, output_root=root)
    Path(inventory.iloc[0]["score_artifact_path"]).write_bytes(b"tampered")
    with pytest.raises(Exception):
        finalize_canonical_admitted_inventory(inventory, output_root=root)
    assert not (root / "canonical_admitted_inventory_manifest.json").exists()


def test_counter_requires_target_100_and_finalized_identity(tmp_path: Path) -> None:
    refs, dates, root = _hundred_projection_refs(tmp_path)
    inventory, _ = build_admitted_inventory(refs, official_sessions=dates, output_root=root)
    status = tmp_path / "counter.json"
    status.write_text(json.dumps({"x1_counter": {"completed": 100, "target": 100, "remaining": 0, "sessions": dates}}))
    pending = reconcile_runtime_counter(status, inventory, attestation_path=tmp_path / "counter_attestation.json")
    assert pending["status"] == "PENDING_CANONICAL_INVENTORY"
    assert not (tmp_path / "counter_attestation.json").exists()
    canonical = finalize_canonical_admitted_inventory(inventory, output_root=root)
    ready = reconcile_runtime_counter(
        status,
        inventory,
        canonical_inventory=canonical,
        attestation_path=tmp_path / "counter_attestation.json",
    )
    assert ready["status"] == "ATTESTED"


def test_counter_target_99_is_rejected(tmp_path: Path) -> None:
    frame = pd.DataFrame({"session_date": ["2026-08-21"]})
    status = tmp_path / "counter.json"
    status.write_text(json.dumps({"x1_counter": {"completed": 1, "target": 99, "remaining": 98, "sessions": ["2026-08-21"]}}))
    with pytest.raises(CompletionArtifactError, match="COUNTER_TARGET_NOT_100"):
        reconcile_runtime_counter(status, frame)


def test_prior_access_clean_explicit_root_is_ready(tmp_path: Path) -> None:
    root = tmp_path / "canonical-real-root"
    root.mkdir()
    result = build_prior_access_audit(
        root,
        output_path=tmp_path / "audit.json",
        canonical_root_id=CANONICAL_REAL_ACCESS_ROOT_ID,
    )
    assert result["status"] == "READY"
    assert result["review_complete"] is True
    assert result["prior_access_marker_exists"] is False


def test_prior_access_arbitrary_empty_root_is_not_certified(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    result = build_prior_access_audit(root, output_path=tmp_path / "audit.json")
    assert result["status"] == "NOT_AVAILABLE"


def test_prior_access_synthetic_state_is_invalid_for_real_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "canonical-real-root"
    root.mkdir()
    monkeypatch.setattr(
        "idx_trade.prospective_preaccess_completion_v1.inspect_persisted_access_status",
        lambda _root: {"status": "SYNTHETIC_REHEARSAL_COMPLETE", "protected_outcomes_accessed": False},
    )
    result = build_prior_access_audit(
        root,
        output_path=tmp_path / "audit.json",
        canonical_root_id=CANONICAL_REAL_ACCESS_ROOT_ID,
    )
    assert result["status"] == "PROVENANCE_INVALID"


def test_paper_attestation_is_bound_to_actual_session_audit_ledgers(tmp_path: Path) -> None:
    bridge, dates, predecessor = _safe_bridge_fixture(tmp_path)
    result = produce_paper_attestation_from_safe_audit(
        bridge,
        output_path=tmp_path / "paper.json",
        expected_sessions=dates,
        predecessor_session_date=predecessor,
        evidence_root=tmp_path / "paper-evidence",
    )
    assert result["status"] == "READY_FOR_FINAL_GATE_REVALIDATION"
    payload = json.loads(Path(result["paper_attestation_path"]).read_text(encoding="utf-8"))
    assert payload["execution_provenance_valid"] is True


def test_paper_exact_predecessor_mismatch_is_rejected(tmp_path: Path) -> None:
    bridge, dates, predecessor = _safe_bridge_fixture(tmp_path)
    payload = json.loads(bridge.read_text(encoding="utf-8"))
    payload["predecessor_session_date"] = "2026-08-19"
    bridge.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CompletionArtifactError, match="PREDECESSOR_DATE_MISMATCH"):
        produce_paper_attestation_from_safe_audit(
            bridge,
            output_path=tmp_path / "paper.json",
            expected_sessions=dates,
            predecessor_session_date=predecessor,
            evidence_root=tmp_path / "paper-evidence",
        )


def test_paper_execution_snapshot_cross_binding_is_enforced(tmp_path: Path) -> None:
    bridge, dates, predecessor = _safe_bridge_fixture(tmp_path)
    bridge_payload = json.loads(bridge.read_text(encoding="utf-8"))
    first_ledger = Path(bridge_payload["session_ledgers"][0]["audit_path"])
    ledger = json.loads(first_ledger.read_text(encoding="utf-8"))
    execution_stage = next(item for item in ledger["stages"] if item["stage"] == "paper_execution")
    execution = Path(execution_stage["artifact_path"])
    terminal = json.loads(execution.read_text(encoding="utf-8"))
    terminal["runtime_snapshot_sha256"] = "0" * 64
    execution.write_text(json.dumps(terminal, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    execution_stage["artifact_sha256"] = hashlib.sha256(execution.read_bytes()).hexdigest()
    first_ledger.write_text(json.dumps(ledger, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    bridge_payload["session_ledgers"][0]["audit_sha256"] = hashlib.sha256(first_ledger.read_bytes()).hexdigest()
    bridge.write_text(json.dumps(bridge_payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    with pytest.raises(CompletionArtifactError, match="EXECUTION_PAPERSTATE_MISMATCH"):
        produce_paper_attestation_from_safe_audit(
            bridge,
            output_path=tmp_path / "paper.json",
            expected_sessions=dates,
            predecessor_session_date=predecessor,
            evidence_root=tmp_path / "paper-evidence",
        )


def test_legitimate_missed_open_remains_preclassified(tmp_path: Path) -> None:
    bridge, dates, predecessor = _safe_bridge_fixture(tmp_path, missed=True)
    result = produce_paper_attestation_from_safe_audit(
        bridge,
        output_path=tmp_path / "paper.json",
        expected_sessions=dates,
        predecessor_session_date=predecessor,
        evidence_root=tmp_path / "paper-evidence",
    )
    payload = json.loads(Path(result["paper_attestation_path"]).read_text(encoding="utf-8"))
    assert payload["preclassified_invalidity"] is True
    assert payload["execution_provenance_valid"] is False
    assert payload["invalidity_reason"] == "MISSED_EXECUTION_NO_CERTIFIED_OPEN"


def _write_index(root: Path, session: str, *, source: str = "IDX_SYNTHETIC") -> None:
    destination = root / "forward_monitoring" / "sessions" / session / "idx_index_summary.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{
            "session_date": session,
            "index_code": "COMPOSITE",
            "close": 7000.0,
            "source": source,
            "source_ref": "synthetic",
            "source_sha256": "a" * 64,
            "source_retrieved_at": f"{session}T16:00:00+07:00",
        }]
    ).to_csv(destination, index=False)


def test_benchmark_uses_exact_predecessor_plus_admitted_boundary(tmp_path: Path) -> None:
    data = tmp_path / "data"
    for session in ("2026-08-20", "2026-08-21", "2026-08-24"):
        _write_index(data, session)
    result = build_local_composite_benchmark(
        data,
        sessions=["2026-08-21", "2026-08-24"],
        predecessor_session_date="2026-08-20",
        output_root=tmp_path / "benchmark",
    )
    assert result["status"] == "PARTIAL_BOUNDARY_COMPLETE_NOT_FINAL"
    assert result["missing_boundary_dates"] == []
    assert result["required_boundary_dates"] == ["2026-08-20", "2026-08-21", "2026-08-24"]
    assert not (tmp_path / "benchmark" / "benchmark_attestation.json").exists()


def test_benchmark_missing_predecessor_is_not_gate_ready(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _write_index(data, "2026-08-21")
    result = build_local_composite_benchmark(
        data,
        sessions=["2026-08-21"],
        predecessor_session_date="2026-08-20",
        output_root=tmp_path / "benchmark",
    )
    assert result["status"] == "PARTIAL_NOT_GATE_READY"
    assert result["missing_boundary_dates"] == ["2026-08-20"]


def test_full_producer_path_synthetic_rehearsal(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "run_v4_x1_preaccess_completion.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--synthetic-rehearsal", "--repo-root", str(repo), "--output-dir", str(tmp_path / "rehearsal")],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert result["status"] == "PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT"
    assert result["session_count"] == 100
    assert result["protected_outcome_accessed"] is False
    assert result["real_protected_loader_called"] is False
    assert result["runtime_counter_changed"] is False
