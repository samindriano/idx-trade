from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade.forward_100_evaluator import (
    O2_FEATURE_ORDER_SHA256,
    O2_MODEL_SHA256,
    PROTOCOL_SHA256,
    SYNTHETIC_MARKER,
    ForwardEvaluationBlocked,
)
from idx_trade.forward_100_evaluator_guarded import (
    run_guarded_synthetic_forward_evaluation,
    validate_guarded_session_inventory,
)
from idx_trade.forward_model_runtime import O2_MODEL_ID
from idx_trade.provenance import sha256_file
from idx_trade.reliability_v1_forward_shadow import (
    PROTECTED_FLAGS as RELIABILITY_PROTECTED_FLAGS,
    RELIABILITY_FORMULA_VERSION,
    RELIABILITY_MODEL_ID,
)
from idx_trade.storage import write_parquet_atomic


PROTOCOL = Path(__file__).parents[1] / "docs" / "checkpoints" / "2026-08-13_FORWARD_100_SESSION_EVALUATION_PROTOCOL_V1.md"
CODE_COMMIT = "a" * 40
RELIABILITY_SPEC_COMMIT = "3239a319fbd4ff492b16a74d899a20edc9affa7f"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _bundle(
    tmp_path: Path,
) -> tuple[Path, pd.DataFrame, pd.DataFrame, dict[str, dict[str, str]]]:
    root = tmp_path / "guarded-fixtures"
    root.mkdir()
    shared_file = root / "shared.fixture"
    shared_file.write_text("synthetic shared provenance\n", encoding="utf-8")
    shared = {
        role: {"path": str(shared_file), "sha256": sha256_file(shared_file)}
        for role in (
            "o2_model",
            "o2_model_manifest",
            "o2_feature_order",
            "official_calendar",
            "security_master",
            "tradability",
            "corporate_actions",
            "source_snapshot",
        )
    }

    dates = pd.bdate_range("2020-01-02", periods=100)
    inventory_rows: list[dict[str, object]] = []
    outcome_rows: list[dict[str, object]] = []

    for offset, (date, session_index) in enumerate(zip(dates, range(2000, 2100), strict=True)):
        session_key = date.date().isoformat()
        tickers = [f"T{rank:03d}" for rank in range(50)]
        scores = np.arange(50, dtype=float)

        o2_path = root / f"o2_{session_index}.parquet"
        o2_frame = pd.DataFrame(
            {
                "ticker": tickers,
                "session_date": [date] * 50,
                "o2_eligible": [True] * 50,
                "o2_exclusion_reason": [""] * 50,
                "score": scores,
                "rank": np.arange(1, 51),
                "score_percentile": np.linspace(1.0, 0.0, 50),
                "model_id": [O2_MODEL_ID] * 50,
                "generation": ["O2"] * 50,
                "model_sha256": [O2_MODEL_SHA256] * 50,
                "feature_order_sha256": [O2_FEATURE_ORDER_SHA256] * 50,
            }
        )
        write_parquet_atomic(o2_frame, o2_path)
        o2_sha = sha256_file(o2_path)

        o2_manifest_path = root / f"o2_manifest_{session_index}.json"
        _write_json(
            o2_manifest_path,
            {
                "status": "DONE",
                "session_date": session_key,
                "official_session_index": session_index,
                "model_id": O2_MODEL_ID,
                "score_artifact_sha256": o2_sha,
                "model_sha256": O2_MODEL_SHA256,
                "feature_order_sha256": O2_FEATURE_ORDER_SHA256,
                "outcome_blind": True,
                "fresh_forward_outcomes_accessed": False,
                "forward_outcome_access_marker_written": False,
            },
        )
        o2_manifest_sha = sha256_file(o2_manifest_path)

        reliability_path = root / f"reliability_{session_index}.parquet"
        reliability_frame = pd.DataFrame(
            {
                "date": [session_key] * 50,
                "session_index": [session_index] * 50,
                "ticker": tickers,
                "o2_eligible": [True] * 50,
                "o2_score": scores,
                "score_margin_reliability": [float((rank % 7) + rank / 100.0) for rank in range(50)],
                "reliability_percentile": np.linspace(0.0, 100.0, 50),
                "reliability_status": ["AVAILABLE"] * 50,
                "reliability_reason": [""] * 50,
                "formula_version": [RELIABILITY_FORMULA_VERSION] * 50,
                "model_id": [RELIABILITY_MODEL_ID] * 50,
                "generation": ["RELIABILITY-V1-SHADOW"] * 50,
            }
        )
        write_parquet_atomic(reliability_frame, reliability_path)
        reliability_sha = sha256_file(reliability_path)

        reliability_manifest_path = root / f"reliability_manifest_{session_index}.json"
        _write_json(
            reliability_manifest_path,
            {
                "schema": "idx-trade/reliability-v1-forward-shadow-artifacts-v1",
                "status": "READY",
                "session_date": session_key,
                "official_session_index": session_index,
                "model_id": RELIABILITY_MODEL_ID,
                "generation": "RELIABILITY-V1-SHADOW",
                "formula_version": RELIABILITY_FORMULA_VERSION,
                "o2_source_score_artifact_path": str(o2_path),
                "o2_source_score_artifact_sha256": o2_sha,
                "o2_source_session_manifest_path": str(o2_manifest_path),
                "o2_source_session_manifest_sha256": o2_manifest_sha,
                "o2_model_sha256": O2_MODEL_SHA256,
                "o2_feature_order_sha256": O2_FEATURE_ORDER_SHA256,
                "spec_commit": RELIABILITY_SPEC_COMMIT,
                "implementation_commit": CODE_COMMIT,
                "reliability_artifact_path": str(reliability_path),
                "reliability_artifact_sha256": reliability_sha,
                "runtime_flags": dict(RELIABILITY_PROTECTED_FLAGS),
                "outcome_access": "LOCKED",
            },
        )
        reliability_manifest_sha = sha256_file(reliability_manifest_path)

        inventory_rows.append(
            {
                "session_date": date,
                "session_index": session_index,
                "o2_score_path": str(o2_path),
                "o2_score_sha256": o2_sha,
                "o2_manifest_path": str(o2_manifest_path),
                "o2_manifest_sha256": o2_manifest_sha,
                "reliability_path": str(reliability_path),
                "reliability_sha256": reliability_sha,
                "reliability_manifest_path": str(reliability_manifest_path),
                "reliability_manifest_sha256": reliability_manifest_sha,
                "protected": False,
            }
        )

        for rank, ticker in enumerate(tickers):
            outcome_rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "binary_target": int(rank >= 25),
                    "unresolved_reason": "",
                    "source_ref": f"synthetic://outcomes/{offset}",
                    "source_sha256": "b" * 64,
                }
            )

    return root, pd.DataFrame(inventory_rows), pd.DataFrame(outcome_rows), shared


