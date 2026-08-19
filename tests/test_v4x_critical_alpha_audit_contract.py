from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKET_AUDIT = ROOT / "scripts" / "audit_v4x_frozen_market_inputs.py"
RESULT_AUDIT = ROOT / "scripts" / "audit_v4x_consumed_result_consistency.py"
NULL_AUDIT = ROOT / "scripts" / "audit_v4x_consumed_result_nulls.py"
ADVERSARIAL = ROOT / "tests" / "test_v4x_critical_alpha_audit.py"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_audit_scripts_parse_and_pin_consumed_inputs() -> None:
    for path in (MARKET_AUDIT, RESULT_AUDIT, NULL_AUDIT, ADVERSARIAL):
        ast.parse(source(path))
    manifest_sha = "05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef"
    assert manifest_sha in source(RESULT_AUDIT)
    assert manifest_sha in source(NULL_AUDIT)
    assert "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76" in source(MARKET_AUDIT)
    assert "a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab" in source(MARKET_AUDIT)
    assert "2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41" in source(MARKET_AUDIT)


def test_audits_do_not_fit_score_or_call_providers() -> None:
    combined = source(MARKET_AUDIT) + source(RESULT_AUDIT) + source(NULL_AUDIT)
    forbidden = (
        "fit_v4_head(",
        "score_v4_head(",
        ".fit(",
        "fetch_stock_summary_snapshot",
        "fetch_index_summary_snapshot",
        "yfinance",
        "requests.get",
        "sync_forward_calendar",
    )
    for token in forbidden:
        assert token not in combined
    assert '"provider_calls": False' in combined
    assert '"model_fit": False' in combined


def test_adversarial_suite_covers_key_causality_boundaries() -> None:
    body = source(ADVERSARIAL)
    assert "test_control_features_are_invariant_to_future_market_mutation" in body
    assert "test_geometry_is_invariant_to_future_open_and_hlc_mutation" in body
    assert "test_h10_training_target_finishes_before_each_validation_fold" in body
    assert "test_target_ledger_uses_next_open_and_horizon_terminal_close_exactly" in body


def test_consumed_result_audit_checks_true_common_support_spearman() -> None:
    body = source(RESULT_AUDIT)
    assert "common_support_spearman" in body
    assert "normalized_rank(observable[spec[\"alpha\"]])" in body
    assert "spearman_minus_frozen" in body
    assert "median_of_paired_fold_mean_deltas" in body
    assert "difference_of_absolute_medians" in body


def test_market_audit_checks_row_lag_drift_and_open_scale() -> None:
    body = source(MARKET_AUDIT)
    assert "rolling_row_lag_semantics" in body
    assert "longer_than_intended_span" in body
    assert "finite_open_outside_canonical_low_high" in body
    assert "derivative_overlay_finite_conflicts" in body


def test_null_audit_is_within_date_and_common_support() -> None:
    body = source(NULL_AUDIT)
    assert "rng.permutation(y)" in body
    assert "TARGET_BOTH_AVAILABLE" in body
    assert "observed_mean_common_support_spearman_ic" in body
    assert "empirical_p_one_sided" in body
