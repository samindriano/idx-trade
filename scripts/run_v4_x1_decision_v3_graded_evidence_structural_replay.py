from __future__ import annotations

import argparse
from pathlib import Path

from idx_trade.decision_v3_structural_integrity import (
    validate_post_replay_integrity,
)
from idx_trade.decision_v3_structural_replay import (
    run_structural_replay,
    write_structural_replay_artifacts,
)
from idx_trade.decision_v3_structural_reporting import (
    enrich_structural_replay_reporting,
)
from idx_trade.decision_v3_structural_source import (
    DecisionV3StructuralReplayError,
    load_pinned_v4_x1_source_strict,
    verify_frozen_replay_contract,
)


DEFAULT_HISTORICAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2"
)
DEFAULT_OUTPUT_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v3-graded-evidence-structural-replay-20260821-v2"
)
AUTHORIZATION_TOKEN = (
    "DECISION_V3_GRADED_EVIDENCE_STRUCTURAL_REPLAY_RUNNER_AUDIT_ACCEPTED_V2"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the single frozen Decision V3 Graded Evidence V2 structural replay "
            "after runner audit acceptance."
        )
    )
    parser.add_argument(
        "--authorization-token",
        required=True,
        help="Process interlock token recorded only after independent runner audit.",
    )
    parser.add_argument(
        "--historical-root",
        type=Path,
        default=DEFAULT_HISTORICAL_ROOT,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    # Deliberately first: a caller without post-audit authorization cannot even
    # inspect or hash the historical source through this execution path.
    if args.authorization_token != AUTHORIZATION_TOKEN:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_AUTHORIZATION_TOKEN_REJECTED"
        )

    contract_path = verify_frozen_replay_contract(args.repo_root)
    source = load_pinned_v4_x1_source_strict(args.historical_root)
    result = run_structural_replay(source)
    result = validate_post_replay_integrity(result, source)
    result = enrich_structural_replay_reporting(result, contract_path)
    manifest_path = write_structural_replay_artifacts(result, args.output_dir)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
