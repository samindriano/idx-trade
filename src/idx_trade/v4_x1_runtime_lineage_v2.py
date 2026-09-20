"""Hash-bound implementation/config/artifact lineage for paper envelopes."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from .v4_x1_decision_v1_contract import DecisionV1Error


RUNTIME_LINEAGE_SCHEMA = "idx_trade_runtime_lineage_v2"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _canonical_hash(value: object) -> str:
    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _optional_sha(value: object, code: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not _SHA_RE.fullmatch(text):
        raise DecisionV1Error(code)
    return text


def _optional_commit(value: object, code: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not _COMMIT_RE.fullmatch(text):
        raise DecisionV1Error(code)
    return text


def build_runtime_lineage_v2(
    *,
    role: str,
    implementation_branch: str | None,
    implementation_commit: str | None,
    config_sha256: str | None,
    entrypoint_sha256: str | None,
    artifacts: Mapping[str, Mapping[str, Any]],
    contracts: Mapping[str, str],
) -> dict[str, Any]:
    normalized_role = str(role).strip().upper()
    if normalized_role not in {"PREPARED_EXECUTION", "EXECUTION_RESULT"}:
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_ROLE_INVALID")
    branch = None if implementation_branch is None else str(implementation_branch).strip()
    if implementation_branch is not None and not branch:
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_BRANCH_INVALID")
    commit = _optional_commit(implementation_commit, "RUNTIME_LINEAGE_V2_COMMIT_INVALID")
    config_sha = _optional_sha(config_sha256, "RUNTIME_LINEAGE_V2_CONFIG_SHA_INVALID")
    entrypoint_sha = _optional_sha(
        entrypoint_sha256,
        "RUNTIME_LINEAGE_V2_ENTRYPOINT_SHA_INVALID",
    )
    if (implementation_branch is None) != (commit is None):
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_IMPLEMENTATION_BINDING_INCOMPLETE")
    normalized_artifacts: dict[str, dict[str, Any]] = {}
    for name, raw in sorted(artifacts.items()):
        if not isinstance(raw, Mapping):
            raise DecisionV1Error("RUNTIME_LINEAGE_V2_ARTIFACT_INVALID")
        item = dict(raw)
        if "sha256" in item and item["sha256"] is not None:
            item["sha256"] = _optional_sha(
                item["sha256"],
                "RUNTIME_LINEAGE_V2_ARTIFACT_SHA_INVALID",
            )
        normalized_artifacts[str(name)] = item
    normalized_contracts: dict[str, str] = {}
    for name, value in sorted(contracts.items()):
        text = str(value).strip()
        if not text:
            raise DecisionV1Error("RUNTIME_LINEAGE_V2_CONTRACT_ID_INVALID")
        normalized_contracts[str(name)] = text
    body: dict[str, Any] = {
        "schema_version": RUNTIME_LINEAGE_SCHEMA,
        "role": normalized_role,
        "binding_status": (
            "BOUND"
            if branch is not None and commit is not None and config_sha is not None
            else "LOCAL_UNBOUND"
        ),
        "implementation_branch": branch,
        "implementation_commit": commit,
        "config_sha256": config_sha,
        "entrypoint_sha256": entrypoint_sha,
        "artifacts": normalized_artifacts,
        "contracts": normalized_contracts,
    }
    body["lineage_sha256"] = _canonical_hash(body)
    return body


def verify_runtime_lineage_v2(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_REQUIRED")
    payload = dict(value)
    if payload.get("schema_version") != RUNTIME_LINEAGE_SCHEMA:
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_SCHEMA_MISMATCH")
    role = str(payload.get("role") or "").upper()
    if role not in {"PREPARED_EXECUTION", "EXECUTION_RESULT"}:
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_ROLE_INVALID")
    declared = str(payload.pop("lineage_sha256") or "").lower()
    if not _SHA_RE.fullmatch(declared) or _canonical_hash(payload) != declared:
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_HASH_MISMATCH")
    try:
        normalized = build_runtime_lineage_v2(
            role=payload.get("role"),
            implementation_branch=payload.get("implementation_branch"),
            implementation_commit=payload.get("implementation_commit"),
            config_sha256=payload.get("config_sha256"),
            entrypoint_sha256=payload.get("entrypoint_sha256"),
            artifacts=payload.get("artifacts"),
            contracts=payload.get("contracts"),
        )
    except (DecisionV1Error, TypeError) as exc:
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_PAYLOAD_INVALID") from exc
    normalized.pop("lineage_sha256", None)
    if normalized != payload:
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_PAYLOAD_NOT_CANONICAL")
    _optional_commit(payload.get("implementation_commit"), "RUNTIME_LINEAGE_V2_COMMIT_INVALID")
    _optional_sha(payload.get("config_sha256"), "RUNTIME_LINEAGE_V2_CONFIG_SHA_INVALID")
    _optional_sha(payload.get("entrypoint_sha256"), "RUNTIME_LINEAGE_V2_ENTRYPOINT_SHA_INVALID")
    if payload.get("binding_status") == "BOUND":
        if not payload.get("implementation_branch") or not payload.get("implementation_commit"):
            raise DecisionV1Error("RUNTIME_LINEAGE_V2_BOUND_IDENTITY_INCOMPLETE")
        if not payload.get("config_sha256"):
            raise DecisionV1Error("RUNTIME_LINEAGE_V2_BOUND_CONFIG_MISSING")
    elif payload.get("binding_status") != "LOCAL_UNBOUND":
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_BINDING_STATUS_INVALID")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_ARTIFACTS_MISSING")
    for raw in artifacts.values():
        if not isinstance(raw, Mapping):
            raise DecisionV1Error("RUNTIME_LINEAGE_V2_ARTIFACT_INVALID")
        _optional_sha(raw.get("sha256"), "RUNTIME_LINEAGE_V2_ARTIFACT_SHA_INVALID")
    contracts = payload.get("contracts")
    if not isinstance(contracts, Mapping) or not contracts:
        raise DecisionV1Error("RUNTIME_LINEAGE_V2_CONTRACTS_MISSING")
    payload["lineage_sha256"] = declared
    return payload


__all__ = [
    "RUNTIME_LINEAGE_SCHEMA",
    "build_runtime_lineage_v2",
    "verify_runtime_lineage_v2",
]
