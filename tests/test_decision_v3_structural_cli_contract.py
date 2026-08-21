from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/run_v4_x1_decision_v3_graded_evidence_structural_replay.py"


def test_cli_authorization_token_is_post_runner_audit_interlock() -> None:
    spec = importlib.util.spec_from_file_location("decision_v3_structural_cli", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.AUTHORIZATION_TOKEN == (
        "DECISION_V3_GRADED_EVIDENCE_STRUCTURAL_REPLAY_RUNNER_AUDIT_ACCEPTED_V2"
    )
