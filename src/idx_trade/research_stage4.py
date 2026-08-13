from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline

from .research_baselines import (
    RANDOM_SEED,
    TREE_L2,
    TREE_LEARNING_RATE,
    TREE_MAX_ITER,
    TREE_MAX_LEAF_NODES,
    expected_calibration_error,
)
from .research_features import BASELINE_FEATURE_COLUMNS, assert_no_open_dependency
from .research_validation import FROZEN_FOLDS, chronological_fit_calibration_split, fold_dates, normalize_calendar


FEATURE_FAMILIES: Mapping[str, tuple[str, ...]] = {
    "MOMENTUM": ("close_return_5", "close_return_20"),
    "VOLATILITY": ("atr14_over_close",),
    "STRUCTURE": (
        "close_position_20",
        "distance_high_20_atr",
        "distance_low_20_atr",
        "distance_high_60_atr",
        "distance_low_60_atr",
    ),
    "VOLUME_LIQUIDITY": ("relative_volume_20", "log_regular_value_relative_20"),
    "HISTORY": ("observed_session_count", "security_age_sessions_exact"),
}

ABLATION_VARIANTS: Mapping[str, tuple[str, ...]] = {
    "HGB_FULL": tuple(BASELINE_FEATURE_COLUMNS),
    **{
        f"HGB_NO_{family}": tuple(col for col in BASELINE_FEATURE_COLUMNS if col not in columns)
        for family, columns in FEATURE_FAMILIES.items()
    },
}

CALIBRATOR_ORDER = ("NATIVE", "PLATT", "ISOTONIC")
REGIME_MIN_ROWS = 1_000


@dataclass(frozen=True)
class Stage4FoldBundle:
    fold: str
    validation: pd.DataFrame
    raw_score: np.ndarray
    native_probability: np.ndarray
    calibration_raw_score: np.ndarray
    calibration_native_probability: np.ndarray
    calibration_target: np.ndarray


def probability_bin_edges(probabilities: Sequence[float], bins: int = 10) -> tuple[float, ...]:
    values = np.clip(np.asarray(probabilities, dtype=float), 0.0, 1.0)
    if len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("calibration probabilities must be finite and non-empty")
    quantiles = np.quantile(values, np.linspace(0.0, 1.0, bins + 1))
    edges = np.maximum.accumulate(quantiles)
    edges[0] = 0.0
    edges[-1] = 1.0
    if np.unique(edges).size < 3:
        edges = np.linspace(0.0, 1.0, bins + 1)
    return tuple(float(value) for value in edges)


