from pathlib import Path

import pandas as pd
import pytest

from idx_trade.curated_tradability import (
    load_curated_tradability_intervals,
    merge_curated_tradability_intervals,
)
from idx_trade.security_master import canonicalize_coverage_windows, tradability_state
from idx_trade.states import TradabilityState


def test_repository_cntb_curated_interval_resolves_july_2026_regular_state():
    path = Path("config/curated_tradability_intervals.csv")
    curated = load_curated_tradability_intervals(path)

    for session in ("2026-07-30", "2026-07-31"):
        assert (
            tradability_state(
                curated,
                canonicalize_coverage_windows(pd.DataFrame()),
                "CNTB",
                pd.Timestamp(session),
                market="REGULAR",
            )
            is TradabilityState.SUSPENDED
        )


def test_curated_merge_keeps_conflict_validation_fail_closed(tmp_path):
    path = tmp_path / "curated.csv"
    pd.DataFrame(
        [
            {
                "evidence_id": "official-1",
                "ticker": "TEST",
                "market": "REGULAR",
                "state": "SUSPENDED",
                "effective_from": "2025-01-01",
                "effective_to": "",
                "announced_at": "2025-01-01",
                "source": "IDX_EXCHANGE_ANNOUNCEMENT",
                "source_ref": "idx://official-suspend",
            }
        ]
    ).to_csv(path, index=False)
    curated = load_curated_tradability_intervals(path)

    reconstructed = pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "market": "REGULAR",
                "state": "ACTIVE",
                "effective_from": "2025-01-02",
                "effective_to": "2025-01-03",
                "announced_at": "2025-01-01",
                "source": "IDX_EXCHANGE_ANNOUNCEMENT",
                "source_ref": "idx://conflicting-active",
            }
        ]
    )

    with pytest.raises(ValueError, match="Conflicting tradability intervals"):
        merge_curated_tradability_intervals(reconstructed, curated)


def test_curated_registry_rejects_non_idx_source(tmp_path):
    path = tmp_path / "curated.csv"
    pd.DataFrame(
        [
            {
                "evidence_id": "bad-1",
                "ticker": "TEST",
                "market": "REGULAR",
                "state": "SUSPENDED",
                "effective_from": "2025-01-01",
                "effective_to": "",
                "announced_at": "2025-01-01",
                "source": "BLOG",
                "source_ref": "https://example.com/post",
            }
        ]
    ).to_csv(path, index=False)

    with pytest.raises(ValueError, match="IDX exchange announcements"):
        load_curated_tradability_intervals(path)
