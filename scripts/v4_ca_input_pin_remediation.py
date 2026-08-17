"""Preflight-only input identity remediation for V4 CA event-window runners.

This helper changes exactly one known malformed 63-character KSEI census
MANIFEST SHA literal into the authoritative 64-character SHA-256 before the
frozen runner is executed. It does not alter event semantics, gates, provider
scope, or any V4 target/model behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import MutableMapping, Any


BAD_KSEI_MANIFEST_SHA = (
    "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25"
)
GOOD_KSEI_MANIFEST_SHA = (
    "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25a"
)


def remediated_source_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    count = text.count(BAD_KSEI_MANIFEST_SHA)
    if count != 1:
        raise RuntimeError(
            f"V4_CA_PIN_REMEDIATION_EXPECTED_ONE_BAD_LITERAL:{path}:{count}"
        )
    remediated = text.replace(BAD_KSEI_MANIFEST_SHA, GOOD_KSEI_MANIFEST_SHA)
    if BAD_KSEI_MANIFEST_SHA in remediated:
        raise RuntimeError("V4_CA_PIN_REMEDIATION_BAD_LITERAL_REMAINS")
    if remediated.count(GOOD_KSEI_MANIFEST_SHA) != 1:
        raise RuntimeError("V4_CA_PIN_REMEDIATION_GOOD_LITERAL_COUNT_INVALID")
    return remediated


def execute_remediated_script(path: Path, globals_overrides: MutableMapping[str, Any] | None = None) -> None:
    source = remediated_source_text(path)
    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(path),
        "__package__": None,
    }
    if globals_overrides:
        namespace.update(dict(globals_overrides))
    exec(compile(source, str(path), "exec"), namespace, namespace)
