"""Outcome-blind capability map for defensible C3 financial contracts.

The map compares only mechanism-defined subsets of the already frozen five
financial fields. It does not impute, forward-fill, relax knowledge-time or
provenance gates, open outcomes, or create new alpha candidates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


VALUES = {
    "leverage": "leverage_liabilities_to_assets__value",
    "liquidity": "liquidity_cash_to_assets__value",
    "margin": "margin_net_income_to_revenue__value",
    "yoy_revenue": "yoy_revenue__value",
    "yoy_assets": "yoy_total_assets__value",
}
CONTRACTS = {
    "quality_core": ["leverage", "liquidity", "margin"],
    "growth_core": ["yoy_revenue", "yoy_assets"],
    "quality_plus_yoy_revenue": ["leverage", "liquidity", "margin", "yoy_revenue"],
    "quality_plus_yoy_assets": ["leverage", "liquidity", "margin", "yoy_assets"],
    "all_five": list(VALUES),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ratio(numerator: int, denominator: int) -> float | None:
    return float(numerator / denominator) if denominator else None


def counts(series: pd.Series) -> dict[str, int]:
    values = series.astype("string").fillna("<NA>")
    return {str(k): int(v) for k, v in values.value_counts(dropna=False).sort_index().items()}


def finite_subset(frame: pd.DataFrame, names: list[str]) -> pd.Series:
    columns = [VALUES[name] for name in names]
    return frame[columns].notna().all(axis=1) & np.isfinite(frame[columns]).all(axis=1)


def contract_funnel(
    frame: pd.DataFrame,
    names: list[str],
    frozen_dates: pd.Series,
    eligible_universe_rows: int,
) -> dict[str, object]:
    required_finite = finite_subset(frame, names)
    all_rows = pd.Series(True, index=frame.index)
    gates = {
        "required_fields_finite": required_finite,
        "same_bundle_ok": ~frame["same_bundle_violation"].fillna(True).astype(bool),
        "selected_knowledge_ok": ~frame["selected_knowledge_time_violation"].fillna(True).astype(bool),
        "knowledge_time_ok": (
            frame["decision_timestamp_utc"].notna()
            & frame["bundle_reporting_knowledge_at_utc"].notna()
            & (frame["bundle_reporting_knowledge_at_utc"] <= frame["decision_timestamp_utc"])
        ),
        "period_date_ok": frame["bundle_period_date"].notna() & (frame["bundle_period_date"] <= frame["date"]),
        "provenance_complete": (
            frame["selected_bundle_provenance_complete"].fillna(False).astype(bool)
            & frame["bundle_reporting_version_id"].notna()
            & frame["bundle_reporting_attachment_sha256"].notna()
            & frame["bundle_reporting_attachment_sha256"].astype("string").str.len().ge(16)
        ),
        "identity_joined": frame["identity_joined"],
        "eligible_decision_universe": frame["eligible_decision_universe"].fillna(False).astype(bool),
    }
    cumulative = all_rows.copy()
    funnel = {}
    for name, gate in gates.items():
        cumulative &= gate
        frozen = cumulative & frame["date"].isin(frozen_dates)
        funnel[name] = {
            "rows": int(cumulative.sum()),
            "frozen_rows": int(frozen.sum()),
            "frozen_dates": int(frame.loc[frozen, "date"].nunique()),
            "frozen_tickers": int(frame.loc[frozen, "ticker"].nunique()),
        }
    final = cumulative & frame["date"].isin(frozen_dates)
    per_date = frame.loc[final].groupby("date").size()
    return {
        "fields": names,
        "field_columns": [VALUES[name] for name in names],
        "raw_finite_rows": int(required_finite.sum()),
        "raw_finite_rate_of_source": ratio(int(required_finite.sum()), len(frame)),
        "raw_finite_dates": int(frame.loc[required_finite, "date"].nunique()),
        "raw_finite_tickers": int(frame.loc[required_finite, "ticker"].nunique()),
        "funnel": funnel,
        "frozen_final_rows": int(final.sum()),
        "frozen_final_dates": int(frame.loc[final, "date"].nunique()),
        "frozen_final_tickers": int(frame.loc[final, "ticker"].nunique()),
        "frozen_final_rate_of_eligible_universe": ratio(int(final.sum()), eligible_universe_rows),
        "frozen_dates_with_at_least_30_names": int((per_date >= 30).sum()),
        "frozen_min_names_on_supported_date": int(per_date.min()) if len(per_date) else None,
        "frozen_median_names_on_supported_date": float(per_date.median()) if len(per_date) else None,
        "frozen_q10_names_on_supported_date": float(per_date.quantile(0.10)) if len(per_date) else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--financial", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    financial = pd.read_parquet(args.financial)
    features = pd.read_parquet(args.features, columns=["ticker", "date", "eligible_decision_universe"])
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    for frame in (financial, features):
        frame["ticker"] = frame["ticker"].astype("string")
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.drop_duplicates("date").sort_values("date", kind="mergesort").reset_index(drop=True)
    frozen_dates = sessions.tail(600)["date"]

    financial["decision_timestamp_utc"] = pd.to_datetime(financial["decision_timestamp_utc"], errors="coerce", utc=True)
    financial["bundle_reporting_knowledge_at_utc"] = pd.to_datetime(
        financial["bundle_reporting_knowledge_at_utc"], errors="coerce", utc=True
    )
    financial["bundle_period_date"] = pd.to_datetime(financial["bundle_period_date"], errors="coerce").dt.normalize()
    for column in VALUES.values():
        financial[column] = pd.to_numeric(financial[column], errors="coerce")
    if financial.duplicated(["ticker", "date"]).any():
        raise ValueError("financial bundle has duplicate ticker/date keys")

    joined = financial.merge(
        features,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    joined["identity_joined"] = joined["_merge"].eq("both")
    eligible_universe_rows = int(features["eligible_decision_universe"].fillna(False).astype(bool).sum())

    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "D_C3_FINANCIAL_CONTRACT_MAP",
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "candidate_id_created": False,
        "source_classification": "PARTIAL_PARKED_CAPABILITY_ONLY",
        "source_hashes": {
            "financial": sha256_file(args.financial),
            "features": sha256_file(args.features),
            "official_sessions": sha256_file(args.sessions),
        },
        "source_rows": int(len(financial)),
        "source_tickers": int(financial["ticker"].nunique()),
        "source_dates": int(financial["date"].nunique()),
        "source_date_start": str(financial["date"].min().date()),
        "source_date_end": str(financial["date"].max().date()),
        "frozen_session_count": int(len(frozen_dates)),
        "frozen_window_start": str(frozen_dates.min().date()),
        "frozen_window_end": str(frozen_dates.max().date()),
        "eligible_universe_rows": eligible_universe_rows,
        "identity_join": {
            "financial_rows_matched": int(joined["identity_joined"].sum()),
            "financial_rows_unmatched": int((~joined["identity_joined"]).sum()),
            "matched_eligible_rows": int((joined["identity_joined"] & joined["eligible_decision_universe"].fillna(False)).sum()),
        },
        "governance_counts": {
            "bundle_status": counts(financial["bundle_status"]),
            "period_stratum": counts(financial["bundle_period_stratum"]),
            "same_bundle_violation_true": int(financial["same_bundle_violation"].fillna(True).astype(bool).sum()),
            "selected_knowledge_time_violation_true": int(financial["selected_knowledge_time_violation"].fillna(True).astype(bool).sum()),
            "knowledge_timestamp_missing": int(financial["bundle_reporting_knowledge_at_utc"].isna().sum()),
            "period_date_missing": int(financial["bundle_period_date"].isna().sum()),
            "reporting_version_missing": int(financial["bundle_reporting_version_id"].isna().sum()),
        },
        "contracts": {
            contract: contract_funnel(joined, fields, frozen_dates, eligible_universe_rows)
            for contract, fields in CONTRACTS.items()
        },
        "interpretation": {
            "subsets_are_mechanism_defined": True,
            "no_missing_value_fill": True,
            "no_forward_fill": True,
            "no_provider_fallback": True,
            "no_predictive_claim": True,
            "all_five_remains_current_c3_contract": True,
        },
        "code_sha256": sha256_file(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(args.output), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