def test_guarded_entrypoint_has_no_in_memory_score_or_reliability_injection() -> None:
    parameters = inspect.signature(run_guarded_synthetic_forward_evaluation).parameters
    assert "o2_scores" not in parameters
    assert "reliability" not in parameters
    assert "expected_protocol_sha256" not in parameters


def test_guarded_inventory_accepts_real_reliability_schema_and_rejects_old_synthetic_flags(tmp_path: Path) -> None:
    root, inventory, _, _ = _bundle(tmp_path)
    sessions, complete = validate_guarded_session_inventory(inventory, fixture_root=root)
    assert len(sessions) == 100
    assert complete is True

    changed = inventory.copy()
    manifest_path = Path(str(changed.loc[0, "reliability_manifest_path"]))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["runtime_flags"] = {
        "provider_call": False,
        "outcome_access": False,
        "o2_refit": False,
        "o2_rescore": False,
        "counter_change": False,
        "tiering_or_filtering": False,
    }
    _write_json(manifest_path, payload)
    changed.loc[0, "reliability_manifest_sha256"] = sha256_file(manifest_path)
    with pytest.raises(ForwardEvaluationBlocked, match="protected_flags"):
        validate_guarded_session_inventory(changed, fixture_root=root)


def test_hash_pinned_sidecar_must_match_exact_o2_row_content(tmp_path: Path) -> None:
    root, inventory, outcomes, shared = _bundle(tmp_path)
    reliability_path = Path(str(inventory.loc[0, "reliability_path"]))
    sidecar = pd.read_parquet(reliability_path)
    sidecar.loc[0, "o2_score"] = float(sidecar.loc[0, "o2_score"]) + 1.0
    write_parquet_atomic(sidecar, reliability_path)
    new_sha = sha256_file(reliability_path)
    inventory.loc[0, "reliability_sha256"] = new_sha

    manifest_path = Path(str(inventory.loc[0, "reliability_manifest_path"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["reliability_artifact_sha256"] = new_sha
    _write_json(manifest_path, manifest)
    inventory.loc[0, "reliability_manifest_sha256"] = sha256_file(manifest_path)

    with pytest.raises(ForwardEvaluationBlocked, match="O2 scores differ"):
        run_guarded_synthetic_forward_evaluation(
            output_dir=tmp_path / "output",
            marker_root=tmp_path / "marker",
            fixture_root=root,
            protocol_path=PROTOCOL,
            session_inventory=inventory,
            shared_artifacts=shared,
            outcome_loader=lambda: outcomes,
            code_commit=CODE_COMMIT,
        )
    assert not (tmp_path / "marker" / SYNTHETIC_MARKER).exists()


def test_missing_sidecar_is_declared_inconclusive_before_outcome_loader(tmp_path: Path) -> None:
    root, inventory, outcomes, shared = _bundle(tmp_path)
    for column in (
        "reliability_path",
        "reliability_sha256",
        "reliability_manifest_path",
        "reliability_manifest_sha256",
    ):
        inventory.loc[0, column] = ""

    output_dir = tmp_path / "output"
    events: list[str] = []

    def loader() -> pd.DataFrame:
        pre = json.loads((output_dir / "pre_outcome_contract.json").read_text(encoding="utf-8"))
        assert pre["reliability_sidecars_complete"] is False
        assert pre["reliability_pre_outcome_disposition"] == "RELIABILITY_FORWARD_INCONCLUSIVE_DATA"
        assert events == ["pre_outcome_manifest_written", "synthetic_marker_written"]
        return outcomes

    result = run_guarded_synthetic_forward_evaluation(
        output_dir=output_dir,
        marker_root=tmp_path / "marker",
        fixture_root=root,
        protocol_path=PROTOCOL,
        session_inventory=inventory,
        shared_artifacts=shared,
        outcome_loader=loader,
        code_commit=CODE_COMMIT,
        event_hook=events.append,
    )
    assert result["reliability_pre_outcome_disposition"] == "RELIABILITY_FORWARD_INCONCLUSIVE_DATA"
    assert result["reliability"]["decision"] == "RELIABILITY_FORWARD_INCONCLUSIVE_DATA"


def test_protocol_hash_is_fixed_and_mismatch_blocks_before_loader(tmp_path: Path) -> None:
    root, inventory, outcomes, shared = _bundle(tmp_path)
    changed_protocol = tmp_path / "changed_protocol.md"
    changed_protocol.write_bytes(PROTOCOL.read_bytes() + b"\nchanged\n")
    assert sha256_file(changed_protocol) != PROTOCOL_SHA256
    called = False

    def loader() -> pd.DataFrame:
        nonlocal called
        called = True
        return outcomes

    with pytest.raises(ForwardEvaluationBlocked, match="protocol hash"):
        run_guarded_synthetic_forward_evaluation(
            output_dir=tmp_path / "output",
            marker_root=tmp_path / "marker",
            fixture_root=root,
            protocol_path=changed_protocol,
            session_inventory=inventory,
            shared_artifacts=shared,
            outcome_loader=loader,
            code_commit=CODE_COMMIT,
        )
    assert called is False
    assert not (tmp_path / "marker" / SYNTHETIC_MARKER).exists()


def test_guarded_complete_bundle_runs_with_manifest_marker_loader_order(tmp_path: Path) -> None:
    root, inventory, outcomes, shared = _bundle(tmp_path)
    events: list[str] = []

    def loader() -> pd.DataFrame:
        assert events == ["pre_outcome_manifest_written", "synthetic_marker_written"]
        return outcomes

    result = run_guarded_synthetic_forward_evaluation(
        output_dir=tmp_path / "output",
        marker_root=tmp_path / "marker",
        fixture_root=root,
        protocol_path=PROTOCOL,
        session_inventory=inventory,
        shared_artifacts=shared,
        outcome_loader=loader,
        code_commit=CODE_COMMIT,
        event_hook=events.append,
    )
    assert result["status"] == "SYNTHETIC_FORWARD_100_EVALUATION_COMPLETE"
    assert result["reliability_pre_outcome_disposition"] == "READY_FOR_FROZEN_RELIABILITY_EVALUATION"
    assert Path(result["artifact_manifest_path"]).is_file()
    assert (tmp_path / "marker" / SYNTHETIC_MARKER).is_file()
