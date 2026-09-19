"""Outcome-blind capability audit for the frozen C3 financial bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


VALUE_COLUMNS = [
    "leverage_liabilities_to_assets__value",
    "liquidity_cash_to_assets__value",
    "margin_net_income_to_revenue__value",
    "yoy_revenue__value",
    "yoy_total_assets__value",
]
REQUIRED_PROVENANCE = [
    "selected_bundle_provenance_complete",
    "bundle_reporting_version_id",
    "bundle_reporting_attachment_sha256",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def counts(series: pd.Series) -> dict[str, int]:
    values = series.astype("string").fillna("<NA>")
    return {str(key): int(value) for key, value in values.value_counts(dropna=False).sort_index().items()}


def ratio(numerator: int, denominator: int) -> float | None:
    return float(numerator / denominator) if denominator else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--financial", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    financial = pd.read_parquet(args.financial)
    features = pd.read_parquet(
        args.features,
        columns=["ticker", "date", "eligible_decision_universe", "C3_financial_quality_growth_v1", "financial_pit_valid"],
    )
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    for frame in (financial, features):
        frame["ticker"] = frame["ticker"].astype("string")
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.drop_duplicates("date").sort_values("date", kind="mergesort").reset_index(drop=True)
    frozen_dates = set(sessions.tail(600)["date"])

    duplicate_keys = int(financial.duplicated(["ticker", "date"]).sum())
    financial["decision_timestamp_utc"] = pd.to_datetime(financial["decision_timestamp_utc"], errors="coerce", utc=True)
    financial["bundle_reporting_knowledge_at_utc"] = pd.to_datetime(
        financial["bundle_reporting_knowledge_at_utc"], errors="coerce", utc=True
    )
    financial["bundle_period_date"] = pd.to_datetime(financial["bundle_period_date"], errors="coerce").dt.normalize()
    for column in VALUE_COLUMNS:
        financial[column] = pd.to_numeric(financial[column], errors="coerce")

    knowledge_ok = (
        financial["decision_timestamp_utc"].notna()
        & financial["bundle_reporting_knowledge_at_utc"].notna()
        & (financial["bundle_reporting_knowledge_at_utc"] <= financial["decision_timestamp_utc"])
    )
    period_ok = financial["bundle_period_date"].notna() & (financial["bundle_period_date"] <= financial["date"])
    provenance_ok = (
        financial["selected_bundle_provenance_complete"].fillna(False).astype(bool)
        & financial["bundle_reporting_version_id"].notna()
        & financial["bundle_reporting_attachment_sha256"].notna()
        & financial["bundle_reporting_attachment_sha256"].astype("string").str.len().ge(16)
    )
    all_five_values = financial[VALUE_COLUMNS].notna().all(axis=1) & np.isfinite(financial[VALUE_COLUMNS]).all(axis=1)
    all_five_flag = financial["all_five_available"].fillna(False).astype(bool)
    same_bundle_ok = ~financial["same_bundle_violation"].fillna(True).astype(bool)
    selected_violation_ok = ~financial["selected_knowledge_time_violation"].fillna(True).astype(bool)

    joined = financial.merge(
        features[["ticker", "date", "eligible_decision_universe"]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    identity_matched = joined["_merge"].eq("both")
    eligible = joined["eligible_decision_universe"].fillna(False).astype(bool)
    valid = (
        all_five_flag
        & all_five_values
        & same_bundle_ok
        & selected_violation_ok
        & knowledge_ok
        & period_ok
        & provenance_ok
        & identity_matched
        & eligible
    )

    flag_coverage = {}
    for column in ["core3_available", "core3_plus_yoy_revenue_available", "core3_plus_yoy_assets_available", "all_five_available"]:
        flag = financial[column].fillna(False).astype(bool)
        flag_coverage[column] = {
            "rows": int(flag.sum()),
            "row_rate": ratio(int(flag.sum()), len(financial)),
            "frozen_window_rows": int((flag & financial["date"].isin(frozen_dates)).sum()),
            "dates": int(financial.loc[flag, "date"].nunique()),
            "tickers": int(financial.loc[flag, "ticker"].nunique()),
        }

    missingness = {}
    for column in VALUE_COLUMNS:
        missingness[column] = {
            "null_rows": int(financial[column].isna().sum()),
            "finite_rows": int(np.isfinite(financial[column]).sum()),
            "missing_class": counts(financial[column.replace("__value", "__missing_class")]),
            "status": counts(financial[column.replace("__value", "__status")]),
        }

    valid_frame = joined.loc[valid].copy()
    valid_frozen = valid_frame[valid_frame["date"].isin(frozen_dates)]
    by_period = financial.groupby("bundle_period_stratum", dropna=False).agg(
        rows=("ticker", "size"),
        tickers=("ticker", "nunique"),
        dates=("date", "nunique"),
        all_five=("all_five_available", "sum"),
    )

    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "D_C3_FINANCIAL_CAPABILITY",
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "source_classification": "PARTIAL_PARKED_CAPABILITY_ONLY",
        "source_hashes": {
            "financial": sha256_file(args.financial),
            "features": sha256_file(args.features),
            "official_sessions": sha256_file(args.sessions),
        },
        "row_count": int(len(financial)),
        "ticker_count": int(financial["ticker"].nunique()),
        "date_count": int(financial["date"].nunique()),
        "date_start": financial["date"].min().strftime("%Y-%m-%d"),
        "date_end": financial["date"].max().strftime("%Y-%m-%d"),
        "duplicate_ticker_date_keys": duplicate_keys,
        "frozen_session_count": 600,
        "frozen_window_start": min(frozen_dates).strftime("%Y-%m-%d"),
        "frozen_window_end": max(frozen_dates).strftime("%Y-%m-%d"),
        "missingness": missingness,
        "flag_coverage": flag_coverage,
        "governance_counts": {
            "bundle_status": counts(financial["bundle_status"]),
            "period_stratum": counts(financial["bundle_period_stratum"]),
            "same_bundle_violation_true": int((~same_bundle_ok).sum()),
            "selected_knowledge_time_violation_true": int((~selected_violation_ok).sum()),
            "knowledge_timestamp_missing_or_future": int((~knowledge_ok).sum()),
            "period_date_missing_or_future": int((~period_ok).sum()),
            "provenance_invalid": int((~provenance_ok).sum()),
            "decision_timestamp_missing": int(financial["decision_timestamp_utc"].isna().sum()),
            "knowledge_timestamp_missing": int(financial["bundle_reporting_knowledge_at_utc"].isna().sum()),
            "period_date_missing": int(financial["bundle_period_date"].isna().sum()),
            "reporting_version_missing": int(financial["bundle_reporting_version_id"].isna().sum()),
            "attachment_hash_missing_or_short": int(
                financial["bundle_reporting_attachment_sha256"].isna().sum()
                + financial["bundle_reporting_attachment_sha256"].astype("string").str.len().lt(16).sum()
            ),
        },
        "identity_join": {
            "financial_rows_unmatched_to_feature_panel": int((~identity_matched).sum()),
            "financial_rows_matched": int(identity_matched.sum()),
            "matched_eligible_rows": int((identity_matched & eligible).sum()),
            "matched_ineligible_rows": int((identity_matched & ~eligible).sum()),
        },
        "validity_funnel": {
            "all_five_flag": int(all_five_flag.sum()),
            "all_five_finite_values": int((all_five_flag & all_five_values).sum()),
            "same_bundle_ok": int((all_five_flag & all_five_values & same_bundle_ok).sum()),
            "selected_knowledge_ok": int((all_five_flag & all_five_values & same_bundle_ok & selected_violation_ok).sum()),
            "knowledge_time_ok": int((all_five_flag & all_five_values & same_bundle_ok & selected_violation_ok & knowledge_ok).sum()),
            "period_ok": int((all_five_flag & all_five_values & same_bundle_ok & selected_violation_ok & knowledge_ok & period_ok).sum()),
            "provenance_ok": int((all_five_flag & all_five_values & same_bundle_ok & selected_violation_ok & knowledge_ok & period_ok & provenance_ok).sum()),
            "identity_and_eligible": int(valid.sum()),
            "frozen_valid_rows": int(valid_frozen.shape[0]),
            "frozen_valid_dates": int(valid_frozen["date"].nunique()),
            "frozen_valid_tickers": int(valid_frozen["ticker"].nunique()),
        },
        "period_summary": {
            str(index): {str(key): (int(value) if pd.notna(value) else None) for key, value in row.items()}
            for index, row in by_period.iterrows()
        },
        "code_sha256": sha256_file(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
