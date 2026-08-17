"""Run targeted KSEI schedule acquisition with parser spelling + SHA pin remediation."""

from __future__ import annotations

from pathlib import Path

import idx_trade.v4_ca_schedule_semantics as semantics

from v4_ca_input_pin_remediation import execute_remediated_script


_original_parse = semantics.parse_ksei_schedule_transition


def _parse_with_official_spelling_normalization(text: str):
    normalized = str(text).replace("Pasar Regular", "Pasar Reguler")
    return _original_parse(normalized)


semantics.parse_ksei_schedule_transition = _parse_with_official_spelling_normalization
execute_remediated_script(Path(__file__).with_name("run_v4_ca_schedule_acquisition.py"))
