"""Read-only probe of same-key security-master history collisions."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
from typing import Any

import pandas as pd


RUNTIME_ROOT = Path(
    r"C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational"
).resolve()
EXPECTED_RUNTIME_HEAD = "402fca4b27e91cf8c82d21ff1394ba2d6da73656"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=RUNTIME_ROOT,
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def run_probe() -> dict[str, Any]:
    if _head() != EXPECTED_RUNTIME_HEAD:
        raise RuntimeError("PINNED_RUNTIME_HEAD_CHANGED")
    import sys

    sys.path.insert(0, str(RUNTIME_ROOT / "src"))
    from idx_trade.security_master import build_security_master

    active = pd.DataFrame({
        "ticker": ["ABCD"],
        "company_name": ["ABCD Active"],
        "listed_from": ["2020-01-01"],
        "listed_to": [None],
        "source": ["IDX_ACTIVE"],
    })
    delisted = pd.DataFrame({
        "ticker": ["ABCD"],
        "company_name": ["ABCD Historical"],
        "listed_from": ["2020-01-01"],
        "listed_to": ["2024-12-31"],
        "source": ["IDX_DELISTED"],
    })
    output = build_security_master(active, delisted)
    result = {
        "status": "SAME_KEY_HISTORY_COLLISION_SILENTLY_REDUCED",
        "runtime_head": _head(),
        "security_master_sha256": _sha256(RUNTIME_ROOT / "src/idx_trade/security_master.py"),
        "input_rows": 2,
        "output_rows": int(len(output)),
        "output_ticker": output.iloc[0]["ticker"],
        "output_company_name": output.iloc[0]["company_name"],
        "output_listed_to": str(output.iloc[0]["listed_to"].date()),
        "output_source": output.iloc[0]["source"],
        "writes_performed": False,
    }
    if result["output_rows"] != 1 or result["output_company_name"] != "ABCD Historical":
        raise AssertionError("SECURITY_MASTER_COLLISION_FIXTURE_NOT_OBSERVED")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_probe(), indent=2, sort_keys=True))
