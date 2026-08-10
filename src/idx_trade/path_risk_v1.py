"""Frozen Path Risk V1 primitives.

This module contains the target, q75 model, diagnostics, and discovery gate
for the separate adverse-excursion lane.  The real H10 label artifact is never
loaded by this module during implementation/cache preparation; target tests
use small synthetic frames only.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from .research_v3_structure_lite import STRUCTURE_LITE_FEATURE_COLUMNS
from .ranking_v3_structure_lite import V3_B_FEATURE_COLUMNS


PATH_RISK_HYPOTHESIS_ID = "PATH-RISK-A-ADVERSE-EXCURSION-Q75-V1"
PATH_RISK_CANDIDATE = "PATH-RISK-A-Q75-HGB-001"
PATH_RISK_BASELINE = "TRAIN-Q75-CONSTANT-BASELINE"
PATH_RISK_DISCOVERY_PASS = "PATH_RISK_A_DISCOVERY_PASS"
PATH_RISK_DISCOVERY_FAIL = "PATH_RISK_A_DISCOVERY_FAIL_CLOSE"
PATH_RISK_CACHE_STATUS = "PATH_RISK_V1_DISCOVERY_FEATURE_CACHE_FROZEN_PRE_OUTCOME"

PATH_RISK_FEATURE_COLUMNS = tuple(V3_B_FEATURE_COLUMNS)
PATH_RISK_FEATURE_ORDER_SHA256 = "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"
PATH_RISK_H10_LABEL_SHA256 = "a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677"
PATH_RISK_QUANTILE = 0.75
PATH_RISK_HORIZON = 10
PATH_RISK_STOP_ATR_MULTIPLE = 1.0
PATH_RISK_REWARD_RISK = 1.5
PATH_RISK_TARGET_TOLERANCE = 1e-9
PATH_RISK_DISCOVERY_FOLDS = ("V2F1", "V2F2", "V2F3", "V2F4")

TARGET_ELIGIBLE_STATUSES = frozenset({"TP_FIRST", "SL_FIRST", "AMBIGUOUS_SAME_BAR", "NO_BARRIER_HIT"})

PATH_RISK_MODEL_CONFIG: dict[str, Any] = {
    "candidate": PATH_RISK_CANDIDATE,
    "feature_columns": list(PATH_RISK_FEATURE_COLUMNS),
    "preprocessing": {
        "transformer": "ColumnTransformer",
        "remainder": "drop",
        "imputer": {
            "strategy": "median",
            "add_indicator": True,
            "keep_empty_features": True,
        },
        "scaler": None,
    },
    "estimator": {
        "class": "HistGradientBoostingRegressor",
        "loss": "quantile",
        "quantile": PATH_RISK_QUANTILE,
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 31,
        "l2_regularization": 1.0,
        "random_state": 42,
    },
}

_LABEL_COLUMNS = {
    "ticker",
    "signal_date",
    "signal_session_index",
    "signal_reference_close",
    "atr",
    "sl_atr_multiple",
    "reward_risk",
    "tp_level",
    "sl_level",
    "label_status",
    "first_barrier_date",
}
_PATH_COLUMNS = {"ticker", "date", "high", "low", "close"}


def _normalize_sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
    if sessions.tz is not None:
        sessions = sessions.tz_localize(None)
    sessions = sessions.normalize().dropna().unique().sort_values()
    if not len(sessions):
        raise ValueError("official_sessions must not be empty")
    return sessions


def _normalize_dates(values: pd.Series, *, name: str) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce")
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_localize(None)
    dates = dates.dt.normalize()
    if dates.isna().any():
        raise ValueError(f"{name} contains invalid dates")
    return dates


def _prepare_path(panel: pd.DataFrame) -> pd.DataFrame:
    missing = _PATH_COLUMNS - set(panel.columns)
    if missing:
        raise ValueError(f"Path Risk panel missing {sorted(missing)}")
    data = panel.loc[:, sorted(_PATH_COLUMNS)].copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["date"] = _normalize_dates(data["date"], name="Path Risk path date")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("Path Risk path contains duplicate ticker/date rows")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].isna().any() or not np.isfinite(data[column].to_numpy(dtype=float)).all():
            raise ValueError(f"Path Risk path contains invalid {column}")
    if not (
        (data["high"] >= data[["low", "close"]].max(axis=1))
        & (data["low"] <= data[["high", "close"]].min(axis=1))
        & (data[["high", "low", "close"]] > 0).all(axis=1)
    ).all():
        raise ValueError("Path Risk path contains invalid HLC envelope")
    return data.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def _first_touch_status(path: pd.DataFrame, *, tp_level: float, sl_level: float) -> tuple[str, pd.Timestamp | pd.NaT]:
    for row in path.itertuples(index=False):
        tp_hit = float(row.high) >= tp_level
        sl_hit = float(row.low) <= sl_level
        if tp_hit and sl_hit:
            return "AMBIGUOUS_SAME_BAR", pd.Timestamp(row.date)
        if tp_hit:
            return "TP_FIRST", pd.Timestamp(row.date)
        if sl_hit:
            return "SL_FIRST", pd.Timestamp(row.date)
    return "NO_BARRIER_HIT", pd.NaT


def _validate_label_identity(label: Mapping[str, Any], path: pd.DataFrame) -> None:
    status = str(label["label_status"])
    actual_status, actual_date = _first_touch_status(
        path,
        tp_level=float(label["tp_level"]),
        sl_level=float(label["sl_level"]),
    )
    expected_date = pd.to_datetime(label["first_barrier_date"], errors="coerce")
    if pd.notna(expected_date):
        expected_date = pd.Timestamp(expected_date).tz_localize(None).normalize()
    if actual_status != status or (
        status != "NO_BARRIER_HIT" and (pd.isna(expected_date) or actual_date != expected_date)
    ) or (status == "NO_BARRIER_HIT" and pd.notna(expected_date)):
        raise ValueError(
            "Path Risk label/barrier identity mismatch: "
            f"expected=({status},{expected_date}) actual=({actual_status},{actual_date})"
        )


def build_adverse_excursion_targets(
    labels: pd.DataFrame,
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Build exact adverse-excursion targets from a frozen H10 label frame.

    This is intentionally a late-bound primitive.  It is covered with
    synthetic fixtures only during this implementation task and is not called
    by the real feature-cache preparation CLI.
    """

    missing = _LABEL_COLUMNS - set(labels.columns)
    if missing:
        raise ValueError(f"Path Risk labels missing {sorted(missing)}")
    data = labels.copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["signal_date"] = _normalize_dates(data["signal_date"], name="Path Risk signal date")
    if data.duplicated(["ticker", "signal_date"]).any():
        raise ValueError("Path Risk labels contain duplicate ticker/signal_date rows")
    sessions = _normalize_sessions(official_sessions)
    index_by_date = {pd.Timestamp(day): index for index, day in enumerate(sessions)}
    path_data = _prepare_path(panel)
    path_lookup = {(row.ticker, pd.Timestamp(row.date)): row for row in path_data.itertuples(index=False)}
    results: list[dict[str, Any]] = []

    for label in data.to_dict(orient="records"):
        status = str(label["label_status"])
        if status not in TARGET_ELIGIBLE_STATUSES:
            continue
        signal_date = pd.Timestamp(label["signal_date"])
        if signal_date not in index_by_date:
            raise ValueError("Path Risk label signal date is not an official session")
        signal_index = index_by_date[signal_date]
        reference = float(label["signal_reference_close"])
        atr = float(label["atr"])
        sl_multiple = float(label["sl_atr_multiple"])
        reward_risk = float(label["reward_risk"])
        stop_distance = sl_multiple * atr
        if not np.isfinite(reference) or reference <= 0 or not np.isfinite(stop_distance) or stop_distance <= 0:
            raise ValueError("Path Risk label has invalid reference/ATR stop distance")
        if not np.isclose(float(label["sl_level"]), reference - stop_distance, rtol=0.0, atol=1e-9):
            raise ValueError("Path Risk stop level disagrees with reference/ATR")
        if not np.isclose(float(label["tp_level"]), reference + reward_risk * stop_distance, rtol=0.0, atol=1e-9):
            raise ValueError("Path Risk target level disagrees with reference/ATR")

        expected_date = pd.to_datetime(label["first_barrier_date"], errors="coerce")
        if pd.notna(expected_date):
            tau_date = pd.Timestamp(expected_date).tz_localize(None).normalize()
            if tau_date not in index_by_date or not signal_index < index_by_date[tau_date] <= signal_index + PATH_RISK_HORIZON:
                raise ValueError("Path Risk first barrier date is outside the H10 future path")
        else:
            end_index = signal_index + PATH_RISK_HORIZON
            if end_index >= len(sessions):
                raise ValueError("Path Risk target has incomplete future session horizon")
            tau_date = pd.Timestamp(sessions[end_index])
        future_dates = sessions[signal_index + 1 : index_by_date[tau_date] + 1]
        future_rows: list[dict[str, Any]] = []
        for future_date in future_dates:
            key = (label["ticker"], pd.Timestamp(future_date))
            row = path_lookup.get(key)
            if row is None:
                raise ValueError(f"Path Risk target has incomplete future path at {key}")
            future_rows.append({"date": row.date, "high": row.high, "low": row.low, "close": row.close})
        path = pd.DataFrame(future_rows)
        _validate_label_identity(label, path)
        minimum_low = float(path["low"].min())
        target = max(0.0, (reference - minimum_low) / stop_distance)
        if not np.isfinite(target) or target < 0:
            raise ValueError("Path Risk target is not finite/non-negative")
        if status in {"SL_FIRST", "AMBIGUOUS_SAME_BAR"} and target < 1.0 - PATH_RISK_TARGET_TOLERANCE:
            raise ValueError("stop-touch Path Risk target is below 1R")
        if status in {"TP_FIRST", "NO_BARRIER_HIT"} and target >= 1.0 + PATH_RISK_TARGET_TOLERANCE:
            raise ValueError("non-stop Path Risk target is at/above 1R")
        results.append(
            {
                "ticker": label["ticker"],
                "signal_date": signal_date,
                "signal_session_index": int(signal_index + 1),
                "label_status": status,
                "first_barrier_date": tau_date if pd.notna(expected_date) else pd.NaT,
                "target_tau_date": tau_date,
                "signal_reference_close": reference,
                "atr": atr,
                "stop_distance": stop_distance,
                "adverse_excursion_r": float(target),
            }
        )
    return pd.DataFrame(results).sort_values(["signal_date", "ticker"]).reset_index(drop=True) if results else pd.DataFrame()


