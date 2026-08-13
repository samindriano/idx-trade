from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .research_baselines import (
    LOGISTIC_C,
    RANDOM_SEED,
    TREE_L2,
    TREE_LEARNING_RATE,
    TREE_MAX_ITER,
    TREE_MAX_LEAF_NODES,
)
from .research_features import BASELINE_FEATURE_COLUMNS, assert_no_open_dependency
from .research_v2_features import V2_FULL_FEATURE_COLUMNS, V2_XS_FEATURE_COLUMNS


V1_HGB_CONTROL = "V1_HGB_CONTROL"
LOGISTIC_XS = "LOGISTIC_XS"
HGB_XS = "HGB_XS"
HGB_XS_MARKET = "HGB_XS_MARKET"
PAIRWISE_LOGISTIC_XS = "PAIRWISE_LOGISTIC_XS"

V2_CANDIDATES = (LOGISTIC_XS, HGB_XS, HGB_XS_MARKET, PAIRWISE_LOGISTIC_XS)
ALL_RANKING_V2_MODELS = (V1_HGB_CONTROL, *V2_CANDIDATES)
PAIRWISE_PAIRS_PER_DATE = 256


def candidate_feature_columns(candidate: str) -> tuple[str, ...]:
    if candidate == V1_HGB_CONTROL:
        return tuple(BASELINE_FEATURE_COLUMNS)
    if candidate in {LOGISTIC_XS, HGB_XS, PAIRWISE_LOGISTIC_XS}:
        return tuple(V2_XS_FEATURE_COLUMNS)
    if candidate == HGB_XS_MARKET:
        return tuple(V2_FULL_FEATURE_COLUMNS)
    raise ValueError(f"unknown Ranking V2 model: {candidate}")


def _numeric_preprocessor(columns: Sequence[str], *, scale: bool) -> ColumnTransformer:
    assert_no_open_dependency(columns)
    steps: list[tuple[str, object]] = [
        ("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True))
    ]
    if scale:
        steps.append(("scale", StandardScaler()))
    numeric = Pipeline(steps=steps)
    return ColumnTransformer([("numeric", numeric, list(columns))], remainder="drop")


def pointwise_model(candidate: str) -> Pipeline:
    """Return one frozen pointwise Ranking-V2 model template."""

    columns = candidate_feature_columns(candidate)
    if candidate == LOGISTIC_XS:
        return Pipeline(
            [
                ("preprocess", _numeric_preprocessor(columns, scale=True)),
                (
                    "model",
                    LogisticRegression(
                        C=LOGISTIC_C,
                        solver="lbfgs",
                        max_iter=1000,
                        random_state=RANDOM_SEED,
                    ),
                ),
            ]
        )
    if candidate in {V1_HGB_CONTROL, HGB_XS, HGB_XS_MARKET}:
        return Pipeline(
            [
                ("preprocess", _numeric_preprocessor(columns, scale=False)),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        learning_rate=TREE_LEARNING_RATE,
                        max_iter=TREE_MAX_ITER,
                        max_leaf_nodes=TREE_MAX_LEAF_NODES,
                        l2_regularization=TREE_L2,
                        random_state=RANDOM_SEED,
                    ),
                ),
            ]
        )
    raise ValueError(f"{candidate} is not a pointwise candidate")


