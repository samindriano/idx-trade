from __future__ import annotations

import pandas as pd

from idx_trade.tradingview_v2_1_fidelity_forensic import (
    add_hlc_comparisons,
    adjudicate_2022,
    concentration_table,
    end_cohort,
    hlc_mismatch_pattern,
    three_way_classification,
)


def test_three_way_classification_distinguishes_oracle_and_provider_conflicts() -> None:
    frame = pd.DataFrame(
        [
            {"tv_high": 10, "tv_low": 8, "tv_close": 9, "canonical_high": 10, "canonical_low": 8, "canonical_close": 9, "idx_high": 10, "idx_low": 8, "idx_close": 9},
            {"tv_high": 10, "tv_low": 8, "tv_close": 9, "canonical_high": 11, "canonical_low": 8, "canonical_close": 9, "idx_high": 10, "idx_low": 8, "idx_close": 9},
            {"tv_high": 11, "tv_low": 8, "tv_close": 9, "canonical_high": 10, "canonical_low": 8, "canonical_close": 9, "idx_high": 10, "idx_low": 8, "idx_close": 9},
            {"tv_high": 10, "tv_low": 8, "tv_close": 9, "canonical_high": 10, "canonical_low": 8, "canonical_close": 9, "idx_high": 11, "idx_low": 8, "idx_close": 9},
        ]
    )
    assert three_way_classification(frame).tolist() == [
        "ALL_AGREE",
        "TV_IDX_AGREE_CANONICAL_DIFF",
        "CANONICAL_IDX_AGREE_TV_DIFF",
        "TV_CANONICAL_AGREE_IDX_DIFF",
    ]


def test_mismatch_pattern_and_exact_flags() -> None:
    frame = pd.DataFrame(
        [
            {"tv_high": 10, "tv_low": 8, "tv_close": 9, "canonical_high": 11, "canonical_low": 8, "canonical_close": 9},
            {"tv_high": 10, "tv_low": 8, "tv_close": 9, "canonical_high": 11, "canonical_low": 7, "canonical_close": 8},
        ]
    )
    result = add_hlc_comparisons(
        frame,
        left_prefix="tv_",
        right_prefix="canonical_",
        result_prefix="tv_canonical",
    )
    assert result["tv_canonical_hlc_exact"].tolist() == [False, False]
    assert hlc_mismatch_pattern(frame, left_prefix="tv_", right_prefix="canonical_").tolist() == ["H", "HLC"]


def test_end_cohort_separates_window_end_from_historical_requests() -> None:
    assert end_cohort("2026-07-31", None) == "WINDOW_END"
    assert end_cohort("2022-06-30", "2022-06-30") == "HISTORICAL_END_2022_OR_EARLIER"
    assert end_cohort("2024-04-01", "2024-04-01") == "HISTORICAL_END_2023_2024"


def test_concentration_table_is_sorted_and_cumulative() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "BBB", "BBB"],
            "mismatch": [True, True, True, False, False],
        }
    )
    result = concentration_table(frame, mismatch_column="mismatch")
    assert result.iloc[0]["ticker"] == "AAA"
    assert int(result.iloc[0]["mismatch_rows"]) == 2
    assert float(result.iloc[-1]["cumulative_mismatch_share"]) == 1.0


def test_adjudication_supports_selection_bias_only_when_controls_are_clean() -> None:
    controls = pd.DataFrame(
        {
            "session_date": ["2022-01-03"] * 20,
            "tv_canonical_hlc_exact": [True] * 20,
            "tv_idx_hlc_exact": [True] * 20,
            "three_way_class": ["ALL_AGREE"] * 20,
        }
    )
    legacy = pd.DataFrame(
        {
            "tv_canonical_hlc_exact": [False] * 8 + [True] * 2 + [False] + [True] * 9,
            "end_cohort": ["HISTORICAL_END_2022_OR_EARLIER"] * 10 + ["WINDOW_END"] * 10,
            "three_way_class": ["ALL_DIFFER"] * 20,
        }
    )
    result = adjudicate_2022(controls, legacy)
    assert result["verdict"] == "2022_APPARENT_ANOMALY_SUPPORT_SELECTION_SUPPORTED"
    assert result["network_calls"] == 0
    assert result["path_risk_authorized"] is False


def test_adjudication_prefers_canonical_conflict_when_idx_agrees_with_tv() -> None:
    controls = pd.DataFrame(
        {
            "session_date": ["2022-01-03"] * 20,
            "tv_canonical_hlc_exact": [True] * 20,
            "tv_idx_hlc_exact": [True] * 20,
            "three_way_class": ["ALL_AGREE"] * 20,
        }
    )
    legacy = pd.DataFrame(
        {
            "tv_canonical_hlc_exact": [False] * 8 + [True] * 2,
            "end_cohort": ["HISTORICAL_END_2022_OR_EARLIER"] * 10,
            "three_way_class": ["TV_IDX_AGREE_CANONICAL_DIFF"] * 8 + ["ALL_AGREE"] * 2,
        }
    )
    result = adjudicate_2022(controls, legacy)
    assert result["verdict"] == "2022_APPARENT_ANOMALY_CANONICAL_ORACLE_CONFLICT_SUPPORTED"
