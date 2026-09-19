"""Independent verifier for the panel-depth field contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIELDS = {
    "date", "open", "high", "low", "close", "previous", "change", "volume",
    "value", "frequency", "bid", "offer", "listedShares", "foreignBuyShares",
    "foreignSellShares", "netForeignShares", "foreignBuyValue", "foreignSellValue",
    "netForeignValue",
}


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = load(args.input)
    scope = audit.get("scope", {})
    source = audit.get("source", {})
    contract = audit.get("field_contract", {})
    structural = audit.get("structural_checks", {})
    future = audit.get("future_specification", {})
    foreign = structural.get("foreign_arithmetic", {})
    checks = {
        "status_exact": audit.get("status") == "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED",
        "scope_outcome_false": scope.get("outcome_accessed") is False,
        "scope_model_false": scope.get("model_scoring") is False,
        "scope_canonical_false": scope.get("canonical_write") is False,
        "scope_cloud_false": scope.get("cloud_or_r2_write") is False,
        "scope_network_false": scope.get("network_used") is False,
        "scope_feature_false": scope.get("feature_or_candidate_created") is False,
        "symbol_files_exact": source.get("symbol_file_count") == 12,
        "rows_exact": source.get("total_rows") == 18835,
        "all_fields_present": set(contract) == FIELDS,
        "row_identity_absent": source.get("row_level_identity_fields_present") is False,
        "row_pit_absent": source.get("row_level_pit_fields_present") is False,
        "row_revision_absent": source.get("row_level_revision_vintage_fields_present") is False,
        "row_ca_absent": source.get("row_level_ca_issuer_fields_present") is False,
        "foreign_shares_arithmetic_exact": foreign.get("netForeignShares_exact_rows") == 18835,
        "foreign_value_arithmetic_exact": foreign.get("netForeignValue_exact_rows") == 18835,
        "bid_offer_both_positive_exact": structural.get("bid_offer", {}).get("both_positive_rows") == 18604,
        "listed_transition_total_exact": structural.get("listed_share_transition_total") == 23,
        "future_spec_not_candidate": future.get("not_a_candidate") is True,
        "future_spec_status_exact": future.get("status") == "FUTURE_DATA / SOURCE_ADMISSION_BLOCKED / NOVELTY_UNKNOWN",
        "source_hashes_present": isinstance(audit.get("source_hashes"), dict) and len(audit["source_hashes"]) == 13,
        "code_hash_present": isinstance(audit.get("code_sha256"), str) and len(audit["code_sha256"]) == 64,
    }
    result = {
        "schema": "idx_trade_alpha_panel_depth_field_contract_verification_v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "input": str(args.input),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
