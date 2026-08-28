from __future__ import annotations

from argparse import Namespace

import pandas as pd
import pytest

from idx_trade.ca_feature_basis_family_coverage_v1 import (
    DEFAULT_REQUIRED_FAMILIES,
    FAMILY_COVERAGE_CERTIFIED,
    FAMILY_COVERAGE_UNKNOWN,
)
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


def test_r31_candidate_after_closure_without_transition_bound_is_unknown() -> None:
    closure = pd.DataFrame({"ticker": ["AAA"], "date": ["2022-01-03"]})
    events = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "event_family": ["STOCK_SPLIT"],
            "candidate_date": ["2022-02-01"],
        }
    )
    result = classify_event_scope(events, closure)
    assert result.loc[0, "closure_scope_classification"] == "UNKNOWN_UNRESOLVED_AFTER_CLOSURE"
    assert not bool(result.loc[0, "transition_lower_bound_certified"])


def test_r31_only_certified_transition_lower_bound_can_be_outside() -> None:
    closure = pd.DataFrame({"ticker": ["AAA"], "date": ["2022-01-03"]})
    events = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "event_family": ["STOCK_SPLIT"],
            "candidate_date": ["2022-02-01"],
            "certified_transition_lower_bound": ["2022-01-04"],
            "transition_lower_bound_certified": [True],
            "transition_lower_bound_status": ["CERTIFIED"],
            "transition_lower_bound_source_ref": ["SOURCE:AAA:2022-01-04"],
            "transition_lower_bound_source_sha256": ["a" * 64],
        }
    )
    result = classify_event_scope(events, closure)
    assert result.loc[0, "closure_scope_classification"] == "OUTSIDE_DEPENDENCY_AFTER_CLOSURE"
    assert bool(result.loc[0, "transition_lower_bound_certified"])


@pytest.mark.parametrize(
    ("overrides", "case"),
    [
        ({"transition_lower_bound_source_sha256": ""}, "empty evidence SHA"),
        ({"transition_lower_bound_source_sha256": "not-a-sha"}, "malformed evidence SHA"),
        ({"transition_lower_bound_source_ref": ""}, "missing source reference"),
        (
            {
                "transition_lower_bound_certified": True,
                "transition_lower_bound_status": "CERTIFIED",
                "transition_lower_bound_source_ref": "",
                "transition_lower_bound_source_sha256": "",
            },
            "boolean/status without provenance",
        ),
    ],
)
def test_r32_transition_lower_bound_requires_source_bound_provenance(
    overrides: dict[str, object], case: str
) -> None:
    closure = pd.DataFrame({"ticker": ["AAA"], "date": ["2022-01-03"]})
    row: dict[str, object] = {
        "ticker": "AAA",
        "event_family": "STOCK_SPLIT",
        "candidate_date": "2022-02-01",
        "certified_transition_lower_bound": "2022-01-04",
        "transition_lower_bound_certified": True,
        "transition_lower_bound_status": "CERTIFIED",
        "transition_lower_bound_source_ref": "SOURCE:AAA:2022-01-04",
        "transition_lower_bound_source_sha256": "a" * 64,
    }
    row.update(overrides)
    result = classify_event_scope(pd.DataFrame([row]), closure)
    assert result.loc[0, "closure_scope_classification"] == "UNKNOWN_UNRESOLVED_AFTER_CLOSURE", case
    assert not bool(result.loc[0, "transition_lower_bound_certified"]), case


