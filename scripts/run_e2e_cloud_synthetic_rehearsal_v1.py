"""Run an isolated synthetic E2E rehearsal on the real GitHub/R2 boundary.

This harness is intentionally *not* a production E2E phase runner.  It reads
only the accepted production CloudInputBundle, runs the existing deterministic
synthetic E2E replay in a fresh local directory, and writes evidence only under
a caller-supplied rehearsal prefix.  No IDX/Zapi provider, production
PaperState, production counter, order/fill ledger, or outcome path is used.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import Any, Mapping


SCHEMA_VERSION = "idx_trade_e2e_cloud_synthetic_rehearsal_v1"
ACCEPTED_IMPLEMENTATION_SHA = "043003ee9ae19f9ec6ad4c2db99ab1c19a1401f2"
EXPECTED_INPUT_MANIFEST_SHA256 = "858327909343a887c54fbc5e3bea4dafe6f7a8b89f2422a313b954dee04c08ee"
PRODUCTION_INPUT_PREFIX = "e2e-paper-v1"
PRODUCTION_INPUT_MANIFEST_KEY = "inputs/manifest.json"
REHEARSAL_ROOT_PREFIX = "e2e-paper-synthetic-rehearsal-v1"
RESERVED_WRITE_PREFIXES = (
    "e2e-paper-v1",
    "official-open-v1",
    "stockbit-stream-v1",
    "stockbit-stream-v2",
    "stockbit-intraday-v1",
)
UTC = timezone.utc


class RehearsalError(RuntimeError):
    """Fail-closed rehearsal contract violation."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _safe_rehearsal_prefix(value: str) -> str:
    prefix = str(value).strip().strip("/").replace("\\", "/")
    path = PurePosixPath(prefix)
    if not prefix or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise RehearsalError("REHEARSAL_PREFIX_UNSAFE")
    if prefix == REHEARSAL_ROOT_PREFIX:
        raise RehearsalError("REHEARSAL_PREFIX_RUN_ID_REQUIRED")
    if not prefix.startswith(REHEARSAL_ROOT_PREFIX + "/"):
        raise RehearsalError("REHEARSAL_PREFIX_OUTSIDE_ISOLATED_ROOT")
    for reserved in RESERVED_WRITE_PREFIXES:
        if prefix == reserved or prefix.startswith(reserved + "/"):
            raise RehearsalError("REHEARSAL_PREFIX_COLLIDES_WITH_PRODUCTION")
    return prefix


def _require_cloud_dispatch(env: Mapping[str, str]) -> tuple[str, str]:
    if str(env.get("GITHUB_ACTIONS", "")).lower() != "true":
        raise RehearsalError("REHEARSAL_GITHUB_ACTIONS_REQUIRED")
    if env.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise RehearsalError("REHEARSAL_MANUAL_DISPATCH_REQUIRED")
    run_id = str(env.get("GITHUB_RUN_ID", "")).strip()
    run_attempt = str(env.get("GITHUB_RUN_ATTEMPT", "")).strip()
    if not run_id.isdigit() or not run_attempt.isdigit():
        raise RehearsalError("REHEARSAL_GITHUB_RUN_ID_INVALID")
    return run_id, run_attempt


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RehearsalError("REHEARSAL_ACCEPTED_RUNTIME_GIT_HEAD_UNAVAILABLE")
    return completed.stdout.strip().lower()


def _validate_accepted_runtime(root: Path, expected_sha: str) -> None:
    expected = str(expected_sha).strip().lower()
    if expected != ACCEPTED_IMPLEMENTATION_SHA:
        raise RehearsalError("REHEARSAL_ACCEPTED_RUNTIME_PIN_CHANGED")
    if _git_head(root) != expected:
        raise RehearsalError("REHEARSAL_ACCEPTED_RUNTIME_HEAD_MISMATCH")
    script = root / "scripts" / "run_e2e_paper_synthetic_replay_v1.py"
    if not script.is_file():
        raise RehearsalError("REHEARSAL_SYNTHETIC_REPLAY_SCRIPT_MISSING")


