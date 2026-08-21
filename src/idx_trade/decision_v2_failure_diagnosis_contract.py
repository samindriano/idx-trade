from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PREREG_RELATIVE_PATH = Path(
    "docs/specs/decision_v2_failure_mechanism_diagnosis_v1.json"
)
EXPECTED_PREREG_CANONICAL_SHA256 = (
    "72b2bfe43c37f5a1a5fd1c8ad5f91e3cf8c2e7393371b9a11e12dcbd287b64da"
)
EXPECTED_STATUS = "FROZEN_BEFORE_DIAGNOSIS_EXECUTION"


class DecisionV2FailureDiagnosisContractError(RuntimeError):
    pass


def canonical_json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_failure_diagnosis_prereg(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser().resolve() / PREREG_RELATIVE_PATH
    if not path.is_file():
        raise DecisionV2FailureDiagnosisContractError("FAILURE_DIAGNOSIS_PREREG_MISSING")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV2FailureDiagnosisContractError("FAILURE_DIAGNOSIS_PREREG_INVALID") from exc
    actual = canonical_json_sha256(payload)
    if actual != EXPECTED_PREREG_CANONICAL_SHA256:
        raise DecisionV2FailureDiagnosisContractError(
            f"FAILURE_DIAGNOSIS_PREREG_SHA_MISMATCH:{actual}!={EXPECTED_PREREG_CANONICAL_SHA256}"
        )
    if payload.get("status") != EXPECTED_STATUS:
        raise DecisionV2FailureDiagnosisContractError("FAILURE_DIAGNOSIS_PREREG_STATUS_CHANGED")
    forbidden = payload.get("forbidden", {})
    required_true = {
        "alternative_decision_rule_simulation",
        "alternative_threshold_test",
        "decision_parameter_sweep",
        "realized_returns",
        "historical_pnl",
        "protected_or_fresh_forward_outcomes",
        "model_refit_or_retune",
        "provider_or_network_calls",
        "decision_v2_structural_replay_rerun",
    }
    if any(forbidden.get(key) is not True for key in required_true):
        raise DecisionV2FailureDiagnosisContractError("FAILURE_DIAGNOSIS_FORBIDDEN_GUARD_CHANGED")
    return path
