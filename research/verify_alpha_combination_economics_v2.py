"""Independent metadata verifier for the eligible-percentile replay."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_COMBINATIONS = {"C1_C2_EW", "C1_C4_EW", "C2_C4_EW", "C1_C2_C4_EW"}
EXPECTED_SCENARIOS = {"LOW", "BASE", "STRESS"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))
    budget = result.get("combination_budget", {})
    contract = result.get("percentile_contract", {})
    combinations = result.get("combinations", {})
    scenarios = result.get("friction_scenarios", {})
    checks: dict[str, bool] = {
        "status_pass_structural_only": result.get("status") == "PASS_STRUCTURAL_ONLY",
        "implementation_is_v2": result.get("implementation") == "alpha_combination_economics_v2_eligible_percentiles",
        "no_target_access": result.get("target_accessed") is False,
        "no_outcome_access": result.get("outcome_accessed") is False,
        "no_provider_access": result.get("provider_accessed") is False,
        "no_incumbent_access": result.get("incumbent_score_accessed") is False,
        "no_candidate_id_created": result.get("candidate_id_created") is False,
        "no_weight_optimization": budget.get("no_weight_optimization") is True,
        "no_new_candidate_ids": budget.get("no_new_candidate_ids") is True,
        "combination_set_exact": set(combinations) == EXPECTED_COMBINATIONS,
        "scenario_set_exact": set(scenarios) == EXPECTED_SCENARIOS,
        "eligible_percentile_contract": contract.get("universe") == "eligible_decision_universe=true rows only"
        and contract.get("grouping") == "date"
        and contract.get("non_eligible_percentile") is None,
        "all_combinations_have_600_top30_dates": all(
            values.get("top_k_dates", {}).get("30") == 600 for values in combinations.values()
        ),
        "all_combinations_have_friction_outputs": all(
            set(values.get("friction_burden_bps_per_nav", {})) == EXPECTED_SCENARIOS
            for values in combinations.values()
        ),
        "source_features_hash": result.get("source_hashes", {}).get("features") == sha256_file(args.features),
        "source_panel_hash": result.get("source_hashes", {}).get("panel") == sha256_file(args.panel),
        "source_sessions_hash": result.get("source_hashes", {}).get("official_sessions") == sha256_file(args.sessions),
        "code_hash": result.get("code_sha256") == sha256_file(args.code),
    }
    if not all(checks.values()):
        raise SystemExit(json.dumps({"status": "FAIL", "checks": checks}, indent=2))
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()

