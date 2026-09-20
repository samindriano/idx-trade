"""Outcome-blind component anatomy for the fixed market candidates.

The audit reconstructs only the C1/C2/C4 market-side formula components from
the frozen structural panel and official calendar, checks the recomputed scores
against the guarded feature artifact, and describes component/rank geometry.
It does not read financial outcomes, targets, forward returns, or incumbent
predictive state, and it does not create a candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CANDIDATES = {
    "C1": "C1_residual_reversal_5_v1",
    "C2": "C2_participation_confirmation_5_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}
FEATURE_COLUMNS = [
    "ticker",
    "date",
    "eligible_decision_universe",
    *(CANDIDATES.values()),
    *(f"rank_{column}" for column in CANDIDATES.values()),
]
PANEL_COLUMNS = ["ticker", "date", "close", "volume"]
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_float(value: object) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if np.isfinite(converted) else None


def quantile_summary(values: pd.Series | list[float]) -> dict[str, float | int | None]:
    series = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return {"count": 0, "min": None, "q25": None, "median": None, "q75": None, "q95": None, "max": None, "mean": None, "std": None}
    return {
        "count": int(len(series)),
        "min": finite_float(series.min()),
        "q25": finite_float(series.quantile(0.25)),
        "median": finite_float(series.median()),
        "q75": finite_float(series.quantile(0.75)),
        "q95": finite_float(series.quantile(0.95)),
        "max": finite_float(series.max()),
        "mean": finite_float(series.mean()),
        "std": finite_float(series.std(ddof=1)),
    }


def correlation_summary(values: list[float]) -> dict[str, float | int | None]:
    return quantile_summary(values)


def rolling(frame: pd.DataFrame, column: str, window: int, operation: str) -> pd.Series:
    grouped = frame.groupby("ticker", sort=False)[column].rolling(window=window, min_periods=window)
    value = getattr(grouped, operation)().reset_index(level=0, drop=True)
    value.index = frame.index
    return value


def prepare_surface(features: pd.DataFrame, panel: pd.DataFrame, official_dates: pd.Series | pd.Index) -> tuple[pd.DataFrame, pd.Index]:
    missing_features = set(FEATURE_COLUMNS).difference(features.columns)
    missing_panel = set(PANEL_COLUMNS).difference(panel.columns)
    if missing_features or missing_panel:
        raise ValueError(f"missing features={sorted(missing_features)} panel={sorted(missing_panel)}")
    features = features[FEATURE_COLUMNS].copy()
    panel = panel[PANEL_COLUMNS].copy()
    panel["source_panel_row_present"] = True
    for frame in (features, panel):
        frame["ticker"] = frame["ticker"].astype("string")
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if features.duplicated(["ticker", "date"]).any() or panel.duplicated(["ticker", "date"]).any():
        raise ValueError("duplicate ticker/date keys")
    feature_keys = features[["ticker", "date"]].sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    panel_keys = panel[["ticker", "date"]].sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    if not feature_keys.equals(panel_keys):
        raise ValueError("feature and panel keys differ")
    sessions = pd.Series(pd.to_datetime(official_dates, errors="raise"), dtype="datetime64[ns]").dt.normalize()
    sessions = sessions.drop_duplicates().sort_values().reset_index(drop=True)
    official = pd.Index(sessions, name="date")
    if not panel["date"].isin(official).all():
        raise ValueError("panel dates fall outside official sessions")
    tickers = pd.Index(sorted(panel["ticker"].dropna().unique()), name="ticker")
    grid = pd.MultiIndex.from_product([tickers, official], names=["ticker", "date"]).to_frame(index=False)
    surface = grid.merge(panel, on=["ticker", "date"], how="left", validate="one_to_one")
    surface = surface.merge(features, on=["ticker", "date"], how="left", validate="one_to_one", suffixes=("", "_feature"))
    surface["source_panel_row_present"] = surface["source_panel_row_present"].astype("boolean").fillna(False).astype(bool)
    surface["eligible_decision_universe"] = surface["eligible_decision_universe"].astype("boolean").fillna(False).astype(bool)
    for column in ["close", "volume"]:
        surface[column] = pd.to_numeric(surface[column], errors="coerce")
    surface = surface.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    return surface, official


def build_components(surface: pd.DataFrame, official: pd.Index) -> pd.DataFrame:
    surface["close_valid"] = surface["close"].gt(0) & np.isfinite(surface["close"])
    surface["volume_valid"] = surface["volume"].gt(0) & np.isfinite(surface["volume"])
    surface["close_for_return"] = surface["close"].where(surface["close_valid"])
    surface["ret_1"] = surface.groupby("ticker", sort=False)["close_for_return"].pct_change(fill_method=None)
    surface["ret_5"] = surface.groupby("ticker", sort=False)["close_for_return"].pct_change(periods=5, fill_method=None)
    surface["ret_20"] = surface.groupby("ticker", sort=False)["close_for_return"].pct_change(periods=20, fill_method=None)
    surface["turnover"] = (surface["close"] * surface["volume"]).where(surface["close_valid"] & surface["volume_valid"])
    surface["abs_ret_1"] = surface["ret_1"].abs()
    surface["abs_ret_sum_20"] = rolling(surface, "abs_ret_1", 20, "sum")
    surface["vol_20"] = rolling(surface, "ret_1", 20, "std")
    surface["turnover_mean_5"] = rolling(surface, "turnover", 5, "mean")
    surface["turnover_median_60"] = rolling(surface, "turnover", 60, "median")
    eligible_returns = surface.loc[
        surface["source_panel_row_present"] & surface["eligible_decision_universe"] & np.isfinite(surface["ret_1"]),
        ["date", "ret_1"],
    ]
    market_ret = eligible_returns.groupby("date", sort=True)["ret_1"].mean().reindex(official)
    surface["market_ret"] = surface["date"].map(market_ret)
    market_ret_5 = (1.0 + market_ret).rolling(window=5, min_periods=5).apply(np.prod, raw=True).sub(1.0)
    surface["market_ret_5"] = surface["date"].map(market_ret_5)
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
    covariance = sxy - sx * sy / n
    market_variance = syy - sy * sy / n
    surface["beta_60_prior"] = covariance / market_variance.replace(0.0, np.nan)
    surface["c1_beta_market_component"] = surface["beta_60_prior"] * surface["market_ret_5"]
    surface["c1_residual"] = surface["ret_5"] - surface["c1_beta_market_component"]
    surface["c1_score_recomputed"] = -surface["c1_residual"] / surface["vol_20"].replace(0.0, np.nan)
    surface["c2_log_abnormal_turnover"] = np.log(surface["turnover_mean_5"] / surface["turnover_median_60"].replace(0.0, np.nan))
    surface["c2_score_recomputed"] = surface["ret_5"] * surface["c2_log_abnormal_turnover"]
    surface["c4_score_recomputed"] = -surface["ret_20"] / surface["abs_ret_sum_20"].replace(0.0, np.nan)
    return surface


def daily_component_correlations(frame: pd.DataFrame, candidate: str, component_columns: list[str]) -> dict[str, Any]:
    score_column = CANDIDATES[candidate]
    rank_column = f"rank_{score_column}"
    valid = frame["eligible_decision_universe"] & frame[score_column].notna() & frame[rank_column].notna()
    score_rank_correlations: dict[str, list[float]] = {column: [] for column in component_columns}
    top30_percentiles: dict[str, list[float]] = {column: [] for column in component_columns}
    formula_differences: list[float] = []
    recomputed_column = f"{candidate.lower()}_score_recomputed"
    for _, group in frame.loc[valid].groupby("date", sort=True):
        if len(group) < 3:
            continue
        score = pd.to_numeric(group[score_column], errors="coerce")
        recomputed = pd.to_numeric(group[recomputed_column], errors="coerce")
        finite_score = score.notna() & recomputed.notna()
        if finite_score.any():
            formula_differences.extend((score[finite_score] - recomputed[finite_score]).abs().tolist())
        ordered = group.sort_values([rank_column, "ticker"], ascending=[False, True], kind="mergesort").head(30)
        for column in component_columns:
            pair = pd.DataFrame({"score": score, "component": pd.to_numeric(group[column], errors="coerce")}).dropna()
            if len(pair) >= 3 and pair["score"].nunique() > 1 and pair["component"].nunique() > 1:
                corr = pair["score"].corr(pair["component"], method="spearman")
                if np.isfinite(corr):
                    score_rank_correlations[column].append(float(corr))
            percentile = pd.to_numeric(group[column], errors="coerce").rank(pct=True, method="average")
            selected_percentile = percentile.loc[ordered.index].dropna()
            if not selected_percentile.empty:
                top30_percentiles[column].append(float(selected_percentile.mean()))
    return {
        "formula_max_abs_difference": finite_float(max(formula_differences)) if formula_differences else None,
        "formula_checked_values": int(len(formula_differences)),
        "component_vs_score_daily_spearman": {column: correlation_summary(values) for column, values in score_rank_correlations.items()},
        "top30_component_percentile_mean": {column: quantile_summary(values) for column, values in top30_percentiles.items()},
    }


def summarize(features: pd.DataFrame, panel: pd.DataFrame, official_dates: pd.Series | pd.Index) -> dict[str, Any]:
    surface, official = prepare_surface(features, panel, official_dates)
    surface = build_components(surface, official)
    definitions = {
        "C1": ["c1_residual", "c1_beta_market_component", "vol_20"],
        "C2": ["ret_5", "c2_log_abnormal_turnover"],
        "C4": ["ret_20", "abs_ret_sum_20"],
    }
    return {
        "status": "PASS_STRUCTURAL_COMPONENT_ANATOMY",
        "scope": "Outcome-blind component/rank anatomy for fixed C1/C2/C4 formulas; no policy, era, candidate, or outcome selection.",
        "formula_definitions": {
            "C1": "-(ret_5 - beta_60_prior * market_ret_5) / vol_20",
            "C2": "ret_5 * log(turnover_mean_5 / turnover_median_60)",
            "C4": "-ret_20 / abs_ret_sum_20",
        },
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official.min().date()) if len(official) else None,
            "official_max": str(official.max().date()) if len(official) else None,
        },
        "panel_rows": int(len(panel)),
        "surface_rows": int(len(surface)),
        "candidates": {candidate: daily_component_correlations(surface, candidate, columns) for candidate, columns in definitions.items()},
        "admission": {
            "policy_selected": False,
            "era_admitted": False,
            "candidate_status_changed": False,
            "protected_boundary": "CLOSED",
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    for path in (args.features, args.panel, args.sessions):
        if any(marker in str(path).lower() for marker in FORBIDDEN_INPUT_MARKERS):
            raise ValueError(f"refusing input path with protected-data marker: {path}")
    features = pd.read_parquet(args.features, columns=FEATURE_COLUMNS)
    panel = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    result = summarize(features, panel, sessions["date"])
    result["inputs"] = {
        "features": {"path": str(args.features), "sha256": sha256_file(args.features), "rows": int(len(features))},
        "panel": {"path": str(args.panel), "sha256": sha256_file(args.panel), "rows": int(len(panel))},
        "official_sessions": {"path": str(args.sessions), "sha256": sha256_file(args.sessions)},
    }
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
