from __future__ import annotations

from pathlib import Path

import pytest

from idx_trade.stockbit_intraday_cloud_smoke import (
    StockbitIntradayR2SmokeError,
    run_r2_smoke,
    safe_smoke_prefix,
)
from idx_trade.stockbit_intraday_cloud_storage import LocalConditionalStore


def test_smoke_prefix_must_be_unique_and_inside_throwaway_root():
    assert safe_smoke_prefix("stockbit-intraday-smoke-v1/run-123") == "stockbit-intraday-smoke-v1/run-123"
    for value in (
        "stockbit-intraday-smoke-v1",
        "stockbit-intraday-v1/run-123",
        "e2e-paper-v1/run-123",
        "stockbit-intraday-smoke-v1/a/b",
        "../stockbit-intraday-smoke-v1/run-123",
    ):
        with pytest.raises(StockbitIntradayR2SmokeError):
            safe_smoke_prefix(value)


def test_smoke_exercises_create_idempotent_conflict_and_readback(tmp_path: Path):
    store = LocalConditionalStore(tmp_path / "smoke")
    result = run_r2_smoke(
        values={},
        prefix="stockbit-intraday-smoke-v1/unit-test-1",
        store=store,
    )
    assert result["status"] == "STOCKBIT_INTRADAY_R2_CONDITIONAL_SMOKE_PASS"
    assert result["first_write_created"] is True
    assert result["identical_replay_created"] is False
    assert result["conflicting_write_rejected"] is True
    assert result["sha256"] == result["readback_sha256"]
    assert result["provider_calls"] == 0
    assert result["production_prefix_written"] is False
    assert result["outcome_accessed"] is False


def test_same_smoke_prefix_cannot_be_reused_as_a_fresh_acceptance_run(tmp_path: Path):
    store = LocalConditionalStore(tmp_path / "smoke")
    prefix = "stockbit-intraday-smoke-v1/unit-test-2"
    run_r2_smoke(values={}, prefix=prefix, store=store)
    with pytest.raises(StockbitIntradayR2SmokeError, match="R2_SMOKE_CONTRACT_FAILED"):
        run_r2_smoke(values={}, prefix=prefix, store=store)
