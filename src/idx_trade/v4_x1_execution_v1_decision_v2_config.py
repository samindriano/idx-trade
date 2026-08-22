from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .decision_v2_minimal import DecisionV2Error

EXPECTED_EXECUTION_V1_DECISION_V2_ADAPTER_CONFIG_SHA256 = (
    "1bdd88e222579eb9728396bde759fb1f7338c7dda4ab3a42efdd46f20aba5f89"
)


def verify_execution_v1_decision_v2_adapter_config(config_path: str | Path) -> None:
    path = Path(config_path).expanduser().resolve()
    if not path.is_file():
        raise DecisionV2Error(f"EXECUTION_V1_DECISION_V2_ADAPTER_CONFIG_MISSING:{path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != EXPECTED_EXECUTION_V1_DECISION_V2_ADAPTER_CONFIG_SHA256:
        raise DecisionV2Error(
            "EXECUTION_V1_DECISION_V2_ADAPTER_CONFIG_SHA_MISMATCH:"
            f"{actual}!={EXPECTED_EXECUTION_V1_DECISION_V2_ADAPTER_CONFIG_SHA256}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema_version": "v4_x1_execution_v1_decision_v2_adapter_v1",
        "execution_rule": "V4_X1_EXECUTION_V1",
        "decision_rule": "V4_X1_DECISION_V2_MINIMAL_V1",
        "sizing_rule": "V4_X1_SIZING_V1",
        "decision_adapter_policy": "EXACT_VERIFIED_DECISION_V2_NO_RULE_ID_PROJECTION",
        "paper_state_session_rule": "EXACT_DECISION_SESSION_MATCH_REQUIRED",
        "shadow_paper_lineage_rule": (
            "DECISION_CURRENT_SHADOW_EQUALS_POSITIONS_MINUS_PENDING_SELLS_PLUS_PENDING_BUYS"
        ),
        "pending_buy_reversal": (
            "CANCEL_STALE_PENDING_BUY_AND_DO_NOT_SELL_NEVER_HELD_SHARES"
        ),
        "pending_sell_reversal": (
            "CANCEL_STALE_PENDING_SELL_AND_DO_NOT_BUY_ALREADY_HELD_SHARES"
        ),
        "paired_replacement_reversal": (
            "NEVER_HELD_REPLACEMENT_PEER_COUNTS_AS_ALREADY_RESOLVED"
        ),
        "sizing_math_changed": False,
        "execution_economics_changed": False,
        "open_semantics_changed": False,
        "corporate_action_semantics_changed": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise DecisionV2Error(
                f"EXECUTION_V1_DECISION_V2_ADAPTER_CONFIG_CONTRACT_CHANGED:{key}"
            )


__all__ = [
    "EXPECTED_EXECUTION_V1_DECISION_V2_ADAPTER_CONFIG_SHA256",
    "verify_execution_v1_decision_v2_adapter_config",
]
