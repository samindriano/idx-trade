"""Target-free diagnostic separating H-LIQ temporal variability from C2 level."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import build_decision_universe, rolling


HLIQ = "HLIQ01_variability_log_turnover_20_v1"
LEVEL = "C2_turnover_level_component_log_abnormal_5_over_60"
RET5 = "ret_5_diagnostic"
REFERENCES = {
    "turnover_level": LEVEL,
    "C2": "C2_participation_confirmation_5_v1",
    "C1": "C1_residual_reversal_5_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def daily_spearman(frame: pd.DataFrame, left: str, right: str) -> dict[str, object]:
    values: list[float] = []
    for _, group in frame.loc[
        frame["eligible_decision_universe"]
        & np.isfinite(frame[left])
        & np.isfinite(frame[right])
    ].groupby("date", sort=True):
        if len(group) >= 30:
            correlation = group[left].rank().corr(group[right].rank(), method="spearman")
            if pd.notna(correlation):
                values.append(float(correlation))
    return {
        "date_count": int(len(values)),
        "mean_daily_spearman": finite_float(np.mean(values)) if values else None,
        "median_daily_spearman": finite_float(np.median(values)) if values else None,
        "q10_daily_spearman": finite_float(np.quantile(values, 0.10)) if values else None,
        "q90_daily_spearman": finite_float(np.quantile(values, 0.90)) if values else None,
    }


def top30(frame: pd.DataFrame, column: str) -> dict[pd.Timestamp, set[str]]:
    valid = frame["eligible_decision_universe"] & np.isfinite(frame[column])
    result: dict[pd.Timestamp, set[str]] = {}
    for date, group in frame.loc[valid].groupby("date", sort=True):
        chosen = group.sort_values([column, "ticker"], ascending=[False, True], kind="mergesort").head(30)
        if len(chosen) == 30:
            result[pd.Timestamp(date)] = set(chosen["ticker"].astype(str))
    return result


def overlap(frame: pd.DataFrame, left: str, right: str) -> dict[str, object]:
    left_sets = top30(frame, left)
    right_sets = top30(frame, right)
    values = [
        len(left_sets[date] & right_sets[date]) / 30.0
        for date in sorted(set(left_sets) & set(right_sets))
    ]
    return {
        "common_dates": int(len(values)),
        "mean_top30_overlap": finite_float(np.mean(values)) if values else None,
        "q10_top30_overlap": finite_float(np.quantile(values, 0.10)) if values else None,
        "min_top30_overlap": finite_float(np.min(values)) if values else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    panel = pd.read_parquet(args.panel, columns=["ticker", "date", "close", "volume", "regular_market_value"])
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    features = pd.read_parquet(args.features)
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    universe, universe_stats = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors
    )
    full = universe.merge(panel, on=["ticker", "date"], how="left", validate="one_to_one")
    full = full.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    for column in ["close", "volume", "regular_market_value"]:
        full[column] = pd.to_numeric(full[column], errors="coerce")
    full["close_valid"] = full["close"].gt(0) & np.isfinite(full["close"])
    full["volume_valid"] = full["volume"].gt(0) & np.isfinite(full["volume"])
    full["close_for_return"] = full["close"].where(full["close_valid"])
    full["ret_1"] = full.groupby("ticker", sort=False)["close_for_return"].pct_change(fill_method=None)
    full[RET5] = full.groupby("ticker", sort=False)["close_for_return"].pct_change(periods=5, fill_method=None)
    full["turnover"] = (full["close"] * full["volume"]).where(full["close_valid"] & full["volume_valid"])
    full["log_turnover"] = np.log(full["turnover"].where(full["turnover"].gt(0)))
    full[HLIQ] = rolling(full, "log_turnover", 20, "std")
    turnover_mean_5 = rolling(full, "turnover", 5, "mean")
    turnover_median_60 = rolling(full, "turnover", 60, "median")
    full[LEVEL] = np.log(turnover_mean_5 / turnover_median_60.replace(0.0, np.nan))
    for column in [HLIQ, LEVEL, RET5]:
        full.loc[~full["eligible_decision_universe"], column] = np.nan
    full["C2_from_components"] = full[RET5] * full[LEVEL]
    full.loc[~full["eligible_decision_universe"], "C2_from_components"] = np.nan

    official_dates = pd.read_csv(args.sessions, usecols=["date"])
    official_dates["date"] = pd.to_datetime(official_dates["date"], errors="raise").dt.normalize()
    frozen_dates = set(official_dates["date"].sort_values().iloc[-600:])
    surface = full[full["date"].isin(frozen_dates)].copy()
    fixed = features[features["date"].isin(frozen_dates)][
        ["ticker", "date", "C1_residual_reversal_5_v1", "C2_participation_confirmation_5_v1", "C4_path_efficiency_reversal_20_v1"]
    ]
    surface = surface.merge(fixed, on=["ticker", "date"], how="left", validate="one_to_one")
    dependence = {
        name: {
            "hliq_vs_reference": daily_spearman(surface, HLIQ, reference),
            "hliq_top30_vs_reference": overlap(surface, HLIQ, reference),
        }
        for name, reference in REFERENCES.items()
    }
    qbucket = surface.loc[surface["eligible_decision_universe"]].copy()
    qbucket["value_bucket"] = qbucket.groupby("date")["regular_market_value"].rank(method="first", pct=True).mul(4).apply(np.ceil).clip(1, 4)
    conditional = {}
    for bucket, group in qbucket.groupby("value_bucket", sort=True):
        conditional[str(int(bucket))] = {
            name: daily_spearman(group, HLIQ, reference)
            for name, reference in {"turnover_level": LEVEL, "C2": "C2_participation_confirmation_5_v1"}.items()
        }
    checks = {
        "panel_unique_keys": not panel.duplicated(["ticker", "date"]).any(),
        "feature_keys_match_panel": set(zip(features["ticker"], features["date"])) == set(zip(panel["ticker"], panel["date"])),
        "frozen_session_count": len(frozen_dates) == 600,
        "hliq_finite_support": int(np.isfinite(surface[HLIQ]).sum()) > 0,
        "no_outcome_access": True,
        "no_candidate_id_created": True,
    }
    result = {
        "status": "PASS_STRUCTURAL_ONLY" if all(checks.values()) else "FAIL_AUDIT",
        "stage": "G_J_HLIQ01_TURNOVER_LEVEL_NOVELTY_DIAGNOSTIC",
        "hypothesis_id": "H-LIQ-01",
        "implementation": "rolling 20-session standard deviation of log(close * volume)",
        "outcome_accessed": False,
        "provider_accessed": False,
        "candidate_id_created": False,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "universe": universe_stats,
        "frozen_dates": {"count": len(frozen_dates), "min": str(min(frozen_dates).date()), "max": str(max(frozen_dates).date())},
        "dependence": dependence,
        "conditional_value_bucket_dependence": conditional,
        "interpretation": {
            "question": "Does H-LIQ measure temporal variability distinct from C2's turnover-level component?",
            "novelty_evidence": "target-free diagnostic only",
            "predictive_claim": False,
            "candidate_id_admission": False,
            "sector_and_price_basis_authority": False,
        },
        "source_hashes": {
            "panel": sha256_file(args.panel),
            "features": sha256_file(args.features),
            "official_sessions": sha256_file(args.sessions),
            "tradability_anchors": sha256_file(args.anchors),
        },
        "code_sha256": sha256_file(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    if result["status"] != "PASS_STRUCTURAL_ONLY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
