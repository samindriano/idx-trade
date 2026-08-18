"""Hardened entrypoint for V4-3 schedule-80 offline adjudication.

V1 already freezes acquisition identity, candidate-document scope, raw hashes,
and the no-network/no-outcome boundaries.  V2 changes only the document parser
binding: every admissive cash/linkage/transition date must be recovered from an
explicit PDF-layout semantic row via ``parse_residual_document_hardened``.

This prevents flattened plain-text dates from becoming admissive evidence.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = Path(__file__).resolve().parent
for value in (SRC_ROOT, SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import run_v4_3_ca_training_domain_schedule_80_offline_adjudication as v1  # noqa: E402
from idx_trade.v4_ca_residual_document_semantics_hardened import (  # noqa: E402
    parse_residual_document_hardened,
)


def main() -> int:
    # The V1 runner resolves this global at execution time.  Rebind only the
    # parser; all input pins, candidate identities, hashes, output contract, and
    # scientific guardrails remain exactly those of V1.
    v1.parse_residual_document = parse_residual_document_hardened
    return v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