def _run_existing_synthetic_replay(accepted_root: Path, output_root: Path) -> tuple[dict[str, Any], bytes]:
    script = accepted_root / "scripts" / "run_e2e_paper_synthetic_replay_v1.py"
    replay_root = output_root / "synthetic-paper"
    child_env = dict(os.environ)
    # Defense in depth: the accepted synthetic replay does not call providers,
    # and the rehearsal does not pass provider credentials to it.
    child_env.pop("ZAPI_API_KEY", None)
    child_env.pop("IDX_API_KEY", None)
    completed = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(replay_root)],
        cwd=str(accepted_root),
        env=child_env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()[-4000:]
        raise RehearsalError("REHEARSAL_SYNTHETIC_REPLAY_FAILED:" + stderr)
    summary_path = replay_root / "acceptance_summary.json"
    if not summary_path.is_file():
        raise RehearsalError("REHEARSAL_SYNTHETIC_SUMMARY_MISSING")
    raw = summary_path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RehearsalError("REHEARSAL_SYNTHETIC_SUMMARY_INVALID") from exc
    if not isinstance(payload, dict):
        raise RehearsalError("REHEARSAL_SYNTHETIC_SUMMARY_NOT_OBJECT")
    if payload.get("schema_version") != "idx_trade_e2e_paper_synthetic_replay_v1":
        raise RehearsalError("REHEARSAL_SYNTHETIC_SCHEMA_MISMATCH")
    if payload.get("synthetic_only") is not True:
        raise RehearsalError("REHEARSAL_SYNTHETIC_ONLY_GUARD_FAILED")
    if payload.get("provider_calls") is not False:
        raise RehearsalError("REHEARSAL_PROVIDER_CALL_GUARD_FAILED")
    if payload.get("protected_outcomes_accessed") is not False:
        raise RehearsalError("REHEARSAL_OUTCOME_GUARD_FAILED")
    if payload.get("session_count") != 5:
        raise RehearsalError("REHEARSAL_SYNTHETIC_SESSION_COUNT_MISMATCH")
    if payload.get("exact_rerun_status") != "ALREADY_COMPLETE":
        raise RehearsalError("REHEARSAL_SYNTHETIC_IDEMPOTENCY_FAILED")
    return payload, raw


def _require_expected_manifest_sha(actual: str, expected: str) -> None:
    if str(expected).strip().lower() != EXPECTED_INPUT_MANIFEST_SHA256:
        raise RehearsalError("REHEARSAL_EXPECTED_INPUT_MANIFEST_PIN_CHANGED")
    if str(actual).strip().lower() != EXPECTED_INPUT_MANIFEST_SHA256:
        raise RehearsalError("REHEARSAL_PRODUCTION_INPUT_MANIFEST_SHA_MISMATCH")


