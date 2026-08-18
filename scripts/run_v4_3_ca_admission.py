"""Outcome-blind V4-3 Corporate Action admission bridge.

This runner only verifies already-frozen pre-target V4-3 lineage against the
final Corporate Action continuity result. It never materializes historical
returns/target ranks, fits a model, generates predictions, computes performance,
or accesses protected-forward outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.ranking_v4_3_ca_admission import (  # noqa: E402
    sha256_file,
    verify_v4_3_ca_admission_inputs,
)


CONTRACT_RELATIVE = Path("config/ranking_v4_3_ca_admission.json")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ca-root", type=Path, required=True)
    parser.add_argument("--pit-support-root", type=Path, required=True)
    parser.add_argument("--execution-code-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    contract_path = REPO_ROOT / CONTRACT_RELATIVE
    if not contract_path.is_file():
        raise RuntimeError(f"V4_3_CA_ADMISSION_CONTRACT_MISSING:{contract_path}")
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes.decode("utf-8"))

    verified = verify_v4_3_ca_admission_inputs(
        contract=contract,
        ca_root=args.ca_root.resolve(),
        pit_support_root=args.pit_support_root.resolve(),
        execution_code_root=args.execution_code_root.resolve(),
    )

    authorization = dict(verified["authorization_on_pass"])
    for key in (
        "historical_target_materialization",
        "historical_target_rank_materialization",
        "historical_model_fit",
        "historical_prediction_generation",
        "historical_frozen_evaluation",
    ):
        if authorization.get(key) is not True:
            raise RuntimeError(f"V4_3_CA_ADMISSION_REQUIRED_AUTHORIZATION_FALSE:{key}")

    payload = {
        "schema_version": "ranking_v4_3_ca_admission_manifest_v1",
        "status": "V4_3_CA_ADMISSION_PASS_HISTORICAL_EXECUTION_AUTHORIZED",
        "outcome_blind": True,
        "historical_target_loaded": False,
        "historical_target_rank_materialized": False,
        "historical_model_fit": False,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "protected_forward_accessed": False,
        "provider_calls": False,
        "scientific_config_changed": False,
        "contract": {
            "path": CONTRACT_RELATIVE.as_posix(),
            "sha256": sha256_bytes(contract_bytes),
            "status": contract["status"],
        },
        "verified_lineage": {
            key: value
            for key, value in verified.items()
            if key != "authorization_on_pass"
        },
        "authorization": authorization,
        "authorization_boundary": (
            "Pass authorizes only the already-frozen V4-3 historical target, "
            "Control/Geometry3 fit, prediction, and frozen evaluation path. "
            "Scientific config changes, post-result rescue, provider calls, "
            "and protected-forward access remain forbidden."
        ),
    }

    args.output_dir.mkdir(parents=True)
    manifest_path = args.output_dir / "v4_3_ca_admission_manifest.json"
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "historical_target_loaded": False,
                "historical_model_fit": False,
                "historical_performance_computed": False,
                "ca_min_rates": verified["ca_per_date_min_rates"],
                "coverage_certified_tickers": verified[
                    "coverage_certified_tickers"
                ],
                "coverage_unresolved_tickers": verified[
                    "coverage_unresolved_tickers"
                ],
                "next": "RUN_FROZEN_V4_3_HISTORICAL_EXECUTION",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
