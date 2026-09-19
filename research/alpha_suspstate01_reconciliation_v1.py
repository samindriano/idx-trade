"""Read-only reconciliation of suspension intervals to NO_TRADE anchors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import sha256_file


INTERVAL_COLUMNS = [
    "ticker", "market", "state", "effective_from", "effective_to",
    "announced_at", "source", "source_ref",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intervals", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--no-trade-anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    intervals = pd.read_csv(args.intervals, usecols=INTERVAL_COLUMNS)
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    no_trade = pd.read_csv(args.no_trade_anchors, usecols=["ticker", "as_of_date"])
    intervals["ticker"] = intervals["ticker"].astype("string")
    intervals["effective_from"] = pd.to_datetime(intervals["effective_from"], errors="raise").dt.normalize()
    intervals["effective_to"] = pd.to_datetime(intervals["effective_to"], errors="coerce").dt.normalize()
    intervals["announced_at"] = pd.to_datetime(intervals["announced_at"], errors="raise")
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    no_trade["ticker"] = no_trade["ticker"].astype("string")
    no_trade["date"] = pd.to_datetime(no_trade["as_of_date"], errors="raise").dt.normalize()

    expanded_rows: list[dict[str, object]] = []
    for interval_id, row in intervals.reset_index(drop=True).iterrows():
        end = row["effective_to"] if pd.notna(row["effective_to"]) else sessions["date"].max()
        matching_dates = sessions.loc[
            sessions["date"].ge(row["effective_from"]) & sessions["date"].le(end), "date"
        ]
        for date in matching_dates:
            expanded_rows.append({
                "interval_id": int(interval_id),
                "ticker": row["ticker"],
                "market": row["market"],
                "date": date,
            })
    expanded = pd.DataFrame(expanded_rows)
    regular = expanded.loc[expanded["market"].eq("REGULAR"), ["ticker", "date"]].drop_duplicates()
    duplicate_mask = expanded.duplicated(["ticker", "market", "date"], keep=False)
    duplicate_groups = expanded.loc[duplicate_mask].groupby(
        ["ticker", "market", "date"], sort=False
    ).size()
    no_trade_keys = no_trade[["ticker", "date"]].drop_duplicates()
    overlap = regular.merge(no_trade_keys, on=["ticker", "date"], how="inner")
    expanded_only = regular.merge(no_trade_keys, on=["ticker", "date"], how="left", indicator=True)
    expanded_only = expanded_only.loc[expanded_only["_merge"].eq("left_only"), ["ticker", "date"]]
    no_trade_only = no_trade_keys.merge(regular, on=["ticker", "date"], how="left", indicator=True)
    no_trade_only = no_trade_only.loc[no_trade_only["_merge"].eq("left_only"), ["ticker", "date"]]

    durations = (intervals["effective_to"] - intervals["effective_from"]).dt.days + 1
    finite_durations = durations.dropna()
    checks = {
        "required_columns_present": set(INTERVAL_COLUMNS).issubset(intervals.columns),
        "interval_state_exact": set(intervals["state"].astype(str)) == {"SUSPENDED"},
        "source_exact": set(intervals["source"].astype(str)) == {"IDX_EXCHANGE_ANNOUNCEMENT"},
        "date_order_valid": bool((intervals["effective_to"].isna() | intervals["effective_to"].ge(intervals["effective_from"])).all()),
        "announcement_not_after_effective": bool((intervals["announced_at"].dt.normalize() <= intervals["effective_from"]).all()),
        "source_refs_nonnull": bool(intervals["source_ref"].notna().all()),
        "interval_sessions_official": bool(expanded["date"].isin(sessions["date"]).all()),
        "expanded_key_unique": int(expanded.duplicated(["ticker", "market", "date"]).sum()) == 0,
        "regular_market_present": int((intervals["market"] == "REGULAR").sum()) > 0,
        "no_trade_anchor_keys_unique": int(no_trade_keys.duplicated(["ticker", "date"]).sum()) == 0,
    }
    result = {
        "hypothesis_id": "SUSPSTATE-01",
        "stage": "SUSPSTATE01_INTERVAL_TO_NO_TRADE_RECONCILIATION",
        "status": "PASS_NARROW_RECONCILIATION_GLOBAL_STATE_UNKNOWN" if all(checks.values()) else "SOURCE_BLOCKED",
        "code_sha256": sha256_file(Path(__file__)),
        "source_hashes": {
            "intervals": sha256_file(args.intervals),
            "official_sessions": sha256_file(args.sessions),
            "no_trade_anchors": sha256_file(args.no_trade_anchors),
        },
        "checks": checks,
        "outcome_accessed": False,
        "provider_accessed": False,
        "candidate_id_created": False,
        "interval_inventory": {
            "rows": int(len(intervals)),
            "tickers": int(intervals["ticker"].nunique()),
            "market_counts": {str(k): int(v) for k, v in intervals["market"].value_counts().items()},
            "open_intervals": int(intervals["effective_to"].isna().sum()),
            "effective_from_min": str(intervals["effective_from"].min().date()),
            "effective_from_max": str(intervals["effective_from"].max().date()),
            "duration_finite_count": int(finite_durations.size),
            "duration_min_days": int(finite_durations.min()) if len(finite_durations) else None,
            "duration_median_days": float(finite_durations.median()) if len(finite_durations) else None,
            "duration_max_days": int(finite_durations.max()) if len(finite_durations) else None,
            "source_ref_count": int(intervals["source_ref"].nunique()),
        },
        "expansion": {
            "official_session_count": int(sessions["date"].nunique()),
            "expanded_market_rows": int(len(expanded)),
            "expanded_unique_keys": int(expanded[["ticker", "market", "date"]].drop_duplicates().shape[0]),
            "expanded_duplicate_rows": int(duplicate_mask.sum()),
            "expanded_duplicate_key_groups": int(len(duplicate_groups)),
            "regular_expanded_duplicate_rows": int(
                expanded.loc[expanded["market"].eq("REGULAR")].duplicated(
                    ["ticker", "market", "date"], keep=False
                ).sum()
            ),
            "expanded_market_counts": {str(k): int(v) for k, v in expanded["market"].value_counts().items()},
            "regular_expanded_rows": int(len(regular)),
            "no_trade_anchor_rows": int(len(no_trade_keys)),
            "regular_interval_no_trade_overlap": int(len(overlap)),
            "regular_interval_not_no_trade": int(len(expanded_only)),
            "no_trade_not_covered_by_regular_interval": int(len(no_trade_only)),
        },
        "interpretation": {
            "admissibility": "PARTIAL",
            "state_semantics_status": "UNKNOWN_NO_TRADE_NOT_EQ_SUSPENSION",
            "publication_semantics_status": "UNKNOWN_ANNOUNCEMENT_NOT_ROW_LEVEL_AVAILABLE_AT",
            "predictive_claim": False,
            "status_change_authorized": False,
        },
        "scope": {
            "outcome_accessed": False,
            "provider_accessed": False,
            "cloud_accessed": False,
            "incumbent_predictive_accessed": False,
        },
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] == "SOURCE_BLOCKED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
