from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.prospective_evaluation_gate_v1 import validate_session_inventory
from idx_trade.prospective_preaccess_adapters_v1 import ProductionAdapterError
from idx_trade.prospective_preaccess_completion_v1 import (
    build_admitted_inventory,
    gate_shape_inventory_sha256,
    project_verified_score_session,
    reconcile_runtime_counter,
    write_synthetic_score_session,
)


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
