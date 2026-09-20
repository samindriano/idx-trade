"""Hash-pinned caller-supplied security identity evidence for E2E children."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Sequence

from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_identity_contract_v1 import (
    SecurityIdentityV1,
    normalize_security_identities,
    resolve_security_identity,
)


IDENTITY_EVIDENCE_SCHEMA = "idx_trade_security_identity_evidence_v1"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_EVIDENCE_KEYS = frozenset(
    {
        "schema_version",
        "source_reference",
        "as_of_session_date",
        "identities",
        "outcome_access",
    }
)
_IDENTITY_ROW_KEYS = frozenset(
    {
        "canonical_security_id",
        "ticker",
        "instrument_class",
        "effective_from",
        "effective_to",
        "identity_revision",
        "source_ref",
        "source_evidence_sha256",
    }
)


class IdentityEvidenceError(RuntimeError):
    """Raised when external identity evidence is absent, stale, or invalid."""


@dataclass(frozen=True)
class LoadedIdentityEvidence:
    path: Path
    file_sha256: str
    as_of_session_date: str
    identities: tuple[SecurityIdentityV1, ...]


def _canonical_hash(value: object) -> str:
    encoded = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise IdentityEvidenceError(f"IDENTITY_EVIDENCE_FIELD_MISSING:{key}")
    return value.strip()


def load_identity_evidence(
    path: str | Path,
    expected_sha256: str,
    *,
    as_of_session_date: str,
    required_tickers: Sequence[str] = (),
) -> tuple[SecurityIdentityV1, ...]:
    """Load one immutable identity artifact and resolve the required tickers."""

    target = Path(path).expanduser().resolve()
    expected = str(expected_sha256 or "").strip().lower()
    if not _SHA_RE.fullmatch(expected):
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_FILE_SHA_INVALID")
    if not target.is_file():
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_FILE_MISSING")
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_FILE_UNREADABLE") from exc
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_FILE_SHA_MISMATCH")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_JSON_INVALID") from exc
    if not isinstance(payload, dict):
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_PAYLOAD_INVALID")
    raw_declared = payload.get("payload_sha256")
    if (
        not isinstance(raw_declared, str)
        or raw_declared != raw_declared.lower()
        or not _SHA_RE.fullmatch(raw_declared)
    ):
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_PAYLOAD_SHA_MISMATCH")
    body = dict(payload)
    declared = body.pop("payload_sha256")
    if _canonical_hash(body) != declared:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_PAYLOAD_SHA_MISMATCH")
    if set(body) != _EVIDENCE_KEYS:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_PAYLOAD_NOT_CANONICAL")
    if payload.get("schema_version") != IDENTITY_EVIDENCE_SCHEMA:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_SCHEMA_MISMATCH")
    if payload.get("outcome_access") is not False:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_OUTCOME_ACCESS_INVALID")
    if payload.get("as_of_session_date") != as_of_session_date:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_SESSION_MISMATCH")
    source_reference = _required_text(payload, "source_reference")
    if source_reference != payload["source_reference"]:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_FIELD_NOT_CANONICAL:source_reference")
    try:
        parsed_as_of = date.fromisoformat(str(payload["as_of_session_date"]))
    except ValueError as exc:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_SESSION_MISMATCH") from exc
    if parsed_as_of.isoformat() != payload["as_of_session_date"]:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_SESSION_MISMATCH")
    raw_rows = payload.get("identities")
    if not isinstance(raw_rows, list) or not raw_rows:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_ROWS_MISSING")
    rows: list[SecurityIdentityV1] = []
    for raw_row in raw_rows:
        if not isinstance(raw_row, dict) or set(raw_row) != _IDENTITY_ROW_KEYS:
            raise IdentityEvidenceError("IDENTITY_EVIDENCE_ROW_INVALID")
        try:
            rows.append(SecurityIdentityV1(**raw_row).validate())
        except (TypeError, DecisionV1Error) as exc:
            raise IdentityEvidenceError("IDENTITY_EVIDENCE_ROW_INVALID") from exc
    try:
        normalized = normalize_security_identities(rows)
        for ticker in required_tickers:
            resolve_security_identity(
                normalized,
                ticker=str(ticker),
                as_of_session_date=as_of_session_date,
            )
    except DecisionV1Error as exc:
        raise IdentityEvidenceError("IDENTITY_EVIDENCE_REQUIRED_TICKER_UNRESOLVED") from exc
    return normalized


__all__ = [
    "IDENTITY_EVIDENCE_SCHEMA",
    "IdentityEvidenceError",
    "LoadedIdentityEvidence",
    "load_identity_evidence",
]
