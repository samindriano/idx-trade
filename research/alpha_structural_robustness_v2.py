"""Key-aligned correction replay of the target-free robustness battery.

This wrapper preserves the V1 formulas and diagnostics but fixes one defect:
lookback variants are joined to the frozen surface by (ticker,date) keys after
the baseline merge, never by a reset positional index. V1 remains preserved.
No target, outcome, provider, or incumbent artifact is read.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_structural_robustness_v1 import (
    CANDIDATES,
    FROZEN_SESSIONS,
    LOOKBACKS,
    build_variant_scores,
    build_decision_universe,
    key_digest,
    missingness_stress,
    prepare_surface,
    rank_transform_audit,
    safe,
    score_summary,
    set_metrics,
    sha256_file,
    temporal_audit,
    ticker_subsample_stress,
    top_sets,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    baseline = pd.read_parquet(args.features)
    baseline["ticker"] = baseline["ticker"].astype("string")
    baseline["date"] = pd.to_datetime(baseline["date"], errors="raise").dt.normalize()
    surface_all, official_dates, universe_stats = prepare_surface(
        args.panel, args.sessions, args.anchors
    )
    frozen_dates = official_dates.iloc[-FROZEN_SESSIONS:]
    if len(frozen_dates) != FROZEN_SESSIONS:
        raise ValueError("expected at least 600 official sessions")
    surface = surface_all[surface_all["date"].isin(frozen_dates)].copy()
    baseline = baseline[baseline["date"].isin(frozen_dates)].copy()
    if key_digest(surface.loc[surface["source_panel_row_present"].astype(bool)]) != key_digest(baseline):
        raise ValueError("baseline and recomputed source-panel keys differ")

    equivalence: dict[str, object] = {}
    for candidate, horizon in [("C1", 5), ("C2", 5), ("C4", 20)]:
        recomputed = build_variant_scores(surface_all, horizon, candidate)
        left = surface_all[["ticker", "date", "source_panel_row_present", "eligible_decision_universe"]].copy()
        left = left[left["date"].isin(frozen_dates)]
        recomputed = recomputed.loc[left.index]
        left["recomputed"] = recomputed
        left = left[left["source_panel_row_present"]]
        right = baseline[["ticker", "date", CANDIDATES[candidate]]]
        joined = left.merge(right, on=["ticker", "date"], how="inner", validate="one_to_one")
        finite = np.isfinite(joined["recomputed"]) & np.isfinite(joined[CANDIDATES[candidate]])
        differences = (joined.loc[finite, "recomputed"] - joined.loc[finite, CANDIDATES[candidate]]).abs()
        equivalence[candidate] = {
            "finite_pairs": int(finite.sum()),
            "max_abs_difference": float(differences.max()) if len(differences) else None,
            "mean_abs_difference": float(differences.mean()) if len(differences) else None,
            "within_1e-10": bool(len(differences) and differences.max() <= 1e-10),
        }
        if not equivalence[candidate]["within_1e-10"]:
            raise ValueError(f"baseline formula equivalence failed for {candidate}")

    score_cols = [*CANDIDATES.values()]
    surface = surface.merge(
        baseline[["ticker", "date", *score_cols]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    evaluation_dates = frozen_dates
    result: dict[str, object] = {
        "status": "PASS_STRUCTURAL_ONLY",
        "implementation": "alpha_structural_robustness_v2_key_aligned",
        "supersedes_interpretation_of": "alpha_structural_robustness_v1 lookback variants only",
        "correction": "join lookback variants by explicit ticker/date keys after baseline merge",
        "outcome_accessed": False,
        "provider_accessed": False,
        "incumbent_score_accessed": False,
        "target_accessed": False,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "features_sha256": sha256_file(args.features),
        "panel_sha256": sha256_file(args.panel),
        "sessions_sha256": sha256_file(args.sessions),
        "anchors_sha256": sha256_file(args.anchors),
        "frozen_session_count": int(len(frozen_dates)),
        "frozen_date_min": str(frozen_dates.min().date()),
        "frozen_date_max": str(frozen_dates.max().date()),
        "universe_stats": universe_stats,
        "base_formula_equivalence": equivalence,
        "baseline": {},
        "lookback_variants": {},
        "rank_normalization": {},
        "missingness_stress": {},
        "ticker_subsample_stress": {},
        "temporal": {},
        "interpretation": {
            "candidate_budget_changed": False,
            "variants_are_new_candidates": False,
            "predictive_claim": False,
            "c3_source_contract_widened": False,
            "v1_variant_alignment_validated": False,
        },
        "code_sha256": sha256_file(Path(__file__)),
    }

    for candidate, source in CANDIDATES.items():
        result["baseline"][candidate] = score_summary(surface, source, evaluation_dates)
        result["rank_normalization"][candidate] = rank_transform_audit(surface, candidate, evaluation_dates)
        result["missingness_stress"][candidate] = missingness_stress(surface, candidate, evaluation_dates)
        result["ticker_subsample_stress"][candidate] = ticker_subsample_stress(surface, candidate, evaluation_dates)
        result["temporal"][candidate] = temporal_audit(surface, candidate, evaluation_dates)

    for candidate, horizons in LOOKBACKS.items():
        result["lookback_variants"][candidate] = {}
        for horizon in horizons:
            name = f"h{horizon}"
            if horizon == (5 if candidate in {"C1", "C2"} else 20):
                result["lookback_variants"][candidate][name] = {
                    "is_fixed_baseline": True,
                    "summary": result["baseline"][candidate],
                }
                continue
            variant_scores = build_variant_scores(surface_all, horizon, candidate)
            variant_lookup = surface_all[["ticker", "date"]].copy()
            variant_lookup["variant_score"] = variant_scores.to_numpy()
            surface_variant = surface[[
                "ticker", "date", "eligible_decision_universe", "source_panel_row_present"
            ]].merge(
                variant_lookup,
                on=["ticker", "date"],
                how="left",
                validate="one_to_one",
            )
            if (
                len(surface_variant) != len(surface)
                or surface_variant[["ticker", "date"]].duplicated().any()
            ):
                raise AssertionError("key-aligned variant join failed")
            result["lookback_variants"][candidate][name] = {
                "is_fixed_baseline": False,
                "alignment": "ticker/date key join",
                "summary": score_summary(surface_variant, "variant_score", evaluation_dates),
                "overlap_vs_fixed_baseline": set_metrics(
                    top_sets(surface_variant, "variant_score", evaluation_dates),
                    top_sets(surface, CANDIDATES[candidate], evaluation_dates),
                ),
            }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(safe(result), indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "output_sha256": sha256_file(args.out),
        "code_sha256": result["code_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
