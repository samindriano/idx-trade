"""Fail-closed structural verifier for the panel-depth source audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifact = json.loads(args.input.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    checks["status_exact"] = artifact.get("status") == "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED"
    scope = artifact.get("scope", {})
    for name in ("outcome_accessed", "target_accessed", "provider_accessed", "feature_created", "candidate_id_created", "canonical_mutation"):
        checks[f"scope_{name}_false"] = scope.get(name) is False
    manifest = artifact.get("manifest", {})
    checks["schema_exact"] = manifest.get("schema") == "idx_trade_alpha_panel_history_probe_v1"
    checks["retry_none"] = manifest.get("retry_policy") == "NONE"
    checks["source_count_exact"] = manifest.get("source_count") == 12
    checks["record_count_exact"] = manifest.get("record_count") == 12
    checks["manifest_safe_flags_false"] = manifest.get("all_safe_flags_false") is True
    symbols = artifact.get("symbols", [])
    checks["symbol_count_exact"] = len(symbols) == 12
    checks["expected_row_counts"] = all(item.get("rows") == (1059 if item.get("code") == "GOTO" else 1616) for item in symbols)
    checks["required_fields_present"] = all(item.get("missing_required_fields") == [] for item in symbols)
    checks["dates_valid_unique_descending"] = all(
        item.get("invalid_date_rows") == 0
        and item.get("duplicate_date_rows") == 0
        and item.get("descending_date_order") is True
        for item in symbols
    )
    checks["identity_fields_absent"] = all(item.get("identity_fields_absent") is True for item in symbols)
    checks["row_code_field_absent_as_observed"] = all(item.get("row_code_field_absent") is True for item in symbols)
    checks["arithmetic_invariants_exact"] = all(
        item.get("net_foreign_shares_exact_rows") == item.get("rows")
        and item.get("net_foreign_value_exact_rows") == item.get("rows")
        and item.get("high_ge_low_rows") == item.get("rows")
        and item.get("bid_le_offer_rows_or_not_applicable") == item.get("rows")
        for item in symbols
    )
    raw_checks = artifact.get("raw_hash_checks", [])
    checks["raw_hash_count_exact"] = len(raw_checks) == 12
    checks["raw_hashes_and_bytes_match"] = all(item.get("raw_exists") is True and item.get("hash_matches") is True and item.get("bytes_match") is True for item in raw_checks)
    parity = artifact.get("official_parity", [])
    checks["official_parity_count_exact"] = len(parity) == 24
    checks["official_shared_fields_exact"] = all(item.get("all_shared_fields_exact") is True for item in parity if item.get("panel_present") and item.get("official_present"))
    checks["official_missing_only_expected_goto_2020"] = sorted(
        (item.get("code"), item.get("date")) for item in parity if not item.get("panel_present") or not item.get("official_present")
    ) == [("GOTO", "2020-01-02")]
    duplicate = artifact.get("historical_duplicate_check", {})
    checks["historical_duplicate_checked"] = duplicate.get("checked") is True
    checks["historical_duplicate_exact"] = duplicate.get("exact_rowset_duplicate") is True and duplicate.get("intersection_rows") == 1616
    coverage = artifact.get("coverage", {})
    checks["coverage_counts_exact"] = coverage.get("official_calendar_rows") == 1260 and coverage.get("panel_depth_rows") == 18835 and coverage.get("panel_depth_symbols") == 12
    admission = artifact.get("admission", {})
    checks["feature_admission_closed"] = admission.get("feature_ready") is False and len(admission.get("reason", [])) >= 4
    checks["source_hashes_present"] = len(artifact.get("source_hashes", {})) >= 27
    result = {
        "audit": "VERIFY_ALPHA_PANEL_DEPTH_SOURCE_AUDIT_V1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "input": str(args.input),
        "scope": {
            "outcome_accessed": False,
            "target_accessed": False,
            "provider_accessed": False,
            "canonical_mutation": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
