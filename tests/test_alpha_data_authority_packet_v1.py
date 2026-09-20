from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "research" / "verify_alpha_data_authority_packet_v1.py"
SPEC = importlib.util.spec_from_file_location("verify_alpha_data_authority_packet_v1", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PACKET = json.loads(
    (Path(__file__).resolve().parents[1] / "research_knowledge" / "data_authority_packet_v1.json").read_text(encoding="utf-8")
)
REPO_ROOT = Path(__file__).resolve().parents[1]


def test_authority_packet_allowlist_passes() -> None:
    result = MODULE.validate(PACKET, REPO_ROOT)
    assert result["status"] == "PASS"
    assert all(result["checks"].values())


def test_extra_top_level_field_fails_closed() -> None:
    mutated = copy.deepcopy(PACKET)
    mutated["unexpected_field"] = "mutation"
    assert MODULE.validate(mutated, REPO_ROOT)["status"] == "FAIL"


def test_c5_injection_fails_candidate_allowlist() -> None:
    mutated = copy.deepcopy(PACKET)
    mutated["candidate_matrix"]["C5"] = {"state": "STRUCTURALLY_ADMISSIBLE"}
    assert MODULE.validate(mutated, REPO_ROOT)["status"] == "FAIL"


def test_policy_selection_and_reentry_opening_fail_closed() -> None:
    mutated = copy.deepcopy(PACKET)
    mutated["eligibility_policy"]["authoritative_rule"] = 20
    mutated["reentry_requirements"]["ready_for_reentry_packet"] = True
    assert MODULE.validate(mutated, REPO_ROOT)["status"] == "FAIL"


def test_protected_key_mutation_fails_closed() -> None:
    mutated = copy.deepcopy(PACKET)
    mutated["candidate_matrix"]["C1"]["h5_value"] = "fixture"
    assert MODULE.validate(mutated, REPO_ROOT)["status"] == "FAIL"


def test_missing_evidence_reference_fails_closed() -> None:
    mutated = copy.deepcopy(PACKET)
    mutated["evidence_refs"].append("research_knowledge/missing_fixture.json")
    assert MODULE.validate(mutated, REPO_ROOT)["status"] == "FAIL"
