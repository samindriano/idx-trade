from idx_trade.ca_source_authority_audit_v1 import (
    _idx_family,
    _ksei_family,
    canonical_set_hash,
    source_bound_certified,
    valid_sha256,
)


def _certification_row(**overrides):
    row = {
        "certified_state": "CERTIFIED",
        "accepted_source_bound_status": "ACCEPTED",
        "source_ref": "https://source.example/event/1",
        "evidence_sha256": "a" * 64,
        "transition_lower_bound_date": "2026-07-18",
    }
    row.update(overrides)
    return row


def test_transition_certification_requires_nonempty_valid_sha_and_source_ref():
    assert source_bound_certified(_certification_row())
    assert not source_bound_certified(_certification_row(evidence_sha256=""))
    assert not source_bound_certified(_certification_row(evidence_sha256="not-a-sha"))
    assert not source_bound_certified(_certification_row(source_ref=""))
    assert not source_bound_certified(_certification_row(certified_state="TRUE", accepted_source_bound_status=""))


def test_transition_certification_requires_valid_lower_bound_date():
    assert not source_bound_certified(_certification_row(transition_lower_bound_date="2026/07/18"))
    assert not source_bound_certified(_certification_row(transition_lower_bound_date=""))


def test_sha_and_ticker_set_hash_are_deterministic():
    assert valid_sha256("A" * 64)
    assert not valid_sha256("")
    assert not valid_sha256("a" * 63)
    assert canonical_set_hash(["BBCA", "AALI", "BBCA"]) == canonical_set_hash(["AALI", "BBCA"])


def test_source_family_mapping_does_not_generalize_mergers():
    assert _idx_family("stockSplit") == "STOCK_SPLIT"
    assert _idx_family("gabungUsaha") == "MERGER"
    assert _idx_family("unknown") == "OTHER_ISSUED_HISTORY"
    assert _ksei_family("Mandatory Conversion") == "MANDATORY_CONVERSION"
    assert _ksei_family("Cash Dividend") == "OTHER_KSEI_HISTORY"
