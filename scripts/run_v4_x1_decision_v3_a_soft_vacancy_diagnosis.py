from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_v3_a_soft_vacancy_diagnosis import (  # noqa: E402
    run_a_soft_vacancy_diagnosis,
    verify_a_soft_vacancy_contract,
    write_a_soft_vacancy_artifacts,
)
from idx_trade.decision_v3_failure_diagnosis import (  # noqa: E402
    DecisionV3FailureDiagnosisError,
)
from idx_trade.decision_v3_structural_source import sha256_file  # noqa: E402

DEFAULT_HISTORICAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2"
)
DEFAULT_STRUCTURAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v3-graded-evidence-structural-replay-20260821-v2"
)
DEFAULT_QUALITY_SUPPLY_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v3-quality-supply-diagnosis-20260822-v1"
)
EXECUTION_AUTHORIZATION = (
    "DECISION_V3_A_SOFT_VACANCY_DIAGNOSIS_AUDIT_ACCEPTED_V1"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen outcome-blind A-soft versus A-vacancy descriptive diagnosis "
            "on the already-observed Decision V3 trajectory."
        )
    )
    parser.add_argument("--historical-root", type=Path, default=DEFAULT_HISTORICAL_ROOT)
    parser.add_argument("--structural-root", type=Path, default=DEFAULT_STRUCTURAL_ROOT)
    parser.add_argument(
        "--quality-supply-root", type=Path, default=DEFAULT_QUALITY_SUPPLY_ROOT
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    # Fail closed before touching contract or any local scientific artifact.
    if args.authorization != EXECUTION_AUTHORIZATION:
        raise DecisionV3FailureDiagnosisError(
            "A_SOFT_VACANCY_DIAGNOSIS_NOT_REVIEW_AUTHORIZED"
        )
    verify_a_soft_vacancy_contract(REPO_ROOT)
    result = run_a_soft_vacancy_diagnosis(
        structural_root=args.structural_root,
        historical_root=args.historical_root,
        quality_supply_root=args.quality_supply_root,
    )
    manifest = write_a_soft_vacancy_artifacts(result, args.output_dir)
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    print(f"manifest={manifest}")
    print(f"manifest_sha256={sha256_file(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
