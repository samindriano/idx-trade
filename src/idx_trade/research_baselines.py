from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .research_features import BASELINE_FEATURE_COLUMNS, assert_no_open_dependency
from .research_labels import SL_FIRST, TP_FIRST
from .research_validation import (
    FROZEN_FOLDS,
    DevelopmentFold,
    assert_fold_contract,
    chronological_fit_calibration_split,
    fold_dates,
    normalize_calendar,
)


RANDOM_SEED = 42
LOGISTIC_C = 1.0
TREE_MAX_ITER = 200
TREE_LEARNING_RATE = 0.05
TREE_MAX_LEAF_NODES = 31
TREE_L2 = 1.0


@dataclass(frozen=True)
class FoldModelResult:
    fold: str
    model_name: str
    metrics: dict[str, float]
    predictions: pd.DataFrame
    calibration_bin_edges: tuple[float, ...]


def _logit(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(values, dtype=float), 1e-6, 1.0 - 1e-6)
    return np.log(clipped / (1.0 - clipped))


def _platt_fit(raw_score: np.ndarray, target: np.ndarray) -> LogisticRegression:
    y = np.asarray(target, dtype=int)
    if np.unique(y).size != 2:
        raise ValueError("Platt calibration requires both binary classes")
    model = LogisticRegression(C=1_000_000.0, solver="lbfgs", max_iter=1000)
    model.fit(np.asarray(raw_score, dtype=float).reshape(-1, 1), y)
    return model


def _platt_predict(model: LogisticRegression, raw_score: np.ndarray) -> np.ndarray:
    return model.predict_proba(np.asarray(raw_score, dtype=float).reshape(-1, 1))[:, 1]


def _probability_bin_edges(training_probabilities: np.ndarray, *, bins: int = 10) -> tuple[float, ...]:
    values = np.clip(np.asarray(training_probabilities, dtype=float), 0.0, 1.0)
    if len(values) == 0:
        raise ValueError("cannot define calibration bins from an empty training set")
    quantiles = np.quantile(values, np.linspace(0.0, 1.0, bins + 1))
    edges = np.maximum.accumulate(quantiles)
    edges[0] = 0.0
    edges[-1] = 1.0
    # Degenerate probability distributions can collapse quantiles. Equal-width
    # fallback is deterministic and avoids defining bins from validation data.
    if np.unique(edges).size < 3:
        edges = np.linspace(0.0, 1.0, bins + 1)
    return tuple(float(value) for value in edges)


