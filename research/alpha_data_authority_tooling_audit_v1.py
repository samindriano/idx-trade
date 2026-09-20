"""Outcome-blind synthetic mutation audit for authority-package tooling.

The fixtures are created in a temporary directory and contain no production,
provider, target, outcome, or cloud data.  The audit records expected failures
as evidence that integrity controls fail closed, and records known gaps where
the current denylist-style firewall is intentionally not a semantic schema
allowlist.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_artifact(path: Path, code: Path, source: Path, manifest: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "code_sha256": sha256_file(code),
                "inputs": {"fixture": sha256_file(source)},
                "manifest_sha256": sha256_file(manifest),
                "scope": {"target_accessed": False, "provider_accessed": False},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    contract = load_module(
        "verify_alpha_research_artifact_contract_v1",
        ROOT / "research" / "verify_alpha_research_artifact_contract_v1.py",
    )
    firewall = load_module(
        "alpha_research_target_firewall_v1",
        ROOT / "research" / "alpha_research_target_firewall_v1.py",
    )
    packet_verifier = load_module(
        "verify_alpha_data_authority_packet_v1",
        ROOT / "research" / "verify_alpha_data_authority_packet_v1.py",
    )
    packet = json.loads(
        (ROOT / "research_knowledge" / "data_authority_packet_v1.json").read_text(encoding="utf-8")
    )

    with tempfile.TemporaryDirectory(prefix="idx-alpha-tooling-audit-") as temp:
        temp_root = Path(temp)
        code = temp_root / "safe_code.py"
        source = temp_root / "fixture.csv"
        manifest = temp_root / "fixture_manifest.json"
        artifact = temp_root / "fixture_artifact.json"
        code.write_text("value = 1\n", encoding="utf-8")
        source.write_text("ticker,date,value\nAAA,2026-01-01,1\n", encoding="utf-8")
        manifest.write_text("{\"schema\": \"fixture\"}\n", encoding="utf-8")
        write_artifact(artifact, code, source, manifest)

        def contract_result() -> dict[str, object]:
            return contract.verify(
                artifact,
                code,
                [f"fixture={source}"],
                manifest,
                True,
            )

        contract_cases: dict[str, dict[str, object]] = {
            "baseline": contract_result(),
        }
        original_artifact = artifact.read_text(encoding="utf-8")
        mutated = json.loads(original_artifact)
        mutated["code_sha256"] = "0" * 64
        artifact.write_text(json.dumps(mutated) + "\n", encoding="utf-8")
        contract_cases["corrupt_code_hash"] = contract_result()
        artifact.write_text(original_artifact, encoding="utf-8")

        mutated = json.loads(original_artifact)
        del mutated["manifest_sha256"]
        artifact.write_text(json.dumps(mutated) + "\n", encoding="utf-8")
        contract_cases["missing_manifest_hash"] = contract_result()
        artifact.write_text(original_artifact, encoding="utf-8")

        mutated = json.loads(original_artifact)
        mutated["inputs"]["fixture"] = "f" * 64
        artifact.write_text(json.dumps(mutated) + "\n", encoding="utf-8")
        contract_cases["corrupt_input_hash"] = contract_result()
        artifact.write_text(original_artifact, encoding="utf-8")

        safe_code = temp_root / "safe_code_again.py"
        safe_code.write_text("value = 2\n", encoding="utf-8")
        contract_cases["changed_code_without_rebind"] = contract.verify(
            artifact,
            safe_code,
            [f"fixture={source}"],
            manifest,
            True,
        )

        firewall_cases: dict[str, object] = {}
        safe_code_checks = firewall.code_checks(code)
        firewall_cases["safe_code"] = {
            "checks": safe_code_checks,
            "status": "PASS" if all(safe_code_checks.values()) else "FAIL",
        }
        network_code = temp_root / "network_code.py"
        network_code.write_text("import requests\nvalue = 1\n", encoding="utf-8")
        network_checks = firewall.code_checks(network_code)
        firewall_cases["network_import"] = {
            "checks": network_checks,
            "status": "PASS" if all(network_checks.values()) else "FAIL",
        }

        obvious_text = temp_root / "obvious.txt"
        obvious_text.write_text("h5_values = fixture\n", encoding="utf-8")
        obvious_checks = firewall.text_checks(obvious_text)
        firewall_cases["obvious_protected_token"] = {
            "checks": obvious_checks,
            "status": "PASS" if all(obvious_checks.values()) else "FAIL",
        }
        disguised_text = temp_root / "disguised.txt"
        disguised_text.write_text("future_ret5_value = fixture\n", encoding="utf-8")
        disguised_checks = firewall.text_checks(disguised_text)
        firewall_cases["disguised_field_known_gap"] = {
            "checks": disguised_checks,
            "status": "PASS" if all(disguised_checks.values()) else "FAIL",
            "interpretation": "Known gap: token-only text checks do not prove semantic protected-field absence.",
        }

        marker_json = temp_root / "marker.json"
        marker_json.write_text("{\"target_accessed\": true}\n", encoding="utf-8")
        marker_checks = firewall.json_checks(marker_json)
        firewall_cases["true_access_marker"] = {
            "checks": marker_checks,
            "status": "PASS" if all(marker_checks.values()) else "FAIL",
        }

        disguised_schema = temp_root / "disguised_schema.parquet"
        pq.write_table(
            pa.table({"ticker": ["AAA"], "future_ret5_value": [0.1], "secret_signal": [1.0]}),
            disguised_schema,
        )
        schema_checks = firewall.schema_checks(disguised_schema)
        firewall_cases["unexpected_schema_known_gap"] = {
            "checks": schema_checks,
            "status": "PASS" if all(schema_checks.values()) else "FAIL",
            "interpretation": "Known gap: denylist schema checks accept unexpected non-matching fields; an allowlist is still required.",
        }

    packet_cases: dict[str, object] = {
        "baseline": packet_verifier.validate(packet),
    }
    mutated = copy.deepcopy(packet)
    mutated["candidate_matrix"]["C5"] = {"state": "STRUCTURALLY_ADMISSIBLE"}
    packet_cases["candidate_injection"] = packet_verifier.validate(mutated)
    mutated = copy.deepcopy(packet)
    mutated["eligibility_policy"]["authoritative_rule"] = 20
    packet_cases["policy_selection"] = packet_verifier.validate(mutated)
    mutated = copy.deepcopy(packet)
    mutated["reentry_requirements"]["ready_for_reentry_packet"] = True
    packet_cases["reentry_opening"] = packet_verifier.validate(mutated)

    expected = {
        "contract_baseline_pass": contract_cases["baseline"]["status"] == "PASS",
        "contract_corrupt_code_hash_fails": contract_cases["corrupt_code_hash"]["status"] == "FAIL",
        "contract_missing_manifest_hash_fails": contract_cases["missing_manifest_hash"]["status"] == "FAIL",
        "contract_corrupt_input_hash_fails": contract_cases["corrupt_input_hash"]["status"] == "FAIL",
        "contract_changed_code_fails": contract_cases["changed_code_without_rebind"]["status"] == "FAIL",
        "firewall_safe_code_passes": firewall_cases["safe_code"]["status"] == "PASS",
        "firewall_network_import_fails": firewall_cases["network_import"]["status"] == "FAIL",
        "firewall_obvious_token_fails": firewall_cases["obvious_protected_token"]["status"] == "FAIL",
        "firewall_true_marker_fails": firewall_cases["true_access_marker"]["status"] == "FAIL",
        "packet_baseline_passes": packet_cases["baseline"]["status"] == "PASS",
        "packet_candidate_injection_fails": packet_cases["candidate_injection"]["status"] == "FAIL",
        "packet_policy_selection_fails": packet_cases["policy_selection"]["status"] == "FAIL",
        "packet_reentry_opening_fails": packet_cases["reentry_opening"]["status"] == "FAIL",
    }
    result = {
        "status": "PASS_EXPECTED_MUTATIONS_AND_RECORDED_GAPS" if all(expected.values()) else "FAIL",
        "scope": "OUTCOME_BLIND_SYNTHETIC_TOOLING_MUTATION_AUDIT",
        "expected_checks": expected,
        "artifact_contract_results": {
            name: {"status": value["status"], "checks": value["checks"]}
            for name, value in contract_cases.items()
        },
        "firewall_results": firewall_cases,
        "packet_allowlist_results": {
            name: {"status": value["status"], "checks": value["checks"]}
            for name, value in packet_cases.items()
        },
        "known_gaps": [
            "The current firewall is a hybrid denylist/static scan, not a semantic schema allowlist.",
            "A disguised protected-looking field can pass text/schema checks when its token is not on the denylist.",
            "The artifact verifier binds declared hashes and explicit paths but does not independently recompute feature formulas.",
            "The packet verifier validates packet shape and closure invariants; it is not evidence of source authority or predictive validity.",
        ],
        "no_provider_or_protected_access": True,
        "audit_code_sha256": sha256_file(Path(__file__)),
    }
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