def test_r31_current_26_row_scope_reclassification_shape_is_fail_closed() -> None:
    closure = pd.DataFrame(
        {
            "ticker": ["MLPT", "RAJA", "SCMA", "SINI"],
            "date": ["2026-07-17", "2026-07-17", "2026-08-09", "2026-07-17"],
        }
    )
    after_closure = [
        ("IDX_GET_ISSUED_HISTORY", "MLPT", "STOCK_SPLIT", "2026-07-21", "82680"),
        ("KSEI_REGISTERED_SECURITY", "RAJA", "MANDATORY_CONVERSION", "2026-07-20", ""),
        ("KSEI_REGISTERED_SECURITY", "MLPT", "MANDATORY_CONVERSION", "2026-07-23", ""),
        ("IDX_GET_ISSUED_HISTORY", "SCMA", "CAPITAL_RESTRUCTURING", "2026-08-10", "82840"),
        ("IDX_GET_ISSUED_HISTORY", "SINI", "RIGHTS_HMETD", "2026-07-24", "82732"),
    ]
    rows = [
        {"source_kind": kind, "ticker": ticker, "event_family": family, "candidate_date": date, "source_action_id": action}
        for kind, ticker, family, date, action in after_closure
    ]
    rows.extend(
        {"ticker": f"OUT{index:02d}", "event_family": "STOCK_SPLIT", "candidate_date": "2026-07-20"}
        for index in range(10)
    )
    rows.extend(
        {"ticker": "MLPT", "event_family": "STOCK_SPLIT", "candidate_date": "2026-07-16"}
        for _ in range(3)
    )
    rows.extend(
        {"ticker": "MLPT", "event_family": "STOCK_SPLIT", "candidate_date": "2026-07-17"}
        for _ in range(8)
    )
    result = classify_event_scope(pd.DataFrame(rows), closure)
    assert len(result) == 26
    assert result["closure_scope_classification"].value_counts().to_dict() == {
        "UNKNOWN_UNRESOLVED_AFTER_CLOSURE": 5,
        "OUTSIDE_DEPENDENCY_TICKER": 10,
        "UNRESOLVED_CANDIDATE_BEFORE_CLOSURE": 3,
        "UNRESOLVED_CANDIDATE_IN_CLOSURE": 8,
    }


def _certified_scope_evidence(keys: set[tuple[str, str]], *, scope: str, false_date: bool = False) -> list[dict[str, object]]:
    return [
        {
            "scope": scope,
            "ticker": ticker,
            "date": date,
            "source_family_certified": True,
            "date_level_attestation": not false_date or index != 0,
        }
        for index, (ticker, date) in enumerate(sorted(keys))
    ]


def _certified_family_coverage(
    keys: set[tuple[str, str]],
    *,
    missing_family: str | None = None,
    conflict_family: str | None = None,
    evidence_sha256: str = "a" * 64,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for ticker, date in sorted(keys):
        for family in DEFAULT_REQUIRED_FAMILIES:
            missing = family == missing_family
            rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "event_family": family,
                    "coverage_state": FAMILY_COVERAGE_UNKNOWN if missing else FAMILY_COVERAGE_CERTIFIED,
                    "source_contract_id": f"CONTRACT:{family}",
                    "source_ref": "" if missing else f"fixture://{family}/{ticker}/{date}",
                    "evidence_sha256": "" if missing else evidence_sha256,
                    "coverage_conflict": family == conflict_family,
                }
            )
    return pd.DataFrame(rows)


def _certified_temporal_attestation(keys: set[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "date": date,
                "coverage_state": "TEMPORAL_ASOF_CERTIFIED",
                "source_contract_id": "CONTRACT:TEMPORAL_ASOF",
                "source_ref": f"fixture://temporal/{ticker}/{date}",
                "evidence_sha256": "b" * 64,
                "as_of_semantics": "PER_SESSION_AS_OF_NO_EVENT_COVERAGE",
            }
            for ticker, date in sorted(keys)
        ]
    )


def _expanded_gate_inputs() -> tuple[set[str], set[str], set[tuple[str, str]], set[tuple[str, str]], set[tuple[str, str]]]:
    fit_tickers = {f"F{index:03d}" for index in range(629)}
    application_tickers = fit_tickers | {f"A{index:03d}" for index in range(87)}
    fit_ids = {(ticker, "2022-01-03") for ticker in sorted(fit_tickers)}
    application_ids = {(ticker, "2022-01-03") for ticker in sorted(application_tickers)}
    return fit_tickers, application_tickers, fit_ids, application_ids, application_ids


