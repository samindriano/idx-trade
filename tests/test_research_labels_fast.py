import numpy as np
import pandas as pd
import pytest

from idx_trade.research_labels import BarrierLabelConfig, build_first_touch_labels
from idx_trade.research_labels_fast import (
    build_first_touch_labels_fast,
    build_first_touch_labels_multi_horizon_fast,
)


COMPARE_COLUMNS = [
    "ticker",
    "signal_date",
    "signal_session_index",
    "signal_reference_close",
    "atr",
    "horizon",
    "sl_atr_multiple",
    "reward_risk",
    "tp_level",
    "sl_level",
    "label_status",
    "binary_target",
    "first_barrier_date",
    "path_complete",
    "mfe_h",
    "mae_h",
    "normalized_close_return_h",
    "research_r_h",
    "unresolved_date",
]


def _panel(periods: int = 45, ticker: str = "TEST") -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    return pd.DataFrame(
        {
            "ticker": ticker,
            "date": dates,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000.0,
            "regular_market_value": 2_000_000_000.0,
        }
    )


def _assert_equivalent(left: pd.DataFrame, right: pd.DataFrame) -> None:
    a = left[COMPARE_COLUMNS].sort_values(["signal_date", "ticker"]).reset_index(drop=True)
    b = right[COMPARE_COLUMNS].sort_values(["signal_date", "ticker"]).reset_index(drop=True)
    assert len(a) == len(b)
    for column in COMPARE_COLUMNS:
        if column in {
            "signal_reference_close",
            "atr",
            "sl_atr_multiple",
            "reward_risk",
            "tp_level",
            "sl_level",
            "binary_target",
            "mfe_h",
            "mae_h",
            "normalized_close_return_h",
            "research_r_h",
        }:
            av = pd.to_numeric(a[column], errors="coerce").to_numpy(dtype=float)
            bv = pd.to_numeric(b[column], errors="coerce").to_numpy(dtype=float)
            assert np.allclose(av, bv, equal_nan=True, rtol=1e-12, atol=1e-12), column
        elif column in {"signal_date", "first_barrier_date", "unresolved_date"}:
            av = pd.to_datetime(a[column], errors="coerce").to_numpy(dtype="datetime64[ns]")
            bv = pd.to_datetime(b[column], errors="coerce").to_numpy(dtype="datetime64[ns]")
            assert np.array_equal(av, bv, equal_nan=True), column
        else:
            assert a[column].tolist() == b[column].tolist(), column


def test_fast_engine_matches_legacy_tp_sl_ambiguous_and_no_hit() -> None:
    panel = _panel()
    panel.loc[14, "high"] = 104.0  # TP for signal row 13
    panel.loc[17, "low"] = 97.0
    panel.loc[20, "high"] = 104.0
    panel.loc[20, "low"] = 97.0
    calendar = panel["date"].copy()
    legacy = build_first_touch_labels(panel, calendar, config=BarrierLabelConfig(horizon=10))
    fast = build_first_touch_labels_fast(panel, calendar, config=BarrierLabelConfig(horizon=10))
    _assert_equivalent(legacy, fast)


def test_fast_engine_matches_legacy_missing_future_and_horizon_end() -> None:
    full = _panel(periods=35)
    calendar = full["date"].copy()
    panel = full[~full["date"].eq(full.loc[17, "date"])].copy()
    legacy = build_first_touch_labels(panel, calendar, config=BarrierLabelConfig(horizon=10))
    fast = build_first_touch_labels_fast(panel, calendar, config=BarrierLabelConfig(horizon=10))
    _assert_equivalent(legacy, fast)


def test_fast_engine_matches_legacy_on_two_tickers_and_multiple_horizons() -> None:
    a = _panel(periods=50, ticker="AAA")
    b = _panel(periods=50, ticker="BBB")
    b["high"] = 102.0
    b["low"] = 98.0
    panel = pd.concat([a, b], ignore_index=True)
    calendar = a["date"].copy()

    outputs = build_first_touch_labels_multi_horizon_fast(panel, calendar, horizons=(5, 10, 20))
    for horizon in (5, 10, 20):
        legacy = build_first_touch_labels(panel, calendar, config=BarrierLabelConfig(horizon=horizon))
        _assert_equivalent(legacy, outputs[horizon])


def test_fast_engine_matches_legacy_with_signal_and_future_bounds() -> None:
    panel = _panel(periods=45)
    calendar = panel["date"].copy()
    legacy = build_first_touch_labels(
        panel,
        calendar,
        config=BarrierLabelConfig(horizon=10),
        max_signal_session_index=25,
        max_future_session_index=35,
    )
    fast = build_first_touch_labels_fast(
        panel,
        calendar,
        config=BarrierLabelConfig(horizon=10),
        max_signal_session_index=25,
        max_future_session_index=35,
    )
    _assert_equivalent(legacy, fast)


def test_fast_engine_preserves_access_boundary_failure() -> None:
    panel = _panel(periods=35)
    with pytest.raises(RuntimeError, match="future-session access boundary"):
        build_first_touch_labels_fast(
            panel,
            panel["date"],
            config=BarrierLabelConfig(horizon=10),
            max_signal_session_index=20,
            max_future_session_index=20,
        )
