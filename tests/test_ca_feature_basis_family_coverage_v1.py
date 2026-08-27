from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ca_feature_basis_family_coverage_v1 import (
    DEFAULT_REQUIRED_FAMILIES,
    FAMILY_COVERAGE_CERTIFIED,
    FAMILY_COVERAGE_UNKNOWN,
    combine_family_coverage,
    prepare_family_coverage,
)
from idx_trade.ca_feature_basis_gate_v1 import CA_COVERAGE_CERTIFIED, CA_COVERAGE_UNKNOWN
from idx_trade.ca_feature_basis_v1 import RIGHTS_HMETD, STOCK_DIVIDEND


SHA = "a" * 64


def sessions() -> pd.DatetimeIndex:
    return pd.bdate_range("2024-01-02", periods=4)


def claim(
    *,
    ticker: str,
    date: object,
    family: str,
    source: str,
    state: str = FAMILY_COVERAGE_CERTIFIED,
    conflict: bool = False,
    evidence_sha: str = SHA,
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "date": date,
        "event_family": family,
        "coverage_state": state,
        "source_contract_id": source,
        "source_ref": f"fixture://{source}",
        "evidence_sha256": evidence_sha if state == FAMILY_COVERAGE_CERTIFIED else "",
        "coverage_conflict": conflict,
    }


def complete_claims(date: object, *, changed_hash: str | None = None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, family in enumerate(DEFAULT_REQUIRED_FAMILIES):
        rows.append(
            claim(
                ticker="TEST",
                date=date,
                family=family,
                source="KSEI" if index % 2 == 0 else "IDX_ISSUED_HISTORY",
                evidence_sha=(changed_hash if changed_hash is not None and index == 0 else SHA),
            )
        )
    return rows


def test_one_source_family_does_not_certify_unrelated_families() -> None:
    days = sessions()
    ids = pd.DataFrame({"ticker": ["TEST"], "date": [days[1]]})
    coverage = pd.DataFrame(
        [claim(ticker="TEST", date=days[1], family=RIGHTS_HMETD, source="KSEI")]
    )

    result = combine_family_coverage(ids, coverage, days)
    row = result.iloc[0]
    assert row["coverage_state"] == CA_COVERAGE_UNKNOWN
    assert "STOCK_SPLIT" in row["missing_structural_families"].split("|")


def test_union_of_independent_source_contracts_can_certify_global_coverage() -> None:
    days = sessions()
    ids = pd.DataFrame({"ticker": ["TEST"], "date": [days[1]]})
    rows = complete_claims(days[1])

    result = combine_family_coverage(ids, pd.DataFrame(rows), days)
    row = result.iloc[0]
    assert row["coverage_state"] == CA_COVERAGE_CERTIFIED
    assert row["missing_structural_families"] == ""
    assert row["conflicting_structural_families"] == ""
    assert set(row["supporting_source_contracts"].split("|")) == {
        "IDX_ISSUED_HISTORY",
        "KSEI",
    }
    assert len(row["evidence_sha256"]) == 64
    assert row["evidence_sha256"] != SHA


def test_composite_provenance_is_order_independent_and_changes_with_evidence() -> None:
    days = sessions()
    ids = pd.DataFrame({"ticker": ["TEST"], "date": [days[1]]})
    rows = complete_claims(days[1])
    forward = combine_family_coverage(ids, pd.DataFrame(rows), days).iloc[0]
    reverse = combine_family_coverage(ids, pd.DataFrame(list(reversed(rows))), days).iloc[0]
    changed = combine_family_coverage(
        ids,
        pd.DataFrame(complete_claims(days[1], changed_hash="b" * 64)),
        days,
    ).iloc[0]

    assert forward["evidence_sha256"] == reverse["evidence_sha256"]
    assert forward["evidence_sha256"] != changed["evidence_sha256"]


def test_source_conflict_overrides_an_otherwise_certified_family() -> None:
    days = sessions()
    ids = pd.DataFrame({"ticker": ["TEST"], "date": [days[1]]})
    rows = []
    for family in DEFAULT_REQUIRED_FAMILIES:
        rows.append(claim(ticker="TEST", date=days[1], family=family, source="PRIMARY"))
    rows.append(
        claim(
            ticker="TEST",
            date=days[1],
            family=STOCK_DIVIDEND,
            source="CROSS_SOURCE_AUDIT",
            state=FAMILY_COVERAGE_UNKNOWN,
            conflict=True,
        )
    )

    result = combine_family_coverage(ids, pd.DataFrame(rows), days)
    row = result.iloc[0]
    assert row["coverage_state"] == CA_COVERAGE_UNKNOWN
    assert row["conflicting_structural_families"] == STOCK_DIVIDEND


def test_unknown_claim_does_not_defeat_independent_certified_claim_without_conflict() -> None:
    days = sessions()
    ids = pd.DataFrame({"ticker": ["TEST"], "date": [days[1]]})
    rows = []
    for family in DEFAULT_REQUIRED_FAMILIES:
        rows.append(claim(ticker="TEST", date=days[1], family=family, source="PRIMARY"))
    rows.append(
        claim(
            ticker="TEST",
            date=days[1],
            family=RIGHTS_HMETD,
            source="SECONDARY_UNAVAILABLE",
            state=FAMILY_COVERAGE_UNKNOWN,
        )
    )

    result = combine_family_coverage(ids, pd.DataFrame(rows), days)
    assert result.iloc[0]["coverage_state"] == CA_COVERAGE_CERTIFIED


def test_family_coverage_rejects_non_structural_family() -> None:
    days = sessions()
    frame = pd.DataFrame(
        [claim(ticker="TEST", date=days[0], family="CASH_DIVIDEND", source="KSEI")]
    )
    with pytest.raises(ValueError, match="unsupported structural family"):
        prepare_family_coverage(frame, days)
