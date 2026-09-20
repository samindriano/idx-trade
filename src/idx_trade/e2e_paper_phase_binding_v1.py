"""Mandatory external runtime binding for E2E PAPER phase child processes."""

from __future__ import annotations

from pathlib import Path

from .e2e_paper_runtime_config_v1 import (
    E2ERuntimeConfigError,
    load_runtime_config,
)
from .e2e_paper_runtime_config_v2 import load_runtime_config_v2


def load_phase_runtime_binding(
    runtime_root: str | Path,
    *,
    expected_branch: str,
    expected_commit: str,
    dual_calendar: bool = False,
) -> str:
    """Return the hash of the one config snapshot that binds a phase child.

    Phase scripts are only valid as scheduled children when the external
    configuration exists, is hash-pinned, and names the same repository
    identity that the parent controller supplied. V2 additionally verifies
    its planned schedule through the dual-calendar config loader.
    """

    loaded = (
        load_runtime_config_v2(runtime_root)
        if dual_calendar
        else load_runtime_config(runtime_root)
    )
    configured_branch = str(loaded.controller.expected_branch).strip()
    configured_commit = str(loaded.controller.expected_commit).strip().lower()
    if (
        configured_branch != str(expected_branch).strip()
        or configured_commit != str(expected_commit).strip().lower()
    ):
        raise E2ERuntimeConfigError("E2E_PHASE_RUNTIME_REPO_IDENTITY_MISMATCH")
    return loaded.config_sha256


__all__ = ["load_phase_runtime_binding"]
