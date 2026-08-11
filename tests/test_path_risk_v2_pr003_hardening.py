from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.path_risk_v2 import (
    CR_CONTINUE,
    CR_FEATURE_COLUMNS,
    CR_HORIZON_COLUMN,
    CR_STOP,
    CR_TP,
    PATH_RISK_V2_FEATURE_COLUMNS,
    PATH_RISK_V2_HORIZON,
    add_competing_risk_event_metadata,
    build_pr003_model,
    expand_competing_risk_training,
    score_pr003_cumulative_risk,
)
from idx_trade.ranking_v3_structure_lite import V3_B_FEATURE_COLUMNS


def _features(value: float) -> dict[str, float]:
    return {column: value for column in PATH_RISK_V2_FEATURE_COLUMNS}


def _row(
    *,
    marker: float,
    signal_date: pd.Timestamp,
    status: str,
    barrier_date: pd.Timestamp | None,
) -> dict[str, object]:
    adverse_excursion = 1.2 if status in {"SL_FIRST", "AMBIGUOUS_SAME_BAR"} else 0.2
    return {
        "ticker": f"T{int(marker):03d}",
        "date": signal_date,
        "label_status": status,
        "first_barrier_date": barrier_date,
        "adverse_excursion_r": adverse_excursion,
        **_features(marker),
    }


def _expanded_mixed_fixture() -> tuple[pd.DatetimeIndex, pd.DataFrame, pd.DataFrame]:
    sessions = pd.date_range("2026-01-02", periods=12, freq="B")
    frame = pd.DataFrame(
        [
            _row(
                marker=1,
                signal_date=sessions[0],
                status="TP_FIRST",
                barrier_date=sessions[1],
            ),
            _row(
                marker=5,
                signal_date=sessions[0],
                status="SL_FIRST",
                barrier_date=sessions[5],
            ),
            _row(
                marker=10,
                signal_date=sessions[0],
                status="AMBIGUOUS_SAME_BAR",
                barrier_date=sessions[10],
            ),
            _row(
                marker=20,
                signal_date=sessions[0],
                status="NO_BARRIER_HIT",
                barrier_date=None,
            ),
        ]
    )
    enriched = add_competing_risk_event_metadata(frame, sessions)
    return sessions, enriched, expand_competing_risk_training(enriched)


@pytest.mark.parametrize(
    ("status", "event_step", "expected_cause", "expected_target"),
    [
        ("TP_FIRST", 1, "TP", CR_TP),
        ("TP_FIRST", 5, "TP", CR_TP),
        ("TP_FIRST", 10, "TP", CR_TP),
        ("SL_FIRST", 1, "STOP", CR_STOP),
        ("SL_FIRST", 5, "STOP", CR_STOP),
        ("SL_FIRST", 10, "STOP", CR_STOP),
    ],
)
def test_first_barrier_event_is_emitted_once_at_its_horizon(
    status: str,
    event_step: int,
    expected_cause: str,
    expected_target: int,
) -> None:
    sessions = pd.date_range("2026-01-02", periods=12, freq="B")
    frame = pd.DataFrame(
        [
            _row(
                marker=100 + event_step,
                signal_date=sessions[0],
                status=status,
                barrier_date=sessions[event_step],
            ),
            _row(
                marker=999,
                signal_date=sessions[0],
                status="NO_BARRIER_HIT",
                barrier_date=None,
            ),
        ]
    )

    enriched = add_competing_risk_event_metadata(frame, sessions)
    event = enriched.iloc[0]
    assert event["event_day"] == float(event_step)
    assert event["event_cause"] == expected_cause

    expanded = expand_competing_risk_training(enriched)
    event_rows = expanded[expanded[PATH_RISK_V2_FEATURE_COLUMNS[0]].eq(100 + event_step)]
    assert event_rows[CR_HORIZON_COLUMN].tolist() == list(range(1, event_step + 1))
    assert event_rows["cr_target"].iloc[:-1].tolist() == [CR_CONTINUE] * (event_step - 1)
    assert event_rows["cr_target"].iloc[-1] == expected_target
    assert not (event_rows["cr_target"].eq(expected_target).iloc[:-1]).any()


def test_ambiguous_same_bar_uses_conservative_stop_event_convention() -> None:
    sessions = pd.date_range("2026-01-02", periods=12, freq="B")
    frame = pd.DataFrame(
        [
            _row(
                marker=7,
                signal_date=sessions[0],
                status="AMBIGUOUS_SAME_BAR",
                barrier_date=sessions[3],
            ),
            _row(
                marker=8,
                signal_date=sessions[0],
                status="TP_FIRST",
                barrier_date=sessions[1],
            ),
        ]
    )
    enriched = add_competing_risk_event_metadata(frame, sessions)
    assert enriched.loc[0, "event_cause"] == "STOP"
    expanded = expand_competing_risk_training(enriched)
    ambiguous = expanded[expanded[PATH_RISK_V2_FEATURE_COLUMNS[0]].eq(7)]
    assert ambiguous["cr_target"].tolist() == [CR_CONTINUE, CR_CONTINUE, CR_STOP]


