"""Independent target-free verifier for the FILINGAGE-01 source audit."""

from __future__ import annotations

import argparse
import hashlib
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


def close(left: object, right: object, tolerance: float = 1e-10) -> bool:
    try:
        return bool(np.isclose(float(left), float(right), rtol=tolerance, atol=tolerance))
    except (TypeError, ValueError):
        return False


def daily_mean_spearman(frame: pd.DataFrame, left: str, right: str) -> tuple[int, float | None]:
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
    return len(values), float(np.mean(values)) if values else None


def top30_sets(frame: pd.DataFrame, column: str) -> dict[pd.Timestamp, set[str]]:
    valid = frame["eligible_decision_universe"] & np.isfinite(frame[column])
    result: dict[pd.Timestamp, set[str]] = {}
    for date, group in frame.loc[valid].groupby("date", sort=True):
        chosen = group.sort_values([column, "ticker"], ascending=[False, True], kind="mergesort").head(TOP_K)
        if len(chosen) == TOP_K:
            result[pd.Timestamp(date)] = set(chosen["ticker"].astype(str))
    return result


def overlap_mean(frame: pd.DataFrame, left: str, right: str) -> tuple[int, float | None]:
    left_sets = top30_sets(frame, left)
    right_sets = top30_sets(frame, right)
    dates = sorted(set(left_sets) & set(right_sets))
    values = [len(left_sets[date] & right_sets[date]) / TOP_K for date in dates]
    return len(values), float(np.mean(values)) if values else None


