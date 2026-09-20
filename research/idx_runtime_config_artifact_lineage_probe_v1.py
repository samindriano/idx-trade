"""Read-only current-HEAD revalidation of runtime-config artifact lineage."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
from typing import Any


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
        ["git", "rev-parse", "HEAD"],
        cwd=RUNTIME_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def run_probe() -> dict[str, Any]:
    if _head() != EXPECTED_RUNTIME_HEAD:
        raise RuntimeError("PINNED_RUNTIME_HEAD_CHANGED")
    orchestration_path = RUNTIME_ROOT / "src/idx_trade/e2e_paper_orchestration_v1.py"
    config_v1_path = RUNTIME_ROOT / "src/idx_trade/e2e_paper_runtime_config_v1.py"
    config_v2_path = RUNTIME_ROOT / "src/idx_trade/e2e_paper_runtime_config_v2.py"
    orchestration = orchestration_path.read_text(encoding="utf-8")
    config_v1 = config_v1_path.read_text(encoding="utf-8")
    config_v2 = config_v2_path.read_text(encoding="utf-8")

    loader_fields_present = all(
        field in config_v1 and field in config_v2
        for field in ("config_sha256", "runner_sha256")
    )
    artifact_fields_absent = all(
        field not in orchestration
        for field in ("config_sha256", "runner_sha256")
    )
    orchestration_api_present = all(
        marker in orchestration
        for marker in ("def prepare_post_eod(", "def execute_preopen(", "def _execution_plan_payload(")
    )
    result = {
        "status": "CURRENT_RUNTIME_LINEAGE_GAP_RECONFIRMED",
        "runtime_head": _head(),
        "source_sha256": {
            "e2e_paper_orchestration_v1.py": _sha256(orchestration_path),
            "e2e_paper_runtime_config_v1.py": _sha256(config_v1_path),
            "e2e_paper_runtime_config_v2.py": _sha256(config_v2_path),
        },
        "loader_fields_present": loader_fields_present,
        "prepared_execution_artifact_fields_absent": artifact_fields_absent,
        "orchestration_api_present": orchestration_api_present,
        "writes_performed": False,
    }
    if not loader_fields_present or not artifact_fields_absent or not orchestration_api_present:
        raise AssertionError("RUNTIME_CONFIG_LINEAGE_REVALIDATION_UNEXPECTED")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_probe(), indent=2, sort_keys=True))
