"""Independent structural verifier for the capacity/friction tail artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_CANDIDATES = {"C1", "C2", "C4", "H-LIQ-01", "H-VOL-01", "H-EXC-02"}
EXPECTED_HASHES = {
    "panel": "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e",
    "features": "aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4",
    "sessions": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "anchors": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
}


def close(left: object, right: object, tolerance: float = 1e-9) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    checks["status_structural_only"] = result.get("status") == "PASS_STRUCTURAL_ONLY"
    checks["stage_exact"] = result.get("stage") == "L_CAPACITY_FRICTION_TAIL_CONCENTRATION"
    checks["top_k_exact"] = result.get("top_k") == 30
    checks["frozen_session_count_exact"] = result.get("frozen_session_count") == 600
    checks["candidate_set_exact"] = set(result.get("candidate_set", [])) == EXPECTED_CANDIDATES
    checks["source_hashes_exact"] = result.get("source_hashes") == EXPECTED_HASHES
    scope = result.get("scope", {})
    for field in (
        "outcome_accessed",
        "target_accessed",
        "provider_accessed",
        "incumbent_score_accessed",
        "canonical_mutation",
        "candidate_id_created",
        "executable_capacity_admitted",
        "pit_price_basis_admitted",
    ):
        checks[f"scope_{field}_false"] = scope.get(field) is False

    candidates = result.get("candidates", {})
    checks["candidate_records_exact"] = set(candidates) == EXPECTED_CANDIDATES
    for name, item in candidates.items():
        prefix = name.replace("-", "_")
        dates = item.get("top30_dates", 0)
        slots = item.get("selected_slots", 0)
        checks[f"{prefix}_dates_exact"] = dates == 600
        checks[f"{prefix}_slots_exact"] = slots == dates * 30
        concentration = item.get("concentration", {})
        checks[f"{prefix}_concentration_bounded"] = (
            0 <= concentration.get("top_1_slot_share", -1) <= 1
            and 0 <= concentration.get("top_10_slot_share", -1) <= 1
            and 0 <= concentration.get("hhi", -1) <= 1
            and concentration.get("unique_names", 0) <= slots
        )
        turnover = item.get("turnover", {})
        one_way = turnover.get("one_way_turnover", {})
        checks[f"{prefix}_turnover_bounded"] = all(
            0 <= one_way.get(key, -1) <= 1 for key in ("mean", "median", "q95", "q99", "max")
        )
        burdens = turnover.get("friction_burden_bps_per_nav", {})
        checks[f"{prefix}_base_burden_consistent"] = all(
            close(burdens.get("base_60bps", {}).get(key), one_way.get(key) * 60.0)
            for key in ("mean", "q95", "q99", "max")
        )
        checks[f"{prefix}_sensitivity_burden_consistent"] = all(
            close(burdens.get("sensitivity_110bps", {}).get(key), one_way.get(key) * 110.0)
            for key in ("mean", "q95", "q99", "max")
        )
        buckets = item.get("buckets", {})
        for bucket_name, bucket in buckets.items():
            bucket_prefix = f"{prefix}_{bucket_name}"
            selected = bucket.get("selected_slots", 0)
            bucketable = bucket.get("bucketable_slots", 0)
            shares = bucket.get("selected_slot_share_by_quartile", {})
            checks[f"{bucket_prefix}_counts_bounded"] = 0 <= bucketable <= selected
            checks[f"{bucket_prefix}_share_consistent"] = close(
                bucket.get("bucketable_share_of_selected"), bucketable / selected if selected else 0.0
            )
            checks[f"{bucket_prefix}_quartiles_complete"] = set(shares) == {"1", "2", "3", "4"}
            checks[f"{bucket_prefix}_quartiles_sum_one"] = close(sum(float(value) for value in shares.values()), 1.0)

    if not all(checks.values()):
        raise SystemExit(json.dumps({"status": "FAIL", "checks": checks}, indent=2, sort_keys=True))
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