def expected_calibration_error(
    target: Sequence[int],
    probabilities: Sequence[float],
    bin_edges: Sequence[float],
) -> float:
    y = np.asarray(target, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    edges = np.asarray(bin_edges, dtype=float)
    if len(y) != len(p) or len(y) == 0:
        raise ValueError("target and probabilities must be non-empty and aligned")
    if np.any(np.diff(edges) < 0) or edges[0] > 0 or edges[-1] < 1:
        raise ValueError("invalid calibration bin edges")
    assignments = np.digitize(p, edges[1:-1], right=True)
    ece = 0.0
    for bucket in range(len(edges) - 1):
        mask = assignments == bucket
        if not mask.any():
            continue
        weight = float(mask.mean())
        ece += weight * abs(float(y[mask].mean()) - float(p[mask].mean()))
    return float(ece)


def _metrics(target: np.ndarray, probabilities: np.ndarray, edges: Sequence[float]) -> dict[str, float]:
    y = np.asarray(target, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    if np.unique(y).size != 2:
        raise ValueError("validation metrics require both binary classes")
    return {
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "ece": expected_calibration_error(y, p, edges),
        "positive_rate": float(y.mean()),
        "prediction_mean": float(p.mean()),
        "rows": float(len(y)),
    }


def _numeric_pipeline(*, scale: bool) -> ColumnTransformer:
    steps: list[tuple[str, object]] = [("impute", SimpleImputer(strategy="median", add_indicator=True))]
    if scale:
        steps.append(("scale", StandardScaler()))
    numeric = Pipeline(steps=steps)
    return ColumnTransformer([("numeric", numeric, list(BASELINE_FEATURE_COLUMNS))], remainder="drop")


def logistic_baseline() -> Pipeline:
    assert_no_open_dependency(BASELINE_FEATURE_COLUMNS)
    return Pipeline(
        [
            ("preprocess", _numeric_pipeline(scale=True)),
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


def tree_challenger() -> Pipeline:
    assert_no_open_dependency(BASELINE_FEATURE_COLUMNS)
    return Pipeline(
        [
            ("preprocess", _numeric_pipeline(scale=False)),
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


def prepare_primary_model_table(features: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Join frozen primary-universe causal features to resolved binary labels."""

    feature_required = {"ticker", "date", "universe_primary_liquid", *BASELINE_FEATURE_COLUMNS}
    label_required = {"ticker", "signal_date", "label_status", "binary_target"}
    if not feature_required.issubset(features.columns):
        raise ValueError(f"feature table missing: {sorted(feature_required - set(features.columns))}")
    if not label_required.issubset(labels.columns):
        raise ValueError(f"label table missing: {sorted(label_required - set(labels.columns))}")
    assert_no_open_dependency(BASELINE_FEATURE_COLUMNS)

    x = features[features["universe_primary_liquid"].astype(bool)].copy()
    x["date"] = pd.to_datetime(x["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    y = labels[labels["label_status"].isin([TP_FIRST, SL_FIRST])].copy()
    y["signal_date"] = pd.to_datetime(y["signal_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    joined = x.merge(
        y[["ticker", "signal_date", "binary_target", "label_status"]],
        left_on=["ticker", "date"],
        right_on=["ticker", "signal_date"],
        how="inner",
        validate="one_to_one",
    )
    if joined.empty:
        raise ValueError("primary model table has no resolved observations")
    joined["binary_target"] = joined["binary_target"].astype(int)
    return joined.sort_values(["date", "ticker"]).reset_index(drop=True)


def _raw_score(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    estimator = model.named_steps["model"]
    transformed = model.named_steps["preprocess"].transform(frame)
    if hasattr(estimator, "decision_function"):
        return np.asarray(estimator.decision_function(transformed), dtype=float)
    return _logit(np.asarray(estimator.predict_proba(transformed)[:, 1], dtype=float))


def _fold_by_name(name: str) -> DevelopmentFold:
    for fold in FROZEN_FOLDS:
        if fold.name == name:
            return fold
    raise ValueError(f"unknown frozen fold: {name}")


def run_development_fold(
    model_table: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    fold_name: str,
    include_tree: bool = True,
) -> list[FoldModelResult]:
    """Fit frozen development baselines without reading locked-holdout rows."""

    calendar = normalize_calendar(official_sessions)
    assert_fold_contract(calendar)
    fold = _fold_by_name(fold_name)
    dates = fold_dates(calendar, fold)
    table = model_table.copy()
    table["date"] = pd.to_datetime(table["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if table["date"].isna().any():
        raise ValueError("model table contains invalid dates")
    holdout_start = calendar[1008]
    if (table["date"] >= holdout_start).any():
        raise RuntimeError("development runner rejects any table containing locked-holdout rows")

    train = table[table["date"].isin(dates["train"])].copy()
    validation = table[table["date"].isin(dates["validation"])].copy()
    if train.empty or validation.empty:
        raise ValueError(f"{fold_name} has empty train or validation rows")
    if np.unique(train["binary_target"]).size != 2 or np.unique(validation["binary_target"]).size != 2:
        raise ValueError(f"{fold_name} requires both binary classes in train and validation")

    internal = chronological_fit_calibration_split(dates["train"])
    fit_rows = train[train["date"].isin(internal["model_fit"])].copy()
    calibration_rows = train[train["date"].isin(internal["calibration"])].copy()
    if fit_rows.empty or calibration_rows.empty:
        raise ValueError(f"{fold_name} has empty model-fit or calibration rows")
    if np.unique(fit_rows["binary_target"]).size != 2 or np.unique(calibration_rows["binary_target"]).size != 2:
        raise ValueError(f"{fold_name} fit/calibration partitions require both classes")

    results: list[FoldModelResult] = []
    train_prevalence = float(train["binary_target"].mean())
    constant_cal = np.full(len(calibration_rows), train_prevalence, dtype=float)
    constant_val = np.full(len(validation), train_prevalence, dtype=float)
    constant_edges = _probability_bin_edges(constant_cal)
    results.append(
        FoldModelResult(
            fold=fold_name,
            model_name="base_rate",
            metrics=_metrics(validation["binary_target"].to_numpy(), constant_val, constant_edges),
            predictions=pd.DataFrame(
                {
                    "ticker": validation["ticker"].to_numpy(),
                    "date": validation["date"].to_numpy(),
                    "target": validation["binary_target"].to_numpy(),
                    "probability": constant_val,
                }
            ),
            calibration_bin_edges=constant_edges,
        )
    )

    # Momentum is a fixed one-dimensional score. Missing values are imputed from
    # the model-fit prefix only, then Platt-calibrated on the chronological tail.
    momentum_median = float(pd.to_numeric(fit_rows["close_return_20"], errors="coerce").median())
    if not np.isfinite(momentum_median):
        raise ValueError(f"{fold_name} has no finite training momentum values")
    momentum_cal = pd.to_numeric(calibration_rows["close_return_20"], errors="coerce").fillna(momentum_median).to_numpy()
    momentum_val = pd.to_numeric(validation["close_return_20"], errors="coerce").fillna(momentum_median).to_numpy()
    momentum_platt = _platt_fit(momentum_cal, calibration_rows["binary_target"].to_numpy())
    momentum_cal_prob = _platt_predict(momentum_platt, momentum_cal)
    momentum_val_prob = _platt_predict(momentum_platt, momentum_val)
    momentum_edges = _probability_bin_edges(momentum_cal_prob)
    results.append(
        FoldModelResult(
            fold=fold_name,
            model_name="momentum_20",
            metrics=_metrics(validation["binary_target"].to_numpy(), momentum_val_prob, momentum_edges),
            predictions=pd.DataFrame(
                {
                    "ticker": validation["ticker"].to_numpy(),
                    "date": validation["date"].to_numpy(),
                    "target": validation["binary_target"].to_numpy(),
                    "probability": momentum_val_prob,
                }
            ),
            calibration_bin_edges=momentum_edges,
        )
    )

    candidates: list[tuple[str, Pipeline]] = [("logistic_compact", logistic_baseline())]
    if include_tree:
        candidates.append(("hist_gradient_boosting", tree_challenger()))

    for model_name, template in candidates:
        model = clone(template)
        model.fit(fit_rows, fit_rows["binary_target"].to_numpy())
        calibration_score = _raw_score(model, calibration_rows)
        validation_score = _raw_score(model, validation)
        platt = _platt_fit(calibration_score, calibration_rows["binary_target"].to_numpy())
        calibration_probability = _platt_predict(platt, calibration_score)
        validation_probability = _platt_predict(platt, validation_score)
        edges = _probability_bin_edges(calibration_probability)
        results.append(
            FoldModelResult(
                fold=fold_name,
                model_name=model_name,
                metrics=_metrics(validation["binary_target"].to_numpy(), validation_probability, edges),
                predictions=pd.DataFrame(
                    {
                        "ticker": validation["ticker"].to_numpy(),
                        "date": validation["date"].to_numpy(),
                        "target": validation["binary_target"].to_numpy(),
                        "raw_score": validation_score,
                        "probability": validation_probability,
                    }
                ),
                calibration_bin_edges=edges,
            )
        )
    return results
