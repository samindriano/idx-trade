from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd

from .research_stage5 import assign_within_date_buckets, bucket_summary, ranking_metrics
from .research_v2_models import (
    HGB_XS,
    HGB_XS_MARKET,
    LOGISTIC_XS,
    PAIRWISE_LOGISTIC_XS,
    V1_HGB_CONTROL,
    V2_CANDIDATES,
)


V2_PRAUC_TIE_TOLERANCE = 0.002
V2_COMPLEXITY_ORDER = {
    LOGISTIC_XS: 0,
    PAIRWISE_LOGISTIC_XS: 1,
    HGB_XS: 2,
    HGB_XS_MARKET: 3,
}


@dataclass(frozen=True)
class RankingV2Fold:
    name: str
    train_start: int
    train_end: int
    gap_start: int
    gap_end: int
    validation_start: int
    validation_end: int


RANKING_V2_FOLDS = (
    RankingV2Fold("V2F1", 1, 504, 505, 524, 525, 624),
    RankingV2Fold("V2F2", 1, 624, 625, 644, 645, 744),
    RankingV2Fold("V2F3", 1, 744, 745, 764, 765, 864),
    RankingV2Fold("V2F4", 1, 864, 865, 884, 885, 984),
    RankingV2Fold("V2F5", 1, 984, 985, 1004, 1005, 1104),
    RankingV2Fold("V2F6", 1, 1104, 1105, 1124, 1125, 1224),
)


def assert_ranking_v2_fold_contract() -> None:
    previous_validation_end = 0
    for fold in RANKING_V2_FOLDS:
        if fold.train_start != 1:
            raise AssertionError(f"{fold.name} must use expanding training from session 1")
        if fold.gap_start != fold.train_end + 1:
            raise AssertionError(f"{fold.name} train/gap boundary is not contiguous")
        if fold.gap_end - fold.gap_start + 1 != 20:
            raise AssertionError(f"{fold.name} gap is not exactly 20 sessions")
        if fold.validation_start != fold.gap_end + 1:
            raise AssertionError(f"{fold.name} gap/validation boundary is not contiguous")
        if fold.validation_end - fold.validation_start + 1 != 100:
            raise AssertionError(f"{fold.name} validation is not exactly 100 sessions")
        if fold.train_end + 20 >= fold.validation_start:
            raise AssertionError(f"{fold.name} H20 maturity path can overlap validation")
        if previous_validation_end and fold.validation_start <= previous_validation_end:
            raise AssertionError("Ranking V2 validation windows overlap")
        previous_validation_end = fold.validation_end


def fold_by_name(name: str) -> RankingV2Fold:
    for fold in RANKING_V2_FOLDS:
        if fold.name == name:
            return fold
    raise ValueError(f"unknown Ranking V2 fold: {name}")


def split_v2_model_table(table: pd.DataFrame, fold: RankingV2Fold) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"signal_session_index", "binary_target", "date", "ticker"}
    if not required.issubset(table.columns):
        raise ValueError(f"Ranking V2 table missing {sorted(required - set(table.columns))}")
    assert_ranking_v2_fold_contract()
    data = table.copy()
    data["signal_session_index"] = pd.to_numeric(data["signal_session_index"], errors="raise").astype(int)
    train = data[data["signal_session_index"].between(fold.train_start, fold.train_end)].copy()
    validation = data[data["signal_session_index"].between(fold.validation_start, fold.validation_end)].copy()
    if train.empty or validation.empty:
        raise ValueError(f"{fold.name} has empty train or validation rows")
    if np.unique(train["binary_target"].astype(int)).size != 2:
        raise ValueError(f"{fold.name} training rows require both classes")
    if np.unique(validation["binary_target"].astype(int)).size != 2:
        raise ValueError(f"{fold.name} validation rows require both classes")
    return train, validation


def evaluate_v2_scores(validation: pd.DataFrame, score: np.ndarray) -> dict[str, float]:
    if len(validation) != len(score):
        raise ValueError("Ranking V2 score length mismatch")
    scored = validation[["ticker", "date", "binary_target"]].copy()
    scored["score"] = np.asarray(score, dtype=float)
    metrics = ranking_metrics(scored["binary_target"].astype(int), scored["score"])

    quintiled = assign_within_date_buckets(scored, score_column="score", buckets=5, output_column="quintile")
    q = bucket_summary(quintiled, bucket_column="quintile").set_index("bucket")
    deciled = assign_within_date_buckets(scored, score_column="score", buckets=10, output_column="decile")
    d = bucket_summary(deciled, bucket_column="decile").set_index("bucket")

    return {
        **metrics,
        "pr_auc_delta_vs_base": float(metrics["pr_auc"] - metrics["positive_rate"]),
        "q1_tp_rate": float(q.loc[1, "tp_rate"]),
        "q5_tp_rate": float(q.loc[5, "tp_rate"]),
        "q5_minus_q1": float(q.loc[5, "tp_rate"] - q.loc[1, "tp_rate"]),
        "top_decile_tp_rate": float(d.loc[10, "tp_rate"]),
        "top_decile_lift": float(d.loc[10, "tp_rate"] - metrics["positive_rate"]),
    }


