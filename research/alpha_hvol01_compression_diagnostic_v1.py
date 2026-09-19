"""Outcome-blind structural diagnostic for the preregistered H-VOL-01 state."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_corporate_action_basis_audit_v1 import top30_sets
from alpha_stage_a_v2 import build_decision_universe, rolling


SCORE = "H_VOL_01_compression_5v60_v1"
CANDIDATES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C4_path_efficiency_reversal_20_v1",
]
PANEL_COLUMNS = ["ticker", "date", "high", "low", "close", "regular_market_value"]
EXPECTED_SESSIONS_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_ANCHORS_SHA256 = "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e"
EXTERNAL_STAGE_ROOT = Path(
    r"D:\Documents\Project\idx-alpha-available-data-staging-20260919"
).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def overlap_stats(base: dict[pd.Timestamp, set[str]], other: dict[pd.Timestamp, set[str]]) -> dict[str, object]:
    overlaps = [len(base[d] & other[d]) / 30.0 for d in sorted(set(base) & set(other))]
    return {
        "common_dates": len(overlaps),
        "mean_top30_overlap": finite(np.mean(overlaps)) if overlaps else None,
        "min_top30_overlap": finite(np.min(overlaps)) if overlaps else None,
    }


def turnover_stats(sets: dict[pd.Timestamp, set[str]]) -> dict[str, object]:
    dates = sorted(sets)
    values = [1.0 - len(sets[left] & sets[right]) / 30.0 for left, right in zip(dates, dates[1:])]
    return {
        "dates": len(dates),
        "mean": finite(np.mean(values)) if values else None,
        "median": finite(np.median(values)) if values else None,
        "q95": finite(np.quantile(values, 0.95)) if values else None,
        "max": finite(np.max(values)) if values else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    if EXTERNAL_STAGE_ROOT not in output.parents:
        raise ValueError("output must remain inside the isolated external staging root")
    if sha256_file(args.sessions) != EXPECTED_SESSIONS_SHA256:
        raise ValueError("session hash is not the frozen guarded hash")
    if sha256_file(args.anchors) != EXPECTED_ANCHORS_SHA256:
        raise ValueError("anchor hash is not the frozen guarded hash")

    raw = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    raw["ticker"] = raw["ticker"].astype("string")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.normalize()
    for column in PANEL_COLUMNS[2:]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    if raw.duplicated(["ticker", "date"]).any():
        raise ValueError("panel has duplicate ticker/date keys")

    universe, universe_stats = build_decision_universe(raw[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors)
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
    full["range_short_5"] = rolling(full, "range_pct", 5, "median")
    full["range_long_60"] = rolling(full, "range_pct", 60, "median")
    ratio = full["range_short_5"] / full["range_long_60"]
    full[SCORE] = (-np.log(ratio.where(ratio.gt(0)))).where(np.isfinite(ratio))

    features = pd.read_parquet(
        args.features,
        columns=["ticker", "date", "eligible_decision_universe", *CANDIDATES],
    )
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    if features.duplicated(["ticker", "date"]).any():
        raise ValueError("feature artifact has duplicate ticker/date keys")
    if not features["eligible_decision_universe"].fillna(False).astype(bool).equals(
        full["eligible_decision_universe"].fillna(False).astype(bool)
    ):
        raise ValueError("feature eligibility does not match the guarded universe")

    selected = full[["ticker", "date", "eligible_decision_universe", SCORE, "regular_market_value"]].copy()
    selected["eligible_decision_universe"] = selected["eligible_decision_universe"].fillna(False).astype(bool)
    h_sets = top30_sets(selected, SCORE)
    turnovers = turnover_stats(h_sets)
    candidate_sets = {column: top30_sets(features, column) for column in CANDIDATES}
    comparisons = {column: overlap_stats(h_sets, sets) for column, sets in candidate_sets.items()}

    value_q = []
    for date, group in selected.loc[selected["eligible_decision_universe"]].groupby("date", sort=True):
        valid_values = group["regular_market_value"].gt(0) & np.isfinite(group["regular_market_value"])
        ranks = group.loc[valid_values, "regular_market_value"].rank(method="first", pct=True)
        for ticker, rank in ranks.items():
            value_q.append((date, group.loc[ticker, "ticker"], int(min(4, max(1, np.ceil(rank * 4))))))
    value_buckets = pd.DataFrame(value_q, columns=["date", "ticker", "value_quartile"])
    selected_rows = pd.concat(
        [pd.DataFrame({"date": date, "ticker": sorted(tickers)}) for date, tickers in sorted(h_sets.items())],
        ignore_index=True,
    )
    selected_rows = selected_rows.merge(value_buckets, on=["date", "ticker"], how="left", validate="one_to_one")
    bucket_share = (
        selected_rows["value_quartile"].value_counts(normalize=True).sort_index().to_dict()
        if not selected_rows.empty
        else {}
    )

    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "E_HVOL01_OUTCOME_BLIND_COMPRESSION_DIAGNOSTIC",
        "candidate_id_created": False,
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_head": args.repo_head,
        "code_sha256": sha256_file(Path(__file__)),
        "manifest_sha256": sha256_file(args.manifest),
        "source_hashes": {
            "panel": sha256_file(args.panel),
            "features": sha256_file(args.features),
            "sessions": sha256_file(args.sessions),
            "anchors": sha256_file(args.anchors),
        },
        "formula": {
            "name": SCORE,
            "range_pct": "(high-low)/close",
            "short_window_sessions": 5,
            "long_window_sessions": 60,
            "aggregation": "median",
            "direction": "-log(short_range/long_range)",
        },
        "universe": universe_stats,
        "support": {
            "finite_eligible_rows": int(selected.loc[selected["eligible_decision_universe"], SCORE].notna().sum()),
            "finite_dates": int(selected.loc[selected["eligible_decision_universe"] & selected[SCORE].notna(), "date"].nunique()),
            "finite_tickers": int(selected.loc[selected["eligible_decision_universe"] & selected[SCORE].notna(), "ticker"].nunique()),
        },
        "turnover_top30": turnovers,
        "top30_overlap_vs_existing": comparisons,
        "selected_value_quartile_share": {str(key): finite(value) for key, value in bucket_share.items()},
        "interpretation": {
            "structural_only": True,
            "predictive_claim": False,
            "candidate_id_created": False,
            "pit_and_price_basis_admitted": False,
            "no_parameter_sweep": True,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
