"""Research-only verifier-result freshness challenger.

The current packet verifier is not modified. Synthetic wrapper records are
checked against a draft freshness contract requiring the current verifier and
packet hashes. The underlying packet is outcome-blind and unchanged in every
case; this isolates freshness from packet validity.
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
VERIFIER_PATH = ROOT / "research" / "verify_alpha_data_authority_packet_v1.py"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_current_verifier():
    spec = importlib.util.spec_from_file_location("current_packet_verifier", VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {VERIFIER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strict_freshness(record: dict[str, Any], expected: dict[str, str]) -> dict[str, Any]:
    required = {"schema_version", "verifier_code_sha256", "packet_sha256"}
    errors = sorted(required - set(record))
    if record.get("schema_version") != "IDX_TRADE_VERIFIER_RESULT_V1":
        errors.append("schema_version_mismatch")
    if record.get("verifier_code_sha256") != expected["verifier_code_sha256"]:
        errors.append("verifier_code_hash_mismatch")
    if record.get("packet_sha256") != expected["packet_sha256"]:
        errors.append("packet_hash_mismatch")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if STAGING_MARKER not in str(output):
        raise ValueError("refusing output outside the isolated alpha staging root")

    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    verifier = load_current_verifier()
    expected = {
        "verifier_code_sha256": sha256_file(VERIFIER_PATH),
        "packet_sha256": sha256_file(PACKET_PATH),
    }
    baseline = {
        "schema_version": "IDX_TRADE_VERIFIER_RESULT_V1",
        **expected,
    }
    cases = [("baseline", baseline, "PASS")]
    missing_verifier = copy.deepcopy(baseline)
    del missing_verifier["verifier_code_sha256"]
    cases.append(("missing_verifier_hash", missing_verifier, "FAIL"))
    stale_verifier = copy.deepcopy(baseline)
    stale_verifier["verifier_code_sha256"] = "0" * 64
    cases.append(("stale_verifier_hash", stale_verifier, "FAIL"))
    stale_packet = copy.deepcopy(baseline)
    stale_packet["packet_sha256"] = "1" * 64
    cases.append(("stale_packet_hash", stale_packet, "FAIL"))
    wrong_schema = copy.deepcopy(baseline)
    wrong_schema["schema_version"] = "IDX_TRADE_VERIFIER_RESULT_OLD"
    cases.append(("stale_result_schema", wrong_schema, "FAIL"))

    results = []
    for name, record, expected_status in cases:
        current_packet_result = verifier.validate(packet, ROOT)
        strict_result = strict_freshness(record, expected)
        results.append(
            {
                "case": name,
                "strict_status": strict_result["status"],
                "strict_errors": strict_result["errors"],
                "current_packet_validation_status": current_packet_result["status"],
                "expected_strict_status": expected_status,
                "expectation_met": strict_result["status"] == expected_status,
            }
        )

    result = {
        "schema_version": "IDX_TRADE_VERIFIER_FRESHNESS_CHALLENGER_V1",
        "experiment_id": "TOOLING-042",
        "status": "PASS_FRESHNESS_MUTATIONS_DETECTED"
        if all(row["expectation_met"] for row in results)
        else "FAIL_FRESHNESS_MUTATION_CHALLENGER",
        "scope": "OUTCOME_BLIND_SYNTHETIC_RESULT_WRAPPERS_ONLY",
        "packet_path": str(PACKET_PATH),
        "packet_sha256": expected["packet_sha256"],
        "verifier_path": str(VERIFIER_PATH),
        "verifier_code_sha256": expected["verifier_code_sha256"],
        "cases": results,
        "trial_count": len(results),
        "interpretation": [
            "The draft freshness contract rejects missing or stale verifier/packet hashes and stale result schema.",
            "The unchanged current packet remains valid in every synthetic wrapper case, isolating freshness from packet validity.",
            "The draft contract is not integrated into the current verifier.",
        ],
        "limitations": [
            "This does not prove historical PASS artifacts were actually produced by the claimed verifier.",
            "Freshness binding does not solve semantic schema or formula correctness by itself.",
            "No provider, cloud, canonical, protected, or production state was accessed or changed.",
        ],
        "reopen_trigger": "Independent review and explicit adoption of a versioned verifier-result contract.",
    }
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] != "FAIL_FRESHNESS_MUTATION_CHALLENGER" else 1


if __name__ == "__main__":
    raise SystemExit(main())
