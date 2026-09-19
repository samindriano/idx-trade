from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.alpha_challenger_effort_result_v1 import (
    FEATURE_COLUMNS,
    build_effort_result_features,
)


def _frame(rows: int = 25) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "ticker": ["BBCA"] * rows,
            "date": dates,
            "open": [100.0 + i for i in range(rows)],
            "high": [102.0 + i for i in range(rows)],
            "low": [99.0 + i for i in range(rows)],
            "close": [101.0 + i for i in range(rows)],
            "volume": [1000.0 + 20.0 * i for i in range(rows)],
        }
    )


def test_features_are_causal_and_history_is_explicit() -> None:
    base = _frame()
    first = build_effort_result_features(base)
    changed = base.copy()
    changed.loc[24, "high"] = 1_000_000.0
    changed.loc[24, "volume"] = 1.0
    second = build_effort_result_features(changed)
    comparable = first.loc[first["date"] < base["date"].iloc[-1], ["date", *FEATURE_COLUMNS]]
    changed_comparable = second.loc[second["date"] < base["date"].iloc[-1], ["date", *FEATURE_COLUMNS]]
    pd.testing.assert_frame_equal(comparable.reset_index(drop=True), changed_comparable.reset_index(drop=True))
    assert not first.loc[first["history_ready"], "effort_signed_body"].isna().all()


def test_outcome_like_columns_are_rejected() -> None:
    frame = _frame()
    frame["binary_target"] = 0
    with pytest.raises(ValueError, match="outcome-like"):
        build_effort_result_features(frame)


def test_duplicate_keys_and_invalid_ohlc_fail_closed() -> None:
    duplicate = pd.concat([_frame(2), _frame(1)], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        build_effort_result_features(duplicate)

    invalid = _frame(2)
    invalid.loc[0, "low"] = 105.0
    with pytest.raises(ValueError, match="invalid OHLCV"):
        build_effort_result_features(invalid)


def test_corporate_action_integrity_must_be_verified() -> None:
    frame = _frame()
    frame["corporate_action_integrity_verified"] = True
    frame.loc[0, "corporate_action_integrity_verified"] = False
    with pytest.raises(ValueError, match="corporate-action"):
        build_effort_result_features(frame)


def test_missing_open_is_preserved_as_missing_and_flagged() -> None:
    frame = _frame()
    frame["open_available"] = True
    frame.loc[0, "open"] = float("nan")
    result = build_effort_result_features(frame)
    assert bool(result.loc[0, "open_usable"]) is False
    assert bool(result.loc[0, "open_metadata_mismatch"]) is True
    assert pd.isna(result.loc[0, "effort_signed_body"])
