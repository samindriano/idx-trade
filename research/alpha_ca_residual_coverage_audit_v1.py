"""Read-only coverage check for unresolved price-basis rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from alpha_stage_a_v2 import sha256_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--residual", type=Path, required=True)
    parser.add_argument("--hlc", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    residual = pd.read_csv(args.residual)
    hlc = pd.read_csv(args.hlc)
    security_master = pd.read_csv(args.security_master)
    for frame in [residual, hlc]:
        frame["ticker"] = frame["ticker"].astype("string")
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    security_master["ticker"] = security_master["ticker"].astype("string")
    security_master["listed_from"] = pd.to_datetime(security_master["listed_from"], errors="raise").dt.normalize()
    security_master["listed_to"] = pd.to_datetime(security_master["listed_to"], errors="coerce").dt.normalize()

    residual_keys = residual[["ticker", "date"]].drop_duplicates()
    hlc_keys = hlc[["ticker", "date"]].drop_duplicates()
    overlap = residual_keys.merge(hlc_keys, on=["ticker", "date"], how="inner")
    active_counts: list[int] = []
    for row in residual_keys.itertuples(index=False):
        active = security_master[
            (security_master["ticker"] == row.ticker)
            & security_master["listed_from"].le(row.date)
            & (security_master["listed_to"].isna() | security_master["listed_to"].ge(row.date))
        ]
        active_counts.append(int(len(active)))
    active_series = pd.Series(active_counts, dtype="int64")
    checks = {
        "residual_keys_unique": len(residual) == len(residual_keys),
        "residual_hlc_overlap_zero": len(overlap) == 0,
        "all_residual_keys_one_active_interval": bool(active_series.eq(1).all()),
        "no_zero_active_intervals": bool(active_series.ne(0).all()),
    }
    result = {
        "stage": "CA_RESIDUAL_COVERAGE_AUDIT",
        "status": "PASS_NARROW_RESIDUAL_COVERAGE_GLOBAL_BASIS_BLOCKED" if all(checks.values()) else "FAIL",
        "code_sha256": sha256_file(Path(__file__)),
        "source_hashes": {
            "residual": sha256_file(args.residual),
            "hlc": sha256_file(args.hlc),
            "security_master": sha256_file(args.security_master),
        },
        "checks": checks,
        "recomputed": {
            "residual_rows": int(len(residual)),
            "residual_unique_keys": int(len(residual_keys)),
            "residual_tickers": int(residual["ticker"].nunique()),
            "hlc_rows": int(len(hlc)),
            "residual_hlc_overlap": int(len(overlap)),
            "active_interval_counts": {str(k): int(v) for k, v in active_series.value_counts().sort_index().items()},
        },
        "interpretation": {
            "outcome_accessed": False,
            "provider_accessed": False,
            "global_corporate_action_basis_admitted": False,
            "residual_rows_resolved": False,
        },
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
