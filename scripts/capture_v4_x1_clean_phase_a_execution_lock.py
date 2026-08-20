"""Capture the hash-only execution lock for V4-X1 clean Phase A.

This runner is intentionally outcome-blind. It verifies the already accepted
clean-data / CA dependencies, the exact frozen runtime, and Git blob identities
before a later structural replay may run. It must never materialize numeric
targets, fit/score a model, compute historical performance, access protected
forward outcomes, or call a provider.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "ranking_v4_x1_clean_phase_a_execution_lock_v1.json"
SELF_PATH = "scripts/capture_v4_x1_clean_phase_a_execution_lock.py"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"V4_X1_CLEAN_LOCK_INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def git_output(repo_root: Path, *args: str, text: bool = True):
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return completed.stdout.strip() if text else completed.stdout


def git_bytes_at_ref(repo_root: Path, git_ref: str, relative: str) -> bytes:
    return git_output(repo_root, "show", f"{git_ref}:{relative}", text=False)


def package_version(name: str) -> str:
    return importlib.metadata.version(name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-bundle-manifest", type=Path, required=True)
    parser.add_argument("--clean-panel", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--field-provenance", type=Path, required=True)
    parser.add_argument("--ca80-prefit-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_config(repo_root: Path, config_path: Path, cfg: dict[str, Any]) -> None:
    expected_path = (repo_root / "config" / "ranking_v4_x1_clean_phase_a_execution_lock_v1.json").resolve()
    if config_path.resolve() != expected_path:
        raise RuntimeError("V4_X1_CLEAN_LOCK_NONCANONICAL_CONFIG_PATH")
    if cfg.get("schema_version") != "ranking_v4_x1_clean_phase_a_execution_lock_v1":
        raise RuntimeError("V4_X1_CLEAN_LOCK_CONFIG_SCHEMA_INVALID")
    if cfg.get("generation_id") != "V4_X1_CLEAN_REMEDIATED_PROSPECTIVE_V1":
        raise RuntimeError("V4_X1_CLEAN_LOCK_GENERATION_INVALID")
    if cfg.get("phase") != "PHASE_A_OUTCOME_BLIND_STRUCTURAL_REPLAY":
        raise RuntimeError("V4_X1_CLEAN_LOCK_PHASE_INVALID")
    guards = cfg.get("hard_guards") or {}
    required_false = (
        "provider_calls_authorized",
        "network_calls_authorized",
        "numeric_target_access_authorized",
        "model_fit_authorized",
        "model_scoring_authorized",
        "historical_prediction_authorized",
        "historical_performance_authorized",
        "protected_forward_outcome_access_authorized",
        "forward_counter_mutation_authorized",
        "session_semantics_change_authorized",
        "data_repair_authorized",
    )
    for key in required_false:
        if guards.get(key) is not False:
            raise RuntimeError(f"V4_X1_CLEAN_LOCK_GUARD_CHANGED:{key}")


def verify_git_blobs(repo_root: Path, mapping: dict[str, str]) -> dict[str, str]:
    actual: dict[str, str] = {}
    for relative, expected in mapping.items():
        blob = git_output(repo_root, "rev-parse", f"HEAD:{relative}")
        if blob != expected:
            raise RuntimeError(
                f"V4_X1_CLEAN_LOCK_GIT_BLOB_CHANGED:{relative}:{blob}!={expected}"
            )
        actual[relative] = blob
    return actual


def verify_runtime(repo_root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    ref = cfg["runtime_manifest"]
    raw = git_bytes_at_ref(repo_root, str(ref["git_ref"]), str(ref["path"]))
    actual_sha = sha256_bytes(raw)
    if actual_sha != str(ref["sha256"]):
        raise RuntimeError(
            f"V4_X1_CLEAN_LOCK_RUNTIME_MANIFEST_SHA_MISMATCH:{actual_sha}!={ref['sha256']}"
        )
    runtime = json.loads(raw.decode("utf-8"))
    expected_python = tuple(int(v) for v in runtime["python"]["version_info"][:3])
    actual_python = tuple(sys.version_info[:3])
    if actual_python != expected_python:
        raise RuntimeError(
            f"V4_X1_CLEAN_LOCK_PYTHON_VERSION_MISMATCH:{actual_python}!={expected_python}"
        )
    expected_packages = runtime["package_versions"]
    actual_packages = {
        "joblib": package_version("joblib"),
        "numpy": package_version("numpy"),
        "pandas": package_version("pandas"),
        "pyarrow": package_version("pyarrow"),
        "scikit-learn": package_version("scikit-learn"),
        "scipy": package_version("scipy"),
        "threadpoolctl": package_version("threadpoolctl"),
    }
    if actual_packages != expected_packages:
        raise RuntimeError(
            "V4_X1_CLEAN_LOCK_RUNTIME_PACKAGE_MISMATCH:"
            + json.dumps(
                {"actual": actual_packages, "expected": expected_packages},
                sort_keys=True,
            )
        )
    return {
        "manifest_git_ref": str(ref["git_ref"]),
        "manifest_git_blob_sha1": str(ref["git_blob_sha1"]),
        "manifest_sha256": actual_sha,
        "python_version": list(actual_python),
        "package_versions": actual_packages,
        "exact_match": True,
    }


def verify_external_inputs(args: argparse.Namespace, cfg: dict[str, Any]) -> dict[str, str]:
    paths = {
        "final_bundle_manifest": args.final_bundle_manifest.resolve(),
        "clean_panel": args.clean_panel.resolve(),
        "security_master": args.security_master.resolve(),
        "field_provenance": args.field_provenance.resolve(),
        "ca80_prefit_manifest": args.ca80_prefit_manifest.resolve(),
    }
    expected = cfg["external_input_sha256"]
    actual: dict[str, str] = {}
    for key, path in paths.items():
        digest = sha256_file(path)
        if digest != str(expected[key]):
            raise RuntimeError(
                f"V4_X1_CLEAN_LOCK_EXTERNAL_SHA_MISMATCH:{key}:{digest}!={expected[key]}"
            )
        actual[key] = digest
    return actual


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config
    output_dir = args.output_dir.resolve()

    if output_dir.exists():
        raise RuntimeError(f"V4_X1_CLEAN_LOCK_REFUSE_OVERWRITE:{output_dir}")
    if git_output(repo_root, "status", "--porcelain"):
        raise RuntimeError("V4_X1_CLEAN_LOCK_GIT_WORKTREE_NOT_CLEAN")

    cfg = read_json(config_path, "V4_X1_CLEAN_LOCK_CONFIG")
    verify_config(repo_root, config_path, cfg)
    git_blobs = verify_git_blobs(repo_root, cfg["pinned_git_blobs"])
    runtime = verify_runtime(repo_root, cfg)
    external_hashes = verify_external_inputs(args, cfg)

    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": "v4_x1_clean_phase_a_execution_lock_manifest_v1",
        "status": "V4_X1_CLEAN_PHASE_A_EXECUTION_LOCK_CAPTURED_REPLAY_NOT_RUN",
        "generation_id": cfg["generation_id"],
        "phase": cfg["phase"],
        "contract_git_blob_sha1": cfg["contract_git_blob_sha1"],
        "pinned_git_blobs": git_blobs,
        "runtime": runtime,
        "external_input_sha256": external_hashes,
        "outcome_blind": True,
        "provider_calls": False,
        "network_calls": False,
        "numeric_target_accessed": False,
        "model_fit": False,
        "model_scoring": False,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "protected_forward_outcomes_accessed": False,
        "forward_counter_mutated": False,
        "phase_a_replay_run": False,
        "next": "INDEPENDENT_REVIEW_THEN_RUN_OUTCOME_BLIND_PHASE_A_STRUCTURAL_REPLAY",
    }
    manifest_path = output_dir / "v4_x1_clean_phase_a_execution_lock_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"manifest": str(manifest_path), "status": manifest["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
