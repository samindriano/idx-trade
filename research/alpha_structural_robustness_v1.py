"""Target-free robustness battery for the fixed C1-C4 research candidates.

This harness answers structural questions that the first lab did not cover:
lookback perturbations for C1/C2/C4, monotone normalization invariance,
deterministic missingness stress, leave-ticker-out rank stability, and
calendar/rolling stability.  It never reads targets, forward returns,
incumbent scores, provider data, or protected outcome artifacts.

Perturbed formulas are diagnostic representations only.  They do not create
new candidate IDs, change the candidate budget, or authorize evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import build_decision_universe, rolling, sha256_file


CANDIDATES = {
    "C1": "C1_residual_reversal_5_v1",
    "C2": "C2_participation_confirmation_5_v1",
    "C3": "C3_financial_quality_growth_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}
LOOKBACKS = {
    "C1": (3, 5, 10),
    "C2": (3, 5, 10),
    "C4": (10, 20, 40),
}
TOP_K = 30
FROZEN_SESSIONS = 600


def safe(value):
    if isinstance(value, dict):
        return {str(key): safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    return value


def stable_hash(text: str) -> int:
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "little")


def key_digest(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date"]].copy()
    keys["ticker"] = keys["ticker"].astype("string")
    keys["date"] = pd.to_datetime(keys["date"], errors="raise").dt.strftime("%Y-%m-%d")
    payload = keys.sort_values(["ticker", "date"], kind="mergesort").to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def prepare_surface(panel_path: Path, sessions_path: Path, anchors_path: Path) -> tuple[pd.DataFrame, pd.Series, dict[str, object]]:
    raw = pd.read_parquet(panel_path, columns=["ticker", "date", "close", "volume", "regular_market_value"])
    raw["ticker"] = raw["ticker"].astype("string")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.normalize()
    if raw.duplicated(["ticker", "date"]).any():
        raise ValueError("panel has duplicate ticker/date keys")
    for column in ["close", "volume", "regular_market_value"]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")

    universe, universe_stats = build_decision_universe(raw, sessions_path, anchors_path)
    surface = universe.merge(raw, on=["ticker", "date"], how="left", validate="one_to_one")
    surface = surface.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    surface["source_panel_row_present"] = surface["close"].notna() | surface["volume"].notna()
    surface["eligible_decision_universe"] = surface["eligible_decision_universe"].fillna(False).astype(bool)
    surface["close_valid"] = surface["close"].gt(0) & np.isfinite(surface["close"])
    surface["volume_valid"] = surface["volume"].gt(0) & np.isfinite(surface["volume"])
    surface["close_for_return"] = surface["close"].where(surface["close_valid"])
    surface["ret_1"] = surface.groupby("ticker", sort=False)["close_for_return"].pct_change(
        fill_method=None
    )
    surface["abs_ret_1"] = surface["ret_1"].abs()
    surface["turnover"] = (surface["close"] * surface["volume"]).where(
        surface["close_valid"] & surface["volume_valid"]
    )

    sessions = pd.read_csv(sessions_path, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    official_dates = sessions["date"].drop_duplicates().sort_values().reset_index(drop=True)
    eligible_returns = surface.loc[
        surface["source_panel_row_present"]
        & surface["eligible_decision_universe"]
        & np.isfinite(surface["ret_1"]),
        ["date", "ret_1"],
    ]
    market_ret = eligible_returns.groupby("date", sort=True)["ret_1"].mean().reindex(official_dates)
    market_ret.name = "market_ret"
    surface = surface.join(market_ret, on="date")
    surface["stock_ret_lag1"] = surface.groupby("ticker", sort=False)["ret_1"].shift(1)
    surface["market_ret_lag1"] = surface.groupby("ticker", sort=False)["market_ret"].shift(1)
    valid_pair = np.isfinite(surface["stock_ret_lag1"]) & np.isfinite(surface["market_ret_lag1"])
    surface["beta_x"] = surface["stock_ret_lag1"].where(valid_pair)
    surface["beta_y"] = surface["market_ret_lag1"].where(valid_pair)
    surface["beta_xy"] = surface["beta_x"] * surface["beta_y"]
    surface["beta_yy"] = surface["beta_y"] ** 2
    n = rolling(surface, "beta_x", 60, "count")
    sx = rolling(surface, "beta_x", 60, "sum")
    sy = rolling(surface, "beta_y", 60, "sum")
    sxy = rolling(surface, "beta_xy", 60, "sum")
    syy = rolling(surface, "beta_yy", 60, "sum")
    covariance = sxy - (sx * sy / n)
    market_variance = syy - (sy * sy / n)
    surface["beta_60_prior"] = covariance / market_variance.replace(0.0, np.nan)
    surface["vol_20"] = rolling(surface, "ret_1", 20, "std")
    surface["turnover_median_60"] = rolling(surface, "turnover", 60, "median")
    return surface, official_dates, universe_stats


def build_variant_scores(surface: pd.DataFrame, horizon: int, candidate: str) -> pd.Series:
    ret_h = surface.groupby("ticker", sort=False)["close_for_return"].pct_change(
        periods=horizon, fill_method=None
    )
    if candidate == "C1":
        market_h = (1.0 + surface["market_ret"]).groupby(surface["date"]).first()
        # The market series is already date-aligned; use a compact indexed rolling
        # calculation so every ticker receives the same causal market horizon.
        market_h = (
            (1.0 + surface[["date", "market_ret"]].drop_duplicates("date").set_index("date")["market_ret"])
            .rolling(horizon, min_periods=horizon)
            .apply(np.prod, raw=True)
            .sub(1.0)
            .rename("market_ret_h")
        )
        market_h = surface["date"].map(market_h)
        return -(
            ret_h - surface["beta_60_prior"] * market_h
        ) / surface["vol_20"].replace(0.0, np.nan)
    if candidate == "C2":
        turnover_mean = rolling(surface, "turnover", horizon, "mean")
        abnormal = turnover_mean / surface["turnover_median_60"].replace(0.0, np.nan)
        return ret_h * np.log(abnormal)
    if candidate == "C4":
        abs_sum = rolling(surface, "abs_ret_1", horizon, "sum")
        return -ret_h / abs_sum.replace(0.0, np.nan)
    raise ValueError(f"unsupported candidate {candidate}")


def top_sets(frame: pd.DataFrame, score_column: str, dates: pd.Series, k: int = TOP_K) -> dict[pd.Timestamp, set[str]]:
    usable = frame.loc[
        frame["date"].isin(dates)
        & frame["eligible_decision_universe"]
        & frame["source_panel_row_present"]
        & np.isfinite(frame[score_column]),
        ["date", "ticker", score_column],
    ]
    result: dict[pd.Timestamp, set[str]] = {}
    for date, group in usable.groupby("date", sort=True):
        if len(group) >= k:
            selected = group.sort_values(
                [score_column, "ticker"],
                ascending=[False, True],
                kind="mergesort",
            ).head(k)
            result[pd.Timestamp(date)] = set(selected["ticker"].astype(str))
    return result


def set_metrics(sets: dict[pd.Timestamp, set[str]], baseline: dict[pd.Timestamp, set[str]] | None = None, k: int = TOP_K) -> dict[str, object]:
    dates = sorted(sets)
    turnovers = []
    overlaps = []
    previous = None
    for date in dates:
        current = sets[date]
        if previous is not None:
            turnovers.append(1.0 - len(previous & current) / k)
        if baseline is not None and date in baseline:
            overlaps.append(len(current & baseline[date]) / k)
        previous = current
    return {
        "usable_top_k_dates": len(dates),
        "mean_one_way_turnover": float(np.mean(turnovers)) if turnovers else None,
        "q10_one_way_turnover": float(np.quantile(turnovers, 0.10)) if turnovers else None,
        "q90_one_way_turnover": float(np.quantile(turnovers, 0.90)) if turnovers else None,
        "mean_overlap_vs_baseline": float(np.mean(overlaps)) if overlaps else None,
    }


def score_summary(frame: pd.DataFrame, score_column: str, dates: pd.Series) -> dict[str, object]:
    eligible = frame["eligible_decision_universe"] & frame["source_panel_row_present"]
    values = pd.to_numeric(frame.loc[eligible & frame["date"].isin(dates), score_column], errors="coerce")
    values = values[np.isfinite(values)]
    sets = top_sets(frame, score_column, dates)
    return {
        "finite_rows": int(len(values)),
        "date_count": int(frame.loc[eligible & np.isfinite(frame[score_column]) & frame["date"].isin(dates), "date"].nunique()),
        "ticker_count": int(frame.loc[eligible & np.isfinite(frame[score_column]) & frame["date"].isin(dates), "ticker"].nunique()),
        "skew": float(values.skew()) if len(values) > 2 else None,
        "excess_kurtosis": float(values.kurt()) if len(values) > 3 else None,
        "top30": set_metrics(sets),
    }


def rank_transform_audit(frame: pd.DataFrame, candidate: str, dates: pd.Series) -> dict[str, object]:
    source = CANDIDATES[candidate]
    work = frame[["ticker", "date", "eligible_decision_universe", "source_panel_row_present", source]].copy()
    eligible = work["eligible_decision_universe"] & work["source_panel_row_present"] & work["date"].isin(dates)
    values = pd.to_numeric(work[source], errors="coerce")
    work["rank_pct"] = values.where(eligible).groupby(work["date"]).rank(pct=True)
    mean = values.where(eligible).groupby(work["date"]).transform("mean")
    std = values.where(eligible).groupby(work["date"]).transform("std").replace(0.0, np.nan)
    work["zscore"] = ((values - mean) / std).where(eligible)
    median = values.where(eligible).groupby(work["date"]).transform("median")
    mad = (values.where(eligible) - median).abs().groupby(work["date"]).transform("median")
    work["robust_zscore"] = ((values - median) / (1.4826 * mad).replace(0.0, np.nan)).where(eligible)
    base_sets = top_sets(work, source, dates)
    transforms = {}
    for name in ["rank_pct", "zscore", "robust_zscore"]:
        transformed = top_sets(work, name, dates)
        metrics = set_metrics(transformed, base_sets)
        metrics["exact_top30_set_match_rate"] = float(
            np.mean([transformed[d] == base_sets[d] for d in transformed if d in base_sets])
        ) if transformed else None
        transforms[name] = metrics
    return {"baseline_top30_dates": len(base_sets), "transforms": transforms}


def missingness_stress(frame: pd.DataFrame, candidate: str, dates: pd.Series) -> dict[str, object]:
    source = CANDIDATES[candidate]
    work = frame[["ticker", "date", "eligible_decision_universe", "source_panel_row_present", source]].copy()
    base_sets = top_sets(work, source, dates)
    eligible = work["eligible_decision_universe"] & work["source_panel_row_present"] & np.isfinite(work[source])
    row_hash = pd.util.hash_pandas_object(work[["ticker", "date"]], index=False).astype("uint64")
    results = {}
    for rate in [0.005, 0.01, 0.05]:
        salt = np.uint64(stable_hash(f"{candidate}|missingness|{rate}"))
        masked = eligible & (((row_hash ^ salt) % np.uint64(1_000_000)) < np.uint64(int(rate * 1_000_000)))
        stressed = work.copy()
        stressed["stress_score"] = work[source].where(~masked)
        stressed_sets = top_sets(stressed, "stress_score", dates)
        eligible_dates = work.loc[eligible & work["date"].isin(dates)].groupby("date").size()
        failed_dates = stressed.loc[
            stressed["date"].isin(dates) & stressed["eligible_decision_universe"] & stressed["source_panel_row_present"] & np.isfinite(stressed["stress_score"])
        ].groupby("date").size()
        all_dates = pd.Index(dates)
        results[str(rate)] = {
            "masked_rows": int(masked.sum()),
            "base_finite_rows": int(eligible.sum()),
            "finite_row_loss_rate": float(masked.sum() / eligible.sum()) if eligible.sum() else None,
            "dates_below_top30_after_mask": int((failed_dates.reindex(all_dates, fill_value=0) < TOP_K).sum()),
            "dates_with_baseline_support": int((eligible_dates.reindex(all_dates, fill_value=0) >= TOP_K).sum()),
            "top30": set_metrics(stressed_sets, base_sets),
        }
    return results


def ticker_subsample_stress(frame: pd.DataFrame, candidate: str, dates: pd.Series) -> dict[str, object]:
    source = CANDIDATES[candidate]
    work = frame[["ticker", "date", "eligible_decision_universe", "source_panel_row_present", source]].copy()
    base_sets = top_sets(work, source, dates)
    ticker_hash = work["ticker"].astype(str).map(lambda value: stable_hash(value))
    results = {}
    for seed in [1, 2, 3]:
        salt = np.uint64(stable_hash(f"{candidate}|ticker_subsample|{seed}"))
        removed = ((ticker_hash.astype("uint64") ^ salt) % np.uint64(10)) == 0
        stressed = work.copy()
        eligible = (
            stressed["date"].isin(dates)
            & stressed["eligible_decision_universe"]
            & stressed["source_panel_row_present"]
            & np.isfinite(stressed[source])
        )
        stressed["full_rank_pct"] = stressed[source].where(eligible).groupby(stressed["date"]).rank(pct=True)
        stressed["subset_score"] = work[source].where(~removed)
        subset_eligible = eligible & ~removed
        stressed["subset_rank_pct"] = stressed["subset_score"].where(subset_eligible).groupby(
            stressed["date"]
        ).rank(pct=True)
        subset_sets = top_sets(stressed, "subset_score", dates)
        rank_corr = []
        percentile_shift = []
        for date, group in stressed.loc[
            eligible & subset_eligible
        ].groupby("date", sort=True):
            if len(group) >= 30:
                rank_corr.append(group["full_rank_pct"].corr(group["subset_rank_pct"], method="spearman"))
                percentile_shift.extend((group["full_rank_pct"] - group["subset_rank_pct"]).abs().tolist())
        results[str(seed)] = {
            "removed_ticker_count": int(work.loc[removed, "ticker"].nunique()),
            "removed_row_count": int(removed.sum()),
            "common_name_order_spearman": float(np.nanmean(rank_corr)) if rank_corr else None,
            "mean_common_name_percentile_abs_shift": float(np.mean(percentile_shift)) if percentile_shift else None,
            "q90_common_name_percentile_abs_shift": float(np.quantile(percentile_shift, 0.90)) if percentile_shift else None,
            "top30": set_metrics(subset_sets, base_sets),
        }
    return results


def temporal_audit(frame: pd.DataFrame, candidate: str, dates: pd.Series) -> dict[str, object]:
    source = CANDIDATES[candidate]
    work = frame[["ticker", "date", "eligible_decision_universe", "source_panel_row_present", source]].copy()
    eligible = work["eligible_decision_universe"] & work["source_panel_row_present"]
    annual = {}
    for year, group in work.loc[work["date"].isin(dates)].groupby(work["date"].dt.year):
        valid = eligible.loc[group.index] & np.isfinite(work.loc[group.index, source])
        annual[str(year)] = {
            "eligible_rows": int(eligible.loc[group.index].sum()),
            "finite_rows": int(valid.sum()),
            "coverage": float(valid.sum() / eligible.loc[group.index].sum()) if eligible.loc[group.index].sum() else None,
            "dates": int(group.loc[valid, "date"].nunique()),
        }
    sets = top_sets(work, source, dates)
    ordered = sorted(sets)
    daily_turnover = pd.Series(
        [1.0 - len(sets[ordered[i - 1]] & sets[ordered[i]]) / TOP_K for i in range(1, len(ordered))],
        index=pd.Index(ordered[1:], name="date"),
        dtype="float64",
    )
    rolling_120 = daily_turnover.rolling(120, min_periods=120).mean().dropna()
    return {
        "annual": annual,
        "rolling_120_turnover": {
            "window_count": int(len(rolling_120)),
            "mean": float(rolling_120.mean()) if len(rolling_120) else None,
            "std": float(rolling_120.std()) if len(rolling_120) > 1 else None,
            "q10": float(rolling_120.quantile(0.10)) if len(rolling_120) else None,
            "q90": float(rolling_120.quantile(0.90)) if len(rolling_120) else None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    baseline = pd.read_parquet(args.features)
    baseline["ticker"] = baseline["ticker"].astype("string")
    baseline["date"] = pd.to_datetime(baseline["date"], errors="raise").dt.normalize()
    surface_all, official_dates, universe_stats = prepare_surface(args.panel, args.sessions, args.anchors)
    frozen_dates = official_dates.iloc[-FROZEN_SESSIONS:]
    if len(frozen_dates) != FROZEN_SESSIONS:
        raise ValueError("expected at least 600 official sessions")
    surface = surface_all[surface_all["date"].isin(frozen_dates)].copy()
    baseline = baseline[baseline["date"].isin(frozen_dates)].copy()
    if key_digest(surface.loc[surface["source_panel_row_present"].astype(bool)]) != key_digest(baseline):
        raise ValueError("baseline and recomputed source-panel keys differ")

    # Recompute the frozen base horizons and prove they agree with the admitted
    # Stage A artifact before any perturbation is summarized.
    equivalence = {}
    for candidate, horizon in [("C1", 5), ("C2", 5), ("C4", 20)]:
        recomputed = build_variant_scores(surface_all, horizon, candidate)
        left = surface_all[["ticker", "date", "source_panel_row_present", "eligible_decision_universe"]].copy()
        left = left[left["date"].isin(frozen_dates)]
        recomputed = recomputed.loc[left.index]
        left["recomputed"] = recomputed
        left = left[left["source_panel_row_present"]]
        right = baseline[["ticker", "date", CANDIDATES[candidate]]]
        joined = left.merge(right, on=["ticker", "date"], how="inner", validate="one_to_one")
        finite = np.isfinite(joined["recomputed"]) & np.isfinite(joined[CANDIDATES[candidate]])
        differences = (joined.loc[finite, "recomputed"] - joined.loc[finite, CANDIDATES[candidate]]).abs()
        equivalence[candidate] = {
            "finite_pairs": int(finite.sum()),
            "max_abs_difference": float(differences.max()) if len(differences) else None,
            "mean_abs_difference": float(differences.mean()) if len(differences) else None,
            "within_1e-10": bool(len(differences) and differences.max() <= 1e-10),
        }
        if not equivalence[candidate]["within_1e-10"]:
            raise ValueError(f"baseline formula equivalence failed for {candidate}")

    # Attach the fixed baseline scores to the recomputed surface for all
    # target-free diagnostics.  C3 remains observed-only because its financial
    # source contract is not widened by this structural battery.
    score_cols = [*CANDIDATES.values()]
    surface = surface.merge(baseline[["ticker", "date", *score_cols]], on=["ticker", "date"], how="left", validate="one_to_one")
    evaluation_dates = frozen_dates
    result: dict[str, object] = {
        "status": "PASS_STRUCTURAL_ONLY",
        "implementation": "alpha_structural_robustness_v1",
        "outcome_accessed": False,
        "provider_accessed": False,
        "incumbent_score_accessed": False,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "features_sha256": sha256_file(args.features),
        "panel_sha256": sha256_file(args.panel),
        "sessions_sha256": sha256_file(args.sessions),
        "anchors_sha256": sha256_file(args.anchors),
        "frozen_session_count": int(len(frozen_dates)),
        "frozen_date_min": str(frozen_dates.min().date()),
        "frozen_date_max": str(frozen_dates.max().date()),
        "universe_stats": universe_stats,
        "base_formula_equivalence": equivalence,
        "baseline": {},
        "lookback_variants": {},
        "rank_normalization": {},
        "missingness_stress": {},
        "ticker_subsample_stress": {},
        "temporal": {},
        "interpretation": {
            "candidate_budget_changed": False,
            "variants_are_new_candidates": False,
            "predictive_claim": False,
            "c3_source_contract_widened": False,
        },
        "code_sha256": sha256_file(Path(__file__)),
    }

    for candidate, source in CANDIDATES.items():
        result["baseline"][candidate] = score_summary(surface, source, evaluation_dates)
        result["rank_normalization"][candidate] = rank_transform_audit(surface, candidate, evaluation_dates)
        result["missingness_stress"][candidate] = missingness_stress(surface, candidate, evaluation_dates)
        result["ticker_subsample_stress"][candidate] = ticker_subsample_stress(surface, candidate, evaluation_dates)
        result["temporal"][candidate] = temporal_audit(surface, candidate, evaluation_dates)

    for candidate, horizons in LOOKBACKS.items():
        result["lookback_variants"][candidate] = {}
        for horizon in horizons:
            name = f"h{horizon}"
            if horizon == (5 if candidate in {"C1", "C2"} else 20):
                result["lookback_variants"][candidate][name] = {
                    "is_fixed_baseline": True,
                    "summary": result["baseline"][candidate],
                }
                continue
            variant = build_variant_scores(surface_all, horizon, candidate).loc[surface.index]
            surface_variant = surface[["ticker", "date", "eligible_decision_universe", "source_panel_row_present"]].copy()
            surface_variant["variant_score"] = variant
            result["lookback_variants"][candidate][name] = {
                "is_fixed_baseline": False,
                "summary": score_summary(surface_variant, "variant_score", evaluation_dates),
                "overlap_vs_fixed_baseline": set_metrics(
                    top_sets(surface_variant, "variant_score", evaluation_dates),
                    top_sets(surface, CANDIDATES[candidate], evaluation_dates),
                ),
            }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(safe(result), indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(args.out), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
