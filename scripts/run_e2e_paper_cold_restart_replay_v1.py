"""Run the production-path E2E replay across a real process restart.

The child process owns the existing production replay implementation.  This
wrapper only creates a fresh synthetic output root, stops after two completed
sessions, and starts a second process from the durable progress artifacts.
No provider or outcome path is imported or called.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


SCRIPT = Path(__file__).resolve().with_name("run_e2e_paper_production_replay_v1.py")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    root = Path(args.output_dir).expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"COLD_RESTART_OUTPUT_NOT_EMPTY:{root}")

    first = subprocess.Popen(
        [
            sys.executable,
            str(SCRIPT),
            "--output-dir",
            str(root),
            "--stop-after",
            "2",
            "--hold-after",
        ]
    )
    deadline = time.monotonic() + 60.0
    progress = root / "replay_progress.json"
    while time.monotonic() < deadline:
        if first.poll() is not None:
            raise SystemExit("COLD_RESTART_CHILD_EXITED_BEFORE_KILL")
        if progress.is_file():
            payload = json.loads(progress.read_text(encoding="utf-8"))
            if payload.get("completed_session_count") == 2:
                break
        time.sleep(0.1)
    else:
        first.kill()
        first.wait(timeout=10)
        raise SystemExit("COLD_RESTART_PARTIAL_PROGRESS_TIMEOUT")

    first.terminate()
    try:
        first.wait(timeout=10)
    except subprocess.TimeoutExpired:
        first.kill()
        first.wait(timeout=10)
    if first.returncode == 0:
        raise SystemExit("COLD_RESTART_CHILD_WAS_NOT_INTERRUPTED")

    if not progress.is_file():
        raise SystemExit(f"COLD_RESTART_PROGRESS_NOT_WRITTEN:{progress}")

    second = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(root), "--resume"],
        check=False,
    )
    if second.returncode == 0:
        summary_path = root / "acceptance_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        anchor = summary.get("resume_anchor")
        if not summary.get("cold_restart") or not summary.get("resume_process"):
            raise SystemExit("COLD_RESTART_SUMMARY_FLAG_INVALID")
        if not isinstance(anchor, dict) or anchor.get("completed_session_count") != 2:
            raise SystemExit("COLD_RESTART_ANCHOR_INVALID")
        snapshot = Path(str(anchor.get("runtime_snapshot_path") or ""))
        if not snapshot.is_file() or hashlib.sha256(snapshot.read_bytes()).hexdigest() != anchor.get("runtime_snapshot_sha256"):
            raise SystemExit("COLD_RESTART_ANCHOR_SNAPSHOT_INVALID")
        third = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--output-dir",
                str(root),
                "--rerun-complete",
                "--session-index",
                "0",
            ],
            check=False,
        )
        if third.returncode != 0:
            raise SystemExit(third.returncode)
        duplicate_path = root / "duplicate_rerun.json"
        duplicate = json.loads(duplicate_path.read_text(encoding="utf-8"))
        if duplicate.get("status") != "ALREADY_COMPLETE":
            raise SystemExit("COLD_RESTART_DUPLICATE_STATUS_INVALID")
        summary["cold_restart_duplicate_rerun"] = duplicate
        summary.pop("summary_sha256", None)
        summary["summary_sha256"] = hashlib.sha256(
            (json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        ).hexdigest()
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return second.returncode


if __name__ == "__main__":
    raise SystemExit(main())
