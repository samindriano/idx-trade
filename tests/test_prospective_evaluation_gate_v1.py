from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from idx_trade.prospective_evaluation_gate_v1 import (
    EVALUATOR_IMPLEMENTATION_COMMIT,
    FAILURE_FILENAME,
    FINAL_MANIFEST_FILENAME,
    MARKER_FILENAME,
    MODE_PROTECTED_PROSPECTIVE,
    MODE_SYNTHETIC_REHEARSAL,
    PREACCESS_FILENAME,
    PROTOCOL_GIT_BLOB_SHA1,
    REHEARSAL_ACCESS_MARKER,
    RESULT_FILENAME,
    ProtectedEvaluationBundle,
    ProspectiveAccessGateBlocked,
    _validate_paper,
    _write_json_exclusive,
    git_blob_sha1_file,
    run_protected_evaluation_once,
    validate_session_inventory,
)
from idx_trade.prospective_evaluation_v1 import MODEL_FINGERPRINT, MODEL_GENERATION, MODEL_NAME
from idx_trade.provenance import sha256_file


PROTOCOL_PATH = Path("docs/checkpoints/2026-08-24_V4_X1_PROSPECTIVE_EVALUATION_PROTOCOL_V1.md")
EVALUATOR_PATH = Path("src/idx_trade/prospective_evaluation_v1.py")


def _write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha256_file(path)