def build_path_risk_model() -> Pipeline:
    """Return the one frozen PR-001 model without fitting it."""

    numeric = Pipeline(
        [
            (
                "impute",
                SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
            )
        ]
    )
    preprocess = ColumnTransformer(
        [("numeric", numeric, list(PATH_RISK_FEATURE_COLUMNS))],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocess", preprocess),
            (
                "model",
                HistGradientBoostingRegressor(
                    loss="quantile",
                    quantile=PATH_RISK_QUANTILE,
                    learning_rate=0.05,
                    max_iter=200,
                    max_leaf_nodes=31,
                    l2_regularization=1.0,
                    random_state=42,
                ),
            ),
        ]
    )


def training_q75_constant(target: Iterable[float]) -> float:
    values = np.asarray(list(target), dtype=float)
    if values.size == 0 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("training q75 baseline requires finite non-negative targets")
    return float(np.quantile(values, PATH_RISK_QUANTILE, method="linear"))


def pinball_loss(target: Iterable[float], prediction: Iterable[float], *, quantile: float = PATH_RISK_QUANTILE) -> float:
    y = np.asarray(list(target), dtype=float)
    qhat = np.asarray(list(prediction), dtype=float)
    if len(y) == 0 or len(y) != len(qhat) or not np.isfinite(y).all() or not np.isfinite(qhat).all():
        raise ValueError("pinball loss requires aligned finite non-empty values")
    if not 0 < quantile < 1:
        raise ValueError("quantile must lie strictly between zero and one")
    error = y - qhat
    return float(np.mean(np.maximum(quantile * error, (quantile - 1.0) * error)))


