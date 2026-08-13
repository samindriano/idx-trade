import pandas as pd
import pytest

from idx_trade.research_labels import (
    AMBIGUOUS_SAME_BAR,
    NO_BARRIER_HIT,
    SL_FIRST,
    TP_FIRST,
    UNRESOLVED_HORIZON_END,
    UNRESOLVED_PATH,
    BarrierLabelConfig,
    build_first_touch_labels,
)


def _panel(periods=35):
    dates = pd.bdate_range("2024-01-02", periods=periods)
    return pd.DataFrame(
        {
            "ticker": "TEST",
            "date": dates,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000.0,
            "regular_market_value": 2_000_000_000.0,
        }
    )


def _status(frame, signal_date):
    row = frame.loc[frame["signal_date"].eq(pd.Timestamp(signal_date))].iloc[0]
    return row


def test_primary_barrier_tp_first_and_no_open_dependency():
    panel = _panel()
    signal_date = panel.loc[13, "date"]
    panel.loc[14, "high"] = 104.0
    labels = build_first_touch_labels(panel, panel["date"], config=BarrierLabelConfig(horizon=10))
    row = _status(labels, signal_date)
    assert row["label_status"] == TP_FIRST
    assert row["binary_target"] == 1.0
    assert row["path_complete"]
    assert row["first_barrier_date"] == panel.loc[14, "date"]
    assert "open" not in labels.columns


def test_primary_barrier_sl_first():
    panel = _panel()
    signal_date = panel.loc[13, "date"]
    panel.loc[14, "low"] = 97.0
    labels = build_first_touch_labels(panel, panel["date"])
    row = _status(labels, signal_date)
    assert row["label_status"] == SL_FIRST
    assert row["binary_target"] == 0.0


def test_same_bar_touch_is_ambiguous_not_guessed():
    panel = _panel()
    signal_date = panel.loc[13, "date"]
    panel.loc[14, "high"] = 104.0
    panel.loc[14, "low"] = 97.0
    labels = build_first_touch_labels(panel, panel["date"])
    row = _status(labels, signal_date)
    assert row["label_status"] == AMBIGUOUS_SAME_BAR
    assert pd.isna(row["binary_target"])


def test_missing_official_future_bar_fails_closed():
    full = _panel()
    calendar = full["date"].copy()
    signal_date = full.loc[13, "date"]
    missing_date = full.loc[17, "date"]
    panel = full[~full["date"].eq(missing_date)].copy()
    labels = build_first_touch_labels(panel, calendar)
    row = _status(labels, signal_date)
    assert row["label_status"] == UNRESOLVED_PATH
    assert row["unresolved_date"] == missing_date
    assert not row["path_complete"]


def test_no_barrier_is_explicit_and_excursions_are_emitted_on_complete_path():
    panel = _panel()
    signal_date = panel.loc[13, "date"]
    labels = build_first_touch_labels(panel, panel["date"])
    row = _status(labels, signal_date)
    assert row["label_status"] == NO_BARRIER_HIT
    assert row["path_complete"]
    assert pd.notna(row["mfe_h"])
    assert pd.notna(row["mae_h"])
    assert pd.notna(row["normalized_close_return_h"])


def test_horizon_end_is_not_silently_dropped():
    panel = _panel(periods=20)
    labels = build_first_touch_labels(panel, panel["date"])
    signal_date = panel.loc[14, "date"]
    row = _status(labels, signal_date)
    assert row["label_status"] == UNRESOLVED_HORIZON_END


def test_development_access_bound_rejects_future_path_crossing_boundary():
    panel = _panel(periods=35)
    with pytest.raises(RuntimeError, match="future-session access boundary"):
        build_first_touch_labels(
            panel,
            panel["date"],
            max_signal_session_index=20,
            max_future_session_index=20,
        )
