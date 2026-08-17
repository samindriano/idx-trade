"""Pre-run transport/parser hardening for official KSEI spelling variants.

KSEI schedule PDFs use both Indonesian spellings ``Pasar Reguler`` and
``Pasar Regular``.  The frozen semantic meaning is identical.  This launcher
normalizes only that literal spelling before the already-frozen schedule
parser and then executes the acquisition runner unchanged.
"""

from __future__ import annotations

from pathlib import Path
import runpy

import idx_trade.v4_ca_schedule_semantics as semantics


_original_parse = semantics.parse_ksei_schedule_transition


def _parse_with_official_spelling_normalization(text: str):
    normalized = str(text).replace("Pasar Regular", "Pasar Reguler")
    return _original_parse(normalized)


semantics.parse_ksei_schedule_transition = _parse_with_official_spelling_normalization

runpy.run_path(
    str(Path(__file__).with_name("run_v4_ca_schedule_acquisition.py")),
    run_name="__main__",
)
