from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.forward_foreign_flow import enrich_session_foreign_flow, verify_session_foreign_flow
from idx_trade.forward_foreign_flow_runtime import run_foreign_flow_catchup


def _session(root: Path) -> Path:
    directory = root / "forward_monitoring" / "sessions" / "2026-08-12"
    directory.mkdir(parents=True)
    payload = {
        "recordsTotal": 1,
        "recordsFiltered": 1,
        "data": [{"StockCode": "BBCA", "Date": "2026-08-12", "ForeignBuy": 1200, "ForeignSell": 1000}],
    }
    raw = json.dumps(payload, sort_keys=True).encode()
    raw_path = directory / "idx_stock_summary.raw.json"
    raw_path.write_bytes(raw)
    manifest = {
        "session_date": "2026-08-12",
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "stock_summary_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "stock_summary_source": {
            "endpoint": "https://www.idx.id/primary/TradingSummary/GetStockSummary",
            "source_ref": "https://www.idx.id/primary/TradingSummary/GetStockSummary?date=20260812",
            "observed_available_at_utc": "2026-08-12T11:05:00+00:00",
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
    return directory


def test_sidecar_is_offline_idempotent_and_hash_bound(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    first = enrich_session_foreign_flow(tmp_path, "2026-08-12")
    second = enrich_session_foreign_flow(tmp_path, "2026-08-12")
    assert first["provider_calls"] == 0
    assert first["sidecar_sha256"] == second["sidecar_sha256"]
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert verify_session_foreign_flow(tmp_path, "2026-08-12")
    frame = pd.read_parquet(directory / "idx_foreign_flow.parquet")
    assert frame.loc[0, "foreign_net"] == 200


def test_parent_revision_fails_closed(tmp_path: Path) -> None:
    directory = _session(tmp_path)
    enrich_session_foreign_flow(tmp_path, "2026-08-12")
    (directory / "idx_stock_summary.raw.json").write_text("{}")
    assert not verify_session_foreign_flow(tmp_path, "2026-08-12")
    with pytest.raises(RuntimeError, match="raw SHA mismatch"):
        enrich_session_foreign_flow(tmp_path, "2026-08-12")


def test_catchup_never_refetches_provider(tmp_path: Path) -> None:
    _session(tmp_path)
    first = run_foreign_flow_catchup(tmp_path)
    second = run_foreign_flow_catchup(tmp_path)
    assert first["provider_calls"] == second["provider_calls"] == 0
    assert len(first["created"]) == 1
    assert second["created"] == []
    assert second["already_valid"] == ["2026-08-12"]
