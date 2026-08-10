from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from . import ranking_v3_true_ranking as base
from .provenance import sha256_file


FROZEN_XGBOOST_VERSION = "3.2.0"
DEPENDENCY_ERRATUM_SHA256 = "bd029458f7a7cd14424af9b748cb7522f1d23b0fe8eaf20ad8f6b44d48894bea"
DEPENDENCY_ERRATUM_GIT_BLOB = "327e053c2a1b4270acc4e7de313bba97680eff8b"

# Preserve every research semantic from the original implementation while
# correcting only the impossible dependency identity before any outcome access.
base.FROZEN_XGBOOST_VERSION = FROZEN_XGBOOST_VERSION

V3_E_HYPOTHESIS_ID = base.V3_E_HYPOTHESIS_ID
V3_E_CONTROL = base.V3_E_CONTROL
V3_E_LAMBDAMART = base.V3_E_LAMBDAMART
V3_E_CANDIDATES = base.V3_E_CANDIDATES
V3_E_FEATURE_COLUMNS = base.V3_E_FEATURE_COLUMNS
RANKER_PARAMS = base.RANKER_PARAMS
TRUE_RANKING_SPEC_SHA256 = base.TRUE_RANKING_SPEC_SHA256
TRUE_RANKING_SPEC_GIT_BLOB = base.TRUE_RANKING_SPEC_GIT_BLOB
TRUE_RANKING_ADDENDUM_SHA256 = base.TRUE_RANKING_ADDENDUM_SHA256
TRUE_RANKING_ADDENDUM_GIT_BLOB = base.TRUE_RANKING_ADDENDUM_GIT_BLOB
MAX_DISCOVERY_SIGNAL_INDEX = base.MAX_DISCOVERY_SIGNAL_INDEX

preregistered_ledger_rows = base.preregistered_ledger_rows
assert_discovery_fold_allowed = base.assert_discovery_fold_allowed
build_imputer = base.build_imputer
build_lambdamart = base.build_lambdamart
build_query_training_frame = base.build_query_training_frame
read_discovery_table = base.read_discovery_table
_score_diversity = base._score_diversity
_top_decile_overlap = base._top_decile_overlap
_feature_order_sha256 = base._feature_order_sha256
_absolute_sanity = base._absolute_sanity
_paired_promotion = base._paired_promotion
_paired_metrics = base._paired_metrics


def _git_blob_sha1(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _assert_xgboost_version() -> str:
    return base._assert_xgboost_version()


def _assert_erratum(erratum_path: Path) -> dict[str, str]:
    hashes = {
        "erratum": sha256_file(erratum_path),
        "erratum_git_blob": _git_blob_sha1(erratum_path),
    }
    expected = {
        "erratum": DEPENDENCY_ERRATUM_SHA256,
        "erratum_git_blob": DEPENDENCY_ERRATUM_GIT_BLOB,
    }
    for key, value in expected.items():
        if hashes[key] != value:
            raise RuntimeError(
                f"V3-E dependency erratum identity mismatch {key}: expected={value} actual={hashes[key]}"
            )
    return hashes


def run_discovery(
    *,
    prepared_table_path: Path,
    prepared_manifest_path: Path,
    reference_v2_dir: Path,
    spec_path: Path,
    addendum_path: Path,
    erratum_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    erratum_hashes = _assert_erratum(erratum_path)
    _assert_xgboost_version()
    summary = base.run_discovery(
        prepared_table_path=prepared_table_path,
        prepared_manifest_path=prepared_manifest_path,
        reference_v2_dir=reference_v2_dir,
        spec_path=spec_path,
        addendum_path=addendum_path,
        output_dir=output_dir,
        code_commit=code_commit,
    )

    identity_path = output_dir / "ranking_v3_e_dependency_erratum_identity.json"
    identity = {
        "status": "V3_E_DEPENDENCY_ERRATUM_APPLIED_PRE_OUTCOME",
        "xgboost_version": FROZEN_XGBOOST_VERSION,
        "dependency_erratum_sha256": erratum_hashes["erratum"],
        "dependency_erratum_git_blob": erratum_hashes["erratum_git_blob"],
        "research_semantics_changed": False,
    }
    identity_path.write_text(
        json.dumps(identity, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary_path = output_dir / "ranking_v3_e_true_ranking_summary.json"
    persisted = json.loads(summary_path.read_text(encoding="utf-8"))
    persisted["dependency_erratum_sha256"] = erratum_hashes["erratum"]
    persisted["dependency_erratum_git_blob"] = erratum_hashes["erratum_git_blob"]
    persisted["dependency_erratum_status"] = identity["status"]
    persisted["artifact_sha256"][identity_path.name] = sha256_file(identity_path)
    summary_path.write_text(
        json.dumps(persisted, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    persisted["summary_sha256"] = sha256_file(summary_path)
    return persisted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run frozen Ranking V3-E true-ranking F1-F4 discovery with dependency erratum"
    )
    parser.add_argument("--prepared-table", type=Path, required=True)
    parser.add_argument("--prepared-manifest", type=Path, required=True)
    parser.add_argument("--reference-v2-dir", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--addendum", type=Path, required=True)
    parser.add_argument("--erratum", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_discovery(
        prepared_table_path=args.prepared_table,
        prepared_manifest_path=args.prepared_manifest,
        reference_v2_dir=args.reference_v2_dir,
        spec_path=args.spec,
        addendum_path=args.addendum,
        erratum_path=args.erratum,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
