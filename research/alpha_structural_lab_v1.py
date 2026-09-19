"""Outcome-blind structural lab for the frozen C1-C4 candidate ranks.

This intentionally does not read targets, forward returns, incumbent scores,
or provider data. It extends the existing Top-30 economics audit with fixed
Top-10/20/30/50 portfolio mechanics, persistence, rank churn, liquidity
exposure, market-state conditioning, and target-free pairwise orthogonality.
It is a structural research artifact, not alpha evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


CANDIDATES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C3_financial_quality_growth_v1",
    "C4_path_efficiency_reversal_20_v1",
]
TOP_KS = [10, 20, 30, 50]
FROZEN_SESSION_COUNT = 600
MIN_CORRELATION_CROSS_SECTION = 20


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


def quantile_summary(series: pd.Series) -> dict[str, float | int | None]:
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return {"count": 0, "min": None, "q01": None, "q05": None, "q25": None, "median": None, "q75": None, "q95": None, "q99": None, "max": None, "mean": None, "std": None, "skew": None, "kurtosis": None}
    return {
        "count": int(len(values)),
        "min": finite_float(values.min()),
        "q01": finite_float(values.quantile(0.01)),
        "q05": finite_float(values.quantile(0.05)),
        "q25": finite_float(values.quantile(0.25)),
        "median": finite_float(values.median()),
        "q75": finite_float(values.quantile(0.75)),
        "q95": finite_float(values.quantile(0.95)),
        "q99": finite_float(values.quantile(0.99)),
        "max": finite_float(values.max()),
        "mean": finite_float(values.mean()),
        "std": finite_float(values.std(ddof=1)),
        "skew": finite_float(values.skew()),
        "kurtosis": finite_float(values.kurt()),
    }


def series_summary(series: Iterable[float]) -> dict[str, float | int | None]:
    return quantile_summary(pd.Series(list(series), dtype="float64"))


def summarize_daily_state(frame: pd.DataFrame, metric: str) -> dict[str, dict[str, float | int | None]]:
    result: dict[str, dict[str, float | int | None]] = {}
    for state, group in frame.groupby(metric, dropna=False, sort=True):
        key = "UNKNOWN" if pd.isna(state) else str(state)
        result[key] = quantile_summary(group["turnover"])
    return result


def build_market_states(frame: pd.DataFrame, session_index: dict[pd.Timestamp, int]) -> pd.DataFrame:
    eligible = frame[frame["eligible_decision_universe"] & frame["close"].notna()].copy()
    eligible["abs_return"] = eligible["daily_return"].abs()
    daily = eligible.groupby("date", sort=True).agg(
        market_median_return=("daily_return", "median"),
        market_return_dispersion=("daily_return", "std"),
        market_median_abs_return=("abs_return", "median"),
        market_median_value=("regular_market_value", "median"),
        market_median_volume=("volume", "median"),
        eligible_names=("ticker", "nunique"),
    ).reset_index()
    daily["session_index"] = daily["date"].map(session_index)
    daily = daily.sort_values("session_index", kind="mergesort").reset_index(drop=True)
    daily["market_trend_20"] = daily["market_median_return"].rolling(20, min_periods=20).sum()

    vol_median = daily["market_median_abs_return"].median()
    value_median = daily["market_median_value"].median()
    trend_values = daily["market_trend_20"].dropna()
    trend_low = trend_values.quantile(1 / 3) if not trend_values.empty else np.nan
    trend_high = trend_values.quantile(2 / 3) if not trend_values.empty else np.nan
    daily["volatility_state"] = np.where(
        daily["market_median_abs_return"] >= vol_median, "HIGH_VOL", "LOW_VOL"
    )
    daily["liquidity_state"] = np.where(
        daily["market_median_value"] >= value_median, "HIGH_VALUE", "LOW_VALUE"
    )
    daily["trend_state"] = np.select(
        [daily["market_trend_20"] <= trend_low, daily["market_trend_20"] >= trend_high],
        ["TREND_LOW", "TREND_HIGH"],
        default="TREND_MIXED",
    )
    daily["session_block"] = (daily["session_index"] // 100 + 1).astype("Int64")
    return daily


def distribution_metrics(frame: pd.DataFrame, candidate: str) -> dict[str, object]:
    score = frame.loc[frame["eligible_decision_universe"], candidate]
    rank = frame.loc[frame["eligible_decision_universe"], f"rank_{candidate}"]
    finite_score = score.replace([np.inf, -np.inf], np.nan).dropna()
    finite_rank = rank.replace([np.inf, -np.inf], np.nan).dropna()
    return {
        "score": quantile_summary(finite_score),
        "rank": quantile_summary(finite_rank),
        "score_finite_rows": int(len(finite_score)),
        "rank_finite_rows": int(len(finite_rank)),
    }


def coverage_metrics(frame: pd.DataFrame, candidate: str) -> dict[str, object]:
    rank_column = f"rank_{candidate}"
    eligible = frame["eligible_decision_universe"]
    finite = eligible & frame[rank_column].replace([np.inf, -np.inf], np.nan).notna()
    eligible_by_date = frame.loc[eligible].groupby("date").size()
    finite_by_date = frame.loc[finite].groupby("date").size()
    date_coverage = (finite_by_date / eligible_by_date).reindex(eligible_by_date.index).fillna(0.0)
    eligible_by_ticker = frame.loc[eligible].groupby("ticker").size()
    finite_by_ticker = frame.loc[finite].groupby("ticker").size()
    ticker_coverage = (finite_by_ticker / eligible_by_ticker).reindex(eligible_by_ticker.index).fillna(0.0)
    finite_dates = set(frame.loc[finite, "date"])
    return {
        "eligible_rows": int(eligible.sum()),
        "finite_rows": int(finite.sum()),
        "row_coverage": finite_float(finite.sum() / eligible.sum()) if eligible.sum() else None,
        "eligible_dates": int(frame.loc[eligible, "date"].nunique()),
        "finite_dates": int(frame.loc[finite, "date"].nunique()),
        "eligible_tickers": int(frame.loc[eligible, "ticker"].nunique()),
        "finite_tickers": int(frame.loc[finite, "ticker"].nunique()),
        "date_coverage_distribution": quantile_summary(date_coverage),
        "ticker_coverage_distribution": quantile_summary(ticker_coverage),
        "zero_finite_dates": int(sum(date_coverage.eq(0.0))),
        "dates_with_at_least_50pct_coverage": int(sum(date_coverage >= 0.5)),
        "finite_date_set_hash": hashlib.sha256(
            "|".join(sorted(pd.Timestamp(value).strftime("%Y-%m-%d") for value in finite_dates)).encode("utf-8")
        ).hexdigest(),
    }


def rank_displacement_metrics(frame: pd.DataFrame, candidate: str) -> dict[str, object]:
    rank_column = f"rank_{candidate}"
    selected = frame.loc[
        frame["eligible_decision_universe"] & frame[rank_column].notna(),
        ["ticker", "date", "session_index", rank_column],
    ].copy()
    current = selected.rename(columns={"session_index": "current_session", rank_column: "current_rank"})
    previous = selected.rename(columns={"session_index": "previous_session", rank_column: "previous_rank"})
    joined = current.merge(previous, on="ticker", how="inner", validate="many_to_many")
    joined = joined[joined["current_session"].eq(joined["previous_session"] + 1)]
    displacement = (joined["current_rank"] - joined["previous_rank"]).abs()
    daily = joined.assign(abs_rank_displacement=displacement).groupby("current_session")["abs_rank_displacement"].mean()
    return {
        "consecutive_name_observations": int(len(joined)),
        "daily_mean_abs_rank_displacement": quantile_summary(daily),
        "mean_abs_rank_displacement": finite_float(displacement.mean()),
    }


def rank_liquidity_relationship(frame: pd.DataFrame, candidate: str) -> dict[str, object]:
    rank_column = f"rank_{candidate}"
    rows = frame.loc[
        frame["eligible_decision_universe"] & frame[rank_column].notna(),
        ["date", rank_column, "liquidity_percentile", "volume_percentile"],
    ]
    value_correlations: list[float] = []
    volume_correlations: list[float] = []
    for _, group in rows.groupby("date", sort=True):
        value_group = group[[rank_column, "liquidity_percentile"]].dropna()
        volume_group = group[[rank_column, "volume_percentile"]].dropna()
        if len(value_group) >= MIN_CORRELATION_CROSS_SECTION:
            value_corr = value_group[rank_column].corr(value_group["liquidity_percentile"], method="spearman")
            if np.isfinite(value_corr):
                value_correlations.append(float(value_corr))
        if len(volume_group) >= MIN_CORRELATION_CROSS_SECTION:
            volume_corr = volume_group[rank_column].corr(volume_group["volume_percentile"], method="spearman")
            if np.isfinite(volume_corr):
                volume_correlations.append(float(volume_corr))
    return {
        "daily_rank_vs_market_value_percentile": quantile_summary(pd.Series(value_correlations, dtype="float64")),
        "daily_rank_vs_volume_percentile": quantile_summary(pd.Series(volume_correlations, dtype="float64")),
    }


def persistence_lengths(selection: pd.DataFrame) -> list[int]:
    lengths: list[int] = []
    for _, group in selection.groupby("ticker", sort=False):
        indices = sorted(set(int(value) for value in group["session_index"]))
        if not indices:
            continue
        start = previous = indices[0]
        for value in indices[1:]:
            if value != previous + 1:
                lengths.append(previous - start + 1)
                start = value
            previous = value
        lengths.append(previous - start + 1)
    return lengths


def concentration_metrics(selection: pd.DataFrame) -> dict[str, object]:
    if selection.empty:
        return {"selection_slots": 0, "unique_tickers": 0, "top10_slot_share": None, "largest_ticker_slot_share": None, "hhi": None, "effective_number_of_names": None}
    counts = selection["ticker"].astype(str).value_counts()
    shares = counts / len(selection)
    hhi = float((shares * shares).sum())
    return {
        "selection_slots": int(len(selection)),
        "unique_tickers": int(counts.size),
        "top10_slot_share": finite_float(counts.head(10).sum() / len(selection)),
        "largest_ticker_slot_share": finite_float(counts.iloc[0] / len(selection)),
        "hhi": finite_float(hhi),
        "effective_number_of_names": finite_float(1.0 / hhi) if hhi > 0 else None,
    }


def liquidity_metrics(selection: pd.DataFrame) -> dict[str, object]:
    if selection.empty:
        return {"market_value": quantile_summary(pd.Series(dtype="float64")), "volume": quantile_summary(pd.Series(dtype="float64")), "liquidity_percentile": quantile_summary(pd.Series(dtype="float64")), "below_liquidity_q25_share": None, "positive_value_coverage": None}
    value = pd.to_numeric(selection["regular_market_value"], errors="coerce")
    volume = pd.to_numeric(selection["volume"], errors="coerce")
    liquidity_pct = pd.to_numeric(selection["liquidity_percentile"], errors="coerce")
    return {
        "market_value": quantile_summary(value[value > 0]),
        "volume": quantile_summary(volume[volume > 0]),
        "liquidity_percentile": quantile_summary(liquidity_pct),
        "below_liquidity_q25_share": finite_float((liquidity_pct <= 0.25).mean()),
        "positive_value_coverage": finite_float((value > 0).mean()),
    }


def selection_sets(selection: pd.DataFrame) -> dict[pd.Timestamp, set[str]]:
    return {pd.Timestamp(date): set(group["ticker"].astype(str)) for date, group in selection.groupby("date", sort=True)}


def top_k_metrics(
    frame: pd.DataFrame,
    candidate: str,
    k: int,
    sessions: pd.DataFrame,
    market_states: pd.DataFrame,
) -> tuple[dict[str, object], dict[pd.Timestamp, set[str]]]:
    rank_column = f"rank_{candidate}"
    candidate_frame = frame.loc[
        frame["eligible_decision_universe"] & frame[rank_column].notna(),
        ["ticker", "date", "session_index", rank_column, "regular_market_value", "volume", "liquidity_percentile"],
    ].copy()
    counts = candidate_frame.groupby("date").size()
    valid_dates = set(counts[counts >= k].index)
    ordered = candidate_frame[candidate_frame["date"].isin(valid_dates)].sort_values(
        ["date", rank_column, "ticker"], ascending=[True, False, True], kind="mergesort"
    )
    selection = ordered.groupby("date", sort=False, group_keys=False).head(k).copy()
    selection_sets_by_date = selection_sets(selection)
    session_dates = [pd.Timestamp(value) for value in sessions["date"]]
    session_index = dict(zip(session_dates, sessions.index, strict=True))
    turnovers: list[float] = []
    overlaps: list[int] = []
    entries: list[int] = []
    exits: list[int] = []
    daily_rows: list[dict[str, object]] = []
    for current_date in sorted(selection_sets_by_date):
        current_index = session_index[current_date]
        previous_date = session_dates[current_index - 1] if current_index > 0 else None
        if previous_date is None or previous_date not in selection_sets_by_date:
            continue
        current_set = selection_sets_by_date[current_date]
        previous_set = selection_sets_by_date[previous_date]
        overlap = len(current_set & previous_set)
        turnover = 1.0 - overlap / k
        turnovers.append(turnover)
        overlaps.append(overlap)
        entries.append(k - overlap)
        exits.append(k - overlap)
        daily_rows.append(
            {
                "date": current_date,
                "session_index": current_index,
                "turnover": turnover,
                "overlap": overlap,
                "entry_count": k - overlap,
                "exit_count": k - overlap,
            }
        )
    daily = pd.DataFrame(daily_rows)
    if not daily.empty:
        daily = daily.merge(market_states, on=["date", "session_index"], how="left", validate="one_to_one")
    lengths = persistence_lengths(selection)
    selected_value = pd.to_numeric(selection["regular_market_value"], errors="coerce")
    selection_rank = pd.to_numeric(selection[rank_column], errors="coerce")
    rank_churn = pd.Series(selection_rank.groupby(selection["date"]).mean(), dtype="float64")
    metrics: dict[str, object] = {
        "top_k": k,
        "candidate_finite_dates": int(len(valid_dates)),
        "selection_dates": int(len(selection_sets_by_date)),
        "selection_slots": int(len(selection)),
        "turnover_observations": int(len(turnovers)),
        "turnover": quantile_summary(pd.Series(turnovers, dtype="float64")),
        "overlap_count": quantile_summary(pd.Series(overlaps, dtype="float64")),
        "entry_count": quantile_summary(pd.Series(entries, dtype="float64")),
        "exit_count": quantile_summary(pd.Series(exits, dtype="float64")),
        "persistence_sessions": quantile_summary(pd.Series(lengths, dtype="float64")),
        "concentration": concentration_metrics(selection),
        "liquidity": liquidity_metrics(selection),
        "selected_rank_distribution": quantile_summary(selection_rank),
        "selected_value_positive_coverage": finite_float((selected_value > 0).mean()) if len(selection) else None,
        "by_session_block": {},
        "by_market_state": {
            "volatility_state": summarize_daily_state(daily, "volatility_state") if not daily.empty else {},
            "liquidity_state": summarize_daily_state(daily, "liquidity_state") if not daily.empty else {},
            "trend_state": summarize_daily_state(daily, "trend_state") if not daily.empty else {},
        },
    }
    if not daily.empty:
        block_result: dict[str, object] = {}
        for block, group in daily.groupby("session_block", sort=True):
            block_result[str(int(block))] = {
                "session_count": int(group["session_index"].nunique()),
                "turnover": quantile_summary(group["turnover"]),
                "mean_overlap": finite_float(group["overlap"].mean()),
            }
        metrics["by_session_block"] = block_result
    return metrics, selection_sets_by_date


def pairwise_orthogonality(
    frame: pd.DataFrame,
    candidate: str,
    other: str,
    selections: dict[str, dict[int, dict[pd.Timestamp, set[str]]]],
    sessions: pd.DataFrame,
) -> dict[str, object]:
    left = frame.loc[
        frame["eligible_decision_universe"] & frame[f"rank_{candidate}"].notna(),
        ["ticker", "date", f"rank_{candidate}"],
    ].rename(columns={f"rank_{candidate}": "left_rank"})
    right = frame.loc[
        frame["eligible_decision_universe"] & frame[f"rank_{other}"].notna(),
        ["ticker", "date", f"rank_{other}"],
    ].rename(columns={f"rank_{other}": "right_rank"})
    common = left.merge(right, on=["ticker", "date"], how="inner", validate="one_to_one")
    daily_corr: list[dict[str, object]] = []
    for date, group in common.groupby("date", sort=True):
        if len(group) < MIN_CORRELATION_CROSS_SECTION:
            continue
        corr = group["left_rank"].corr(group["right_rank"], method="spearman")
        if np.isfinite(corr):
            daily_corr.append({"date": pd.Timestamp(date), "session_index": int(group["date"].map(dict(zip(sessions["date"], sessions.index, strict=True))).iloc[0]), "correlation": float(corr)})
    corr_frame = pd.DataFrame(daily_corr)
    corr_values = corr_frame["correlation"] if not corr_frame.empty else pd.Series(dtype="float64")
    corr_result: dict[str, object] = {
        "common_rows": int(len(common)),
        "daily_correlation_observations": int(len(corr_values)),
        "daily_spearman": quantile_summary(corr_values),
        "rolling_correlation": {},
        "by_session_block": {},
    }
    if not corr_frame.empty:
        corr_series = corr_frame.sort_values("session_index").set_index("session_index")["correlation"]
        for window in (20, 60):
            rolling = corr_series.rolling(window, min_periods=max(10, window // 2)).mean().dropna()
            corr_result["rolling_correlation"][str(window)] = quantile_summary(rolling)
        for block, group in corr_frame.assign(session_block=corr_frame["session_index"] // 100 + 1).groupby("session_block", sort=True):
            corr_result["by_session_block"][str(int(block))] = quantile_summary(group["correlation"])

    overlap_result: dict[str, object] = {}
    for k in TOP_KS:
        left_sets = selections[candidate].get(k, {})
        right_sets = selections[other].get(k, {})
        overlaps: list[float] = []
        jaccards: list[float] = []
        for date in sorted(set(left_sets) & set(right_sets)):
            left_set = left_sets[date]
            right_set = right_sets[date]
            intersection = len(left_set & right_set)
            union = len(left_set | right_set)
            overlaps.append(intersection / k)
            jaccards.append(intersection / union if union else 0.0)
        overlap_result[str(k)] = {
            "common_selection_dates": int(len(overlaps)),
            "overlap_fraction": quantile_summary(pd.Series(overlaps, dtype="float64")),
            "jaccard": quantile_summary(pd.Series(jaccards, dtype="float64")),
        }
    corr_result["top_k_overlap"] = overlap_result
    return corr_result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    feature_columns = [
        "ticker",
        "date",
        "eligible_decision_universe",
        *CANDIDATES,
        *(f"rank_{candidate}" for candidate in CANDIDATES),
    ]
    features = pd.read_parquet(args.features, columns=feature_columns)
    panel = pd.read_parquet(
        args.panel,
        columns=["ticker", "date", "high", "low", "close", "volume", "regular_market_value"],
    )
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    for frame in (features, panel):
        frame["ticker"] = frame["ticker"].astype("string")
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.drop_duplicates("date").sort_values("date", kind="mergesort").reset_index(drop=True)
    if len(sessions) < FROZEN_SESSION_COUNT:
        raise ValueError("official session source is shorter than frozen window")
    frozen_sessions = sessions.tail(FROZEN_SESSION_COUNT).copy().reset_index(drop=True)
    frozen_dates = set(frozen_sessions["date"])
    session_index = dict(zip(frozen_sessions["date"], frozen_sessions.index, strict=True))

    if features.duplicated(["ticker", "date"]).any():
        raise ValueError("features contain duplicate ticker/date keys")
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel contains duplicate ticker/date keys")

    panel = panel.sort_values(["ticker", "date"], kind="mergesort").copy()
    panel["close"] = pd.to_numeric(panel["close"], errors="coerce")
    panel["daily_return"] = panel.groupby("ticker", sort=False)["close"].pct_change()
    panel = panel[panel["date"].isin(frozen_dates)].copy()
    features = features[features["date"].isin(frozen_dates)].copy()
    merged = features.merge(panel, on=["ticker", "date"], how="left", validate="one_to_one", indicator=True)
    if not merged["_merge"].eq("both").all():
        raise ValueError("feature/panel key closure failed")
    merged = merged.drop(columns=["_merge"])
    merged["session_index"] = merged["date"].map(session_index)
    merged["eligible_decision_universe"] = merged["eligible_decision_universe"].astype(bool)
    eligible = merged["eligible_decision_universe"]
    merged["liquidity_percentile"] = np.nan
    merged["volume_percentile"] = np.nan
    eligible_rows = merged.loc[eligible].copy()
    merged.loc[eligible_rows.index, "liquidity_percentile"] = eligible_rows.groupby("date")["regular_market_value"].rank(pct=True, method="average")
    merged.loc[eligible_rows.index, "volume_percentile"] = eligible_rows.groupby("date")["volume"].rank(pct=True, method="average")
    market_states = build_market_states(merged, session_index)

    candidate_metrics: dict[str, object] = {}
    selections: dict[str, dict[int, dict[pd.Timestamp, set[str]]]] = {}
    for candidate in CANDIDATES:
        candidate_metrics[candidate] = {
            "coverage": coverage_metrics(merged, candidate),
            "distribution": distribution_metrics(merged, candidate),
            "rank_displacement": rank_displacement_metrics(merged, candidate),
            "rank_liquidity_relationship": rank_liquidity_relationship(merged, candidate),
            "top_k": {},
        }
        selections[candidate] = {}
        for k in TOP_KS:
            metrics, sets = top_k_metrics(merged, candidate, k, frozen_sessions, market_states)
            candidate_metrics[candidate]["top_k"][str(k)] = metrics
            selections[candidate][k] = sets

    pairwise: dict[str, object] = {}
    for left, right in itertools.combinations(CANDIDATES, 2):
        pairwise[f"{left}__{right}"] = pairwise_orthogonality(merged, left, right, selections, frozen_sessions)

    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "C_F_G_K_L_M_OUTCOME_BLIND_STRUCTURAL_LAB",
        "protocol": "2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1",
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "incumbent_score_accessed": False,
        "candidate_ids": CANDIDATES,
        "top_k_values": TOP_KS,
        "frozen_session_count": FROZEN_SESSION_COUNT,
        "frozen_window_start": frozen_sessions["date"].min().strftime("%Y-%m-%d"),
        "frozen_window_end": frozen_sessions["date"].max().strftime("%Y-%m-%d"),
        "state_definitions": {
            "volatility_state": "HIGH/LOW by frozen-window median of daily cross-sectional median absolute close-to-close return",
            "liquidity_state": "HIGH/LOW by frozen-window median of daily cross-sectional median regular_market_value",
            "trend_state": "LOW/MIXED/HIGH by tertiles of 20-session rolling sum of daily cross-sectional median close-to-close return",
            "liquidity_percentile": "same-day cross-sectional percentile of regular_market_value within eligible names",
        },
        "unavailable_dimensions": [
            "sector_or_industry_history_not_present_in_frozen_panel",
            "listing_delisting_authority_not_present_in_frozen_panel",
            "historical_spread_or_queue_data_not_present_in_frozen_panel",
        ],
        "source_classification": "PARTIAL_FROZEN_ONLY_CAPABILITY_DIAGNOSTIC",
        "source_hashes": {
            "features": sha256_file(args.features),
            "panel": sha256_file(args.panel),
            "official_sessions": sha256_file(args.sessions),
        },
        "code_sha256": sha256_file(Path(__file__)),
        "candidate_metrics": candidate_metrics,
        "pairwise_orthogonality": pairwise,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
