from __future__ import annotations

import hashlib
import json

import pytest

from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_runtime_lineage_v2 import (
    build_runtime_lineage_v2,
    verify_runtime_lineage_v2,
)


def _lineage(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "role": "PREPARED_EXECUTION",
        "implementation_branch": "runtime/paper",
        "implementation_commit": "a" * 40,
        "config_sha256": "b" * 64,
        "entrypoint_sha256": "c" * 64,
        "artifacts": {
            "score": {"path": "score.json", "sha256": "d" * 64},
        },
        "contracts": {"execution": "V4_X1_EXECUTION_V1"},
    }
    values.update(overrides)
    return build_runtime_lineage_v2(**values)  # type: ignore[arg-type]


def test_runtime_lineage_v2_is_hash_bound_and_operationally_bound() -> None:
    payload = _lineage()
    verified = verify_runtime_lineage_v2(payload)
    assert verified["binding_status"] == "BOUND"
    assert verified["lineage_sha256"] == payload["lineage_sha256"]


def test_runtime_lineage_v2_rejects_tampered_artifact_hash() -> None:
    payload = _lineage()
    tampered = dict(payload)
    tampered_artifacts = dict(tampered["artifacts"])
    tampered_artifacts["score"] = {"path": "score.json", "sha256": "e" * 64}
    tampered["artifacts"] = tampered_artifacts
    with pytest.raises(DecisionV1Error, match="HASH_MISMATCH"):
        verify_runtime_lineage_v2(tampered)


def test_runtime_lineage_v2_rejects_hash_valid_binding_status_drift() -> None:
    payload = _lineage()
    tampered = dict(payload)
    tampered["binding_status"] = "LOCAL_UNBOUND"
    body = dict(tampered)
    body.pop("lineage_sha256")
    tampered["lineage_sha256"] = hashlib.sha256(
        (
            json.dumps(
                body,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            + "\n"
        ).encode()
    ).hexdigest()

    with pytest.raises(DecisionV1Error, match="PAYLOAD_NOT_CANONICAL"):
        verify_runtime_lineage_v2(tampered)


def test_runtime_lineage_v2_allows_explicit_local_unbound_unit_mode() -> None:
    payload = _lineage(
        implementation_branch=None,
        implementation_commit=None,
        config_sha256=None,
    )
    assert payload["binding_status"] == "LOCAL_UNBOUND"
    assert verify_runtime_lineage_v2(payload)["binding_status"] == "LOCAL_UNBOUND"
