from __future__ import annotations

import argparse
from pathlib import Path

from idx_trade.decision_v3_structural_integrity import (
    validate_post_replay_integrity,
)
from idx_trade.decision_v3_structural_source import (
    DecisionV3StructuralReplayError,
    load_pinned_v4_x1_source_strict,
)
from idx_trade.decision_v4_structural_contract import (
    verify_frozen_v4_preregistration,
)
from idx_trade.decision_v4_structural_replay import (
    run_structural_replay_v4,
    write_structural_replay_artifacts_v4,
)


DEFAULT_HISTORICAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2"
)
DEFAULT_OUTPUT_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-decision-v4-refill-decoupling-structural-replay-20260822-v1"
)
AUTHORIZATION_TOKEN = (
    "DECISION_V4_REFILL_DECOUPLING_STRUCTURAL_REPLAY_RUNNER_AUDIT_ACCEPTED_V1"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the single frozen Decision V4 Refill Decoupling structural replay "
            "only after independent runner audit acceptance."
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

    # Deliberately first. Without post-audit authorization, this path may not
    # inspect/hash the frozen preregistration or historical rank source.
    if args.authorization_token != AUTHORIZATION_TOKEN:
        raise DecisionV3StructuralReplayError(
            "DECISION_V4_REPLAY_AUTHORIZATION_TOKEN_REJECTED"
        )

    verify_frozen_v4_preregistration(args.repo_root)
    source = load_pinned_v4_x1_source_strict(args.historical_root)
    result = run_structural_replay_v4(source)
    result = validate_post_replay_integrity(result, source)
    manifest_path = write_structural_replay_artifacts_v4(result, args.output_dir)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
