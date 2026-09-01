from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
from threading import Event, Thread
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
    _not_found,
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


def test_stale_recovery_cannot_enter_while_old_provider_owner_is_active(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "cloud")
    archive = StockbitIntradayCloudArchive(store)
    provider_started = Event()
    release_provider = Event()
    owner_calls: list[str] = []
    owner_errors: list[BaseException] = []

    def owner_requester(ticker: str):
        owner_calls.append(ticker)
        if ticker == "ZERO":
            provider_started.set()
            assert release_provider.wait(5)
        return _payload(ticker), {"status": 200, "classification": "SUCCESS"}

    def owner():
        try:
            run_cloud_slot(
                expected_date=SESSION,
                slot="1830",
                now=datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA),
                schedule=_schedule(),
                context=_context(tmp_path),
                archive=archive,
                journal_root=tmp_path / "journal-owner",
                requester=owner_requester,
                code_identity={"commit": "f" * 40},
            )
        except BaseException as exc:  # surfaced below after the overlap proof
            owner_errors.append(exc)

    thread = Thread(target=owner)
    thread.start()
    assert provider_started.wait(5)

    takeover_calls: list[str] = []

    def takeover_requester(ticker: str):
        takeover_calls.append(ticker)
        raise AssertionError("stale recovery must not enter the provider boundary")

    with pytest.raises(StockbitIntradayCloudError, match="STALE_CLAIM_FENCING_UNPROVEN"):
        run_cloud_slot(
            expected_date=SESSION,
            slot="1830",
            now=datetime(2026, 8, 26, 22, 31, tzinfo=JAKARTA),
            schedule=_schedule(),
            context=_context(tmp_path),
            archive=StockbitIntradayCloudArchive(store),
            journal_root=tmp_path / "journal-takeover",
            requester=takeover_requester,
            code_identity={"commit": "f" * 40},
        )
    assert takeover_calls == []
    release_provider.set()
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert owner_errors == []
    assert owner_calls == ["BBCA", "ZERO"]


def test_stale_recovery_blocks_when_provider_fencing_is_unproven(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "cloud")
    archive = StockbitIntradayCloudArchive(store)
    first_calls: list[str] = []

    def interrupted_request(ticker: str):
        first_calls.append(ticker)
        if ticker == "ZERO":
            raise RuntimeError("PROCESS_KILLED_AFTER_ONE_PROVIDER_RESPONSE")
        return _payload(ticker), {"status": 200, "classification": "SUCCESS"}

    with pytest.raises(RuntimeError, match="PROCESS_KILLED"):
        run_cloud_slot(
            expected_date=SESSION,
            slot="1830",
            now=datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA),
            schedule=_schedule(),
            context=_context(tmp_path),
            archive=archive,
            journal_root=tmp_path / "journal-a",
            requester=interrupted_request,
            code_identity={"commit": "d" * 40},
        )
    assert first_calls == ["BBCA", "ZERO"]
    assert archive.latest_progress(SESSION, "1830") is not None

    resumed_calls: list[str] = []

    def resumed_request(ticker: str):
        resumed_calls.append(ticker)
        return None, _not_found()

    with pytest.raises(StockbitIntradayCloudError, match="STALE_CLAIM_FENCING_UNPROVEN"):
        run_cloud_slot(
            expected_date=SESSION,
            slot="1830",
            now=datetime(2026, 8, 26, 22, 31, tzinfo=JAKARTA),
            schedule=_schedule(),
            context=_context(tmp_path),
            archive=StockbitIntradayCloudArchive(store),
            journal_root=tmp_path / "journal-b",
            requester=resumed_request,
            code_identity={"commit": "d" * 40},
        )
    assert resumed_calls == []
    assert archive.latest_progress(SESSION, "1830") is not None


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
