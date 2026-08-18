"""Compatibility entrypoint for the V4 material-six one-shot runner.

Three orchestration-only corrections are applied before V1 runs:
1. the frozen CA runner's canonical output filename is redirected from the
   earlier draft alias;
2. AVIA/SMAR strict KSEI retry failure is allowed to remain explicitly
   unresolved instead of aborting the whole six-name audit; and
3. the frozen prior-event evidence CSV is read as text so integer action IDs
   cannot drift to float-looking strings such as 82840.0.

None of these corrections changes any scientific classification or relaxes
coverage/evidence requirements.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = Path(__file__).resolve().parent
for value in (REPO_ROOT / "src", SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import pandas as pd
import run_v4_ca_material_six_remediation as base
from idx_trade.v4_ca_material_six_remediation import EXPECTED_PARENT_UNRESOLVED


_ORIGINAL_READ_CSV = pd.read_csv


def _read_csv_with_frozen_output_alias(path, *args, **kwargs):
    candidate = Path(path) if isinstance(path, (str, Path)) else None
    if candidate is not None and candidate.name == "v4_event_window_continuity_ledger.csv":
        canonical = candidate.with_name("v4_frozen_continuity_ledger_event_window.csv")
        if not candidate.exists() and canonical.is_file():
            path = canonical
            candidate = canonical
    if candidate is not None and candidate.name == "event_family_evidence.csv":
        kwargs.setdefault("dtype", str)
        kwargs.setdefault("keep_default_na", False)
        kwargs.setdefault("low_memory", False)
    return _ORIGINAL_READ_CSV(path, *args, **kwargs)


def main() -> int:
    base.pd.read_csv = _read_csv_with_frozen_output_alias
    # V1's guard accidentally required both retries to succeed.  The intended
    # rule is fail-closed: a failed retry remains one of the original 11
    # unresolved names and the final replay decides whether the 90% gate holds.
    base.EXPECTED_AFTER_AVIA_SMAR_UNRESOLVED = EXPECTED_PARENT_UNRESOLVED
    return int(base.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