def _fixture(tmp_path: Path, *, paper_valid: bool = True, benchmark_status: str = "PINNED") -> dict:
    root = tmp_path / "fixture"
    root.mkdir(parents=True)
    score_root = root / "scores"
    score_root.mkdir()
    dates = pd.bdate_range("2026-01-05", periods=100)
    indices = np.arange(5000, 5100, dtype=int)
    inventory_rows = []
    target_rows = []

    for position, (date, session_index) in enumerate(zip(dates, indices, strict=True), start=1):
        score_path = score_root / f"score_{position:03d}.csv"
        score = pd.DataFrame(
            {
                "date": [date.date().isoformat()] * 3,
                "ticker": ["AAA", "BBB", "CCC"],
                "alpha_consensus": [0.9, 0.6, 0.2],
            }
        )
        score.to_csv(score_path, index=False)
        score_sha = sha256_file(score_path)
        manifest_path = score_root / f"manifest_{position:03d}.json"
        manifest_sha = _write_json(
            manifest_path,
            {
                "schema_version": "v4_x1_prospective_score_manifest_v2",
                "model_id": MODEL_NAME,
                "generation": MODEL_GENERATION,
                "model_fingerprint": MODEL_FINGERPRINT,
                "ranking": "alpha_consensus DESC, ticker ASC",
                "session_date": date.date().isoformat(),
                "status": "DONE",
                "output": {
                    "artifact_path": str(score_path.resolve()),
                    "artifact_sha256": score_sha,
                    "columns": list(score.columns),
                },
                "guards": {
                    "provider_calls": False,
                    "protected_outcome_accessed": False,
                    "realized_forward_outcome_loaded": False,
                    "historical_prediction_generated": False,
                    "model_refit": False,
                    "model_retuned": False,
                    "science_changed": False,
                },
            },
        )
        inventory_rows.append(
            {
                "forward_position": position,
                "session_index": int(session_index),
                "session_date": date,
                "score_artifact_path": str(score_path.resolve()),
                "score_artifact_sha256": score_sha,
                "score_manifest_path": str(manifest_path.resolve()),
                "score_manifest_sha256": manifest_sha,
            }
        )
        for ticker, target in zip(["AAA", "BBB", "CCC"], [0.03, 0.02, 0.01], strict=True):
            target_rows.append(
                {"session_date": date, "ticker": ticker, "canonical_target": target}
            )

    inventory = pd.DataFrame(inventory_rows)
    _, _, inventory_sha = validate_session_inventory(inventory, fixture_root=root)

    counter_path = root / "counter.json"
    counter_sha = _write_json(
        counter_path,
        {"current": 100, "target": 100, "session_inventory_sha256": inventory_sha},
    )

    source_manifest_path = root / "canonical_target_source_manifest.json"
    source_manifest_sha = _write_json(
        source_manifest_path,
        {"status": "MATURED", "fixture": True, "session_count": 100},
    )
    target_path = root / "target_attestation.json"
    target_id = "V4_X1_CANONICAL_TARGET_TEST_V1"
    target_sha = _write_json(
        target_path,
        {
            "canonical_target_id": target_id,
            "resolved": True,
            "required_session_count": 100,
            "matured_session_count": 100,
            "first_session_date": dates[0].date().isoformat(),
            "last_session_date": dates[-1].date().isoformat(),
            "resolution_lineage": "SYNTHETIC_TEST_LINEAGE_ONLY",
            "source_manifest_path": str(source_manifest_path.resolve()),
            "source_manifest_sha256": source_manifest_sha,
        },
    )

    predecessor = pd.Timestamp("2026-01-02")
    paper_path = root / "paper_attestation.json"
    paper_sha = _write_json(
        paper_path,
        {
            "session_count": 100,
            "predecessor_session_date": predecessor.date().isoformat(),
            "first_session_date": dates[0].date().isoformat(),
            "last_session_date": dates[-1].date().isoformat(),
            "continuity_valid": paper_valid,
            "execution_provenance_valid": paper_valid,
            "preclassified_invalidity": not paper_valid,
            "invalidity_reason": "SYNTHETIC_PRECLASSIFIED_BREAK" if not paper_valid else "",
            "execution_material_drag": False,
            "material_drag_rule_id": "SYNTHETIC_NO_MATERIAL_DRAG",
            "transitions": [
                {"session_date": date.date().isoformat(), "forward_position": position}
                for position, date in enumerate(dates, start=1)
            ],
        },
    )

    benchmark_path = root / "ihsg.csv"
    benchmark_dates = [predecessor, *dates.tolist()]
    pd.DataFrame(
        {
            "session_date": benchmark_dates,
            "benchmark_close": 7000.0 + np.arange(len(benchmark_dates), dtype=float),
        }
    ).to_csv(benchmark_path, index=False)
    benchmark_artifact_sha = sha256_file(benchmark_path)
    benchmark_attestation_path = root / "benchmark_attestation.json"
    if benchmark_status == "PINNED":
        benchmark_payload = {
            "status": "PINNED",
            "artifact_path": str(benchmark_path.resolve()),
            "artifact_sha256": benchmark_artifact_sha,
            "series": "IHSG_PRICE_INDEX_SYNTHETIC",
        }
    else:
        benchmark_payload = {"status": "UNAVAILABLE", "reason": "SYNTHETIC_TEST"}
    benchmark_attestation_sha = _write_json(benchmark_attestation_path, benchmark_payload)

    access_audit_path = root / "access_audit.json"
    access_audit_sha = _write_json(
        access_audit_path,
        {
            "review_complete": True,
            "unauthorized_access_known": False,
            "prior_access_marker_exists": False,
        },
    )

    returns = np.array([0.002 if i % 3 else -0.001 for i in range(100)], dtype=float)
    nav_values = [50_000_000.0]
    for value in returns:
        nav_values.append(nav_values[-1] * (1.0 + value))
    nav = pd.DataFrame(
        {"session_date": [predecessor, *dates.tolist()], "nav": nav_values}
    )
    execution = pd.DataFrame(
        {
            "session_date": dates,
            "gross_buy_notional": np.full(100, 500_000.0),
            "gross_sell_notional": np.full(100, 250_000.0),
            "nav_prev": np.array(nav_values[:-1], dtype=float),
        }
    )
    orders = pd.DataFrame(
        {
            "session_date": dates,
            "requires_open_decision": [True] * 100,
            "pending_due_to_unavailable_open": [False] * 100,
        }
    )
    ledger = pd.DataFrame(
        {
            "session_date": dates,
            "session_index": indices,
            "state": ["EVALUABLE"] * 100,
            "reason": [""] * 100,
        }
    )
    bundle = ProtectedEvaluationBundle(
        target_frame=pd.DataFrame(target_rows),
        ledger=ledger,
        nav_frame=nav if paper_valid else None,
        execution_frame=execution if paper_valid else None,
        order_frame=orders if paper_valid else None,
        metadata={
            "canonical_target_id": target_id,
            "target_source_manifest_sha256": source_manifest_sha,
            "paper_attestation_sha256": paper_sha,
            "counter_attestation_sha256": counter_sha,
            "session_inventory_sha256": inventory_sha,
        },
    )
    kwargs = {
        "mode": MODE_SYNTHETIC_REHEARSAL,
        "session_inventory": inventory,
        "counter_attestation_path": counter_path,
        "counter_attestation_sha256": counter_sha,
        "target_attestation_path": target_path,
        "target_attestation_sha256": target_sha,
        "paper_attestation_path": paper_path,
        "paper_attestation_sha256": paper_sha,
        "benchmark_attestation_path": benchmark_attestation_path,
        "benchmark_attestation_sha256": benchmark_attestation_sha,
        "access_audit_path": access_audit_path,
        "access_audit_sha256": access_audit_sha,
        "protocol_path": PROTOCOL_PATH.resolve(),
        "evaluator_path": EVALUATOR_PATH.resolve(),
        "evaluator_commit": EVALUATOR_IMPLEMENTATION_COMMIT,
        "fixture_root": root,
        "final_access_authorized": False,
    }
    return {
        "root": root,
        "dates": dates,
        "inventory": inventory,
        "bundle": bundle,
        "kwargs": kwargs,
        "paths": {
            "counter": counter_path,
            "target": target_path,
            "target_source_manifest": source_manifest_path,
            "paper": paper_path,
            "benchmark_attestation": benchmark_attestation_path,
            "benchmark_artifact": benchmark_path,
            "access_audit": access_audit_path,
        },
    }


