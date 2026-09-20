"""Inventory the pinned checkout for retained obligation-migration fixtures."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
from typing import Any


RUNTIME_ROOT = Path(
    r"C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational"
).resolve()
EXPECTED_RUNTIME_HEAD = "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
KNOWN_RUNTIME_OUTPUT_DIRS = (
    Path("runtime"),
    Path("prepared"),
    Path("executions"),
    Path("state/decisions"),
    Path("t0"),
)


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=RUNTIME_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _tracked_files(*patterns: str) -> list[str]:
    output = subprocess.run(
        ["git", "ls-files", *patterns],
        cwd=RUNTIME_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in output.splitlines() if line]


def _sha256(value: object) -> str:
    return hashlib.sha256(str(value).encode()).hexdigest()


def run_probe() -> dict[str, Any]:
    runtime_head = _head()
    if runtime_head != EXPECTED_RUNTIME_HEAD:
        raise RuntimeError("PINNED_RUNTIME_HEAD_CHANGED")

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=RUNTIME_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    tracked_json = _tracked_files("*.json")
    tracked_csv = _tracked_files("*.csv")
    tracked_candidate_names = [
        path
        for path in _tracked_files()
        if any(
            marker in path.lower()
            for marker in (
                "fixture",
                "snapshot",
                "prepared",
                "execution",
                "legacy",
            )
        )
    ]
    known_runtime_dirs = {
        str(relative): (RUNTIME_ROOT / relative).is_dir()
        for relative in KNOWN_RUNTIME_OUTPUT_DIRS
    }
    retained_fill_vector_files = [
        path
        for path in tracked_json + tracked_csv
        if path.startswith(("runtime/", "prepared/", "executions/", "state/", "t0/"))
    ]

    result = {
        "status": "NO_RETAINED_LEGACY_FIXTURES_IN_PINNED_CHECKOUT",
        "runtime_head": runtime_head,
        "runtime_worktree_clean": status == [],
        "tracked_json_files": tracked_json,
        "tracked_csv_files": tracked_csv,
        "tracked_candidate_names": tracked_candidate_names,
        "known_runtime_output_dirs": known_runtime_dirs,
        "retained_fill_vector_files": retained_fill_vector_files,
        "inventory_fingerprint": _sha256(
            "\n".join(tracked_json + tracked_csv + sorted(known_runtime_dirs))
        ),
        "writes_performed": False,
    }
    if status:
        raise AssertionError("RUNTIME_WORKTREE_NOT_CLEAN")
    if any(known_runtime_dirs.values()):
        raise AssertionError("UNEXPECTED_RETAINED_RUNTIME_OUTPUT_DIRECTORY")
    if retained_fill_vector_files:
        raise AssertionError("UNEXPECTED_RETAINED_FILL_VECTOR_FILE")
    if result["writes_performed"] is not False:
        raise AssertionError("INVENTORY_MUST_BE_READ_ONLY")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_probe(), indent=2, sort_keys=True))
