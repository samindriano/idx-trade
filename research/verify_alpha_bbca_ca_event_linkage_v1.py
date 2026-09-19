"""Independent verifier for the BBCA CA event-linkage audit."""

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
    trace = audit.get("trace", {})
    ledgers = audit.get("ca_ledgers", {})
    scope = audit.get("scope", {})
    checks = {
        "status_exact": audit.get("status") == "PASS_STRUCTURAL_ONLY / EVENT_AUTHORITY_NOT_ESTABLISHED",
        "scope_outcome_false": scope.get("outcome_accessed") is False,
        "scope_model_false": scope.get("model_scoring") is False,
        "scope_canonical_false": scope.get("canonical_write") is False,
        "scope_cloud_false": scope.get("cloud_or_r2_write") is False,
        "scope_network_false": scope.get("network_used") is False,
        "scope_feature_false": scope.get("feature_or_candidate_created") is False,
        "scope_event_not_inferred": scope.get("event_semantics_inferred") is False,
        "trace_rows_exact": trace.get("rows") == 61,
        "trace_ticker_exact": trace.get("ticker_set") == ["BBCA"],
        "trace_date_range_exact": trace.get("date_from") == "2021-10-13" and trace.get("date_to") == "2022-01-07",
        "trace_split_zero_exact": trace.get("recorded_split_zero_rows") == 1 and trace.get("recorded_split_zero_dates") == ["2021-10-13"],
        "trace_hlc_exact": trace.get("panel_idx_hlc_exact_rows") == 61,
        "trace_h5_identity_false": trace.get("h5_exact_final_fit_identity_true_rows") == 0,
        "trace_h10_identity_false": trace.get("h10_exact_final_fit_identity_true_rows") == 0,
        "event_census_bbca_absent": ledgers.get("event_census_bbca_rows") == 0,
        "transition_ledger_bbca_absent": ledgers.get("transition_ledger_bbca_rows") == 0,
        "input_hashes_present": set(audit.get("source_hashes", {})) == {"bbca_trace", "event_census", "transition_ledger"},
        "code_hash_present": isinstance(audit.get("code_sha256"), str) and len(audit["code_sha256"]) == 64,
    }
    result = {
        "schema": "idx_trade_alpha_bbca_ca_event_linkage_verification_v1",
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
