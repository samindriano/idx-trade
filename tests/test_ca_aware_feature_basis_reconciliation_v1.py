from __future__ import annotations

from argparse import Namespace

import pandas as pd
import pytest

from idx_trade.ca_aware_feature_basis_r3 import (
    build_cross_section_population,
    build_observed_dependency_closure,
    build_primary_membership_dependency_closure,
    classify_event_scope,
    compare_identity_sets,
    global_ca_population_gate,
    merge_dependency_closures,
    reconcile_ksei_populations,
    validate_strict_event_census,
)
from scripts.run_ca_aware_feature_basis_reconciliation_v1 import (
    _family_verdict,
    require_hash,
    validate_identity_rows,
    run,
)


def test_identity_ledger_rejects_duplicate_ticker_date() -> None:
    rows = [{"ticker": "AAPL", "date": "2022-01-03"}, {"ticker": "AAPL", "date": "2022-01-03"}]
    with pytest.raises(RuntimeError, match="duplicate identity"):
        validate_identity_rows(rows, "synthetic")


def test_input_hash_gate_rejects_mismatch(tmp_path) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"immutable")
    with pytest.raises(RuntimeError, match="SHA256 mismatch"):
        require_hash(path, "0" * 64, "synthetic")


def test_absent_family_does_not_become_no_event_proof() -> None:
    verdict, reason, _ = _family_verdict("REVERSE_SPLIT", 0)
    assert verdict == "UNKNOWN_NO_POSITIVE_EVENT_PROOF"
    assert "absence" in reason


def test_run_refuses_existing_output_or_staging(tmp_path) -> None:
    output = tmp_path / "audit"
    output.mkdir()
    args = Namespace(
        phase_a_root=str(tmp_path / "phase-a"),
        phase_b_root=str(tmp_path / "phase-b"),
        clean_panel=str(tmp_path / "clean-panel.parquet"),
        ksei_root=str(tmp_path / "ksei"),
        ca_audit_root=str(tmp_path / "ca"),
        output_dir=str(output),
    )
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        run(args)


def test_run_refuses_existing_staging(tmp_path) -> None:
    output = tmp_path / "audit"
    (tmp_path / "audit.staging").mkdir()
    args = Namespace(
        phase_a_root=str(tmp_path / "phase-a"),
        phase_b_root=str(tmp_path / "phase-b"),
        clean_panel=str(tmp_path / "clean-panel.parquet"),
        ksei_root=str(tmp_path / "ksei"),
        ca_audit_root=str(tmp_path / "ca"),
        output_dir=str(output),
    )
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        run(args)


def test_r3_cross_section_population_includes_non_fit_primary_rows() -> None:
    features = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "date": ["2022-01-03"] * 3,
            "universe_primary_liquid": [True, True, False],
        }
    )
    population, summary = build_cross_section_population(
        features,
        {("AAA", "2022-01-03")},
        set(),
    )
    assert set(population["ticker"]) == {"AAA", "BBB"}
    assert set(population.loc[population["population_role"] == "CROSS_SECTION_ONLY", "ticker"]) == {"BBB"}
    assert summary["cross_section_only_rows"] == 1


def test_r3_dependency_closure_uses_observed_rows_not_calendar_subtraction() -> None:
    features = pd.DataFrame(
        {
            "ticker": ["AAA"] * 3,
            "date": ["2022-01-03", "2022-01-05", "2022-01-06"],
        }
    )
    closure, summary = build_observed_dependency_closure(
        features,
        {("AAA", "2022-01-06")},
        dependencies={"sparse_lag": (-2, 0)},
    )
    assert set(zip(closure["ticker"], closure["date"])) == {
        ("AAA", "2022-01-03"),
        ("AAA", "2022-01-06"),
    }
    assert summary["missing_offset_counts"]["sparse_lag"] == 0


def test_r3_primary_membership_closure_uses_official_session_window() -> None:
    features = pd.DataFrame(
        {
            "ticker": ["AAA"] * 3,
            "date": ["2022-01-03", "2022-01-05", "2022-01-07"],
        }
    )
    closure, summary = build_primary_membership_dependency_closure(
        features,
        {("AAA", "2022-01-07")},
        ["2022-01-03", "2022-01-04", "2022-01-05", "2022-01-06", "2022-01-07"],
        lookback_sessions=3,
    )
    assert set(closure["date"]) == {"2022-01-05", "2022-01-07"}
    assert summary["lookback_sessions"] == 3


def test_r3_closure_merge_retains_direct_and_membership_flags() -> None:
    direct = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": ["2022-01-03"],
            "source_observation_position": [0],
            "dependency_families": ["rolling60"],
            "dependency_family_count": [1],
            "is_cross_section_application": [False],
        }
    )
    membership = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "date": ["2022-01-03"],
            "source_observation_position": [0],
            "dependency_families": ["primary_liquidity_60"],
            "dependency_family_count": [1],
            "is_cross_section_application": [False],
        }
    )
    merged = merge_dependency_closures(direct, membership)
    row = merged.iloc[0]
    assert row["dependency_families"] == "primary_liquidity_60;rolling60"
    assert bool(row["is_direct_dependency"])
    assert bool(row["is_primary_membership_dependency"])


