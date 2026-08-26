from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
import time

import pytest

from idx_trade.stockbit_intraday_cloud_archive import (
    StockbitIntradayCloudArchive,
    StockbitIntradayCloudError,
)
from idx_trade.stockbit_intraday_cloud_runner import run_cloud_slot
from idx_trade.stockbit_intraday_cloud_storage import LocalConditionalStore
from idx_trade.stockbit_intraday_runtime import JAKARTA

from tests.test_stockbit_intraday_cloud_runner import (
    SESSION,
    _context,
    _payload,
    _schedule,
)


def test_same_slot_claim_allows_one_provider_stage_only(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "cloud")
    calls: list[str] = []

    def requester(ticker: str):
        calls.append(ticker)
        time.sleep(0.05)
        return _payload(ticker), {"status": 200, "classification": "SUCCESS"}

    def invoke():
        return run_cloud_slot(
            expected_date=SESSION,
            slot="1930",
            now=datetime(2026, 8, 26, 19, 30, tzinfo=JAKARTA),
            schedule=_schedule(),
            context=_context(tmp_path),
            archive=StockbitIntradayCloudArchive(store),
            journal_root=tmp_path / "journal",
            requester=requester,
            code_identity={"commit": "a" * 40},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(invoke), pool.submit(invoke)]
        results = []
        errors = []
        for future in futures:
            try:
                results.append(future.result())
            except Exception as exc:
                errors.append(exc)
    assert len(results) == 1
    assert len(errors) == 1
    assert str(errors[0]) == "STOCKBIT_INTRADAY_SLOT_ALREADY_CLAIMED"
    assert len(calls) > 0
    replay = StockbitIntradayCloudArchive(store).existing_slot(SESSION, "1930")
    assert replay is not None


def test_existing_slot_rejects_noncanonical_child_keys(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "cloud")
    archive = StockbitIntradayCloudArchive(store)
    commit = archive.commit_slot(
        session_date=SESSION,
        slot="1930",
        status="WAITING_CANONICAL_EOD_GATE",
        snapshot_bytes=b"snapshot",
        result_payload={"status": "WAITING_CANONICAL_EOD_GATE"},
        code_identity={"commit": "b" * 40},
        eod_manifest_sha256=None,
        session_manifest_sha256=None,
    )
    raw = json.loads(store.read(commit.commit_key).decode("utf-8"))
    raw["snapshot"]["key"] = "sessions/other/slots/1930/snapshots/" + raw["snapshot"]["sha256"] + ".zip"
    store._path(commit.commit_key).write_bytes((json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n").encode())
    with pytest.raises(StockbitIntradayCloudError, match="SNAPSHOT_KEY_MISMATCH"):
        archive.existing_slot(SESSION, "1930")


def test_production_entrypoint_rejects_local_storage(monkeypatch) -> None:
    from scripts import run_stockbit_intraday_cloud_v1 as entrypoint

    monkeypatch.setattr(
        entrypoint,
        "_now",
        lambda: datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA),
    )
    monkeypatch.setattr(entrypoint, "_verify_code_pin", lambda: "c" * 40)
    monkeypatch.setenv("STOCKBIT_INTRADAY_STORAGE_BACKEND", "local")
    with pytest.raises(RuntimeError, match="PRODUCTION_REQUIRES_S3_STORAGE"):
        entrypoint.run_once(slot="1830", session_date="2026-08-26")


def test_pr_preflight_workflow_has_no_r2_credentials() -> None:
    workflow = Path(".github/workflows/stockbit-intraday-e2e-preflight-pr95.yml").read_text(encoding="utf-8")
    assert "R2_SECRET_ACCESS_KEY" not in workflow
    assert "R2_ACCESS_KEY_ID" not in workflow
    assert "R2_ACCOUNT_ID" not in workflow
    assert "R2_BUCKET_NAME" not in workflow
