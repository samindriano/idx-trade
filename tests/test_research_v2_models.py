from __future__ import annotations

import numpy as np
import pandas as pd

from idx_trade.research_v2_features import V2_FULL_FEATURE_COLUMNS, V2_XS_FEATURE_COLUMNS
from idx_trade.research_v2_models import (
    HGB_XS,
    HGB_XS_MARKET,
    LOGISTIC_XS,
    PAIRWISE_LOGISTIC_XS,
    PairwiseLogisticRanker,
    candidate_feature_columns,
    pointwise_model,
)


def _pairwise_frame() -> tuple[pd.DataFrame, np.ndarray]:
    rows: list[dict[str, object]] = []
    targets: list[int] = []
    for day in range(3):
        date = pd.Timestamp("2026-01-05") + pd.Timedelta(days=day)
        for i in range(8):
            row: dict[str, object] = {"date": date}
            for j, feature in enumerate(V2_XS_FEATURE_COLUMNS):
                row[feature] = (i + 1) / 8.0 + j * 0.001
            rows.append(row)
            targets.append(int(i >= 4))
    return pd.DataFrame(rows), np.asarray(targets, dtype=int)


def test_candidate_feature_sets_are_frozen() -> None:
    assert candidate_feature_columns(LOGISTIC_XS) == tuple(V2_XS_FEATURE_COLUMNS)
    assert candidate_feature_columns(HGB_XS) == tuple(V2_XS_FEATURE_COLUMNS)
    assert candidate_feature_columns(PAIRWISE_LOGISTIC_XS) == tuple(V2_XS_FEATURE_COLUMNS)
    assert candidate_feature_columns(HGB_XS_MARKET) == tuple(V2_FULL_FEATURE_COLUMNS)


def test_pointwise_models_build_without_search_space() -> None:
    logistic = pointwise_model(LOGISTIC_XS)
    hgb_xs = pointwise_model(HGB_XS)
    hgb_market = pointwise_model(HGB_XS_MARKET)
    assert logistic.named_steps["model"].C == 1.0
    assert hgb_xs.named_steps["model"].max_iter == 200
    assert hgb_market.named_steps["model"].max_leaf_nodes == 31


def test_pairwise_ranker_is_deterministic_and_orders_toy_signal() -> None:
    frame, target = _pairwise_frame()
    first = PairwiseLogisticRanker().fit(frame, target)
    second = PairwiseLogisticRanker().fit(frame, target)
    score_a = first.score(frame)
    score_b = second.score(frame)
    assert np.allclose(score_a, score_b)
    assert first.fitted_pair_days == 3
    assert first.fitted_unique_pairs > 0
    assert float(score_a[target == 1].mean()) > float(score_a[target == 0].mean())
