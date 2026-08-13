from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.ranking_v3_forward_runtime import (
    V3_FINAL_FEATURE_ORDER_SHA256,
    _join_structure_onto_exact_rows,
    build_outcome_blind_v3_forward_features,
)
from idx_trade.ranking_v3_structure_lite import V3_B_FEATURE_COLUMNS, _feature_order_hash
from idx_trade.research_v3_structure_lite import STRUCTURE_LITE_FEATURE_COLUMNS


def _synthetic_signal_panel(*, sessions: int = 100) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    dates = pd.date_range("2026-04-01", periods=sessions, freq="B")
    rows: list[dict[str, object]] = []
    for ticker_index, ticker in enumerate(("AAA", "BBB", "CCC", "DDD", "EEE")):
        for index, date in enumerate(dates):
            drift = 0.25 + ticker_index * 0.03
            wave = np.sin(index / (4.0 + ticker_index)) * (0.5 + ticker_index * 0.05)
            close = 100.0 + ticker_index * 8.0 + index * drift + wave
            high = close + 1.5 + (index % 3) * 0.1
            low = close - 1.4 - (index % 2) * 0.1
            rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": 1_000_000.0 + ticker_index * 50_000.0 + index * 2_000.0,
                    "regular_market_value": 2_000_000_000.0 + ticker_index * 100_000_000.0,
                    "tradability_state": "ACTIVE",
                }
            )
    return pd.DataFrame(rows), dates


def test_final_feature_order_hash_is_frozen() -> None:
    assert len(V3_B_FEATURE_COLUMNS) == 33
    assert tuple(V3_B_FEATURE_COLUMNS[-8:]) == tuple(STRUCTURE_LITE_FEATURE_COLUMNS)
    assert _feature_order_hash(tuple(V3_B_FEATURE_COLUMNS)) == V3_FINAL_FEATURE_ORDER_SHA256


def test_structure_join_preserves_rows_and_missing_values() -> None:
    base = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": pd.to_datetime(["2026-01-05", "2026-01-05"]),
            "signal_session_index": [20, 20],
            "binary_target": [1, 0],
        }
    )
    structure = base[["ticker", "date"]].copy()
    for index, column in enumerate(STRUCTURE_LITE_FEATURE_COLUMNS):
        structure[column] = [np.nan if index == 0 else float(index), float(index + 1)]

    joined = _join_structure_onto_exact_rows(
        base,
        structure,
        require_frozen_training_facts=False,
    )
    assert len(joined) == len(base)
    assert joined[["ticker", "date", "signal_session_index", "binary_target"]].equals(base)
    assert pd.isna(joined.loc[0, STRUCTURE_LITE_FEATURE_COLUMNS[0]])


def test_structure_join_fails_on_orphan_base_row() -> None:
    base = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": pd.to_datetime(["2026-01-05", "2026-01-05"]),
            "signal_session_index": [20, 20],
            "binary_target": [1, 0],
        }
    )
    structure = base.iloc[[0]][["ticker", "date"]].copy()
    for column in STRUCTURE_LITE_FEATURE_COLUMNS:
        structure[column] = 0.0
    with pytest.raises(RuntimeError, match="orphan"):
        _join_structure_onto_exact_rows(base, structure, require_frozen_training_facts=False)


def test_v3_forward_builder_is_outcome_blind_primary_and_post_cutoff() -> None:
    panel, dates = _synthetic_signal_panel()
    cutoff = dates[70]
    result = build_outcome_blind_v3_forward_features(
        panel,
        dates,
        listed_from={ticker: dates[0] for ticker in panel["ticker"].unique()},
        cutoff_date=cutoff,
    )
    assert not result.empty
    assert result["date"].min() > cutoff
    assert result["universe_primary_liquid"].astype(bool).all()
    assert tuple(V3_B_FEATURE_COLUMNS[-8:]) == tuple(STRUCTURE_LITE_FEATURE_COLUMNS)
    assert set(STRUCTURE_LITE_FEATURE_COLUMNS).issubset(result.columns)
    assert "binary_target" not in result.columns
    assert "label_status" not in result.columns


def test_v3_forward_builder_rejects_outcome_columns() -> None:
    panel, dates = _synthetic_signal_panel()
    panel["binary_target"] = 0
    with pytest.raises(ValueError, match="outcome columns"):
        build_outcome_blind_v3_forward_features(
            panel,
            dates,
            listed_from={ticker: dates[0] for ticker in panel["ticker"].unique()},
            cutoff_date=dates[70],
        )


def test_v3_forward_builder_rejects_non_active_signal_panel() -> None:
    panel, dates = _synthetic_signal_panel()
    panel.loc[0, "tradability_state"] = "SUSPENDED"
    with pytest.raises(ValueError, match="ACTIVE-only"):
        build_outcome_blind_v3_forward_features(
            panel,
            dates,
            listed_from={ticker: dates[0] for ticker in panel["ticker"].unique()},
            cutoff_date=dates[70],
        )


def test_v3_forward_features_are_invariant_to_appended_future_rows() -> None:
    panel, dates = _synthetic_signal_panel(sessions=105)
    cutoff = dates[70]
    early_dates = dates[:96]
    early_panel = panel[panel["date"].isin(early_dates)].copy()
    full = build_outcome_blind_v3_forward_features(
        panel,
        dates,
        listed_from={ticker: dates[0] for ticker in panel["ticker"].unique()},
        cutoff_date=cutoff,
    )
    early = build_outcome_blind_v3_forward_features(
        early_panel,
        early_dates,
        listed_from={ticker: dates[0] for ticker in panel["ticker"].unique()},
        cutoff_date=cutoff,
    )
    common = full[full["date"].isin(early["date"].unique())].copy().reset_index(drop=True)
    early = early.reset_index(drop=True)
    assert common[["ticker", "date"]].equals(early[["ticker", "date"]])
    for column in V3_B_FEATURE_COLUMNS:
        left = pd.to_numeric(common[column], errors="coerce").to_numpy(dtype=float)
        right = pd.to_numeric(early[column], errors="coerce").to_numpy(dtype=float)
        assert np.allclose(left, right, rtol=0.0, atol=1e-12, equal_nan=True), column
