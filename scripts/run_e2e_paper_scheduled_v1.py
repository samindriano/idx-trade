"""Run the E2E PAPER controller from one immutable external runtime config."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_CONFIG_SCHEMA = "idx_trade_e2e_paper_runtime_config_v1"


class _BootstrapError(RuntimeError):
    """Raised before repository modules are trusted/imported."""


def _git(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _BootstrapError("E2E_RUNTIME_REPO_ATTESTATION_FAILED") from exc
    return completed.stdout.strip()


def _bootstrap_attest(runtime_root: Path, expected_sha256: str | None) -> str:
    config_path = runtime_root / "operational" / "config.json"
    digest_path = runtime_root / "operational" / "config.json.sha256"
    if not config_path.is_file() or not digest_path.is_file():
        raise _BootstrapError("E2E_RUNTIME_CONFIG_MISSING")
    try:
        config_bytes = config_path.read_bytes()
        declared_sha = digest_path.read_text(encoding="utf-8").strip().lower()
        payload = json.loads(config_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _BootstrapError("E2E_RUNTIME_CONFIG_INVALID") from exc
    actual_sha = hashlib.sha256(config_bytes).hexdigest()
    if not _SHA_RE.fullmatch(declared_sha) or declared_sha != actual_sha:
        raise _BootstrapError("E2E_RUNTIME_CONFIG_SHA_MISMATCH")
    if expected_sha256 is not None and declared_sha != expected_sha256.strip().lower():
        raise _BootstrapError("E2E_RUNTIME_CONFIG_EXPECTED_SHA_MISMATCH")
    if not isinstance(payload, dict) or payload.get("schema_version") != _CONFIG_SCHEMA:
        raise _BootstrapError("E2E_RUNTIME_CONFIG_SCHEMA_MISMATCH")
    configured_root = Path(str(payload.get("repo_root") or "")).expanduser()
    if not configured_root.is_absolute() or configured_root.resolve() != REPO_ROOT.resolve():
        raise _BootstrapError("E2E_RUNTIME_CONFIG_REPO_ROOT_MISMATCH")
    expected_branch = str(payload.get("expected_branch") or "").strip()
    expected_commit = str(payload.get("expected_commit") or "").strip().lower()
    runner_sha = str(payload.get("runner_sha256") or "").strip().lower()
    if not expected_branch or not _COMMIT_RE.fullmatch(expected_commit):
        raise _BootstrapError("E2E_RUNTIME_CONFIG_REPO_IDENTITY_INVALID")
    if not _SHA_RE.fullmatch(runner_sha):
        raise _BootstrapError("E2E_RUNTIME_CONFIG_RUNNER_SHA_INVALID")
    actual_runner_sha = hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
    if actual_runner_sha != runner_sha:
        raise _BootstrapError("E2E_RUNTIME_RUNNER_SHA_MISMATCH")
    if _git(REPO_ROOT, "branch", "--show-current") != expected_branch:
        raise _BootstrapError("E2E_RUNTIME_REPO_BRANCH_MISMATCH")
    if _git(REPO_ROOT, "rev-parse", "HEAD").lower() != expected_commit:
        raise _BootstrapError("E2E_RUNTIME_REPO_COMMIT_MISMATCH")
    if _git(REPO_ROOT, "status", "--porcelain", "--untracked-files=all"):
        raise _BootstrapError("E2E_RUNTIME_REPO_DIRTY")
    return declared_sha


_NON_ERROR_STATUSES = {
    "ALREADY_COMPLETE",
    "EXECUTION_COMPLETE",
    "POST_EOD_PREPARED",
    "PREOPEN_CA_READY",
    "PREOPEN_CA_REUSED",
    "WEEKEND_OR_HOLIDAY_NOOP",
    "WAITING_PREOPEN_WINDOW",
    "WAITING_PREPARED_EXECUTION",
    "WAITING_PREOPEN_CA_CAPTURE",
    "WAITING_OFFICIAL_OPEN",
    "WAITING_UPSTREAM_EOD_SCORE",
    "PREOPEN_WINDOW_MISSED_NO_EXECUTION",
}


def scheduler_exit_code(status: str) -> int:
    return 0 if status in _NON_ERROR_STATUSES else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--config-sha256")
    args = parser.parse_args()
    try:
        runtime_root = args.runtime_root.expanduser().resolve()
        config_sha = _bootstrap_attest(runtime_root, args.config_sha256)
    except _BootstrapError as exc:
        print(json.dumps({"controller_status": "WAITING_OPERATIONAL_CONFIGURATION", "reason": str(exc)}, sort_keys=True))
        return 1
    try:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from idx_trade.e2e_paper_operational_controller_v1 import run_operational_cycle
        from idx_trade.e2e_paper_runtime_config_v1 import (
            E2ERuntimeConfigError,
            load_runtime_config,
        )

        loaded = load_runtime_config(runtime_root, expected_sha256=config_sha)
        if (
            loaded.controller.repo_root != REPO_ROOT.resolve()
            or loaded.runner_sha256 != hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
        ):
            raise E2ERuntimeConfigError("E2E_RUNTIME_REPO_ATTESTATION_FAILED")
        result = run_operational_cycle(loaded.controller)
    except E2ERuntimeConfigError as exc:
        print(json.dumps({"controller_status": "WAITING_OPERATIONAL_CONFIGURATION", "reason": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True, default=str))
    return scheduler_exit_code(str(result.get("controller_status") or "FAIL_CLOSED"))


if __name__ == "__main__":
    raise SystemExit(main())
