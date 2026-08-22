from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/run_v4_x1_decision_v4_refill_decoupling_structural_replay.py"


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    src = str(REPO_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not existing else src + os.pathsep + existing
    return env


def test_cli_rejects_bad_authorization_before_prereg_or_source_access(
    tmp_path: Path,
) -> None:
    output = tmp_path / "should-not-exist"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--authorization-token",
            "WRONG",
            "--historical-root",
            str(tmp_path / "missing-source"),
            "--output-dir",
            str(output),
            "--repo-root",
            str(tmp_path / "missing-repo"),
        ],
        cwd=REPO_ROOT,
        env=_child_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    combined = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert "DECISION_V4_REPLAY_AUTHORIZATION_TOKEN_REJECTED" in combined
    assert "DECISION_V4_REPLAY_PREREG_MISSING" not in combined
    assert "DECISION_V3_REPLAY_SOURCE_MISSING" not in combined
    assert not output.exists()


def test_cli_source_orders_authorization_before_contract_and_source() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    auth = text.index("DECISION_V4_REPLAY_AUTHORIZATION_TOKEN_REJECTED")
    contract = text.index("verify_frozen_v4_preregistration(args.repo_root)")
    source = text.index("load_pinned_v4_x1_source_strict(args.historical_root)")
    replay = text.index("run_structural_replay_v4(source)")
    assert auth < contract < source < replay