def _assign_risk_quintiles(frame: pd.DataFrame, *, prediction_column: str) -> pd.DataFrame:
    required = {"date", "ticker", "adverse_excursion_r", prediction_column}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Path Risk quintile input missing {sorted(missing)}")
    pieces: list[pd.DataFrame] = []
    for _, block in frame.groupby("date", sort=True):
        ordered = block.sort_values([prediction_column, "ticker"], kind="mergesort").copy()
        n = len(ordered)
        ordered["risk_quintile"] = np.ceil(5 * np.arange(1, n + 1) / n).astype(int).clip(1, 5)
        pieces.append(ordered)
    if not pieces:
        raise ValueError("Path Risk quintile input produced no dates")
    return pd.concat(pieces, ignore_index=True).sort_values(["date", "ticker"]).reset_index(drop=True)


def path_risk_metrics(frame: pd.DataFrame, *, prediction_column: str = "prediction") -> dict[str, Any]:
    """Compute frozen discovery diagnostics for an already materialized fold."""

    required = {"date", "ticker", "adverse_excursion_r", prediction_column}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Path Risk metrics input missing {sorted(missing)}")
    data = frame.copy()
    target = pd.to_numeric(data["adverse_excursion_r"], errors="coerce").to_numpy(dtype=float)
    prediction = pd.to_numeric(data[prediction_column], errors="coerce").to_numpy(dtype=float)
    if len(target) == 0 or not np.isfinite(target).all() or not np.isfinite(prediction).all() or (target < 0).any():
        raise ValueError("Path Risk metrics require finite non-negative target/prediction")
    quintiled = _assign_risk_quintiles(data, prediction_column=prediction_column)
    grouped = quintiled.groupby("risk_quintile", sort=True)["adverse_excursion_r"].mean()
    stop_rate = quintiled.assign(stop_touch=quintiled["adverse_excursion_r"] >= 1.0).groupby("risk_quintile")["stop_touch"].mean()
    spearman = pd.Series(target).corr(pd.Series(prediction), method="spearman")
    return {
        "rows": int(len(data)),
        "dates": int(data["date"].nunique()),
        "tickers": int(data["ticker"].nunique()),
        "pinball_loss": pinball_loss(target, prediction),
        "mae": float(np.mean(np.abs(target - prediction))),
        "spearman": float(spearman) if pd.notna(spearman) else np.nan,
        "empirical_q75_coverage": float(np.mean(target <= prediction)),
        "absolute_coverage_error": float(abs(np.mean(target <= prediction) - PATH_RISK_QUANTILE)),
        "q1_mean_adverse_excursion": float(grouped.get(1, np.nan)),
        "q5_mean_adverse_excursion": float(grouped.get(5, np.nan)),
        "q5_minus_q1_adverse_excursion": float(grouped.get(5, np.nan) - grouped.get(1, np.nan)),
        "q1_stop_touch_rate": float(stop_rate.get(1, np.nan)),
        "q5_stop_touch_rate": float(stop_rate.get(5, np.nan)),
        "finite_prediction_rate": float(np.isfinite(prediction).mean()),
        "unique_prediction_count": int(pd.Series(prediction).nunique()),
    }