def test_censoring_is_ten_continue_rows_and_no_event_rows_follow_a_barrier() -> None:
    _, enriched, expanded = _expanded_mixed_fixture()

    censored = expanded[expanded[PATH_RISK_V2_FEATURE_COLUMNS[0]].eq(20)]
    assert len(censored) == PATH_RISK_V2_HORIZON
    assert censored[CR_HORIZON_COLUMN].tolist() == list(range(1, PATH_RISK_V2_HORIZON + 1))
    assert censored["cr_target"].eq(CR_CONTINUE).all()

    for marker, expected_length in ((1, 1), (5, 5), (10, 10)):
        event_rows = expanded[expanded[PATH_RISK_V2_FEATURE_COLUMNS[0]].eq(marker)]
        assert len(event_rows) == expected_length
        assert event_rows[CR_HORIZON_COLUMN].max() == expected_length


def test_mixed_expansion_preserves_signal_identity_by_frozen_feature_values_and_counts() -> None:
    _, enriched, expanded = _expanded_mixed_fixture()
    marker_column = PATH_RISK_V2_FEATURE_COLUMNS[0]
    expected = {
        1.0: (1, [CR_TP]),
        5.0: (5, [CR_CONTINUE] * 4 + [CR_STOP]),
        10.0: (10, [CR_CONTINUE] * 9 + [CR_STOP]),
        20.0: (10, [CR_CONTINUE] * 10),
    }

    assert enriched["event_cause"].tolist() == ["TP", "STOP", "STOP", "NONE"]
    assert tuple(expanded.columns) == (*PATH_RISK_V2_FEATURE_COLUMNS, CR_HORIZON_COLUMN, "cr_target")
    assert set(expanded[CR_HORIZON_COLUMN]) == set(range(1, PATH_RISK_V2_HORIZON + 1))
    assert pd.api.types.is_integer_dtype(expanded[CR_HORIZON_COLUMN])
    assert expanded[CR_HORIZON_COLUMN].between(1, PATH_RISK_V2_HORIZON).all()

    for marker, (expected_count, expected_targets) in expected.items():
        rows = expanded[expanded[marker_column].eq(marker)]
        assert len(rows) == expected_count
        assert rows["cr_target"].tolist() == expected_targets


def test_pr003_candidate_columns_are_exactly_frozen_features_plus_horizon() -> None:
    assert tuple(PATH_RISK_V2_FEATURE_COLUMNS) == tuple(V3_B_FEATURE_COLUMNS)
    assert len(PATH_RISK_V2_FEATURE_COLUMNS) == 33
    assert tuple(CR_FEATURE_COLUMNS) == (*PATH_RISK_V2_FEATURE_COLUMNS, CR_HORIZON_COLUMN)

    _, _, expanded = _expanded_mixed_fixture()
    assert tuple(expanded.columns) == (*CR_FEATURE_COLUMNS, "cr_target")
    model_columns = tuple(build_pr003_model().named_steps["preprocess"].transformers[0][2])
    assert model_columns == tuple(CR_FEATURE_COLUMNS)
    assert "ticker" not in expanded.columns
    assert "date" not in expanded.columns
    assert "label_status" not in expanded.columns
    assert "first_barrier_date" not in expanded.columns


class _HorizonProbabilityModel:
    classes_ = np.array([CR_TP, CR_CONTINUE, CR_STOP], dtype=int)

    def __init__(self) -> None:
        self.seen_columns: tuple[str, ...] | None = None
        self.seen_horizons: np.ndarray | None = None

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        self.seen_columns = tuple(frame.columns)
        self.seen_horizons = frame[CR_HORIZON_COLUMN].to_numpy(dtype=int)
        horizon = self.seen_horizons.astype(float)
        p_stop = 0.03 + 0.002 * horizon
        p_tp = 0.01 + 0.001 * horizon
        p_continue = 1.0 - p_stop - p_tp
        # Deliberately return a non-sorted class order; scoring must use classes_.
        return np.column_stack([p_tp, p_continue, p_stop])


def _expected_cif_by_horizon() -> list[tuple[float, float, float]]:
    survival = 1.0
    stop = 0.0
    tp = 0.0
    expected: list[tuple[float, float, float]] = []
    for horizon in range(1, PATH_RISK_V2_HORIZON + 1):
        p_stop = 0.03 + 0.002 * horizon
        p_tp = 0.01 + 0.001 * horizon
        p_continue = 1.0 - p_stop - p_tp
        stop += survival * p_stop
        tp += survival * p_tp
        survival *= p_continue
        expected.append((stop, tp, survival))
    return expected