def test_r3_pre_fit_event_remains_unresolved_against_closure() -> None:
    closure = pd.DataFrame({"ticker": ["AAA", "AAA"], "date": ["2022-01-03", "2022-01-05"]})
    events = pd.DataFrame(
        {
            "source_kind": ["IDX"],
            "ticker": ["AAA"],
            "event_family": ["STOCK_SPLIT"],
            "candidate_date": ["2021-12-01"],
        }
    )
    result = classify_event_scope(events, closure)
    assert result.loc[0, "closure_scope_classification"] == "UNRESOLVED_CANDIDATE_BEFORE_CLOSURE"
    assert result.loc[0, "transition_semantics"] == "UNRESOLVED"


def test_r3_event_after_closure_is_not_silently_in_scope() -> None:
    closure = pd.DataFrame({"ticker": ["AAA"], "date": ["2022-01-03"]})
    events = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "event_family": ["STOCK_SPLIT"],
            "candidate_date": ["2022-02-01"],
        }
    )
    result = classify_event_scope(events, closure)
    assert result.loc[0, "closure_scope_classification"] == "OUTSIDE_DEPENDENCY_AFTER_CLOSURE"


def test_r3_lineage_comparison_is_exact_and_deterministic() -> None:
    rows, summary = compare_identity_sets(
        {("AAA", "2022-01-03"), ("BBB", "2022-01-03")},
        {("AAA", "2022-01-03"), ("CCC", "2022-01-03")},
    )
    assert summary == {
        "old_rows": 2,
        "current_rows": 2,
        "common_rows": 1,
        "old_only_rows": 1,
        "current_only_rows": 1,
        "equivalent": 0,
    }
    assert rows["comparison"].tolist() == ["COMMON", "OLD_ONLY", "CURRENT_ONLY"]


def test_r3_ksei_reconciliation_keeps_ticker_and_date_scope_separate() -> None:
    ksei = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "coverage_status": ["COVERAGE_CERTIFIED", "COVERAGE_UNRESOLVED"],
        }
    )
    result = reconcile_ksei_populations(
        {
            "FIT": {"AAA"},
            "APPLICATION": {"AAA", "CCC"},
            "CLOSURE": {"AAA", "BBB", "CCC"},
        },
        ksei,
    )
    assert result.set_index("population_scope").loc["APPLICATION", "ksei_absent_tickers"] == 1
    assert not bool(result["date_level_attestation"].any())


def test_r3_global_gate_cannot_promote_without_date_level_ca_attestation() -> None:
    ksei_scope = pd.DataFrame({"date_level_attestation": [False, False, False]})
    gate = global_ca_population_gate(
        fit_tickers=1,
        application_tickers=2,
        closure_tickers=2,
        ksei_scope=ksei_scope,
        structural_event_complete=True,
    )
    assert gate["verdict"] == "FAIL_KSEI_DATE_LEVEL_ATTESTATION_MISSING"


def test_r3_strict_event_census_rejects_partial_and_malformed_inputs() -> None:
    base = {
        "source_kind": ["IDX"],
        "ticker": ["AAA"],
        "event_family": ["STOCK_SPLIT"],
        "candidate_date": ["2022-01-03"],
        "effective_date_status": ["UNRESOLVED"],
        "continuity_status": ["UNRESOLVED"],
        "source_action_id": ["1"],
        "source_ref": ["IDX:1"],
        "source_sha256": ["a" * 64],
        "published_at_utc": ["2022-01-01T00:00:00Z"],
        "evidence_id": ["E1"],
    }
    frame = pd.DataFrame(base)
    with pytest.raises(ValueError, match="row count mismatch"):
        validate_strict_event_census(frame, expected_rows=2, expected_family_counts={"STOCK_SPLIT": 2})
    malformed = frame.copy()
    malformed.loc[0, "source_sha256"] = "bad"
    with pytest.raises(ValueError, match="malformed evidence SHA"):
        validate_strict_event_census(malformed, expected_rows=1, expected_family_counts={"STOCK_SPLIT": 1})


def test_r3_strict_event_census_allows_distinct_ksei_fallback_identities() -> None:
    rows = {
        "source_kind": ["KSEI", "KSEI"],
        "ticker": ["AAA", "AAA"],
        "event_family": ["RIGHTS_HMETD", "STOCK_DIVIDEND"],
        "candidate_date": ["2022-01-03", "2022-01-04"],
        "effective_date_status": ["UNRESOLVED", "UNRESOLVED"],
        "continuity_status": ["UNRESOLVED", "UNRESOLVED"],
        "source_action_id": ["", ""],
        "source_ref": ["Right Distribution", "Stock Dividend"],
        "source_sha256": ["a" * 64, "a" * 64],
        "published_at_utc": ["", ""],
        "evidence_id": ["E1", "E2"],
    }
    validate_strict_event_census(
        pd.DataFrame(rows),
        expected_rows=2,
        expected_family_counts={"RIGHTS_HMETD": 1, "STOCK_DIVIDEND": 1},
    )