def candidate_aggregate(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    required = {"candidate", "fold", "pr_auc_delta_vs_base", "roc_auc", "q5_minus_q1"}
    if not required.issubset(fold_metrics.columns):
        raise ValueError(f"candidate metrics missing {sorted(required - set(fold_metrics.columns))}")
    rows: list[dict[str, object]] = []
    for candidate, block in fold_metrics.groupby("candidate", sort=True):
        if len(block) != len(RANKING_V2_FOLDS):
            raise ValueError(f"{candidate} must have exactly {len(RANKING_V2_FOLDS)} fold rows")
        pr = pd.to_numeric(block["pr_auc_delta_vs_base"], errors="coerce").to_numpy(dtype=float)
        roc = pd.to_numeric(block["roc_auc"], errors="coerce").to_numpy(dtype=float)
        spread = pd.to_numeric(block["q5_minus_q1"], errors="coerce").to_numpy(dtype=float)
        finite = bool(np.isfinite(pr).all() and np.isfinite(roc).all() and np.isfinite(spread).all())
        rows.append(
            {
                "candidate": candidate,
                "all_metrics_finite": finite,
                "median_pr_auc_delta": float(np.median(pr)) if finite else np.nan,
                "q25_pr_auc_delta": float(np.quantile(pr, 0.25)) if finite else np.nan,
                "worst_pr_auc_delta": float(np.min(pr)) if finite else np.nan,
                "positive_pr_delta_folds": int(np.sum(pr > 0.0)) if finite else 0,
                "median_roc_auc": float(np.median(roc)) if finite else np.nan,
                "roc_gt_half_folds": int(np.sum(roc > 0.5)) if finite else 0,
                "median_q5_minus_q1": float(np.median(spread)) if finite else np.nan,
                "positive_q5_minus_q1_folds": int(np.sum(spread > 0.0)) if finite else 0,
            }
        )
    result = pd.DataFrame(rows)
    result["eligible"] = (
        result["all_metrics_finite"].astype(bool)
        & result["candidate"].isin(V2_CANDIDATES)
        & result["median_pr_auc_delta"].gt(0.0)
        & result["positive_pr_delta_folds"].ge(4)
        & result["median_roc_auc"].gt(0.5)
        & result["roc_gt_half_folds"].ge(4)
        & result["positive_q5_minus_q1_folds"].ge(4)
    )
    return result.sort_values("candidate").reset_index(drop=True)


def select_v2_champion(fold_metrics: pd.DataFrame) -> tuple[str, str | None, pd.DataFrame]:
    """Apply the frozen robustness-first historical-development selection rule."""

    aggregate = candidate_aggregate(fold_metrics)
    eligible = aggregate[aggregate["eligible"].astype(bool)].copy()
    if eligible.empty:
        return "RANKING_V2_NO_CHAMPION", None, aggregate

    best_median = float(eligible["median_pr_auc_delta"].max())
    shortlist = eligible[
        eligible["median_pr_auc_delta"] >= best_median - V2_PRAUC_TIE_TOLERANCE
    ].copy()

    best_q25 = float(shortlist["q25_pr_auc_delta"].max())
    shortlist = shortlist[
        shortlist["q25_pr_auc_delta"] >= best_q25 - V2_PRAUC_TIE_TOLERANCE
    ].copy()

    best_spread = float(shortlist["median_q5_minus_q1"].max())
    finalists = shortlist[np.isclose(shortlist["median_q5_minus_q1"], best_spread, rtol=0.0, atol=1e-12)].copy()
    if len(finalists) > 1:
        finalists["complexity_order"] = finalists["candidate"].map(V2_COMPLEXITY_ORDER)
        finalists = finalists.sort_values(["complexity_order", "candidate"])
    champion = str(finalists.iloc[0]["candidate"])
    return "RANKING_V2_HISTORICAL_CHAMPION_SELECTED", champion, aggregate


def comparison_to_control(aggregate: pd.DataFrame) -> pd.DataFrame:
    if V1_HGB_CONTROL not in set(aggregate["candidate"]):
        raise ValueError("V1_HGB_CONTROL aggregate is required")
    control = aggregate[aggregate["candidate"].eq(V1_HGB_CONTROL)].iloc[0]
    rows: list[Mapping[str, object]] = []
    for _, row in aggregate.iterrows():
        if row["candidate"] == V1_HGB_CONTROL:
            continue
        rows.append(
            {
                "candidate": row["candidate"],
                "median_pr_delta_minus_v1": float(row["median_pr_auc_delta"] - control["median_pr_auc_delta"]),
                "q25_pr_delta_minus_v1": float(row["q25_pr_auc_delta"] - control["q25_pr_auc_delta"]),
                "median_roc_minus_v1": float(row["median_roc_auc"] - control["median_roc_auc"]),
                "median_q5q1_minus_v1": float(row["median_q5_minus_q1"] - control["median_q5_minus_q1"]),
            }
        )
    return pd.DataFrame(rows).sort_values("candidate").reset_index(drop=True)
