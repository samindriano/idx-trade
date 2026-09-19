"""Independent verifier for the outcome-blind CA/price-basis audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CANDIDATES = {
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C4_path_efficiency_reversal_20_v1",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {
        "status_pass_structural_only": result.get("status") == "PASS_STRUCTURAL_ONLY",
        "all_audit_checks_pass": all(result.get("checks", {}).values()),
        "no_outcome_access": result.get("outcome_accessed") is False,
        "no_target_access": result.get("target_accessed") is False,
        "no_provider_access": result.get("provider_accessed") is False,
        "no_model_fit": result.get("model_fit") is False,
        "no_model_scoring": result.get("model_scoring") is False,
        "no_panel_mutation": result.get("panel_mutated") is False,
        "clean_refit_not_authorized": result.get("clean_refit_authorized") is False,
        "candidate_set_exact": set(result.get("candidate_exposure", {}).get("counterfactual_close_overlay_sensitivity", {})) == CANDIDATES,
        "overlay_panel_exactly_matches_remediated_close": (
            result.get("hlc_overlay_inventory", {})
            .get("panel_overlay_comparison", {})
            .get("panel_close_mismatch_rows") == 0
        ),
        "counterfactual_top30_unchanged": all(
            value.get("mean_top30_overlap") == 1.0
            and value.get("min_top30_overlap") == 1.0
            and value.get("rows_with_score_change") == 0
            and value.get("rows_with_rank_change") == 0
            for value in result.get("candidate_exposure", {}).get("counterfactual_close_overlay_sensitivity", {}).values()
        ),
        "pit_and_ca_admission_explicitly_false": (
            result.get("interpretation", {}).get("corporate_action_basis_admitted") is False
            and result.get("interpretation", {}).get("historical_pit_admitted") is False
        ),
    }
    if not all(checks.values()):
        raise SystemExit(json.dumps({"status": "FAIL", "checks": checks}, indent=2))
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
