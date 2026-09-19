"""Outcome-blind attribution of unresolved CA sensitivity.

The script reuses the retained counterfactual scoring contract only to classify
which changed score/rank rows are direct unresolved-row keys versus spillover
rows. It never writes the panel or treats idx_close as an admitted correction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_corporate_action_basis_audit_v1 import (
    CANDIDATES,
    HLIQ_DIAGNOSTIC,
    PANEL_COLUMNS,
    build_decision_universe,
    score_panel,
    sha256_file,
    top30_sets,
)


SENSITIVITY_COLUMNS = [*CANDIDATES, HLIQ_DIAGNOSTIC]


def finite_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def summarize_changes(
    baseline: pd.DataFrame,
    counterfactual: pd.DataFrame,
    unresolved_keys: set[tuple[str, pd.Timestamp]],
    column: str,
) -> dict[str, object]:
    base = baseline[["ticker", "date", "eligible_decision_universe", column]].rename(columns={column: "base"})
    cf = counterfactual[["ticker", "date", "eligible_decision_universe", column]].rename(columns={column: "cf"})
    merged = base.merge(cf, on=["ticker", "date", "eligible_decision_universe"], how="inner", validate="one_to_one")
    valid = merged["eligible_decision_universe"] & np.isfinite(merged["base"]) & np.isfinite(merged["cf"])
    merged["direct_row"] = [
        (str(ticker), pd.Timestamp(date)) in unresolved_keys
        for ticker, date in zip(merged["ticker"], merged["date"], strict=True)
    ]
    merged["score_delta"] = (merged["cf"] - merged["base"]).where(valid)
    base_rank = merged.loc[valid].groupby("date", sort=False)["base"].rank(method="average", pct=True)
    cf_rank = merged.loc[valid].groupby("date", sort=False)["cf"].rank(method="average", pct=True)
    merged.loc[valid, "rank_changed"] = (base_rank - cf_rank).abs().gt(1e-12).to_numpy()
    merged["rank_changed"] = merged["rank_changed"].fillna(False).astype(bool)
    merged["score_changed"] = merged["score_delta"].abs().gt(1e-12).fillna(False)

    groups: dict[str, object] = {}
    for label, mask in (("direct_row", merged["direct_row"]), ("spillover_row", ~merged["direct_row"])):
        score_mask = valid & merged["score_changed"] & mask
        rank_mask = valid & merged["rank_changed"] & mask
        score_abs = merged.loc[score_mask, "score_delta"].abs()
        groups[label] = {
            "rows": int(mask.sum()),
            "finite_compared": int((valid & mask).sum()),
            "score_changed_rows": int(score_mask.sum()),
            "rank_changed_rows": int(rank_mask.sum()),
            "mean_abs_score_change": finite_float(score_abs.mean()),
            "max_abs_score_change": finite_float(score_abs.max()),
        }

    base_sets = top30_sets(baseline, column)
    cf_sets = top30_sets(counterfactual, column)
    overlap: list[float] = []
    changed_dates = 0
    direct_changed_slots = 0
    spillover_changed_slots = 0
    for date in sorted(set(base_sets) & set(cf_sets)):
        left = base_sets[date]
        right = cf_sets[date]
        overlap.append(len(left & right) / 30.0)
        changed = left ^ right
        if changed:
            changed_dates += 1
            for ticker in changed:
                if (str(ticker), pd.Timestamp(date)) in unresolved_keys:
                    direct_changed_slots += 1
                else:
                    spillover_changed_slots += 1
    return {
        "finite_eligible_rows_compared": int(valid.sum()),
        "rows_with_score_change": int((valid & merged["score_changed"]).sum()),
        "rows_with_rank_change": int((valid & merged["rank_changed"]).sum()),
        "direct_vs_spillover": groups,
        "top30_common_dates": int(len(overlap)),
        "top30_changed_dates": changed_dates,
        "mean_top30_overlap": finite_float(np.mean(overlap)) if overlap else None,
        "min_top30_overlap": finite_float(np.min(overlap)) if overlap else None,
        "changed_top30_slots_direct": direct_changed_slots,
        "changed_top30_slots_spillover": spillover_changed_slots,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--unresolved-scale", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    panel = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    features = pd.read_parquet(args.features, columns=["ticker", "date", "eligible_decision_universe", *CANDIDATES])
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    universe, universe_stats = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors
    )
    baseline = score_panel(panel, universe)
    counterfactual_panel = panel.copy()
    unresolved = pd.read_csv(args.unresolved_scale, usecols=["ticker", "date", "idx_close"])
    unresolved["ticker"] = unresolved["ticker"].astype("string")
    unresolved["date"] = pd.to_datetime(unresolved["date"], errors="raise").dt.normalize()
    unresolved["idx_close"] = pd.to_numeric(unresolved["idx_close"], errors="coerce")
    unresolved_keys = set(zip(unresolved["ticker"].astype(str), unresolved["date"], strict=True))
    counterfactual_panel = counterfactual_panel.merge(
        unresolved[["ticker", "date", "idx_close"]], on=["ticker", "date"], how="left", validate="one_to_one"
    )
    counterfactual_panel["close"] = counterfactual_panel["idx_close"].fillna(counterfactual_panel["close"])
    counterfactual = score_panel(counterfactual_panel[PANEL_COLUMNS], universe)

    stored = features.merge(baseline, on=["ticker", "date", "eligible_decision_universe"], suffixes=("_stored", "_recomputed"), validate="one_to_one")
    reproduction: dict[str, object] = {}
    for column in CANDIDATES:
        left = pd.to_numeric(stored[f"{column}_stored"], errors="coerce")
        right = pd.to_numeric(stored[f"{column}_recomputed"], errors="coerce")
        valid = np.isfinite(left) & np.isfinite(right)
        reproduction[column] = {
            "finite_compared": int(valid.sum()),
            "max_abs_diff": finite_float((left[valid] - right[valid]).abs().max()),
        }

    attribution = {column: summarize_changes(baseline, counterfactual, unresolved_keys, column) for column in SENSITIVITY_COLUMNS}
    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "B_J_CORPORATE_ACTION_UNRESOLVED_EXPOSURE_ATTRIBUTION",
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "panel_mutated": False,
        "clean_refit_authorized": False,
        "unresolved_rows": int(len(unresolved)),
        "unresolved_tickers": int(unresolved["ticker"].nunique()),
        "universe": universe_stats,
        "stored_score_reproduction": reproduction,
        "attribution": attribution,
        "interpretation": {
            "direct_row_definition": "changed row key is present in the 188-row unresolved comparison artifact",
            "spillover_definition": "changed row key is absent from the unresolved artifact; label is not a proof of one causal path",
            "comparison_is_counterfactual": True,
            "price_basis_admitted": False,
            "predictive_claim": False,
        },
        "source_hashes": {
            "panel": sha256_file(args.panel),
            "features": sha256_file(args.features),
            "official_sessions": sha256_file(args.sessions),
            "tradability_anchors": sha256_file(args.anchors),
            "unresolved_scale": sha256_file(args.unresolved_scale),
        },
        "manifest_sha256": sha256_file(args.manifest),
        "code_sha256": sha256_file(Path(__file__)),
        "repo_head": args.repo_head,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(args.output), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
