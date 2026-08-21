from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_v2_failure_diagnosis import (  # noqa: E402
    DecisionV2FailureDiagnosisError,
    run_failure_mechanism_diagnosis,
    write_failure_diagnosis_artifacts,
)
from idx_trade.decision_v2_structural_replay import sha256_file  # noqa: E402


DEFAULT_HISTORICAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2"
)
DEFAULT_STRUCTURAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v2-minimal-structural-replay-20260821-v1"
)
EXECUTION_AUTHORIZATION = (
    "DECISION_V2_FAILURE_MECHANISM_DIAGNOSIS_REVIEW_ACCEPTED_V1"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen outcome-blind Decision V2 failure-mechanism "
            "diagnosis from existing structural ledgers plus pinned alpha ranks."
        )
    )
    parser.add_argument("--historical-root", type=Path, default=DEFAULT_HISTORICAL_ROOT)
    parser.add_argument("--structural-root", type=Path, default=DEFAULT_STRUCTURAL_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.authorization != EXECUTION_AUTHORIZATION:
        raise DecisionV2FailureDiagnosisError(
            "DECISION_V2_FAILURE_DIAGNOSIS_NOT_REVIEW_AUTHORIZED"
        )
    result = run_failure_mechanism_diagnosis(
        structural_root=args.structural_root,
        historical_root=args.historical_root,
    )
    manifest = write_failure_diagnosis_artifacts(result, args.output_dir)
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    print(f"manifest={manifest}")
    print(f"manifest_sha256={sha256_file(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
