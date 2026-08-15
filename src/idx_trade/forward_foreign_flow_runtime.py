from __future__ import annotations

import argparse
import json
from pathlib import Path

from .forward_foreign_flow import (
    enrich_session_foreign_flow,
    inspect_session_foreign_flow,
    verify_session_foreign_flow,
)
from .forward_foreign_flow_setup import (
    enrich_session_foreign_flow_setup,
    inspect_session_foreign_flow_setup,
    verify_session_foreign_flow_setup,
)


def run_foreign_flow_catchup(runtime_root: str | Path) -> dict[str, object]:
    """Backfill missing sidecars from existing canonical session artifacts only.

    This runtime performs zero provider calls. It scans immutable DATA_READY session
    folders, derives a foreign-flow sidecar only when canonical Stock Summary bytes and
    the canonical manifest are present, and leaves existing valid sidecars untouched.
    """
    root = Path(runtime_root).expanduser().resolve()
    sessions_root = root / "forward_monitoring" / "sessions"
    result: dict[str, object] = {
        "status": "COMPLETE",
        "runtime_root": str(root),
        "provider_calls": 0,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "created": [],
        "already_valid": [],
        "verified": [],
        "skipped_no_stock_summary": [],
        "setup_state_created": [],
        "setup_state_already_valid": [],
        "setup_state_skipped_no_representation": [],
        "setup_state_verified": [],
        "failed": [],
    }
    if not sessions_root.exists():
        return result

    for directory in sorted(path for path in sessions_root.iterdir() if path.is_dir()):
        session = directory.name
        parent = directory / "manifest.json"
        raw = directory / "idx_stock_summary.raw.json"
        if not parent.exists() or not raw.exists():
            result["skipped_no_stock_summary"].append(session)
            continue
        if verify_session_foreign_flow(root, session):
            try:
                result["already_valid"].append(session)
                result["verified"].append(inspect_session_foreign_flow(root, session))
            except Exception as error:
                result["status"] = "INCOMPLETE"
                result["already_valid"].pop()
                result["failed"].append(
                    {
                        "session_date": session,
                        "error_code": type(error).__name__.upper(),
                        "error_message": str(error),
                    }
                )
        else:
            try:
                artifact = enrich_session_foreign_flow(root, session)
            except Exception as error:
                result["status"] = "INCOMPLETE"
                result["failed"].append(
                    {
                        "session_date": session,
                        "error_code": type(error).__name__.upper(),
                        "error_message": str(error),
                    }
                )
                continue
            result["created"].append(artifact)
            result["verified"].append(artifact)

        # Setup State is a consumer of an already materialized V2 representation,
        # not a second capture/calculation path.  Existing raw-flow sessions that
        # do not carry that input remain explicitly skipped and do not fail raw
        # Foreign Flow readiness.
        directory = sessions_root / session
        representation = directory / "foreign_flow_representation_v2.parquet"
        representation_manifest = directory / "foreign_flow_representation_v2.manifest.json"
        if not representation.exists() or not representation_manifest.exists():
            result["setup_state_skipped_no_representation"].append(session)
            continue
        try:
            if verify_session_foreign_flow_setup(root, session):
                result["setup_state_already_valid"].append(session)
                result["setup_state_verified"].append(
                    inspect_session_foreign_flow_setup(root, session)
                )
            else:
                setup_artifact = enrich_session_foreign_flow_setup(root, session)
                result["setup_state_created"].append(setup_artifact)
                result["setup_state_verified"].append(setup_artifact)
        except Exception as error:
            result["status"] = "INCOMPLETE"
            result["failed"].append(
                {
                    "session_date": session,
                    "error_code": f"SETUP_{type(error).__name__.upper()}",
                    "error_message": str(error),
                }
            )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create IDX foreign-flow sidecars from existing canonical EOD captures"
    )
    parser.add_argument("--runtime-root", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_foreign_flow_catchup(args.runtime_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
