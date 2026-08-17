from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from v4_ca_input_pin_remediation import (  # noqa: E402
    BAD_KSEI_MANIFEST_SHA,
    GOOD_KSEI_MANIFEST_SHA,
    remediated_source_text,
)


def test_authoritative_ksei_manifest_pin_is_full_sha256():
    assert len(BAD_KSEI_MANIFEST_SHA) == 63
    assert len(GOOD_KSEI_MANIFEST_SHA) == 64
    assert GOOD_KSEI_MANIFEST_SHA == BAD_KSEI_MANIFEST_SHA + "a"


def test_remediation_overlay_pins_exact_authoritative_manifest_sha():
    payload = json.loads(
        (ROOT / "config/v4_ca_event_window_semantics_v1_input_pin_remediation.json").read_text(
            encoding="utf-8"
        )
    )
    correction = payload["correction"]
    assert correction["erroneous_literal"] == BAD_KSEI_MANIFEST_SHA
    assert correction["authoritative_sha256"] == GOOD_KSEI_MANIFEST_SHA
    assert correction["erroneous_literal_length"] == 63
    assert correction["authoritative_sha256_length"] == 64
    assert payload["scope"]["scientific_semantics_changed"] is False
    assert payload["scope"]["only_input_identity_pin_corrected"] is True


def test_frozen_runners_receive_only_the_exact_pin_replacement():
    for relative in (
        "scripts/run_v4_ca_event_window_support.py",
        "scripts/run_v4_ca_schedule_acquisition.py",
    ):
        path = ROOT / relative
        original = path.read_text(encoding="utf-8")
        assert original.count(BAD_KSEI_MANIFEST_SHA) == 1
        remediated = remediated_source_text(path)
        assert BAD_KSEI_MANIFEST_SHA not in remediated
        assert remediated.count(GOOD_KSEI_MANIFEST_SHA) == 1
        compile(remediated, str(path), "exec")
