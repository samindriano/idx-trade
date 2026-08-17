"""Capture V4-3 execution-code identity without loading any historical target data."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path


SELF_PATH = "scripts/capture_v4_3_execution_code_manifest.py"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(repo_root: Path, *args: str, text: bool = True):
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return completed.stdout.strip() if text else completed.stdout


def git_bytes(repo_root: Path, relative: str) -> bytes:
    return git_output(repo_root, "show", f"HEAD:{relative}", text=False)


def package_version(name: str) -> str:
    return importlib.metadata.version(name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT: {output_dir}")
    if git_output(repo_root, "status", "--porcelain"):
        raise RuntimeError("GIT_WORKTREE_NOT_CLEAN")

    protocol_path = "config/ranking_v4_3_execution_code_protocol.json"
    protocol = json.loads(git_bytes(repo_root, protocol_path).decode("utf-8"))
    if protocol.get("status") != "V4_3_EXECUTION_CODE_FREEZE_PENDING_LOCAL_SYNTHETIC_VALIDATION":
        raise RuntimeError("EXECUTION_CODE_PROTOCOL_NOT_LOCKED_PENDING_VALIDATION")
    if protocol.get("outcome_blind") is not True:
        raise RuntimeError("EXECUTION_CODE_PROTOCOL_NOT_OUTCOME_BLIND")
    if protocol.get("historical_target_access_authorized") is not False:
        raise RuntimeError("HISTORICAL_TARGET_ACCESS_ALREADY_AUTHORIZED_UNEXPECTEDLY")

    prereg = protocol["scientific_preregistration"]
    actual_prereg_sha = sha256_bytes(git_bytes(repo_root, prereg["path"]))
    if actual_prereg_sha != prereg["canonical_git_sha256"]:
        raise RuntimeError(
            f"PREREGISTRATION_HASH_MISMATCH: {actual_prereg_sha} != {prereg['canonical_git_sha256']}"
        )

    runtime_ref = protocol["runtime_manifest"]
    runtime_bytes = git_bytes(repo_root, runtime_ref["path"])
    runtime_sha = sha256_bytes(runtime_bytes)
    if runtime_sha != runtime_ref["sha256"]:
        raise RuntimeError(
            f"PREFIT_RUNTIME_MANIFEST_HASH_MISMATCH: {runtime_sha} != {runtime_ref['sha256']}"
        )
    runtime = json.loads(runtime_bytes.decode("utf-8"))

    expected_python = tuple(runtime["python"]["version_info"][:3])
    actual_python = tuple(sys.version_info[:3])
    if actual_python != expected_python:
        raise RuntimeError(f"PYTHON_VERSION_MISMATCH: {actual_python} != {expected_python}")

    expected_packages = runtime["package_versions"]
    actual_packages = {
        "numpy": package_version("numpy"),
        "pandas": package_version("pandas"),
        "pyarrow": package_version("pyarrow"),
        "scipy": package_version("scipy"),
        "scikit-learn": package_version("scikit-learn"),
        "joblib": package_version("joblib"),
        "threadpoolctl": package_version("threadpoolctl"),
    }
    if actual_packages != expected_packages:
        raise RuntimeError(
            "RUNTIME_PACKAGE_VERSION_MISMATCH: "
            + json.dumps({"actual": actual_packages, "expected": expected_packages}, sort_keys=True)
        )

    source_paths = list(protocol["source_paths_to_freeze"])
    if SELF_PATH not in source_paths:
        source_paths.append(SELF_PATH)
    if len(source_paths) != len(set(source_paths)):
        raise RuntimeError("DUPLICATE_EXECUTION_SOURCE_PATH")

    canonical_hashes: dict[str, str] = {}
    worktree_hashes: dict[str, str] = {}
    for relative in source_paths:
        path = repo_root / relative
        if not path.is_file():
            raise RuntimeError(f"EXECUTION_SOURCE_PATH_MISSING: {relative}")
        canonical_hashes[relative] = sha256_bytes(git_bytes(repo_root, relative))
        worktree_hashes[relative] = sha256_file(path)

    payload = {
        "schema_version": "ranking_v4_3_execution_code_manifest_v1",
        "status": "V4_3_EXECUTION_CODE_IDENTITY_CAPTURED_NO_HISTORICAL_TARGET_ACCESS",
        "outcome_blind": True,
        "historical_target_loaded": False,
        "historical_model_fit": False,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "provider_calls": False,
        "git": {
            "head": git_output(repo_root, "rev-parse", "HEAD"),
            "branch": git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
            "worktree_clean": True,
        },
        "runtime": {
            "accepted_manifest_sha256": runtime_sha,
            "python_version": list(actual_python),
            "package_versions": actual_packages,
            "exact_match": True,
        },
        "scientific_preregistration_sha256": actual_prereg_sha,
        "canonical_git_source_sha256": canonical_hashes,
        "working_tree_source_sha256": worktree_hashes,
        "line_ending_note": "canonical Git hashes govern scientific identity; worktree hashes are diagnostic only",
        "remaining_hard_gates": protocol["remaining_pre_target_gates"],
    }

    output_dir.mkdir(parents=True)
    manifest = output_dir / "v4_3_execution_code_manifest.json"
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "git_head": payload["git"]["head"],
                "manifest": str(manifest),
                "manifest_sha256": sha256_file(manifest),
                "runtime_exact_match": True,
                "source_file_count": len(source_paths),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
