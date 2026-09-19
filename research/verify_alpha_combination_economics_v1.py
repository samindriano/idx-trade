"""Independent verifier for the outcome-blind combination/economics artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_COMBINATIONS = {"C1_C2_EW", "C1_C4_EW", "C2_C4_EW", "C1_C2_C4_EW"}
EXPECTED_SCENARIOS = {"LOW", "BASE", "STRESS"}


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
    budget = result.get("combination_budget", {})
    checks["no_weight_optimization"] = budget.get("no_weight_optimization") is True
    checks["budget_has_no_new_candidate_ids"] = budget.get("no_new_candidate_ids") is True
    combinations = result.get("combinations", {})
    checks["combination_set_exact"] = set(combinations) == EXPECTED_COMBINATIONS
    scenarios = result.get("friction_scenarios", {})
    checks["friction_scenario_set_exact"] = set(scenarios) == EXPECTED_SCENARIOS
    checks["scenario_costs_exact"] = all(
        values.get("matched_turnover_bps")
        == values.get("buy_fee_bps")
        + values.get("sell_fee_bps")
        + 2.0 * values.get("slippage_bps_per_side")
        for values in scenarios.values()
    )
    checks["all_combinations_have_600_top30_dates"] = all(
        values.get("top_k_dates", {}).get("30") == 600
        for values in combinations.values()
    )
    checks["all_combinations_have_friction_outputs"] = all(
        set(values.get("friction_burden_bps_per_nav", {})) == EXPECTED_SCENARIOS
        for values in combinations.values()
    )
    checks["all_combinations_have_component_overlap"] = all(
        values.get("top30_common_component_dates") == 600
        and set(values.get("top30_component_overlap", {}))
        == set(values.get("components", []))
        for values in combinations.values()
    )
    if not all(checks.values()):
        raise SystemExit(json.dumps({"status": "FAIL", "checks": checks}, indent=2))
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
