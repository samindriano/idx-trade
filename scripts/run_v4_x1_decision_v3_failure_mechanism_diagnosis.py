from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_v3_failure_diagnosis import (  # noqa: E402
    DecisionV3FailureDiagnosisError,
    run_failure_mechanism_diagnosis,
    write_failure_diagnosis_artifacts,
)
from idx_trade.decision_v3_failure_diagnosis_boundary import (  # noqa: E402
    apply_terminal_observation_boundary,
)
from idx_trade.decision_v3_failure_diagnosis_contract import (  # noqa: E402
    verify_failure_diagnosis_prereg,
)
from idx_trade.decision_v3_structural_source import sha256_file  # noqa: E402


DEFAULT_STRUCTURAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v3-graded-evidence-structural-replay-20260821-v2"
)
EXECUTION_AUTHORIZATION = "DECISION_V3_FAILURE_MECHANISM_DIAGNOSIS_AUDIT_ACCEPTED_V1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen outcome-blind Decision V3 failure-mechanism diagnosis "
            "from immutable structural replay artifacts only."
        )
    )
    parser.add_argument("--structural-root", type=Path, default=DEFAULT_STRUCTURAL_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.authorization != EXECUTION_AUTHORIZATION:
        raise DecisionV3FailureDiagnosisError(
            "DECISION_V3_FAILURE_DIAGNOSIS_NOT_AUDIT_AUTHORIZED"
        )
    verify_failure_diagnosis_prereg(REPO_ROOT)
    result = run_failure_mechanism_diagnosis(structural_root=args.structural_root)
    result = apply_terminal_observation_boundary(result)
    manifest = write_failure_diagnosis_artifacts(result, args.output_dir)
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    print(f"manifest={manifest}")
    print(f"manifest_sha256={sha256_file(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
