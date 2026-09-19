"""Outcome-blind structural diagnostic for the new bounded H-EXC-02 contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_hvol01_compression_diagnostic_v1 import (
    daily_rank_dependence,
    finite,
    overlap_stats,
    quartile_share,
    top30_sets,
    turnover_stats,
)
from alpha_stage_a_v2 import build_decision_universe, rolling


SCORE = "H_EXC_02_bounded_excursion_balance_5_v1"
HLIQ = "HLIQ01_variability_log_turnover_20_v1"
HVOL = "H_VOL_01_compression_5v60_v1"
CANDIDATES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C4_path_efficiency_reversal_20_v1",
]
PANEL_COLUMNS = ["ticker", "date", "high", "low", "close", "volume", "regular_market_value"]
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


def build_scores(full: pd.DataFrame) -> pd.DataFrame:
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
    up_distance = (result["high"] - result["prev_close"]).abs()
    down_distance = (result["low"] - result["prev_close"]).abs()
    denominator = up_distance + down_distance
    result["bounded_daily_balance"] = ((up_distance - down_distance) / denominator).where(
        valid & denominator.gt(0)
    )
    result[SCORE] = rolling(result, "bounded_daily_balance", 5, "median")

    range_valid = (
        result["high"].gt(0)
        & result["low"].gt(0)
        & result["close"].gt(0)
        & np.isfinite(result["high"])
        & np.isfinite(result["low"])
        & np.isfinite(result["close"])
        & result["high"].ge(result["low"])
    )
    result["range_pct"] = ((result["high"] - result["low"]) / result["close"]).where(range_valid)
    ratio = rolling(result, "range_pct", 5, "median") / rolling(result, "range_pct", 60, "median")
    result[HVOL] = (-np.log(ratio.where(ratio.gt(0)))).where(np.isfinite(ratio))

    result["dollar_turnover"] = (result["close"] * result["volume"]).where(
        result["close"].gt(0) & result["volume"].gt(0)
        & np.isfinite(result["close"]) & np.isfinite(result["volume"])
    )
    result["log_dollar_turnover"] = np.log(result["dollar_turnover"].where(result["dollar_turnover"].gt(0)))
    result[HLIQ] = rolling(result, "log_dollar_turnover", 20, "std")
    for column in [SCORE, HVOL, HLIQ]:
        result.loc[~result["eligible_decision_universe"], column] = np.nan
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--hvol-output", type=Path, required=True)
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
    prior = json.loads(args.hvol_output.read_text(encoding="utf-8"))
    if prior.get("status") != "PASS_STRUCTURAL_ONLY" or prior.get("candidate_id_created") is not False:
        raise ValueError("prior H-VOL output is not the expected structural-only result")

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
    scored = build_scores(full)

    features = pd.read_parquet(args.features, columns=["ticker", "date", "eligible_decision_universe", *CANDIDATES])
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    eligibility = features[["ticker", "date", "eligible_decision_universe"]].merge(
        universe[["ticker", "date", "eligible_decision_universe"]], on=["ticker", "date"], how="left",
        suffixes=("_stored", "_recomputed"), validate="one_to_one"
    )
    if len(eligibility) != len(features):
        raise ValueError("feature eligibility key coverage mismatch")
    if not eligibility["eligible_decision_universe_stored"].fillna(False).astype(bool).equals(
        eligibility["eligible_decision_universe_recomputed"].fillna(False).astype(bool)
    ):
        raise ValueError("feature eligibility mismatch")

    candidate_sets = {column: top30_sets(features, column) for column in CANDIDATES}
    comparison_sets = {**candidate_sets, "H-LIQ-01": top30_sets(scored, HLIQ), "H-VOL-01_5v60": top30_sets(scored, HVOL)}
    sets = top30_sets(scored, SCORE)
    selected = scored[["ticker", "date", "eligible_decision_universe", SCORE, "regular_market_value", "dollar_turnover"]]
    chosen = selected_rows(sets)
    values = selected.loc[selected["eligible_decision_universe"] & selected[SCORE].notna(), SCORE]
    distribution = values.describe(percentiles=[0.01, 0.05, 0.50, 0.95, 0.99]).to_dict()
    combined = scored[["ticker", "date", "eligible_decision_universe", SCORE, HLIQ, HVOL]].merge(
        features[["ticker", "date", *CANDIDATES]], on=["ticker", "date"], how="left", validate="one_to_one"
    )
    rank_dependence = {
        label: daily_rank_dependence(combined, SCORE, column)
        for label, column in {"C1": CANDIDATES[0], "C2": CANDIDATES[1], "C4": CANDIDATES[2], "H-LIQ-01": HLIQ, "H-VOL-01_5v60": HVOL}.items()
    }
    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "I_E_HEXC02_OUTCOME_BLIND_BOUNDED_EXCURSION_DIAGNOSTIC",
        "candidate_id_created": False,
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "panel_mutated": False,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_head": args.repo_head,
        "code_sha256": sha256_file(Path(__file__)),
        "hvol_result_sha256": sha256_file(args.hvol_output),
        "manifest_sha256": actual_hashes["manifest"],
        "source_hashes": actual_hashes,
        "universe": universe_stats,
        "formula": {
            "name": SCORE,
            "daily_term": "(abs(high-prev_close)-abs(low-prev_close))/(abs(high-prev_close)+abs(low-prev_close))",
            "aggregation": "median",
            "window_sessions": 5,
            "bounded_daily_domain": "[-1,1]",
            "uses_open": False,
            "uses_volume": False,
        },
        "support": {
            "finite_eligible_rows": int((selected["eligible_decision_universe"] & selected[SCORE].notna()).sum()),
            "finite_dates": int(selected.loc[selected["eligible_decision_universe"] & selected[SCORE].notna(), "date"].nunique()),
            "finite_tickers": int(selected.loc[selected["eligible_decision_universe"] & selected[SCORE].notna(), "ticker"].nunique()),
        },
        "score_distribution": {str(key): finite(value) for key, value in distribution.items()},
        "turnover_top30": turnover_stats(sets),
        "selected_value_quartile_share": quartile_share(selected, "regular_market_value", chosen, "value_quartile"),
        "selected_turnover_quartile_share": quartile_share(selected, "dollar_turnover", chosen, "turnover_quartile"),
        "top30_overlap_vs_existing": {label: overlap_stats(sets, other) for label, other in comparison_sets.items()},
        "daily_rank_dependence_vs_existing": rank_dependence,
        "interpretation": {
            "structural_only": True,
            "predictive_claim": False,
            "pit_and_price_basis_admitted": False,
            "numerical_bound_claim": True,
            "h_exc01_modified": False,
            "protected_packet_changed": False,
            "candidate_disposition": "FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
