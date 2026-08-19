from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_v4x_last_mile_support_selection.py"


def source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_last_mile_audit_parses_and_pins_consumed_artifacts() -> None:
    body = source()
    ast.parse(body)
    assert "05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef" in body
    assert "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76" in body
    assert "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a" in body


def test_last_mile_audit_is_read_only_and_outcome_bounded() -> None:
    body = source()
    forbidden = (
        "fit_v4_head(",
        "score_v4_head(",
        ".fit(",
        "fetch_stock_summary_snapshot",
        "fetch_index_summary_snapshot",
        "requests.get",
        "yfinance",
        "sync_forward_calendar",
        "materialize_v4_target_ledger(",
    )
    for token in forbidden:
        assert token not in body
    assert '"provider_calls": False' in body
    assert '"model_fit": False' in body
    assert '"model_scored": False' in body
    assert '"protected_forward_accessed": False' in body
    assert '"target_materialized": False' in body


def test_attack_a_covers_endpoint_and_strict_feature_windows() -> None:
    body = source()
    for token in (
        "exact_endpoint_5_20_60",
        "exact_feature_windows_strict",
        "exact_shift_5",
        "exact_shift_20",
        "exact_shift_13",
        "exact_shift_19",
        "exact_shift_59",
        "mean_daily_common_support_spearman_ic",
        "delta_mean_ic_vs_all_common_support",
    ):
        assert token in body


def test_attack_b_covers_multiple_selection_diagnostics() -> None:
    body = source()
    for token in (
        "pooled_observable_minus_unobservable_mean_rank",
        "mean_daily_alpha_observability_correlation",
        "mean_daily_ks_observable_vs_unobservable_alpha_rank",
        "top_decile_minus_overall_observable_rate",
        "bottom_decile_minus_overall_observable_rate",
        "target_state_breakdown",
    ):
        assert token in body
