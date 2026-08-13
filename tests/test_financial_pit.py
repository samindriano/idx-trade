from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.financial_pit import (
    canonicalize_financial_facts,
    canonicalize_financial_filings,
    financial_facts_asof,
    financial_filings_asof,
)


def _filing(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": "ABCD",
        "fiscal_period_end": "2025-03-31",
        "period_kind": "Q1",
        "statement_scope": "CONSOLIDATED",
        "currency": "IDR",
        "published_at": "2025-04-30T09:00:00Z",
        "source": "IDX",
        "source_ref": "IDX-FS-001",
        "source_url": "https://www.idx.id/example.xlsx",
        "source_sha256": "a" * 64,
    }
    row.update(overrides)
    return row


def _fact(filing_id: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "filing_id": filing_id,
        "concept": "Revenue",
        "value": 1000,
        "unit": "IDR",
        "period_start": "2025-01-01",
        "period_end": "2025-03-31",
    }
    row.update(overrides)
    return row


def test_filing_is_not_visible_before_publication() -> None:
    filings = pd.DataFrame([_filing()])

    before = financial_filings_asof(filings, pd.Timestamp("2025-04-30 08:59:59"))
    after = financial_filings_asof(filings, pd.Timestamp("2025-04-30 09:00:00"))

    assert before.empty
    assert len(after) == 1


def test_revision_replaces_older_version_only_after_knowledge_time() -> None:
    filings = pd.DataFrame(
        [
            _filing(source_ref="V1", source_sha256="a" * 64),
            _filing(
                published_at="2025-05-10T12:00:00Z",
                source_ref="V2",
                source_sha256="b" * 64,
            ),
        ]
    )

    early = financial_filings_asof(filings, pd.Timestamp("2025-05-05"))
    late = financial_filings_asof(filings, pd.Timestamp("2025-05-11"))

    assert early.loc[0, "source_ref"] == "V1"
    assert late.loc[0, "source_ref"] == "V2"


def test_delayed_supporting_evidence_preserves_later_knowledge_time() -> None:
    filings = pd.DataFrame(
        [
            _filing(
                published_at="2025-04-30T09:00:00Z",
                knowledge_at="2025-05-02T15:00:00Z",
            )
        ]
    )

    result = canonicalize_financial_filings(filings)
    assert result.loc[0, "knowledge_at"] == pd.Timestamp("2025-05-02 15:00:00")
    assert financial_filings_asof(filings, pd.Timestamp("2025-05-01")).empty


def test_same_knowledge_time_conflicting_versions_fail_closed() -> None:
    filings = pd.DataFrame(
        [
            _filing(source_ref="A", source_sha256="a" * 64),
            _filing(source_ref="B", source_sha256="b" * 64),
        ]
    )

    with pytest.raises(ValueError, match="same knowledge time"):
        canonicalize_financial_filings(filings)


def test_statement_scope_must_be_explicit() -> None:
    with pytest.raises(ValueError, match="scope"):
        canonicalize_financial_filings(pd.DataFrame([_filing(statement_scope="UNKNOWN")]))


def test_duration_and_instant_facts_stay_distinct() -> None:
    filing = canonicalize_financial_filings(pd.DataFrame([_filing()])).iloc[0]
    facts = pd.DataFrame(
        [
            _fact(filing.filing_id),
            _fact(
                filing.filing_id,
                concept="Cash",
                value=250,
                period_start=None,
                period_end=None,
                instant_date="2025-03-31",
            ),
        ]
    )

    result = canonicalize_financial_facts(facts)
    assert len(result) == 2
    assert result.loc[result["concept"].eq("Cash"), "instant_date"].notna().all()


def test_facts_follow_selected_revision_asof() -> None:
    filings = canonicalize_financial_filings(
        pd.DataFrame(
            [
                _filing(source_ref="V1", source_sha256="a" * 64),
                _filing(
                    published_at="2025-05-10T12:00:00Z",
                    source_ref="V2",
                    source_sha256="b" * 64,
                ),
            ]
        )
    )
    v1 = filings.loc[filings["source_ref"].eq("V1"), "filing_id"].iloc[0]
    v2 = filings.loc[filings["source_ref"].eq("V2"), "filing_id"].iloc[0]
    facts = pd.DataFrame([_fact(v1, value=1000), _fact(v2, value=1200)])

    early = financial_facts_asof(filings, facts, pd.Timestamp("2025-05-05"))
    late = financial_facts_asof(filings, facts, pd.Timestamp("2025-05-11"))

    assert early.loc[0, "value"] == 1000
    assert late.loc[0, "value"] == 1200


def test_orphan_fact_fails_closed() -> None:
    filings = pd.DataFrame([_filing()])
    facts = pd.DataFrame([_fact("IDX:DOES-NOT-EXIST")])

    with pytest.raises(ValueError, match="unknown filing_id"):
        financial_facts_asof(filings, facts, pd.Timestamp("2025-06-01"))
