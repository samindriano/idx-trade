"""Capture the exact V4-3 runtime before any target/model execution.

This script is deliberately outcome-blind. It verifies preregistered artifact
hashes and estimator/imputer semantics, then records the local runtime identity.
It must not load R5/R10, target ranks, model predictions, or performance data.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


THREAD_ENV_KEYS = (
    "PYTHONHASHSEED",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)

SOURCE_HASH_PATHS = (
    "config/ranking_v4_3_preregistration.json",
    "config/ranking_v4_3_prefit_runtime_protocol.json",
    "docs/SIGNAL_RESEARCH_HLCV_CONTRACT.md",
    "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/manifest.json",
    "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_validation_folds.csv",
    "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_eligible_h5_sessions.csv",
    "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_eligible_h10_sessions.csv",
    "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_eligible_consensus_sessions.csv",
    "src/idx_trade/ranking_v4_3_preregistration.py",
    "scripts/run_v4_3_primary_liquid_support.py",
    "scripts/capture_v4_3_prefit_environment.py",
    "tests/test_ranking_v4_3_preregistration.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def package_version(distribution_name: str) -> str:
    return importlib.metadata.version(distribution_name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return repr(value)


def main() -> int:
    parsed = parse_args()
    repo_root = parsed.repo_root.resolve()
    output_dir = parsed.output_dir.resolve()
    protocol_path = repo_root / "config" / "ranking_v4_3_prefit_runtime_protocol.json"
    if not protocol_path.is_file():
        raise RuntimeError("V4_3_PREFIT_PROTOCOL_MISSING")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("status") != "V4_3_PREFIT_RUNTIME_CAPTURE_PROTOCOL_LOCKED_NO_TARGET_OR_MODEL_RUN":
        raise RuntimeError("V4_3_PREFIT_PROTOCOL_NOT_LOCKED")
    if protocol.get("outcome_blind") is not True:
        raise RuntimeError("V4_3_PREFIT_PROTOCOL_NOT_OUTCOME_BLIND")

    if output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT: {output_dir}")

    required_hashes = protocol["required_repo_artifacts"]
    for relative, expected in required_hashes.items():
        path = repo_root / relative
        if not path.is_file():
            raise RuntimeError(f"REQUIRED_REPO_ARTIFACT_MISSING: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"REQUIRED_REPO_ARTIFACT_HASH_MISMATCH: {relative}: {actual} != {expected}"
            )

    git_status = run_git(repo_root, "status", "--porcelain")
    if git_status:
        raise RuntimeError("GIT_WORKTREE_NOT_CLEAN")
    git_head = run_git(repo_root, "rev-parse", "HEAD")
    git_branch = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")

    # Import only runtime libraries. No dataset or outcome artifact is touched.
    import joblib
    import numpy as np
    import pandas as pd
    import pyarrow
    import scipy
    import sklearn
    import threadpoolctl
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.impute import SimpleImputer

    learner_cfg = protocol["learner"]
    estimator = HistGradientBoostingRegressor(
        loss=learner_cfg["loss"],
        **learner_cfg["parameters"],
    )
    effective = estimator.get_params(deep=False)
    expected_effective = {"loss": learner_cfg["loss"], **learner_cfg["parameters"]}
    for key, expected in expected_effective.items():
        actual = effective.get(key)
        if actual != expected:
            raise RuntimeError(
                f"ESTIMATOR_EFFECTIVE_PARAMETER_MISMATCH: {key}: {actual!r} != {expected!r}"
            )

    control_cfg = protocol["imputers"]["control"]
    geometry_cfg = protocol["imputers"]["geometry"]
    control_imputer = SimpleImputer(
        strategy=control_cfg["strategy"],
        add_indicator=control_cfg["add_indicator"],
        keep_empty_features=control_cfg["keep_empty_features"],
    )
    geometry_imputer = SimpleImputer(
        strategy=geometry_cfg["strategy"],
        add_indicator=geometry_cfg["add_indicator"],
        keep_empty_features=geometry_cfg["keep_empty_features"],
    )
    for name, imputer, cfg in (
        ("control", control_imputer, control_cfg),
        ("geometry", geometry_imputer, geometry_cfg),
    ):
        effective_imputer = imputer.get_params(deep=False)
        for key in ("strategy", "add_indicator", "keep_empty_features"):
            if effective_imputer.get(key) != cfg[key]:
                raise RuntimeError(
                    f"IMPUTER_EFFECTIVE_PARAMETER_MISMATCH: {name}.{key}: "
                    f"{effective_imputer.get(key)!r} != {cfg[key]!r}"
                )

    source_hashes: dict[str, str] = {}
    for relative in SOURCE_HASH_PATHS:
        path = repo_root / relative
        if not path.is_file():
            raise RuntimeError(f"PREFIT_SOURCE_PATH_MISSING: {relative}")
        source_hashes[relative] = sha256(path)

    versions = {
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "pyarrow": pyarrow.__version__,
        "scipy": scipy.__version__,
        "scikit-learn": sklearn.__version__,
        "joblib": joblib.__version__,
        "threadpoolctl": package_version("threadpoolctl"),
    }

    payload = {
        "schema_version": "ranking_v4_3_prefit_environment_manifest_v1",
        "status": "V4_3_PREFIT_ENVIRONMENT_CAPTURED_NO_TARGET_OR_MODEL_RUN",
        "outcome_blind": True,
        "target_or_return_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "provider_calls": False,
        "git": {
            "head": git_head,
            "branch": git_branch,
            "worktree_clean": True,
        },
        "python": {
            "version": sys.version,
            "version_info": list(sys.version_info),
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": list(platform.architecture()),
        },
        "package_versions": versions,
        "thread_environment": {key: os.environ.get(key) for key in THREAD_ENV_KEYS},
        "threadpool_info": _jsonable(threadpoolctl.threadpool_info()),
        "estimator": {
            "class": f"{HistGradientBoostingRegressor.__module__}.{HistGradientBoostingRegressor.__name__}",
            "signature": str(inspect.signature(HistGradientBoostingRegressor)),
            "effective_parameters": _jsonable(effective),
            "fit_called": False,
        },
        "imputers": {
            "class": f"{SimpleImputer.__module__}.{SimpleImputer.__name__}",
            "signature": str(inspect.signature(SimpleImputer)),
            "control_effective_parameters": _jsonable(control_imputer.get_params(deep=False)),
            "geometry_effective_parameters": _jsonable(geometry_imputer.get_params(deep=False)),
            "fit_called": False,
        },
        "repo_file_sha256": source_hashes,
        "required_artifact_sha256": required_hashes,
    }

    output_dir.mkdir(parents=True)
    manifest_path = output_dir / "v4_3_prefit_environment_manifest.json"
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    digest = sha256(manifest_path)
    print(json.dumps({
        "status": payload["status"],
        "git_head": git_head,
        "manifest": str(manifest_path),
        "manifest_sha256": digest,
        "package_versions": versions,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
