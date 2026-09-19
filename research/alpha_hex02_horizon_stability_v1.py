"""Outcome-blind fixed-horizon structural audit for H-EXC-02."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_hex02_bounded_excursion_balance_diagnostic_v1 import SCORE as BASE_SCORE
from alpha_hvol01_compression_diagnostic_v1 import finite, overlap_stats, quartile_share, top30_sets, turnover_stats
from alpha_stage_a_v2 import build_decision_universe, rolling


PANEL_COLUMNS = ["ticker", "date", "high", "low", "close", "volume", "regular_market_value"]
CANDIDATES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C4_path_efficiency_reversal_20_v1",
]
HORIZONS = {"5": 5, "20": 20, "60": 60}
EXPECTED_HASHES = {
    "panel": "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e",
    "features": "aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4",
    "sessions": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "anchors": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
    "manifest": "27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96",
}
EXTERNAL_STAGE_ROOT = Path(r"D:\Documents\Project\idx-alpha-available-data-staging-20260919").resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selected_rows(sets: dict[pd.Timestamp, set[str]]) -> pd.DataFrame:
    return pd.concat(
        [pd.DataFrame({"date": date, "ticker": sorted(tickers)}) for date, tickers in sorted(sets.items())],
        ignore_index=True,
    )


def build_daily_balance(full: pd.DataFrame) -> pd.DataFrame:
    result = full.copy()
    result["prev_close"] = result.groupby("ticker", sort=False)["close"].shift(1)
    valid = (
        result["high"].gt(0)
        & result["low"].gt(0)
        & result["prev_close"].gt(0)
        & np.isfinite(result["high"])
        & np.isfinite(result["low"])
        & np.isfinite(result["prev_close"])
        & result["high"].ge(result["low"])
    )
    up = (result["high"] - result["prev_close"]).abs()
    down = (result["low"] - result["prev_close"]).abs()
    denominator = up + down
    result["bounded_daily_balance"] = ((up - down) / denominator).where(valid & denominator.gt(0))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--hex02-output", type=Path, required=True)
    parser.add_argument("--repo-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    if EXTERNAL_STAGE_ROOT not in output.parents:
        raise ValueError("refusing output outside isolated alpha staging")
    paths = {"panel": args.panel, "features": args.features, "sessions": args.sessions, "anchors": args.anchors, "manifest": args.manifest}
    actual_hashes = {name: sha256_file(path) for name, path in paths.items()}
    if actual_hashes != EXPECTED_HASHES:
        raise ValueError(f"input hash mismatch: {actual_hashes}")
    prior = json.loads(args.hex02_output.read_text(encoding="utf-8"))
    if prior.get("status") != "PASS_STRUCTURAL_ONLY" or prior.get("candidate_id_created") is not False:
        raise ValueError("prior H-EXC-02 output is not the expected structural-only result")

    raw = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    raw["ticker"] = raw["ticker"].astype("string")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.normalize()
    for column in PANEL_COLUMNS[2:]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    if raw.duplicated(["ticker", "date"]).any():
        raise ValueError("panel duplicate ticker/date keys")
    universe, universe_stats = build_decision_universe(raw[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors)
    full = universe.merge(raw, on=["ticker", "date"], how="left", validate="one_to_one")
    full = full.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    full = build_daily_balance(full)

    features = pd.read_parquet(args.features, columns=["ticker", "date", "eligible_decision_universe", *CANDIDATES])
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    eligibility = features[["ticker", "date", "eligible_decision_universe"]].merge(
        universe[["ticker", "date", "eligible_decision_universe"]], on=["ticker", "date"], how="left",
        suffixes=("_stored", "_recomputed"), validate="one_to_one"
    )
    if len(eligibility) != len(features) or not eligibility["eligible_decision_universe_stored"].fillna(False).astype(bool).equals(
        eligibility["eligible_decision_universe_recomputed"].fillna(False).astype(bool)
    ):
        raise ValueError("feature eligibility mismatch")

    candidate_sets = {column: top30_sets(features, column) for column in CANDIDATES}
    variants: dict[str, object] = {}
    variant_sets: dict[str, dict[pd.Timestamp, set[str]]] = {}
    for label, window in HORIZONS.items():
        name = f"H_EXC_02_bounded_excursion_balance_{label}_v1"
        scored = full.copy()
        scored[name] = rolling(scored, "bounded_daily_balance", window, "median")
        scored.loc[~scored["eligible_decision_universe"], name] = np.nan
        sets = top30_sets(scored, name)
        variant_sets[label] = sets
        selected = scored[["ticker", "date", "eligible_decision_universe", name, "regular_market_value"]].copy()
        selected["dollar_turnover"] = (scored["close"] * scored["volume"]).where(
            scored["close"].gt(0) & scored["volume"].gt(0) & np.isfinite(scored["close"]) & np.isfinite(scored["volume"])
        )
        chosen = selected_rows(sets)
        values = selected.loc[selected["eligible_decision_universe"] & selected[name].notna(), name]
        distribution = values.describe(percentiles=[0.01, 0.05, 0.50, 0.95, 0.99]).to_dict()
        variants[label] = {
            "formula": {"daily_term": "(abs(high-prev_close)-abs(low-prev_close))/(abs(high-prev_close)+abs(low-prev_close))", "aggregation": "median", "window_sessions": window},
            "support": {
                "finite_eligible_rows": int((selected["eligible_decision_universe"] & selected[name].notna()).sum()),
                "finite_dates": int(selected.loc[selected["eligible_decision_universe"] & selected[name].notna(), "date"].nunique()),
                "finite_tickers": int(selected.loc[selected["eligible_decision_universe"] & selected[name].notna(), "ticker"].nunique()),
            },
            "score_distribution": {str(key): finite(value) for key, value in distribution.items()},
            "turnover_top30": turnover_stats(sets),
            "selected_value_quartile_share": quartile_share(selected, "regular_market_value", chosen, "value_quartile"),
            "selected_turnover_quartile_share": quartile_share(selected, "dollar_turnover", chosen, "turnover_quartile"),
            "top30_overlap_vs_existing": {column: overlap_stats(sets, other) for column, other in candidate_sets.items()},
        }

    baseline = variants["5"]
    if baseline["support"]["finite_eligible_rows"] != int(prior["support"]["finite_eligible_rows"]):
        raise ValueError("5-session support does not reproduce prior H-EXC-02 output")
    if not np.isclose(float(baseline["turnover_top30"]["mean"]), float(prior["turnover_top30"]["mean"]), rtol=0.0, atol=1e-12):
        raise ValueError("5-session turnover does not reproduce prior H-EXC-02 output")
    pairwise = {left: {right: overlap_stats(variant_sets[left], variant_sets[right]) for right in HORIZONS} for left in HORIZONS}
    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "J_HEXC02_FIXED_HORIZON_STABILITY",
        "candidate_id_created": False,
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "panel_mutated": False,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_head": args.repo_head,
        "code_sha256": sha256_file(Path(__file__)),
        "hex02_result_sha256": sha256_file(args.hex02_output),
        "manifest_sha256": actual_hashes["manifest"],
        "source_hashes": actual_hashes,
        "universe": universe_stats,
        "horizons_evaluated": HORIZONS,
        "variants": variants,
        "pairwise_top30_overlap": pairwise,
        "baseline_5_session_reproduction": {"support_match": True, "turnover_mean_match": True},
        "interpretation": {"structural_only": True, "predictive_claim": False, "horizon_selected_by_outcome": False, "no_parameter_sweep": True, "protected_packet_changed": False},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()

