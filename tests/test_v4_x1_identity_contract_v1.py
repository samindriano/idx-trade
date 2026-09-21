from __future__ import annotations

import pytest

from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_identity_contract_v1 import (
    SecurityIdentityV1,
    normalize_security_identities,
    resolve_security_identity,
    security_identity_hash,
)


def _identity(
    *,
    canonical: str = "ISSUER-1",
    ticker: str = "ABCD",
    revision: str = "R1",
    start: str = "2020-01-01",
    end: str | None = None,
    source: str = "idx://identity/1",
) -> SecurityIdentityV1:
    return SecurityIdentityV1(
        canonical_security_id=canonical,
        ticker=ticker,
        instrument_class="COMMON_SHARE",
        effective_from=start,
        effective_to=end,
        identity_revision=revision,
        source_ref=source,
        source_evidence_sha256="a" * 64,
    )


def test_identity_contract_allows_non_overlapping_same_issuer_revision() -> None:
    rows = normalize_security_identities(
        (
            _identity(revision="R1", start="2020-01-01", end="2021-12-31"),
            _identity(revision="R2", start="2022-01-01"),
        )
    )
    assert resolve_security_identity(rows, ticker="ABCD.JK", as_of_session_date="2022-02-01").identity_revision == "R2"
    assert len(security_identity_hash(rows)) == 64


def test_identity_contract_rejects_overlapping_aliases() -> None:
    with pytest.raises(DecisionV1Error, match="ALIAS_CONFLICT"):
        normalize_security_identities(
            (
                _identity(canonical="ISSUER-1"),
                _identity(canonical="ISSUER-2", source="idx://identity/2"),
            )
        )


def test_identity_contract_rejects_unresolved_ticker() -> None:
    with pytest.raises(DecisionV1Error, match="UNRESOLVED"):
        resolve_security_identity(
            (_identity(),),
            ticker="MISSING",
            as_of_session_date="2022-01-01",
        )