def pointwise_raw_score(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    transformed = model.named_steps["preprocess"].transform(frame)
    estimator = model.named_steps["model"]
    if hasattr(estimator, "decision_function"):
        score = estimator.decision_function(transformed)
        return np.asarray(score, dtype=float)
    probability = np.asarray(estimator.predict_proba(transformed)[:, 1], dtype=float)
    clipped = np.clip(probability, 1e-9, 1.0 - 1e-9)
    return np.log(clipped / (1.0 - clipped))


def _date_seed(value: object, *, seed: int = RANDOM_SEED) -> int:
    day = pd.Timestamp(value).tz_localize(None).normalize()
    return int((seed * 1_000_003 + day.toordinal()) % (2**32 - 1))


@dataclass
class PairwiseLogisticRanker:
    feature_columns: tuple[str, ...] = tuple(V2_XS_FEATURE_COLUMNS)
    pairs_per_date: int = PAIRWISE_PAIRS_PER_DATE
    random_seed: int = RANDOM_SEED
    imputer: SimpleImputer | None = None
    scaler: StandardScaler | None = None
    model: LogisticRegression | None = None
    fitted_pair_days: int = 0
    fitted_unique_pairs: int = 0

    def fit(self, frame: pd.DataFrame, target: Sequence[int]) -> "PairwiseLogisticRanker":
        required = {"date", *self.feature_columns}
        if not required.issubset(frame.columns):
            raise ValueError(f"pairwise training frame missing {sorted(required - set(frame.columns))}")
        assert_no_open_dependency(self.feature_columns)
        if self.pairs_per_date <= 0:
            raise ValueError("pairs_per_date must be positive")

        work = frame.reset_index(drop=True).copy()
        y = np.asarray(target, dtype=int)
        if len(work) == 0 or len(work) != len(y):
            raise ValueError("pairwise training requires aligned non-empty rows")
        if np.unique(y).size != 2:
            raise ValueError("pairwise training requires both target classes")
        work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
        if work["date"].isna().any():
            raise ValueError("pairwise training contains invalid dates")

        x = work.loc[:, self.feature_columns].apply(pd.to_numeric, errors="coerce")
        self.imputer = SimpleImputer(strategy="median", keep_empty_features=True)
        x_imputed = self.imputer.fit_transform(x)
        self.scaler = StandardScaler()
        x_scaled = self.scaler.fit_transform(x_imputed)

        pair_x: list[np.ndarray] = []
        pair_y: list[np.ndarray] = []
        pair_days = 0
        unique_pairs = 0

        for date, positions in work.groupby("date", sort=True).indices.items():
            idx = np.asarray(positions, dtype=int)
            positives = idx[y[idx] == 1]
            negatives = idx[y[idx] == 0]
            if len(positives) == 0 or len(negatives) == 0:
                continue
            total = int(len(positives) * len(negatives))
            take = min(self.pairs_per_date, total)
            if take == total:
                flat = np.arange(total, dtype=np.int64)
            else:
                rng = np.random.default_rng(_date_seed(date, seed=self.random_seed))
                flat = np.sort(rng.choice(total, size=take, replace=False).astype(np.int64))
            pos_choice = positives[flat // len(negatives)]
            neg_choice = negatives[flat % len(negatives)]
            difference = x_scaled[pos_choice] - x_scaled[neg_choice]
            pair_x.append(np.vstack([difference, -difference]))
            pair_y.append(np.concatenate([np.ones(take, dtype=int), np.zeros(take, dtype=int)]))
            pair_days += 1
            unique_pairs += take

        if not pair_x:
            raise ValueError("pairwise training produced no positive-negative date pairs")
        train_x = np.vstack(pair_x)
        train_y = np.concatenate(pair_y)
        if np.unique(train_y).size != 2:
            raise RuntimeError("pairwise training unexpectedly produced one class")

        self.model = LogisticRegression(
            C=LOGISTIC_C,
            solver="lbfgs",
            max_iter=1000,
            random_state=self.random_seed,
        )
        self.model.fit(train_x, train_y)
        self.fitted_pair_days = int(pair_days)
        self.fitted_unique_pairs = int(unique_pairs)
        return self

    def score(self, frame: pd.DataFrame) -> np.ndarray:
        if self.imputer is None or self.scaler is None or self.model is None:
            raise RuntimeError("pairwise ranker is not fitted")
        required = set(self.feature_columns)
        if not required.issubset(frame.columns):
            raise ValueError(f"pairwise scoring frame missing {sorted(required - set(frame.columns))}")
        x = frame.loc[:, self.feature_columns].apply(pd.to_numeric, errors="coerce")
        scaled = self.scaler.transform(self.imputer.transform(x))
        return np.asarray(self.model.decision_function(scaled), dtype=float)
