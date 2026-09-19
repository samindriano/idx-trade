"""Independent target-free verifier for SUSPSTATE-01 reconciliation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from alpha_stage_a_v2 import sha256_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--intervals", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--no-trade-anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    intervals = pd.read_csv(args.intervals)
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    no_trade = pd.read_csv(args.no_trade_anchors, usecols=["ticker", "as_of_date"])
    intervals["ticker"] = intervals["ticker"].astype("string")
    intervals["effective_from"] = pd.to_datetime(intervals["effective_from"], errors="raise").dt.normalize()
    intervals["effective_to"] = pd.to_datetime(intervals["effective_to"], errors="coerce").dt.normalize()
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    no_trade["ticker"] = no_trade["ticker"].astype("string")
    no_trade["date"] = pd.to_datetime(no_trade["as_of_date"], errors="raise").dt.normalize()
    expanded_rows: list[tuple[str, str, pd.Timestamp]] = []
    for row in intervals.itertuples(index=False):
        end = row.effective_to if pd.notna(row.effective_to) else sessions["date"].max()
        for date in sessions.loc[sessions["date"].ge(row.effective_from) & sessions["date"].le(end), "date"]:
            expanded_rows.append((str(row.ticker), str(row.market), pd.Timestamp(date)))
    expanded = pd.DataFrame(expanded_rows, columns=["ticker", "market", "date"])
    regular = expanded.loc[expanded["market"].eq("REGULAR"), ["ticker", "date"]].drop_duplicates()
    no_keys = no_trade[["ticker", "date"]].drop_duplicates()
    overlap = regular.merge(no_keys, on=["ticker", "date"], how="inner")
    duplicate_mask = expanded.duplicated(["ticker", "market", "date"], keep=False)
    checks = {
        "artifact_status_blocked": artifact.get("status") == "SOURCE_BLOCKED",
        "artifact_stage": artifact.get("stage") == "SUSPSTATE01_INTERVAL_TO_NO_TRADE_RECONCILIATION",
        "no_outcome_access": artifact.get("outcome_accessed") is False,
        "no_provider_access": artifact.get("provider_accessed") is False,
        "code_hash": artifact.get("code_sha256") == sha256_file(args.code),
        "interval_hash": artifact.get("source_hashes", {}).get("intervals") == sha256_file(args.intervals),
        "sessions_hash": artifact.get("source_hashes", {}).get("official_sessions") == sha256_file(args.sessions),
        "no_trade_hash": artifact.get("source_hashes", {}).get("no_trade_anchors") == sha256_file(args.no_trade_anchors),
        "expanded_rows": len(expanded) == artifact["expansion"]["expanded_market_rows"],
        "expanded_unique_keys": int(expanded.drop_duplicates(["ticker", "market", "date"]).shape[0]) == artifact["expansion"]["expanded_unique_keys"],
        "expanded_duplicate_groups": int(expanded.loc[duplicate_mask].groupby(["ticker", "market", "date"]).ngroups) == artifact["expansion"]["expanded_duplicate_key_groups"],
        "regular_overlap": len(overlap) == artifact["expansion"]["regular_interval_no_trade_overlap"],
        "regular_not_no_trade": int(len(regular.merge(no_keys, on=["ticker", "date"], how="left", indicator=True).query("_merge == 'left_only'"))) == artifact["expansion"]["regular_interval_not_no_trade"],
        "state_exact": set(intervals["state"].astype(str)) == {"SUSPENDED"},
        "announced_not_after_effective": bool((pd.to_datetime(intervals["announced_at"]).dt.normalize() <= intervals["effective_from"]).all()),
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verification_type": "independent_suspension_interval_reconciliation_target_free",
        "artifact_sha256": sha256_file(args.artifact),
        "verifier_code_sha256": sha256_file(Path(__file__)),
        "checks": checks,
        "recomputed": {
            "interval_rows": int(len(intervals)),
            "expanded_market_rows": int(len(expanded)),
            "expanded_unique_keys": int(expanded.drop_duplicates(["ticker", "market", "date"]).shape[0]),
            "expanded_duplicate_rows": int(duplicate_mask.sum()),
            "expanded_duplicate_key_groups": int(expanded.loc[duplicate_mask].groupby(["ticker", "market", "date"]).ngroups),
            "regular_expanded_unique_rows": int(len(regular)),
            "regular_overlap": int(len(overlap)),
        },
        "scope": {"outcome_accessed": False, "provider_accessed": False, "cloud_accessed": False},
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
