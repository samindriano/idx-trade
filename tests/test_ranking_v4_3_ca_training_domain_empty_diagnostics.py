from __future__ import annotations

import pandas as pd

from idx_trade.ranking_v4_3_ca_training_domain import build_training_date_sets


def test_empty_training_domain_is_returned_for_blocked_diagnostics() -> None:
    per_date = pd.DataFrame(
        {
            "session_index": [0, 1, 2],
            "date": pd.date_range("2024-01-02", periods=3, freq="B"),
            "h5_eligible": [False, False, False],
            "h10_eligible": [False, False, False],
        }
    )
    folds = pd.DataFrame(
        {
            "fold": [1, 1, 2, 2],
            "max_training_signal_session_index": [1, 1, 2, 2],
        }
    )
    result = build_training_date_sets(per_date, folds)
    assert result.empty
    assert result.columns.tolist() == [
        "fold",
        "head",
        "session_index",
        "date",
        "max_training_signal_session_index",
    ]