def bottom_value_q1(frame: pd.DataFrame, score: str) -> tuple[int, float | None]:
    valid = (
        frame["eligible_decision_universe"]
        & np.isfinite(frame[score])
        & np.isfinite(frame["regular_market_value"])
        & frame["regular_market_value"].gt(0)
    )
    work = frame.loc[valid, ["date", "ticker", score, "regular_market_value"]].copy()
    work["value_percentile"] = work.groupby("date")["regular_market_value"].rank(pct=True, method="average")
    selected: list[pd.DataFrame] = []
    for _, group in work.groupby("date", sort=True):
        chosen = group.sort_values([score, "ticker"], ascending=[False, True], kind="mergesort").head(TOP_K)
        if len(chosen) == TOP_K:
            selected.append(chosen)
    if not selected:
        return 0, None
    selected_frame = pd.concat(selected, ignore_index=True)
    return len(selected_frame), float(selected_frame["value_percentile"].le(0.25).mean())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    bundle = pd.read_parquet(
        args.bundle,
        columns=[
            "ticker", "date", "decision_timestamp_utc", "bundle_status",
            "bundle_reporting_knowledge_at_utc", AGE,
        ],
    )
    bundle["ticker"] = bundle["ticker"].astype("string")
    bundle["date"] = pd.to_datetime(bundle["date"], errors="raise").dt.normalize()
    bundle["age"] = pd.to_numeric(bundle[AGE], errors="coerce")
    bundle["decision_time"] = pd.to_datetime(bundle["decision_timestamp_utc"], errors="coerce", utc=True)
    bundle["knowledge_time"] = pd.to_datetime(bundle["bundle_reporting_knowledge_at_utc"], errors="coerce", utc=True)
    bundle["recomputed_age"] = (bundle["decision_time"] - bundle["knowledge_time"]).dt.total_seconds() / 86400.0
    panel = pd.read_parquet(args.panel, columns=["ticker", "date", "regular_market_value"])
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    features = pd.read_parquet(args.features, columns=["ticker", "date", C1, C2, C4])
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()

    universe, _ = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors
    )
    surface = universe.merge(panel, on=["ticker", "date"], how="left", validate="one_to_one").merge(
        bundle[["ticker", "date", "age"]], on=["ticker", "date"], how="left", validate="one_to_one"
    ).merge(features, on=["ticker", "date"], how="left", validate="one_to_one")
    for column in ["age", C1, C2, C4, "regular_market_value"]:
        surface[column] = pd.to_numeric(surface[column], errors="coerce")
    surface["recency"] = -surface["age"]
    frozen_dates = set(sessions["date"].sort_values().iloc[-FROZEN_SESSIONS:])
    structural = surface[surface["date"].isin(frozen_dates)].copy()
    age_present = bundle["age"].notna() & np.isfinite(bundle["age"])
    age_diff = bundle.loc[age_present, "age"] - bundle.loc[age_present, "recomputed_age"]

    artifact_dependence = artifact["structural_window"]["dependence_recency"]
    artifact_overlap = artifact["structural_window"]["top30_overlap_recency"]
    artifact_bottom = artifact["structural_window"]["bottom_value_q1_share_recency"]
    recomputed_dependence: dict[str, dict[str, object]] = {}
    recomputed_overlap: dict[str, dict[str, object]] = {}
    for name, column in {"C1": C1, "C2": C2, "C4": C4}.items():
        count, mean = daily_mean_spearman(structural, "recency", column)
        dates, overlap = overlap_mean(structural, "recency", column)
        recomputed_dependence[name] = {"date_count": count, "mean_daily_spearman": mean}
        recomputed_overlap[name] = {"common_dates": dates, "mean_overlap": overlap}
    bottom_slots, bottom_share = bottom_value_q1(structural, "recency")

    checks = {
        "artifact_status": artifact.get("status") == "SOURCE_PARTIAL_STRUCTURAL_SIGNAL",
        "artifact_stage": artifact.get("stage") == "FILINGAGE01_FINANCIAL_REPORTING_AGE_SOURCE_AUDIT",
        "no_outcome_access": artifact.get("outcome_accessed") is False,
        "no_provider_access": artifact.get("provider_accessed") is False,
        "no_candidate_id_created": artifact.get("candidate_id_created") is False,
        "code_hash": artifact.get("code_sha256") == sha256_file(args.code),
        "bundle_hash": artifact.get("source_hashes", {}).get("bundle") == sha256_file(args.bundle),
        "panel_hash": artifact.get("source_hashes", {}).get("panel") == sha256_file(args.panel),
        "features_hash": artifact.get("source_hashes", {}).get("features") == sha256_file(args.features),
        "sessions_hash": artifact.get("source_hashes", {}).get("official_sessions") == EXPECTED_SESSION_HASH,
        "anchors_hash": artifact.get("source_hashes", {}).get("tradability_anchors") == EXPECTED_ANCHOR_HASH,
        "keys_unique": int(bundle.duplicated(["ticker", "date"]).sum()) == 0,
        "age_nonnegative": bool(bundle.loc[age_present, "age"].ge(0).all()),
        "age_status_alignment": bool(
            bundle.loc[age_present, "bundle_status"].eq("SELECTED").all()
        ),
        "knowledge_not_after_decision": bool(
            (bundle.loc[age_present, "knowledge_time"] <= bundle.loc[age_present, "decision_time"]).all()
        ),
        "age_recomputation_exact": bool(age_diff.abs().le(1e-9).all()),
        "eligible_age_rows": int((surface["eligible_decision_universe"] & surface["age"].notna()).sum())
        == artifact["universe"]["eligible_age_rows"],
        "frozen_dates": len(frozen_dates) == FROZEN_SESSIONS,
        "bottom_slots": bottom_slots == artifact_bottom["selected_slots"],
        "bottom_share": close(bottom_share, artifact_bottom["bottom_value_q1_share"]),
    }
    for name in ["C1", "C2", "C4"]:
        checks[f"dependence_{name}"] = (
            recomputed_dependence[name]["date_count"] == artifact_dependence[name]["date_count"]
            and close(recomputed_dependence[name]["mean_daily_spearman"], artifact_dependence[name]["mean_daily_spearman"])
        )
        checks[f"overlap_{name}"] = (
            recomputed_overlap[name]["common_dates"] == artifact_overlap[name]["common_dates"]
            and close(recomputed_overlap[name]["mean_overlap"], artifact_overlap[name]["mean_overlap"])
        )

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verification_type": "independent_reporting_age_recomputation_target_free",
        "artifact_sha256": sha256_file(args.artifact),
        "verifier_code_sha256": sha256_file(Path(__file__)),
        "checks": checks,
        "recomputed": {
            "rows": int(len(bundle)),
            "age_present_rows": int(age_present.sum()),
            "age_max_abs_difference": float(age_diff.abs().max()),
            "eligible_age_rows": int((surface["eligible_decision_universe"] & surface["age"].notna()).sum()),
            "dependence_recency": recomputed_dependence,
            "top30_overlap_recency": recomputed_overlap,
            "bottom_value_q1_share_recency": {"selected_slots": bottom_slots, "bottom_value_q1_share": bottom_share},
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
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
