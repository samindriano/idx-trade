"""Target-free H-LIQ source decomposition against the fixed C2 level component."""

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
C2 = "C2_participation_confirmation_5_v1"
C1 = "C1_residual_reversal_5_v1"
C4 = "C4_path_efficiency_reversal_20_v1"
TOP_K = 30
FROZEN_SESSIONS = 600


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
    valid = (
        frame["eligible_decision_universe"]
        & np.isfinite(frame[left])
        & np.isfinite(frame[right])
    )
    for _, group in frame.loc[valid].groupby("date", sort=True):
        if len(group) >= TOP_K:
            correlation = group[left].rank(method="average").corr(
                group[right].rank(method="average"), method="spearman"
            )
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
        chosen = group.sort_values(
            [column, "ticker"], ascending=[False, True], kind="mergesort"
        ).head(TOP_K)
        if len(chosen) == TOP_K:
            result[pd.Timestamp(date)] = set(chosen["ticker"].astype(str))
    return result


def top30_metrics(
    frame: pd.DataFrame, baseline_column: str, variant_column: str
) -> dict[str, object]:
    baseline = top30(frame, baseline_column)
    variant = top30(frame, variant_column)
    common_dates = sorted(set(baseline) & set(variant))
    overlaps = [len(baseline[date] & variant[date]) / TOP_K for date in common_dates]
    turnovers = [1.0 - value for value in overlaps]
    return {
        "baseline_dates": int(len(baseline)),
        "variant_dates": int(len(variant)),
        "common_dates": int(len(common_dates)),
        "mean_overlap": finite_float(np.mean(overlaps)) if overlaps else None,
        "q10_overlap": finite_float(np.quantile(overlaps, 0.10)) if overlaps else None,
        "min_overlap": finite_float(np.min(overlaps)) if overlaps else None,
        "mean_turnover": finite_float(np.mean(turnovers)) if turnovers else None,
        "q95_turnover": finite_float(np.quantile(turnovers, 0.95)) if turnovers else None,
        "max_turnover": finite_float(np.max(turnovers)) if turnovers else None,
    }


def bottom_value_q1_share(frame: pd.DataFrame, score_column: str) -> dict[str, object]:
    work = frame.loc[
        frame["eligible_decision_universe"]
        & np.isfinite(frame[score_column])
        & np.isfinite(frame["regular_market_value"])
        & frame["regular_market_value"].gt(0),
        ["date", "ticker", score_column, "regular_market_value"],
    ].copy()
    work["value_percentile"] = work.groupby("date")["regular_market_value"].rank(
        pct=True, method="average"
    )
    selected: list[pd.DataFrame] = []
    for _, group in work.groupby("date", sort=True):
        chosen = group.sort_values(
            [score_column, "ticker"], ascending=[False, True], kind="mergesort"
        ).head(TOP_K)
        if len(chosen) == TOP_K:
            selected.append(chosen)
    if not selected:
        return {"selected_slots": 0, "bottom_value_q1_share": None}
    selected_frame = pd.concat(selected, ignore_index=True)
    return {
        "selected_slots": int(len(selected_frame)),
        "bottom_value_q1_share": finite_float(
            selected_frame["value_percentile"].le(0.25).mean()
        ),
    }


