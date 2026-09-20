"""Outcome-blind native versus common-support census for C1-C4.

This is a support/methodology artifact only. It never reads targets, labels,
forward returns, incumbent scores, providers, or cloud state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


CANDIDATES = {
    "C1": "C1_residual_reversal_5_v1",
    "C2": "C2_participation_confirmation_5_v1",
    "C3": "C3_financial_quality_growth_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}
REQUIRED_COLUMNS = {"ticker", "date", "eligible_decision_universe", *CANDIDATES.values()}
FORBIDDEN_COLUMNS = {
    "target",
    "label",
    "forward_return",
    "realized_return",
    "pnl",
    "incumbent_score",
    "ic",
    "icir",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    features_path = args.features.resolve()
    output_path = args.output.resolve()
    frame = pd.read_parquet(features_path)
    columns = set(frame.columns)
    missing = REQUIRED_COLUMNS.difference(columns)
    forbidden = sorted(column for column in columns if column.lower() in FORBIDDEN_COLUMNS)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if forbidden:
        raise ValueError(f"protected-looking columns present: {forbidden}")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.strftime("%Y-%m-%d")
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("duplicate ticker/date keys")
    eligible = frame["eligible_decision_universe"].astype(bool)
    finite = pd.DataFrame({candidate: pd.to_numeric(frame[column], errors="coerce").notna() for candidate, column in CANDIDATES.items()})
    native = {candidate: int((eligible & finite[candidate]).sum()) for candidate in CANDIDATES}
    all_four = eligible & finite.all(axis=1)

    pairwise: dict[str, int] = {}
    names = list(CANDIDATES)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            pairwise[f"{left}+{right}"] = int((eligible & finite[left] & finite[right]).sum())

    common_daily = all_four.groupby(frame["date"]).sum()
    result = {
        "status": "PASS",
        "scope": "OUTCOME_BLIND_STRUCTURAL_SUPPORT_ONLY",
        "code_sha256": sha256_file(Path(__file__).resolve()),
        "input": {
            "path": str(features_path),
            "sha256": sha256_file(features_path),
            "rows": int(len(frame)),
            "unique_keys": True,
            "eligible_rows": int(eligible.sum()),
            "dates": int(frame["date"].nunique()),
        },
        "candidate_columns": CANDIDATES,
        "native_support_rows": native,
        "pairwise_common_support_rows": pairwise,
        "all_four_common_support_rows": int(all_four.sum()),
        "native_to_all_four_loss_rows": {candidate: native[candidate] - int(all_four.sum()) for candidate in CANDIDATES},
        "all_four_common_support_fraction_of_eligible": float(all_four.sum() / eligible.sum()) if eligible.sum() else None,
        "daily_all_four_common_support": {
            "date_count": int(len(common_daily)),
            "min_names": int(common_daily.min()) if len(common_daily) else None,
            "median_names": float(common_daily.median()) if len(common_daily) else None,
            "max_names": int(common_daily.max()) if len(common_daily) else None,
            "dates_with_at_least_30_names": int((common_daily >= 30).sum()) if len(common_daily) else 0,
        },
        "interpretation": [
            "Native support is candidate-specific finite score support inside the current eligibility mask.",
            "Common support is the exact ticker/date intersection where all four candidate scores are finite inside the current mask.",
            "This census does not choose an eligibility policy, alter the population, or evaluate any outcome.",
            "The current min_periods=60 versus minimum-20 conflict remains upstream and unresolved.",
        ],
        "limitations": [
            "Structural support is not predictive common-support evidence.",
            "C3 sparsity may dominate the four-way intersection.",
            "Current population and finite-score semantics remain subject to policy/PIT/CA admission.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
