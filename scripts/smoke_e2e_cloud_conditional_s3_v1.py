"""Opt-in live smoke test for the E2E conditional S3/R2 store.

This command is deliberately inert unless the exact activation flag is
provided.  It writes only to a caller-supplied throwaway prefix and never
deletes objects.  It does not access IDX providers, models, PaperState, or
outcomes.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.e2e_paper_cloud_runtime_v1 import (
    ConditionalS3Store,
    StorageImmutabilityConflict,
    build_cloud_store_from_env,
    sha256_bytes,
)


ACTIVATION = "RUN_LIVE_CONDITIONAL_S3_SMOKE_V1"


def run_smoke(store: Any, *, key: str = "probe/payload.bin") -> dict[str, object]:
    payload = b"idx-trade-conditional-s3-smoke-v1\n"
    conflicting = b"idx-trade-conditional-s3-smoke-v1-conflict\n"
    first = store.put_if_absent(key, payload, "application/octet-stream")
    replay = store.put_if_absent(key, payload, "application/octet-stream")
    conflict_rejected = False
    try:
        store.put_if_absent(key, conflicting, "application/octet-stream")
    except StorageImmutabilityConflict:
        conflict_rejected = True
    observed = store.read(key)
    expected_sha = sha256_bytes(payload)
    if not first.created or replay.created or not conflict_rejected:
        raise RuntimeError("CONDITIONAL_S3_SMOKE_CREATE_ONLY_CONTRACT_FAILED")
    if observed is None or sha256_bytes(observed) != expected_sha:
        raise RuntimeError("CONDITIONAL_S3_SMOKE_READBACK_SHA_FAILED")
    return {
        "status": "PASS",
        "first_write_created": first.created,
        "identical_replay_created": replay.created,
        "conflicting_write_rejected": conflict_rejected,
        "readback_sha256": expected_sha,
        "key": key,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--activate", default="")
    parser.add_argument(
        "--prefix",
        required=True,
        help="Throwaway E2E_CLOUD storage prefix; objects are intentionally retained.",
    )
    args = parser.parse_args()
    if args.activate != ACTIVATION:
        print(
            json.dumps(
                {
                    "status": "NOT_RUN",
                    "reason": "EXPLICIT_ACTIVATION_REQUIRED",
                    "activation": ACTIVATION,
                },
                sort_keys=True,
            )
        )
        return 2
    prefix = str(args.prefix).strip().strip("/")
    if not prefix or ".." in prefix.split("/"):
        raise SystemExit("throwaway prefix must be non-empty and safe")
    env = dict(os.environ)
    env["E2E_CLOUD_LIVE_SMOKE_PREFIX"] = prefix
    store = build_cloud_store_from_env(env, prefix_key="E2E_CLOUD_LIVE_SMOKE_PREFIX")
    if not isinstance(store, ConditionalS3Store):
        raise SystemExit("live conditional S3 smoke requires E2E_CLOUD_STORAGE_BACKEND=s3")
    print(json.dumps(run_smoke(store), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
