from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_training_price_basis_impact_audit_v1_1.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("step2_v1_1_test_module", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_v1_1_pins_corrected_v2_file_and_key_sha_separately():
    runner = _load_runner()
    assert runner.V2_CLEAN_REPLAY_FILE_SHA256 == (
        "b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8"
    )
    assert runner.V2_CLEAN_REPLAY_KEY_SHA256 == (
        "79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826"
    )
    assert runner.impl.V2_CLEAN_REPLAY_TABLE_SHA256 == runner.V2_CLEAN_REPLAY_FILE_SHA256
    assert runner.impl.DEFAULT_V2_REPLAY_ROOT.name == (
        "pit_safe_v2_v3b_o2_reproduction_v1_20260813_002_fast_h10"
    )


def test_v1_1_key_hash_matches_frozen_key_contract_shape():
    runner = _load_runner()
    frame = pd.DataFrame(
        {
            "ticker": ["B", "A"],
            "date": [pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-01")],
            "signal_session_index": [2, 1],
        }
    )
    expected = hashlib.sha256(
        b"A|2020-01-01|1\nB|2020-01-02|2\n"
    ).hexdigest()
    assert runner._stable_key_hash(frame) == expected