def residualize_hliq(surface: pd.DataFrame) -> tuple[pd.Series, dict[str, int]]:
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
        finite = np.isfinite(x) & np.isfinite(y)
        if finite.sum() < TOP_K:
            continue
        design = np.column_stack([np.ones(int(finite.sum())), x[finite]])
        coefficients, *_ = np.linalg.lstsq(design, y[finite], rcond=None)
        residual.loc[group.index[finite]] = y[finite] - design @ coefficients
        dates_used += 1
        rows_used += int(finite.sum())
    return residual, {"dates_used": dates_used, "rows_used": rows_used}


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

    panel = pd.read_parquet(
        args.panel,
        columns=["ticker", "date", "close", "volume", "regular_market_value"],
    )
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
    close_valid = full["close"].gt(0) & np.isfinite(full["close"])
    volume_valid = full["volume"].gt(0) & np.isfinite(full["volume"])
    close_for_return = full["close"].where(close_valid)
    full["close_for_return"] = close_for_return
    full["ret_5_diagnostic"] = full.groupby("ticker", sort=False)["close_for_return"].pct_change(
        periods=5, fill_method=None
    )
    full["turnover"] = (full["close"] * full["volume"]).where(close_valid & volume_valid)
    full["log_turnover"] = np.log(full["turnover"].where(full["turnover"].gt(0)))
    full[HLIQ] = rolling(full, "log_turnover", 20, "std")
    turnover_mean_5 = rolling(full, "turnover", 5, "mean")
    turnover_median_60 = rolling(full, "turnover", 60, "median")
    full[LEVEL] = np.log(turnover_mean_5 / turnover_median_60.replace(0.0, np.nan))
    full[C2] = full["ret_5_diagnostic"] * full[LEVEL]
    for column in [HLIQ, LEVEL, C2]:
        full.loc[~full["eligible_decision_universe"], column] = np.nan

    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    frozen_dates = set(sessions["date"].sort_values().iloc[-FROZEN_SESSIONS:])
    surface = full[full["date"].isin(frozen_dates)].copy()
    fixed = features[features["date"].isin(frozen_dates)][
        ["ticker", "date", C1, C2.replace("_participation_confirmation_5_v1", "_participation_confirmation_5_v1"), C4]
    ].copy()
    # The C2 feature is overwritten below by the fixed component construction;
    # this merge keeps the stored C1/C4 references on the same key surface.
    fixed = fixed.rename(columns={C2: "C2_stored"}) if C2 in fixed.columns else fixed
    surface = surface.merge(fixed, on=["ticker", "date"], how="left", validate="one_to_one")
    if "C2_stored" in surface.columns:
        surface = surface.drop(columns=["C2_stored"])
    surface["HLIQ01_level_residual_v1"], residual_stats = residualize_hliq(surface)

    references = {"turnover_level": LEVEL, "C2": C2, "C1": C1, "C4": C4}
    dependence = {
        name: {
            "baseline": daily_spearman(surface, HLIQ, column),
            "residual": daily_spearman(surface, "HLIQ01_level_residual_v1", column),
        }
        for name, column in references.items()
    }
    checks = {
        "panel_unique_keys": not panel.duplicated(["ticker", "date"]).any(),
        "feature_keys_match_panel": set(zip(features["ticker"], features["date"]))
        == set(zip(panel["ticker"], panel["date"])),
        "frozen_session_count": len(frozen_dates) == FROZEN_SESSIONS,
        "residual_dates_used": residual_stats["dates_used"],
        "residual_rows_used": residual_stats["rows_used"],
        "no_outcome_access": True,
        "no_candidate_id_created": True,
    }
    result = {
        "status": "PASS_STRUCTURAL_ONLY" if all(bool(value) for value in checks.values()) else "FAIL_AUDIT",
        "stage": "D_E_F_G_J_K_HLIQ01_SOURCE_DECOMPOSITION",
        "hypothesis_id": "H-LIQ-01",
        "implementation": {
            "baseline": "rolling 20-session std(log(close * volume))",
            "removed_component": "cross-sectional percentile rank of log(mean_turnover_5 / median_turnover_60)",
            "residual": "per-date OLS residual of percentile-ranked HLIQ on percentile-ranked C2 turnover-level, intercept included",
            "top_k": TOP_K,
            "frozen_sessions": FROZEN_SESSIONS,
        },
        "outcome_accessed": False,
        "provider_accessed": False,
        "candidate_id_created": False,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "universe": universe_stats,
        "frozen_dates": {
            "count": len(frozen_dates),
            "min": str(min(frozen_dates).date()),
            "max": str(max(frozen_dates).date()),
        },
        "dependence": dependence,
        "top30_baseline_vs_residual": top30_metrics(surface, HLIQ, "HLIQ01_level_residual_v1"),
        "bottom_value_q1_share": {
            "baseline": bottom_value_q1_share(surface, HLIQ),
            "residual": bottom_value_q1_share(surface, "HLIQ01_level_residual_v1"),
        },
        "interpretation": {
            "question": "Does H-LIQ retain a component not explained by C2 turnover-level information?",
            "novelty_evidence": "target-free diagnostic only",
            "predictive_claim": False,
            "candidate_id_admission": False,
            "status_change_authorized": False,
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
