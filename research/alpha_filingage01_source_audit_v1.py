"""Target-free capability audit for the financial reporting-age surface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import build_decision_universe, sha256_file


C1 = "C1_residual_reversal_5_v1"
C2 = "C2_participation_confirmation_5_v1"
C4 = "C4_path_efficiency_reversal_20_v1"
TOP_K = 30
FROZEN_SESSIONS = 600
AGE = "bundle_filing_age_days"
EXPECTED_SESSION_HASH = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_ANCHOR_HASH = "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e"
REQUIRED_BUNDLE_COLUMNS = [
    "ticker",
    "date",
    "decision_timestamp_utc",
    "bundle_status",
    "bundle_period_date",
    "bundle_reporting_version_id",
    "bundle_reporting_attachment_sha256",
    "bundle_reporting_knowledge_at_utc",
    AGE,
]


def finite_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def daily_spearman(frame: pd.DataFrame, left: str, right: str) -> dict[str, object]:
    values: list[float] = []
    valid = frame["eligible_decision_universe"] & np.isfinite(frame[left]) & np.isfinite(frame[right])
    for _, group in frame.loc[valid].groupby("date", sort=True):
        if len(group) < TOP_K:
            continue
        corr = group[left].rank(method="average").corr(
            group[right].rank(method="average"), method="spearman"
        )
        if pd.notna(corr):
            values.append(float(corr))
    return {
        "date_count": len(values),
        "mean_daily_spearman": finite_float(np.mean(values)) if values else None,
        "median_daily_spearman": finite_float(np.median(values)) if values else None,
    }


def top30(frame: pd.DataFrame, column: str, ascending: bool = False) -> dict[pd.Timestamp, set[str]]:
    valid = frame["eligible_decision_universe"] & np.isfinite(frame[column])
    result: dict[pd.Timestamp, set[str]] = {}
    for date, group in frame.loc[valid].groupby("date", sort=True):
        chosen = group.sort_values(
            [column, "ticker"], ascending=[ascending, True], kind="mergesort"
        ).head(TOP_K)
        if len(chosen) == TOP_K:
            result[pd.Timestamp(date)] = set(chosen["ticker"].astype(str))
    return result


def top30_overlap(frame: pd.DataFrame, left: str, right: str) -> dict[str, object]:
    left_sets = top30(frame, left)
    right_sets = top30(frame, right)
    dates = sorted(set(left_sets) & set(right_sets))
    overlaps = [len(left_sets[date] & right_sets[date]) / TOP_K for date in dates]
    return {
        "common_dates": len(dates),
        "mean_overlap": finite_float(np.mean(overlaps)) if overlaps else None,
        "min_overlap": finite_float(np.min(overlaps)) if overlaps else None,
    }


def bottom_value_q1_share(frame: pd.DataFrame, score: str) -> dict[str, object]:
    valid = (
        frame["eligible_decision_universe"]
        & np.isfinite(frame[score])
        & np.isfinite(frame["regular_market_value"])
        & frame["regular_market_value"].gt(0)
    )
    work = frame.loc[valid, ["date", "ticker", score, "regular_market_value"]].copy()
    work["value_percentile"] = work.groupby("date")["regular_market_value"].rank(
        pct=True, method="average"
    )
    selected: list[pd.DataFrame] = []
    for _, group in work.groupby("date", sort=True):
        chosen = group.sort_values([score, "ticker"], ascending=[False, True], kind="mergesort").head(TOP_K)
        if len(chosen) == TOP_K:
            selected.append(chosen)
    if not selected:
        return {"selected_slots": 0, "bottom_value_q1_share": None}
    selected_frame = pd.concat(selected, ignore_index=True)
    return {
        "selected_slots": int(len(selected_frame)),
        "bottom_value_q1_share": finite_float(selected_frame["value_percentile"].le(0.25).mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    bundle = pd.read_parquet(args.bundle, columns=REQUIRED_BUNDLE_COLUMNS)
    bundle["ticker"] = bundle["ticker"].astype("string")
    bundle["date"] = pd.to_datetime(bundle["date"], errors="raise").dt.normalize()
    panel = pd.read_parquet(args.panel, columns=["ticker", "date", "regular_market_value"])
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    features = pd.read_parquet(args.features, columns=["ticker", "date", C1, C2, C4])
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()

    bundle["age"] = pd.to_numeric(bundle[AGE], errors="coerce")
    bundle["decision_time"] = pd.to_datetime(bundle["decision_timestamp_utc"], errors="coerce", utc=True)
    bundle["knowledge_time"] = pd.to_datetime(
        bundle["bundle_reporting_knowledge_at_utc"], errors="coerce", utc=True
    )
    bundle["recomputed_age"] = (
        bundle["decision_time"] - bundle["knowledge_time"]
    ).dt.total_seconds() / 86400.0
    bundle["age_difference"] = bundle["age"] - bundle["recomputed_age"]

    universe, _ = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors
    )
    full = universe.merge(
        panel, on=["ticker", "date"], how="left", validate="one_to_one"
    ).merge(
        bundle[["ticker", "date", "age", "bundle_status"]],
        on=["ticker", "date"], how="left", validate="one_to_one",
    )
    full = full.merge(features, on=["ticker", "date"], how="left", validate="one_to_one")
    for column in [C1, C2, C4, "age", "regular_market_value"]:
        full[column] = pd.to_numeric(full[column], errors="coerce")
    full["recency"] = -full["age"]

    eligible = full["eligible_decision_universe"]
    age_finite = bundle["age"].notna() & np.isfinite(bundle["age"])
    age_dates = bundle.loc[age_finite, "date"]
    age_by_year = bundle.loc[age_finite].assign(year=bundle.loc[age_finite, "date"].dt.year)["year"].value_counts().sort_index()
    frozen_dates = set(sessions["date"].sort_values().iloc[-FROZEN_SESSIONS:])
    structural = full[full["date"].isin(frozen_dates)].copy()
    references = {"C1": C1, "C2": C2, "C4": C4}
    valid_structural_age = structural["eligible_decision_universe"] & np.isfinite(structural["recency"])
    age_values = bundle.loc[age_finite, "age"]
    exact_age_mask = bundle["age"].notna() & bundle["recomputed_age"].notna()
    age_difference = bundle.loc[exact_age_mask, "age_difference"]

    source_checks = {
        "required_columns_present": set(REQUIRED_BUNDLE_COLUMNS).issubset(bundle.columns),
        "bundle_keys_unique": int(bundle.duplicated(["ticker", "date"]).sum()) == 0,
        "official_dates": set(bundle["date"].unique()).issubset(set(sessions["date"].unique())),
        "age_nonnegative": bool(age_values.ge(0).all()),
        "age_finite_when_present": bool(np.isfinite(age_values).all()),
        "age_status_alignment": bool(
            bundle.loc[age_finite, "bundle_status"].eq("SELECTED").all()
            and bundle.loc[~age_finite, "bundle_status"].ne("SELECTED").all()
        ),
        "timestamp_parseable_for_age": bool(bundle.loc[age_finite, ["decision_time", "knowledge_time"]].notna().all().all()),
        "knowledge_not_after_decision": bool(
            (bundle.loc[age_finite, "knowledge_time"] <= bundle.loc[age_finite, "decision_time"]).all()
        ),
        "age_recomputation_exact": bool(age_difference.abs().le(1e-9).all()),
        "panel_join_all_bundle_rows": len(
            bundle.merge(panel[["ticker", "date"]], on=["ticker", "date"], how="left", indicator=True)
            .query("_merge == 'left_only'")
        ) == 0,
        "features_join_all_bundle_rows": len(
            bundle.merge(features[["ticker", "date"]], on=["ticker", "date"], how="left", indicator=True)
            .query("_merge == 'left_only'")
        ) == 0,
    }
    structural_checks = {
        "eligible_recency_rows_present": int(valid_structural_age.sum()) > 0,
        "structural_window_exact": len(frozen_dates) == FROZEN_SESSIONS,
    }
    checks = {
        **source_checks,
        **structural_checks,
        "no_outcome_access": True,
        "no_provider_access": True,
        "candidate_id_created": False,
    }
    status = "SOURCE_PARTIAL_STRUCTURAL_SIGNAL" if all(source_checks.values()) else "SOURCE_BLOCKED"
    result = {
        "hypothesis_id": "FILINGAGE-01",
        "stage": "FILINGAGE01_FINANCIAL_REPORTING_AGE_SOURCE_AUDIT",
        "status": status,
        "run_timestamp_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "code_sha256": sha256_file(Path(__file__)),
        "source_hashes": {
            "bundle": sha256_file(args.bundle),
            "panel": sha256_file(args.panel),
            "features": sha256_file(args.features),
            "official_sessions": sha256_file(args.sessions),
            "tradability_anchors": sha256_file(args.anchors),
        },
        "outcome_accessed": False,
        "provider_accessed": False,
        "candidate_id_created": False,
        "checks": checks,
        "source": {
            "path": str(args.bundle),
            "rows": int(len(bundle)),
            "tickers": int(bundle["ticker"].nunique()),
            "dates": int(bundle["date"].nunique()),
            "date_min": str(bundle["date"].min().date()),
            "date_max": str(bundle["date"].max().date()),
            "age_nonnull_rows": int(age_finite.sum()),
            "age_nonnull_dates": int(age_dates.nunique()),
            "age_nonnull_tickers": int(bundle.loc[age_finite, "ticker"].nunique()),
            "age_date_min": str(age_dates.min().date()),
            "age_date_max": str(age_dates.max().date()),
            "age_rows_by_year": {str(k): int(v) for k, v in age_by_year.items()},
            "status_counts": {str(k): int(v) for k, v in bundle["bundle_status"].value_counts(dropna=False).items()},
            "knowledge_nonnull_rows": int(bundle["knowledge_time"].notna().sum()),
            "version_nonnull_rows": int(bundle["bundle_reporting_version_id"].notna().sum()),
            "attachment_nonnull_rows": int(bundle["bundle_reporting_attachment_sha256"].notna().sum()),
            "period_date_nonnull_rows": int(bundle["bundle_period_date"].notna().sum()),
            "age_summary": {
                "min": finite_float(age_values.min()),
                "q10": finite_float(age_values.quantile(0.10)),
                "median": finite_float(age_values.quantile(0.50)),
                "q90": finite_float(age_values.quantile(0.90)),
                "q99": finite_float(age_values.quantile(0.99)),
                "max": finite_float(age_values.max()),
            },
            "age_recomputation_max_abs_difference": finite_float(age_difference.abs().max()),
        },
        "universe": {
            "eligible_rows": int(eligible.sum()),
            "eligible_tickers": int(full.loc[eligible, "ticker"].nunique()),
            "eligible_age_rows": int((eligible & full["age"].notna()).sum()),
            "eligible_age_dates": int(full.loc[eligible & full["age"].notna(), "date"].nunique()),
            "eligible_age_tickers": int(full.loc[eligible & full["age"].notna(), "ticker"].nunique()),
            "session_count": int(sessions["date"].nunique()),
            "session_hash": sha256_file(args.sessions),
            "anchor_hash": sha256_file(args.anchors),
        },
        "structural_window": {
            "min": str(min(frozen_dates).date()),
            "max": str(max(frozen_dates).date()),
            "date_count": len(frozen_dates),
            "dependence_recency": {
                name: daily_spearman(structural, "recency", column)
                for name, column in references.items()
            },
            "top30_overlap_recency": {
                name: top30_overlap(structural, "recency", column)
                for name, column in references.items()
            },
            "bottom_value_q1_share_recency": bottom_value_q1_share(structural, "recency"),
            "eligible_recency_rows": int(valid_structural_age.sum()),
        },
        "interpretation": {
            "admissibility": "PARTIAL",
            "predictive_claim": False,
            "source_semantics_status": "ARITHMETICALLY_CONSISTENT_BUT_PUBLIC_AVAILABILITY_AND_REVISION_AUTHORITY_UNKNOWN",
            "status_change_authorized": False,
            "candidate_id_authorized": False,
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
    if status == "SOURCE_BLOCKED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
