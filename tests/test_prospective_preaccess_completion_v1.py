from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.prospective_evaluation_gate_v1 import validate_session_inventory
from idx_trade.prospective_preaccess_adapters_v1 import ProductionAdapterError
from idx_trade.prospective_preaccess_completion_v1 import (
    CompletionArtifactError,
    SAFE_SESSION_AUDIT_SCHEMA,
    build_admitted_inventory,
    build_local_composite_benchmark,
    build_prior_access_audit,
    gate_shape_inventory_sha256,
    project_verified_score_session,
    produce_paper_attestation_from_safe_audit,
    reconcile_runtime_counter,
    sha256_bytes,
    write_synthetic_score_session,
)


def _write_json(path: Path, payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _snapshot(path: Path, session: str, parent: tuple[Path, str] | None) -> str:
    payload = {
        "schema_version": "idx_trade_forward_dividend_runtime_state_v1_1",
        "session_date": session,
        "state": {"operational": "METADATA_ONLY"},
        "hashes": {},
    }
    if parent is not None:
        payload["previous_snapshot"] = {
            "path": str(parent[0]),
            "sha256": parent[1],
            "session_date": parent[0].stem,
        }
    body = dict(payload)
    payload["snapshot_payload_sha256"] = sha256_bytes(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return _write_json(path, payload)


def _safe_audit_fixture(tmp_path: Path, *, missed: bool = False) -> tuple[Path, list[str]]:
    root = tmp_path / "safe-audit"
    predecessor = root / "snapshots" / "2026-08-20.json"
    predecessor_sha = _snapshot(predecessor, "2026-08-20", None)
    dates = ["2026-08-21", "2026-08-24"]
    rows = []
    parent = (predecessor, predecessor_sha)
    for position, session in enumerate(dates, start=1):
        paper = root / "snapshots" / f"{session}.json"
        paper_sha = _snapshot(paper, session, parent)
        entry = {
            "session_date": session,
            "forward_position": position,
            "terminal_state": "MISSED_EXECUTION_NO_CERTIFIED_OPEN" if missed and position == 2 else "EXECUTION",
            "continuity_valid": True,
            "execution_provenance_valid": False if missed and position == 2 else True,
            "preclassified_invalidity": bool(missed and position == 2),
            "invalidity_reason": "MISSED_EXECUTION_NO_CERTIFIED_OPEN" if missed and position == 2 else "",
            "paperstate_path": str(paper),
            "paperstate_sha256": paper_sha,
        }
        if entry["terminal_state"] == "EXECUTION":
            execution = root / "terminal" / f"{session}.json"
            execution_sha = _write_json(
                execution,
                {"schema_version": "synthetic_safe_execution_v1", "status": "EXECUTION_COMPLETE", "session_date": session},
            )
            entry.update({"execution_path": str(execution), "execution_sha256": execution_sha})
        else:
            missed_path = root / "terminal" / f"{session}.json"
            missed_sha = _write_json(
                missed_path,
                {"schema_version": "idx_trade_e2e_paper_missed_execution_v1", "status": "MISSED_EXECUTION_NO_CERTIFIED_OPEN", "session_date": session},
            )
            entry.update({"missed_execution_path": str(missed_path), "missed_execution_sha256": missed_sha})
        rows.append(entry)
        parent = (paper, paper_sha)
    source = root / "session_audit.json"
    _write_json(
        source,
        {
            "schema_version": SAFE_SESSION_AUDIT_SCHEMA,
            "outcome_blind": True,
            "source_reference": "SYNTHETIC_SESSION_AUDIT_ONLY",
            "sessions": rows,
        },
    )
    return source, dates


def test_exact_gate_projection_preserves_actual_v4_x1_row_shape() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["GOTO", "BBCA"],
            "date": ["2026-08-21", "2026-08-21"],
            "raw_control_h5": [0.1, 0.2],
            "alpha_control_h5": [0.3, 0.4],
            "raw_control_h10": [0.5, 0.6],
            "alpha_control_h10": [0.7, 0.8],
            "alpha_control_consensus": [0.5, 0.6],
            "raw_challenger_h5": [0.2, 0.3],
            "alpha_h5": [0.9, 1.0],
            "raw_challenger_h10": [0.4, 0.5],
            "alpha_h10": [1.1, 1.2],
            "alpha_consensus": [0.91, 0.81],
            "rank_consensus": [1, 2],
            "rank_control_consensus": [2, 1],
        }
    )
    from idx_trade.prospective_preaccess_adapters_v1 import project_score_frame_to_gate_shape

    projected = project_score_frame_to_gate_shape(frame)
    assert list(projected.columns) == ["date", "ticker", "alpha_consensus"]
    assert projected["ticker"].tolist() == ["GOTO", "BBCA"]
    assert projected["alpha_consensus"].tolist() == [0.91, 0.81]
    assert projected["date"].tolist() == ["2026-08-21", "2026-08-21"]


