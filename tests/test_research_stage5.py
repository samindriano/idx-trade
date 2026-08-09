import numpy as np
import pandas as pd

from idx_trade.research_stage5 import (
    FINAL_TRAIN_SIGNAL_INDEX,
    HOLDOUT_A,
    HOLDOUT_B,
    HOLDOUT_H10_LAST_SIGNAL_INDEX,
    HOLDOUT_H20_LAST_SIGNAL_INDEX,
    HOLDOUT_H5_LAST_SIGNAL_INDEX,
    HOLDOUT_START_INDEX,
    assign_within_date_buckets,
    bucket_summary,
    momentum_ranker,
    pipeline_raw_score,
    ranking_metrics,
    stage5_decision,
    temporal_half_metrics,
)
from idx_trade.stage5_ranking_holdout import EXPECTED_ENVIRONMENT, FROZEN_STAGE4B_SUMMARY_SHA256


def test_stage5_runner_wiring_and_parent_hash_are_frozen():
    assert EXPECTED_ENVIRONMENT == {
        "python": "3.13.5",
        "numpy": "2.4.2",
        "pandas": "2.3.3",
        "pyarrow": "23.0.1",
        "scikit-learn": "1.8.0",
    }
    assert FROZEN_STAGE4B_SUMMARY_SHA256 == "f9cbce089c21debd6420943ebf5cd647fc41942e4f210964ddbb5d165d10ebb7"


def test_stage5_boundaries_are_frozen_and_h20_purged():
    assert HOLDOUT_START_INDEX == 1009
    assert FINAL_TRAIN_SIGNAL_INDEX == 988
    assert FINAL_TRAIN_SIGNAL_INDEX == HOLDOUT_START_INDEX - 20 - 1
    assert HOLDOUT_H10_LAST_SIGNAL_INDEX == 1250
    assert HOLDOUT_H5_LAST_SIGNAL_INDEX == 1255
    assert HOLDOUT_H20_LAST_SIGNAL_INDEX == 1240
    assert HOLDOUT_A == (1009, 1129)
    assert HOLDOUT_B == (1130, 1250)
    assert HOLDOUT_A[1] - HOLDOUT_A[0] + 1 == 121
    assert HOLDOUT_B[1] - HOLDOUT_B[0] + 1 == 121


def test_momentum_ranker_score_is_finite_and_training_fitted():
    train = pd.DataFrame({"close_return_20": [-0.2, -0.1, 0.1, 0.2, np.nan]})
    target = np.array([0, 0, 1, 1, 1])
    model = momentum_ranker().fit(train[["close_return_20"]], target)
    score = pipeline_raw_score(model, pd.DataFrame({"close_return_20": [-0.15, 0.15, np.nan]}))
    assert np.isfinite(score).all()
    assert score[1] > score[0]


def test_within_date_buckets_are_deterministic_and_local():
    rows = []
    for date in pd.to_datetime(["2026-01-02", "2026-01-05"]):
        for i in range(10):
            rows.append(
                {
                    "date": date,
                    "ticker": f"T{i:02d}",
                    "binary_target": int(i >= 6),
                    "score": float(i),
                }
            )
    frame = pd.DataFrame(rows)
    first = assign_within_date_buckets(
        frame.sample(frac=1.0, random_state=1),
        score_column="score",
        buckets=5,
        output_column="quintile",
    )
    second = assign_within_date_buckets(
        frame.sample(frac=1.0, random_state=2),
        score_column="score",
        buckets=5,
        output_column="quintile",
    )
    pd.testing.assert_frame_equal(first, second)
    counts = first.groupby(["date", "quintile"]).size()
    assert counts.eq(2).all()
    summary = bucket_summary(first, bucket_column="quintile").set_index("bucket")
    assert summary.loc[5, "tp_rate"] > summary.loc[1, "tp_rate"]


def test_ranking_metrics_accept_raw_scores_not_probabilities():
    target = [0, 0, 1, 1]
    metrics = ranking_metrics(target, [-3.0, -1.0, 2.0, 5.0])
    assert metrics["pr_auc"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["positive_rate"] == 0.5


def _half_frame(*, good_a: bool = True, good_b: bool = True) -> pd.DataFrame:
    rows = []
    for name, (start, end), good in (
        ("A", HOLDOUT_A, good_a),
        ("B", HOLDOUT_B, good_b),
    ):
        for idx in range(start, end + 1):
            synthetic_date = pd.Timestamp("2025-01-01") + pd.Timedelta(int(idx), unit="D")
            for j in range(10):
                target = int(j >= 6)
                score = float(j if good else -j)
                rows.append(
                    {
                        "signal_session_index": idx,
                        "binary_target": target,
                        "score": score,
                        "date": synthetic_date,
                        "ticker": f"{name}{j:02d}",
                    }
                )
    return pd.DataFrame(rows)


def test_temporal_half_metrics_cover_both_predeclared_blocks():
    metrics = temporal_half_metrics(_half_frame(), score_column="score")
    assert set(metrics["half"]) == {"HOLDOUT_A", "HOLDOUT_B"}
    assert (metrics["pr_auc"] > metrics["positive_rate"]).all()
    assert (metrics["q5_minus_q1"] > 0).all()


def test_stage5_decision_pass_mixed_and_fail_are_not_posthoc():
    pass_halves = temporal_half_metrics(_half_frame(), score_column="score")
    hgb = {"pr_auc": 0.45, "roc_auc": 0.54, "positive_rate": 0.38}
    momentum = {"pr_auc": 0.40}
    status, checks = stage5_decision(
        hgb_metrics=hgb,
        momentum_metrics=momentum,
        q5_rate=0.44,
        q1_rate=0.32,
        half_metrics=pass_halves,
        models_frozen_before_holdout_labels=True,
    )
    assert status == "STAGE5_RANKING_HOLDOUT_PASS"
    assert all(checks.values())

    mixed_halves = temporal_half_metrics(_half_frame(good_b=False), score_column="score")
    status, _ = stage5_decision(
        hgb_metrics=hgb,
        momentum_metrics=momentum,
        q5_rate=0.44,
        q1_rate=0.32,
        half_metrics=mixed_halves,
        models_frozen_before_holdout_labels=True,
    )
    assert status == "STAGE5_RANKING_HOLDOUT_MIXED"

    status, _ = stage5_decision(
        hgb_metrics={"pr_auc": 0.37, "roc_auc": 0.49, "positive_rate": 0.38},
        momentum_metrics=momentum,
        q5_rate=0.31,
        q1_rate=0.32,
        half_metrics=pass_halves,
        models_frozen_before_holdout_labels=True,
    )
    assert status == "STAGE5_RANKING_HOLDOUT_FAIL"


def test_stage5_decision_blocks_if_models_not_frozen_before_labels():
    halves = temporal_half_metrics(_half_frame(), score_column="score")
    status, checks = stage5_decision(
        hgb_metrics={"pr_auc": 0.45, "roc_auc": 0.54, "positive_rate": 0.38},
        momentum_metrics={"pr_auc": 0.40},
        q5_rate=0.44,
        q1_rate=0.32,
        half_metrics=halves,
        models_frozen_before_holdout_labels=False,
    )
    assert status == "STAGE5_RUNTIME_BLOCKED"
    assert not checks["models_frozen_before_holdout_labels"]