def test_cif_recursion_is_causal_bounded_and_mass_conserving_at_every_horizon() -> None:
    model = _HorizonProbabilityModel()
    frame = pd.DataFrame(
        [
            {"ticker": "AAA", "date": pd.Timestamp("2026-01-02"), **_features(1.0)},
            {"ticker": "BBB", "date": pd.Timestamp("2026-01-02"), **_features(2.0)},
        ]
    )

    scored = score_pr003_cumulative_risk(
        type("Model", (), {"named_steps": {"model": model}, "predict_proba": model.predict_proba})(),
        frame,
    )
    expected = _expected_cif_by_horizon()

    assert model.seen_columns == tuple(CR_FEATURE_COLUMNS)
    assert model.seen_horizons is not None
    assert model.seen_horizons.tolist() == list(range(1, 11)) * 2
    for stop, tp, survival in expected:
        assert 0.0 <= stop <= 1.0
        assert 0.0 <= tp <= 1.0
        assert 0.0 <= survival <= 1.0
        assert stop + tp + survival == pytest.approx(1.0, abs=1e-12)

    for row in scored.itertuples(index=False):
        assert row.stop_probability_h3 == pytest.approx(expected[2][0])
        assert row.stop_probability_h5 == pytest.approx(expected[4][0])
        assert row.stop_probability_h10 == pytest.approx(expected[9][0])
        assert row.tp_probability_h10 == pytest.approx(expected[9][1])
        assert row.survival_probability_h10 == pytest.approx(expected[9][2])
        assert row.mass_error_h10 == pytest.approx(0.0, abs=1e-12)


class _InvalidMassModel:
    classes_ = np.array([CR_CONTINUE, CR_STOP, CR_TP], dtype=int)

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        probabilities = np.tile(np.array([[0.8, 0.1, 0.1]], dtype=float), (len(frame), 1))
        probabilities[5, 0] = 0.7
        return probabilities


def test_cif_rejects_non_unit_conditional_probability_mass() -> None:
    frame = pd.DataFrame(
        [{"ticker": "AAA", "date": pd.Timestamp("2026-01-02"), **_features(1.0)}]
    )
    model = _InvalidMassModel()
    wrapped = type(
        "Model",
        (),
        {"named_steps": {"model": model}, "predict_proba": model.predict_proba},
    )()
    with pytest.raises(RuntimeError, match="conditional probability mass"):
        score_pr003_cumulative_risk(wrapped, frame)


def test_repeated_pr003_fit_and_prediction_are_deterministic_under_seed_42() -> None:
    sessions = pd.date_range("2026-01-02", periods=12, freq="B")
    rows: list[dict[str, object]] = []
    for index in range(30):
        status = ("SL_FIRST", "TP_FIRST", "NO_BARRIER_HIT")[index % 3]
        event_step = (index % 10) + 1
        rows.append(
            _row(
                marker=float(index + 1),
                signal_date=sessions[0],
                status=status,
                barrier_date=None if status == "NO_BARRIER_HIT" else sessions[event_step],
            )
        )
    enriched = add_competing_risk_event_metadata(pd.DataFrame(rows), sessions)
    expanded = expand_competing_risk_training(enriched)
    target = expanded.pop("cr_target").to_numpy(dtype=int)

    first = build_pr003_model()
    second = build_pr003_model()
    assert first.named_steps["model"].get_params()["random_state"] == 42
    assert second.named_steps["model"].get_params()["random_state"] == 42
    first.fit(expanded, target)
    second.fit(expanded, target)
    np.testing.assert_array_equal(first.predict_proba(expanded), second.predict_proba(expanded))


@pytest.mark.parametrize(
    ("signal_index", "barrier_date"),
    [
        (3, pd.Timestamp("2026-01-05")),  # before signal on 2026-01-07
        (3, pd.Timestamp("2026-01-07")),  # equal to signal
        (0, pd.Timestamp("2026-01-19")),  # H11, outside H1..H10
        (3, pd.Timestamp("2026-01-10")),  # Saturday, not an official session
    ],
)
def test_malformed_barrier_timing_fails_closed(
    signal_index: int, barrier_date: pd.Timestamp
) -> None:
    sessions = pd.date_range("2026-01-02", periods=12, freq="B")
    frame = pd.DataFrame(
        [
            _row(
                marker=1,
                signal_date=sessions[signal_index],
                status="SL_FIRST",
                barrier_date=barrier_date,
            )
        ]
    )
    with pytest.raises(ValueError):
        add_competing_risk_event_metadata(frame, sessions)
