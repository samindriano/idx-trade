"""Outcome-blind census of regular-market-value denominator states.

The exact pinned runtime maps missing/nonfinite execution values to zero in one
verifier and uses zero-clamped capacity in the allocator.  This audit measures
whether that state exists in the available frozen structural panel, without
accessing targets, outcomes, providers, or production artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CANDIDATES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C3_financial_quality_growth_v1",
    "C4_path_efficiency_reversal_20_v1",
]
TOP_K = 30
FROZEN_SESSION_COUNT = 600
EXTERNAL_STAGE_ROOT = Path(
    r"D:\Documents\Project\idx-alpha-available-data-staging-20260919"
).resolve()
EXPECTED_HASHES = {
    "features": "aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4",
    "panel": "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e",
    "official_sessions": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify_value(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "INVALID_NONFINITE"
    if not np.isfinite(number):
        return "INVALID_NONFINITE"
    if number < 0:
        return "INVALID_NEGATIVE"
    if number == 0:
        return "VALID_ZERO"
    return "VALID_POSITIVE"


def counts(frame: pd.DataFrame) -> dict[str, int]:
    result = frame["value_state"].value_counts().to_dict()
    return {key: int(result.get(key, 0)) for key in (
        "VALID_POSITIVE", "VALID_ZERO", "INVALID_NONFINITE", "INVALID_NEGATIVE"
    )}


def top_k(frame: pd.DataFrame, candidate: str) -> pd.DataFrame:
    rank_column = f"rank_{candidate}"
    eligible = frame["eligible_decision_universe"].astype(bool)
    finite_rank = pd.to_numeric(frame[rank_column], errors="coerce").notna()
    selected = frame.loc[eligible & finite_rank].copy()
    selected["rank_value"] = pd.to_numeric(selected[rank_column], errors="coerce")
    selected = selected.sort_values(
        ["date", "rank_value", "ticker"],
        ascending=[True, False, True],
        kind="mergesort",
    )
    selected["rank_position"] = selected.groupby("date", sort=False).cumcount() + 1
    valid_dates = selected.groupby("date").size()
    valid_dates = set(valid_dates[valid_dates >= TOP_K].index)
    return selected[
        selected["date"].isin(valid_dates) & selected["rank_position"].le(TOP_K)
    ].copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--runtime-ref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    if EXTERNAL_STAGE_ROOT not in output.parents:
        raise ValueError("output must remain in the isolated alpha staging root")
    paths = {"features": args.features, "panel": args.panel, "official_sessions": args.sessions}
    source_hashes = {name: sha256_file(path) for name, path in paths.items()}
    if source_hashes != EXPECTED_HASHES:
        raise ValueError(f"input hash mismatch: {source_hashes}")

    features = pd.read_parquet(
        args.features,
        columns=[
            "ticker", "date", "eligible_decision_universe",
            *(f"rank_{candidate}" for candidate in CANDIDATES),
        ],
    )
    panel = pd.read_parquet(
        args.panel, columns=["ticker", "date", "regular_market_value"]
    )
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    for table in (features, panel):
        table["ticker"] = table["ticker"].astype("string")
        table["date"] = pd.to_datetime(table["date"], errors="raise").dt.normalize()
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.drop_duplicates("date").sort_values("date", kind="mergesort")
    frozen = sessions.tail(FROZEN_SESSION_COUNT).reset_index(drop=True)
    frozen_dates = set(frozen["date"])
    features = features[features["date"].isin(frozen_dates)].copy()
    panel = panel[panel["date"].isin(frozen_dates)].copy()
    merged = features.merge(panel, on=["ticker", "date"], how="left", validate="one_to_one")
    if merged["regular_market_value"].isna().all() and len(merged):
        raise ValueError("feature/panel value join unexpectedly empty")
    merged["value_state"] = merged["regular_market_value"].map(classify_value)

    results: dict[str, Any] = {
        "all_rows": int(len(merged)),
        "eligible_rows": int(merged["eligible_decision_universe"].astype(bool).sum()),
        "all_row_states": counts(merged),
        "eligible_row_states": counts(merged[merged["eligible_decision_universe"].astype(bool)]),
        "by_candidate_top30": {},
    }
    for candidate in CANDIDATES:
        selected = top_k(merged, candidate)
        results["by_candidate_top30"][candidate] = {
            "complete_dates": int(selected["date"].nunique()),
            "selected_rows": int(len(selected)),
            "states": counts(selected),
        }

    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "admission_status": "BLOCKED_SOURCE_ADMISSION",
        "stage": "EXECUTION_CAPACITY_DENOMINATOR_CENSUS_V1",
        "runtime_ref": args.runtime_ref,
        "runtime_contract_observations": {
            "forward_ohlcv_rejects_nonfinite_or_negative": True,
            "forward_ohlcv_allows_zero": True,
            "execution_verifier_maps_missing_or_invalid_to_zero": True,
            "allocator_zero_clamps_capacity_denominator": True,
            "production_controller_selects_official_predecessor": True,
        },
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "canonical_data_accessed": False,
        "protected_payloads_persisted": False,
        "source_hashes": source_hashes,
        "frozen_session_count": FROZEN_SESSION_COUNT,
        "frozen_window_start": frozen["date"].min().strftime("%Y-%m-%d"),
        "frozen_window_end": frozen["date"].max().strftime("%Y-%m-%d"),
        "candidate_ids": CANDIDATES,
        "top_k": TOP_K,
        "result": results,
        "code_sha256": sha256_file(Path(__file__)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "frozen_window": [result["frozen_window_start"], result["frozen_window_end"]],
        "eligible": result["result"]["eligible_rows"],
        "eligible_states": result["result"]["eligible_row_states"],
    }, indent=2))


if __name__ == "__main__":
    main()
