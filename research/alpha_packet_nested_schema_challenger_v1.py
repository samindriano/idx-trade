"""Research-only nested-schema challenger for the authority packet.

The current packet verifier is intentionally left unchanged. This challenger
defines a reviewed-in-this-lane draft allowlist for the packet's current
schema, then compares strict results with the existing verifier on synthetic
unknown-field mutations. It never reads protected outcomes or provider data.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGING_MARKER = "idx-alpha-available-data-staging-20260919"
PACKET_PATH = ROOT / "research_knowledge" / "data_authority_packet_v1.json"

ROOT_KEYS = {
    "schema_version",
    "status",
    "scope",
    "lane",
    "eligibility_policy",
    "taxonomy",
    "capability_verdicts",
    "candidate_matrix",
    "bounded_admission",
    "verifier_audit",
    "firewall_audit",
    "reentry_requirements",
    "remaining_authority_decisions",
    "unavailable_authority",
    "evidence_refs",
}
LANE_KEYS = {
    "branch",
    "canonical_mutation",
    "cloud_access",
    "head_at_packet_creation",
    "protected_boundary",
    "provider_access",
    "worktree",
}
ELIGIBILITY_KEYS = {
    "authoritative_rule",
    "counterfactual_scenario",
    "implementation_interpretation",
    "prose_interpretation",
    "provenance_timeline",
    "semantics",
    "status",
}
ELIGIBILITY_INTERPRETATION_KEYS = {
    "source",
    "window",
    "minimum_finite_observations",
}
ELIGIBILITY_IMPLEMENTATION_KEYS = {
    "source",
    "window",
    "count_min_periods",
    "median_min_periods",
}
ELIGIBILITY_SEMANTICS_KEYS = {
    "min_periods_60",
    "minimum_20",
    "policy_selection",
    "security_warmup_60",
}
PROVENANCE_KEYS = {"commit", "finding", "role", "timestamp"}
TAXONOMY_KEYS = {
    "candidate_support",
    "common_support",
    "feature_finiteness",
    "feature_warmup",
    "listing_age_requirement",
    "model_training_eligibility",
    "population_eligibility",
    "portfolio_eligibility",
    "rolling_window_min_periods",
    "security_date_eligibility",
    "tradability",
}
TAXONOMY_VALUE_KEYS = {"reason", "status"}
CAPABILITY_KEYS = {
    "CA_BASIS",
    "ELIGIBILITY_POLICY",
    "FINANCIAL_PIT",
    "FIREWALL_STRENGTH",
    "ISSUER_IDENTITY",
    "LIQUIDITY_PIT",
    "POPULATION_AUTHORITY",
    "SECURITY_IDENTITY",
    "SURVIVORSHIP",
    "VERIFIER_STRENGTH",
}
CANDIDATE_KEYS = {"C1", "C2", "C3", "C4", "H-EXC", "H-LIQ", "H-VOL"}
CANDIDATE_VALUE_KEYS = {"predictive_reentry", "reason", "required", "state"}
REQUIRED_KEYS_BY_CANDIDATE = {
    "C1": {"ca_basis", "executable_capacity", "financial_pit", "issuer_identity", "liquidity_pit", "population", "price_pit", "security_identity"},
    "C2": {"ca_basis", "executable_capacity", "financial_pit", "issuer_identity", "liquidity_pit", "population", "price_pit", "security_identity"},
    "C3": {"common_support", "financial_pit", "issuer_identity", "population", "revision_vintage", "security_identity"},
    "C4": {"ca_basis", "executable_capacity", "financial_pit", "issuer_identity", "liquidity_pit", "population", "price_pit", "security_identity"},
    "H-LIQ": {"ca_basis", "executable_capacity", "liquidity_pit", "population", "price_pit", "security_identity"},
    "H-VOL": {"ca_basis", "executable_capacity", "population", "price_pit", "security_identity"},
    "H-EXC": {"ca_basis", "population", "price_pit", "security_identity"},
}
H_EXC_EXTRA_KEYS = {"subforms"}
H_EXC_SUBFORM_KEYS = {"H-EXC-01", "H-EXC-02"}
BOUNDED_KEYS = {
    "basis",
    "missing_for_defensible_subset",
    "predictive_research",
    "selection_rule",
    "structural_research",
}
VERIFIER_KEYS = {
    "independent_constructor_replay",
    "knowledge_base_verifier",
    "lane_10_of_10",
    "limitations",
    "packet_65_of_65",
    "synthetic_mutation_audit",
}
FIREWALL_KEYS = {
    "authority_packet_allowlist",
    "existing_firewall",
    "production_target_access",
    "synthetic_disguised_field",
    "synthetic_obvious_forbidden_payload",
    "synthetic_unexpected_schema_column",
}
REENTRY_KEYS = {"before_any_protected_access", "protected_boundary", "ready_for_reentry_packet"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_current_verifier():
    path = ROOT / "research" / "verify_alpha_data_authority_packet_v1.py"
    spec = importlib.util.spec_from_file_location("current_packet_verifier", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def exact_keys(value: Any, expected: set[str], path: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{path}:not_object"]
    actual = set(value)
    errors: list[str] = []
    for name in sorted(actual - expected):
        errors.append(f"{path}:unknown:{name}")
    for name in sorted(expected - actual):
        errors.append(f"{path}:missing:{name}")
    return errors


def strict_validate(packet: dict[str, Any]) -> dict[str, Any]:
    errors = exact_keys(packet, ROOT_KEYS, "root")
    if packet.get("schema_version") != "IDX_TRADE_DATA_AUTHORITY_PACKET_V1":
        errors.append("root:schema_version_mismatch")
    errors += exact_keys(packet.get("lane"), LANE_KEYS, "lane")
    eligibility = packet.get("eligibility_policy")
    errors += exact_keys(eligibility, ELIGIBILITY_KEYS, "eligibility_policy")
    if isinstance(eligibility, dict):
        errors += exact_keys(eligibility.get("prose_interpretation"), ELIGIBILITY_INTERPRETATION_KEYS, "eligibility_policy.prose_interpretation")
        errors += exact_keys(eligibility.get("implementation_interpretation"), ELIGIBILITY_IMPLEMENTATION_KEYS, "eligibility_policy.implementation_interpretation")
        errors += exact_keys(eligibility.get("semantics"), ELIGIBILITY_SEMANTICS_KEYS, "eligibility_policy.semantics")
        timeline = eligibility.get("provenance_timeline")
        if not isinstance(timeline, list):
            errors.append("eligibility_policy.provenance_timeline:not_list")
        else:
            for index, row in enumerate(timeline):
                errors += exact_keys(row, PROVENANCE_KEYS, f"eligibility_policy.provenance_timeline[{index}]")
    errors += exact_keys(packet.get("taxonomy"), TAXONOMY_KEYS, "taxonomy")
    taxonomy = packet.get("taxonomy")
    if isinstance(taxonomy, dict):
        for key in TAXONOMY_KEYS:
            errors += exact_keys(taxonomy.get(key), TAXONOMY_VALUE_KEYS, f"taxonomy.{key}")
    errors += exact_keys(packet.get("capability_verdicts"), CAPABILITY_KEYS, "capability_verdicts")
    errors += exact_keys(packet.get("candidate_matrix"), CANDIDATE_KEYS, "candidate_matrix")
    candidates = packet.get("candidate_matrix")
    if isinstance(candidates, dict):
        for key in CANDIDATE_KEYS:
            allowed = CANDIDATE_VALUE_KEYS | (H_EXC_EXTRA_KEYS if key == "H-EXC" else set())
            errors += exact_keys(candidates.get(key), allowed, f"candidate_matrix.{key}")
            value = candidates.get(key)
            if isinstance(value, dict):
                errors += exact_keys(value.get("required"), REQUIRED_KEYS_BY_CANDIDATE[key], f"candidate_matrix.{key}.required")
                if key == "H-EXC":
                    errors += exact_keys(value.get("subforms"), H_EXC_SUBFORM_KEYS, "candidate_matrix.H-EXC.subforms")
    errors += exact_keys(packet.get("bounded_admission"), BOUNDED_KEYS, "bounded_admission")
    errors += exact_keys(packet.get("verifier_audit"), VERIFIER_KEYS, "verifier_audit")
    errors += exact_keys(packet.get("firewall_audit"), FIREWALL_KEYS, "firewall_audit")
    errors += exact_keys(packet.get("reentry_requirements"), REENTRY_KEYS, "reentry_requirements")
    for list_key in ("remaining_authority_decisions", "unavailable_authority", "evidence_refs"):
        if not isinstance(packet.get(list_key), list):
            errors.append(f"{list_key}:not_list")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if STAGING_MARKER not in str(output):
        raise ValueError("refusing output outside the isolated alpha staging root")

    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    current_verifier, verifier_path = load_current_verifier()
    cases: list[dict[str, Any]] = []

    def record(name: str, mutated: dict[str, Any], expected_strict: str, expected_current: str | None = None) -> None:
        strict = strict_validate(mutated)
        current = current_verifier.validate(mutated, ROOT)
        cases.append(
            {
                "case": name,
                "strict_status": strict["status"],
                "strict_errors": strict["errors"],
                "current_verifier_status": current["status"],
                "expected_strict_status": expected_strict,
                "expected_current_verifier_status": expected_current,
                "expectation_met": strict["status"] == expected_strict
                and (expected_current is None or current["status"] == expected_current),
            }
        )

    record("baseline", copy.deepcopy(packet), "PASS", "PASS")
    nested = copy.deepcopy(packet)
    nested["candidate_matrix"]["C1"]["unexpected_safe_field"] = "fixture"
    record("unknown_candidate_nested_field", nested, "FAIL", "PASS")
    top_level = copy.deepcopy(packet)
    top_level["unexpected_top_level_field"] = "fixture"
    record("unknown_top_level_field", top_level, "FAIL", "FAIL")
    bounded = copy.deepcopy(packet)
    bounded["bounded_admission"]["unexpected_nested_field"] = "fixture"
    record("unknown_bounded_admission_field", bounded, "FAIL", "PASS")
    timeline = copy.deepcopy(packet)
    timeline["eligibility_policy"]["provenance_timeline"][0]["unexpected_field"] = "fixture"
    record("unknown_provenance_timeline_field", timeline, "FAIL", "PASS")
    missing = copy.deepcopy(packet)
    del missing["candidate_matrix"]["C3"]["required"]["revision_vintage"]
    record("missing_required_candidate_field", missing, "FAIL", "PASS")

    result = {
        "schema_version": "IDX_TRADE_PACKET_NESTED_SCHEMA_CHALLENGER_V1",
        "experiment_id": "TOOLING-041",
        "status": "PASS_NESTED_ALLOWLIST_CHALLENGE"
        if all(case["expectation_met"] for case in cases)
        else "FAIL_NESTED_ALLOWLIST_CHALLENGE",
        "scope": "OUTCOME_BLIND_SYNTHETIC_PACKET_FIXTURES_ONLY",
        "packet_path": str(PACKET_PATH),
        "packet_sha256": sha256_file(PACKET_PATH),
        "current_verifier_path": str(verifier_path),
        "current_verifier_sha256": sha256_file(verifier_path),
        "schema_policy": "DRAFT_RESEARCH_ALLOWLIST_NOT_INTEGRATED",
        "cases": cases,
        "trial_count": len(cases),
        "interpretation": [
            "The draft strict allowlist rejects unknown nested fields that the current verifier accepts.",
            "The draft strict allowlist rejects missing required nested fields.",
            "Unknown top-level fields remain rejected by both layers.",
            "This is a research proposal and does not change the production verifier.",
        ],
        "limitations": [
            "The allowlist is reviewed only within this isolated research lane.",
            "Value semantics, type ranges, and verifier-version freshness are not fully solved by key allowlisting.",
            "No provider, cloud, canonical, protected, or production state was accessed or changed.",
        ],
        "reopen_trigger": "Independent review and explicit adoption decision for a nested schema/version contract.",
    }
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] != "FAIL_NESTED_ALLOWLIST_CHALLENGE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
