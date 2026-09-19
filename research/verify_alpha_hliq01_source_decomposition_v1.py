"""Independent target-free verifier for the H-LIQ source decomposition artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import build_decision_universe, rolling


HLIQ = "HLIQ01_variability_log_turnover_20_v1"
LEVEL = "C2_turnover_level_component_log_abnormal_5_over_60"
C2 = "C2_participation_confirmation_5_v1"
C1 = "C1_residual_reversal_5_v1"
C4 = "C4_path_efficiency_reversal_20_v1"
TOP_K = 30
FROZEN_SESSIONS = 600
EXPECTED_SESSIONS_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_ANCHORS_SHA256 = "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(left: object, right: object, tolerance: float = 1e-12) -> bool:
    try:
        return bool(np.isclose(float(left), float(right), rtol=tolerance, atol=tolerance))
    except (TypeError, ValueError):
        return False


def daily_spearman(frame: pd.DataFrame, left: str, right: str) -> float:
    values: list[float] = []
    valid = (
        frame["eligible_decision_universe"]
        & np.isfinite(frame[left])
        & np.isfinite(frame[right])
    )
    for _, group in frame.loc[valid].groupby("date", sort=True):
        if len(group) < TOP_K:
            continue
        correlation = group[left].rank(method="average").corr(
            group[right].rank(method="average"), method="spearman"
        )
        if pd.notna(correlation):
            values.append(float(correlation))
    return float(np.mean(values)) if values else float("nan")


def top30(frame: pd.DataFrame, column: str) -> dict[pd.Timestamp, set[str]]:
    valid = frame["eligible_decision_universe"] & np.isfinite(frame[column])
    result: dict[pd.Timestamp, set[str]] = {}
    for date, group in frame.loc[valid].groupby("date", sort=True):
        chosen = group.sort_values(
            [column, "ticker"], ascending=[False, True], kind="mergesort"
        ).head(TOP_K)
        if len(chosen) == TOP_K:
            result[pd.Timestamp(date)] = set(chosen["ticker"].astype(str))
    return result


def top30_summary(frame: pd.DataFrame, left: str, right: str) -> dict[str, float | int]:
    baseline = top30(frame, left)
    variant = top30(frame, right)
    dates = sorted(set(baseline) & set(variant))
    overlaps = [len(baseline[date] & variant[date]) / TOP_K for date in dates]
    turnovers = [1.0 - overlap for overlap in overlaps]
    return {
        "common_dates": len(dates),
        "mean_overlap": float(np.mean(overlaps)),
        "min_overlap": float(np.min(overlaps)),
        "mean_turnover": float(np.mean(turnovers)),
        "q95_turnover": float(np.quantile(turnovers, 0.95)),
        "max_turnover": float(np.max(turnovers)),
    }


def bottom_value_q1_share(frame: pd.DataFrame, score: str) -> float:
    work = frame.loc[
        frame["eligible_decision_universe"]
        & np.isfinite(frame[score])
        & np.isfinite(frame["regular_market_value"])
        & frame["regular_market_value"].gt(0),
        ["date", "ticker", score, "regular_market_value"],
    ].copy()
    work["value_percentile"] = work.groupby("date")["regular_market_value"].rank(
        pct=True, method="average"
    )
    selected: list[pd.DataFrame] = []
    for _, group in work.groupby("date", sort=True):
        chosen = group.sort_values(
            [score, "ticker"], ascending=[False, True], kind="mergesort"
        ).head(TOP_K)
        if len(chosen) == TOP_K:
            selected.append(chosen)
    selected_frame = pd.concat(selected, ignore_index=True)
    return float(selected_frame["value_percentile"].le(0.25).mean())


def residualize(surface: pd.DataFrame) -> tuple[pd.Series, int, int]:
    valid = (
        surface["eligible_decision_universe"]
        & np.isfinite(surface[HLIQ])
        & np.isfinite(surface[LEVEL])
    )
    residual = pd.Series(np.nan, index=surface.index, dtype="float64")
    dates_used = 0
    rows_used = 0
    for _, group in surface.loc[valid].groupby("date", sort=True):
        if len(group) < TOP_K:
            continue
        x = group[LEVEL].rank(method="average", pct=True).to_numpy(dtype="float64")
        y = group[HLIQ].rank(method="average", pct=True).to_numpy(dtype="float64")
        design = np.column_stack([np.ones(len(group)), x])
        coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
        residual.loc[group.index] = y - design @ coefficients
        dates_used += 1
        rows_used += len(group)
    return residual, dates_used, rows_used


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    panel = pd.read_parquet(
        args.panel,
        columns=["ticker", "date", "close", "volume", "regular_market_value"],
    )
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    features = pd.read_parquet(args.features, columns=["ticker", "date", C1, C4])
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    universe, _ = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors
    )

    full = universe.merge(panel, on=["ticker", "date"], how="left", validate="one_to_one")
    full = full.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    for column in ["close", "volume", "regular_market_value"]:
        full[column] = pd.to_numeric(full[column], errors="coerce")
    close_valid = full["close"].gt(0) & np.isfinite(full["close"])
    volume_valid = full["volume"].gt(0) & np.isfinite(full["volume"])
    close_for_return = full["close"].where(close_valid)
    full["return_source"] = close_for_return
    full["ret_5"] = full.groupby("ticker", sort=False)["return_source"].pct_change(
        periods=5, fill_method=None
    )
    full["turnover_source"] = (full["close"] * full["volume"]).where(
        close_valid & volume_valid
    )
    full["log_turnover_source"] = np.log(full["turnover_source"].where(full["turnover_source"].gt(0)))
    full[HLIQ] = rolling(full, "log_turnover_source", 20, "std")
    turnover_mean_5 = rolling(full, "turnover_source", 5, "mean")
    turnover_median_60 = rolling(full, "turnover_source", 60, "median")
    full[LEVEL] = np.log(turnover_mean_5 / turnover_median_60.replace(0.0, np.nan))
    full[C2] = full["ret_5"] * full[LEVEL]
    for column in [HLIQ, LEVEL, C2]:
        full.loc[~full["eligible_decision_universe"], column] = np.nan

    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    frozen_dates = set(sessions["date"].sort_values().iloc[-FROZEN_SESSIONS:])
    fixed = features[features["date"].isin(frozen_dates)].copy()
    surface = full[full["date"].isin(frozen_dates)].merge(
        fixed, on=["ticker", "date"], how="left", validate="one_to_one"
    )
    surface["residual"] , dates_used, rows_used = residualize(surface)

    artifact_dependence = artifact["dependence"]
    artifact_top = artifact["top30_baseline_vs_residual"]
    artifact_bottom = artifact["bottom_value_q1_share"]
    checks: dict[str, bool] = {
        "artifact_status": artifact.get("status") == "PASS_STRUCTURAL_ONLY",
        "artifact_stage": artifact.get("stage") == "D_E_F_G_J_K_HLIQ01_SOURCE_DECOMPOSITION",
        "no_outcome_access": artifact.get("outcome_accessed") is False,
        "no_provider_access": artifact.get("provider_accessed") is False,
        "no_candidate_id_created": artifact.get("candidate_id_created") is False,
        "artifact_code_hash": artifact.get("code_sha256") == sha256_file(args.code),
        "panel_hash": artifact.get("source_hashes", {}).get("panel") == sha256_file(args.panel),
        "features_hash": artifact.get("source_hashes", {}).get("features") == sha256_file(args.features),
        "sessions_hash": artifact.get("source_hashes", {}).get("official_sessions") == sha256_file(args.sessions),
        "anchors_hash": artifact.get("source_hashes", {}).get("tradability_anchors") == sha256_file(args.anchors),
        "frozen_sessions_exact": len(frozen_dates) == FROZEN_SESSIONS,
        "recomputed_residual_dates": dates_used == artifact["checks"]["residual_dates_used"],
        "recomputed_residual_rows": rows_used == artifact["checks"]["residual_rows_used"],
        "turnover_level_spearman": close(
            daily_spearman(surface, HLIQ, LEVEL),
            artifact_dependence["turnover_level"]["baseline"]["mean_daily_spearman"],
        ),
        "residual_turnover_level_spearman": close(
            daily_spearman(surface, "residual", LEVEL),
            artifact_dependence["turnover_level"]["residual"]["mean_daily_spearman"],
        ),
        "baseline_c2_spearman": close(
            daily_spearman(surface, HLIQ, C2),
            artifact_dependence["C2"]["baseline"]["mean_daily_spearman"],
        ),
        "residual_c2_spearman": close(
            daily_spearman(surface, "residual", C2),
            artifact_dependence["C2"]["residual"]["mean_daily_spearman"],
        ),
        "top30_mean_overlap": close(
            top30_summary(surface, HLIQ, "residual")["mean_overlap"], artifact_top["mean_overlap"]
        ),
        "top30_min_overlap": close(
            top30_summary(surface, HLIQ, "residual")["min_overlap"], artifact_top["min_overlap"]
        ),
        "bottom_value_baseline": close(
            bottom_value_q1_share(surface, HLIQ), artifact_bottom["baseline"]["bottom_value_q1_share"]
        ),
        "bottom_value_residual": close(
            bottom_value_q1_share(surface, "residual"), artifact_bottom["residual"]["bottom_value_q1_share"]
        ),
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verification_type": "independent_recomputation_target_free",
        "artifact_sha256": sha256_file(args.artifact),
        "verifier_code_sha256": sha256_file(Path(__file__)),
        "checks": checks,
        "recomputed": {
            "residual_dates_used": dates_used,
            "residual_rows_used": rows_used,
            "turnover_level_baseline_mean_daily_spearman": daily_spearman(surface, HLIQ, LEVEL),
            "turnover_level_residual_mean_daily_spearman": daily_spearman(surface, "residual", LEVEL),
            "c2_baseline_mean_daily_spearman": daily_spearman(surface, HLIQ, C2),
            "c2_residual_mean_daily_spearman": daily_spearman(surface, "residual", C2),
            "top30": top30_summary(surface, HLIQ, "residual"),
            "bottom_value_q1_share_baseline": bottom_value_q1_share(surface, HLIQ),
            "bottom_value_q1_share_residual": bottom_value_q1_share(surface, "residual"),
        },
        "scope": {
            "outcome_accessed": False,
            "provider_accessed": False,
            "cloud_accessed": False,
            "incumbent_predictive_accessed": False,
        },
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise SystemExit(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
