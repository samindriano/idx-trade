"""Independent structural verifier for the C3 financial contract map."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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
    checks["no_candidate_id_created"] = result.get("candidate_id_created") is False
    contracts = result.get("contracts", {})
    required = {"quality_core", "growth_core", "quality_plus_yoy_revenue", "quality_plus_yoy_assets", "all_five"}
    checks["contract_set_exact"] = set(contracts) == required
    quality = contracts.get("quality_core", {})
    all_five = contracts.get("all_five", {})
    growth = contracts.get("growth_core", {})
    plus_revenue = contracts.get("quality_plus_yoy_revenue", {})
    plus_assets = contracts.get("quality_plus_yoy_assets", {})
    checks["quality_core_has_more_raw_finite_rows"] = quality.get("raw_finite_rows", 0) > all_five.get("raw_finite_rows", 0)
    checks["quality_core_has_more_final_rows"] = quality.get("frozen_final_rows", 0) > all_five.get("frozen_final_rows", 0)
    checks["growth_equals_all_five"] = (
        growth.get("raw_finite_rows") == all_five.get("raw_finite_rows")
        and growth.get("frozen_final_rows") == all_five.get("frozen_final_rows")
        and growth.get("frozen_dates_with_at_least_30_names") == all_five.get("frozen_dates_with_at_least_30_names")
    )
    checks["plus_yoy_revenue_equals_all_five"] = (
        plus_revenue.get("raw_finite_rows") == all_five.get("raw_finite_rows")
        and plus_revenue.get("frozen_final_rows") == all_five.get("frozen_final_rows")
    )
    checks["plus_yoy_assets_equals_all_five"] = (
        plus_assets.get("raw_finite_rows") == all_five.get("raw_finite_rows")
        and plus_assets.get("frozen_final_rows") == all_five.get("frozen_final_rows")
    )
    checks["interpretation_no_fill"] = result.get("interpretation", {}).get("no_missing_value_fill") is True
    checks["interpretation_no_forward_fill"] = result.get("interpretation", {}).get("no_forward_fill") is True
    checks["interpretation_no_provider_fallback"] = result.get("interpretation", {}).get("no_provider_fallback") is True
    if not all(checks.values()):
        raise SystemExit(json.dumps({"status": "FAIL", "checks": checks}, indent=2))
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
