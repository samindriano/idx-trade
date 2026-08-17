"""Run the offline V4 CA voluntary-conversion semantic remediation.

This launcher reuses the frozen event-window support runner and changes only:

- the known 63-character KSEI census MANIFEST pin to its authoritative
  64-character SHA-256; and
- the event classifier to the preregistered voluntary security->currency
  remediation classifier.

No provider acquisition or schedule search is performed by this launcher.
"""

from __future__ import annotations

import run_v4_ca_event_window_support as frozen

from idx_trade.v4_ca_voluntary_conversion_semantics import (
    POLICY_ID,
    classify_event as classify_event_remediated,
)


BAD_KSEI_MANIFEST_SHA = (
    "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25"
)
GOOD_KSEI_MANIFEST_SHA = (
    "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25a"
)

_ORIGINAL_BUILD_WINDOW_LEDGER = frozen.build_window_ledger


def _remediated_build_window_ledger(*args, **kwargs):
    result = _ORIGINAL_BUILD_WINDOW_LEDGER(*args, **kwargs)
    result = result.copy()
    result["policy_id"] = POLICY_ID
    return result


def main() -> int:
    if frozen.PINNED.get("ksei_manifest") != BAD_KSEI_MANIFEST_SHA:
        raise RuntimeError("V4_CA_VC_REMEDIATION_UNEXPECTED_PARENT_KSEI_PIN")

    frozen.PINNED = dict(frozen.PINNED)
    frozen.PINNED["ksei_manifest"] = GOOD_KSEI_MANIFEST_SHA
    frozen.classify_event = classify_event_remediated
    frozen.build_window_ledger = _remediated_build_window_ledger
    return frozen.main()


if __name__ == "__main__":
    raise SystemExit(main())
