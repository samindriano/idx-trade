from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_v3_kill_diagnosis import (  # noqa: E402
    DecisionV3KillDiagnosisError,
    verify_kill_diagnosis_prereg,
    write_kill_diagnosis_artifacts,
)
from idx_trade.decision_v3_kill_runner import (  # noqa: E402
    run_kill_diagnosis_safe,
)
from idx_trade.decision_v2_structural_replay import sha256_file  # noqa: E402


DEFAULT_HISTORICAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2"
)
DEFAULT_STRUCTURAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v2-minimal-structural-replay-20260821-v1"
)
EXECUTION_AUTHORIZATION = "DECISION_V3_KILL_DIAGNOSIS_REVIEW_ACCEPTED_V1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen outcome-blind Decision V3 prereg kill diagnosis "
            "without executing Decision V3."
        )
    )
    parser.add_argument(
        "--historical-root", type=Path, default=DEFAULT_HISTORICAL_ROOT
    )
    parser.add_argument(
        "--structural-root", type=Path, default=DEFAULT_STRUCTURAL_ROOT
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--authorization", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.authorization != EXECUTION_AUTHORIZATION:
        raise DecisionV3KillDiagnosisError(
            "DECISION_V3_KILL_DIAGNOSIS_NOT_REVIEW_AUTHORIZED"
        )
    verify_kill_diagnosis_prereg(REPO_ROOT)
    result = run_kill_diagnosis_safe(
        structural_root=args.structural_root,
        historical_root=args.historical_root,
    )
    manifest = write_kill_diagnosis_artifacts(result, args.output_dir)
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    print(f"manifest={manifest}")
    print(f"manifest_sha256={sha256_file(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
