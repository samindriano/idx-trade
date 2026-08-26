from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
import subprocess
import sys

import pytest

from idx_trade.official_trading_schedule_v1 import VerifiedOfficialTradingSchedule
from idx_trade.stockbit_intraday_cloud_archive import (
    StockbitIntradayCloudArchive,
    StockbitIntradayCloudError,
)
from idx_trade.stockbit_intraday_cloud_runner import run_cloud_slot
from idx_trade.stockbit_intraday_cloud_storage import LocalConditionalStore
from idx_trade.stockbit_intraday_e2e_bridge import _child_env


SESSION = date(2026, 8, 26)
REPO_ROOT = Path(__file__).resolve().parents[1]


def _schedule() -> VerifiedOfficialTradingSchedule:
    return VerifiedOfficialTradingSchedule(
        attestation_path=Path("schedule.json"),
        attestation_sha256="a" * 64,
        source_document_path=Path("schedule.pdf"),
        source_document_sha256="b" * 64,
        source_reference="IDX",
        coverage_start=SESSION.isoformat(),
        coverage_end=SESSION.isoformat(),
        holiday_dates=(),
        session_dates=(SESSION.isoformat(),),
    )


def test_cloud_slot_rejects_naive_clock_before_provider_call(tmp_path: Path):
    archive = StockbitIntradayCloudArchive(LocalConditionalStore(tmp_path / "cloud"))
    called = False

    def requester(_: str):
        nonlocal called
        called = True
        raise AssertionError("naive clock must fail before provider")

    with pytest.raises(StockbitIntradayCloudError, match="CLOCK_NOT_TIMEZONE_AWARE"):
        run_cloud_slot(
            expected_date=SESSION,
            slot="1830",
            now=datetime(2026, 8, 26, 18, 30),
            schedule=_schedule(),
            context=None,
            archive=archive,
            journal_root=tmp_path / "journal",
            requester=requester,
            code_identity={"commit": "a" * 40},
        )
    assert called is False


def test_dry_run_requires_no_cloud_or_provider_environment():
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_stockbit_intraday_cloud_v1.py"),
            "--slot",
            "1830",
            "--dry-run",
        ],
        cwd=str(REPO_ROOT),
        env={},
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["mode"] == "DRY_RUN"
    assert payload["provider_calls"] == 0
    assert payload["r2_calls"] == 0
    assert payload["retroactive_capture_authorized"] is False
    assert payload["synthetic_fill_authorized"] is False
    assert payload["outcome_access_authorized"] is False


def test_e2e_bridge_child_does_not_inherit_provider_credentials(tmp_path: Path):
    values = {
        "STOCKBIT_INTRADAY_S3_ENDPOINT": "https://example.invalid",
        "STOCKBIT_INTRADAY_S3_BUCKET": "bucket",
        "STOCKBIT_INTRADAY_S3_ACCESS_KEY_ID": "access",
        "STOCKBIT_INTRADAY_S3_SECRET_ACCESS_KEY": "secret",
        "ZAPI_API_KEY": "must-not-cross",
        "IDX_API_KEY": "must-not-cross-either",
        "PYTHONPATH": "existing-path",
    }
    child = _child_env(values, tmp_path / "accepted")
    assert "ZAPI_API_KEY" not in child
    assert "IDX_API_KEY" not in child
    assert child["E2E_CLOUD_STORAGE_BACKEND"] == "s3"
    assert child["E2E_CLOUD_STORAGE_PREFIX"] == "e2e-paper-v1"
    assert child["PYTHONPATH"].split(__import__("os").pathsep)[0].endswith("accepted/src")
