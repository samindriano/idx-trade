from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from idx_trade.decision_v3_failure_diagnosis_contract import (
    EXPECTED_PREREG_CANONICAL_SHA256,
    canonical_json_sha256,
    verify_failure_diagnosis_prereg,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_frozen_v3_failure_diagnosis_contract_hash() -> None:
    path = REPO_ROOT / "docs/specs/decision_v3_failure_mechanism_diagnosis_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert canonical_json_sha256(payload) == EXPECTED_PREREG_CANONICAL_SHA256
    assert verify_failure_diagnosis_prereg(REPO_ROOT) == path.resolve()
    assert payload["execution_authorized"] is False
    assert payload["forbidden"]["counterfactual_policy_simulation"] is True
    assert payload["forbidden"]["historical_alpha_source_access"] is True


def test_cli_rejects_bad_token_before_structural_source_access(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts/run_v4_x1_decision_v3_failure_mechanism_diagnosis.py"
    missing = tmp_path / "missing-parent"
    output = tmp_path / "out"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--structural-root",
            str(missing),
            "--output-dir",
            str(output),
            "--authorization",
            "WRONG",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "DECISION_V3_FAILURE_DIAGNOSIS_NOT_AUDIT_AUTHORIZED" in (
        completed.stdout + completed.stderr
    )
    assert not output.exists()
