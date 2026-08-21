from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_cli_rejects_before_any_historical_source_read(tmp_path: Path) -> None:
    missing_root = tmp_path / "definitely-missing-source"
    output_dir = tmp_path / "output"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_v4_x1_decision_v2_minimal_structural_replay.py",
            "--historical-root",
            str(missing_root),
            "--output-dir",
            str(output_dir),
            "--authorization",
            "NOT_AUTHORIZED",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    combined = completed.stdout + completed.stderr
    assert "DECISION_V2_STRUCTURAL_REPLAY_NOT_REVIEW_AUTHORIZED" in combined
    assert "DECISION_V2_REPLAY_SOURCE_MISSING" not in combined
    assert not output_dir.exists()
