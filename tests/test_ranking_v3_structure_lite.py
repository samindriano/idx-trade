from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.ranking_v3_structure_lite import (
    MAX_DISCOVERY_SIGNAL_INDEX,
    V3_B_FEATURE_COLUMNS,
    _read_v2_discovery_subset,
    _structure_model,
    assert_discovery_fold_allowed,
)
from idx_trade.research_v2_features import V2_FULL_FEATURE_COLUMNS
from idx_trade.research_v3_structure_lite import (
    Cluster,
    Pivot,
    StructureContext,
    STRUCTURE_LITE_FEATURE_COLUMNS,
    _causal_pivots,
    _clusters_for_signal,
    _event_features,
    _touch_count,
    _volume_confirmed,
    build_structure_lite_features,
)


def test_structure_feature_order_appends_exactly_eight_after_v2() -> None:
    assert tuple(V3_B_FEATURE_COLUMNS[: len(V2_FULL_FEATURE_COLUMNS)]) == tuple(V2_FULL_FEATURE_COLUMNS)
    assert tuple(V3_B_FEATURE_COLUMNS[len(V2_FULL_FEATURE_COLUMNS) :]) == tuple(STRUCTURE_LITE_FEATURE_COLUMNS)
    assert len(V3_B_FEATURE_COLUMNS) == 33


def test_left_only_pivot_does_not_depend_on_future_append() -> None:
    sessions = np.arange(1, 8)
    high = np.array([1, 2, 3, 4, 5, 4, 3], dtype=float)
    low = np.array([5, 4, 3, 2, 1, 2, 3], dtype=float)
    atr = np.ones(7, dtype=float)
    first = _causal_pivots(sessions[:6], high[:6], low[:6], atr[:6])
    second = _causal_pivots(sessions, high, low, atr)
    first_identity = [(p.session_index, p.price, p.side) for p in first]
    second_prefix = [(p.session_index, p.price, p.side) for p in second if p.session_index <= 6]
    assert first_identity == second_prefix


def test_official_session_gap_breaks_five_session_pivot() -> None:
    sessions = np.array([1, 2, 3, 5, 6, 7], dtype=int)
    high = np.array([1, 2, 3, 10, 11, 12], dtype=float)
    low = np.ones(6, dtype=float)
    atr = np.ones(6, dtype=float)
    pivots = _causal_pivots(sessions, high, low, atr)
    assert all(p.session_index not in {5, 6, 7} for p in pivots)


def test_level_clustering_is_deterministic_connected_component() -> None:
    pivots = (
        Pivot(10, 100.0, 2.0, "HIGH", 0),
        Pivot(20, 100.8, 2.0, "HIGH", 1),
        Pivot(30, 105.0, 2.0, "HIGH", 2),
        Pivot(15, 90.0, 2.0, "LOW", 3),
    )
    by_side = {
        "HIGH": tuple(p for p in pivots if p.side == "HIGH"),
        "LOW": tuple(p for p in pivots if p.side == "LOW"),
    }
    sessions = {
        side: np.asarray([p.session_index for p in by_side[side]], dtype=int)
        for side in ("HIGH", "LOW")
    }
    result1 = _clusters_for_signal(by_side, sessions, signal_session=40)
    result2 = _clusters_for_signal(by_side, sessions, signal_session=40)
    assert result1 == result2
    high_clusters = [c for c in result1 if c.side == "HIGH"]
    assert len(high_clusters) == 2
    assert high_clusters[0].level == pytest.approx(100.4)


def test_touch_count_collapses_adjacent_sessions() -> None:
    sessions = np.arange(1, 10, dtype=int)
    high = np.full(9, 101.0)
    low = np.full(9, 99.0)
    atr = np.ones(9)
    count = _touch_count(
        level=100.0,
        signal_session=10,
        session_index=sessions,
        high=high,
        low=low,
        atr=atr,
    )
    assert count == 3.0


def test_volume_confirmation_uses_prior_baseline_only() -> None:
    sessions = np.arange(1, 22, dtype=int)
    volume = np.full(21, 100.0)
    volume[-1] = 200.0
    assert _volume_confirmed(trigger_session=21, session_index=sessions, volume=volume) == 1.0
    volume[-1] = 140.0
    assert _volume_confirmed(trigger_session=21, session_index=sessions, volume=volume) == 0.0


def test_breakout_then_retest_state_is_causal() -> None:
    sessions = np.array([1, 2, 3, 4], dtype=int)
    high = np.array([99.0, 100.0, 103.0, 102.0])
    low = np.array([98.0, 99.0, 101.0, 99.5])
    close = np.array([99.0, 100.0, 102.0, 101.5])
    volume = np.array([100.0, 100.0, 200.0, 100.0])
    atr = np.ones(4)
    resistance = Cluster("HIGH", 100.0, 1, (), 0)
    contexts = [
        StructureContext(False, None, None, np.nan, np.nan, np.nan, np.nan),
        StructureContext(True, None, resistance, np.nan, 1.0, 1.0, 0.0),
        StructureContext(True, None, resistance, np.nan, 1.0, 2.0, 0.0),
        StructureContext(True, None, resistance, np.nan, 1.0, 3.0, 0.0),
    ]
    state, _ = _event_features(
        session_index=sessions,
        high=high,
        low=low,
        close=close,
        volume=volume,
        atr=atr,
        contexts=contexts,
    )
    assert state[2] == 1.0
    assert state[3] == 2.0


def test_structure_builder_rejects_label_columns() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": ["2026-01-02"],
            "high": [10.0],
            "low": [9.0],
            "close": [9.5],
            "volume": [100.0],
            "binary_target": [1],
        }
    )
    with pytest.raises(ValueError, match="label/outcome"):
        build_structure_lite_features(
            frame,
            pd.date_range("2026-01-02", periods=10, freq="B"),
            max_signal_session_index=1,
        )


def test_structure_model_preserves_frozen_hgb_parameters() -> None:
    model = _structure_model()
    estimator = model.named_steps["model"]
    assert estimator.learning_rate == 0.05
    assert estimator.max_iter == 200
    assert estimator.max_leaf_nodes == 31
    assert estimator.l2_regularization == 1.0
    assert estimator.random_state == 42
    columns = tuple(model.named_steps["preprocess"].transformers[0][2])
    assert columns == tuple(V3_B_FEATURE_COLUMNS)


def test_v3_b_runner_hard_blocks_f5_f6() -> None:
    for name in ("V2F5", "V2F6"):
        with pytest.raises(PermissionError):
            assert_discovery_fold_allowed(name)
    for name in ("V2F1", "V2F2", "V2F3", "V2F4"):
        assert_discovery_fold_allowed(name)


def test_v2_discovery_reader_does_not_materialize_later_rows(tmp_path) -> None:
    path = tmp_path / "prepared.parquet"
    pd.DataFrame(
        {
            "signal_session_index": [10, MAX_DISCOVERY_SIGNAL_INDEX, MAX_DISCOVERY_SIGNAL_INDEX + 1],
            "x": [1, 2, 3],
        }
    ).to_parquet(path, index=False)
    result = _read_v2_discovery_subset(path)
    assert result["signal_session_index"].tolist() == [10, MAX_DISCOVERY_SIGNAL_INDEX]


def test_event_state_space_and_feature_names_have_no_open_dependency() -> None:
    assert all("open" not in name.lower() for name in STRUCTURE_LITE_FEATURE_COLUMNS)
    assert STRUCTURE_LITE_FEATURE_COLUMNS[-2:] == (
        "structure_breakout_retest_state",
        "structure_breakout_volume_confirmed",
    )
