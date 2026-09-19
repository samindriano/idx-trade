"""Independent structural verifier for the BBCA price-basis audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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
    checks: dict[str, bool] = {}
    scope = audit.get("scope", {})
    checks["status_exact"] = audit.get("status") == "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED"
    checks["scope_outcome_false"] = scope.get("outcome_accessed") is False
    checks["scope_model_false"] = scope.get("model_scoring") is False
    checks["scope_canonical_false"] = scope.get("canonical_write") is False
    checks["scope_cloud_false"] = scope.get("cloud_or_r2_write") is False
    checks["scope_network_false"] = scope.get("network_used") is False
    checks["scope_feature_false"] = scope.get("feature_or_candidate_created") is False
    checks["sources_present"] = set(audit.get("sources", {})) == {"tradingview", "investing", "idx"}
    checks["tradingview_rows_exact"] = audit.get("sources", {}).get("tradingview", {}).get("rows") == 6356
    checks["investing_rows_exact"] = audit.get("sources", {}).get("investing", {}).get("rows") == 2065
    checks["idx_rows_exact"] = audit.get("sources", {}).get("idx", {}).get("rows") == 1616
    tv_idx = audit.get("comparisons", {}).get("tradingview_vs_idx", {})
    inv_idx = audit.get("comparisons", {}).get("investing_vs_idx", {})
    tv_inv = audit.get("comparisons", {}).get("tradingview_vs_investing", {})
    checks["tv_idx_overlap_exact"] = tv_idx.get("overlap_rows") == 1615
    checks["tv_idx_price_exact_exact"] = tv_idx.get("exact_counts", {}).get("close") == 1182
    checks["tv_idx_all_field_exact_exact"] = tv_idx.get("exact_all_compare_fields") == 1164
    checks["investing_idx_overlap_exact"] = inv_idx.get("overlap_rows") == 1568
    checks["investing_idx_no_exact_price"] = inv_idx.get("exact_counts", {}).get("close") == 0
    checks["investing_idx_no_exact_all_fields"] = inv_idx.get("exact_all_compare_fields") == 0
    checks["tv_investing_overlap_exact"] = tv_inv.get("overlap_rows") == 1901
    blocks = audit.get("tradingview_idx_basis", {}).get("price_ratio_blocks", [])
    checks["tv_price_basis_two_blocks"] = blocks == [
        {"from": "2020-01-02", "to": "2021-10-12", "label": "5.0"},
        {"from": "2021-10-13", "to": "2026-09-18", "label": "1.0"},
    ]
    changes = audit.get("tradingview_idx_basis", {}).get("idx_listed_share_changes", [])
    checks["listed_share_five_change_observed"] = changes == [
        {
            "date": "2021-10-13",
            "previous_date": "2021-10-12",
            "previous_listed_shares": 24408459900,
            "listed_shares": 122042299500,
            "ratio": 5.0,
        }
    ]
    checks["interpretation_present"] = len(audit.get("interpretation", [])) >= 4
    checks["code_hash_present"] = isinstance(audit.get("code_sha256"), str) and len(audit["code_sha256"]) == 64
    result = {
        "schema": "idx_trade_alpha_bbca_price_basis_reconciliation_verification_v1",
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