def relative_pinball_improvement(baseline_loss: float, model_loss: float) -> float:
    if not np.isfinite([baseline_loss, model_loss]).all() or baseline_loss <= 0:
        raise ValueError("relative pinball improvement requires positive finite baseline loss")
    return float((baseline_loss - model_loss) / baseline_loss)


def path_risk_discovery_gate(fold_metrics: pd.DataFrame) -> tuple[str, dict[str, bool]]:
    """Apply the exact preregistered F1-F4 discovery gate."""

    required = {"fold", "relative_pinball_improvement", "spearman", "q5_minus_q1_adverse_excursion"}
    missing = required - set(fold_metrics.columns)
    if missing:
        raise ValueError(f"Path Risk gate input missing {sorted(missing)}")
    data = fold_metrics[fold_metrics["fold"].isin(PATH_RISK_DISCOVERY_FOLDS)].copy()
    if set(data["fold"]) != set(PATH_RISK_DISCOVERY_FOLDS) or len(data) != len(PATH_RISK_DISCOVERY_FOLDS):
        raise ValueError("Path Risk discovery gate requires exactly V2F1..V2F4")
    data = data.set_index("fold").loc[list(PATH_RISK_DISCOVERY_FOLDS)]
    pr = pd.to_numeric(data["relative_pinball_improvement"], errors="coerce").to_numpy(dtype=float)
    rho = pd.to_numeric(data["spearman"], errors="coerce").to_numpy(dtype=float)
    spread = pd.to_numeric(data["q5_minus_q1_adverse_excursion"], errors="coerce").to_numpy(dtype=float)
    finite = bool(np.isfinite(pr).all() and np.isfinite(rho).all() and np.isfinite(spread).all())
    checks = {
        "all_required_metrics_finite": finite,
        "relative_pinball_nonnegative_3_of_4": bool(finite and (pr >= 0).sum() >= 3),
        "median_relative_pinball_ge_0_02": bool(finite and np.median(pr) >= 0.02),
        "q25_relative_pinball_nonnegative": bool(finite and np.quantile(pr, 0.25) >= 0),
        "worst_relative_pinball_ge_minus_0_01": bool(finite and pr.min() >= -0.01),
        "spearman_positive_3_of_4": bool(finite and (rho > 0).sum() >= 3),
        "median_spearman_ge_0_10": bool(finite and np.median(rho) >= 0.10),
        "risk_spread_positive_3_of_4": bool(finite and (spread > 0).sum() >= 3),
        "median_risk_spread_ge_0_10": bool(finite and np.median(spread) >= 0.10),
    }
    return (PATH_RISK_DISCOVERY_PASS if all(checks.values()) else PATH_RISK_DISCOVERY_FAIL), checks
