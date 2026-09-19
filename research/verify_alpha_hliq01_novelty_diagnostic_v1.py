"""Independent verifier for the H-LIQ-01 novelty diagnostic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_REFERENCES = {"turnover_level", "C2", "C1", "C4"}
EXPECTED_BUCKETS = {"1", "2", "3", "4"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))
    dependence = result.get("dependence", {})
    conditional = result.get("conditional_value_bucket_dependence", {})
    checks = {
        "status_pass_structural_only": result.get("status") == "PASS_STRUCTURAL_ONLY",
        "all_checks_pass": all(result.get("checks", {}).values()),
        "no_outcome_access": result.get("outcome_accessed") is False,
        "no_provider_access": result.get("provider_accessed") is False,
        "no_candidate_id": result.get("candidate_id_created") is False,
        "reference_set_exact": set(dependence) == EXPECTED_REFERENCES,
        "value_bucket_set_exact": set(conditional) == EXPECTED_BUCKETS,
        "predictive_claim_false": result.get("interpretation", {}).get("predictive_claim") is False,
        "candidate_admission_false": result.get("interpretation", {}).get("candidate_id_admission") is False,
    }
    if not all(checks.values()):
        raise SystemExit(json.dumps({"status": "FAIL", "checks": checks}, indent=2))
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
