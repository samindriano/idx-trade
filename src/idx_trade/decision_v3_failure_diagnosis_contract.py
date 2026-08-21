from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PREREG_RELATIVE_PATH = Path("docs/specs/decision_v3_failure_mechanism_diagnosis_v1.json")
EXPECTED_PREREG_CANONICAL_SHA256 = (
    "3a72bf9de9edd7181f15d9cd6bf50d590828407704ded426cb13586f3a89fd03"
)
EXPECTED_STATUS = "FROZEN_BEFORE_DIAGNOSIS_IMPLEMENTATION"


class DecisionV3FailureDiagnosisContractError(RuntimeError):
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
        raise DecisionV3FailureDiagnosisContractError("V3_FAILURE_DIAGNOSIS_PREREG_MISSING")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3FailureDiagnosisContractError("V3_FAILURE_DIAGNOSIS_PREREG_INVALID") from exc
    if not isinstance(payload, dict):
        raise DecisionV3FailureDiagnosisContractError("V3_FAILURE_DIAGNOSIS_PREREG_NOT_OBJECT")
    actual = canonical_json_sha256(payload)
    if actual != EXPECTED_PREREG_CANONICAL_SHA256:
        raise DecisionV3FailureDiagnosisContractError(
            f"V3_FAILURE_DIAGNOSIS_PREREG_SHA_MISMATCH:{actual}!={EXPECTED_PREREG_CANONICAL_SHA256}"
        )
    if payload.get("status") != EXPECTED_STATUS:
        raise DecisionV3FailureDiagnosisContractError("V3_FAILURE_DIAGNOSIS_PREREG_STATUS_CHANGED")
    if payload.get("execution_authorized") is not False:
        raise DecisionV3FailureDiagnosisContractError("V3_FAILURE_DIAGNOSIS_EXECUTION_FLAG_CHANGED")
    forbidden = payload.get("forbidden", {})
    required_true = {
        "decision_v3_structural_replay_rerun",
        "alternative_decision_rule_simulation",
        "alternative_threshold_test",
        "decision_parameter_sweep",
        "counterfactual_policy_simulation",
        "historical_alpha_source_access",
        "realized_returns",
        "historical_pnl",
        "protected_or_fresh_forward_outcomes",
        "model_refit_or_retune",
        "provider_or_network_calls",
        "successor_decision_implementation",
        "paper_or_live_activation",
    }
    if any(forbidden.get(key) is not True for key in required_true):
        raise DecisionV3FailureDiagnosisContractError("V3_FAILURE_DIAGNOSIS_FORBIDDEN_GUARD_CHANGED")
    return path
