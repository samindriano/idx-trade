"""Compatibility entrypoint for the V4 material-six one-shot runner.

The frozen CA runner's canonical output name is
`v4_frozen_continuity_ledger_event_window.csv`.  V1 of the orchestration runner
looked for an earlier draft alias after the replay had already completed.  This
entrypoint redirects only that post-replay read; it changes no scientific
logic, inputs, provider calls, or continuity classification.
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


_ORIGINAL_READ_CSV = pd.read_csv


def _read_csv_with_frozen_output_alias(path, *args, **kwargs):
    candidate = Path(path) if isinstance(path, (str, Path)) else None
    if candidate is not None and candidate.name == "v4_event_window_continuity_ledger.csv":
        canonical = candidate.with_name("v4_frozen_continuity_ledger_event_window.csv")
        if not candidate.exists() and canonical.is_file():
            path = canonical
    return _ORIGINAL_READ_CSV(path, *args, **kwargs)


def main() -> int:
    base.pd.read_csv = _read_csv_with_frozen_output_alias
    return int(base.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
