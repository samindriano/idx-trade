from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from .research_baselines import expected_calibration_error
from .research_validation import FROZEN_FOLDS, chronological_fit_calibration_split, fold_dates, normalize_calendar


PRIMARY_HORIZON = 10
PRIMARY_PRIOR_WINDOW = 60
SENSITIVITY_PRIOR_WINDOW = 126
MIN_RECENT_RESOLVED_ROWS = 1_000
EPSILON = 1e-6
FIXED_ECE_EDGES = tuple(float(x) for x in np.linspace(0.0, 1.0, 11))

STATIC_BASE_RATE = "STATIC_BASE_RATE"
STATIC_ISOTONIC = "STATIC_ISOTONIC"
CAUSAL_PRIOR_ONLY_60 = "CAUSAL_PRIOR_ONLY_60"
ISOTONIC_PRIOR_SHIFT_60 = "ISOTONIC_PRIOR_SHIFT_60"
ISOTONIC_PRIOR_SHIFT_126 = "ISOTONIC_PRIOR_SHIFT_126"


def _normalize_dates(frame: pd.DataFrame, column: str = "date") -> pd.DataFrame:
    if column not in frame.columns:
        raise ValueError(f"missing date column: {column}")
    out = frame.copy()
    out[column] = pd.to_datetime(out[column], errors="coerce").dt.tz_localize(None).dt.normalize()
    if out[column].isna().any():
        raise ValueError(f"invalid dates in {column}")
    return out


def _clip_probability(values: np.ndarray | pd.Series | float) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPSILON, 1.0 - EPSILON)


def prior_shift_probability(
    probability: np.ndarray | pd.Series,
    reference_prior: np.ndarray | pd.Series | float,
    target_prior: np.ndarray | pd.Series | float,
) -> np.ndarray:
    """Apply deterministic prior-probability-shift correction in odds space."""

    p = _clip_probability(probability)
    ref = _clip_probability(reference_prior)
    target = _clip_probability(target_prior)
    odds = p / (1.0 - p)
    ref_odds = ref / (1.0 - ref)
    target_odds = target / (1.0 - target)
    adjusted_odds = odds * (target_odds / ref_odds)
    adjusted = adjusted_odds / (1.0 + adjusted_odds)
    if not np.isfinite(adjusted).all():
        raise ValueError("prior-shift produced non-finite probability")
    return np.clip(adjusted, EPSILON, 1.0 - EPSILON)


