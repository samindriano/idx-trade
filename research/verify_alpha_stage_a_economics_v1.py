"""Independent integrity verifier for the outcome-blind economics artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


CANDIDATES = {
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C3_financial_quality_growth_v1",
    "C4_path_efficiency_reversal_20_v1",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= 1e-9


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    checks["status_structural_only"] = artifact.get("status") == "PASS_STRUCTURAL_ONLY"
    checks["protocol_bound"] = artifact.get("protocol") == "2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1"
    checks["fixed_600_sessions"] = artifact.get("frozen_session_count") == 600
    checks["fixed_top30"] = artifact.get("top_n") == 30
    checks["outcome_not_accessed"] = artifact.get("outcome_accessed") is False
    checks["target_not_accessed"] = artifact.get("target_accessed") is False
    checks["provider_not_accessed"] = artifact.get("provider_accessed") is False
    checks["incumbent_not_accessed"] = artifact.get("incumbent_score_accessed") is False
    checks["source_classification_capability_only"] = artifact.get("source_classification") == "PARTIAL_FROZEN_ONLY_CAPABILITY_DIAGNOSTIC"
    checks["candidate_set_exact"] = set(artifact.get("candidate_metrics", {})) == CANDIDATES
    checks["features_hash_matches"] = artifact["source_hashes"]["features"] == sha256_file(args.features)
    checks["panel_hash_matches"] = artifact["source_hashes"]["panel"] == sha256_file(args.panel)
    checks["sessions_hash_matches"] = artifact["source_hashes"]["official_sessions"] == sha256_file(args.sessions)
    checks["code_hash_matches"] = artifact["code_sha256"] == sha256_file(args.code)

    friction = artifact["friction_contract"]
    checks["base_friction_formula"] = close(
        friction["base_matched_turnover_bps"],
        friction["buy_fee_bps"] + friction["sell_fee_bps"] + 2 * friction["slippage_bps_per_side"],
    )
    checks["sensitivity_friction_formula"] = close(
        friction["sensitivity_matched_turnover_bps"],
        friction["buy_fee_bps"] + friction["sell_fee_bps"] + 2 * (friction["slippage_bps_per_side"] + 25.0),
    )

    for candidate, metrics in artifact["candidate_metrics"].items():
        turnover = [
            metrics.get("one_way_turnover_mean"),
            metrics.get("one_way_turnover_median"),
            metrics.get("one_way_turnover_q95"),
            metrics.get("one_way_turnover_max"),
        ]
        checks[f"{candidate}_turnover_bounded"] = all(value is None or 0.0 <= float(value) <= 1.0 for value in turnover)
        checks[f"{candidate}_coverage_bounded"] = all(
            value is None or 0.0 <= float(value) <= 1.0
            for value in (
                metrics.get("top30_market_value_coverage"),
                metrics.get("top30_positive_market_value_coverage"),
                metrics.get("top10_ticker_slot_share"),
                metrics.get("largest_single_ticker_slot_share"),
            )
        )
        mean_turnover = metrics.get("one_way_turnover_mean")
        checks[f"{candidate}_base_cost_reconciles"] = (
            mean_turnover is None
            or close(metrics["base_friction_bps_mean_of_nav"], mean_turnover * friction["base_matched_turnover_bps"])
        )
        checks[f"{candidate}_sensitivity_cost_reconciles"] = (
            mean_turnover is None
            or close(metrics["sensitivity_friction_bps_mean_of_nav"], mean_turnover * friction["sensitivity_matched_turnover_bps"])
        )

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "artifact_sha256": sha256_file(args.artifact),
        "code_sha256": sha256_file(args.code),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
