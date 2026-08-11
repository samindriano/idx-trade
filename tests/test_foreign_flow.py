from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.foreign_flow import canonicalize_foreign_flow, foreign_flow_asof


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": "BBCA",
        "session_date": "2025-01-10",
        "unit": "SHARES",
        "published_at": "2025-01-10T17:00:00+07:00",
        "knowledge_at": "2025-01-10T17:00:00+07:00",
        "foreign_buy": 1200,
        "foreign_sell": 1000,
        "foreign_net": 200,
        "source": "IDX",
        "source_ref": "TEST-001",
        "source_url": "https://www.idx.id/example",
        "source_sha256": "a" * 64,
    }
    row.update(overrides)
    return row


def test_canonicalizes_explicit_unit_and_net_identity() -> None:
    out = canonicalize_foreign_flow(pd.DataFrame([_row()]))

    assert out.loc[0, "ticker"] == "BBCA"
    assert out.loc[0, "unit"] == "SHARES"
    assert out.loc[0, "foreign_net"] == 200
    assert str(out.loc[0, "knowledge_at"].tz) == "UTC"


def test_rejects_ambiguous_unit() -> None:
    with pytest.raises(ValueError, match="Unsupported foreign-flow unit"):
        canonicalize_foreign_flow(pd.DataFrame([_row(unit="UNKNOWN")]))


def test_rejects_inconsistent_net() -> None:
    with pytest.raises(ValueError, match="foreign_net"):
        canonicalize_foreign_flow(pd.DataFrame([_row(foreign_net=201)]))


def test_rejects_knowledge_before_session() -> None:
    with pytest.raises(ValueError, match="precedes its trading session"):
        canonicalize_foreign_flow(
            pd.DataFrame([_row(knowledge_at="2025-01-09T17:00:00+07:00")])
        )


def test_preserves_later_revision_and_asof_selects_correct_version() -> None:
    rows = pd.DataFrame(
        [
            _row(source_ref="V1", source_sha256="a" * 64),
            _row(
                knowledge_at="2025-01-12T12:00:00+07:00",
                published_at="2025-01-12T12:00:00+07:00",
                foreign_buy=1250,
                foreign_sell=1000,
                foreign_net=250,
                source_ref="V2",
                source_sha256="b" * 64,
            ),
        ]
    )

    before_revision = foreign_flow_asof(rows, "2025-01-11T00:00:00+07:00")
    after_revision = foreign_flow_asof(rows, "2025-01-13T00:00:00+07:00")

    assert before_revision.loc[0, "foreign_net"] == 200
    assert after_revision.loc[0, "foreign_net"] == 250


def test_same_knowledge_duplicate_fails_closed() -> None:
    rows = pd.DataFrame(
        [
            _row(source_ref="A", source_sha256="a" * 64),
            _row(source_ref="B", source_sha256="b" * 64),
        ]
    )

    with pytest.raises(ValueError, match="same-knowledge revision"):
        canonicalize_foreign_flow(rows)


def test_asof_requires_timezone_aware_decision_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        foreign_flow_asof(pd.DataFrame([_row()]), "2025-01-11")