def fold_reference_priors(
    model_table: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Return frozen fold train prevalence and calibration-tail reference prior."""

    table = _normalize_dates(model_table)
    calendar = normalize_calendar(official_sessions)
    rows: list[dict[str, object]] = []
    for fold in FROZEN_FOLDS:
        dates = fold_dates(calendar, fold)
        train = table[table["date"].isin(dates["train"])].copy()
        if train.empty or "binary_target" not in train.columns:
            raise ValueError(f"{fold.name} missing training binary rows")
        internal = chronological_fit_calibration_split(dates["train"])
        calibration = train[train["date"].isin(internal["calibration"])].copy()
        if calibration.empty:
            raise ValueError(f"{fold.name} empty calibration tail")
        train_prior = float(train["binary_target"].mean())
        calibration_prior = float(calibration["binary_target"].mean())
        if not (0.0 < train_prior < 1.0 and 0.0 < calibration_prior < 1.0):
            raise ValueError(f"{fold.name} invalid prevalence")
        rows.append(
            {
                "fold": fold.name,
                "train_prior": train_prior,
                "calibration_reference_prior": calibration_prior,
                "train_rows": int(len(train)),
                "calibration_rows": int(len(calibration)),
            }
        )
    return pd.DataFrame(rows)


def causal_recent_prior_audit(
    model_table: pd.DataFrame,
    prediction_dates: Iterable[object],
    official_sessions: Iterable[object],
    *,
    window: int,
    horizon: int = PRIMARY_HORIZON,
    min_rows: int = MIN_RECENT_RESOLVED_ROWS,
) -> pd.DataFrame:
    """Build causal recent TP-rate estimates using only fully matured signal dates."""

    if window <= 0 or horizon <= 0:
        raise ValueError("window and horizon must be positive")
    table = _normalize_dates(model_table)
    if "binary_target" not in table.columns:
        raise ValueError("model_table missing binary_target")
    calendar = normalize_calendar(official_sessions)
    index_by_date = {pd.Timestamp(day): idx for idx, day in enumerate(calendar)}
    requested = (
        pd.DatetimeIndex(pd.to_datetime(list(prediction_dates), errors="coerce"))
        .tz_localize(None)
        .normalize()
        .dropna()
        .unique()
        .sort_values()
    )
    rows: list[dict[str, object]] = []
    for date in requested:
        date = pd.Timestamp(date)
        if date not in index_by_date:
            raise ValueError(f"prediction date outside official calendar: {date.date()}")
        prediction_index = int(index_by_date[date])
        maturity_index = prediction_index - horizon
        if maturity_index < 0:
            raise ValueError(f"insufficient maturity history for {date.date()}")
        window_start_index = maturity_index - window + 1
        if window_start_index < 0:
            raise ValueError(f"insufficient {window}-session history for {date.date()}")
        maturity_date = pd.Timestamp(calendar[maturity_index])
        window_start_date = pd.Timestamp(calendar[window_start_index])
        block = table[table["date"].between(window_start_date, maturity_date, inclusive="both")].copy()
        if len(block) < min_rows:
            raise ValueError(
                f"recent prior has only {len(block)} resolved rows for {date.date()} window={window}; minimum={min_rows}"
            )
        if block.empty or block["binary_target"].isna().any():
            raise ValueError("recent prior block contains invalid target rows")
        recent_prior = float(block["binary_target"].mean())
        max_source = pd.Timestamp(block["date"].max())
        causal_ok = bool(max_source <= maturity_date)
        if not causal_ok:
            raise RuntimeError("causal recent-prior audit failed")
        rows.append(
            {
                "date": date,
                "window_sessions": int(window),
                "prediction_session_index": prediction_index + 1,
                "maturity_cutoff_session_index": maturity_index + 1,
                "maturity_cutoff_date": maturity_date,
                "prior_window_start_session_index": window_start_index + 1,
                "prior_window_start_date": window_start_date,
                "prior_window_end_date": maturity_date,
                "recent_resolved_rows": int(len(block)),
                "recent_prior": recent_prior,
                "max_prior_source_signal_date": max_source,
                "causal_audit_pass": causal_ok,
            }
        )
    return pd.DataFrame(rows)


def _metrics(target: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    y = np.asarray(target, dtype=int)
    p = _clip_probability(probability)
    if len(y) == 0 or len(y) != len(p) or np.unique(y).size != 2:
        raise ValueError("metrics require aligned non-empty binary classes")
    if not np.isfinite(p).all():
        raise ValueError("non-finite Stage-4B probability")
    positive_rate = float(y.mean())
    mean_probability = float(p.mean())
    return {
        "rows": float(len(y)),
        "positive_rate": positive_rate,
        "mean_probability": mean_probability,
        "prevalence_gap": abs(mean_probability - positive_rate),
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "ece": float(expected_calibration_error(y, p, FIXED_ECE_EDGES)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
    }


def build_stage4b_predictions(
    model_table: pd.DataFrame,
    stage4_calibration_predictions: pd.DataFrame,
    official_sessions: Iterable[object],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Construct frozen Stage-4B probability candidates without refitting HGB."""

    table = _normalize_dates(model_table)
    predictions = _normalize_dates(stage4_calibration_predictions)
    required = {"fold", "calibrator", "ticker", "date", "target", "probability"}
    if not required.issubset(predictions.columns):
        raise ValueError(f"Stage-4 predictions missing: {sorted(required - set(predictions.columns))}")
    isotonic = predictions[predictions["calibrator"].eq("ISOTONIC")].copy()
    if isotonic.empty:
        raise ValueError("Stage-4 calibration artifact has no ISOTONIC predictions")
    if isotonic.duplicated(["fold", "ticker", "date"]).any():
        raise ValueError("duplicate Stage-4 isotonic prediction rows")

    priors = fold_reference_priors(table, official_sessions)
    prior_map = priors.set_index("fold")
    audits: list[pd.DataFrame] = []
    candidate_frames: list[pd.DataFrame] = []

    for fold_name, block in isotonic.groupby("fold", sort=True):
        if fold_name not in prior_map.index:
            raise ValueError(f"unknown fold in Stage-4 predictions: {fold_name}")
        reference_prior = float(prior_map.loc[fold_name, "calibration_reference_prior"])
        train_prior = float(prior_map.loc[fold_name, "train_prior"])
        dates = block["date"].unique()
        audit60 = causal_recent_prior_audit(table, dates, official_sessions, window=PRIMARY_PRIOR_WINDOW)
        audit60["fold"] = fold_name
        audit126 = causal_recent_prior_audit(table, dates, official_sessions, window=SENSITIVITY_PRIOR_WINDOW)
        audit126["fold"] = fold_name
        audits.extend([audit60, audit126])
        recent60 = audit60.set_index("date")["recent_prior"]
        recent126 = audit126.set_index("date")["recent_prior"]

        base = block[["fold", "ticker", "date", "target", "probability"]].copy()
        base = base.rename(columns={"probability": "static_isotonic_probability"})
        base["reference_prior"] = reference_prior
        base["train_prior"] = train_prior
        base["recent_prior_60"] = base["date"].map(recent60)
        base["recent_prior_126"] = base["date"].map(recent126)
        if base[["recent_prior_60", "recent_prior_126"]].isna().any().any():
            raise ValueError("failed to map causal prior to every validation row")

        series = {
            STATIC_BASE_RATE: np.full(len(base), train_prior, dtype=float),
            STATIC_ISOTONIC: base["static_isotonic_probability"].to_numpy(dtype=float),
            CAUSAL_PRIOR_ONLY_60: base["recent_prior_60"].to_numpy(dtype=float),
            ISOTONIC_PRIOR_SHIFT_60: prior_shift_probability(
                base["static_isotonic_probability"], reference_prior, base["recent_prior_60"]
            ),
            ISOTONIC_PRIOR_SHIFT_126: prior_shift_probability(
                base["static_isotonic_probability"], reference_prior, base["recent_prior_126"]
            ),
        }
        for candidate, probability in series.items():
            candidate_frames.append(
                pd.DataFrame(
                    {
                        "fold": fold_name,
                        "candidate": candidate,
                        "ticker": base["ticker"].to_numpy(),
                        "date": base["date"].to_numpy(),
                        "target": base["target"].to_numpy(dtype=int),
                        "probability": probability,
                    }
                )
            )

    candidate_predictions = pd.concat(candidate_frames, ignore_index=True)
    audit = pd.concat(audits, ignore_index=True).sort_values(["fold", "window_sessions", "date"]).reset_index(drop=True)
    if not audit["causal_audit_pass"].all():
        raise RuntimeError("Stage-4B causal audit contains failure")
    return candidate_predictions, priors, audit


def candidate_metrics(candidate_predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"fold", "candidate", "target", "probability"}
    if not required.issubset(candidate_predictions.columns):
        raise ValueError(f"candidate predictions missing: {sorted(required - set(candidate_predictions.columns))}")
    fold_rows: list[dict[str, object]] = []
    for (fold, candidate), block in candidate_predictions.groupby(["fold", "candidate"], sort=True):
        fold_rows.append(
            {
                "fold": fold,
                "candidate": candidate,
                **_metrics(block["target"].to_numpy(dtype=int), block["probability"].to_numpy(dtype=float)),
            }
        )
    fold_metrics = pd.DataFrame(fold_rows)
    pooled_rows: list[dict[str, object]] = []
    for candidate, block in candidate_predictions.groupby("candidate", sort=True):
        pooled_rows.append(
            {
                "candidate": candidate,
                **_metrics(block["target"].to_numpy(dtype=int), block["probability"].to_numpy(dtype=float)),
            }
        )
    return fold_metrics, pd.DataFrame(pooled_rows)


def stage4b_readiness(
    fold_metrics: pd.DataFrame,
    pooled_metrics: pd.DataFrame,
    audit: pd.DataFrame,
    *,
    holdout_outcome_accessed: bool,
) -> dict[str, object]:
    pooled = pooled_metrics.set_index("candidate")
    required = {
        STATIC_BASE_RATE,
        STATIC_ISOTONIC,
        CAUSAL_PRIOR_ONLY_60,
        ISOTONIC_PRIOR_SHIFT_60,
        ISOTONIC_PRIOR_SHIFT_126,
    }
    if not required.issubset(pooled.index):
        raise ValueError(f"pooled metrics missing candidates: {sorted(required - set(pooled.index))}")
    primary = pooled.loc[ISOTONIC_PRIOR_SHIFT_60]
    base = pooled.loc[STATIC_BASE_RATE]
    prior_only = pooled.loc[CAUSAL_PRIOR_ONLY_60]
    static_iso = pooled.loc[STATIC_ISOTONIC]

    fold = fold_metrics.set_index(["fold", "candidate"])
    prevalence_better_folds: list[str] = []
    for name in ("F1", "F2", "F3"):
        if float(fold.loc[(name, ISOTONIC_PRIOR_SHIFT_60), "prevalence_gap"]) < float(
            fold.loc[(name, STATIC_BASE_RATE), "prevalence_gap"]
        ):
            prevalence_better_folds.append(name)

    numeric_columns = ["pr_auc", "roc_auc", "brier", "ece", "log_loss", "positive_rate", "mean_probability", "prevalence_gap"]
    metrics_finite = bool(np.isfinite(fold_metrics[numeric_columns].to_numpy(dtype=float)).all()) and bool(
        np.isfinite(pooled_metrics[numeric_columns].to_numpy(dtype=float)).all()
    )
    causal_pass = bool(len(audit)) and bool(audit["causal_audit_pass"].all())
    conditions = {
        "pooled_brier_beats_static_base": float(primary["brier"]) < float(base["brier"]),
        "pooled_brier_beats_causal_prior_only": float(primary["brier"]) < float(prior_only["brier"]),
        "pooled_brier_beats_static_isotonic": float(primary["brier"]) < float(static_iso["brier"]),
        "pooled_ece_beats_static_base": float(primary["ece"]) < float(base["ece"]),
        "prevalence_gap_beats_static_base_at_least_2_folds": len(prevalence_better_folds) >= 2,
        "metrics_finite": metrics_finite,
        "causal_audit_pass": causal_pass,
        "holdout_outcome_accessed_false": not bool(holdout_outcome_accessed),
    }
    ready = all(conditions.values())
    return {
        **conditions,
        "prevalence_gap_better_folds": prevalence_better_folds,
        "calibration_freeze_ready": ready,
        "decision": "STAGE4B_CALIBRATION_FREEZE_READY" if ready else "STAGE4B_CALIBRATION_STILL_BLOCKED",
    }
