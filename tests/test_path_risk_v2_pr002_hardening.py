from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer

from idx_trade.path_risk_v2 import (
    PATH_RISK_V2_FEATURE_COLUMNS,
    PATH_RISK_V2_FEATURE_ORDER_SHA256,
    PATH_RISK_V2_HORIZON,
    add_competing_risk_event_metadata,
    add_stop_touch_target,
    build_pr002_model,
    predict_pr002_probability,
)


_POSITIVE_STATUSES = {"SL_FIRST", "AMBIGUOUS_SAME_BAR"}
_STATUS_CYCLE = ("SL_FIRST", "AMBIGUOUS_SAME_BAR", "TP_FIRST", "NO_BARRIER_HIT")


def _features(row_index: int, *, missing_first: bool = False) -> dict[str, float]:
    values = {
        column: float(((row_index + 1) * (column_index + 2)) % 23) + column_index / 100.0
        for column_index, column in enumerate(PATH_RISK_V2_FEATURE_COLUMNS)
    }
    if missing_first:
        values[PATH_RISK_V2_FEATURE_COLUMNS[0]] = np.nan
    return values


def _synthetic_labels(rows: int = 24, *, missing_first_at: int | None = None) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for index in range(rows):
        status = _STATUS_CYCLE[index % len(_STATUS_CYCLE)]
        records.append(
            {
                "ticker": f"SYN{index:03d}",
                "date": pd.Timestamp("2026-01-02") + pd.Timedelta(days=index),
                "label_status": status,
                "adverse_excursion_r": 1.0 if status in _POSITIVE_STATUSES else 0.2,
                **_features(index, missing_first=index == missing_first_at),
            }
        )
    return pd.DataFrame(records)


def _synthetic_score_frame(rows: int = 8) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": f"SCORE{index:03d}",
                "date": pd.Timestamp("2026-03-02") + pd.Timedelta(days=index),
                **_features(index + 100),
            }
            for index in range(rows)
        ]
    )


def test_pr002_stop_touch_mapping_is_conservative_and_status_whitelisted() -> None:
    frame = pd.DataFrame({"label_status": list(_STATUS_CYCLE)})

    result = add_stop_touch_target(frame)

    assert result["stop_touch_h10"].tolist() == [1, 1, 0, 0]


@pytest.mark.parametrize(
    ("status", "adverse_excursion", "message"),
    [
        ("UNKNOWN_STATUS", 0.2, "unsupported statuses"),
        ("SL_FIRST", 1.0 - 2e-9, "below 1R"),
        ("TP_FIRST", 1.0 + 2e-9, "at/above 1R"),
        ("SL_FIRST", np.nan, "finite and non-negative"),
        ("NO_BARRIER_HIT", -0.1, "finite and non-negative"),
    ],
)
def test_pr002_invalid_status_or_target_fails_closed(
    status: str, adverse_excursion: float, message: str
) -> None:
    frame = pd.DataFrame(
        [{"label_status": status, "adverse_excursion_r": adverse_excursion}]
    )

    with pytest.raises(ValueError, match=message):
        add_stop_touch_target(frame)


def test_pr002_event_metadata_preserves_h10_censoring_and_inclusive_path_boundary() -> None:
    sessions = pd.date_range("2026-02-02", periods=PATH_RISK_V2_HORIZON + 1, freq="B")
    frame = pd.DataFrame(
        [
            {
                "date": sessions[0],
                "label_status": "NO_BARRIER_HIT",
                "first_barrier_date": pd.NaT,
                "adverse_excursion_r": 0.2,
            },
            {
                "date": sessions[0],
                "label_status": "SL_FIRST",
                "first_barrier_date": sessions[PATH_RISK_V2_HORIZON],
                "adverse_excursion_r": 1.0,
            },
            {
                "date": sessions[0],
                "label_status": "TP_FIRST",
                "first_barrier_date": sessions[1],
                "adverse_excursion_r": 0.2,
            },
        ]
    )

    result = add_competing_risk_event_metadata(frame, sessions)

    assert result["stop_touch_h10"].tolist() == [0, 1, 0]
    assert result["event_day"].tolist()[1:] == [float(PATH_RISK_V2_HORIZON), 1.0]
    assert np.isnan(result.iloc[0]["event_day"])
    assert result["event_cause"].tolist() == ["NONE", "STOP", "TP"]


@pytest.mark.parametrize(
    ("signal_date", "status", "barrier_date"),
    [
        (0, "SL_FIRST", 0),  # same-session touch is outside H1..H10
        (0, "SL_FIRST", 11),  # H11 is outside the frozen horizon
        (0, "SL_FIRST", None),  # an event requires a barrier date
        (0, "NO_BARRIER_HIT", 1),  # censored rows have no event date
        (-1, "SL_FIRST", 1),  # the signal itself must be an official session
    ],
)
def test_pr002_event_metadata_rejects_path_boundary_and_censoring_mismatches(
    signal_date: int, status: str, barrier_date: int | None
) -> None:
    sessions = pd.date_range("2026-02-02", periods=12, freq="B")
    frame = pd.DataFrame(
        [
            {
                "date": sessions[signal_date] if signal_date >= 0 else sessions[0] - pd.Timedelta(days=1),
                "label_status": status,
                "first_barrier_date": pd.NaT if barrier_date is None else sessions[barrier_date],
                "adverse_excursion_r": 1.0 if status == "SL_FIRST" else 0.2,
            }
        ]
    )

    with pytest.raises(ValueError):
        add_competing_risk_event_metadata(frame, sessions)


