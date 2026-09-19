"""Corrected, outcome-blind Stage A construction for the frozen roster.

This version supersedes the invalid v1 implementation after independent
review. It keeps EOD-t information causal for a t -> t+1 decision, estimates
beta using observations through t-1, applies the authoritative active/liquid
decision mask before market aggregation and ranking, and validates financial
knowledge time explicitly. It never reads a target or forward label.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PANEL_COLUMNS = ["ticker", "date", "close", "volume", "regular_market_value"]
FINANCIAL_COLUMNS = [
    "ticker",
    "date",
    "decision_timestamp_utc",
    "bundle_period_date",
    "bundle_reporting_knowledge_at_utc",
    "bundle_reporting_version_id",
    "bundle_reporting_attachment_sha256",
    "leverage_liabilities_to_assets__value",
    "liquidity_cash_to_assets__value",
    "margin_net_income_to_revenue__value",
    "yoy_revenue__value",
    "yoy_total_assets__value",
    "all_five_available",
    "same_bundle_violation",
    "selected_knowledge_time_violation",
    "selected_bundle_provenance_complete",
]
OUTCOME_TOKENS = ("return", "target", "label", "outcome", "pnl", "nav", "sharpe")
SCORE_COLUMNS = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C3_financial_quality_growth_v1",
    "C4_path_efficiency_reversal_20_v1",
]
EXPECTED_SESSIONS_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_ANCHORS_SHA256 = "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e"
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    return value


def git_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def key_digest(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date"]].copy()
    keys["ticker"] = keys["ticker"].astype("string")
    keys["date"] = pd.to_datetime(keys["date"], errors="raise").dt.strftime("%Y-%m-%d")
    payload = keys.sort_values(["ticker", "date"], kind="mergesort").to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def rolling(frame: pd.DataFrame, column: str, window: int, operation: str) -> pd.Series:
    grouped = frame.groupby("ticker", sort=False)[column].rolling(
        window=window, min_periods=window
    )
    value = getattr(grouped, operation)().reset_index(level=0, drop=True)
    value.index = frame.index
    return value


def build_decision_universe(
    panel: pd.DataFrame, sessions_path: Path, anchors_path: Path
) -> tuple[pd.DataFrame, dict[str, object]]:
    sessions = pd.read_csv(sessions_path, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    if sessions["date"].duplicated().any():
        raise ValueError("official session dates are not unique")
    if sha256_file(sessions_path) != EXPECTED_SESSIONS_SHA256:
        raise ValueError("official session artifact hash is not the frozen canonical hash")
    sessions = sessions.sort_values("date").reset_index(drop=True)
    panel_dates = set(panel["date"].dropna().unique())
    session_dates = set(sessions["date"].unique())
    if not panel_dates.issubset(session_dates):
        raise ValueError("panel contains dates outside the official session calendar")

    if sha256_file(anchors_path) != EXPECTED_ANCHORS_SHA256:
        raise ValueError("tradability anchor artifact hash is not the frozen canonical hash")
    anchors = pd.read_csv(anchors_path)
    required = {"ticker", "market", "as_of_date", "state"}
    missing = required.difference(anchors.columns)
    if missing:
        raise ValueError(f"tradability anchor missing columns: {sorted(missing)}")
    anchors["as_of_date"] = pd.to_datetime(anchors["as_of_date"], errors="raise").dt.normalize()
    active = anchors[(anchors["market"] == "REGULAR") & (anchors["state"] == "ACTIVE")][
        ["ticker", "as_of_date"]
    ].rename(columns={"as_of_date": "date"})
    if active.duplicated(["ticker", "date"]).any():
        raise ValueError("active regular tradability mask has duplicate keys")

    tickers = pd.Index(sorted(panel["ticker"].dropna().unique()), name="ticker")
    grid = pd.MultiIndex.from_product([tickers, sessions["date"]], names=["ticker", "date"])
    full = grid.to_frame(index=False)
    full = full.merge(
        panel[["ticker", "date", "regular_market_value"]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    full["active_regular"] = full.set_index(["ticker", "date"]).index.isin(
        active.set_index(["ticker", "date"]).index
    )
    full["regular_market_value"] = pd.to_numeric(full["regular_market_value"], errors="coerce")
    full["value_for_liquidity"] = full["regular_market_value"].where(
        full["active_regular"]
        & full["regular_market_value"].gt(0)
        & np.isfinite(full["regular_market_value"])
    )
    full = full.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    full["value_count_60"] = rolling(full, "value_for_liquidity", 60, "count")
    full["value_median_60"] = rolling(full, "value_for_liquidity", 60, "median")
    full["eligible_decision_universe"] = (
        full["active_regular"]
        & full["value_count_60"].ge(20)
        & full["value_median_60"].ge(1_000_000_000)
    )
    mask = full[["ticker", "date", "active_regular", "value_count_60", "value_median_60", "eligible_decision_universe"]]
    stats = {
        "session_count": int(len(sessions)),
        "session_min": str(sessions["date"].min().date()),
        "session_max": str(sessions["date"].max().date()),
        "anchor_hash": sha256_file(anchors_path),
        "session_hash": sha256_file(sessions_path),
        "active_regular_rows": int(mask["active_regular"].sum()),
        "eligible_rows": int(mask["eligible_decision_universe"].sum()),
        "eligible_tickers": int(mask.loc[mask["eligible_decision_universe"], "ticker"].nunique()),
    }
    return mask, stats


def build_market_scores(panel_path: Path, universe: pd.DataFrame) -> pd.DataFrame:
    raw = pd.read_parquet(panel_path, columns=PANEL_COLUMNS)
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.normalize()
    raw["ticker"] = raw["ticker"].astype("string")
    if raw.duplicated(["ticker", "date"]).any():
        raise ValueError("panel has duplicate ticker/date keys")
    for column in ["close", "volume", "regular_market_value"]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw["source_panel_row_present"] = True
    # Reindex to every official session so rolling windows count sessions, not
    # merely rows surviving an IPO/no-trade/source-coverage filter.
    panel = universe.merge(raw, on=["ticker", "date"], how="left", validate="one_to_one")
    panel = panel.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    panel["source_panel_row_present"] = panel["source_panel_row_present"].fillna(False).astype(bool)
    panel["eligible_decision_universe"] = panel["eligible_decision_universe"].fillna(False).astype(bool)
    panel["close_valid"] = panel["close"].gt(0) & np.isfinite(panel["close"])
    panel["volume_valid"] = panel["volume"].gt(0) & np.isfinite(panel["volume"])
    panel["close_for_return"] = panel["close"].where(panel["close_valid"])
    panel["ret_1"] = panel.groupby("ticker", sort=False)["close_for_return"].pct_change(
        fill_method=None
    )
    panel["ret_5"] = panel.groupby("ticker", sort=False)["close_for_return"].pct_change(
        periods=5, fill_method=None
    )
    panel["ret_20"] = panel.groupby("ticker", sort=False)["close_for_return"].pct_change(
        periods=20, fill_method=None
    )
    panel["turnover"] = (panel["close"] * panel["volume"]).where(
        panel["close_valid"] & panel["volume_valid"]
    )
    panel["abs_ret_1"] = panel["ret_1"].abs()
    panel["abs_ret_sum_20"] = rolling(panel, "abs_ret_1", 20, "sum")
    panel["vol_20"] = rolling(panel, "ret_1", 20, "std")
    panel["turnover_mean_5"] = rolling(panel, "turnover", 5, "mean")
    panel["turnover_median_60"] = rolling(panel, "turnover", 60, "median")

    eligible_returns = panel.loc[
        panel["source_panel_row_present"]
        & panel["eligible_decision_universe"]
        & np.isfinite(panel["ret_1"]),
        ["date", "ret_1"],
    ]
    official_dates = pd.Index(sorted(universe["date"].unique()), name="date")
    market_ret = eligible_returns.groupby("date", sort=True)["ret_1"].mean().reindex(official_dates)
    market_ret.name = "market_ret"
    market_ret_5 = (
        (1.0 + market_ret)
        .rolling(window=5, min_periods=5)
        .apply(np.prod, raw=True)
        .sub(1.0)
        .rename("market_ret_5")
    )
    market_frame = pd.concat([market_ret, market_ret_5], axis=1)
    panel = panel.join(market_frame, on="date")

    # Beta uses the 60 valid observations through t-1, and divides by market variance.
    panel["stock_ret_lag1"] = panel.groupby("ticker", sort=False)["ret_1"].shift(1)
    panel["market_ret_lag1"] = panel.groupby("ticker", sort=False)["market_ret"].shift(1)
    valid_pair = np.isfinite(panel["stock_ret_lag1"]) & np.isfinite(panel["market_ret_lag1"])
    panel["beta_x"] = panel["stock_ret_lag1"].where(valid_pair)
    panel["beta_y"] = panel["market_ret_lag1"].where(valid_pair)
    panel["beta_xy"] = panel["beta_x"] * panel["beta_y"]
    panel["beta_yy"] = panel["beta_y"] ** 2
    n = rolling(panel, "beta_x", 60, "count")
    sx = rolling(panel, "beta_x", 60, "sum")
    sy = rolling(panel, "beta_y", 60, "sum")
    sxy = rolling(panel, "beta_xy", 60, "sum")
    syy = rolling(panel, "beta_yy", 60, "sum")
    covariance = sxy - (sx * sy / n)
    market_variance = syy - (sy * sy / n)
    panel["beta_60_prior"] = covariance / market_variance.replace(0.0, np.nan)

    panel["C1_residual_reversal_5_v1"] = -(
        panel["ret_5"] - panel["beta_60_prior"] * panel["market_ret_5"]
    ) / panel["vol_20"].replace(0.0, np.nan)
    abnormal_turnover = panel["turnover_mean_5"] / panel["turnover_median_60"].replace(0.0, np.nan)
    panel["C2_participation_confirmation_5_v1"] = panel["ret_5"] * np.log(abnormal_turnover)
    panel["C4_path_efficiency_reversal_20_v1"] = -panel["ret_20"] / panel[
        "abs_ret_sum_20"
    ].replace(0.0, np.nan)
    for column in [
        "C1_residual_reversal_5_v1",
        "C2_participation_confirmation_5_v1",
        "C4_path_efficiency_reversal_20_v1",
    ]:
        panel.loc[~panel["eligible_decision_universe"], column] = np.nan
    return panel.loc[
        panel["source_panel_row_present"],
        [
            "ticker",
            "date",
            "eligible_decision_universe",
            "C1_residual_reversal_5_v1",
            "C2_participation_confirmation_5_v1",
            "C4_path_efficiency_reversal_20_v1",
            "source_panel_row_present",
        ],
    ].copy()


def build_financial_score(financial_path: Path, universe: pd.DataFrame) -> pd.DataFrame:
    financial = pd.read_parquet(financial_path, columns=FINANCIAL_COLUMNS)
    financial["date"] = pd.to_datetime(financial["date"], errors="raise").dt.normalize()
    financial["ticker"] = financial["ticker"].astype("string")
    if financial.duplicated(["ticker", "date"]).any():
        raise ValueError("financial bundle has duplicate ticker/date keys")
    values = [
        "leverage_liabilities_to_assets__value",
        "liquidity_cash_to_assets__value",
        "margin_net_income_to_revenue__value",
        "yoy_revenue__value",
        "yoy_total_assets__value",
    ]
    for column in values:
        financial[column] = pd.to_numeric(financial[column], errors="coerce")
    decision_time = pd.to_datetime(financial["decision_timestamp_utc"], errors="coerce", utc=True)
    knowledge_time = pd.to_datetime(financial["bundle_reporting_knowledge_at_utc"], errors="coerce", utc=True)
    period_date = pd.to_datetime(financial["bundle_period_date"], errors="coerce").dt.normalize()
    knowledge_ok = knowledge_time.notna() & decision_time.notna() & (knowledge_time <= decision_time)
    period_ok = period_date.notna() & (period_date <= financial["date"])
    provenance_ok = (
        financial["selected_bundle_provenance_complete"].fillna(False).astype(bool)
        & financial["bundle_reporting_version_id"].notna()
        & financial["bundle_reporting_attachment_sha256"].notna()
        & financial["bundle_reporting_attachment_sha256"].astype("string").str.len().ge(16)
    )
    financial = financial.merge(
        universe[["ticker", "date", "eligible_decision_universe"]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    valid = (
        financial["all_five_available"].fillna(False).astype(bool)
        & ~financial["same_bundle_violation"].fillna(True).astype(bool)
        & ~financial["selected_knowledge_time_violation"].fillna(True).astype(bool)
        & knowledge_ok
        & period_ok
        & provenance_ok
        & financial[values].notna().all(axis=1)
        & np.isfinite(financial[values]).all(axis=1)
        & financial["eligible_decision_universe"].fillna(False).astype(bool)
    )
    financial["financial_pit_valid"] = valid
    financial["financial_leverage_positive"] = -financial[values[0]]
    components = ["financial_leverage_positive", *values[1:]]
    for column in components:
        rank_column = f"rank_{column}"
        financial[rank_column] = financial.loc[valid].groupby("date", sort=False)[column].rank(
            method="average", pct=True
        )
    rank_columns = [f"rank_{column}" for column in components]
    financial["C3_financial_quality_growth_v1"] = financial[rank_columns].mean(axis=1)
    financial.loc[~valid, "C3_financial_quality_growth_v1"] = np.nan
    return financial[
        ["ticker", "date", "C3_financial_quality_growth_v1", "financial_pit_valid"]
    ]


def audit(
    features: pd.DataFrame,
    source_paths: dict[str, Path],
    universe_stats: dict[str, object],
    code_path: Path,
    repo: Path,
    source_panel_row_count: int,
    source_panel_key_digest: str,
) -> dict[str, object]:
    outcome_named_columns = [
        column for column in features.columns if any(token in column.lower() for token in OUTCOME_TOKENS)
    ]
    duplicate_keys = int(features.duplicated(["ticker", "date"]).sum())
    coverage = {}
    for column in SCORE_COLUMNS:
        finite = np.isfinite(pd.to_numeric(features[column], errors="coerce"))
        coverage[column] = {
            "finite_rows": int(finite.sum()),
            "coverage_of_all_panel_rows": float(finite.mean()),
            "coverage_of_eligible_rows": float(
                finite.sum() / features["eligible_decision_universe"].sum()
            )
            if features["eligible_decision_universe"].sum()
            else None,
            "date_count": int(features.loc[finite, "date"].nunique()),
            "ticker_count": int(features.loc[finite, "ticker"].nunique()),
        }
    finite_scores = features[SCORE_COLUMNS].replace([np.inf, -np.inf], np.nan)
    correlation = finite_scores.corr(method="spearman", min_periods=100).round(8)
    schema = {column: str(dtype) for column, dtype in features.dtypes.items()}
    return json_safe(
        {
            "protocol": "2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1",
            "implementation": "alpha_stage_a_v3_corrected",
            "stage": "A_OUTCOME_BLIND",
            "outcome_accessed": False,
            "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "repo_head": git_head(repo),
            "code_sha256": sha256_file(code_path),
            "source_hashes": {name: sha256_file(path) for name, path in source_paths.items()},
            "source_paths": {name: str(path) for name, path in source_paths.items()},
            "schema": schema,
            "row_count": int(len(features)),
            "source_panel_row_count": int(source_panel_row_count),
            "source_panel_key_digest": source_panel_key_digest,
            "feature_key_digest": key_digest(features),
            "unique_tickers": int(features["ticker"].nunique()),
            "date_min": str(features["date"].min().date()),
            "date_max": str(features["date"].max().date()),
            "duplicate_ticker_date_rows": duplicate_keys,
            "eligible_rows": int(features["eligible_decision_universe"].sum()),
            "outcome_named_columns": outcome_named_columns,
            "candidate_coverage": coverage,
            "candidate_spearman_correlation": correlation.to_dict(),
            "universe": universe_stats,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--financial", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    out_dir = args.out_dir.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(out_dir):
        raise ValueError("refusing output outside the isolated alpha staging root")
    out_dir.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[1]

    panel_for_keys = pd.read_parquet(args.panel, columns=["ticker", "date"])
    panel_for_keys["date"] = pd.to_datetime(panel_for_keys["date"], errors="raise").dt.normalize()
    panel_for_keys["ticker"] = panel_for_keys["ticker"].astype("string")
    if panel_for_keys.duplicated(["ticker", "date"]).any():
        raise ValueError("panel has duplicate ticker/date keys")
    source_panel_row_count = int(len(panel_for_keys))
    source_panel_key_digest = key_digest(panel_for_keys)
    for input_path in [args.panel, args.financial, args.sessions, args.anchors]:
        if any(marker in str(input_path).lower() for marker in FORBIDDEN_INPUT_MARKERS):
            raise ValueError(f"refusing input path with protected-data marker: {input_path}")
    universe, universe_stats = build_decision_universe(panel_for_keys.merge(
        pd.read_parquet(args.panel, columns=["ticker", "date", "regular_market_value"]),
        on=["ticker", "date"], validate="one_to_one"), args.sessions, args.anchors)
    market = build_market_scores(args.panel, universe)
    financial = build_financial_score(args.financial, universe)
    features = market[["ticker", "date", "eligible_decision_universe", *SCORE_COLUMNS[:2], SCORE_COLUMNS[3]]].merge(
        financial, on=["ticker", "date"], how="left", validate="one_to_one"
    )
    features["source_panel_row_present"] = True
    features = features[
        [
            "ticker",
            "date",
            "eligible_decision_universe",
            *SCORE_COLUMNS,
            "financial_pit_valid",
            "source_panel_row_present",
        ]
    ].sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    if len(features) != source_panel_row_count or key_digest(features) != source_panel_key_digest:
        raise ValueError("derived feature keys are not closed over the source panel keys")
    for column in SCORE_COLUMNS:
        features[f"rank_{column}"] = features.groupby("date", sort=False)[column].rank(
            method="average", pct=True
        )

    source_paths = {
        "panel": args.panel,
        "financial": args.financial,
        "official_sessions": args.sessions,
        "tradability_anchors": args.anchors,
    }
    audit_result = audit(
        features,
        source_paths,
        universe_stats,
        Path(__file__),
        repo,
        source_panel_row_count,
        source_panel_key_digest,
    )
    audit_result["feature_code_sha256"] = sha256_file(Path(__file__))
    features_path = out_dir / "alpha_stage_a_v3_features.parquet"
    audit_path = out_dir / "alpha_stage_a_v3_audit.json"
    manifest_path = out_dir / "alpha_stage_a_v3_manifest.json"
    features.to_parquet(features_path, index=False)
    audit_path.write_text(json.dumps(audit_result, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    manifest = json_safe(
        {
            "protocol": audit_result["protocol"],
            "implementation": audit_result["implementation"],
            "stage": audit_result["stage"],
            "files": {
                features_path.name: sha256_file(features_path),
                audit_path.name: sha256_file(audit_path),
            },
            "source_hashes": audit_result["source_hashes"],
            "code_sha256": audit_result["code_sha256"],
            "repo_head": audit_result["repo_head"],
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    print(json.dumps({"audit": audit_result, "manifest": manifest}, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
