from idx_trade.ca_source_authority_audit_v11 import (
    FROZEN_FAMILIES,
    classify_event_scope,
    global_ca_population_gate,
    source_bound_certified,
    valid_sha256,
)


def _lower_bound(**overrides):
    row = {
        "transition_lower_bound_certified": True,
        "transition_lower_bound_status": "CERTIFIED",
        "transition_lower_bound_source_ref": "KSEI:EVENT:1",
        "transition_lower_bound_source_sha256": "a" * 64,
        "certified_transition_lower_bound": "2025-01-03",
    }
    row.update(overrides)
    return row


def test_lower_bound_requires_all_provenance_fields():
    assert source_bound_certified(_lower_bound())
    assert not source_bound_certified(_lower_bound(transition_lower_bound_source_sha256=""))
    assert not source_bound_certified(_lower_bound(transition_lower_bound_source_sha256="bad"))
    assert not source_bound_certified(_lower_bound(transition_lower_bound_source_ref=""))
    assert not source_bound_certified(_lower_bound(transition_lower_bound_certified=True, transition_lower_bound_status=""))
    assert valid_sha256("a" * 64)


def test_candidate_after_closure_stays_unknown_without_certified_lower_bound():
    result = classify_event_scope(
        [{"ticker": "AAA", "candidate_date": "2025-01-04"}],
        [{"ticker": "AAA", "date": "2025-01-01"}, {"ticker": "AAA", "date": "2025-01-02"}],
    )
    assert result[0]["closure_scope_classification"] == "UNKNOWN_UNRESOLVED_AFTER_CLOSURE"


def test_only_valid_certified_lower_bound_can_classify_outside():
    result = classify_event_scope(
        [{"ticker": "AAA", "candidate_date": "2025-01-04", **_lower_bound()}],
        [{"ticker": "AAA", "date": "2025-01-01"}, {"ticker": "AAA", "date": "2025-01-02"}],
    )
    assert result[0]["closure_scope_classification"] == "OUTSIDE_DEPENDENCY_AFTER_CLOSURE"

    empty_sha = classify_event_scope(
        [{"ticker": "AAA", "candidate_date": "2025-01-04", **_lower_bound(transition_lower_bound_source_sha256="")}],
        [{"ticker": "AAA", "date": "2025-01-01"}, {"ticker": "AAA", "date": "2025-01-02"}],
    )
    assert empty_sha[0]["closure_scope_classification"] == "UNKNOWN_UNRESOLVED_AFTER_CLOSURE"


def _complete_evidence():
    tickers = {f"T{i:03d}" for i in range(716)}
    fit = {f"T{i:03d}" for i in range(629)}
    identities = {(ticker, "2026-01-02") for ticker in tickers}
    fit_ids = {(ticker, "2026-01-02") for ticker in fit}
    family = []
    for ticker, day in sorted(identities):
        for number, event_family in enumerate(FROZEN_FAMILIES, start=1):
            family.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "event_family": event_family,
                    "coverage_state": "CERTIFIED",
                    "source_contract_id": "CONTRACT-V11",
                    "source_ref": f"SOURCE:{ticker}:{event_family}",
                    "evidence_sha256": f"{number:064x}",
                }
            )
    temporal = [
        {
            "ticker": ticker,
            "date": day,
            "coverage_state": "CERTIFIED",
            "source_contract_id": "TEMPORAL-CONTRACT-V11",
            "source_ref": f"ASOF:{ticker}:{day}",
            "evidence_sha256": "b" * 64,
            "as_of_semantics": "complete observed-through interval",
        }
        for ticker, day in sorted(identities)
    ]
    return tickers, fit, identities, fit_ids, family, temporal


def _gate(**changes):
    tickers, fit, identities, fit_ids, family, temporal = _complete_evidence()
    values = {
        "fit_tickers": fit,
        "application_tickers": tickers,
        "closure_tickers": tickers,
        "fit_identities": fit_ids,
        "application_identities": identities,
        "closure_identities": identities,
        "family_coverage": family,
        "temporal_attestation": temporal,
        "source_family_certified": True,
        "date_level_attestation": True,
        "structural_event_complete": True,
    }
    values.update(changes)
    return global_ca_population_gate(**values)


def test_expanded_629_716_716_scope_passes_only_with_complete_provenance():
    assert _gate()["verdict"] == "PASS"
    naked = _gate(family_coverage=None, temporal_attestation=None)
    assert naked["verdict"] != "PASS"


def test_missing_family_or_bad_hash_fails_closed():
    tickers, fit, identities, fit_ids, family, temporal = _complete_evidence()
    missing = family[:-1]
    assert _gate(family_coverage=missing)["verdict"] != "PASS"
    malformed = list(family)
    malformed[0] = dict(malformed[0], evidence_sha256="not-a-sha")
    assert _gate(family_coverage=malformed)["verdict"] != "PASS"


def test_missing_temporal_provenance_and_conflict_fail_closed():
    tickers, fit, identities, fit_ids, family, temporal = _complete_evidence()
    assert _gate(temporal_attestation=[dict(temporal[0], source_ref="")])["verdict"] != "PASS"
    conflicted = list(family)
    conflicted[0] = dict(conflicted[0], coverage_conflict=True)
    assert _gate(family_coverage=conflicted)["verdict"] != "PASS"


def test_fit_only_629_evidence_cannot_certify_expanded_716_scope():
    tickers, fit, identities, fit_ids, family, temporal = _complete_evidence()
    fit_only = [row for row in family if row["ticker"] in fit]
    temporal_fit_only = [row for row in temporal if row["ticker"] in fit]
    assert _gate(family_coverage=fit_only, temporal_attestation=temporal_fit_only)["verdict"] != "PASS"