def stage4_hgb_pipeline(feature_columns: Sequence[str]) -> Pipeline:
    columns = tuple(feature_columns)
    if not columns:
        raise ValueError("Stage-4 HGB requires at least one feature")
    unknown = set(columns) - set(BASELINE_FEATURE_COLUMNS)
    if unknown:
        raise ValueError(f"Stage-4 feature columns outside frozen registry: {sorted(unknown)}")
    assert_no_open_dependency(columns)
    preprocess = ColumnTransformer(
        [("numeric", SimpleImputer(strategy="median", add_indicator=True), list(columns))],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocess", preprocess),
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


def _raw_score(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    transformed = model.named_steps["preprocess"].transform(frame)
    estimator = model.named_steps["model"]
    return np.asarray(estimator.decision_function(transformed), dtype=float)


def _platt_fit(raw_score: np.ndarray, target: np.ndarray) -> LogisticRegression:
    y = np.asarray(target, dtype=int)
    if np.unique(y).size != 2:
        raise ValueError("Platt calibration requires both classes")
    model = LogisticRegression(C=1_000_000.0, solver="lbfgs", max_iter=1000)
    model.fit(np.asarray(raw_score, dtype=float).reshape(-1, 1), y)
    return model


def _platt_predict(model: LogisticRegression, raw_score: np.ndarray) -> np.ndarray:
    return model.predict_proba(np.asarray(raw_score, dtype=float).reshape(-1, 1))[:, 1]


def _metrics(target: Sequence[int], probability: Sequence[float], edges: Sequence[float]) -> dict[str, float]:
    y = np.asarray(target, dtype=int)
    p = np.clip(np.asarray(probability, dtype=float), 1e-9, 1.0 - 1e-9)
    if len(y) == 0 or len(y) != len(p) or np.unique(y).size != 2:
        raise ValueError("metrics require aligned non-empty binary classes")
    if not np.isfinite(p).all():
        raise ValueError("probabilities must be finite")
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
        "ece": float(expected_calibration_error(y, p, edges)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
    }


def fit_full_hgb_fold(
    model_table: pd.DataFrame,
    official_sessions: Iterable[object],
    fold_name: str,
) -> Stage4FoldBundle:
    calendar = normalize_calendar(official_sessions)
    fold = next((item for item in FROZEN_FOLDS if item.name == fold_name), None)
    if fold is None:
        raise ValueError(f"unknown frozen fold: {fold_name}")
    dates = fold_dates(calendar, fold)
    table = model_table.copy()
    table["date"] = pd.to_datetime(table["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    holdout_start = calendar[1008]
    if table["date"].isna().any() or (table["date"] >= holdout_start).any():
        raise RuntimeError("Stage-4 model table contains invalid or locked-holdout dates")
    train = table[table["date"].isin(dates["train"])].copy()
    validation = table[table["date"].isin(dates["validation"])].copy()
    internal = chronological_fit_calibration_split(dates["train"])
    fit_rows = train[train["date"].isin(internal["model_fit"])].copy()
    calibration_rows = train[train["date"].isin(internal["calibration"])].copy()
    if any(frame.empty for frame in (fit_rows, calibration_rows, validation)):
        raise ValueError(f"{fold_name} has an empty Stage-4 partition")
    model = stage4_hgb_pipeline(BASELINE_FEATURE_COLUMNS)
    model.fit(fit_rows, fit_rows["binary_target"].to_numpy())
    cal_raw = _raw_score(model, calibration_rows)
    val_raw = _raw_score(model, validation)
    cal_native = np.asarray(model.predict_proba(calibration_rows)[:, 1], dtype=float)
    val_native = np.asarray(model.predict_proba(validation)[:, 1], dtype=float)
    return Stage4FoldBundle(
        fold=fold_name,
        validation=validation,
        raw_score=val_raw,
        native_probability=val_native,
        calibration_raw_score=cal_raw,
        calibration_native_probability=cal_native,
        calibration_target=calibration_rows["binary_target"].to_numpy(dtype=int),
    )


def calibration_candidates(bundle: Stage4FoldBundle) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, tuple[float, ...]]]:
    y_cal = bundle.calibration_target
    y_val = bundle.validation["binary_target"].to_numpy(dtype=int)
    candidates: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    candidates["NATIVE"] = (bundle.calibration_native_probability, bundle.native_probability)

    platt = _platt_fit(bundle.calibration_raw_score, y_cal)
    candidates["PLATT"] = (
        _platt_predict(platt, bundle.calibration_raw_score),
        _platt_predict(platt, bundle.raw_score),
    )

    isotonic = IsotonicRegression(out_of_bounds="clip")
    isotonic.fit(bundle.calibration_raw_score, y_cal)
    candidates["ISOTONIC"] = (
        np.asarray(isotonic.predict(bundle.calibration_raw_score), dtype=float),
        np.asarray(isotonic.predict(bundle.raw_score), dtype=float),
    )

    metrics_rows: list[dict[str, object]] = []
    predictions: list[pd.DataFrame] = []
    edge_map: dict[str, tuple[float, ...]] = {}
    for name in CALIBRATOR_ORDER:
        cal_probability, val_probability = candidates[name]
        edges = probability_bin_edges(cal_probability)
        edge_map[name] = edges
        metrics_rows.append({"fold": bundle.fold, "calibrator": name, **_metrics(y_val, val_probability, edges)})
        predictions.append(
            pd.DataFrame(
                {
                    "fold": bundle.fold,
                    "calibrator": name,
                    "ticker": bundle.validation["ticker"].to_numpy(),
                    "date": bundle.validation["date"].to_numpy(),
                    "target": y_val,
                    "raw_score": bundle.raw_score,
                    "probability": val_probability,
                }
            )
        )
    return pd.DataFrame(metrics_rows), pd.concat(predictions, ignore_index=True), edge_map


def run_ablation_fold(
    model_table: pd.DataFrame,
    official_sessions: Iterable[object],
    fold_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    calendar = normalize_calendar(official_sessions)
    fold = next((item for item in FROZEN_FOLDS if item.name == fold_name), None)
    if fold is None:
        raise ValueError(f"unknown frozen fold: {fold_name}")
    dates = fold_dates(calendar, fold)
    table = model_table.copy()
    table["date"] = pd.to_datetime(table["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if (table["date"] >= calendar[1008]).any():
        raise RuntimeError("Stage-4 ablation rejects locked-holdout rows")
    train = table[table["date"].isin(dates["train"])].copy()
    validation = table[table["date"].isin(dates["validation"])].copy()
    internal = chronological_fit_calibration_split(dates["train"])
    fit_rows = train[train["date"].isin(internal["model_fit"])].copy()
    calibration_rows = train[train["date"].isin(internal["calibration"])].copy()
    y_cal = calibration_rows["binary_target"].to_numpy(dtype=int)
    y_val = validation["binary_target"].to_numpy(dtype=int)

    metric_rows: list[dict[str, object]] = []
    prediction_rows: list[pd.DataFrame] = []
    for variant, columns in ABLATION_VARIANTS.items():
        model = stage4_hgb_pipeline(columns)
        model.fit(fit_rows, fit_rows["binary_target"].to_numpy(dtype=int))
        cal_raw = _raw_score(model, calibration_rows)
        val_raw = _raw_score(model, validation)
        platt = _platt_fit(cal_raw, y_cal)
        cal_probability = _platt_predict(platt, cal_raw)
        val_probability = _platt_predict(platt, val_raw)
        edges = probability_bin_edges(cal_probability)
        metric_rows.append({"fold": fold_name, "variant": variant, **_metrics(y_val, val_probability, edges)})
        prediction_rows.append(
            pd.DataFrame(
                {
                    "fold": fold_name,
                    "variant": variant,
                    "ticker": validation["ticker"].to_numpy(),
                    "date": validation["date"].to_numpy(),
                    "target": y_val,
                    "raw_score": val_raw,
                    "probability": val_probability,
                }
            )
        )
    return pd.DataFrame(metric_rows), pd.concat(prediction_rows, ignore_index=True)


def attribution_summary(ablation_metrics: pd.DataFrame) -> pd.DataFrame:
    required = {"fold", "variant", "pr_auc"}
    if not required.issubset(ablation_metrics.columns):
        raise ValueError(f"ablation metrics missing {sorted(required - set(ablation_metrics.columns))}")
    full = ablation_metrics[ablation_metrics["variant"].eq("HGB_FULL")].set_index("fold")
    rows: list[dict[str, object]] = []
    for family in FEATURE_FAMILIES:
        variant = f"HGB_NO_{family}"
        candidate = ablation_metrics[ablation_metrics["variant"].eq(variant)].set_index("fold")
        folds = sorted(set(full.index) & set(candidate.index))
        deltas = {fold: float(candidate.loc[fold, "pr_auc"] - full.loc[fold, "pr_auc"]) for fold in folds}
        mean_delta = float(np.mean(list(deltas.values()))) if deltas else np.nan
        helps = sum(delta > 0 for delta in deltas.values())
        hurts = sum(delta < 0 for delta in deltas.values())
        if hurts >= 2 and mean_delta < 0:
            status = "CONTRIBUTES_DIRECTIONALLY"
        elif helps == 3 and mean_delta > 0:
            status = "CONSISTENTLY_HARMFUL"
        else:
            status = "INCONCLUSIVE"
        rows.append(
            {
                "family": family,
                "removed_variant": variant,
                **{f"delta_{fold}": deltas.get(fold, np.nan) for fold in ("F1", "F2", "F3")},
                "mean_pr_auc_delta_removed_minus_full": mean_delta,
                "folds_removal_helps": helps,
                "folds_removal_hurts": hurts,
                "attribution_status": status,
            }
        )
    return pd.DataFrame(rows)


def assign_cross_sectional_quintiles(predictions: pd.DataFrame) -> pd.DataFrame:
    required = {"fold", "date", "ticker", "target", "raw_score"}
    if not required.issubset(predictions.columns):
        raise ValueError(f"prediction table missing {sorted(required - set(predictions.columns))}")
    frame = predictions.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    pieces: list[pd.DataFrame] = []
    for (_, date), group in frame.groupby(["fold", "date"], sort=True):
        ordered = group.sort_values(["raw_score", "ticker"], kind="mergesort").copy()
        n = len(ordered)
        ordered["score_quintile"] = np.ceil(5.0 * np.arange(1, n + 1) / n).astype(int).clip(1, 5)
        pieces.append(ordered)
    return pd.concat(pieces, ignore_index=True).sort_values(["fold", "date", "ticker"]).reset_index(drop=True)


def quintile_summary(quintiled: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    groups = [(fold, block) for fold, block in quintiled.groupby("fold", sort=True)]
    groups.append(("POOLED", quintiled))
    for fold, block in groups:
        base_rate = float(block["target"].mean())
        rates: dict[int, float] = {}
        for quintile in range(1, 6):
            bucket = block[block["score_quintile"].eq(quintile)]
            rate = float(bucket["target"].mean()) if len(bucket) else np.nan
            rates[quintile] = rate
            rows.append(
                {
                    "fold": fold,
                    "quintile": quintile,
                    "rows": int(len(bucket)),
                    "tp_rate": rate,
                    "base_rate": base_rate,
                    "lift_vs_base": rate - base_rate if np.isfinite(rate) else np.nan,
                    "q5_minus_q1": np.nan,
                    "q5_gt_q1": False,
                }
            )
        spread = rates[5] - rates[1] if np.isfinite(rates[5]) and np.isfinite(rates[1]) else np.nan
        for row in rows[-5:]:
            row["q5_minus_q1"] = spread
            row["q5_gt_q1"] = bool(np.isfinite(spread) and spread > 0)
    return pd.DataFrame(rows)


def daily_regime_metrics(feature_table: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "universe_primary_liquid", "close_return_20", "atr14_over_close"}
    if not required.issubset(feature_table.columns):
        raise ValueError(f"feature table missing {sorted(required - set(feature_table.columns))}")
    frame = feature_table[feature_table["universe_primary_liquid"].astype(bool)].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    result = frame.groupby("date", as_index=False).agg(
        trend_metric=("close_return_20", "median"),
        volatility_metric=("atr14_over_close", "median"),
        regime_source_rows=("ticker", "size") if "ticker" in frame.columns else ("date", "size"),
    )
    return result.sort_values("date").reset_index(drop=True)


def _tertile_thresholds(values: pd.Series) -> tuple[float, float]:
    finite = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(finite) < 10:
        raise ValueError("not enough training dates for regime thresholds")
    low, high = np.quantile(finite, [1.0 / 3.0, 2.0 / 3.0])
    return float(low), float(high)


def _classify(values: pd.Series, low: float, high: float) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return pd.Series(
        np.where(numeric < low, "LOW", np.where(numeric > high, "HIGH", "MID")),
        index=values.index,
        dtype="object",
    ).where(numeric.notna(), "UNKNOWN")


def regime_diagnostics(
    feature_table: pd.DataFrame,
    platt_predictions: pd.DataFrame,
    calibration_edges: Mapping[str, Sequence[float]],
    official_sessions: Iterable[object],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    calendar = normalize_calendar(official_sessions)
    daily = daily_regime_metrics(feature_table)
    thresholds_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    for fold in FROZEN_FOLDS:
        dates = fold_dates(calendar, fold)
        train_daily = daily[daily["date"].isin(dates["train"])].copy()
        validation_daily = daily[daily["date"].isin(dates["validation"])].copy()
        trend_low, trend_high = _tertile_thresholds(train_daily["trend_metric"])
        vol_low, vol_high = _tertile_thresholds(train_daily["volatility_metric"])
        thresholds_rows.extend(
            [
                {"fold": fold.name, "regime_axis": "TREND", "low_threshold": trend_low, "high_threshold": trend_high},
                {"fold": fold.name, "regime_axis": "VOLATILITY", "low_threshold": vol_low, "high_threshold": vol_high},
            ]
        )
        validation_daily["TREND"] = _classify(validation_daily["trend_metric"], trend_low, trend_high)
        validation_daily["VOLATILITY"] = _classify(validation_daily["volatility_metric"], vol_low, vol_high)
        predictions = platt_predictions[platt_predictions["fold"].eq(fold.name)].merge(
            validation_daily[["date", "TREND", "VOLATILITY"]], on="date", how="left", validate="many_to_one"
        )
        edges = calibration_edges[fold.name]
        for axis in ("TREND", "VOLATILITY"):
            for regime, block in predictions.groupby(axis, dropna=False, sort=True):
                sample_flag = "OK" if len(block) >= REGIME_MIN_ROWS else "LOW_SAMPLE_DIAGNOSTIC"
                row: dict[str, object] = {
                    "fold": fold.name,
                    "regime_axis": axis,
                    "regime": str(regime),
                    "rows": int(len(block)),
                    "sample_flag": sample_flag,
                }
                if len(block) and block["target"].nunique() == 2:
                    row.update(_metrics(block["target"], block["probability"], edges))
                metric_rows.append(row)
    return pd.DataFrame(thresholds_rows), pd.DataFrame(metric_rows)


def pooled_calibration_metrics(
    fold_metrics: pd.DataFrame,
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for calibrator in CALIBRATOR_ORDER:
        pred = predictions[predictions["calibrator"].eq(calibrator)].copy()
        metrics = fold_metrics[fold_metrics["calibrator"].eq(calibrator)].copy()
        y = pred["target"].to_numpy(dtype=int)
        p = np.clip(pred["probability"].to_numpy(dtype=float), 1e-9, 1.0 - 1e-9)
        rows.append(
            {
                "calibrator": calibrator,
                "rows": int(len(pred)),
                "positive_rate": float(y.mean()),
                "mean_probability": float(p.mean()),
                "prevalence_gap": abs(float(p.mean()) - float(y.mean())),
                "pr_auc": float(average_precision_score(y, p)),
                "roc_auc": float(roc_auc_score(y, p)),
                "brier": float(brier_score_loss(y, p)),
                "weighted_fold_ece": float(np.average(metrics["ece"], weights=metrics["rows"])),
                "log_loss": float(log_loss(y, p, labels=[0, 1])),
            }
        )
    return pd.DataFrame(rows)


def select_calibrator(pooled: pd.DataFrame) -> str:
    required = {"calibrator", "brier", "weighted_fold_ece"}
    if not required.issubset(pooled.columns):
        raise ValueError(f"pooled calibration table missing {sorted(required - set(pooled.columns))}")
    rank = {name: idx for idx, name in enumerate(CALIBRATOR_ORDER)}
    frame = pooled.copy()
    frame["brier_key"] = frame["brier"].round(8)
    frame["ece_key"] = frame["weighted_fold_ece"].round(8)
    frame["simplicity"] = frame["calibrator"].map(rank)
    return str(frame.sort_values(["brier_key", "ece_key", "simplicity"]).iloc[0]["calibrator"])


def calibration_readiness(
    selected: str,
    calibration_fold_metrics: pd.DataFrame,
    pooled_calibration: pd.DataFrame,
    base_fold_metrics: pd.DataFrame,
    base_pooled_brier: float,
    base_weighted_ece: float,
) -> dict[str, object]:
    selected_pooled = pooled_calibration[pooled_calibration["calibrator"].eq(selected)].iloc[0]
    selected_folds = calibration_fold_metrics[calibration_fold_metrics["calibrator"].eq(selected)].set_index("fold")
    base_folds = base_fold_metrics.set_index("fold")
    prevalence_gap_wins = 0
    finite = True
    for fold in ("F1", "F2", "F3"):
        if fold not in selected_folds.index or fold not in base_folds.index:
            finite = False
            continue
        values = selected_folds.loc[fold, ["brier", "ece", "prevalence_gap"]].to_numpy(dtype=float)
        finite = finite and bool(np.isfinite(values).all())
        if float(selected_folds.loc[fold, "prevalence_gap"]) < float(base_folds.loc[fold, "prevalence_gap"]):
            prevalence_gap_wins += 1
    checks = {
        "pooled_brier_beats_base": float(selected_pooled["brier"]) < float(base_pooled_brier),
        "pooled_ece_beats_base": float(selected_pooled["weighted_fold_ece"]) < float(base_weighted_ece),
        "prevalence_gap_better_in_at_least_2_folds": prevalence_gap_wins >= 2,
        "finite_metrics_all_folds": finite,
    }
    return {
        "selected_calibrator": selected,
        "prevalence_gap_wins": prevalence_gap_wins,
        **checks,
        "calibration_ready": all(checks.values()),
    }