def test_r32_global_gate_accepts_expanded_629_716_716_scope_with_provenance() -> None:
    fit_tickers, application_tickers, fit_ids, application_ids, closure_ids = _expanded_gate_inputs()
    gate = global_ca_population_gate(
        fit_tickers=fit_tickers,
        application_tickers=application_tickers,
        closure_tickers=application_tickers,
        fit_identities=fit_ids,
        application_identities=application_ids,
        closure_identities=closure_ids,
        family_coverage=_certified_family_coverage(application_ids),
        official_sessions=["2022-01-03"],
        temporal_attestation=_certified_temporal_attestation(application_ids),
        ksei_scope=pd.DataFrame({"date_level_attestation": [True]}),
        structural_event_complete=True,
    )
    assert gate["verdict"] == "PASS"
    assert (gate["fit_tickers"], gate["application_tickers"], gate["closure_tickers"]) == (629, 716, 716)
    assert gate["fit_contained_in_application"]
    assert gate["application_contained_in_closure"]


def test_r32_global_gate_rejects_naked_scope_booleans_without_provenance() -> None:
    fit_tickers, application_tickers, fit_ids, application_ids, closure_ids = _expanded_gate_inputs()
    evidence = pd.DataFrame(
        _certified_scope_evidence(application_ids, scope="APPLICATION")
        + _certified_scope_evidence(closure_ids, scope="CLOSURE")
    )
    gate = global_ca_population_gate(
        fit_tickers=fit_tickers,
        application_tickers=application_tickers,
        closure_tickers=application_tickers,
        fit_identities=fit_ids,
        application_identities=application_ids,
        closure_identities=closure_ids,
        scope_evidence=evidence,
        ksei_scope=pd.DataFrame({"date_level_attestation": [True]}),
        structural_event_complete=True,
    )
    assert gate["verdict"] == "FAIL_FAMILY_COVERAGE_EVIDENCE_MISSING"


def test_r32_global_gate_rejects_missing_frozen_structural_family() -> None:
    fit_tickers, application_tickers, fit_ids, application_ids, closure_ids = _expanded_gate_inputs()
    gate = global_ca_population_gate(
        fit_tickers=fit_tickers,
        application_tickers=application_tickers,
        closure_tickers=application_tickers,
        fit_identities=fit_ids,
        application_identities=application_ids,
        closure_identities=closure_ids,
        family_coverage=_certified_family_coverage(application_ids, missing_family=DEFAULT_REQUIRED_FAMILIES[0]),
        official_sessions=["2022-01-03"],
        temporal_attestation=_certified_temporal_attestation(application_ids),
        ksei_scope=pd.DataFrame({"date_level_attestation": [True]}),
        structural_event_complete=True,
    )
    assert gate["verdict"] == "FAIL_FAMILY_COVERAGE_NOT_FULLY_CERTIFIED"


@pytest.mark.parametrize("evidence_sha256", ["", "malformed-sha"])
def test_r32_global_gate_rejects_missing_or_malformed_family_evidence_sha(
    evidence_sha256: str,
) -> None:
    fit_tickers, application_tickers, fit_ids, application_ids, closure_ids = _expanded_gate_inputs()
    gate = global_ca_population_gate(
        fit_tickers=fit_tickers,
        application_tickers=application_tickers,
        closure_tickers=application_tickers,
        fit_identities=fit_ids,
        application_identities=application_ids,
        closure_identities=closure_ids,
        family_coverage=_certified_family_coverage(application_ids, evidence_sha256=evidence_sha256),
        official_sessions=["2022-01-03"],
        temporal_attestation=_certified_temporal_attestation(application_ids),
        ksei_scope=pd.DataFrame({"date_level_attestation": [True]}),
        structural_event_complete=True,
    )
    assert gate["verdict"] == "FAIL_FAMILY_COVERAGE_EVIDENCE_INVALID"


def test_r32_global_gate_rejects_missing_date_asof_provenance() -> None:
    fit_tickers, application_tickers, fit_ids, application_ids, closure_ids = _expanded_gate_inputs()
    naked_temporal = pd.DataFrame(
        [
            {"ticker": ticker, "date": date, "date_level_attestation": True}
            for ticker, date in sorted(application_ids)
        ]
    )
    gate = global_ca_population_gate(
        fit_tickers=fit_tickers,
        application_tickers=application_tickers,
        closure_tickers=application_tickers,
        fit_identities=fit_ids,
        application_identities=application_ids,
        closure_identities=closure_ids,
        family_coverage=_certified_family_coverage(application_ids),
        official_sessions=["2022-01-03"],
        temporal_attestation=naked_temporal,
        ksei_scope=pd.DataFrame({"date_level_attestation": [True]}),
        structural_event_complete=True,
    )
    assert gate["verdict"] == "FAIL_TEMPORAL_ASOF_EVIDENCE_INVALID"


