"""Independent verifier for the local market-context source audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    checks["status_exact"] = result.get("status") == "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED"
    scope = result.get("scope", {})
    for name in ("outcome_accessed", "target_accessed", "provider_accessed", "feature_created", "canonical_mutation"):
        checks[f"scope_{name}_false"] = scope.get(name) is False
    panel = result.get("panel", {})
    checks["panel_rows_positive"] = panel.get("rows", 0) > 0
    checks["panel_dates_exact"] = panel.get("dates") == 1260
    rows = result.get("rich_daily_crosschecks", [])
    checks["sample_date_count_exact"] = len(rows) == 3
    checks["index_parity_exact"] = all(row.get("index_parity", {}).get("all_fields_exact") is True for row in rows)
    checks["stock_parity_exact"] = all(row.get("stock_parity", {}).get("all_fields_exact") is True for row in rows)
    checks["stock_keys_unique"] = all(
        row.get("stock_quality", {}).get("duplicate_codes") == 0 for row in rows
    )
    checks["stock_dates_exact"] = all(
        row.get("stock_quality", {}).get("all_rows_same_date") is True for row in rows
    )
    by_date = {row.get("date"): row for row in rows}
    checks["2024_panel_overlap_complete"] = (
        by_date.get("2024-06-21", {}).get("stock_quality", {}).get("panel_ticker_coverage") == 1.0
    )
    checks["2026_panel_overlap_complete"] = (
        by_date.get("2026-07-31", {}).get("stock_quality", {}).get("panel_ticker_coverage") == 1.0
    )
    checks["2024_reconciliation_exact"] = (
        by_date.get("2024-06-21", {}).get("market_reconciliation", {}).get("status") == "EXACT"
    )
    checks["2026_reconciliation_exact"] = (
        by_date.get("2026-07-31", {}).get("market_reconciliation", {}).get("status") == "EXACT"
    )
    checks["2021_exception_explicit"] = (
        by_date.get("2021-01-04", {}).get("market_reconciliation", {}).get("status")
        == "LOCALIZED_SOURCE_ARITHMETIC_DISCREPANCY"
    )
    checks["digital_market_file_count"] = len(result.get("digital_monthly_blocks", {}).get("market", [])) == 3
    checks["digital_index_file_count"] = len(result.get("digital_monthly_blocks", {}).get("indices", [])) == 3
    checks["digital_index_close_complete"] = all(
        item.get("null_close_rows") == 0 for item in result.get("digital_monthly_blocks", {}).get("indices", [])
    )
    checks["daily_population_closed"] = result.get("admission", {}).get("daily_population_complete") is False
    checks["feature_admission_closed"] = result.get("admission", {}).get("feature_ready") is False
    checks["admission_reasons_present"] = len(result.get("admission", {}).get("reason", [])) >= 4
    status = "PASS" if all(checks.values()) else "FAIL"
    output = {
        "audit": "VERIFY_ALPHA_MARKET_CONTEXT_SOURCE_AUDIT_V1",
        "status": status,
        "checks": checks,
        "input": str(args.input),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
