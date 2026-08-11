from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ownership_pit import (
    canonicalize_ownership_facts,
    canonicalize_ownership_snapshots,
    ownership_facts_asof,
    ownership_snapshots_asof,
)


def _snapshot(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": "ABCD",
        "as_of_date": "2025-01-31",
        "published_at": "2025-02-10T10:00:00+07:00",
        "source": "IDX",
        "source_ref": "OWN-202501",
        "source_url": "https://www.idx.id/example.csv",
        "source_sha256": "a" * 64,
    }
    row.update(overrides)
    return row


def test_snapshot_is_invisible_before_publication() -> None:
    snapshots = canonicalize_ownership_snapshots(pd.DataFrame([_snapshot()]))

    before = ownership_snapshots_asof(snapshots, "2025-02-10T02:59:59Z")
    at = ownership_snapshots_asof(snapshots, "2025-02-10T03:00:00Z")

    assert before.empty
    assert len(at) == 1


def test_later_revision_does_not_rewrite_earlier_asof() -> None:
    snapshots = canonicalize_ownership_snapshots(
        pd.DataFrame(
            [
                _snapshot(),
                _snapshot(
                    published_at="2025-02-15T09:00:00+07:00",
                    source_ref="OWN-202501-CORR",
                    source_sha256="b" * 64,
                ),
            ]
        )
    )

    earlier = ownership_snapshots_asof(snapshots, "2025-02-12T00:00:00Z")
    later = ownership_snapshots_asof(snapshots, "2025-02-16T00:00:00Z")

    assert earlier.iloc[0]["source_ref"] == "OWN-202501"
    assert later.iloc[0]["source_ref"] == "OWN-202501-CORR"


def test_same_knowledge_conflicting_revision_fails_closed() -> None:
    frame = pd.DataFrame(
        [
            _snapshot(),
            _snapshot(source_ref="CONFLICT", source_sha256="b" * 64),
        ]
    )

    with pytest.raises(ValueError, match="same knowledge time"):
        canonicalize_ownership_snapshots(frame)


def test_naive_publication_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        canonicalize_ownership_snapshots(
            pd.DataFrame([_snapshot(published_at="2025-02-10 10:00:00")])
        )


def test_ownership_fact_metric_units_and_percent_bounds() -> None:
    snapshots = canonicalize_ownership_snapshots(pd.DataFrame([_snapshot()]))
    snapshot_id = snapshots.iloc[0]["snapshot_id"]
    facts = canonicalize_ownership_facts(
        pd.DataFrame(
            [
                {
                    "snapshot_id": snapshot_id,
                    "dimension_type": "RESIDENCY",
                    "dimension_value": "FOREIGN",
                    "metric": "SHARES",
                    "value": 1000,
                    "unit": "SHARES",
                },
                {
                    "snapshot_id": snapshot_id,
                    "dimension_type": "FREE_FLOAT",
                    "dimension_value": "TOTAL",
                    "metric": "PERCENT",
                    "value": 42.5,
                    "unit": "PERCENT",
                },
            ]
        ),
        snapshots,
    )

    assert len(facts) == 2

    bad = pd.DataFrame(
        [
            {
                "snapshot_id": snapshot_id,
                "dimension_type": "FREE_FLOAT",
                "dimension_value": "TOTAL",
                "metric": "PERCENT",
                "value": 120,
                "unit": "PERCENT",
            }
        ]
    )
    with pytest.raises(ValueError, match="exceeds 100"):
        canonicalize_ownership_facts(bad, snapshots)


def test_orphan_fact_fails_closed() -> None:
    snapshots = canonicalize_ownership_snapshots(pd.DataFrame([_snapshot()]))
    facts = pd.DataFrame(
        [
            {
                "snapshot_id": "UNKNOWN",
                "dimension_type": "RESIDENCY",
                "dimension_value": "LOCAL",
                "metric": "SHARES",
                "value": 1,
                "unit": "SHARES",
            }
        ]
    )

    with pytest.raises(ValueError, match="unknown snapshot_id"):
        canonicalize_ownership_facts(facts, snapshots)


def test_facts_follow_selected_snapshot_revision() -> None:
    snapshots = canonicalize_ownership_snapshots(
        pd.DataFrame(
            [
                _snapshot(),
                _snapshot(
                    published_at="2025-02-15T09:00:00+07:00",
                    source_ref="OWN-202501-CORR",
                    source_sha256="b" * 64,
                ),
            ]
        )
    )
    facts = canonicalize_ownership_facts(
        pd.DataFrame(
            [
                {
                    "snapshot_id": snapshots.iloc[0]["snapshot_id"],
                    "dimension_type": "RESIDENCY",
                    "dimension_value": "FOREIGN",
                    "metric": "PERCENT",
                    "value": 20,
                    "unit": "PERCENT",
                },
                {
                    "snapshot_id": snapshots.iloc[1]["snapshot_id"],
                    "dimension_type": "RESIDENCY",
                    "dimension_value": "FOREIGN",
                    "metric": "PERCENT",
                    "value": 25,
                    "unit": "PERCENT",
                },
            ]
        ),
        snapshots,
    )

    earlier = ownership_facts_asof(snapshots, facts, "2025-02-12T00:00:00Z")
    later = ownership_facts_asof(snapshots, facts, "2025-02-16T00:00:00Z")

    assert earlier.iloc[0]["value"] == 20
    assert later.iloc[0]["value"] == 25