def _invoke(case: dict, output_name: str, loader, **overrides):
    kwargs = dict(case["kwargs"])
    kwargs.update(overrides)
    return run_protected_evaluation_once(
        output_dir=case["root"] / output_name,
        protected_loader=loader,
        **kwargs,
    )


def _rewrite_attestation(case: dict, name: str, mutate) -> tuple[Path, str]:
    path = case["paths"][name]
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    return path, _write_json(path, payload)


def test_frozen_protocol_blob_pin_is_exact() -> None:
    assert git_blob_sha1_file(PROTOCOL_PATH) == PROTOCOL_GIT_BLOB_SHA1


def test_rehearsal_writes_marker_before_loader_and_completes(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    events: list[str] = []

    def loader():
        marker = case["root"] / "run" / MARKER_FILENAME
        assert marker.exists()
        assert json.loads(marker.read_text(encoding="utf-8"))["marker"] == REHEARSAL_ACCESS_MARKER
        return case["bundle"]

    result = _invoke(case, "run", loader, event_hook=events.append)
    assert events == [
        "PREATTESTATION_WRITTEN",
        "MARKER_WRITTEN",
        "LOADER_CALLED",
        "FINAL_RESULT_WRITTEN",
    ]
    assert result["verdicts"]["overall"] == "PROSPECTIVE_PASS"
    assert (case["root"] / "run" / PREACCESS_FILENAME).is_file()
    assert (case["root"] / "run" / RESULT_FILENAME).is_file()
    assert (case["root"] / "run" / FINAL_MANIFEST_FILENAME).is_file()
    assert not (case["root"] / "run" / FAILURE_FILENAME).exists()


def test_fault_before_attestation_write_never_reaches_marker_or_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _fixture(tmp_path)
    called = False

    def loader():
        nonlocal called
        called = True
        return case["bundle"]

    def fail_write(path: Path, payload: dict) -> None:
        if path.name == PREACCESS_FILENAME:
            raise ProspectiveAccessGateBlocked("synthetic attestation write failure")
        _write_json(path, payload)

    monkeypatch.setattr("idx_trade.prospective_evaluation_gate_v1._write_json_exclusive", fail_write)
    with pytest.raises(ProspectiveAccessGateBlocked, match="attestation write failure"):
        _invoke(case, "fault-before-attestation", loader)
    assert called is False
    assert not (case["root"] / "fault-before-attestation" / MARKER_FILENAME).exists()


def test_fault_after_attestation_before_marker_blocks_future_resume(tmp_path: Path) -> None:
    case = _fixture(tmp_path)

    def stop(event: str) -> None:
        if event == "PREATTESTATION_WRITTEN":
            raise RuntimeError("synthetic before marker")

    with pytest.raises(RuntimeError, match="before marker"):
        _invoke(case, "fault-before-marker", lambda: case["bundle"], event_hook=stop)
    assert (case["root"] / "fault-before-marker" / PREACCESS_FILENAME).exists()
    assert not (case["root"] / "fault-before-marker" / MARKER_FILENAME).exists()
    with pytest.raises(ProspectiveAccessGateBlocked, match="partial prior"):
        _invoke(case, "fault-before-marker", lambda: case["bundle"])


def test_fault_during_marker_creation_blocks_future_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _fixture(tmp_path)
    original_link = __import__("os").link
    calls = 0

    def fail_second_link(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic marker publish failure")
        return original_link(source, destination)

    monkeypatch.setattr("idx_trade.prospective_evaluation_gate_v1.os.link", fail_second_link)
    with pytest.raises(ProspectiveAccessGateBlocked, match="atomic publish unavailable"):
        _invoke(case, "fault-marker", lambda: case["bundle"])
    assert (case["root"] / "fault-marker" / PREACCESS_FILENAME).exists()
    assert not (case["root"] / "fault-marker" / MARKER_FILENAME).exists()
    monkeypatch.undo()
    with pytest.raises(ProspectiveAccessGateBlocked, match="partial prior"):
        _invoke(case, "fault-marker", lambda: case["bundle"])


def test_fault_immediately_before_loader_is_recorded_without_loader_call(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    called = False

    def loader():
        nonlocal called
        called = True
        return case["bundle"]

    def stop(event: str) -> None:
        if event == "LOADER_CALLED":
            raise RuntimeError("synthetic before loader")

    with pytest.raises(ProspectiveAccessGateBlocked, match="protected access started"):
        _invoke(case, "fault-before-loader", loader, event_hook=stop)
    assert called is False
    assert (case["root"] / "fault-before-loader" / FAILURE_FILENAME).exists()


def test_fault_during_result_serialization_locks_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _fixture(tmp_path)
    original = __import__("idx_trade.prospective_evaluation_gate_v1", fromlist=["_write_json_exclusive"])._write_json_exclusive

    def fail_result(path: Path, payload: dict) -> None:
        if path.name == RESULT_FILENAME:
            raise ProspectiveAccessGateBlocked("synthetic result serialization failure")
        original(path, payload)

    monkeypatch.setattr("idx_trade.prospective_evaluation_gate_v1._write_json_exclusive", fail_result)
    with pytest.raises(ProspectiveAccessGateBlocked, match="result serialization failure"):
        _invoke(case, "fault-result", lambda: case["bundle"])
    assert (case["root"] / "fault-result" / MARKER_FILENAME).exists()
    assert (case["root"] / "fault-result" / FAILURE_FILENAME).exists()
    monkeypatch.undo()
    with pytest.raises(ProspectiveAccessGateBlocked, match="partial prior"):
        _invoke(case, "fault-result", lambda: case["bundle"])


def test_fault_during_final_manifest_write_locks_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _fixture(tmp_path)
    original = __import__("idx_trade.prospective_evaluation_gate_v1", fromlist=["_write_json_exclusive"])._write_json_exclusive

    def fail_manifest(path: Path, payload: dict) -> None:
        if path.name == FINAL_MANIFEST_FILENAME:
            raise ProspectiveAccessGateBlocked("synthetic final manifest failure")
        original(path, payload)

    monkeypatch.setattr("idx_trade.prospective_evaluation_gate_v1._write_json_exclusive", fail_manifest)
    with pytest.raises(ProspectiveAccessGateBlocked, match="final manifest failure"):
        _invoke(case, "fault-final-manifest", lambda: case["bundle"])
    assert (case["root"] / "fault-final-manifest" / RESULT_FILENAME).exists()
    assert (case["root"] / "fault-final-manifest" / FAILURE_FILENAME).exists()


def test_fault_after_final_result_write_locks_rerun(tmp_path: Path) -> None:
    case = _fixture(tmp_path)

    def stop(event: str) -> None:
        if event == "FINAL_RESULT_WRITTEN":
            raise RuntimeError("synthetic after final result")

    with pytest.raises(ProspectiveAccessGateBlocked, match="protected access started"):
        _invoke(case, "fault-after-final", lambda: case["bundle"], event_hook=stop)
    output = case["root"] / "fault-after-final"
    assert (output / FINAL_MANIFEST_FILENAME).exists()
    assert (output / FAILURE_FILENAME).exists()


def test_counter_99_blocks_before_loader_and_marker(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    _, sha = _rewrite_attestation(case, "counter", lambda p: p.update(current=99))
    called = False

    def loader():
        nonlocal called
        called = True
        return case["bundle"]

    with pytest.raises(ProspectiveAccessGateBlocked, match="100/100"):
        _invoke(case, "counter99", loader, counter_attestation_sha256=sha)
    assert called is False
    assert not (case["root"] / "counter99" / MARKER_FILENAME).exists()


def test_inventory_must_be_exactly_100_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    with pytest.raises(ProspectiveAccessGateBlocked, match="exactly 100"):
        _invoke(
            case,
            "inventory99",
            lambda: case["bundle"],
            session_inventory=case["inventory"].iloc[:-1].copy(),
        )
    assert not (case["root"] / "inventory99" / MARKER_FILENAME).exists()


def test_score_manifest_outcome_guard_tamper_blocks_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    inventory = case["inventory"].copy()
    path = Path(inventory.iloc[0]["score_manifest_path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["guards"]["protected_outcome_accessed"] = True
    new_sha = _write_json(path, payload)
    inventory.loc[0, "score_manifest_sha256"] = new_sha
    with pytest.raises(ProspectiveAccessGateBlocked, match="guard changed"):
        _invoke(case, "scoreguard", lambda: case["bundle"], session_inventory=inventory)


def test_score_manifest_fingerprint_tamper_blocks_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    inventory = case["inventory"].copy()
    path = Path(inventory.iloc[0]["score_manifest_path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["model_fingerprint"] = "0" * 64
    new_sha = _write_json(path, payload)
    inventory.loc[0, "score_manifest_sha256"] = new_sha
    with pytest.raises(ProspectiveAccessGateBlocked, match="identity mismatch"):
        _invoke(case, "fingerprint", lambda: case["bundle"], session_inventory=inventory)


def test_score_artifact_hash_mutation_blocks_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    inventory = case["inventory"].copy()
    artifact = Path(inventory.iloc[0]["score_artifact_path"])
    score = pd.read_csv(artifact)
    score.loc[0, "alpha_consensus"] = 0.91
    score.to_csv(artifact, index=False)
    with pytest.raises(ProspectiveAccessGateBlocked, match="score artifact sha256 mismatch"):
        _invoke(case, "score-artifact-tamper", lambda: case["bundle"], session_inventory=inventory)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_id", "WRONG_MODEL"),
        ("generation", "WRONG_GENERATION"),
        ("ranking", "ticker ASC, alpha_consensus DESC"),
    ],
)
def test_score_manifest_identity_and_ranking_mutation_blocks_before_loader(
    tmp_path: Path, field: str, value: str
) -> None:
    case = _fixture(tmp_path)
    inventory = case["inventory"].copy()
    manifest = Path(inventory.iloc[0]["score_manifest_path"])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload[field] = value
    inventory.loc[0, "score_manifest_sha256"] = _write_json(manifest, payload)
    with pytest.raises(ProspectiveAccessGateBlocked, match="identity mismatch"):
        _invoke(case, f"manifest-{field}", lambda: case["bundle"], session_inventory=inventory)


def test_inventory_above_100_and_duplicate_identity_block_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    extra = case["inventory"].iloc[[0]].copy()
    too_many = pd.concat([case["inventory"], extra], ignore_index=True)
    with pytest.raises(ProspectiveAccessGateBlocked, match="exactly 100"):
        _invoke(case, "inventory101", lambda: case["bundle"], session_inventory=too_many)

    duplicate = case["inventory"].copy()
    duplicate.loc[1, "session_index"] = duplicate.loc[0, "session_index"]
    with pytest.raises(ProspectiveAccessGateBlocked, match="duplicate date/index"):
        _invoke(case, "inventory-duplicate", lambda: case["bundle"], session_inventory=duplicate)


@pytest.mark.parametrize("mutation", ["gap", "duplicate"])
def test_detailed_paperstate_transition_gap_or_duplicate_fails_closed(
    tmp_path: Path, mutation: str
) -> None:
    case = _fixture(tmp_path)
    path = case["paths"]["paper"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "gap":
        payload["transitions"][5]["forward_position"] = 7
    else:
        payload["transitions"][5]["session_date"] = payload["transitions"][4]["session_date"]
    sha = _write_json(path, payload)
    with pytest.raises(ProspectiveAccessGateBlocked, match="transition ledger"):
        _validate_paper(
            path,
            sha,
            expected_sessions=case["inventory"][["session_date", "session_index"]],
            fixture_root=case["root"],
            require_detailed_continuity=True,
        )


def test_neutral_extra_score_column_is_not_silently_ignored(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    inventory = case["inventory"].copy()
    artifact = Path(inventory.iloc[0]["score_artifact_path"])
    score = pd.read_csv(artifact)
    score["fwd5"] = 0.0
    score.to_csv(artifact, index=False)
    inventory.loc[0, "score_artifact_sha256"] = sha256_file(artifact)
    manifest = Path(inventory.iloc[0]["score_manifest_path"])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["output"]["artifact_sha256"] = inventory.loc[0, "score_artifact_sha256"]
    payload["output"]["columns"] = list(score.columns)
    inventory.loc[0, "score_manifest_sha256"] = _write_json(manifest, payload)
    with pytest.raises(ProspectiveAccessGateBlocked, match="schema must be exactly"):
        _invoke(case, "score-extra-column", lambda: case["bundle"], session_inventory=inventory)


def test_target_maturity_99_blocks_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    _, sha = _rewrite_attestation(case, "target", lambda p: p.update(matured_session_count=99))
    with pytest.raises(ProspectiveAccessGateBlocked, match="not mature"):
        _invoke(case, "target99", lambda: case["bundle"], target_attestation_sha256=sha)


def test_unresolved_target_blocks_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    _, sha = _rewrite_attestation(case, "target", lambda p: p.update(resolved=False))
    with pytest.raises(ProspectiveAccessGateBlocked, match="not uniquely resolved"):
        _invoke(case, "target-unresolved", lambda: case["bundle"], target_attestation_sha256=sha)


def test_paper_invalidity_must_be_preclassified_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)

    def mutate(payload):
        payload.update(
            continuity_valid=False,
            execution_provenance_valid=False,
            preclassified_invalidity=False,
            invalidity_reason="",
        )

    _, sha = _rewrite_attestation(case, "paper", mutate)
    with pytest.raises(ProspectiveAccessGateBlocked, match="classified before outcomes"):
        _invoke(case, "paper-unclassified", lambda: case["bundle"], paper_attestation_sha256=sha)


def test_preclassified_paper_invalidity_allows_alpha_but_forces_overall_invalid(tmp_path: Path) -> None:
    case = _fixture(tmp_path, paper_valid=False)
    result = _invoke(case, "paper-invalid", lambda: case["bundle"])
    assert result["alpha"]["mean_ic"] > 0
    assert result["portfolio"] is None
    assert result["verdicts"]["execution"] == "EXECUTION_BROKEN"
    assert result["verdicts"]["overall"] == "PROSPECTIVE_INVALID_OPERATIONAL"


def test_known_prior_outcome_access_blocks_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    _, sha = _rewrite_attestation(
        case, "access_audit", lambda p: p.update(unauthorized_access_known=True)
    )
    with pytest.raises(ProspectiveAccessGateBlocked, match="prior outcome access"):
        _invoke(case, "auditbad", lambda: case["bundle"], access_audit_sha256=sha)


def test_protocol_blob_tamper_blocks_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    tampered = case["root"] / "protocol.md"
    tampered.write_text(PROTOCOL_PATH.read_text(encoding="utf-8") + "\nTAMPER\n", encoding="utf-8")
    with pytest.raises(ProspectiveAccessGateBlocked, match="protocol Git blob changed"):
        _invoke(case, "protocolbad", lambda: case["bundle"], protocol_path=tampered)


def test_evaluator_blob_tamper_blocks_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    tampered = case["root"] / "evaluator.py"
    tampered.write_text(EVALUATOR_PATH.read_text(encoding="utf-8") + "\n# tamper\n", encoding="utf-8")
    with pytest.raises(ProspectiveAccessGateBlocked, match="evaluator Git blob changed"):
        _invoke(case, "evaluatorbad", lambda: case["bundle"], evaluator_path=tampered)


def test_real_mode_requires_explicit_final_authorization_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    called = False

    def loader():
        nonlocal called
        called = True
        return case["bundle"]

    kwargs = dict(case["kwargs"])
    kwargs.update(mode=MODE_PROTECTED_PROSPECTIVE, fixture_root=None, final_access_authorized=False)
    with pytest.raises(ProspectiveAccessGateBlocked, match="explicit final authorization"):
        run_protected_evaluation_once(
            output_dir=tmp_path / "real-blocked",
            protected_loader=loader,
            **kwargs,
        )
    assert called is False
    assert not (tmp_path / "real-blocked" / MARKER_FILENAME).exists()


def test_benchmark_hash_mismatch_blocks_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    case["paths"]["benchmark_artifact"].write_text("corrupt", encoding="utf-8")
    with pytest.raises(ProspectiveAccessGateBlocked, match="benchmark artifact sha256 mismatch"):
        _invoke(case, "benchmarkbad", lambda: case["bundle"])


def test_target_source_manifest_mutation_blocks_before_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    case["paths"]["target_source_manifest"].write_text("mutated\n", encoding="utf-8")
    with pytest.raises(ProspectiveAccessGateBlocked, match="canonical target source manifest sha256"):
        _invoke(case, "target-source-bad", lambda: case["bundle"])


def test_execution_bundle_must_cover_all_sessions(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    bad_bundle = ProtectedEvaluationBundle(
        target_frame=case["bundle"].target_frame,
        ledger=case["bundle"].ledger,
        nav_frame=case["bundle"].nav_frame,
        execution_frame=case["bundle"].execution_frame.iloc[:-1].copy(),
        order_frame=case["bundle"].order_frame,
        metadata=case["bundle"].metadata,
    )
    with pytest.raises(ProspectiveAccessGateBlocked, match="exactly all 100 sessions"):
        _invoke(case, "execution-missing", lambda: bad_bundle)
    assert (case["root"] / "execution-missing" / MARKER_FILENAME).exists()


def test_crash_after_marker_creates_orphan_that_blocks_fresh_process_equivalent(tmp_path: Path) -> None:
    case = _fixture(tmp_path)

    def crash(event: str) -> None:
        if event == "MARKER_WRITTEN":
            raise RuntimeError("synthetic process crash")

    with pytest.raises(RuntimeError, match="synthetic process crash"):
        _invoke(case, "crashed", lambda: case["bundle"], event_hook=crash)
    assert (case["root"] / "crashed" / MARKER_FILENAME).exists()
    called = False

    def resumed_loader():
        nonlocal called
        called = True
        return case["bundle"]

    with pytest.raises(ProspectiveAccessGateBlocked, match="partial prior"):
        _invoke(case, "crashed", resumed_loader)
    assert called is False


def test_benchmark_unavailable_is_frozen_not_reconstructed_after_access(tmp_path: Path) -> None:
    case = _fixture(tmp_path, benchmark_status="UNAVAILABLE")
    result = _invoke(case, "benchmark-none", lambda: case["bundle"])
    assert result["diagnostics"]["benchmark"] == {"benchmark_status": "BENCHMARK_UNAVAILABLE"}


def test_post_access_metadata_mismatch_writes_failure_and_locks_rerun(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    bad = ProtectedEvaluationBundle(
        target_frame=case["bundle"].target_frame,
        ledger=case["bundle"].ledger,
        nav_frame=case["bundle"].nav_frame,
        execution_frame=case["bundle"].execution_frame,
        order_frame=case["bundle"].order_frame,
        metadata={**dict(case["bundle"].metadata), "canonical_target_id": "WRONG"},
    )
    output = case["root"] / "post-access-bad"
    with pytest.raises(ProspectiveAccessGateBlocked, match="metadata mismatch"):
        _invoke(case, "post-access-bad", lambda: bad)
    assert (output / MARKER_FILENAME).exists()
    assert (output / FAILURE_FILENAME).exists()
    called = False

    def second_loader():
        nonlocal called
        called = True
        return case["bundle"]

    with pytest.raises(ProspectiveAccessGateBlocked, match="partial prior"):
        _invoke(case, "post-access-bad", second_loader)
    assert called is False


def test_target_key_mismatch_fails_only_after_marker_and_locks_state(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    bad_target = case["bundle"].target_frame.iloc[:-1].copy()
    bad = ProtectedEvaluationBundle(
        target_frame=bad_target,
        ledger=case["bundle"].ledger,
        nav_frame=case["bundle"].nav_frame,
        execution_frame=case["bundle"].execution_frame,
        order_frame=case["bundle"].order_frame,
        metadata=case["bundle"].metadata,
    )
    with pytest.raises(ProspectiveAccessGateBlocked, match="target keys"):
        _invoke(case, "target-keys", lambda: bad)
    assert (case["root"] / "target-keys" / MARKER_FILENAME).exists()
    assert (case["root"] / "target-keys" / FAILURE_FILENAME).exists()


def test_successful_rerun_is_idempotent_and_never_calls_loader_again(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    first = _invoke(case, "idem", lambda: case["bundle"])
    hashes_before = {
        name: sha256_file(case["root"] / "idem" / name)
        for name in (PREACCESS_FILENAME, MARKER_FILENAME, RESULT_FILENAME, FINAL_MANIFEST_FILENAME)
    }
    called = False
    events: list[str] = []

    def loader():
        nonlocal called
        called = True
        raise AssertionError("loader must not run on idempotent replay")

    second = _invoke(case, "idem", loader, event_hook=events.append)
    assert called is False
    assert events == ["IDEMPOTENT_RESULT_REUSED"]
    assert second["verdicts"] == first["verdicts"]
    assert hashes_before == {
        name: sha256_file(case["root"] / "idem" / name)
        for name in (PREACCESS_FILENAME, MARKER_FILENAME, RESULT_FILENAME, FINAL_MANIFEST_FILENAME)
    }


def test_cold_restart_resume_and_completed_rerun_are_cross_process_idempotent(tmp_path: Path) -> None:
    """Processes A/B/C must prove durable resume without reloading the bundle."""

    case = _fixture(tmp_path)
    bundle_path = case["root"] / "cold-bundle.pkl"
    kwargs_path = case["root"] / "cold-kwargs.pkl"
    with bundle_path.open("wb") as handle:
        pickle.dump(case["bundle"], handle)
    with kwargs_path.open("wb") as handle:
        pickle.dump(case["kwargs"], handle)
    child = r'''
import json
import pickle
import sys
from pathlib import Path

from idx_trade.prospective_evaluation_gate_v1 import run_protected_evaluation_once

root = Path(sys.argv[1])
mode = sys.argv[2]
with (root / "cold-bundle.pkl").open("rb") as handle:
    bundle = pickle.load(handle)
with (root / "cold-kwargs.pkl").open("rb") as handle:
    kwargs = pickle.load(handle)

def loader():
    if mode == "sentinel":
        (root / "loader-called").write_text("called\n", encoding="utf-8")
    return bundle

result = run_protected_evaluation_once(
    output_dir=root / "cold-run",
    protected_loader=loader,
    **kwargs,
)
print(json.dumps({"evaluation_id": result["evaluation_id"]}, sort_keys=True))
'''
    env = os.environ.copy()
    src_root = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        [src_root, env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    subprocess.run(
        [sys.executable, "-c", child, str(case["root"]), "loader"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    immutable_names = (PREACCESS_FILENAME, MARKER_FILENAME, RESULT_FILENAME, FINAL_MANIFEST_FILENAME)
    hashes_before = {
        name: sha256_file(case["root"] / "cold-run" / name) for name in immutable_names
    }
    for _ in range(2):
        subprocess.run(
            [sys.executable, "-c", child, str(case["root"]), "sentinel"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        assert not (case["root"] / "loader-called").exists()
        assert hashes_before == {
            name: sha256_file(case["root"] / "cold-run" / name) for name in immutable_names
        }


def test_orphan_marker_fails_closed_without_loader(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    output = case["root"] / "orphan"
    output.mkdir()
    _write_json(output / MARKER_FILENAME, {"mode": MODE_SYNTHETIC_REHEARSAL})
    called = False

    def loader():
        nonlocal called
        called = True
        return case["bundle"]

    with pytest.raises(ProspectiveAccessGateBlocked, match="partial prior"):
        _invoke(case, "orphan", loader)
    assert called is False


def test_atomic_publish_failure_cleans_temporary_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "immutable.json"

    def fail_link(*args, **kwargs):
        raise OSError("synthetic publish interruption")

    monkeypatch.setattr("idx_trade.prospective_evaluation_gate_v1.os.link", fail_link)
    with pytest.raises(ProspectiveAccessGateBlocked, match="atomic publish unavailable"):
        _write_json_exclusive(destination, {"status": "synthetic"})
    assert not destination.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_orphan_atomic_temporary_file_blocks_resume(tmp_path: Path) -> None:
    case = _fixture(tmp_path)
    output = case["root"] / "orphan-temp"
    output.mkdir()
    (output / ".result.json.synthetic.tmp").write_text("partial", encoding="utf-8")
    with pytest.raises(ProspectiveAccessGateBlocked, match="partial atomic temporary"):
        _invoke(case, "orphan-temp", lambda: case["bundle"])
