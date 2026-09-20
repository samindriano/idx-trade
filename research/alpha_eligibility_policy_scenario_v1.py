"""Outcome-blind counterfactual impact replay for the 20-vs-60 rule.

This script deliberately evaluates both interpretations without selecting one
as policy.  It reads only the explicitly supplied structural panel, official
session calendar, tradability anchors, and financial capability bundle.  It
does not read targets, outcomes, protected arrays, providers, or cloud state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


CANDIDATES = {
    "C1": "C1_residual_reversal_5_v1",
    "C2": "C2_participation_confirmation_5_v1",
    "C3": "C3_financial_quality_growth_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}
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
WINDOW = 60
POLICIES = (20, 60)
TOP_K = 30
FROZEN_SESSION_COUNT = 600
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def policy_sha(minimum: int) -> str:
    payload = json.dumps(
        {"window": WINDOW, "minimum_finite_observations": minimum, "median_min_periods": minimum},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def rolling(frame: pd.DataFrame, column: str, window: int, operation: str, *, minimum: int | None = None) -> pd.Series:
    min_periods = window if minimum is None else minimum
    grouped = frame.groupby("ticker", sort=False)[column].rolling(window=window, min_periods=min_periods)
    value = getattr(grouped, operation)().reset_index(level=0, drop=True)
    value.index = frame.index
    return value


def build_universe(panel: pd.DataFrame, sessions: pd.DataFrame, anchors: pd.DataFrame, minimum: int) -> tuple[pd.DataFrame, dict[str, object]]:
    session_dates = pd.to_datetime(sessions["date"], errors="raise").dt.normalize().sort_values().reset_index(drop=True)
    if session_dates.duplicated().any():
        raise ValueError("official session dates are not unique")
    anchors = anchors.copy()
    anchors["ticker"] = anchors["ticker"].astype("string")
    anchors["as_of_date"] = pd.to_datetime(anchors["as_of_date"], errors="raise").dt.normalize()
    active = anchors.loc[
        (anchors["market"] == "REGULAR") & (anchors["state"] == "ACTIVE"),
        ["ticker", "as_of_date"],
    ].rename(columns={"as_of_date": "date"})
    if active.duplicated(["ticker", "date"]).any():
        raise ValueError("active regular anchors are duplicated")

    tickers = pd.Index(sorted(panel["ticker"].dropna().unique()), name="ticker")
    full = pd.MultiIndex.from_product([tickers, session_dates], names=["ticker", "date"]).to_frame(index=False)
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
    full["value_count_60"] = rolling(full, "value_for_liquidity", WINDOW, "count", minimum=minimum)
    full["value_median_60"] = rolling(full, "value_for_liquidity", WINDOW, "median", minimum=minimum)
    full["eligible_decision_universe"] = (
        full["active_regular"]
        & full["value_count_60"].ge(minimum)
        & full["value_median_60"].ge(1_000_000_000)
    )
    mask = full[["ticker", "date", "active_regular", "value_count_60", "value_median_60", "eligible_decision_universe"]]
    daily = mask.groupby("date")["eligible_decision_universe"].sum()
    stats = {
        "minimum_finite_observations": minimum,
        "eligible_rows": int(mask["eligible_decision_universe"].sum()),
        "eligible_tickers": int(mask.loc[mask["eligible_decision_universe"], "ticker"].nunique()),
        "eligible_dates": int((daily > 0).sum()),
        "daily_population": {
            "min": int(daily.min()) if len(daily) else 0,
            "median": float(daily.median()) if len(daily) else None,
            "mean": float(daily.mean()) if len(daily) else None,
            "max": int(daily.max()) if len(daily) else 0,
        },
    }
    return mask, stats


def build_market_scores(panel_path: Path, universe: pd.DataFrame) -> pd.DataFrame:
    raw = pd.read_parquet(panel_path, columns=PANEL_COLUMNS)
    raw["ticker"] = raw["ticker"].astype("string")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.normalize()
    for column in PANEL_COLUMNS[2:]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw["source_panel_row_present"] = True
    frame = universe.merge(raw, on=["ticker", "date"], how="left", validate="one_to_one")
    frame = frame.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    frame["source_panel_row_present"] = frame["source_panel_row_present"].eq(True)
    frame["eligible_decision_universe"] = frame["eligible_decision_universe"].fillna(False).astype(bool)
    frame["close_valid"] = frame["close"].gt(0) & np.isfinite(frame["close"])
    frame["volume_valid"] = frame["volume"].gt(0) & np.isfinite(frame["volume"])
    frame["close_for_return"] = frame["close"].where(frame["close_valid"])
    frame["ret_1"] = frame.groupby("ticker", sort=False)["close_for_return"].pct_change(fill_method=None)
    frame["ret_5"] = frame.groupby("ticker", sort=False)["close_for_return"].pct_change(periods=5, fill_method=None)
    frame["ret_20"] = frame.groupby("ticker", sort=False)["close_for_return"].pct_change(periods=20, fill_method=None)
    frame["turnover"] = (frame["close"] * frame["volume"]).where(frame["close_valid"] & frame["volume_valid"])
    frame["abs_ret_1"] = frame["ret_1"].abs()
    frame["abs_ret_sum_20"] = rolling(frame, "abs_ret_1", 20, "sum")
    frame["vol_20"] = rolling(frame, "ret_1", 20, "std")
    frame["turnover_mean_5"] = rolling(frame, "turnover", 5, "mean")
    frame["turnover_median_60"] = rolling(frame, "turnover", WINDOW, "median")

    eligible_returns = frame.loc[
        frame["source_panel_row_present"] & frame["eligible_decision_universe"] & np.isfinite(frame["ret_1"]),
        ["date", "ret_1"],
    ]
    official_dates = pd.Index(sorted(universe["date"].unique()), name="date")
    market_ret = eligible_returns.groupby("date", sort=True)["ret_1"].mean().reindex(official_dates)
    market_ret_5 = (1.0 + market_ret).rolling(window=5, min_periods=5).apply(np.prod, raw=True).sub(1.0)
    frame["market_ret"] = frame["date"].map(market_ret)
    frame["market_ret_5"] = frame["date"].map(market_ret_5)
    frame["stock_ret_lag1"] = frame.groupby("ticker", sort=False)["ret_1"].shift(1)
    frame["market_ret_lag1"] = frame.groupby("ticker", sort=False)["market_ret"].shift(1)
    valid_pair = np.isfinite(frame["stock_ret_lag1"]) & np.isfinite(frame["market_ret_lag1"])
    frame["beta_x"] = frame["stock_ret_lag1"].where(valid_pair)
    frame["beta_y"] = frame["market_ret_lag1"].where(valid_pair)
    frame["beta_xy"] = frame["beta_x"] * frame["beta_y"]
    frame["beta_yy"] = frame["beta_y"] ** 2
    n = rolling(frame, "beta_x", WINDOW, "count")
    sx = rolling(frame, "beta_x", WINDOW, "sum")
    sy = rolling(frame, "beta_y", WINDOW, "sum")
    sxy = rolling(frame, "beta_xy", WINDOW, "sum")
    syy = rolling(frame, "beta_yy", WINDOW, "sum")
    covariance = sxy - sx * sy / n
    variance = syy - sy * sy / n
    frame["beta_60_prior"] = covariance / variance.replace(0.0, np.nan)
    frame[CANDIDATES["C1"]] = -(
        frame["ret_5"] - frame["beta_60_prior"] * frame["market_ret_5"]
    ) / frame["vol_20"].replace(0.0, np.nan)
    abnormal_turnover = frame["turnover_mean_5"] / frame["turnover_median_60"].replace(0.0, np.nan)
    frame[CANDIDATES["C2"]] = frame["ret_5"] * np.log(abnormal_turnover)
    frame[CANDIDATES["C4"]] = -frame["ret_20"] / frame["abs_ret_sum_20"].replace(0.0, np.nan)
    for candidate in ("C1", "C2", "C4"):
        frame.loc[~frame["eligible_decision_universe"], CANDIDATES[candidate]] = np.nan
    return frame.loc[frame["source_panel_row_present"], ["ticker", "date", "regular_market_value", "volume", "turnover", "eligible_decision_universe", CANDIDATES["C1"], CANDIDATES["C2"], CANDIDATES["C4"]]].copy()


def build_c3_score(financial_path: Path, universe: pd.DataFrame) -> pd.DataFrame:
    financial = pd.read_parquet(financial_path, columns=FINANCIAL_COLUMNS)
    financial["ticker"] = financial["ticker"].astype("string")
    financial["date"] = pd.to_datetime(financial["date"], errors="raise").dt.normalize()
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
    period_ok = period_date.notna() & period_date.le(financial["date"])
    provenance_ok = (
        financial["selected_bundle_provenance_complete"].fillna(False).astype(bool)
        & financial["bundle_reporting_version_id"].notna()
        & financial["bundle_reporting_attachment_sha256"].notna()
        & financial["bundle_reporting_attachment_sha256"].astype("string").str.len().ge(16)
    )
    financial = financial.merge(universe[["ticker", "date", "eligible_decision_universe"]], on=["ticker", "date"], how="left", validate="one_to_one")
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
    financial["C3_financial_quality_growth_v1"] = np.nan
    components = ["financial_leverage_positive", *values[1:]]
    financial["financial_leverage_positive"] = -financial[values[0]]
    for column in components:
        financial[f"rank_{column}"] = np.nan
        financial.loc[valid, f"rank_{column}"] = financial.loc[valid].groupby("date", sort=False)[column].rank(method="average", pct=True)
    rank_columns = [f"rank_{column}" for column in components]
    financial.loc[valid, "C3_financial_quality_growth_v1"] = financial.loc[valid, rank_columns].mean(axis=1)
    return financial[["ticker", "date", "C3_financial_quality_growth_v1"]]


def add_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for candidate, column in CANDIDATES.items():
        score = pd.to_numeric(output[column], errors="coerce")
        valid = output["eligible_decision_universe"] & score.notna() & np.isfinite(score)
        output[f"rank_{candidate}"] = np.nan
        output.loc[valid, f"rank_{candidate}"] = output.loc[valid].groupby("date")[column].rank(method="average", pct=True)
    return output


def top_k_summary(
    frame: pd.DataFrame,
    candidate: str,
    official_dates: pd.Index,
    *,
    frozen_only: bool,
) -> dict[str, object]:
    rank = f"rank_{candidate}"
    work = frame.loc[frame["eligible_decision_universe"] & frame[rank].notna(), ["ticker", "date", rank]].copy()
    if frozen_only:
        scope_dates = set(official_dates[-FROZEN_SESSION_COUNT:])
        work = work[work["date"].isin(scope_dates)]
    counts = work.groupby("date").size()
    valid_dates = counts[counts >= TOP_K].index
    work = work[work["date"].isin(valid_dates)].sort_values(["date", rank, "ticker"], ascending=[True, False, True], kind="mergesort")
    selected = work.groupby("date", sort=False, group_keys=False).head(TOP_K)
    sets = {date: set(group["ticker"]) for date, group in selected.groupby("date", sort=True)}
    dates = [date for date in official_dates if date in sets]
    official_index = {date: index for index, date in enumerate(official_dates)}
    overlaps: list[float] = []
    turnovers: list[float] = []
    for current in dates:
        current_index = official_index[current]
        if current_index == 0:
            continue
        previous = official_dates[current_index - 1]
        if previous not in sets:
            continue
        overlap = len(sets[previous] & sets[current]) / TOP_K
        overlaps.append(overlap)
        turnovers.append(1.0 - overlap)
    return {
        "finite_rows": int(len(work)),
        "finite_dates": int(work["date"].nunique()),
        "finite_tickers": int(work["ticker"].nunique()),
        "top_k": TOP_K,
        "selection_dates": len(dates),
        "selection_slots": int(len(selected)),
        "mean_top_k_overlap": float(np.mean(overlaps)) if overlaps else None,
        "mean_top_k_turnover": float(np.mean(turnovers)) if turnovers else None,
        "top_k_dates_with_at_least_k": int(len(valid_dates)),
        "scope": "last_600_official_sessions" if frozen_only else "all_official_sessions",
    }


def scenario_candidate_stats(frame: pd.DataFrame, official_dates: pd.Index) -> dict[str, object]:
    eligible_rows = int(frame["eligible_decision_universe"].sum())
    result: dict[str, object] = {}
    for candidate, column in CANDIDATES.items():
        finite = frame["eligible_decision_universe"] & pd.to_numeric(frame[column], errors="coerce").notna()
        daily = finite.groupby(frame["date"]).sum()
        result[candidate] = {
            "finite_rows": int(finite.sum()),
            "finite_tickers": int(frame.loc[finite, "ticker"].nunique()),
            "finite_dates": int(frame.loc[finite, "date"].nunique()),
            "coverage_of_eligible_rows": float(finite.sum() / eligible_rows) if eligible_rows else None,
            "rank_denominator": {
                "min": int(daily.min()) if len(daily) else 0,
                "median": float(daily.median()) if len(daily) else None,
                "mean": float(daily.mean()) if len(daily) else None,
                "max": int(daily.max()) if len(daily) else 0,
            },
            "top_k": top_k_summary(frame, candidate, official_dates, frozen_only=True),
            "top_k_all_official": top_k_summary(frame, candidate, official_dates, frozen_only=False),
        }
    return result


def compare_scenarios(left: pd.DataFrame, right: pd.DataFrame) -> dict[str, object]:
    result: dict[str, object] = {}
    keys = ["ticker", "date"]
    for candidate, column in CANDIDATES.items():
        rank = f"rank_{candidate}"
        merged = left[keys + [column, rank]].merge(right[keys + [column, rank]], on=keys, how="inner", suffixes=("_20", "_60"))
        both = merged[[f"{column}_20", f"{column}_60", f"{rank}_20", f"{rank}_60"]].notna().all(axis=1)
        rank_delta = (merged.loc[both, f"{rank}_20"] - merged.loc[both, f"{rank}_60"]).abs()
        score_delta = (merged.loc[both, f"{column}_20"] - merged.loc[both, f"{column}_60"]).abs()
        result[candidate] = {
            "common_finite_rows": int(both.sum()),
            "rows_with_rank_change": int((rank_delta > 1e-12).sum()),
            "rank_change_fraction": float((rank_delta > 1e-12).mean()) if len(rank_delta) else None,
            "mean_abs_rank_delta": float(rank_delta.mean()) if len(rank_delta) else None,
            "max_abs_rank_delta": float(rank_delta.max()) if len(rank_delta) else None,
            "mean_abs_score_delta": float(score_delta.mean()) if len(score_delta) else None,
        }
    return result


def run(args: argparse.Namespace) -> dict[str, object]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    for path in (args.panel, args.financial, args.sessions, args.anchors):
        if any(marker in str(path).lower() for marker in FORBIDDEN_INPUT_MARKERS):
            raise ValueError(f"refusing input path with protected-data marker: {path}")

    panel = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel has duplicate ticker/date keys")
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    official_dates = pd.Index(sorted(sessions["date"].drop_duplicates()), name="date")
    anchors = pd.read_csv(args.anchors)
    scenarios: dict[int, dict[str, object]] = {}
    frames: dict[int, pd.DataFrame] = {}
    for minimum in POLICIES:
        universe, universe_stats = build_universe(panel, sessions, anchors, minimum)
        market = build_market_scores(args.panel, universe)
        financial = build_c3_score(args.financial, universe)
        frame = market.merge(financial, on=["ticker", "date"], how="left", validate="one_to_one")
        frame = add_ranks(frame)
        frames[minimum] = frame
        scenarios[minimum] = {
            "policy": {
                "window": WINDOW,
                "minimum_finite_observations": minimum,
                "count_min_periods": minimum,
                "median_min_periods": minimum,
                "policy_sha256": policy_sha(minimum),
            },
            "universe": universe_stats,
            "candidates": scenario_candidate_stats(frame, official_dates),
        }

    mask20 = frames[20].set_index(["ticker", "date"])["eligible_decision_universe"]
    mask60 = frames[60].set_index(["ticker", "date"])["eligible_decision_universe"]
    newly20 = mask20 & ~mask60
    scenarios[20]["versus_60"] = {
        "newly_admitted_rows": int(newly20.sum()),
        "newly_admitted_tickers": int(newly20[newly20].index.get_level_values("ticker").nunique()),
        "newly_admitted_dates": int(newly20[newly20].index.get_level_values("date").nunique()),
        "new_listing_count": None,
        "delisted_security_count": None,
        "listing_age_distribution": "UNAVAILABLE_NO_LISTING_DATE_AUTHORITY",
        "sector_composition": "UNAVAILABLE_NO_PIT_SAFE_SECTOR_AUTHORITY",
        "note": "Newly admitted means mask difference only; it is not inferred to be newly listed or delisted.",
        "rank_and_score_effects": compare_scenarios(frames[20], frames[60]),
    }
    result = {
        "status": "PASS_STRUCTURAL_SCENARIO_ONLY",
        "scope": "outcome-blind counterfactual eligibility impact; no policy selected",
        "input": {
            "panel": {"path": str(args.panel), "sha256": sha256_file(args.panel), "rows": int(len(panel))},
            "financial": {"path": str(args.financial), "sha256": sha256_file(args.financial)},
            "official_sessions": {"path": str(args.sessions), "sha256": sha256_file(args.sessions)},
            "tradability_anchors": {"path": str(args.anchors), "sha256": sha256_file(args.anchors)},
        },
        "scenarios": {str(minimum): scenarios[minimum] for minimum in POLICIES},
        "h_families": {
            "status": "DEFERRED_POLICY_CONFLICT",
            "families": ["H-LIQ", "H-VOL", "H-EXC"],
            "reason": "Their fixed structural artifacts consume the same eligibility mask and cross-sectional ranks; exact family replays must follow an authoritative policy decision and must not silently mix masks.",
        },
        "limitations": [
            "This is not predictive evaluation and contains no forward outcomes, IC, Rank-IC, PnL, or protected arrays.",
            "The 20-policy branch is a counterfactual scenario, not an admitted population.",
            "No listing-age, delisting-completeness, ticker-reuse, or PIT sector authority is present in the supplied inputs.",
        ],
        "policy_decision": "BLOCKED_POLICY_CONFLICT",
        "code_sha256": sha256_file(Path(__file__).resolve()),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--financial", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
