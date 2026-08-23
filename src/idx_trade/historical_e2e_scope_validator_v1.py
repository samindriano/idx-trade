"""Fail-closed validation for an outcome-blind historical E2E scope.

This module validates only the JSON scope contract.  It does not load source
artifacts, call providers, inspect outcomes, fit models, or derive any replay
result.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SCHEMA_VERSION = "idx_trade_historical_e2e_scope_v1"
STRICT_SCOPE_FROZEN = "STRICT_SCOPE_FROZEN"
STRICT_SCOPE_EMPTY_BLOCKED = "STRICT_SCOPE_EMPTY_BLOCKED"
EXPECTED_CANDIDATE_SESSION_COUNT = 600
STRICT_BLOCK_COUNT = 6
STRICT_BLOCK_SIZE = 100
_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
_MISSING = object()


class HistoricalE2EScopeValidationError(ValueError):
    """Raised when a replay scope is missing, malformed, or unsafe to use."""


# Keep a short, discoverable alias for callers that use the repository's
# existing ``...Error`` naming convention.
HistoricalE2EScopeError = HistoricalE2EScopeValidationError


def _error(code: str, detail: str | None = None) -> None:
    if detail is None:
        raise HistoricalE2EScopeValidationError(code)
    raise HistoricalE2EScopeValidationError(f"{code}:{detail}")


def _require_mapping(value: object, code: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _error(code)
    if not all(isinstance(key, str) for key in value):
        _error(code)
    return dict(value)


def _require_false(payload: Mapping[str, object], field_name: str) -> None:
    if payload.get(field_name, _MISSING) is not False:
        _error(f"REPLAY_SCOPE_{field_name.upper()}_FLAG_INVALID")


def _require_sha256(value: object, code: str, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        _error(code, field_name)
    return value


def _require_iso_date(row: Mapping[str, object], field_name: str, position: int) -> str:
    value = row.get(field_name, _MISSING)
    if not isinstance(value, str) or not value:
        _error("REPLAY_SCOPE_SESSION_DATE_MISSING", f"{position}.{field_name}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise HistoricalE2EScopeValidationError(
            f"REPLAY_SCOPE_SESSION_DATE_INVALID:{position}.{field_name}"
        ) from exc
    if parsed.isoformat() != value:
        _error("REPLAY_SCOPE_SESSION_DATE_INVALID", f"{position}.{field_name}")
    return value


def canonical_scope_payload_hash(payload: Mapping[str, object]) -> str:
    """Return the deterministic hash used by ``REPLAY_SCOPE.json``.

    The declared ``scope_payload_sha256`` field is excluded by the caller
    before invoking this function, matching the existing scope freezer.
    """

    try:
        encoded = (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise HistoricalE2EScopeValidationError(
            "REPLAY_SCOPE_PAYLOAD_HASH_INPUT_INVALID"
        ) from exc
    return hashlib.sha256(encoded).hexdigest()


def _validate_payload_hash(payload: Mapping[str, object]) -> None:
    declared = payload.get("scope_payload_sha256", _MISSING)
    if declared is _MISSING:
        _error("REPLAY_SCOPE_PAYLOAD_HASH_MISSING")
    declared_hash = _require_sha256(
        declared,
        "REPLAY_SCOPE_PAYLOAD_HASH_INVALID",
        "scope_payload_sha256",
    )
    body = dict(payload)
    body.pop("scope_payload_sha256", None)
    try:
        actual_hash = canonical_scope_payload_hash(body)
    except HistoricalE2EScopeValidationError as exc:
        _error("REPLAY_SCOPE_PAYLOAD_HASH_INVALID", str(exc))
    if actual_hash != declared_hash.lower():
        _error("REPLAY_SCOPE_PAYLOAD_HASH_MISMATCH")


def _validate_candidate_sessions(payload: Mapping[str, object]) -> list[int]:
    candidate_count = payload.get("candidate_session_count", _MISSING)
    if (
        type(candidate_count) is not int
        or candidate_count != EXPECTED_CANDIDATE_SESSION_COUNT
    ):
        _error("REPLAY_SCOPE_CANDIDATE_SESSION_COUNT_INVALID")

    open_payload = _require_mapping(
        payload.get("open", _MISSING),
        "REPLAY_SCOPE_OPEN_SCHEMA_INVALID",
    )
    per_session = open_payload.get("per_session", _MISSING)
    if not isinstance(per_session, list):
        _error("REPLAY_SCOPE_CANDIDATE_SESSIONS_INVALID")
    if len(per_session) != EXPECTED_CANDIDATE_SESSION_COUNT:
        _error("REPLAY_SCOPE_CANDIDATE_SESSION_COUNT_MISMATCH")

    indices: list[int] = []
    seen_indices: set[int] = set()
    seen_identities: set[tuple[str, str]] = set()
    for position, raw_row in enumerate(per_session):
        row = _require_mapping(raw_row, "REPLAY_SCOPE_SESSION_ROW_INVALID")
        raw_index = row.get("session_index", _MISSING)
        if type(raw_index) is not int or raw_index < 0:
            _error("REPLAY_SCOPE_SESSION_INDEX_INVALID", str(position))
        if raw_index in seen_indices:
            _error("REPLAY_SCOPE_SESSION_INDEX_DUPLICATE", str(raw_index))
        if indices and raw_index <= indices[-1]:
            _error("REPLAY_SCOPE_SESSION_INDICES_NOT_ORDERED", str(position))
        decision_date = _require_iso_date(row, "decision_session_date", position)
        execution_date = _require_iso_date(row, "execution_session_date", position)
        identity = (decision_date, execution_date)
        if identity in seen_identities:
            _error(
                "REPLAY_SCOPE_SESSION_IDENTITY_DUPLICATE",
                f"{decision_date}/{execution_date}",
            )
        seen_indices.add(raw_index)
        seen_identities.add(identity)
        indices.append(raw_index)
    if indices != list(range(EXPECTED_CANDIDATE_SESSION_COUNT)):
        _error("REPLAY_SCOPE_SESSION_INDEX_SET_INVALID")
    return indices


def _validate_strict_indices(
    payload: Mapping[str, object],
    status: str,
    candidate_indices: list[int],
) -> None:
    raw_strict_indices = payload.get("strict_session_indices", _MISSING)
    if not isinstance(raw_strict_indices, list):
        _error("REPLAY_SCOPE_STRICT_SESSION_INDICES_INVALID")
    strict_indices = raw_strict_indices

    if status == STRICT_SCOPE_EMPTY_BLOCKED:
        if strict_indices:
            _error("REPLAY_SCOPE_NONEMPTY_SCOPE_STATUS_INVALID")
        return

    if not strict_indices:
        _error("REPLAY_SCOPE_EMPTY_STRICT_SCOPE_INVALID")
    if len(strict_indices) != EXPECTED_CANDIDATE_SESSION_COUNT:
        _error("REPLAY_SCOPE_STRICT_SESSION_COUNT_INVALID")

    normalized: list[int] = []
    seen: set[int] = set()
    for position, raw_index in enumerate(strict_indices):
        if type(raw_index) is not int or raw_index < 0:
            _error("REPLAY_SCOPE_STRICT_SESSION_INDEX_INVALID", str(position))
        if raw_index in seen:
            _error("REPLAY_SCOPE_STRICT_SESSION_INDEX_DUPLICATE", str(raw_index))
        if normalized and raw_index <= normalized[-1]:
            _error("REPLAY_SCOPE_STRICT_SESSION_INDICES_NOT_ORDERED", str(position))
        seen.add(raw_index)
        normalized.append(raw_index)

    if normalized != candidate_indices:
        _error("REPLAY_SCOPE_STRICT_SESSION_INDEX_SET_INVALID")

    if len(normalized) != STRICT_BLOCK_COUNT * STRICT_BLOCK_SIZE:
        _error("REPLAY_SCOPE_BLOCK_GEOMETRY_INVALID")
    for block_number in range(STRICT_BLOCK_COUNT):
        start = block_number * STRICT_BLOCK_SIZE
        block = normalized[start : start + STRICT_BLOCK_SIZE]
        if len(block) != STRICT_BLOCK_SIZE:
            _error("REPLAY_SCOPE_BLOCK_GEOMETRY_INVALID", str(block_number))
        if block != list(range(block[0], block[0] + STRICT_BLOCK_SIZE)):
            _error("REPLAY_SCOPE_BLOCK_NOT_CONTIGUOUS", str(block_number))
        if block_number and block[0] != normalized[start - 1] + 1:
            _error("REPLAY_SCOPE_BLOCKS_NOT_CONTIGUOUS", str(block_number))


def validate_scope_payload(payload: object) -> dict[str, Any]:
    """Validate and return a replay scope payload without opening any data.

    Both an empty blocked scope and a fully frozen strict scope are valid
    statuses.  Only the latter may carry a non-empty strict session list.
    """

    root = _require_mapping(payload, "REPLAY_SCOPE_SCHEMA_INVALID")
    if root.get("schema_version", _MISSING) != SCHEMA_VERSION:
        _error("REPLAY_SCOPE_SCHEMA_VERSION_INVALID")
    status = root.get("status", _MISSING)
    if status not in {STRICT_SCOPE_FROZEN, STRICT_SCOPE_EMPTY_BLOCKED}:
        _error("REPLAY_SCOPE_STATUS_INVALID")

    _require_false(root, "outcome_access")
    _require_false(root, "model_fit")
    _require_false(root, "protected_outcome_access")

    source_pins = _require_mapping(
        root.get("source_pins", _MISSING),
        "REPLAY_SCOPE_SOURCE_PINS_INVALID",
    )
    if not source_pins:
        _error("REPLAY_SCOPE_SOURCE_PINS_EMPTY")
    for field_name, value in source_pins.items():
        if not field_name:
            _error("REPLAY_SCOPE_SOURCE_PIN_INVALID", "empty_name")
        _require_sha256(value, "REPLAY_SCOPE_SOURCE_PIN_INVALID", field_name)

    candidate_indices = _validate_candidate_sessions(root)
    _validate_strict_indices(root, status, candidate_indices)
    _validate_payload_hash(root)
    return root


def load_replay_scope(path: str | Path) -> dict[str, Any]:
    """Load and validate one ``REPLAY_SCOPE.json`` file."""

    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        _error("REPLAY_SCOPE_FILE_MISSING", str(resolved))
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HistoricalE2EScopeValidationError(
            f"REPLAY_SCOPE_JSON_INVALID:{resolved}"
        ) from exc
    return validate_scope_payload(payload)


# Explicit aliases keep the module easy to consume without changing the
# validation surface or introducing a dependency on the existing replay code.
validate_replay_scope_payload = validate_scope_payload
validate_historical_e2e_scope = validate_scope_payload


__all__ = [
    "EXPECTED_CANDIDATE_SESSION_COUNT",
    "HistoricalE2EScopeError",
    "HistoricalE2EScopeValidationError",
    "SCHEMA_VERSION",
    "STRICT_BLOCK_COUNT",
    "STRICT_BLOCK_SIZE",
    "STRICT_SCOPE_EMPTY_BLOCKED",
    "STRICT_SCOPE_FROZEN",
    "canonical_scope_payload_hash",
    "load_replay_scope",
    "validate_historical_e2e_scope",
    "validate_replay_scope_payload",
    "validate_scope_payload",
]
