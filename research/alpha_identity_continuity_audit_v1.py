"""Read-only ticker/security-master continuity audit for the alpha lane."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    panel = pd.read_parquet(args.panel, columns=["ticker", "date"])
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    features = pd.read_parquet(args.features, columns=["ticker", "date", "eligible_decision_universe"])
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    master = pd.read_csv(args.security_master)
    required = {"security_id", "ticker", "listed_from", "listed_to"}
    missing = required.difference(master.columns)
    if missing:
        raise ValueError(f"security master missing columns: {sorted(missing)}")
    master["ticker"] = master["ticker"].astype("string")
    master["listed_from"] = pd.to_datetime(master["listed_from"], errors="coerce").dt.normalize()
    master["listed_to"] = pd.to_datetime(master["listed_to"], errors="coerce").dt.normalize()
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel has duplicate ticker/date keys")
    if master["security_id"].duplicated().any():
        raise ValueError("security master has duplicate security_id")

    mapping = master.groupby("ticker")["security_id"].nunique()
    panel_join = panel.merge(master[["security_id", "ticker", "listed_from", "listed_to"]], on="ticker", how="left", validate="many_to_many")
    panel_join["active_listing"] = (
        panel_join["listed_from"].notna()
        & (panel_join["date"] >= panel_join["listed_from"])
        & (panel_join["listed_to"].isna() | (panel_join["date"] <= panel_join["listed_to"]))
    )
    active_counts = panel_join.loc[panel_join["active_listing"]].groupby(["ticker", "date"])["security_id"].nunique()
    panel_keys = panel[["ticker", "date"]].drop_duplicates().set_index(["ticker", "date"]).index
    active_counts = active_counts.reindex(panel_keys, fill_value=0)

    eligible = features[features["eligible_decision_universe"].fillna(False).astype(bool)][["ticker", "date"]].drop_duplicates()
    eligible_index = eligible.set_index(["ticker", "date"]).index
    eligible_counts = active_counts.reindex(eligible_index, fill_value=0)
    multi_ticker_count = int((mapping > 1).sum())
    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "J_IDENTITY_CONTINUITY_AUDIT",
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "panel_sha256": sha256_file(args.panel),
            "features_sha256": sha256_file(args.features),
            "security_master_sha256": sha256_file(args.security_master),
        },
        "panel": {
            "rows": int(len(panel)),
            "tickers": int(panel["ticker"].nunique()),
            "dates": int(panel["date"].nunique()),
            "source_keys": int(len(panel_keys)),
        },
        "security_master": {
            "rows": int(len(master)),
            "security_ids": int(master["security_id"].nunique()),
            "tickers": int(master["ticker"].nunique()),
            "duplicate_ticker_count": int((mapping > 1).sum()),
            "duplicate_security_id_count": int(master["security_id"].duplicated().sum()),
            "unmapped_panel_ticker_count": int(panel.loc[~panel["ticker"].isin(mapping.index), "ticker"].nunique()),
        },
        "panel_listing_interval": {
            "keys_with_exactly_one_active_security_id": int((active_counts == 1).sum()),
            "keys_with_no_active_security_id": int((active_counts == 0).sum()),
            "keys_with_multiple_active_security_ids": int((active_counts > 1).sum()),
            "eligible_keys": int(len(eligible_index)),
            "eligible_with_exactly_one_active_security_id": int((eligible_counts == 1).sum()),
            "eligible_with_no_active_security_id": int((eligible_counts == 0).sum()),
            "eligible_with_multiple_active_security_ids": int((eligible_counts > 1).sum()),
        },
        "interpretation": {
            "ticker_date_is_not_issuer_proof": True,
            "current_master_has_one_row_per_ticker": bool(multi_ticker_count == 0),
            "active_interval_join_is_audit_only": True,
            "does_not_certify_corporate_action_basis": True,
            "does_not_change_candidate_status": True,
        },
        "code_sha256": sha256_file(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(args.output), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
