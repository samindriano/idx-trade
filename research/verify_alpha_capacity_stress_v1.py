"""Independent verifier for the outcome-blind capacity proxy stress map."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_CANDIDATES = {"C1", "C2", "C3", "C4"}
EXPECTED_RATES = {"0.0025", "0.0050", "0.0100", "0.0200"}


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
    checks["candidate_set_exact"] = set(result.get("candidates", {})) == EXPECTED_CANDIDATES
    checks["rate_set_exact"] = {
        f"{float(rate):.4f}" for rate in result.get("participation_rates", [])
    } == EXPECTED_RATES
    checks["all_candidate_dates_present"] = all(
        values.get("top30_dates", 0) > 0 for values in result.get("candidates", {}).values()
    )
    checks["all_candidate_rate_maps_exact"] = all(
        set(values.get("capacity_proxy_idr_by_participation_rate", {})) == EXPECTED_RATES
        for values in result.get("candidates", {}).values()
    )
    checks["all_candidate_capacity_quantiles_have_counts"] = all(
        all(metric.get("count", 0) >= 0 for metric in values.get("capacity_proxy_idr_by_participation_rate", {}).values())
        for values in result.get("candidates", {}).values()
    )
    if not all(checks.values()):
        raise SystemExit(json.dumps({"status": "FAIL", "checks": checks}, indent=2))
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
