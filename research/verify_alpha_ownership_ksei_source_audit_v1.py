"""Independent arithmetic and scope verifier for the ownership/KSEI audit."""

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
    snapshots = result.get("ksei_archive", {}).get("snapshots", [])
    checks["snapshot_count_exact"] = len(snapshots) == 8
    checks["snapshot_files_unique"] = len({row.get("file") for row in snapshots}) == len(snapshots)
    checks["snapshot_schema_exact"] = all(row.get("schema_exact") is True for row in snapshots)
    checks["equity_rows_positive"] = all(row.get("equity_rows", 0) > 0 for row in snapshots)
    checks["equity_codes_unique"] = all(
        row.get("equity_unique_codes") == row.get("equity_rows")
        and row.get("equity_duplicate_code_keys") == 0
        for row in snapshots
    )
    checks["equity_numeric_clean"] = all(
        row.get("equity_numeric_bad_rows") == 0
        and row.get("equity_negative_numeric_rows") == 0
        and row.get("equity_holder_total_gt_outstanding") == 0
        for row in snapshots
    )
    snapshot_dates = [date for row in snapshots for date in row.get("snapshot_dates", [])]
    checks["snapshot_dates_unique"] = len(snapshot_dates) == len(set(snapshot_dates)) == 8
    checks["profile_five_ticker_probe"] = result.get("company_profile_probe", {}).get("file_count") == 5
    checks["profile_no_explicit_free_float"] = not result.get("company_profile_probe", {}).get(
        "explicit_free_float_like_columns"
    )
    checks["admission_closed"] = result.get("admission", {}).get("daily_pit_feature_ready") is False
    checks["admission_reasons_present"] = len(result.get("admission", {}).get("reason", [])) >= 4
    status = "PASS" if all(checks.values()) else "FAIL"
    output = {
        "audit": "VERIFY_ALPHA_OWNERSHIP_KSEI_SOURCE_AUDIT_V1",
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
