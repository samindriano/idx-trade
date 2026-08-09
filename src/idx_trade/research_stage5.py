from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline

from .research_baselines import RANDOM_SEED


HOLDOUT_START_INDEX = 1009
HOLDOUT_H10_LAST_SIGNAL_INDEX = 1250
HOLDOUT_H5_LAST_SIGNAL_INDEX = 1255
HOLDOUT_H20_LAST_SIGNAL_INDEX = 1240
FINAL_TRAIN_SIGNAL_INDEX = 988
HOLDOUT_A = (1009, 1129)
HOLDOUT_B = (1130, 1250)


def momentum_ranker() -> Pipeline:
    """Frozen one-feature development-fitted rank mapping for close_return_20."""

    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            (
                "model",
                LogisticRegression(
                    C=1.0,
                    solver="lbfgs",
                    max_iter=1000,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def pipeline_raw_score(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    """Return a monotone raw ranking score without declaring probability semantics."""

    if "preprocess" in model.named_steps:
        transformed = model.named_steps["preprocess"].transform(frame)
        estimator = model.named_steps["model"]
    else:
        transformed = frame[["close_return_20"]]
        estimator = model.named_steps["model"]
        transformed = model.named_steps["impute"].transform(transformed)
    if hasattr(estimator, "decision_function"):
        return np.asarray(estimator.decision_function(transformed), dtype=float)
    probability = np.asarray(estimator.predict_proba(transformed)[:, 1], dtype=float)
    clipped = np.clip(probability, 1e-9, 1.0 - 1e-9)
    return np.log(clipped / (1.0 - clipped))


def ranking_metrics(target: Sequence[int], score: Sequence[float]) -> dict[str, float]:
    y = np.asarray(target, dtype=int)
    s = np.asarray(score, dtype=float)
    if len(y) == 0 or len(y) != len(s):
        raise ValueError("ranking metrics require aligned non-empty arrays")
    if np.unique(y).size != 2:
        raise ValueError("ranking metrics require both binary classes")
    if not np.isfinite(s).all():
        raise ValueError("ranking scores must be finite")
    return {
        "rows": float(len(y)),
        "positive_rate": float(y.mean()),
        "pr_auc": float(average_precision_score(y, s)),
        "roc_auc": float(roc_auc_score(y, s)),
    }


def assign_within_date_buckets(
    frame: pd.DataFrame,
    *,
    score_column: str,
    buckets: int,
    output_column: str,
) -> pd.DataFrame:
    required = {"date", "ticker", "binary_target", score_column}
    if not required.issubset(frame.columns):
        raise ValueError(f"bucket input missing {sorted(required - set(frame.columns))}")
    if buckets < 2:
        raise ValueError("buckets must be >=2")
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if data["date"].isna().any():
        raise ValueError("bucket input contains invalid dates")
    pieces: list[pd.DataFrame] = []
    for date, group in data.groupby("date", sort=True):
        ordered = group.sort_values([score_column, "ticker"], kind="mergesort").copy()
        n = len(ordered)
        if n == 0:
            continue
        ordered[output_column] = np.ceil(buckets * np.arange(1, n + 1) / n).astype(int).clip(1, buckets)
        pieces.append(ordered)
    if not pieces:
        raise ValueError("bucket input produced no groups")
    return pd.concat(pieces, ignore_index=True).sort_values(["date", "ticker"]).reset_index(drop=True)


def bucket_summary(frame: pd.DataFrame, *, bucket_column: str) -> pd.DataFrame:
    required = {bucket_column, "binary_target"}
    if not required.issubset(frame.columns):
        raise ValueError("bucket summary missing required columns")
    rows: list[dict[str, object]] = []
    overall = float(frame["binary_target"].mean())
    for bucket, block in frame.groupby(bucket_column, sort=True):
        rate = float(block["binary_target"].mean())
        rows.append(
            {
                "bucket": int(bucket),
                "rows": int(len(block)),
                "tp_rate": rate,
                "lift_vs_overall": rate - overall,
            }
        )
    return pd.DataFrame(rows)


def temporal_half_metrics(frame: pd.DataFrame, *, score_column: str) -> pd.DataFrame:
    required = {"signal_session_index", "binary_target", score_column, "date", "ticker"}
    if not required.issubset(frame.columns):
        raise ValueError(f"temporal-half input missing {sorted(required - set(frame.columns))}")
    definitions: Mapping[str, tuple[int, int]] = {"HOLDOUT_A": HOLDOUT_A, "HOLDOUT_B": HOLDOUT_B}
    rows: list[dict[str, object]] = []
    for name, (start, end) in definitions.items():
        block = frame[frame["signal_session_index"].between(start, end)].copy()
        metrics = ranking_metrics(block["binary_target"], block[score_column])
        quintiled = assign_within_date_buckets(
            block,
            score_column=score_column,
            buckets=5,
            output_column="quintile",
        )
        summary = bucket_summary(quintiled, bucket_column="quintile").set_index("bucket")
        rows.append(
            {
                "half": name,
                **metrics,
                "pr_auc_delta_vs_base": float(metrics["pr_auc"] - metrics["positive_rate"]),
                "q5_minus_q1": float(summary.loc[5, "tp_rate"] - summary.loc[1, "tp_rate"]),
                "first_signal_index": int(block["signal_session_index"].min()),
                "last_signal_index": int(block["signal_session_index"].max()),
            }
        )
    return pd.DataFrame(rows)


def stage5_decision(
    *,
    hgb_metrics: Mapping[str, float],
    momentum_metrics: Mapping[str, float],
    q5_rate: float,
    q1_rate: float,
    half_metrics: pd.DataFrame,
    models_frozen_before_holdout_labels: bool,
) -> tuple[str, dict[str, bool]]:
    required_halves = {"HOLDOUT_A", "HOLDOUT_B"}
    if set(half_metrics["half"]) != required_halves:
        raise ValueError("Stage-5 decision requires both frozen temporal halves")
    finite = all(
        np.isfinite(float(value))
        for value in [
            hgb_metrics["pr_auc"],
            hgb_metrics["roc_auc"],
            hgb_metrics["positive_rate"],
            momentum_metrics["pr_auc"],
            q5_rate,
            q1_rate,
            *half_metrics["pr_auc"].tolist(),
            *half_metrics["positive_rate"].tolist(),
        ]
    )
    checks = {
        "hgb_pr_auc_gt_base": float(hgb_metrics["pr_auc"]) > float(hgb_metrics["positive_rate"]),
        "hgb_pr_auc_gt_momentum": float(hgb_metrics["pr_auc"]) > float(momentum_metrics["pr_auc"]),
        "hgb_roc_auc_gt_half": float(hgb_metrics["roc_auc"]) > 0.5,
        "q5_gt_q1": float(q5_rate) > float(q1_rate),
        "holdout_a_pr_auc_gt_base": bool(
            half_metrics.loc[half_metrics["half"].eq("HOLDOUT_A"), "pr_auc"].iloc[0]
            > half_metrics.loc[half_metrics["half"].eq("HOLDOUT_A"), "positive_rate"].iloc[0]
        ),
        "holdout_b_pr_auc_gt_base": bool(
            half_metrics.loc[half_metrics["half"].eq("HOLDOUT_B"), "pr_auc"].iloc[0]
            > half_metrics.loc[half_metrics["half"].eq("HOLDOUT_B"), "positive_rate"].iloc[0]
        ),
        "all_metrics_finite": finite,
        "models_frozen_before_holdout_labels": bool(models_frozen_before_holdout_labels),
    }
    overall = all(checks[key] for key in ("hgb_pr_auc_gt_base", "hgb_pr_auc_gt_momentum", "hgb_roc_auc_gt_half", "q5_gt_q1"))
    halves = checks["holdout_a_pr_auc_gt_base"] and checks["holdout_b_pr_auc_gt_base"]
    safety = checks["all_metrics_finite"] and checks["models_frozen_before_holdout_labels"]
    if not safety:
        return "STAGE5_RUNTIME_BLOCKED", checks
    if overall and halves:
        return "STAGE5_RANKING_HOLDOUT_PASS", checks
    if overall:
        return "STAGE5_RANKING_HOLDOUT_MIXED", checks
    return "STAGE5_RANKING_HOLDOUT_FAIL", checks
