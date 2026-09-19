"""Outcome-blind H-VOL-01 sensitivity to the retained unresolved CA rows.

The counterfactual replaces close with retained idx_close values in memory
only. It does not repair the panel, admit a price basis, access outcomes, or
create a candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_hvol01_compression_diagnostic_v1 import SCORE, top30_sets
from alpha_stage_a_v2 import build_decision_universe, rolling


PANEL_COLUMNS = ["ticker", "date", "high", "low", "close", "volume", "regular_market_value"]
EXPECTED_HASHES = {
    "panel": "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e",
    "features": "aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4",
    "sessions": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "anchors": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
    "unresolved_scale": "eaedba187a3645a83c06c3885dac2c819e818fb68636cfedf2d32e7792432743",
    "manifest": "27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96",
}
EXTERNAL_STAGE_ROOT = Path(r"D:\Documents\Project\idx-alpha-available-data-staging-20260919").resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def compute_score(panel: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    raw = panel[PANEL_COLUMNS].copy()
    raw["ticker"] = raw["ticker"].astype("string")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.normalize()
    for column in PANEL_COLUMNS[2:]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    full = universe.merge(raw, on=["ticker", "date"], how="left", validate="one_to_one")
    full = full.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    valid = (
        full["high"].gt(0)
        & full["low"].gt(0)
        & full["close"].gt(0)
        & np.isfinite(full["high"])
        & np.isfinite(full["low"])
        & np.isfinite(full["close"])
        & full["high"].ge(full["low"])
    )
    full["range_pct"] = ((full["high"] - full["low"]) / full["close"]).where(valid)
    short = rolling(full, "range_pct", 5, "median")
    long = rolling(full, "range_pct", 60, "median")
    ratio = short / long
    full[SCORE] = (-np.log(ratio.where(ratio.gt(0)))).where(np.isfinite(ratio))
    full.loc[~full["eligible_decision_universe"], SCORE] = np.nan
    return full[["ticker", "date", "eligible_decision_universe", SCORE]]


def summarize(
    baseline: pd.DataFrame,
    counterfactual: pd.DataFrame,
    unresolved_keys: set[tuple[str, pd.Timestamp]],
) -> dict[str, object]:
    merged = baseline.merge(
        counterfactual,
        on=["ticker", "date", "eligible_decision_universe"],
        suffixes=("_base", "_cf"),
        validate="one_to_one",
    )
    valid = (
        merged["eligible_decision_universe"].astype(bool)
        & np.isfinite(merged[f"{SCORE}_base"])
        & np.isfinite(merged[f"{SCORE}_cf"])
    )
    merged["direct_row"] = [
        (str(ticker), pd.Timestamp(date)) in unresolved_keys
        for ticker, date in zip(merged["ticker"], merged["date"], strict=True)
    ]
    merged["score_delta"] = (merged[f"{SCORE}_cf"] - merged[f"{SCORE}_base"]).where(valid)
    ranked = merged.loc[valid].copy()
    ranked["base_rank"] = ranked.groupby("date", sort=False)[f"{SCORE}_base"].rank(method="average", pct=True)
    ranked["cf_rank"] = ranked.groupby("date", sort=False)[f"{SCORE}_cf"].rank(method="average", pct=True)
    merged["rank_changed"] = False
    merged.loc[ranked.index, "rank_changed"] = (
        (ranked["base_rank"] - ranked["cf_rank"]).abs() > 1e-12
    ).to_numpy()
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

    base_sets = top30_sets(baseline, SCORE)
    cf_sets = top30_sets(counterfactual, SCORE)
    overlaps: list[float] = []
    changed_dates = 0
    direct_slots = 0
    spillover_slots = 0
    for date in sorted(set(base_sets) & set(cf_sets)):
        left = base_sets[date]
        right = cf_sets[date]
        overlaps.append(len(left & right) / 30.0)
        changed = left ^ right
        if changed:
            changed_dates += 1
            for ticker in changed:
                if (str(ticker), pd.Timestamp(date)) in unresolved_keys:
                    direct_slots += 1
                else:
                    spillover_slots += 1
    return {
        "finite_eligible_rows_compared": int(valid.sum()),
        "rows_with_score_change": int((valid & merged["score_changed"]).sum()),
        "rows_with_rank_change": int((valid & merged["rank_changed"]).sum()),
        "direct_vs_spillover": groups,
        "top30_common_dates": int(len(overlaps)),
        "top30_changed_dates": changed_dates,
        "mean_top30_overlap": finite_float(np.mean(overlaps)) if overlaps else None,
        "min_top30_overlap": finite_float(np.min(overlaps)) if overlaps else None,
        "changed_top30_slots_direct": direct_slots,
        "changed_top30_slots_spillover": spillover_slots,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--unresolved-scale", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--hvol-output", type=Path, required=True)
    parser.add_argument("--repo-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    if EXTERNAL_STAGE_ROOT not in output.parents:
        raise ValueError("refusing output outside isolated alpha staging")
    paths = {
        "panel": args.panel,
        "features": args.features,
        "sessions": args.sessions,
        "anchors": args.anchors,
        "unresolved_scale": args.unresolved_scale,
        "manifest": args.manifest,
    }
    actual_hashes = {name: sha256_file(path) for name, path in paths.items()}
    if actual_hashes != EXPECTED_HASHES:
        raise ValueError(f"input hash mismatch: {actual_hashes}")
    prior = json.loads(args.hvol_output.read_text(encoding="utf-8"))
    if prior.get("status") != "PASS_STRUCTURAL_ONLY" or prior.get("candidate_id_created") is not False:
        raise ValueError("prior H-VOL output is not the expected structural-only result")

    panel = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel duplicate ticker/date keys")
    universe, universe_stats = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors
    )
    features = pd.read_parquet(args.features, columns=["ticker", "date", "eligible_decision_universe"])
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    eligibility = features.merge(
        universe[["ticker", "date", "eligible_decision_universe"]],
        on=["ticker", "date"],
        how="left",
        suffixes=("_stored", "_recomputed"),
        validate="one_to_one",
    )
    if len(eligibility) != len(features):
        raise ValueError("feature eligibility key coverage mismatch")
    if not eligibility["eligible_decision_universe_stored"].fillna(False).astype(bool).equals(
        eligibility["eligible_decision_universe_recomputed"].fillna(False).astype(bool)
    ):
        raise ValueError("feature eligibility mismatch")

    baseline = compute_score(panel, universe)
    unresolved = pd.read_csv(args.unresolved_scale, usecols=["ticker", "date", "idx_close"])
    unresolved["ticker"] = unresolved["ticker"].astype("string")
    unresolved["date"] = pd.to_datetime(unresolved["date"], errors="raise").dt.normalize()
    unresolved["idx_close"] = pd.to_numeric(unresolved["idx_close"], errors="coerce")
    if unresolved.duplicated(["ticker", "date"]).any() or len(unresolved) != 188:
        raise ValueError("unresolved-scale artifact is not the frozen 188-row key set")
    unresolved_keys = set(zip(unresolved["ticker"].astype(str), unresolved["date"], strict=True))
    counterfactual_panel = panel.merge(
        unresolved[["ticker", "date", "idx_close"]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    counterfactual_panel["close"] = counterfactual_panel["idx_close"].fillna(counterfactual_panel["close"])
    counterfactual = compute_score(counterfactual_panel[PANEL_COLUMNS], universe)

    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "B_J_HVOL01_CORPORATE_ACTION_UNRESOLVED_SENSITIVITY",
        "candidate_id_created": False,
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "panel_mutated": False,
        "price_basis_admitted": False,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_head": args.repo_head,
        "code_sha256": sha256_file(Path(__file__)),
        "hvol_result_sha256": sha256_file(args.hvol_output),
        "manifest_sha256": actual_hashes["manifest"],
        "source_hashes": actual_hashes,
        "formula": {
            "name": SCORE,
            "range_pct": "(high-low)/close",
            "short_window_sessions": 5,
            "long_window_sessions": 60,
            "aggregation": "median",
            "direction": "-log(short_range/long_range)",
        },
        "universe": universe_stats,
        "unresolved_rows": int(len(unresolved)),
        "unresolved_tickers": int(unresolved["ticker"].nunique()),
        "baseline_support": int((baseline["eligible_decision_universe"] & baseline[SCORE].notna()).sum()),
        "counterfactual_support": int((counterfactual["eligible_decision_universe"] & counterfactual[SCORE].notna()).sum()),
        "attribution": summarize(baseline, counterfactual, unresolved_keys),
        "interpretation": {
            "direct_row_definition": "changed row key is present in the 188-row unresolved comparison artifact",
            "spillover_definition": "changed row key is absent from the unresolved artifact; not a causal label",
            "comparison_is_counterfactual": True,
            "predictive_claim": False,
            "clean_refit_authorized": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
