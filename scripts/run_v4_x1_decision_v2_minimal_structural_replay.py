from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.decision_v2_structural_replay import (  # noqa: E402
    DecisionV2StructuralReplayError,
    run_structural_replay,
    sha256_file,
    write_structural_replay_artifacts,
)
from idx_trade.decision_v2_structural_source import (  # noqa: E402
    load_pinned_v4_x1_source_strict,
    verify_frozen_replay_contract,
)


DEFAULT_HISTORICAL_ROOT = Path(
    r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2"
)
EXECUTION_AUTHORIZATION = "DECISION_V2_MINIMAL_STRUCTURAL_REPLAY_REVIEW_ACCEPTED_V1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the single guarded outcome-blind Decision V2 Minimal "
            "structural replay on the pinned exact 600-OOS V4-X1 score path."
        )
    )
    parser.add_argument(
        "--historical-root",
        type=Path,
        default=DEFAULT_HISTORICAL_ROOT,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--authorization",
        required=True,
        help=(
            "Must equal the post-review execution token. The runner is "
            "deliberately non-executable before independent runner review."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.authorization != EXECUTION_AUTHORIZATION:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_STRUCTURAL_REPLAY_NOT_REVIEW_AUTHORIZED"
        )

    # Pin the local executable contract itself before any historical data read.
    verify_frozen_replay_contract(REPO_ROOT)
    source = load_pinned_v4_x1_source_strict(args.historical_root)
    result = run_structural_replay(source)
    manifest_path = write_structural_replay_artifacts(
        result,
        args.output_dir,
    )

    print(json.dumps(result.summary, indent=2, sort_keys=True))
    print(f"manifest={manifest_path}")
    print(f"manifest_sha256={sha256_file(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
