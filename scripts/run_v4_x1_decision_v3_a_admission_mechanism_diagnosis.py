from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_v3_a_admission_mechanism_diagnosis import (  # noqa: E402
    run_admission_mechanism_diagnosis,
    verify_admission_mechanism_contract,
    write_admission_mechanism_artifacts,
)
from idx_trade.decision_v3_failure_diagnosis import (  # noqa: E402
    DecisionV3FailureDiagnosisError,
)
from idx_trade.decision_v3_structural_source import sha256_file  # noqa: E402

DEFAULT_PARENT_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v3-a-same-session-diagnosis-20260822-v1"
)
EXECUTION_AUTHORIZATION = (
    "DECISION_V3_A_ADMISSION_MECHANISM_DIAGNOSIS_AUDIT_ACCEPTED_V1"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen final outcome-blind A-soft admission-mechanism diagnosis "
            "using only the already-consumed same-session diagnosis artifacts."
        )
    )
    parser.add_argument("--parent-root", type=Path, default=DEFAULT_PARENT_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    # Fail closed before touching the contract or any local scientific artifact.
    if args.authorization != EXECUTION_AUTHORIZATION:
        raise DecisionV3FailureDiagnosisError(
            "A_ADMISSION_MECHANISM_DIAGNOSIS_NOT_REVIEW_AUTHORIZED"
        )
    verify_admission_mechanism_contract(REPO_ROOT)
    result = run_admission_mechanism_diagnosis(parent_root=args.parent_root)
    manifest = write_admission_mechanism_artifacts(result, args.output_dir)
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    print(f"manifest={manifest}")
    print(f"manifest_sha256={sha256_file(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
