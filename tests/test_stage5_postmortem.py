from __future__ import annotations

import numpy as np
import pandas as pd

from idx_trade.research_features import BASELINE_FEATURE_COLUMNS
from idx_trade.stage5_postmortem import (
    FIXED_BLOCKS,
    feature_drift_table,
    feature_target_relation_table,
    fixed_block_metrics,
    hgb_deciles_by_half,
)


def _toy_scored() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for block_name, start, _end in FIXED_BLOCKS:
        for i in range(10):
            rows.append(
                {
                    "ticker": f"T{i:02d}",
                    "date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=start - 1009),
                    "signal_session_index": start,
                    "binary_target": int(i >= 5),
                    "score_hist_gradient_boosting": float(i),
                    "half": "HOLDOUT_A" if block_name.startswith("A") else "HOLDOUT_B",
                }
            )
    return pd.DataFrame(rows)


def _toy_features() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for half, offset in (("HOLDOUT_A", 0.0), ("HOLDOUT_B", 1.0)):
        for day in range(2):
            date = pd.Timestamp("2026-01-01") + pd.Timedelta(days=day + (10 if half == "HOLDOUT_B" else 0))
            for i in range(10):
                row: dict[str, object] = {
                    "ticker": f"T{i:02d}",
                    "date": date,
                    "binary_target": int(i >= 5),
                    "half": half,
                }
                for j, feature in enumerate(BASELINE_FEATURE_COLUMNS):
                    row[feature] = float(i + j) + offset
                rows.append(row)
    return pd.DataFrame(rows)


def test_fixed_blocks_cover_frozen_h10_window_without_overlap() -> None:
    covered: list[int] = []
    for _name, start, end in FIXED_BLOCKS:
        covered.extend(range(start, end + 1))
    assert covered == list(range(1009, 1251))


def test_fixed_block_metrics_are_finite_and_keep_all_blocks() -> None:
    result = fixed_block_metrics(_toy_scored())
    assert result["block"].tolist() == ["A1", "A2", "A3", "B1", "B2", "B3"]
    assert np.isfinite(result[["pr_auc", "roc_auc", "q5_minus_q1", "top_decile_lift"]].to_numpy()).all()
    assert (result["q5_minus_q1"] > 0).all()


def test_feature_drift_reports_all_frozen_features() -> None:
    result = feature_drift_table(_toy_features())
    assert set(result["feature"]) == set(BASELINE_FEATURE_COLUMNS)
    assert np.isfinite(result["smd_b_minus_a"]).all()
    assert (result["smd_b_minus_a"] > 0).all()


def test_feature_target_relation_uses_within_date_ordering() -> None:
    result = feature_target_relation_table(_toy_features())
    assert set(result["half"]) == {"HOLDOUT_A", "HOLDOUT_B"}
    assert len(result) == 2 * len(BASELINE_FEATURE_COLUMNS)
    assert (result["within_date_rank_corr_target"] > 0).all()
    assert (result["feature_q5_minus_q1"] > 0).all()


def test_deciles_are_reported_separately_by_half() -> None:
    result = hgb_deciles_by_half(_toy_scored())
    assert set(result["half"]) == {"HOLDOUT_A", "HOLDOUT_B"}
    assert set(result["bucket"]) == set(range(1, 11))
    assert len(result) == 20
