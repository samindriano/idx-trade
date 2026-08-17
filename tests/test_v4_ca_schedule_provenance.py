from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.run_v4_ca_event_window_support_with_schedule import verify_schedule_root


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_root(tmp_path: Path, *, outcome_blind: bool = True) -> Path:
    root = tmp_path / "schedule"
    root.mkdir()
    evidence = root / "schedule_evidence.csv"
    evidence.write_text("event_id,ticker,linkage_status,transition_semantic,transition_date,ksei_reference,source_sha256\n", encoding="utf-8")
    summary = {
        "schema_version": "v4_ca_schedule_acquisition_v1",
        "status": "V4_CA_TARGETED_KSEI_SCHEDULE_ACQUISITION_COMPLETE",
        "outcome_blind": outcome_blind,
        "provider_calls": True,
        "source_substitution": False,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "output_hashes": {"schedule_evidence": digest(evidence)},
    }
    summary_path = root / "summary.json"
    summary_path.write_text(json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ca_schedule_acquisition_manifest_v1",
        "summary_sha256": digest(summary_path),
    }
    (root / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    return root


def test_verified_schedule_root_returns_exact_evidence(tmp_path):
    root = make_root(tmp_path)
    assert verify_schedule_root(root) == root / "schedule_evidence.csv"


def test_schedule_root_rejects_non_outcome_blind_summary(tmp_path):
    root = make_root(tmp_path, outcome_blind=False)
    with pytest.raises(RuntimeError, match="outcome_blind"):
        verify_schedule_root(root)