def test_r32_global_gate_rejects_conflicting_family_evidence() -> None:
    fit_tickers, application_tickers, fit_ids, application_ids, closure_ids = _expanded_gate_inputs()
    gate = global_ca_population_gate(
        fit_tickers=fit_tickers,
        application_tickers=application_tickers,
        closure_tickers=application_tickers,
        fit_identities=fit_ids,
        application_identities=application_ids,
        closure_identities=closure_ids,
        family_coverage=_certified_family_coverage(application_ids, conflict_family=DEFAULT_REQUIRED_FAMILIES[0]),
        official_sessions=["2022-01-03"],
        temporal_attestation=_certified_temporal_attestation(application_ids),
        ksei_scope=pd.DataFrame({"date_level_attestation": [True]}),
        structural_event_complete=True,
    )
    assert gate["verdict"] == "FAIL_FAMILY_COVERAGE_NOT_FULLY_CERTIFIED"


def test_r32_global_gate_rejects_partial_629_only_evidence_for_716_scope() -> None:
    fit_tickers, application_tickers, fit_ids, application_ids, closure_ids = _expanded_gate_inputs()
    gate = global_ca_population_gate(
        fit_tickers=fit_tickers,
        application_tickers=application_tickers,
        closure_tickers=application_tickers,
        fit_identities=fit_ids,
        application_identities=application_ids,
        closure_identities=closure_ids,
        family_coverage=_certified_family_coverage(fit_ids),
        official_sessions=["2022-01-03"],
        temporal_attestation=_certified_temporal_attestation(application_ids),
        ksei_scope=pd.DataFrame({"date_level_attestation": [True]}),
        structural_event_complete=True,
    )
    assert gate["verdict"] == "FAIL_FAMILY_COVERAGE_NOT_FULLY_CERTIFIED"


def test_r31_global_gate_rejects_missing_application_or_closure_identity() -> None:
    fit_tickers, application_tickers, fit_ids, application_ids, closure_ids = _expanded_gate_inputs()
    missing_fit_application = set(application_ids) - {next(iter(fit_ids))}
    gate = global_ca_population_gate(
        fit_tickers=fit_tickers,
        application_tickers=application_tickers,
        closure_tickers=application_tickers,
        fit_identities=fit_ids,
        application_identities=missing_fit_application,
        closure_identities=closure_ids,
        scope_evidence=pd.DataFrame(),
        ksei_scope=pd.DataFrame({"date_level_attestation": [True]}),
        structural_event_complete=True,
    )
    assert gate["verdict"] == "FAIL_FIT_IDENTITIES_OUTSIDE_APPLICATION_SCOPE"
    gate = global_ca_population_gate(
        fit_tickers=fit_tickers,
        application_tickers=application_tickers,
        closure_tickers=application_tickers,
        fit_identities=fit_ids,
        application_identities=application_ids - {("A000", "2022-01-03")},
        closure_identities=closure_ids,
        family_coverage=_certified_family_coverage(closure_ids),
        official_sessions=["2022-01-03"],
        temporal_attestation=_certified_temporal_attestation(closure_ids),
        ksei_scope=pd.DataFrame({"date_level_attestation": [True]}),
        structural_event_complete=True,
    )
    assert gate["verdict"] == "FAIL_APPLICATION_IDENTITY_TICKER_SCOPE_MISMATCH"
    gate = global_ca_population_gate(
        fit_tickers=fit_tickers,
        application_tickers=application_tickers,
        closure_tickers=application_tickers,
        fit_identities=fit_ids,
        application_identities=application_ids,
        closure_identities=set(closure_ids) - {next(iter(application_ids))},
        scope_evidence=pd.DataFrame(),
        ksei_scope=pd.DataFrame({"date_level_attestation": [True]}),
        structural_event_complete=True,
    )
    assert gate["verdict"] == "FAIL_APPLICATION_IDENTITIES_OUTSIDE_CLOSURE"


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
