"""Eligible-universe correction replay of combination structural economics.

This wrapper preserves V1 formulas, equal weights, and friction scenarios but
computes daily value/volume percentiles only within eligible decision rows.
V1 remains preserved and is not overwritten.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_combination_economics_v1 import (
    COMPONENTS,
    COMBINATIONS,
    FRICTION_SCENARIOS,
    FROZEN_SESSION_COUNT,
    combination_metrics,
    finite_float,
    scenario_contracts,
    sha256_file,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    feature_columns = [
        "ticker", "date", "eligible_decision_universe", *COMPONENTS.values()
    ]
    features = pd.read_parquet(args.features, columns=feature_columns)
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    panel = pd.read_parquet(
        args.panel,
        columns=["ticker", "date", "regular_market_value", "volume"],
    )
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    if features.duplicated(["ticker", "date"]).any():
        raise ValueError("features contain duplicate ticker/date keys")
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel contains duplicate ticker/date keys")

    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.drop_duplicates("date").sort_values("date", kind="mergesort").reset_index(drop=True)
    if len(sessions) < FROZEN_SESSION_COUNT:
        raise ValueError("official session source is shorter than frozen window")
    frozen_sessions = sessions.tail(FROZEN_SESSION_COUNT).copy().reset_index(drop=True)
    frozen_dates = set(frozen_sessions["date"])
    features = features[features["date"].isin(frozen_dates)].copy()
    frame = features.merge(
        panel, on=["ticker", "date"], how="left", validate="one_to_one", indicator=True
    )
    if not frame["_merge"].eq("both").all():
        raise ValueError("feature/panel key closure failed")
    frame = frame.drop(columns=["_merge"])
    for column in COMPONENTS.values():
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    eligible = frame["eligible_decision_universe"].astype(bool)
    frame["value_percentile"] = np.nan
    frame["volume_percentile"] = np.nan
    eligible_rows = frame.loc[eligible]
    frame.loc[eligible_rows.index, "value_percentile"] = eligible_rows.groupby("date")[
        "regular_market_value"
    ].rank(pct=True, method="average")
    frame.loc[eligible_rows.index, "volume_percentile"] = eligible_rows.groupby("date")[
        "volume"
    ].rank(pct=True, method="average")

    for name, components in COMBINATIONS.items():
        columns = [COMPONENTS[component] for component in components]
        frame[f"combo_{name}"] = frame[columns].mean(axis=1, skipna=False)

    session_index = dict(zip(frozen_sessions["date"], frozen_sessions.index, strict=True))
    scenario_map = scenario_contracts()
    combinations = {
        name: combination_metrics(frame, name, components, session_index, scenario_map)
        for name, components in COMBINATIONS.items()
    }
    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "M_COMBINATION_READINESS_L_IMPLEMENTATION_ECONOMICS_V2",
        "implementation": "alpha_combination_economics_v2_eligible_percentiles",
        "supersedes_interpretation_of": "alpha_combination_economics_v1 liquidity exposure only",
        "correction": "daily liquidity percentiles ranked within eligible decision universe",
        "outcome_accessed": False,
        "provider_accessed": False,
        "target_accessed": False,
        "incumbent_score_accessed": False,
        "candidate_id_created": False,
        "frozen_session_count": FROZEN_SESSION_COUNT,
        "frozen_window_start": frozen_sessions["date"].min().strftime("%Y-%m-%d"),
        "frozen_window_end": frozen_sessions["date"].max().strftime("%Y-%m-%d"),
        "combination_budget": {
            "exact_set": list(COMBINATIONS),
            "weight_policy": "equal weights only",
            "no_weight_optimization": True,
            "no_new_candidate_ids": True,
        },
        "percentile_contract": {
            "universe": "eligible_decision_universe=true rows only",
            "grouping": "date",
            "non_eligible_percentile": None,
            "eligible_rows": int(eligible.sum()),
            "eligible_dates": int(frame.loc[eligible, "date"].nunique()),
        },
        "friction_scenarios": scenario_map,
        "source_hashes": {
            "features": sha256_file(args.features),
            "panel": sha256_file(args.panel),
            "official_sessions": sha256_file(args.sessions),
        },
        "code_sha256": sha256_file(Path(__file__)),
        "combinations": combinations,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "output_sha256": sha256_file(args.output),
        "code_sha256": result["code_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()

