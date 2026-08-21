from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_v3_a_same_session_diagnosis import (  # noqa: E402
    run_same_session_diagnosis,
    verify_same_session_contract,
    write_same_session_artifacts,
)
from idx_trade.decision_v3_failure_diagnosis import (  # noqa: E402
    DecisionV3FailureDiagnosisError,
)
from idx_trade.decision_v3_structural_source import sha256_file  # noqa: E402

DEFAULT_PARENT_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v3-a-soft-vacancy-diagnosis-20260822-v1"
)
EXECUTION_AUTHORIZATION = "DECISION_V3_A_SAME_SESSION_DIAGNOSIS_AUDIT_ACCEPTED_V1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen outcome-blind same-session A-soft versus A-vacancy "
            "diagnosis using only the already-produced parent diagnosis artifacts."
        )
    )
    parser.add_argument("--parent-root", type=Path, default=DEFAULT_PARENT_ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    # Fail closed before touching contract or local scientific artifacts.
    if args.authorization != EXECUTION_AUTHORIZATION:
        raise DecisionV3FailureDiagnosisError(
            "A_SAME_SESSION_DIAGNOSIS_NOT_REVIEW_AUTHORIZED"
        )
    verify_same_session_contract(REPO_ROOT)
    result = run_same_session_diagnosis(parent_root=args.parent_root)
    manifest = write_same_session_artifacts(result, args.output_dir)
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    print(f"manifest={manifest}")
    print(f"manifest_sha256={sha256_file(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
