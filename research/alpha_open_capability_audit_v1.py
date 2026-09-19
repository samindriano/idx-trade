"""Read-only capability audit for the frozen historical Open field."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import build_decision_universe


PANEL_COLUMNS = [
    "ticker", "date", "open", "open_available", "open_evidence_status",
    "price_provenance", "corporate_action_integrity_verified", "signal_contract",
    "high", "low", "close", "volume", "regular_market_value",
]
EXPECTED_HASHES = {
    "panel": "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e",
    "sessions": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "anchors": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
}
EXTERNAL_STAGE_ROOT = Path(r"D:\Documents\Project\idx-alpha-available-data-staging-20260919").resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pct(numerator: int, denominator: int) -> float | None:
    return float(numerator / denominator) if denominator else None


def counts(series: pd.Series) -> dict[str, int]:
    return {("<NA>" if pd.isna(key) else str(key)): int(value) for key, value in series.value_counts(dropna=False).items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--repo-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    if EXTERNAL_STAGE_ROOT not in output.parents:
        raise ValueError("refusing output outside isolated alpha staging")
    paths = {"panel": args.panel, "sessions": args.sessions, "anchors": args.anchors}
    actual_hashes = {name: sha256_file(path) for name, path in paths.items()}
    if actual_hashes != EXPECTED_HASHES:
        raise ValueError(f"input hash mismatch: {actual_hashes}")

    panel = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    for column in ["open", "high", "low", "close", "volume", "regular_market_value"]:
        panel[column] = pd.to_numeric(panel[column], errors="coerce")
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel duplicate ticker/date keys")
    panel["open_available_bool"] = panel["open_available"].fillna(False).astype(bool)
    panel["open_positive_finite"] = panel["open"].gt(0) & np.isfinite(panel["open"])
    panel["open_range_valid"] = panel["open_positive_finite"] & panel["high"].gt(0) & panel["low"].gt(0) & panel["open"].between(panel["low"], panel["high"], inclusive="both")

    universe, universe_stats = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors
    )
    full = universe.merge(panel, on=["ticker", "date"], how="left", validate="one_to_one")
    eligible = full["eligible_decision_universe"].astype(bool)
    open_present = eligible & full["open_positive_finite"]
    open_flag = eligible & full["open_available_bool"]

    by_date = full.loc[eligible].groupby("date", sort=True)["open_positive_finite"].sum()
    by_ticker = full.loc[eligible].groupby("ticker", sort=True)["open_positive_finite"].sum()
    eligible_counts = full.loc[eligible].groupby("date", sort=True).size()
    dates_ge_30 = int((by_date >= 30).sum())
    source = full.loc[open_present, "price_provenance"]
    evidence = full.loc[open_present, "open_evidence_status"]
    source_counts = counts(source)
    evidence_counts = counts(evidence)

    ordered = full.sort_values(["ticker", "date"], kind="mergesort")
    source_nonnull = ordered["price_provenance"].notna() & ordered["price_provenance"].ne(ordered.groupby("ticker", sort=False)["price_provenance"].shift(1))
    source_transition_count = int((source_nonnull & ordered.groupby("ticker", sort=False)["price_provenance"].shift(1).notna()).sum())

    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "B_H_MICRO02_OPEN_SOURCE_CAPABILITY_AUDIT",
        "capability_classification": "PARTIAL / SOURCE_SENSITIVE / BLOCKED_FOR_PIT_EXECUTABLE_ADMISSION",
        "hypothesis_id": "H-MICRO-02",
        "candidate_id_created": False,
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "panel_mutated": False,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_head": args.repo_head,
        "code_sha256": sha256_file(Path(__file__)),
        "source_hashes": actual_hashes,
        "panel": {
            "rows": int(len(panel)),
            "tickers": int(panel["ticker"].nunique()),
            "dates": int(panel["date"].nunique()),
            "date_min": str(panel["date"].min().date()),
            "date_max": str(panel["date"].max().date()),
            "duplicate_keys": False,
        },
        "universe": universe_stats,
        "eligible_open_coverage": {
            "eligible_rows": int(eligible.sum()),
            "eligible_dates": int(full.loc[eligible, "date"].nunique()),
            "eligible_tickers": int(full.loc[eligible, "ticker"].nunique()),
            "open_positive_finite_rows": int(open_present.sum()),
            "open_positive_finite_share": pct(int(open_present.sum()), int(eligible.sum())),
            "open_available_true_rows": int(open_flag.sum()),
            "open_available_true_share": pct(int(open_flag.sum()), int(eligible.sum())),
            "open_available_missing_open_rows": int((open_flag & ~open_present).sum()),
            "open_present_but_flag_false_rows": int((open_present & ~open_flag).sum()),
        },
        "breadth": {
            "official_eligible_dates_with_30_open_rows": dates_ge_30,
            "official_eligible_date_count": int(len(by_date)),
            "date_open_count_min": int(by_date.min()) if len(by_date) else 0,
            "date_open_count_median": float(by_date.median()) if len(by_date) else None,
            "date_open_count_max": int(by_date.max()) if len(by_date) else 0,
            "date_eligible_count_median": float(eligible_counts.median()) if len(eligible_counts) else None,
            "ticker_open_count_median": float(by_ticker.median()) if len(by_ticker) else None,
            "ticker_open_count_q10": float(by_ticker.quantile(0.10)) if len(by_ticker) else None,
            "ticker_open_count_q90": float(by_ticker.quantile(0.90)) if len(by_ticker) else None,
        },
        "provenance": {
            "open_positive_finite_price_provenance": source_counts,
            "open_positive_finite_evidence_status": evidence_counts,
            "all_panel_price_provenance": counts(panel["price_provenance"]),
            "all_panel_open_evidence_status": counts(panel["open_evidence_status"]),
            "price_provenance_source_transition_count": source_transition_count,
        },
        "quality_checks": {
            "positive_finite_open_rows_panel": int(panel["open_positive_finite"].sum()),
            "open_outside_high_low_rows_panel": int((panel["open_positive_finite"] & ~panel["open_range_valid"]).sum()),
            "open_available_missing_open_rows_panel": int((panel["open_available_bool"] & ~panel["open_positive_finite"]).sum()),
            "corporate_action_integrity_values": counts(panel["corporate_action_integrity_verified"]),
            "signal_contract_values": counts(panel["signal_contract"]),
        },
        "interpretation": {
            "historical_open_capability": "PARTIAL",
            "source_authority": "UNKNOWN",
            "available_at_knowledge_time": "UNKNOWN",
            "corporate_action_basis": "UNKNOWN",
            "executable_fill_semantics": "UNKNOWN",
            "survivorship_and_identity": "UNKNOWN",
            "h_micro02_status": "BLOCKED_SOURCE_ADMISSION",
            "predictive_claim": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()

