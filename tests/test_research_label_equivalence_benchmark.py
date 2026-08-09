from __future__ import annotations

import pandas as pd

from idx_trade.research_label_equivalence_benchmark import compare_label_frames
from idx_trade.research_labels import BarrierLabelConfig, build_first_touch_labels
from idx_trade.research_labels_fast import build_first_touch_labels_fast


def _panel() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=35)
    frame = pd.DataFrame(
        {
            "ticker": "AAA",
            "date": dates,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000.0,
        }
    )
    frame.loc[14, "high"] = 104.0
    frame.loc[20, "low"] = 97.0
    return frame


def test_equivalence_comparator_accepts_fast_legacy_semantic_match() -> None:
    panel = _panel()
    calendar = panel["date"]
    legacy = build_first_touch_labels(panel, calendar, config=BarrierLabelConfig(horizon=10))
    fast = build_first_touch_labels_fast(panel, calendar, config=BarrierLabelConfig(horizon=10))
    comparison = compare_label_frames(legacy, fast)
    assert comparison["equal"]
    assert comparison["row_count_equal"]


def test_equivalence_comparator_rejects_semantic_difference() -> None:
    panel = _panel()
    calendar = panel["date"]
    legacy = build_first_touch_labels(panel, calendar, config=BarrierLabelConfig(horizon=10))
    fast = build_first_touch_labels_fast(panel, calendar, config=BarrierLabelConfig(horizon=10))
    fast = fast.copy()
    fast.loc[fast.index[0], "label_status"] = "BROKEN"
    comparison = compare_label_frames(legacy, fast)
    assert not comparison["equal"]
    assert not comparison["exact_columns"]["label_status"]
