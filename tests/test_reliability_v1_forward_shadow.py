from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade.forward_monitoring import runtime_paths
from idx_trade.reliability_v1_forward_shadow import (
    EXPECTED_FIRST_O2_MANIFEST_SHA256,
    EXPECTED_FIRST_O2_SCORE_SHA256,
    O2_FEATURE_ORDER_SHA256,
    O2_MODEL_ID,
    O2_MODEL_MANIFEST_SHA256,
    O2_MODEL_SHA256,
    RELIABILITY_FORMULA_VERSION,
    align_reliability_v1_sessions,
    score_reliability_v1_session,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime(tmp_path: Path, *, scores: list[float | None]) -> Path:
    root = tmp_path
    paths = runtime_paths(root)
    session = "2026-08-13"
    source = paths.monitor_root / "model_runs" / session / "o2-geometry-full3-v1-candidate-001"
    source.mkdir(parents=True)
    frame = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D", "FLAT"],
            "session_date": [session] * 5,
            "o2_eligible": [score is not None for score in scores],
            "o2_exclusion_reason": [None, None, None, None, "FLAT_RANGE_ZERO_DENOMINATOR"],
            "score": scores,
        }
    )
    artifact = source / "score_artifact.parquet"
    frame.to_parquet(artifact, index=False)
    manifest = {
        "status": "DONE",
        "session_date": session,
        "model_id": O2_MODEL_ID,
        "model_sha256": O2_MODEL_SHA256,
        "model_manifest_sha256": O2_MODEL_MANIFEST_SHA256,
        "feature_order_sha256": O2_FEATURE_ORDER_SHA256,
        "score_artifact_path": str(artifact),
        "score_artifact_sha256": _sha(artifact),
        "official_session_index": 1268,
        "outcome_blind": True,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
    }
    manifest_path = source / "manifest.json"
    # This fixture uses a later session, so it does not need the frozen
    # first-session manifest hash while still exercising the exact source pin.
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return root


def test_score_margin_formula_and_unscored_rows_are_sidecar_only(tmp_path: Path) -> None:
    root = _runtime(tmp_path, scores=[0.1, 0.2, 0.5, 0.9, None])
    paths = runtime_paths(root)
    before_counter = paths.monitor_root / "o2_forward_counter.json"
    before_counter.parent.mkdir(parents=True, exist_ok=True)
    before_counter.write_text('{"session_count": 1}', encoding="utf-8")
    before = before_counter.read_bytes()

    result = score_reliability_v1_session(paths, "2026-08-13")
    output = pd.read_parquet(result["reliability_artifact_path"])
    scored = output.loc[output["o2_eligible"]].sort_values("o2_score")

    assert result["formula_version"] == RELIABILITY_FORMULA_VERSION
    assert result["o2_scored_rows"] == 4
    assert result["reliability_finite_rows"] == 4
    assert result["o2_unscored_not_applicable_rows"] == 1
    assert scored["score_margin_reliability"].tolist() == pytest.approx(
        [0.1 / 0.425, 0.1 / 0.425, 0.3 / 0.425, 0.4 / 0.425]
    )
    assert output.loc[~output["o2_eligible"], "score_margin_reliability"].isna().all()
    assert output.loc[~output["o2_eligible"], "reliability_status"].tolist() == ["NOT_APPLICABLE_O2_UNSCORED"]
    assert before_counter.read_bytes() == before
    assert result["runtime_flags"]["independent_reliability_counter_registration"] is False


def test_zero_iqr_is_unavailable_without_failing_o2(tmp_path: Path) -> None:
    root = _runtime(tmp_path, scores=[0.2, 0.2, 0.2, 0.2, None])
    result = score_reliability_v1_session(runtime_paths(root), "2026-08-13")
    output = pd.read_parquet(result["reliability_artifact_path"])
    scored = output.loc[output["o2_eligible"]]
    assert result["o2_scored_rows"] == 4
    assert result["reliability_finite_rows"] == 0
    assert scored["reliability_status"].eq("UNAVAILABLE_SESSION_GEOMETRY").all()
    assert scored["score_margin_reliability"].isna().all()


def test_alignment_reads_only_existing_data_ready_session_and_is_idempotent(tmp_path: Path) -> None:
    root = _runtime(tmp_path, scores=[0.1, 0.2, 0.5, 0.9, None])
    paths = runtime_paths(root)
    from idx_trade.forward_monitoring import _connect

    connection = _connect(paths)
    try:
        now = "2026-08-13T00:00:00+00:00"
        connection.execute(
            "INSERT INTO session_snapshots(session_date,state,updated_at) VALUES(?,?,?)",
            ("2026-08-13", "DATA_READY", now),
        )
    finally:
        connection.close()
    first = align_reliability_v1_sessions(root, ["2026-08-13"])
    artifact = Path(first["sessions"][0]["reliability_artifact_path"])
    artifact_sha = _sha(artifact)
    second = align_reliability_v1_sessions(root, ["2026-08-13"])
    assert len(first["sessions"]) == 1
    assert len(second["sessions"]) == 1
    assert _sha(artifact) == artifact_sha
    assert first["runtime_flags"]["fresh_forward_outcomes_accessed"] is False


def test_source_artifact_revision_fails_closed(tmp_path: Path) -> None:
    root = _runtime(tmp_path, scores=[0.1, 0.2, 0.5, 0.9, None])
    paths = runtime_paths(root)
    source_manifest = paths.monitor_root / "model_runs" / "2026-08-13" / "o2-geometry-full3-v1-candidate-001" / "manifest.json"
    payload = json.loads(source_manifest.read_text(encoding="utf-8"))
    payload["score_artifact_sha256"] = "0" * 64
    source_manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="hash mismatch"):
        score_reliability_v1_session(paths, "2026-08-13")
