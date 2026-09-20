"""Outcome-blind missingness companion check for component anatomy V1.

The original component-anatomy result compared finite stored and recomputed
values. This companion verifies the stronger full-mask property: within the
eligible decision universe, stored and recomputed score finiteness agree for
every C1/C2/C4 key. It reads no targets or protected outcomes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from research.alpha_candidate_component_anatomy_v1 import (
    CANDIDATES,
    FORBIDDEN_INPUT_MARKERS,
    PANEL_COLUMNS,
    build_components,
    prepare_surface,
    sha256_file,
)


def score_finite_mask(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    return frame["eligible_decision_universe"] & values.notna() & np.isfinite(values)


def missingness_report(surface: pd.DataFrame) -> dict[str, Any]:
    candidates: dict[str, Any] = {}
    all_match = True
    for candidate, stored_column in CANDIDATES.items():
        recomputed_column = f"{candidate.lower()}_score_recomputed"
        stored_finite = score_finite_mask(surface, stored_column)
        recomputed_finite = score_finite_mask(surface, recomputed_column)
        mismatch = stored_finite ^ recomputed_finite
        mismatch_count = int(mismatch.sum())
        stored_count = int(stored_finite.sum())
        recomputed_count = int(recomputed_finite.sum())
        match = mismatch_count == 0
        all_match = all_match and match
        candidates[candidate] = {
            "eligible_rows": int(surface["eligible_decision_universe"].sum()),
            "stored_finite_rows": stored_count,
            "recomputed_finite_rows": recomputed_count,
            "missingness_mismatch_rows": mismatch_count,
            "formula_missingness_match": match,
        }
    return {
        "status": "PASS_FORMULA_MISSINGNESS_MATCH" if all_match else "FAIL_FORMULA_MISSINGNESS_MISMATCH",
        "all_candidates_match": all_match,
        "candidates": candidates,
    }


def summarize(features: pd.DataFrame, panel: pd.DataFrame, official_dates: pd.Series | pd.Index) -> dict[str, Any]:
    surface, official = prepare_surface(features, panel, official_dates)
    surface = build_components(surface, official)
    result = missingness_report(surface)
    result["calendar"] = {
        "official_session_count": int(len(official)),
        "official_min": str(official.min().date()) if len(official) else None,
        "official_max": str(official.max().date()) if len(official) else None,
    }
    result["panel_rows"] = int(len(panel))
    result["surface_rows"] = int(len(surface))
    return result


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    for path in (args.features, args.panel, args.sessions):
        if any(marker in str(path).lower() for marker in FORBIDDEN_INPUT_MARKERS):
            raise ValueError(f"refusing input path with protected-data marker: {path}")
    features = pd.read_parquet(args.features)
    panel = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    result = summarize(features, panel, sessions["date"])
    result["inputs"] = {
        "features": {"path": str(args.features), "sha256": sha256_file(args.features), "rows": int(len(features))},
        "panel": {"path": str(args.panel), "sha256": sha256_file(args.panel), "rows": int(len(panel))},
        "official_sessions": {"path": str(args.sessions), "sha256": sha256_file(args.sessions)},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if not result["all_candidates_match"]:
        raise ValueError("component formula missingness mismatch")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
