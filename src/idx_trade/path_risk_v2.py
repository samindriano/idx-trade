"""Frozen Path Risk V2 primitives.

V2 is a bounded follow-on to failed Path Risk V1. It defines two new
probability architectures on the already-viewed F1-F4 development period:
PR-002 direct H10 stop-touch probability and PR-003 discrete competing-risk
barrier hazards. F5/F6 and fresh-forward outcomes are outside this module's
execution contract.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline

from .ranking_v3_structure_lite import V3_B_FEATURE_COLUMNS
from .research_baselines import (
    RANDOM_SEED,
    TREE_L2,
    TREE_LEARNING_RATE,
    TREE_MAX_ITER,
    TREE_MAX_LEAF_NODES,
)


PATH_RISK_V2_SPEC_GIT_BLOB = "6d171d3f492b9cd15e0a176428eb9d6e4f6c20c5"
PATH_RISK_V2_FEATURE_COLUMNS = tuple(V3_B_FEATURE_COLUMNS)
PATH_RISK_V2_FEATURE_ORDER_SHA256 = "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"
PATH_RISK_V2_V1_MODEL_TABLE_SHA256 = "b66fc7e40f18940ae9db418331a421e0f36d23b86597500b1d3ba73a8e3777fe"
PATH_RISK_V2_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
PATH_RISK_V2_MODEL_TABLE_ROWS = 252_198
PATH_RISK_V2_MAX_SIGNAL_SESSION = 984
PATH_RISK_V2_HORIZON = 10
PATH_RISK_V2_DISCOVERY_FOLDS = ("V2F1", "V2F2", "V2F3", "V2F4")

PR002_HYPOTHESIS = "PATH-RISK-V2-STOP-TOUCH-H10-V1"
PR002_CANDIDATE = "PATH-RISK-V2-STOP-H10-HGB-002"
PR003_HYPOTHESIS = "PATH-RISK-V2-DISCRETE-COMPETING-RISK-V1"
PR003_CANDIDATE = "PATH-RISK-V2-DISCRETE-CR-HGB-003"
PATH_RISK_V2_CANDIDATES = (PR002_CANDIDATE, PR003_CANDIDATE)

PATH_RISK_V2_DISCOVERY_WINNER = "PATH_RISK_V2_DISCOVERY_WINNER_SELECTED"
PATH_RISK_V2_DISCOVERY_FAIL = "PATH_RISK_V2_DISCOVERY_FAIL_CLOSE"
PATH_RISK_V2_SELECTION_TIE_TOLERANCE = 0.002

STOP_TOUCH_POSITIVE_STATUSES = frozenset({"SL_FIRST", "AMBIGUOUS_SAME_BAR"})
STOP_TOUCH_NEGATIVE_STATUSES = frozenset({"TP_FIRST", "NO_BARRIER_HIT"})
PATH_RISK_V2_STATUSES = STOP_TOUCH_POSITIVE_STATUSES | STOP_TOUCH_NEGATIVE_STATUSES

CR_CONTINUE = 0
CR_STOP = 1
CR_TP = 2
CR_CLASS_NAMES = {CR_CONTINUE: "CONTINUE", CR_STOP: "STOP", CR_TP: "TP"}
CR_HORIZON_COLUMN = "path_horizon_step"
CR_FEATURE_COLUMNS = (*PATH_RISK_V2_FEATURE_COLUMNS, CR_HORIZON_COLUMN)


def _numeric_preprocessor(columns: Iterable[str]) -> ColumnTransformer:
    numeric = Pipeline(
        [
            (
                "impute",
                SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
            )
        ]
    )
    return ColumnTransformer([("numeric", numeric, list(columns))], remainder="drop")


def build_pr002_model() -> Pipeline:
    return Pipeline(
        [
            ("preprocess", _numeric_preprocessor(PATH_RISK_V2_FEATURE_COLUMNS)),
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


def build_pr003_model() -> Pipeline:
    return Pipeline(
        [
            ("preprocess", _numeric_preprocessor(CR_FEATURE_COLUMNS)),
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


def add_stop_touch_target(frame: pd.DataFrame) -> pd.DataFrame:
    if "label_status" not in frame.columns:
        raise ValueError("Path Risk V2 frame requires label_status")
    data = frame.copy()
    status = data["label_status"].astype(str)
    invalid = sorted(set(status.unique()) - PATH_RISK_V2_STATUSES)
    if invalid:
        raise ValueError(f"Path Risk V2 contains unsupported statuses: {invalid}")
    data["stop_touch_h10"] = status.isin(STOP_TOUCH_POSITIVE_STATUSES).astype(int)
    if "adverse_excursion_r" in data.columns:
        ae = pd.to_numeric(data["adverse_excursion_r"], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(ae).all() or (ae < 0).any():
            raise ValueError("Path Risk V2 adverse_excursion_r must be finite and non-negative")
        positive = data["stop_touch_h10"].to_numpy(dtype=int) == 1
        if np.any(ae[positive] < 1.0 - 1e-9):
            raise ValueError("Path Risk V2 stop-touch row has adverse excursion below 1R")
        if np.any(ae[~positive] >= 1.0 + 1e-9):
            raise ValueError("Path Risk V2 non-stop row has adverse excursion at/above 1R")
    return data


def _normalize_sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
    if sessions.tz is not None:
        sessions = sessions.tz_localize(None)
    sessions = sessions.normalize().dropna().unique().sort_values()
    if not len(sessions):
        raise ValueError("official_sessions must not be empty")
    return sessions


def add_competing_risk_event_metadata(
    frame: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    required = {"date", "label_status", "first_barrier_date"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Path Risk V2 event metadata missing {sorted(missing)}")
    data = add_stop_touch_target(frame)
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    barrier = pd.to_datetime(data["first_barrier_date"], errors="coerce")
    if getattr(barrier.dt, "tz", None) is not None:
        barrier = barrier.dt.tz_localize(None)
    data["first_barrier_date"] = barrier.dt.normalize()
    if data["date"].isna().any():
        raise ValueError("Path Risk V2 contains invalid signal dates")

    sessions = _normalize_sessions(official_sessions)
    session_to_index = {pd.Timestamp(day): index for index, day in enumerate(sessions)}
    event_day = np.full(len(data), np.nan, dtype=float)
    event_cause = np.full(len(data), "NONE", dtype=object)

    for position, row in enumerate(
        data[["date", "label_status", "first_barrier_date"]].itertuples(index=False)
    ):
        signal_date = pd.Timestamp(row.date)
        status = str(row.label_status)
        barrier_date = row.first_barrier_date
        if signal_date not in session_to_index:
            raise ValueError("Path Risk V2 signal date is not an official session")
        if status == "NO_BARRIER_HIT":
            if pd.notna(barrier_date):
                raise ValueError("NO_BARRIER_HIT must not have first_barrier_date")
            continue
        if pd.isna(barrier_date):
            raise ValueError(f"{status} requires first_barrier_date")
        barrier_date = pd.Timestamp(barrier_date)
        if barrier_date not in session_to_index:
            raise ValueError("Path Risk V2 first_barrier_date is not an official session")
        delta = session_to_index[barrier_date] - session_to_index[signal_date]
        if not 1 <= delta <= PATH_RISK_V2_HORIZON:
            raise ValueError("Path Risk V2 first barrier is outside H1..H10")
        event_day[position] = float(delta)
        event_cause[position] = "TP" if status == "TP_FIRST" else "STOP"

    data["event_day"] = event_day
    data["event_cause"] = event_cause
    return data


def expand_competing_risk_training(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"event_day", "event_cause", *PATH_RISK_V2_FEATURE_COLUMNS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Path Risk V2 competing-risk training missing {sorted(missing)}")
    data = frame.reset_index(drop=True).copy()
    if data.empty:
        raise ValueError("Path Risk V2 competing-risk training frame is empty")

    event_day = pd.to_numeric(data["event_day"], errors="coerce").to_numpy(dtype=float)
    cause = data["event_cause"].astype(str).to_numpy(dtype=object)
    has_event = np.isfinite(event_day)
    if np.any(
        has_event
        & ((event_day < 1) | (event_day > PATH_RISK_V2_HORIZON) | (event_day != np.floor(event_day)))
    ):
        raise ValueError("Path Risk V2 event_day must be integer H1..H10 when present")
    if np.any(has_event & ~np.isin(cause, ["STOP", "TP"])) or np.any(~has_event & (cause != "NONE")):
        raise ValueError("Path Risk V2 event cause/day mismatch")

    lengths = np.where(has_event, event_day, PATH_RISK_V2_HORIZON).astype(int)
    cumulative = np.cumsum(lengths, dtype=np.int64)
    total = int(cumulative[-1])
    starts = np.repeat(cumulative - lengths, lengths)
    positions = np.repeat(np.arange(len(data), dtype=np.int64), lengths)
    steps = np.arange(total, dtype=np.int64) - starts + 1

    expanded = data.iloc[positions][list(PATH_RISK_V2_FEATURE_COLUMNS)].reset_index(drop=True)
    expanded[CR_HORIZON_COLUMN] = steps.astype(int)
    target = np.full(total, CR_CONTINUE, dtype=int)
    event_positions = np.flatnonzero(has_event)
    if len(event_positions):
        final_rows = cumulative[event_positions] - 1
        target[final_rows] = np.where(cause[event_positions] == "STOP", CR_STOP, CR_TP)
    expanded["cr_target"] = target
    if np.unique(target).size < 2:
        raise ValueError("Path Risk V2 competing-risk expansion produced fewer than two classes")
    return expanded


def _predict_positive_probability(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    probabilities = np.asarray(model.predict_proba(frame), dtype=float)
    classes = np.asarray(model.named_steps["model"].classes_)
    matches = np.flatnonzero(classes == 1)
    if len(matches) != 1:
        raise RuntimeError("Path Risk V2 binary model lacks positive class 1")
    prediction = probabilities[:, int(matches[0])]
    if not np.isfinite(prediction).all() or (prediction < 0).any() or (prediction > 1).any():
        raise RuntimeError("Path Risk V2 binary probability is invalid")
    return prediction


def predict_pr002_probability(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    return _predict_positive_probability(model, frame)


def _competing_probability_matrix(model: Pipeline, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    probabilities = np.asarray(model.predict_proba(frame), dtype=float)
    classes = np.asarray(model.named_steps["model"].classes_, dtype=int)
    if set(classes.tolist()) != {CR_CONTINUE, CR_STOP, CR_TP}:
        raise RuntimeError(f"Path Risk V2 competing-risk model classes mismatch: {classes.tolist()}")
    if not np.isfinite(probabilities).all() or (probabilities < 0).any() or (probabilities > 1).any():
        raise RuntimeError("Path Risk V2 competing-risk conditional probabilities are invalid")
    if not np.allclose(probabilities.sum(axis=1), 1.0, rtol=0.0, atol=1e-10):
        raise RuntimeError("Path Risk V2 competing-risk conditional probability mass is not one")
    return probabilities, classes


def score_pr003_cumulative_risk(model: Pipeline, frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", *PATH_RISK_V2_FEATURE_COLUMNS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Path Risk V2 competing-risk scoring missing {sorted(missing)}")
    data = frame.reset_index(drop=True).copy()
    n = len(data)
    if n == 0:
        raise ValueError("Path Risk V2 competing-risk scoring frame is empty")

    positions = np.repeat(np.arange(n, dtype=np.int64), PATH_RISK_V2_HORIZON)
    expanded = data.iloc[positions][list(PATH_RISK_V2_FEATURE_COLUMNS)].reset_index(drop=True)
    expanded[CR_HORIZON_COLUMN] = np.tile(
        np.arange(1, PATH_RISK_V2_HORIZON + 1, dtype=int), n
    )
    conditional, classes = _competing_probability_matrix(model, expanded)
    class_to_column = {int(value): index for index, value in enumerate(classes)}
    conditional = conditional.reshape(n, PATH_RISK_V2_HORIZON, len(classes))

    survival = np.ones(n, dtype=float)
    stop_cif = np.zeros(n, dtype=float)
    tp_cif = np.zeros(n, dtype=float)
    stop_checkpoints: dict[int, np.ndarray] = {}
    for step in range(PATH_RISK_V2_HORIZON):
        p_continue = conditional[:, step, class_to_column[CR_CONTINUE]]
        p_stop = conditional[:, step, class_to_column[CR_STOP]]
        p_tp = conditional[:, step, class_to_column[CR_TP]]
        stop_cif = stop_cif + survival * p_stop
        tp_cif = tp_cif + survival * p_tp
        survival = survival * p_continue
        horizon = step + 1
        if horizon in {3, 5, 10}:
            stop_checkpoints[horizon] = stop_cif.copy()

    mass_error = np.abs(stop_cif + tp_cif + survival - 1.0)
    if not np.isfinite(mass_error).all() or float(mass_error.max()) > 1e-8:
        raise RuntimeError("Path Risk V2 competing-risk cumulative mass failed conservation")
    output = data[["ticker", "date"]].copy()
    if "signal_session_index" in data.columns:
        output["signal_session_index"] = data["signal_session_index"].to_numpy()
    output["stop_probability_h3"] = stop_checkpoints[3]
    output["stop_probability_h5"] = stop_checkpoints[5]
    output["stop_probability_h10"] = stop_checkpoints[10]
    output["tp_probability_h10"] = tp_cif
    output["survival_probability_h10"] = survival
    output["mass_error_h10"] = mass_error
    return output


def _fixed_ece(target: np.ndarray, probability: np.ndarray, *, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    assignments = np.digitize(probability, edges[1:-1], right=True)
    total = float(len(target))
    ece = 0.0
    for bucket in range(bins):
        mask = assignments == bucket
        if not mask.any():
            continue
        ece += float(mask.sum() / total) * abs(
            float(target[mask].mean()) - float(probability[mask].mean())
        )
    return float(ece)


def _assign_within_date_quintile(frame: pd.DataFrame, prediction_column: str) -> pd.DataFrame:
    required = {"date", "ticker", prediction_column}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Path Risk V2 quintile input missing {sorted(missing)}")
    pieces: list[pd.DataFrame] = []
    for _, block in frame.groupby("date", sort=True):
        ordered = block.sort_values([prediction_column, "ticker"], kind="mergesort").copy()
        n = len(ordered)
        if n == 0:
            continue
        ordered["risk_quintile"] = np.ceil(5 * np.arange(1, n + 1) / n).astype(int).clip(1, 5)
        pieces.append(ordered)
    if not pieces:
        raise ValueError("Path Risk V2 quintile input is empty")
    return pd.concat(pieces, ignore_index=True)


def probability_metrics(frame: pd.DataFrame, *, prediction_column: str = "prediction") -> dict[str, Any]:
    required = {"date", "ticker", "stop_touch_h10", "adverse_excursion_r", prediction_column}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Path Risk V2 metrics input missing {sorted(missing)}")
    data = frame.copy()
    target = pd.to_numeric(data["stop_touch_h10"], errors="raise").to_numpy(dtype=int)
    probability = pd.to_numeric(data[prediction_column], errors="coerce").to_numpy(dtype=float)
    ae = pd.to_numeric(data["adverse_excursion_r"], errors="coerce").to_numpy(dtype=float)
    if len(target) == 0 or np.unique(target).size != 2:
        raise ValueError("Path Risk V2 metrics require non-empty binary validation target")
    if not np.isfinite(probability).all() or (probability < 0).any() or (probability > 1).any():
        raise ValueError("Path Risk V2 metrics require finite probabilities in [0,1]")
    if not np.isfinite(ae).all():
        raise ValueError("Path Risk V2 metrics require finite adverse excursion")

    quintiled = _assign_within_date_quintile(data, prediction_column)
    q1 = quintiled[quintiled["risk_quintile"].eq(1)]
    q5 = quintiled[quintiled["risk_quintile"].eq(5)]
    if q1.empty or q5.empty:
        raise ValueError("Path Risk V2 metrics require populated Q1/Q5")
    spearman = pd.Series(probability).corr(pd.Series(ae), method="spearman")
    return {
        "rows": int(len(data)),
        "dates": int(pd.to_datetime(data["date"]).nunique()),
        "tickers": int(data["ticker"].astype(str).nunique()),
        "positive_rate": float(target.mean()),
        "prediction_mean": float(probability.mean()),
        "log_loss": float(
            log_loss(target, np.clip(probability, 1e-12, 1.0 - 1e-12), labels=[0, 1])
        ),
        "brier": float(brier_score_loss(target, probability)),
        "roc_auc": float(roc_auc_score(target, probability)),
        "pr_auc": float(average_precision_score(target, probability)),
        "ece_10_equal_width": _fixed_ece(target, probability),
        "q1_stop_touch_rate": float(q1["stop_touch_h10"].mean()),
        "q5_stop_touch_rate": float(q5["stop_touch_h10"].mean()),
        "q5_minus_q1_stop_touch_rate": float(
            q5["stop_touch_h10"].mean() - q1["stop_touch_h10"].mean()
        ),
        "spearman_vs_adverse_excursion": float(spearman) if pd.notna(spearman) else np.nan,
        "finite_prediction_rate": float(np.isfinite(probability).mean()),
        "unique_prediction_count": int(pd.Series(probability).nunique(dropna=True)),
    }


def relative_improvement(baseline: float, candidate: float) -> float:
    baseline = float(baseline)
    candidate = float(candidate)
    if not np.isfinite(baseline) or not np.isfinite(candidate) or baseline <= 0:
        raise ValueError("relative improvement requires finite positive baseline and finite candidate")
    return float((baseline - candidate) / baseline)


def path_risk_v2_candidate_gate(
    metrics: pd.DataFrame,
) -> tuple[bool, dict[str, bool], dict[str, float | int]]:
    required = {
        "fold",
        "relative_logloss_improvement_vs_base",
        "relative_brier_improvement_vs_base",
        "relative_logloss_improvement_vs_alpha",
        "roc_auc",
        "q5_minus_q1_stop_touch_rate",
    }
    missing = required - set(metrics.columns)
    if missing:
        raise ValueError(f"Path Risk V2 gate missing {sorted(missing)}")
    if len(metrics) != 4 or set(metrics["fold"].astype(str)) != set(PATH_RISK_V2_DISCOVERY_FOLDS):
        raise ValueError("Path Risk V2 gate requires exact F1-F4 rows")

    log_base = pd.to_numeric(
        metrics["relative_logloss_improvement_vs_base"], errors="coerce"
    ).to_numpy(dtype=float)
    brier_base = pd.to_numeric(
        metrics["relative_brier_improvement_vs_base"], errors="coerce"
    ).to_numpy(dtype=float)
    log_alpha = pd.to_numeric(
        metrics["relative_logloss_improvement_vs_alpha"], errors="coerce"
    ).to_numpy(dtype=float)
    roc = pd.to_numeric(metrics["roc_auc"], errors="coerce").to_numpy(dtype=float)
    spread = pd.to_numeric(
        metrics["q5_minus_q1_stop_touch_rate"], errors="coerce"
    ).to_numpy(dtype=float)
    finite = bool(np.isfinite(np.concatenate([log_base, brier_base, log_alpha, roc, spread])).all())
    aggregate = {
        "nonnegative_logloss_vs_base_folds": int(np.sum(log_base >= 0.0)) if finite else 0,
        "median_logloss_vs_base": float(np.median(log_base)) if finite else np.nan,
        "nonnegative_brier_vs_base_folds": int(np.sum(brier_base >= 0.0)) if finite else 0,
        "nonnegative_logloss_vs_alpha_folds": int(np.sum(log_alpha >= 0.0)) if finite else 0,
        "median_logloss_vs_alpha": float(np.median(log_alpha)) if finite else np.nan,
        "roc_gt_half_folds": int(np.sum(roc > 0.5)) if finite else 0,
        "median_roc_auc": float(np.median(roc)) if finite else np.nan,
        "positive_spread_folds": int(np.sum(spread > 0.0)) if finite else 0,
        "median_q5_minus_q1_stop_touch_rate": float(np.median(spread)) if finite else np.nan,
    }
    checks = {
        "all_required_metrics_finite": finite,
        "logloss_vs_base_nonnegative_3_of_4": finite
        and aggregate["nonnegative_logloss_vs_base_folds"] >= 3,
        "median_logloss_vs_base_ge_0_005": finite
        and aggregate["median_logloss_vs_base"] >= 0.005,
        "brier_vs_base_nonnegative_3_of_4": finite
        and aggregate["nonnegative_brier_vs_base_folds"] >= 3,
        "logloss_vs_alpha_nonnegative_3_of_4": finite
        and aggregate["nonnegative_logloss_vs_alpha_folds"] >= 3,
        "median_logloss_vs_alpha_ge_0_002": finite
        and aggregate["median_logloss_vs_alpha"] >= 0.002,
        "roc_gt_half_3_of_4": finite and aggregate["roc_gt_half_folds"] >= 3,
        "median_roc_ge_0_55": finite and aggregate["median_roc_auc"] >= 0.55,
        "positive_q5_q1_spread_4_of_4": finite and aggregate["positive_spread_folds"] == 4,
        "median_q5_q1_spread_ge_0_08": finite
        and aggregate["median_q5_minus_q1_stop_touch_rate"] >= 0.08,
    }
    return bool(all(checks.values())), checks, aggregate


def select_path_risk_v2_candidate(
    candidate_metrics: pd.DataFrame,
) -> tuple[str, str | None, dict[str, Any]]:
    required = {"candidate", "fold"}
    if not required.issubset(candidate_metrics.columns):
        raise ValueError("Path Risk V2 selection requires candidate and fold columns")
    candidates = set(candidate_metrics["candidate"].astype(str))
    if candidates != set(PATH_RISK_V2_CANDIDATES):
        raise ValueError(f"Path Risk V2 selection requires exactly {PATH_RISK_V2_CANDIDATES}")

    details: dict[str, Any] = {}
    eligible: list[str] = []
    for candidate in PATH_RISK_V2_CANDIDATES:
        block = candidate_metrics[candidate_metrics["candidate"].eq(candidate)].copy()
        passed, checks, aggregate = path_risk_v2_candidate_gate(block)
        details[candidate] = {"eligible": passed, "checks": checks, "aggregate": aggregate}
        if passed:
            eligible.append(candidate)
    if not eligible:
        return PATH_RISK_V2_DISCOVERY_FAIL, None, details
    if len(eligible) == 1:
        return PATH_RISK_V2_DISCOVERY_WINNER, eligible[0], details

    pr002 = float(details[PR002_CANDIDATE]["aggregate"]["median_logloss_vs_alpha"])
    pr003 = float(details[PR003_CANDIDATE]["aggregate"]["median_logloss_vs_alpha"])
    if abs(pr002 - pr003) <= PATH_RISK_V2_SELECTION_TIE_TOLERANCE:
        winner = PR002_CANDIDATE
    else:
        winner = PR002_CANDIDATE if pr002 > pr003 else PR003_CANDIDATE
    return PATH_RISK_V2_DISCOVERY_WINNER, winner, details
