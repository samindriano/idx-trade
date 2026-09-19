"""Outcome-blind Stage A construction for the frozen alpha research roster.

This script reads only the two admitted local research artifacts, never reads a
target/label, and writes derived features plus a structural audit to an
explicit external staging directory.  The formulas are intentionally fixed
to the frozen protocol; there is no parameter search or retry path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


PANEL_COLUMNS = ["ticker", "date", "close", "volume"]
FINANCIAL_COLUMNS = [
    "ticker",
    "date",
    "leverage_liabilities_to_assets__value",
    "liquidity_cash_to_assets__value",
    "margin_net_income_to_revenue__value",
    "yoy_revenue__value",
    "yoy_total_assets__value",
    "all_five_available",
    "selected_bundle_provenance_complete",
]

OUTCOME_NAME_RE = ("return", "target", "label", "outcome", "pnl", "nav", "sharpe")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_stats(series: pd.Series) -> dict[str, object]:
    finite = series.replace([np.inf, -np.inf], np.nan).dropna()
    if finite.empty:
        return {"finite_rows": 0, "min": None, "max": None, "median": None}
    return {
        "finite_rows": int(finite.size),
        "min": float(finite.min()),
        "max": float(finite.max()),
        "median": float(finite.median()),
    }


def rolling_sum_by_ticker(frame: pd.DataFrame, column: str, window: int) -> pd.Series:
    return (
        frame.groupby("ticker", sort=False)[column]
        .rolling(window=window, min_periods=window)
        .sum()
        .reset_index(level=0, drop=True)
    )


def rolling_median_by_ticker(frame: pd.DataFrame, column: str, window: int) -> pd.Series:
    return (
        frame.groupby("ticker", sort=False)[column]
        .rolling(window=window, min_periods=window)
        .median()
        .reset_index(level=0, drop=True)
    )


def rolling_std_by_ticker(frame: pd.DataFrame, column: str, window: int) -> pd.Series:
    return (
        frame.groupby("ticker", sort=False)[column]
        .rolling(window=window, min_periods=window)
        .std(ddof=1)
        .reset_index(level=0, drop=True)
    )


def rolling_mean_by_ticker(frame: pd.DataFrame, column: str, window: int) -> pd.Series:
    return (
        frame.groupby("ticker", sort=False)[column]
        .rolling(window=window, min_periods=window)
        .mean()
        .reset_index(level=0, drop=True)
    )


def add_prior_beta(frame: pd.DataFrame) -> pd.Series:
    """Return beta estimated from the 60 observations strictly before each t."""

    frame = frame.copy()
    frame["stock_ret_lag1"] = frame.groupby("ticker", sort=False)["ret_1"].shift(1)
    frame["market_ret_lag1"] = frame.groupby("ticker", sort=False)["market_ret"].shift(1)
    frame["cross_lag1"] = frame["stock_ret_lag1"] * frame["market_ret_lag1"]
    frame["stock_sq_lag1"] = frame["stock_ret_lag1"] ** 2
    groups = frame.groupby("ticker", sort=False)
    n = groups["stock_ret_lag1"].rolling(60, min_periods=60).count().reset_index(level=0, drop=True)
    sx = groups["stock_ret_lag1"].rolling(60, min_periods=60).sum().reset_index(level=0, drop=True)
    sy = groups["market_ret_lag1"].rolling(60, min_periods=60).sum().reset_index(level=0, drop=True)
    sxy = groups["cross_lag1"].rolling(60, min_periods=60).sum().reset_index(level=0, drop=True)
    sxx = groups["stock_sq_lag1"].rolling(60, min_periods=60).sum().reset_index(level=0, drop=True)
    covariance = sxy - (sx * sy / n)
    variance = sxx - (sx * sx / n)
    beta = covariance / variance.replace(0.0, np.nan)
    beta.index = frame.index
    return beta


def rank_by_date(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame.groupby("date", sort=False)[column].rank(method="average", pct=True)


def build_market_features(panel_path: Path) -> pd.DataFrame:
    panel = pd.read_parquet(panel_path, columns=PANEL_COLUMNS)
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    panel["ticker"] = panel["ticker"].astype("string")
    panel = panel.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    panel["close"] = pd.to_numeric(panel["close"], errors="coerce")
    panel["volume"] = pd.to_numeric(panel["volume"], errors="coerce")
    panel["ret_1"] = panel.groupby("ticker", sort=False)["close"].pct_change()
    panel["ret_5"] = panel.groupby("ticker", sort=False)["close"].pct_change(5)
    panel["ret_20"] = panel.groupby("ticker", sort=False)["close"].pct_change(20)
    panel["turnover"] = panel["close"] * panel["volume"]
    panel["abs_ret_1"] = panel["ret_1"].abs()
    panel["abs_ret_sum_20"] = rolling_sum_by_ticker(panel, "abs_ret_1", 20)
    panel["vol_20"] = rolling_std_by_ticker(panel, "ret_1", 20)
    panel["turnover_mean_5"] = rolling_mean_by_ticker(panel, "turnover", 5)
    panel["turnover_median_60"] = rolling_median_by_ticker(panel, "turnover", 60)

    market = panel.groupby("date", sort=True)["ret_1"].mean().rename("market_ret")
    market_index = (1.0 + market.fillna(0.0)).cumprod().rename("market_index")
    market_frame = pd.concat([market, market_index], axis=1)
    market_frame["market_ret_5"] = market_frame["market_index"].pct_change(5)
    panel = panel.join(market_frame, on="date")
    panel["beta_60_prior"] = add_prior_beta(panel)

    # C1: short security-specific reversal after market adjustment.
    panel["C1_residual_reversal_5_v1"] = -(
        panel["ret_5"] - panel["beta_60_prior"] * panel["market_ret_5"]
    ) / panel["vol_20"].replace(0.0, np.nan)

    # C2: fixed participation-confirmation score.
    abnormal_turnover = panel["turnover_mean_5"] / panel["turnover_median_60"].replace(0.0, np.nan)
    panel["C2_participation_confirmation_5_v1"] = panel["ret_5"] * np.log(abnormal_turnover)

    # C4: fixed path-efficiency reversal score.
    panel["C4_path_efficiency_reversal_20_v1"] = -panel["ret_20"] / panel["abs_ret_sum_20"].replace(0.0, np.nan)

    result = panel[
        [
            "ticker",
            "date",
            "C1_residual_reversal_5_v1",
            "C2_participation_confirmation_5_v1",
            "C4_path_efficiency_reversal_20_v1",
        ]
    ].copy()
    result["source_panel_row_present"] = True
    return result


def build_financial_feature(financial_path: Path) -> pd.DataFrame:
    financial = pd.read_parquet(financial_path, columns=FINANCIAL_COLUMNS)
    financial["date"] = pd.to_datetime(financial["date"], errors="raise").dt.normalize()
    financial["ticker"] = financial["ticker"].astype("string")
    values = [
        "leverage_liabilities_to_assets__value",
        "liquidity_cash_to_assets__value",
        "margin_net_income_to_revenue__value",
        "yoy_revenue__value",
        "yoy_total_assets__value",
    ]
    for column in values:
        financial[column] = pd.to_numeric(financial[column], errors="coerce")
    valid = (
        financial["all_five_available"].fillna(False).astype(bool)
        & financial["selected_bundle_provenance_complete"].fillna(False).astype(bool)
        & financial[values].notna().all(axis=1)
        & np.isfinite(financial[values]).all(axis=1)
    )
    # Higher is preferred for every component after the fixed leverage sign flip.
    financial["financial_leverage_positive"] = -financial[values[0]]
    component_ranks = []
    for column in ["financial_leverage_positive", *values[1:]]:
        rank_column = f"rank_{column}"
        financial[rank_column] = financial.groupby("date", sort=False)[column].rank(method="average", pct=True)
        component_ranks.append(rank_column)
    financial["C3_financial_quality_growth_v1"] = financial[component_ranks].mean(axis=1)
    financial.loc[~valid, "C3_financial_quality_growth_v1"] = np.nan
    return financial[["ticker", "date", "C3_financial_quality_growth_v1"]].copy()


def audit_features(features: pd.DataFrame, panel_path: Path, financial_path: Path) -> dict[str, object]:
    candidate_columns = [column for column in features.columns if column.startswith("C")]
    outcome_named_columns = [
        column for column in features.columns if any(token in column.lower() for token in OUTCOME_NAME_RE)
    ]
    duplicate_keys = int(features.duplicated(["ticker", "date"]).sum())
    dates = pd.to_datetime(features["date"])
    counts_by_date = features.groupby("date", sort=True).size()
    counts_by_ticker = features.groupby("ticker", sort=True).size()
    coverage = {}
    finite_stats_by_candidate = {}
    for column in candidate_columns:
        finite = np.isfinite(pd.to_numeric(features[column], errors="coerce"))
        coverage[column] = {
            "finite_rows": int(finite.sum()),
            "coverage_of_rows": float(finite.mean()),
            "date_count": int(features.loc[finite, "date"].nunique()),
            "ticker_count": int(features.loc[finite, "ticker"].nunique()),
            "finite_dates_min": str(features.loc[finite, "date"].min().date()) if finite.any() else None,
            "finite_dates_max": str(features.loc[finite, "date"].max().date()) if finite.any() else None,
        }
        finite_stats_by_candidate[column] = finite_stats(features[column])

    ranked = features[candidate_columns].rank(pct=True)
    correlation = features[candidate_columns].corr(method="spearman", min_periods=100).round(8)
    top_ticker_share = float(counts_by_ticker.nlargest(10).sum() / len(features)) if len(features) else math.nan
    top_date_share = float(counts_by_date.nlargest(10).sum() / len(features)) if len(features) else math.nan

    return {
        "row_count": int(len(features)),
        "unique_ticker_count": int(features["ticker"].nunique()),
        "date_min": str(dates.min().date()),
        "date_max": str(dates.max().date()),
        "duplicate_ticker_date_rows": duplicate_keys,
        "non_null_ticker_rows": int(features["ticker"].notna().sum()),
        "non_null_date_rows": int(features["date"].notna().sum()),
        "outcome_named_columns": outcome_named_columns,
        "candidate_coverage": coverage,
        "candidate_finite_stats": finite_stats_by_candidate,
        "candidate_spearman_correlation": correlation.to_dict(),
        "candidate_rank_spearman_correlation": ranked.corr(method="spearman", min_periods=100).round(8).to_dict(),
        "top_10_ticker_row_share": top_ticker_share,
        "top_10_date_row_share": top_date_share,
        "source_hashes": {
            "panel": sha256_file(panel_path),
            "financial": sha256_file(financial_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--financial", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    market_features = build_market_features(args.panel)
    financial_features = build_financial_feature(args.financial)
    features = market_features.merge(financial_features, on=["ticker", "date"], how="left", validate="one_to_one")
    features = features.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    audit = audit_features(features, args.panel, args.financial)
    audit["protocol"] = "2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1"
    audit["stage"] = "A_OUTCOME_BLIND"
    audit["feature_code_sha256"] = sha256_file(Path(__file__))
    audit["financial_join"] = {
        "market_feature_rows": int(len(market_features)),
        "financial_feature_rows": int(len(financial_features)),
        "joined_financial_rows": int(features["C3_financial_quality_growth_v1"].notna().sum()),
    }
    features.to_parquet(args.out_dir / "alpha_stage_a_features.parquet", index=False)
    (args.out_dir / "alpha_stage_a_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8"
    )
    manifest = {
        "protocol": audit["protocol"],
        "stage": audit["stage"],
        "feature_code_sha256": audit["feature_code_sha256"],
        "files": {
            "alpha_stage_a_features.parquet": sha256_file(args.out_dir / "alpha_stage_a_features.parquet"),
            "alpha_stage_a_audit.json": sha256_file(args.out_dir / "alpha_stage_a_audit.json"),
        },
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False))
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
