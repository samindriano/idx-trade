"""Dual-calendar external config loader for the E2E PAPER controller."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .e2e_paper_operational_controller_v2 import OperationalControllerConfigV2
from .e2e_paper_runtime_config_v1 import (
    E2ERuntimeConfigError,
    LoadedRuntimeConfig,
    load_runtime_config as load_runtime_config_v1,
)
from .official_trading_schedule_v1 import (
    OfficialTradingScheduleError,
    load_verified_official_trading_schedule,
)


CONTRACT_VERSION = "DUAL_CALENDAR_V1"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class LoadedRuntimeConfigV2:
    config_path: Path
    config_sha256: str
    runner_sha256: str
    controller: OperationalControllerConfigV2


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise E2ERuntimeConfigError(f"E2E_RUNTIME_CONFIG_FIELD_MISSING:{key}")
    return value.strip()


def load_runtime_config_v2(
    runtime_root: str | Path,
    *,
    expected_sha256: str | None = None,
) -> LoadedRuntimeConfigV2:
    """Load V1 deployment bindings plus the separately pinned planned schedule."""

    base: LoadedRuntimeConfig = load_runtime_config_v1(
        runtime_root, expected_sha256=expected_sha256
    )
    try:
        payload = json.loads(base.config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_INVALID_JSON") from exc
    if not isinstance(payload, dict):
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_INVALID_JSON")
    if payload.get("operational_contract_version") != CONTRACT_VERSION:
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_DUAL_CALENDAR_CONTRACT_MISSING")

    raw_path = _required_text(payload, "execution_schedule_attestation_path")
    schedule_path = Path(raw_path).expanduser()
    if not schedule_path.is_absolute():
        raise E2ERuntimeConfigError(
            "E2E_RUNTIME_CONFIG_PATH_NOT_ABSOLUTE:execution_schedule_attestation_path"
        )
    schedule_path = schedule_path.resolve()
    schedule_sha = _required_text(
        payload, "execution_schedule_attestation_sha256"
    ).lower()
    if not _SHA_RE.fullmatch(schedule_sha):
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_EXECUTION_SCHEDULE_SHA_INVALID")
    try:
        verified = load_verified_official_trading_schedule(
            schedule_path, expected_sha256=schedule_sha
        )
    except OfficialTradingScheduleError as exc:
        raise E2ERuntimeConfigError(
            f"E2E_RUNTIME_CONFIG_EXECUTION_SCHEDULE_INVALID:{exc}"
        ) from exc

    controller = OperationalControllerConfigV2(
        base=base.controller,
        execution_schedule_attestation_path=verified.attestation_path,
        execution_schedule_attestation_sha256=verified.attestation_sha256,
    )
    return LoadedRuntimeConfigV2(
        config_path=base.config_path,
        config_sha256=base.config_sha256,
        runner_sha256=base.runner_sha256,
        controller=controller,
    )


__all__ = [
    "CONTRACT_VERSION",
    "LoadedRuntimeConfigV2",
    "load_runtime_config_v2",
]
