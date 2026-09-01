from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys


def _child_code() -> str:
    return r'''
from datetime import datetime
from pathlib import Path
import os
import signal
import sys

from tests.test_stockbit_intraday_cloud_runner import SESSION, _context, _not_found, _payload, _schedule
from idx_trade.stockbit_intraday_cloud_archive import StockbitIntradayCloudArchive
from idx_trade.stockbit_intraday_cloud_runner import run_cloud_slot
from idx_trade.stockbit_intraday_cloud_storage import LocalConditionalStore
from idx_trade.stockbit_intraday_runtime import JAKARTA

root = Path(sys.argv[1])
archive = StockbitIntradayCloudArchive(LocalConditionalStore(root / "cloud"))
mode = sys.argv[2]
calls = []

def requester(ticker):
    calls.append(ticker)
    if mode == "kill" and ticker == "ZERO":
        os.kill(os.getpid(), signal.SIGTERM)
    return (_payload(ticker), {"status": 200, "classification": "SUCCESS"}) if mode == "kill" else (None, _not_found())

result = run_cloud_slot(
    expected_date=SESSION,
    slot="1830",
    now=datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA) if mode == "kill" else datetime(2026, 8, 26, 22, 31, tzinfo=JAKARTA),
    schedule=_schedule(),
    context=_context(root / "fixture"),
    archive=archive,
    journal_root=root / ("journal-a" if mode == "kill" else "journal-b"),
    requester=requester,
    code_identity={"commit": "e" * 40},
)
print(result.status)
print(",".join(calls))
'''


def test_fresh_process_after_hard_kill_blocks_unfenced_recovery(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(Path.cwd() / "src"), str(Path.cwd()), env.get("PYTHONPATH", "")]
    )
    first = subprocess.run(
        [sys.executable, "-c", _child_code(), str(tmp_path), "kill"],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert first.returncode != 0
    resumed = subprocess.run(
        [sys.executable, "-c", _child_code(), str(tmp_path), "resume"],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert resumed.returncode != 0
    assert "STOCKBIT_INTRADAY_STALE_CLAIM_FENCING_UNPROVEN" in resumed.stderr
    assert resumed.stdout == ""
