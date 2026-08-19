from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ranking_v4_3r_support import (
    GATE_RATE,
    frozen_support_bucket_counts,
    rethreshold_per_date_support,
    support_bucket,
)


def _per_date() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session_index": [1, 2, 3],
            "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "decision_rows": [100, 100, 100],
            "h5_supported_rows": [80, 89, 95],
            "h10_supported_rows": [80, 88, 94],
            "consensus_supported_rows": [80, 85, 93],
            "h5_rate": [0.80, 0.89, 0.95],
            "h10_rate": [0.80, 0.88, 0.94],
            "consensus_rate": [0.80, 0.85, 0.93],
            "h5_eligible": [False, False, True],
            "h10_eligible": [False, False, True],
            "consensus_eligible": [False, False, True],
        }
    )


def test_ca80_rethreshold_changes_only_date_eligibility() -> None:
    source = _per_date()
    out = rethreshold_per_date_support(source)
    assert GATE_RATE == 0.80
    assert out["h5_eligible"].tolist() == [True, True, True]
    assert out["h10_eligible"].tolist() == [True, True, True]
    assert out["consensus_eligible"].tolist() == [True, True, True]
    for column in (
        "decision_rows",
        "h5_supported_rows",
        "h10_supported_rows",
        "consensus_supported_rows",
        "h5_rate",
        "h10_rate",
        "consensus_rate",
    ):
        assert out[column].tolist() == source[column].tolist()


def test_rethreshold_rejects_stored_rate_mismatch() -> None:
    source = _per_date()
    source.loc[0, "consensus_rate"] = 0.81
    with pytest.raises(RuntimeError, match="V4_3R_STORED_RATE_MISMATCH:consensus"):
        rethreshold_per_date_support(source)


def test_support_buckets_keep_old_90_reference_visible() -> None:
    assert support_bucket(0.7999) == "below_0.80"
    assert support_bucket(0.80) == "0.80_to_below_0.90"
    assert support_bucket(0.8999) == "0.80_to_below_0.90"
    assert support_bucket(0.90) == "at_least_0.90"


def test_frozen_bucket_counts_require_exact_600_identity() -> None:
    per_date = pd.DataFrame(
        {
            "session_index": range(600),
            "date": pd.date_range("2020-01-01", periods=600, freq="D"),
            "consensus_rate": [0.85] * 300 + [0.95] * 300,
        }
    )
    folds = per_date[["session_index", "date"]].copy()
    counts = frozen_support_bucket_counts(per_date, folds)
    assert counts == {
        "below_0.80": 0,
        "0.80_to_below_0.90": 300,
        "at_least_0.90": 300,
    }