def test_real_projection_is_immutable_and_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source_item = write_synthetic_score_session(source, "2026-08-21", row_count=2)
    first = project_verified_score_session(
        source_item["projected_manifest_path"],
        source_root=source,
        output_root=output,
        expected_session="2026-08-21",
    )
    second = project_verified_score_session(
        source_item["projected_manifest_path"],
        source_root=source,
        output_root=output,
        expected_session="2026-08-21",
    )
    assert first["projected_artifact_sha256"] == second["projected_artifact_sha256"]
    assert first["projected_manifest_sha256"] == second["projected_manifest_sha256"]
    payload = json.loads(Path(first["projected_manifest_path"]).read_text(encoding="utf-8"))
    assert payload["metadata"]["source_production_artifact_sha256"] == source_item[
        "projected_artifact_sha256"
    ]


def test_partial_admitted_identity_is_distinct_and_not_canonical(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    projections = [
        project_verified_score_session(
            write_synthetic_score_session(source, date)["projected_manifest_path"],
            source_root=source,
            output_root=output,
            expected_session=date,
        )
        for date in ("2026-08-21", "2026-08-24")
    ]
    inventory, manifest = build_admitted_inventory(
        projections,
        official_sessions=["2026-08-21", "2026-08-24"],
        output_root=output,
    )
    assert manifest["partial_admitted_gate_shape_sha256"]
    assert manifest["canonical_admitted_gate_inventory_sha256"] == "NOT_AVAILABLE"
    changed = inventory.copy()
    changed.loc[0, "score_manifest_sha256"] = "f" * 64
    assert gate_shape_inventory_sha256(changed) != gate_shape_inventory_sha256(inventory)


def test_counter_remains_accumulating_and_does_not_write_attestation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    projection = project_verified_score_session(
        write_synthetic_score_session(source, "2026-08-21")["projected_manifest_path"],
        source_root=source,
        output_root=output,
        expected_session="2026-08-21",
    )
    inventory, _ = build_admitted_inventory(
        [projection], official_sessions=["2026-08-21"], output_root=output
    )
    status = tmp_path / "latest.json"
    status.write_text(
        json.dumps(
            {
                "x1_counter": {
                    "completed": 1,
                    "target": 100,
                    "remaining": 99,
                    "sessions": ["2026-08-21"],
                }
            }
        ),
        encoding="utf-8",
    )
    attestation = tmp_path / "counter_attestation.json"
    result = reconcile_runtime_counter(status, inventory, attestation_path=attestation)
    assert result["status"] == "ACCUMULATING"
    assert result["runtime_counter_changed"] is False
    assert not attestation.exists()


def test_gate_rejects_projection_with_duplicate_ticker(tmp_path: Path) -> None:
    source = tmp_path / "source"
    item = write_synthetic_score_session(source, "2026-08-21", row_count=2)
    frame = pd.read_parquet(item["projected_artifact_path"])
    frame.loc[1, "ticker"] = frame.loc[0, "ticker"]
    with pytest.raises(ProductionAdapterError, match="DUPLICATE_TICKER"):
        from idx_trade.prospective_preaccess_adapters_v1 import project_score_frame_to_gate_shape

        project_score_frame_to_gate_shape(frame)


def test_safe_session_audit_consumer_builds_gate_paper_attestation(tmp_path: Path) -> None:
    source, sessions = _safe_audit_fixture(tmp_path)
    result = produce_paper_attestation_from_safe_audit(
        source,
        output_path=tmp_path / "paper_attestation.json",
        expected_sessions=sessions,
        predecessor_session_date="2026-08-20",
    )
    assert result["status"] == "READY_FOR_FINAL_GATE_REVALIDATION"
    payload = json.loads(Path(result["paper_attestation_path"]).read_text(encoding="utf-8"))
    assert payload["session_count"] == 2
    assert payload["preclassified_invalidity"] is False


def test_safe_session_audit_legitimate_missed_open_is_preclassified(tmp_path: Path) -> None:
    source, sessions = _safe_audit_fixture(tmp_path, missed=True)
    result = produce_paper_attestation_from_safe_audit(
        source,
        output_path=tmp_path / "paper_attestation.json",
        expected_sessions=sessions,
        predecessor_session_date="2026-08-20",
    )
    payload = json.loads(Path(result["paper_attestation_path"]).read_text(encoding="utf-8"))
    assert payload["preclassified_invalidity"] is True
    assert payload["execution_provenance_valid"] is False
    assert payload["missed_execution_count"] == 1


@pytest.mark.parametrize("mutation", ["parent", "duplicate", "gap", "both"])
def test_safe_session_audit_fail_closed_adversarial(tmp_path: Path, mutation: str) -> None:
    source, sessions = _safe_audit_fixture(tmp_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if mutation == "parent":
        payload["sessions"][1]["paperstate_sha256"] = "0" * 64
    elif mutation == "duplicate":
        payload["sessions"][1]["session_date"] = payload["sessions"][0]["session_date"]
    elif mutation == "gap":
        payload["sessions"][1]["forward_position"] = 3
    else:
        payload["sessions"][1]["missed_execution_path"] = payload["sessions"][0]["execution_path"]
        payload["sessions"][1]["missed_execution_sha256"] = payload["sessions"][0]["execution_sha256"]
    source.write_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    with pytest.raises(CompletionArtifactError):
        produce_paper_attestation_from_safe_audit(
            source,
            output_path=tmp_path / "paper_attestation.json",
            expected_sessions=sessions,
            predecessor_session_date="2026-08-20",
        )


def test_prior_access_requires_explicit_canonical_root(tmp_path: Path) -> None:
    result = build_prior_access_audit(None)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["reason"] == "PRIOR_ACCESS_AUDIT_NOT_AVAILABLE_CANONICAL_ROOT_UNSET"
    empty = build_prior_access_audit(tmp_path / "arbitrary-empty")
    assert empty["status"] == "NOT_AVAILABLE"


def test_local_benchmark_stays_partial_without_all_public_rows(tmp_path: Path) -> None:
    root = tmp_path / "data"
    session_dir = root / "forward_monitoring" / "sessions" / "2026-08-21"
    session_dir.mkdir(parents=True)
    pd.DataFrame(
        [{
            "session_date": "2026-08-21",
            "index_code": "COMPOSITE",
            "close": 7000.0,
            "source": "IDX",
            "source_ref": "synthetic",
            "source_sha256": "a" * 64,
            "source_retrieved_at": "2026-08-21T12:00:00+00:00",
        }]
    ).to_csv(session_dir / "idx_index_summary.csv", index=False)
    result = build_local_composite_benchmark(
        root,
        sessions=["2026-08-21"],
        predecessor_session_date="2026-08-20",
        output_root=tmp_path / "benchmark",
    )
    assert result["status"] == "PARTIAL_NOT_GATE_READY"
    assert not (tmp_path / "benchmark" / "benchmark_attestation.json").exists()
