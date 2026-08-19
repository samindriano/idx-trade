"""Capture V4-3R CA80 execution authorization without loading historical targets."""

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
DEFAULT_CONFIG = REPO_ROOT / "config" / "ranking_v4_3r_execution_freeze_v1.json"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def git_output(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def package_version(name: str) -> str:
    return importlib.metadata.version(name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefit-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_expected_summary(summary: dict[str, Any], expected: dict[str, Any]) -> None:
    if summary.get("status") != expected["expected_status"]:
        raise RuntimeError("PREFIT_STATUS_CHANGED")
    if summary.get("outcome_blind") is not True:
        raise RuntimeError("PREFIT_NOT_OUTCOME_BLIND")
    if float(summary.get("support_gate", -1.0)) != float(expected["support_gate"]):
        raise RuntimeError("PREFIT_SUPPORT_GATE_CHANGED")
    if summary.get("historical_execution_authorized") is not True:
        raise RuntimeError("PREFIT_HISTORICAL_EXECUTION_NOT_AUTHORIZED")
    for key in ("historical_target_loaded", "model_fit", "performance_computed"):
        if summary.get(key) is not False:
            raise RuntimeError(f"PREFIT_OUTCOME_GUARD_CHANGED:{key}")
    if summary.get("all_fold_head_training_sets_nonempty") is not True:
        raise RuntimeError("PREFIT_TRAINING_SET_GATE_CHANGED")
    if summary.get("eligible_sessions") != expected["eligible_sessions"]:
        raise RuntimeError("PREFIT_ELIGIBLE_SESSION_COUNTS_CHANGED")
    if summary.get("frozen_consensus_support_buckets") != expected["frozen_consensus_support_buckets"]:
        raise RuntimeError("PREFIT_SUPPORT_BUCKETS_CHANGED")

    actual_validation = summary.get("frozen_validation") or {}
    for key, value in expected["frozen_validation"].items():
        actual = actual_validation.get(key)
        if isinstance(value, float):
            if abs(float(actual) - value) > 1e-15:
                raise RuntimeError(f"PREFIT_FROZEN_VALIDATION_CHANGED:{key}")
        elif actual != value:
            raise RuntimeError(f"PREFIT_FROZEN_VALIDATION_CHANGED:{key}")

    actual_counts = summary.get("training_date_counts") or []
    if actual_counts != expected["training_date_counts"]:
        raise RuntimeError("PREFIT_TRAINING_DATE_COUNTS_CHANGED")


def verify_git_blobs(repo_root: Path, mapping: dict[str, str], label: str) -> dict[str, str]:
    actual: dict[str, str] = {}
    for path, expected_blob in mapping.items():
        blob = git_output(repo_root, "rev-parse", f"HEAD:{path}")
        if blob != expected_blob:
            raise RuntimeError(f"{label}_BLOB_CHANGED:{path}:{blob}!={expected_blob}")
        actual[path] = blob
    return actual


def verify_runtime(repo_root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    ref = cfg["runtime_manifest"]
    runtime_path = repo_root / ref["path"]
    actual_sha = sha256_file(runtime_path)
    if actual_sha != ref["sha256"]:
        raise RuntimeError(f"RUNTIME_MANIFEST_SHA_MISMATCH:{actual_sha}!={ref['sha256']}")
    runtime = read_json(runtime_path, "RUNTIME_MANIFEST")

    expected_python = tuple(runtime["python"]["version_info"][:3])
    actual_python = tuple(sys.version_info[:3])
    if actual_python != expected_python:
        raise RuntimeError(f"PYTHON_VERSION_MISMATCH:{actual_python}!={expected_python}")

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
            "RUNTIME_PACKAGE_VERSION_MISMATCH:"
            + json.dumps({"actual": actual_packages, "expected": expected_packages}, sort_keys=True)
        )
    return {
        "manifest_sha256": actual_sha,
        "python_version": list(actual_python),
        "package_versions": actual_packages,
        "exact_match": True,
    }


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    prefit_root = args.prefit_root.resolve()
    output_dir = args.output_dir.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config

    if output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{output_dir}")
    if git_output(repo_root, "status", "--porcelain"):
        raise RuntimeError("GIT_WORKTREE_NOT_CLEAN")

    cfg = read_json(config_path, "CONFIG")
    if cfg.get("schema_version") != "ranking_v4_3r_execution_freeze_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if cfg.get("generation_id") != "V4_3R_CA80":
        raise RuntimeError("CONFIG_GENERATION_INVALID")
    if cfg.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    if cfg.get("historical_target_access_authorized_before_capture") is not False:
        raise RuntimeError("CONFIG_PRECAPTURE_AUTHORIZATION_CHANGED")

    expected = cfg["prefit_support_result"]
    prefit_manifest_path = prefit_root / "MANIFEST.json"
    prefit_summary_path = prefit_root / "summary.json"
    actual_prefit_manifest_sha = sha256_file(prefit_manifest_path)
    if actual_prefit_manifest_sha != expected["manifest_sha256"]:
        raise RuntimeError(
            f"PREFIT_MANIFEST_SHA_MISMATCH:{actual_prefit_manifest_sha}!={expected['manifest_sha256']}"
        )
    prefit_manifest = read_json(prefit_manifest_path, "PREFIT_MANIFEST")
    prefit_summary = read_json(prefit_summary_path, "PREFIT_SUMMARY")
    if prefit_manifest.get("status") != expected["expected_status"]:
        raise RuntimeError("PREFIT_MANIFEST_STATUS_CHANGED")
    output_hashes = prefit_manifest.get("output_hashes") or {}
    expected_summary_sha = output_hashes.get("summary")
    actual_summary_sha = sha256_file(prefit_summary_path)
    if not expected_summary_sha or actual_summary_sha != expected_summary_sha:
        raise RuntimeError(
            f"PREFIT_SUMMARY_CHILD_SHA_MISMATCH:{actual_summary_sha}!={expected_summary_sha}"
        )
    verify_expected_summary(prefit_summary, expected)

    v4_3r_blobs = verify_git_blobs(
        repo_root, cfg["v4_3r_contract_git_blobs"], "V4_3R_CONTRACT"
    )
    inherited_blobs = verify_git_blobs(
        repo_root, cfg["inherited_v4_3_scientific_git_blobs"], "V4_3_INHERITED_SCIENCE"
    )
    runtime = verify_runtime(repo_root, cfg)

    capture = cfg["capture_gate"]
    for key, value in capture.items():
        if key in {
            "prefit_manifest_exact_match",
            "prefit_summary_child_hash_exact_match",
            "prefit_summary_expected_values_exact_match",
            "git_worktree_clean",
            "contract_git_blobs_exact_match",
            "runtime_exact_match",
        }:
            if value is not True:
                raise RuntimeError(f"CAPTURE_GATE_EXPECTATION_CHANGED:{key}")
        elif value is not False:
            raise RuntimeError(f"CAPTURE_OUTCOME_GUARD_CHANGED:{key}")

    payload = {
        "schema_version": "ranking_v4_3r_execution_freeze_manifest_v1",
        "generation_id": "V4_3R_CA80",
        "status": "V4_3R_EXECUTION_FREEZE_CAPTURED_HISTORICAL_EXECUTION_AUTHORIZED",
        "outcome_blind": True,
        "prefit_support_manifest_sha256": actual_prefit_manifest_sha,
        "prefit_summary_sha256": actual_summary_sha,
        "support_gate": float(expected["support_gate"]),
        "git": {
            "head": git_output(repo_root, "rev-parse", "HEAD"),
            "branch": git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
            "worktree_clean": True,
        },
        "v4_3r_contract_git_blobs": v4_3r_blobs,
        "inherited_v4_3_scientific_git_blobs": inherited_blobs,
        "runtime": runtime,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "provider_calls": False,
        "historical_execution_authorized": True,
        "protected_forward_access_authorized": False,
        "scientific_contract": cfg["scientific_contract"],
        "post_target_rule": cfg["post_target_rule"],
        "next": "RUN_ONE_SHOT_V4_3R_HISTORICAL_TARGET_MODEL_EVALUATION_WITH_NO_SCIENTIFIC_CHANGES",
    }

    output_dir.mkdir(parents=True)
    manifest_path = output_dir / "v4_3r_execution_freeze_manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_sha = sha256_file(manifest_path)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "historical_execution_authorized": True,
                "historical_target_loaded": False,
                "model_fit": False,
                "performance_computed": False,
                "prefit_support_manifest_sha256": actual_prefit_manifest_sha,
                "git_head": payload["git"]["head"],
                "manifest": str(manifest_path),
                "manifest_sha256": manifest_sha,
                "next": payload["next"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
