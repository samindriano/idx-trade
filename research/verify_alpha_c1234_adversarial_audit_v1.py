"""Independent verifier for the C1/C2/C4 adversarial structural audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_LABELS = {"C1", "C2", "C4"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    checks["status_pass_structural_only"] = result.get("status") == "PASS_STRUCTURAL_ONLY"
    checks["no_outcome_access"] = result.get("outcome_accessed") is False
    checks["no_target_access"] = result.get("target_accessed") is False
    checks["no_provider_access"] = result.get("provider_accessed") is False
    checks["no_incumbent_access"] = result.get("incumbent_score_accessed") is False
    checks["no_candidate_id_created"] = result.get("candidate_id_created") is False
    checks["all_structural_checks_pass"] = all(result.get("checks", {}).values())
    checks["candidate_set_exact"] = set(result.get("candidate_checks", {})) == EXPECTED_LABELS
    checks["listing_age_set_exact"] = set(result.get("listing_age_exposure", {})) == EXPECTED_LABELS
    checks["identity_pit_limits_explicit"] = (
        result.get("interpretation", {}).get("corporate_action_basis_certified") is False
        and result.get("interpretation", {}).get("historical_pit_certified") is False
    )
    if not all(checks.values()):
        raise SystemExit(json.dumps({"status": "FAIL", "checks": checks}, indent=2))
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
