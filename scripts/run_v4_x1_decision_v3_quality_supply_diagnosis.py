from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_v3_failure_diagnosis import DecisionV3FailureDiagnosisError  # noqa: E402
from idx_trade.decision_v3_quality_supply_diagnosis import (  # noqa: E402
    run_quality_supply_diagnosis,
    verify_quality_supply_contract,
    write_quality_supply_artifacts,
)
from idx_trade.decision_v3_structural_source import sha256_file  # noqa: E402

DEFAULT_HISTORICAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2"
)
DEFAULT_STRUCTURAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v3-graded-evidence-structural-replay-20260821-v2"
)
DEFAULT_OUTPUT_DIR = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v3-quality-supply-diagnosis-20260822-v1"
)
EXECUTION_AUTHORIZATION = "DECISION_V3_QUALITY_SUPPLY_DIAGNOSIS_AUDIT_ACCEPTED_V1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen outcome-blind Decision V3 time-to-quality-supply diagnosis. "
            "This is descriptive rank-stream analysis only and does not simulate Decision V4."
        )
    )
    parser.add_argument("--historical-root", type=Path, default=DEFAULT_HISTORICAL_ROOT)
    parser.add_argument("--structural-root", type=Path, default=DEFAULT_STRUCTURAL_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--authorization", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.authorization != EXECUTION_AUTHORIZATION:
        raise DecisionV3FailureDiagnosisError(
            "DECISION_V3_QUALITY_SUPPLY_DIAGNOSIS_NOT_AUDIT_AUTHORIZED"
        )
    verify_quality_supply_contract(REPO_ROOT)
    result = run_quality_supply_diagnosis(
        structural_root=args.structural_root,
        historical_root=args.historical_root,
    )
    manifest = write_quality_supply_artifacts(result, args.output_dir)
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    print(f"manifest={manifest}")
    print(f"manifest_sha256={sha256_file(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
