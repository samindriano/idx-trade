"""Target-free audit of official regular-market execution-state anchors."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import build_decision_universe, sha256_file


ANCHOR_COLUMNS = ["ticker", "market", "as_of_date", "state", "source", "source_ref", "evidence_type"]
RAW_COLUMNS = [
    "ticker", "as_of_date", "volume", "frequency", "regular_value",
    "nonregular_volume", "nonregular_frequency",
]
EXPECTED_SESSION_HASH = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_ANCHOR_HASH = "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e"
EXPECTED_SOURCE = "IDX_PUBLIC_STOCK_SUMMARY"


def inventory_hash(cache_dir: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(cache_dir).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--regular-anchors", type=Path, required=True)
    parser.add_argument("--no-trade-anchors", type=Path, required=True)
    parser.add_argument("--session-report", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--tradability-anchors", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    anchors = pd.read_csv(args.anchors, usecols=ANCHOR_COLUMNS)
    regular = pd.read_csv(args.regular_anchors, usecols=ANCHOR_COLUMNS)
    no_trade = pd.read_csv(args.no_trade_anchors, usecols=ANCHOR_COLUMNS)
    report = pd.read_csv(args.session_report)
    for frame in [anchors, regular, no_trade]:
        frame["ticker"] = frame["ticker"].astype("string")
        frame["as_of_date"] = pd.to_datetime(frame["as_of_date"], errors="raise").dt.normalize()
    report["session"] = pd.to_datetime(report["session"], errors="raise").dt.normalize()
    session_dates = pd.read_csv(args.sessions, usecols=["date"])
    session_dates["date"] = pd.to_datetime(session_dates["date"], errors="raise").dt.normalize()

    parquet_files = sorted(args.cache_dir.glob("*.parquet"))
    meta_files = sorted(args.cache_dir.glob("*.meta.json"))
    raw_frames = []
    for path in parquet_files:
        frame = pd.read_parquet(path, columns=RAW_COLUMNS)
        frame["ticker"] = frame["ticker"].astype("string")
        frame["as_of_date"] = pd.to_datetime(frame["as_of_date"], errors="raise").dt.normalize()
        raw_frames.append(frame)
    raw = pd.concat(raw_frames, ignore_index=True)
    numeric = raw[["volume", "frequency", "regular_value", "nonregular_volume", "nonregular_frequency"]].apply(
        pd.to_numeric, errors="coerce"
    )
    raw["nonregular_activity"] = numeric["nonregular_volume"].gt(0) | numeric["nonregular_frequency"].gt(0)
    raw["regular_positive"] = numeric[["volume", "frequency", "regular_value"]].gt(0).all(axis=1)
    raw["regular_zero"] = numeric[["volume", "frequency", "regular_value"]].eq(0).all(axis=1)

    merged = anchors.merge(
        raw, on=["ticker", "as_of_date"], how="outer", indicator=True, validate="one_to_one"
    )
    merged["state"] = merged["state"].astype("string")
    state_active = merged["state"].eq("ACTIVE")
    state_no_trade = merged["state"].eq("NO_TRADE")
    no_trade_nonregular = state_no_trade & merged["nonregular_activity"].fillna(False)
    active_nonregular = state_active & merged["nonregular_activity"].fillna(False)

    panel = pd.read_parquet(args.panel, columns=["ticker", "date", "regular_market_value"])
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    universe, _ = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions,
        args.tradability_anchors,
    )
    panel_state = universe.merge(
        panel, on=["ticker", "date"], how="left", validate="one_to_one"
    ).merge(
        merged[["ticker", "as_of_date", "state", "nonregular_activity"]],
        left_on=["ticker", "date"], right_on=["ticker", "as_of_date"],
        how="left", validate="one_to_one",
    )
    panel_state["regular_market_value"] = pd.to_numeric(panel_state["regular_market_value"], errors="coerce")
    eligible_no_trade_nonregular = (
        panel_state["eligible_decision_universe"]
        & panel_state["state"].eq("NO_TRADE")
        & panel_state["nonregular_activity"].astype("boolean").fillna(False)
    )
    value_valid = eligible_no_trade_nonregular & panel_state["regular_market_value"].gt(0)
    value_percentile = panel_state.loc[value_valid].groupby("date")["regular_market_value"].rank(
        pct=True, method="average"
    )

    transitions = 0
    transition_tickers = 0
    max_transitions = 0
    for _, group in anchors.sort_values(["ticker", "as_of_date"], kind="mergesort").groupby("ticker", sort=False):
        count = int(group["state"].ne(group["state"].shift()).sum() - 1)
        transitions += max(count, 0)
        transition_tickers += int(count > 0)
        max_transitions = max(max_transitions, count)

    checks = {
        "anchor_keys_unique": int(anchors.duplicated(["ticker", "as_of_date"]).sum()) == 0,
        "regular_keys_unique": int(regular.duplicated(["ticker", "as_of_date"]).sum()) == 0,
        "no_trade_keys_unique": int(no_trade.duplicated(["ticker", "as_of_date"]).sum()) == 0,
        "anchors_source_exact": set(anchors["source"].astype(str)) == {EXPECTED_SOURCE},
        "anchors_market_regular": set(anchors["market"].astype(str)) == {"REGULAR"},
        "states_allowed": set(anchors["state"].astype(str)).issubset({"ACTIVE", "NO_TRADE"}),
        "required_anchor_nonnull": bool(anchors[ANCHOR_COLUMNS].notna().all().all()),
        "official_dates": set(anchors["as_of_date"].unique()).issubset(set(session_dates["date"].unique())),
        "official_session_hash": sha256_file(args.sessions) == EXPECTED_SESSION_HASH,
        "tradability_anchor_hash": sha256_file(args.tradability_anchors) == EXPECTED_ANCHOR_HASH,
        "raw_keys_exact": bool(merged["_merge"].eq("both").all()),
        "active_positive_regular_fields": bool(merged.loc[state_active, "regular_positive"].all()),
        "no_trade_zero_regular_fields": bool(merged.loc[state_no_trade, "regular_zero"].all()),
        "regular_subset_exact": len(regular) == int(state_active.sum()),
        "no_trade_subset_exact": len(no_trade) == int(state_no_trade.sum()),
        "session_report_all_ok": bool(report["status"].eq("OK").all()),
        "session_report_unresolved_zero": int(report["unresolved_rows"].sum()) == 0,
        "session_report_anchor_sum": int(report["anchor_rows"].sum()) == len(anchors),
        "session_report_active_sum": int(report["active_rows"].sum()) == int(state_active.sum()),
        "session_report_no_trade_sum": int(report["no_trade_rows"].sum()) == int(state_no_trade.sum()),
        "session_report_dates_exact": set(report["session"]) == set(session_dates["date"]),
        "panel_only_zero": len(panel.merge(anchors[["ticker", "as_of_date"]], left_on=["ticker", "date"], right_on=["ticker", "as_of_date"], how="left", indicator=True).query("_merge == 'left_only'")) == 0,
        "diagnostic_nonempty": int(no_trade_nonregular.sum()) > 0,
    }
    result = {
        "hypothesis_id": "EXECSTATE-01",
        "stage": "EXECSTATE01_OFFICIAL_EXECUTION_STATE_SOURCE_AUDIT",
        "status": "SOURCE_PARTIAL_STRUCTURAL_SIGNAL" if all(checks.values()) else "SOURCE_BLOCKED",
        "code_sha256": sha256_file(Path(__file__)),
        "source_hashes": {
            "anchors": sha256_file(args.anchors),
            "regular_anchors": sha256_file(args.regular_anchors),
            "no_trade_anchors": sha256_file(args.no_trade_anchors),
            "session_report": sha256_file(args.session_report),
            "official_sessions": sha256_file(args.sessions),
            "tradability_anchors": sha256_file(args.tradability_anchors),
            "panel": sha256_file(args.panel),
            "security_master": sha256_file(args.security_master),
            "cache_inventory": inventory_hash(args.cache_dir, sorted(parquet_files + meta_files)),
        },
        "checks": checks,
        "outcome_accessed": False,
        "provider_accessed": False,
        "candidate_id_created": False,
        "source": {
            "anchor_rows": int(len(anchors)),
            "active_rows": int(state_active.sum()),
            "no_trade_rows": int(state_no_trade.sum()),
            "tickers": int(anchors["ticker"].nunique()),
            "dates": int(anchors["as_of_date"].nunique()),
            "cache_rows": int(len(raw)),
            "cache_only_rows": int(merged["_merge"].eq("right_only").sum()),
            "panel_overlap_rows": int(panel.merge(anchors[["ticker", "as_of_date"]], left_on=["ticker", "date"], right_on=["ticker", "as_of_date"], how="inner").shape[0]),
            "no_trade_nonregular_rows": int(no_trade_nonregular.sum()),
            "active_nonregular_rows": int(active_nonregular.sum()),
            "no_trade_nonregular_dates": int(merged.loc[no_trade_nonregular, "as_of_date"].nunique()),
            "no_trade_nonregular_tickers": int(merged.loc[no_trade_nonregular, "ticker"].nunique()),
            "state_transitions": transitions,
            "tickers_with_state_transitions": transition_tickers,
            "max_ticker_state_transitions": max_transitions,
            "session_report_rows": int(len(report)),
        },
        "eligible_diagnostic": {
            "eligible_rows": int(panel_state["eligible_decision_universe"].sum()),
            "eligible_no_trade_nonregular_rows": int(eligible_no_trade_nonregular.sum()),
            "eligible_no_trade_nonregular_dates": int(panel_state.loc[eligible_no_trade_nonregular, "date"].nunique()),
            "eligible_no_trade_nonregular_tickers": int(panel_state.loc[eligible_no_trade_nonregular, "ticker"].nunique()),
            "bottom_value_q1_share": float(value_percentile.le(0.25).mean()) if len(value_percentile) else None,
            "bottom_value_q1_rows": int(value_percentile.size),
        },
        "interpretation": {
            "admissibility": "PARTIAL",
            "mechanism": "regular-market no-trade state with nonregular activity",
            "state_semantics_status": "UNKNOWN_PENDING_EXCHANGE_DEFINITION_AND_COMPLETENESS",
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