def run(
    *,
    accepted_runtime_root: Path,
    output_dir: Path,
    throwaway_prefix: str,
    accepted_implementation_sha: str,
    expected_input_manifest_sha256: str,
    env: Mapping[str, str] | None = None,
) -> Path:
    values = dict(os.environ if env is None else env)
    run_id, run_attempt = _require_cloud_dispatch(values)
    prefix = _safe_rehearsal_prefix(throwaway_prefix)
    _validate_accepted_runtime(accepted_runtime_root, accepted_implementation_sha)

    if str(values.get("E2E_CLOUD_STORAGE_BACKEND", "s3")).strip().lower() != "s3":
        raise RehearsalError("REHEARSAL_REAL_S3_BACKEND_REQUIRED")

    # Import only after the accepted runtime checkout has been installed by the
    # workflow.  This keeps the launcher branch from becoming science authority.
    from idx_trade.e2e_paper_cloud_runtime_v1 import (  # type: ignore[import-not-found]
        CloudInputBundle,
        ConditionalS3Store,
        StorageImmutabilityConflict,
        build_cloud_store_from_env,
        build_runtime_snapshot,
        restore_runtime_snapshot,
        sha256_bytes,
    )

    output_root = output_dir.expanduser().resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise RehearsalError("REHEARSAL_OUTPUT_DIR_NOT_EMPTY")
    output_root.mkdir(parents=True, exist_ok=True)

    production_env = dict(values)
    production_env["E2E_CLOUD_STORAGE_PREFIX"] = PRODUCTION_INPUT_PREFIX
    production_store = build_cloud_store_from_env(production_env)
    if not isinstance(production_store, ConditionalS3Store):
        raise RehearsalError("REHEARSAL_PRODUCTION_INPUT_STORE_NOT_CONDITIONAL_S3")

    bundle = CloudInputBundle.load(production_store, PRODUCTION_INPUT_MANIFEST_KEY)
    _require_expected_manifest_sha(bundle.manifest_sha256, expected_input_manifest_sha256)
    materialized = bundle.materialize(production_store, output_root / "production-input-readback")
    if len(materialized) != 10 or len(bundle.refs) != 10:
        raise RehearsalError("REHEARSAL_PRODUCTION_INPUT_ROLE_COUNT_MISMATCH")

    synthetic_payload, synthetic_summary_bytes = _run_existing_synthetic_replay(
        accepted_runtime_root, output_root
    )
    synthetic_root = output_root / "synthetic-paper"

    snapshot_bytes, snapshot_sha, snapshot_metadata = build_runtime_snapshot(
        {"paper": synthetic_root}
    )
    restore_root = output_root / "snapshot-restore-check"
    restored = restore_runtime_snapshot(
        snapshot_bytes,
        {"paper": restore_root},
        expected_sha256=snapshot_sha,
    )
    if restored.get("paper") != snapshot_metadata.get("file_count"):
        raise RehearsalError("REHEARSAL_RUNTIME_SNAPSHOT_ROUNDTRIP_FAILED")

    rehearsal_env = dict(values)
    rehearsal_env["E2E_CLOUD_REHEARSAL_PREFIX"] = prefix
    rehearsal_store = build_cloud_store_from_env(
        rehearsal_env, prefix_key="E2E_CLOUD_REHEARSAL_PREFIX"
    )
    if not isinstance(rehearsal_store, ConditionalS3Store):
        raise RehearsalError("REHEARSAL_OUTPUT_STORE_NOT_CONDITIONAL_S3")

    summary_key = "artifacts/acceptance_summary.json"
    first = rehearsal_store.put_if_absent(
        summary_key, synthetic_summary_bytes, "application/json"
    )
    replay = rehearsal_store.put_if_absent(
        summary_key, synthetic_summary_bytes, "application/json"
    )
    conflict_rejected = False
    try:
        rehearsal_store.put_if_absent(
            summary_key,
            synthetic_summary_bytes + b"conflicting-rehearsal-write\n",
            "application/json",
        )
    except StorageImmutabilityConflict:
        conflict_rejected = True
    summary_readback = rehearsal_store.read(summary_key)
    if (
        not first.created
        or replay.created
        or not conflict_rejected
        or summary_readback is None
        or sha256_bytes(summary_readback) != sha256_bytes(synthetic_summary_bytes)
    ):
        raise RehearsalError("REHEARSAL_R2_IMMUTABILITY_CONTRACT_FAILED")

    snapshot_key = "artifacts/runtime_snapshot.zip"
    snapshot_ref = rehearsal_store.put_if_absent(
        snapshot_key, snapshot_bytes, "application/zip"
    )
    snapshot_readback = rehearsal_store.read(snapshot_key)
    if (
        not snapshot_ref.created
        or snapshot_readback is None
        or sha256_bytes(snapshot_readback) != snapshot_sha
    ):
        raise RehearsalError("REHEARSAL_R2_SNAPSHOT_READBACK_FAILED")

    role_hashes = {ref.role: ref.sha256 for ref in bundle.refs}
    observed_at = datetime.now(UTC).isoformat()
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "SYNTHETIC_FULL_CLOUD_E2E_REHEARSAL_PASS",
        "synthetic_only": True,
        "observed_at_utc": observed_at,
        "github": {
            "event_name": values.get("GITHUB_EVENT_NAME"),
            "run_id": run_id,
            "run_attempt": run_attempt,
            "repository": values.get("GITHUB_REPOSITORY", ""),
        },
        "accepted_implementation_sha": ACCEPTED_IMPLEMENTATION_SHA,
        "production_input": {
            "access": "READ_ONLY",
            "prefix": PRODUCTION_INPUT_PREFIX,
            "manifest_key": PRODUCTION_INPUT_MANIFEST_KEY,
            "manifest_sha256": bundle.manifest_sha256,
            "role_count": len(materialized),
            "role_sha256": dict(sorted(role_hashes.items())),
        },
        "synthetic_replay": {
            "summary_key": summary_key,
            "summary_sha256": _sha256_bytes(synthetic_summary_bytes),
            "session_count": synthetic_payload["session_count"],
            "exact_rerun_status": synthetic_payload["exact_rerun_status"],
            "ca_extension_exercised": synthetic_payload.get("ca_extension_exercised"),
        },
        "runtime_snapshot": {
            "key": snapshot_key,
            "sha256": snapshot_sha,
            "file_count": snapshot_metadata.get("file_count"),
            "restore_file_count": restored.get("paper"),
        },
        "r2_contract": {
            "throwaway_prefix": prefix,
            "first_write_created": first.created,
            "identical_replay_created": replay.created,
            "conflicting_write_rejected": conflict_rejected,
            "summary_readback_sha256": sha256_bytes(summary_readback),
            "snapshot_readback_sha256": sha256_bytes(snapshot_readback),
            "manifest_written_last": True,
        },
        "guards": {
            "provider_calls": 0,
            "direct_idx_calls": 0,
            "zapi_calls": 0,
            "production_paper_state_mutated": False,
            "production_forward_counter_mutated": False,
            "production_order_or_fill_created": False,
            "protected_outcomes_accessed": False,
            "retroactive_execution_authorized": False,
            "production_operational_prefix_written": False,
        },
    }
    manifest_bytes = _canonical_json_bytes(manifest)
    manifest_key = "manifest.json"
    manifest_ref = rehearsal_store.put_if_absent(
        manifest_key, manifest_bytes, "application/json"
    )
    manifest_readback = rehearsal_store.read(manifest_key)
    if (
        not manifest_ref.created
        or manifest_readback is None
        or sha256_bytes(manifest_readback) != sha256_bytes(manifest_bytes)
    ):
        raise RehearsalError("REHEARSAL_MANIFEST_COMMIT_FAILED")

    report_path = output_root / "rehearsal_manifest.json"
    report_path.write_bytes(manifest_bytes)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "accepted_implementation_sha": ACCEPTED_IMPLEMENTATION_SHA,
                "production_input_manifest_sha256": bundle.manifest_sha256,
                "throwaway_prefix": prefix,
                "rehearsal_manifest_sha256": sha256_bytes(manifest_bytes),
                "provider_calls": 0,
                "protected_outcomes_accessed": False,
            },
            sort_keys=True,
        )
    )
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted-runtime-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--throwaway-prefix", required=True)
    parser.add_argument(
        "--accepted-implementation-sha",
        default=ACCEPTED_IMPLEMENTATION_SHA,
    )
    parser.add_argument(
        "--expected-input-manifest-sha256",
        default=EXPECTED_INPUT_MANIFEST_SHA256,
    )
    args = parser.parse_args()
    run(
        accepted_runtime_root=Path(args.accepted_runtime_root).expanduser().resolve(),
        output_dir=Path(args.output_dir).expanduser().resolve(),
        throwaway_prefix=args.throwaway_prefix,
        accepted_implementation_sha=args.accepted_implementation_sha,
        expected_input_manifest_sha256=args.expected_input_manifest_sha256,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
