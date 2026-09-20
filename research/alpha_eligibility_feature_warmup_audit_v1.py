"""Separate eligibility gating from candidate feature warm-up.

This outcome-blind audit reads only the guarded feature artifact. It measures
whether finite candidate scores exist outside the current eligibility mask and
then decomposes missingness inside eligible rows. It does not read targets,
forward returns, protected outcomes, or provider/canonical state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CANDIDATES = {
    "C1": "C1_residual_reversal_5_v1",
    "C2": "C2_participation_confirmation_5_v1",
    "C3": "C3_financial_quality_growth_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}
FEATURE_COLUMNS = ["ticker", "date", "eligible_decision_universe", *CANDIDATES.values()]
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_mask(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values)


def summarize(features: pd.DataFrame) -> dict[str, Any]:
    missing = set(FEATURE_COLUMNS).difference(features.columns)
    if missing:
        raise ValueError(f"missing feature columns: {sorted(missing)}")
    frame = features[FEATURE_COLUMNS].copy()
    frame["ticker"] = frame["ticker"].astype("string")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("duplicate ticker/date keys")
    eligible = frame["eligible_decision_universe"].astype("boolean").fillna(False).astype(bool)
    candidates: dict[str, Any] = {}
    for candidate, column in CANDIDATES.items():
        finite = finite_mask(frame[column])
        eligible_finite = eligible & finite
        eligible_missing = eligible & ~finite
        outside_finite = ~eligible & finite
        first_eligible = frame.loc[eligible].groupby("ticker")["date"].min()
        first_finite = frame.loc[finite].groupby("ticker")["date"].min()
        aligned = pd.concat(
            [first_eligible.rename("eligible"), first_finite.rename("finite")], axis=1
        ).dropna()
        day_delta = (aligned["finite"] - aligned["eligible"]).dt.days
        candidates[candidate] = {
            "score_column": column,
            "all_rows": int(len(frame)),
            "eligible_rows": int(eligible.sum()),
            "all_finite_rows": int(finite.sum()),
            "eligible_finite_rows": int(eligible_finite.sum()),
            "eligible_missing_rows": int(eligible_missing.sum()),
            "outside_eligible_finite_rows": int(outside_finite.sum()),
            "finite_outside_eligibility_is_zero": int(outside_finite.sum()) == 0,
            "tickers_with_both_first_dates": int(len(aligned)),
            "tickers_finite_after_first_eligibility": int((day_delta > 0).sum()),
            "tickers_finite_same_or_before_first_eligibility": int((day_delta <= 0).sum()),
            "median_first_finite_minus_eligible_days": float(day_delta.median()) if len(day_delta) else None,
            "max_first_finite_minus_eligible_days": int(day_delta.max()) if len(day_delta) else None,
        }
    all_gated = all(row["finite_outside_eligibility_is_zero"] for row in candidates.values())
    return {
        "status": "PASS_ELIGIBILITY_FEATURE_WARMUP_SEPARATION" if all_gated else "FAIL_SCORE_OUTSIDE_ELIGIBILITY",
        "scope": "Outcome-blind eligibility-gating versus feature warm-up decomposition",
        "rows": int(len(frame)),
        "ticker_count": int(frame["ticker"].nunique()),
        "date_count": int(frame["date"].nunique()),
        "eligible_rows": int(eligible.sum()),
        "all_candidates_score_gated_by_eligibility": all_gated,
        "candidates": candidates,
        "protected_boundary": "CLOSED",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    if any(marker in str(args.features).lower() for marker in FORBIDDEN_INPUT_MARKERS):
        raise ValueError(f"refusing input path with protected-data marker: {args.features}")
    features = pd.read_parquet(args.features, columns=FEATURE_COLUMNS)
    result = summarize(features)
    result["inputs"] = {
        "features": {
            "path": str(args.features),
            "sha256": sha256_file(args.features),
            "rows": int(len(features)),
        }
    }
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if not result["all_candidates_score_gated_by_eligibility"]:
        raise ValueError("candidate score exists outside eligibility")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
