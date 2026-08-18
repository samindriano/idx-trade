"""Run the frozen residual-document audit with layout-bound date hardening.

This launcher changes no evidence policy. It only replaces the pre-run parser
entrypoint so dates capable of admitting evidence must be bound to explicit
layout rows instead of flattened-text proximity.
"""

from __future__ import annotations

import run_v4_ca_residual_document_semantics as frozen

from idx_trade.v4_ca_residual_document_semantics_hardened import (
    parse_residual_document_hardened,
)


def main() -> int:
    frozen.parse_residual_document = parse_residual_document_hardened
    return frozen.main()


if __name__ == "__main__":
    raise SystemExit(main())
