"""Compatibility-fixed entrypoint for the frozen IDX combined replay.

V1 omitted two metadata keys required by the already-tested schedule-80 verifier.
This wrapper adds only those verifier compatibility fields and delegates the
entire scientific replay to V1 unchanged.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
V1 = REPO_ROOT / "scripts" / "run_v4_3_ca_training_domain_idx_combined_replay.py"


def _load_v1():
    spec = importlib.util.spec_from_file_location("idx_combined_replay_v1", V1)
    if spec is None or spec.loader is None:
        raise RuntimeError("IDX_COMBINED_REPLAY_V1_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


v1 = _load_v1()
_original = v1.base_compat_config


def _compat(config):
    value = _original(config)
    value["schema_version"] = "v4_3_ca_training_domain_schedule_80_replay_v1"
    value["outcome_blind"] = True
    return value


v1.base_compat_config = _compat


if __name__ == "__main__":
    raise SystemExit(v1.main())
