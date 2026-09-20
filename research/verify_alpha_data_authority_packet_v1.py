"""Fail-closed allowlist verifier for the durable data-authority packet."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TOP_LEVEL = {
    "schema_version", "status", "scope", "lane", "eligibility_policy", "taxonomy",
    "capability_verdicts", "candidate_matrix", "bounded_admission", "verifier_audit",
    "firewall_audit", "reentry_requirements", "remaining_authority_decisions",
    "unavailable_authority", "evidence_refs",
}
CANDIDATES = {"C1", "C2", "C3", "C4", "H-LIQ", "H-VOL", "H-EXC"}
ALLOWED_STATES = {"BLOCKED", "STRUCTURALLY_ADMISSIBLE", "READY_FOR_REENTRY_PACKET", "NOT_APPLICABLE"}
ALLOWED_EVIDENCE_PREFIXES = ("docs/", "research/", "research_knowledge/", "src/", "tests/")
FORBIDDEN_KEY_PATTERNS = (
    r"(?i)(?:h5|h10|target|forward_return|realized_return|pnl|rank_ic|icir).*value",
    r"(?i)(?:protected|hidden).*(?:array|payload|outcome)",
)


def _scan_keys(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{path}.{key}" if path else key
            if any(re.search(pattern, key) for pattern in FORBIDDEN_KEY_PATTERNS):
                hits.append(current)
            hits.extend(_scan_keys(child, current))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_scan_keys(child, f"{path}[{index}]"))
    return hits


def validate(payload: dict[str, Any], evidence_root: Path | None = None) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["top_level_allowlist"] = set(payload) == TOP_LEVEL
    checks["schema"] = payload.get("schema_version") == "IDX_TRADE_DATA_AUTHORITY_PACKET_V1"
    checks["blocked_status"] = payload.get("status") == "BLOCKED_PRE_ADMISSION"
    checks["policy_missing"] = payload.get("eligibility_policy", {}).get("status") == "ELIGIBILITY_POLICY_AUTHORITY_MISSING"
    checks["policy_not_selected"] = payload.get("eligibility_policy", {}).get("authoritative_rule") is None
    checks["protected_boundary_closed"] = payload.get("lane", {}).get("protected_boundary") == "CLOSED"
    checks["no_canonical_mutation"] = payload.get("lane", {}).get("canonical_mutation") is False
    checks["no_provider_access"] = payload.get("lane", {}).get("provider_access") is False
    checks["no_cloud_access"] = payload.get("lane", {}).get("cloud_access") is False
    checks["candidate_allowlist"] = set(payload.get("candidate_matrix", {})) == CANDIDATES
    checks["candidate_states_valid"] = all(
        isinstance(row, dict) and row.get("state") in ALLOWED_STATES
        for row in payload.get("candidate_matrix", {}).values()
    )
    checks["no_ready_candidate"] = not any(
        row.get("state") == "READY_FOR_REENTRY_PACKET"
        for row in payload.get("candidate_matrix", {}).values()
        if isinstance(row, dict)
    )
    checks["reentry_closed"] = payload.get("reentry_requirements", {}).get("ready_for_reentry_packet") is False
    checks["evidence_refs_nonempty"] = isinstance(payload.get("evidence_refs"), list) and bool(payload["evidence_refs"])
    checks["evidence_refs_relative"] = all(
        isinstance(ref, str) and ref.startswith(ALLOWED_EVIDENCE_PREFIXES) and ".." not in ref
        for ref in payload.get("evidence_refs", [])
    )
    root = evidence_root.resolve() if evidence_root is not None else Path.cwd().resolve()
    refs = payload.get("evidence_refs", [])
    checks["evidence_refs_exist"] = checks["evidence_refs_relative"] and all(
        (root / ref).is_file() for ref in refs if isinstance(ref, str)
    )
    counterfactual_ref = payload.get("eligibility_policy", {}).get("counterfactual_scenario")
    checks["counterfactual_ref_relative"] = (
        isinstance(counterfactual_ref, str)
        and counterfactual_ref.startswith(ALLOWED_EVIDENCE_PREFIXES)
        and ".." not in counterfactual_ref
    )
    checks["counterfactual_ref_exists"] = checks["counterfactual_ref_relative"] and (root / counterfactual_ref).is_file()
    forbidden_keys = _scan_keys(payload)
    checks["protected_key_allowlist"] = not forbidden_keys
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "forbidden_keys": forbidden_keys}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.packet.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("packet root must be an object")
    result = validate(payload, args.packet.resolve().parents[1])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