def test_pr002_frozen_feature_order_and_model_contract_excludes_forbidden_inputs() -> None:
    model = build_pr002_model()
    preprocess = model.named_steps["preprocess"]
    imputer_pipeline = preprocess.transformers[0][1]
    imputer = imputer_pipeline.named_steps["impute"]
    estimator = model.named_steps["model"]

    assert len(PATH_RISK_V2_FEATURE_COLUMNS) == 33
    assert tuple(preprocess.transformers[0][2]) == PATH_RISK_V2_FEATURE_COLUMNS
    feature_order_payload = json.dumps(
        list(PATH_RISK_V2_FEATURE_COLUMNS), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    assert hashlib.sha256(feature_order_payload).hexdigest() == PATH_RISK_V2_FEATURE_ORDER_SHA256

    forbidden = {
        "ticker",
        "date",
        "Open",
        "label_status",
        "first_barrier_date",
        "adverse_excursion_r",
        "stop_touch_h10",
        "alpha_score",
        "alpha_probability",
    }
    assert forbidden.isdisjoint(PATH_RISK_V2_FEATURE_COLUMNS)
    assert not any("open" in column.lower() for column in PATH_RISK_V2_FEATURE_COLUMNS)
    assert preprocess.remainder == "drop"
    assert tuple(imputer_pipeline.named_steps) == ("impute",)
    assert isinstance(imputer, SimpleImputer)
    assert imputer.get_params()["strategy"] == "median"
    assert imputer.get_params()["add_indicator"] is True
    assert imputer.get_params()["keep_empty_features"] is True

    assert isinstance(estimator, HistGradientBoostingClassifier)
    assert {
        "learning_rate": estimator.get_params()["learning_rate"],
        "max_iter": estimator.get_params()["max_iter"],
        "max_leaf_nodes": estimator.get_params()["max_leaf_nodes"],
        "l2_regularization": estimator.get_params()["l2_regularization"],
        "random_state": estimator.get_params()["random_state"],
    } == {
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 31,
        "l2_regularization": 1.0,
        "random_state": 42,
    }


def test_pr002_training_only_median_imputation_handles_missing_train_and_score_values() -> None:
    train = _synthetic_labels(missing_first_at=2)
    target = add_stop_touch_target(train)["stop_touch_h10"].to_numpy(dtype=int)
    feature = PATH_RISK_V2_FEATURE_COLUMNS[0]
    expected_median = float(np.nanmedian(train[feature].to_numpy(dtype=float)))

    model = build_pr002_model()
    model.fit(train[list(PATH_RISK_V2_FEATURE_COLUMNS)], target)

    imputer = model.named_steps["preprocess"].transformers_[0][1].named_steps["impute"]
    assert imputer.statistics_[0] == expected_median

    score = _synthetic_score_frame()
    score.loc[0, feature] = np.nan
    score.loc[1, feature] = 999_999.0
    prediction = predict_pr002_probability(model, score)
    assert np.isfinite(prediction).all()
    assert ((prediction >= 0.0) & (prediction <= 1.0)).all()


def test_pr002_probability_is_bounded_and_repeated_fit_is_deterministic() -> None:
    train = _synthetic_labels()
    target = add_stop_touch_target(train)["stop_touch_h10"].to_numpy(dtype=int)
    features = train[list(PATH_RISK_V2_FEATURE_COLUMNS)]
    score = _synthetic_score_frame()

    first = build_pr002_model()
    second = build_pr002_model()
    first.fit(features, target)
    second.fit(features, target)
    first_prediction = predict_pr002_probability(first, score)
    second_prediction = predict_pr002_probability(second, score)

    assert np.isfinite(first_prediction).all()
    assert ((first_prediction >= 0.0) & (first_prediction <= 1.0)).all()
    np.testing.assert_array_equal(first_prediction, second_prediction)


def test_pr002_forbidden_columns_cannot_change_probability_output() -> None:
    train = _synthetic_labels()
    target = add_stop_touch_target(train)["stop_touch_h10"].to_numpy(dtype=int)
    model = build_pr002_model().fit(train[list(PATH_RISK_V2_FEATURE_COLUMNS)], target)
    base_score = _synthetic_score_frame()
    contaminated_score = base_score.copy()
    contaminated_score["Open"] = np.linspace(1.0, 10_000.0, len(base_score))
    contaminated_score["ticker"] = ["FORBIDDEN"] * len(base_score)
    contaminated_score["alpha_score"] = np.linspace(-100.0, 100.0, len(base_score))
    contaminated_score["alpha_probability"] = np.linspace(0.0, 1.0, len(base_score))
    contaminated_score["label_status"] = ["SL_FIRST"] * len(base_score)
    contaminated_score["stop_touch_h10"] = 1

    base_prediction = predict_pr002_probability(model, base_score)
    contaminated_prediction = predict_pr002_probability(model, contaminated_score)

    np.testing.assert_array_equal(base_prediction, contaminated_prediction)
