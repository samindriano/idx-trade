"""Independent metadata verifier for the key-aligned robustness replay."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.input.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {
        "status_pass_structural_only": result.get("status") == "PASS_STRUCTURAL_ONLY",
        "implementation_is_v2": result.get("implementation") == "alpha_structural_robustness_v2_key_aligned",
        "no_target_access": result.get("target_accessed") is False,
        "no_outcome_access": result.get("outcome_accessed") is False,
        "no_provider_access": result.get("provider_accessed") is False,
        "no_incumbent_access": result.get("incumbent_score_accessed") is False,
        "no_candidate_budget_change": result.get("interpretation", {}).get("candidate_budget_changed") is False,
        "base_equivalence_exact": all(
            item.get("within_1e-10") is True
            for item in result.get("base_formula_equivalence", {}).values()
        ),
        "source_features_hash": result.get("features_sha256") == sha256_file(args.features),
        "source_panel_hash": result.get("panel_sha256") == sha256_file(args.panel),
        "source_sessions_hash": result.get("sessions_sha256") == sha256_file(args.sessions),
        "source_anchors_hash": result.get("anchors_sha256") == sha256_file(args.anchors),
        "code_hash": result.get("code_sha256") == sha256_file(args.code),
    }
    variant_checks = []
    for candidate, payload in result.get("lookback_variants", {}).items():
        for name, item in payload.items():
            if name == ("h5" if candidate in {"C1", "C2"} else "h20"):
                continue
            variant_checks.append(
                item.get("alignment") == "ticker/date key join"
                and item.get("overlap_vs_fixed_baseline", {}).get("usable_top_k_dates") == 600
            )
    checks["all_nonbaseline_variants_key_aligned"] = bool(variant_checks) and all(variant_checks)
    if not all(checks.values()):
        raise SystemExit(json.dumps({"status": "FAIL", "checks": checks}, indent=2))
    print(json.dumps({"status": "PASS", "checks": checks}, indent=2))


if __name__ == "__main__":
    main()

