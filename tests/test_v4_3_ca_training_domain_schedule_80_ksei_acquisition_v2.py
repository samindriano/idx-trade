from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_v4_3_ca_training_domain_schedule_80_ksei_acquisition_v2 as v2


def test_required_int_accepts_zero() -> None:
    assert v2._required_int({"resolved_existing_evidence_events": 0}, "resolved_existing_evidence_events", "missing") == 0


def test_required_int_rejects_missing_not_zero() -> None:
    with pytest.raises(RuntimeError, match="missing"):
        v2._required_int({}, "resolved_existing_evidence_events", "missing")


def test_wrapper_replaces_only_reuse_verifier_before_v1_main() -> None:
    original = v2.v1.verify_reuse_root
    original_main = v2.v1.main
    observed = {}

    def fake_main() -> int:
        observed["verifier"] = v2.v1.verify_reuse_root
        return 0

    try:
        v2.v1.main = fake_main
        assert v2.main() == 0
        assert observed["verifier"] is v2.verify_reuse_root_zero_safe
    finally:
        v2.v1.verify_reuse_root = original
        v2.v1.main = original_main
