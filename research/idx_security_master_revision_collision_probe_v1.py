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

    columns = ["ticker", "company_name", "listed_from", "listed_to", "source"]
    active = pd.DataFrame(columns=columns)
    revisions = [
        {
            "ticker": "ABCD",
            "company_name": "History A",
            "listed_from": "2020-01-01",
            "listed_to": "2024-12-31",
            "source": "ARCHIVE_A",
        },
        {
            "ticker": "ABCD",
            "company_name": "History B",
            "listed_from": "2020-01-01",
            "listed_to": "2025-12-31",
            "source": "ARCHIVE_B",
        },
    ]

    def selected(rows: list[dict[str, str]]) -> dict[str, str]:
        output = build_security_master(active, pd.DataFrame(rows, columns=columns))
        row = output.iloc[0]
        return {
            "company_name": str(row["company_name"]),
            "listed_to": str(row["listed_to"].date()),
            "source": str(row["source"]),
        }

    a_then_b = selected(revisions)
    b_then_a = selected(list(reversed(revisions)))
    result = {
        "status": "SAME_KEY_REVISION_COLLISION_IS_ORDER_SENSITIVE",
        "runtime_head": _head(),
        "security_master_sha256": _sha256(RUNTIME_ROOT / "src/idx_trade/security_master.py"),
        "input_rows": 2,
        "a_then_b": a_then_b,
        "b_then_a": b_then_a,
        "order_sensitive": a_then_b != b_then_a,
        "writes_performed": False,
    }
    if not result["order_sensitive"]:
        raise AssertionError("SECURITY_MASTER_COLLISION_FIXTURE_NOT_OBSERVED")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_probe(), indent=2, sort_keys=True))
