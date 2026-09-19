"""Independent structural checks for alpha_structural_lab_v1 output."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


CANDIDATES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C3_financial_quality_growth_v1",
    "C4_path_efficiency_reversal_20_v1",
]
TOP_KS = [10, 20, 30, 50]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def within(value: object, low: float, high: float) -> bool:
    return value is None or (isinstance(value, (int, float)) and low <= float(value) <= high)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--builder", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.audit.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    checks["status_structural_only"] = payload.get("status") == "PASS_STRUCTURAL_ONLY"
    checks["stage_present"] = payload.get("stage") == "C_F_G_K_L_M_OUTCOME_BLIND_STRUCTURAL_LAB"
    checks["outcome_accessed_false"] = payload.get("outcome_accessed") is False
    checks["target_accessed_false"] = payload.get("target_accessed") is False
    checks["provider_accessed_false"] = payload.get("provider_accessed") is False
    checks["incumbent_score_accessed_false"] = payload.get("incumbent_score_accessed") is False
    checks["candidate_ids_exact"] = payload.get("candidate_ids") == CANDIDATES
    checks["top_k_values_exact"] = payload.get("top_k_values") == TOP_KS
    checks["frozen_session_count"] = payload.get("frozen_session_count") == 600
    checks["builder_hash_matches"] = payload.get("code_sha256") == sha256_file(args.builder)
    source_hashes = payload.get("source_hashes", {})
    checks["features_hash_matches"] = source_hashes.get("features") == sha256_file(args.features)
    checks["panel_hash_matches"] = source_hashes.get("panel") == sha256_file(args.panel)
    checks["sessions_hash_matches"] = source_hashes.get("official_sessions") == sha256_file(args.sessions)
    checks["unavailable_dimensions_recorded"] = bool(payload.get("unavailable_dimensions"))

    candidate_metrics = payload.get("candidate_metrics", {})
    checks["candidate_metrics_exact"] = set(candidate_metrics) == set(CANDIDATES)
    for candidate in CANDIDATES:
        item = candidate_metrics.get(candidate, {})
        coverage = item.get("coverage", {})
        checks[f"{candidate}:coverage_row_range"] = within(coverage.get("row_coverage"), 0.0, 1.0)
        checks[f"{candidate}:finite_not_above_eligible"] = (
            coverage.get("finite_rows") is not None
            and coverage.get("eligible_rows") is not None
            and coverage["finite_rows"] <= coverage["eligible_rows"]
        )
        top_k = item.get("top_k", {})
        checks[f"{candidate}:top_k_exact"] = set(top_k) == {str(k) for k in TOP_KS}
        relationship = item.get("rank_liquidity_relationship", {})
        for relationship_name in ("daily_rank_vs_market_value_percentile", "daily_rank_vs_volume_percentile"):
            checks[f"{candidate}:{relationship_name}:range"] = all(
                within(relationship.get(relationship_name, {}).get(key), -1.0, 1.0)
                for key in ("min", "q01", "q05", "q25", "median", "q75", "q95", "q99", "max", "mean")
            )
        for k in TOP_KS:
            metrics = top_k.get(str(k), {})
            turnover = metrics.get("turnover", {})
            checks[f"{candidate}:{k}:turnover_range"] = all(
                within(turnover.get(key), 0.0, 1.0) for key in ("min", "q01", "q05", "q25", "median", "q75", "q95", "q99", "max", "mean")
            )
            checks[f"{candidate}:{k}:turnover_observations_bound"] = (
                isinstance(metrics.get("turnover_observations"), int) and 0 <= metrics["turnover_observations"] <= 599
            )
            persistence = metrics.get("persistence_sessions", {})
            checks[f"{candidate}:{k}:persistence_range"] = within(persistence.get("min"), 0.0, 600.0) and within(persistence.get("max"), 0.0, 600.0)
            liquidity = metrics.get("liquidity", {})
            checks[f"{candidate}:{k}:liquidity_percentile_range"] = all(
                within(liquidity.get("liquidity_percentile", {}).get(key), 0.0, 1.0)
                for key in ("min", "q01", "q05", "q25", "median", "q75", "q95", "q99", "max", "mean")
            )
            checks[f"{candidate}:{k}:low_liquidity_share_range"] = within(liquidity.get("below_liquidity_q25_share"), 0.0, 1.0)

    pairs = payload.get("pairwise_orthogonality", {})
    checks["pairwise_count"] = len(pairs) == 6
    for pair, item in pairs.items():
        spearman = item.get("daily_spearman", {})
        checks[f"{pair}:spearman_range"] = all(
            within(spearman.get(key), -1.0, 1.0) for key in ("min", "q01", "q05", "q25", "median", "q75", "q95", "q99", "max", "mean")
        )
        overlap = item.get("top_k_overlap", {})
        checks[f"{pair}:top_k_overlap_exact"] = set(overlap) == {str(k) for k in TOP_KS}
        for k in TOP_KS:
            item_k = overlap.get(str(k), {})
            checks[f"{pair}:{k}:overlap_range"] = all(
                within(item_k.get("overlap_fraction", {}).get(key), 0.0, 1.0)
                for key in ("min", "q01", "q05", "q25", "median", "q75", "q95", "q99", "max", "mean")
            )
            checks[f"{pair}:{k}:jaccard_range"] = all(
                within(item_k.get("jaccard", {}).get(key), 0.0, 1.0)
                for key in ("min", "q01", "q05", "q25", "median", "q75", "q95", "q99", "max", "mean")
            )

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scope": "INDEPENDENT_OUTCOME_BLIND_STRUCTURAL_LAB_AUDIT",
        "checks": checks,
        "builder_sha256": sha256_file(args.builder),
        "audit_sha256": sha256_file(args.audit),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
