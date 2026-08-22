import hashlib
from pathlib import Path

from idx_trade.v4_x1_execution_v1_decision_v2_config import (
    EXPECTED_EXECUTION_V1_DECISION_V2_ADAPTER_CONFIG_SHA256,
    verify_execution_v1_decision_v2_adapter_config,
)


def test_execution_v1_decision_v2_adapter_config_hash_and_contract():
    path = (
        Path(__file__).parents[1]
        / "config"
        / "v4_x1_execution_v1_decision_v2_adapter.json"
    )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        EXPECTED_EXECUTION_V1_DECISION_V2_ADAPTER_CONFIG_SHA256
    )
    verify_execution_v1_decision_v2_adapter_config(path)
