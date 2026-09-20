"""Fail-closed security identity and revision contract for runtime joins."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re
from typing import Sequence

from .v4_x1_decision_v1_contract import DecisionV1Error


IDENTITY_SCHEMA = "idx_trade_security_identity_v1"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, code: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise DecisionV1Error(code)
    return text


def _ticker(value: object) -> str:
    normalized = _text(value, "SECURITY_IDENTITY_TICKER_INVALID").upper().replace(".JK", "")
    if not normalized:
        raise DecisionV1Error("SECURITY_IDENTITY_TICKER_INVALID")
    return normalized


def _day(value: object, code: str) -> str:
    text = _text(value, code)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise DecisionV1Error(code) from exc
    if parsed.isoformat() != text:
        raise DecisionV1Error(code)
    return text


def _sha(value: object) -> str:
    text = _text(value, "SECURITY_IDENTITY_SOURCE_SHA_INVALID").lower()
    if not _SHA_RE.fullmatch(text):
        raise DecisionV1Error("SECURITY_IDENTITY_SOURCE_SHA_INVALID")
    return text


@dataclass(frozen=True)
class SecurityIdentityV1:
    canonical_security_id: str
    ticker: str
    instrument_class: str
    effective_from: str
    effective_to: str | None
    identity_revision: str
    source_ref: str
    source_evidence_sha256: str

    def validate(self) -> "SecurityIdentityV1":
        canonical = _text(
            self.canonical_security_id,
            "SECURITY_IDENTITY_CANONICAL_ID_INVALID",
        )
        ticker = _ticker(self.ticker)
        instrument_class = _text(
            self.instrument_class,
            "SECURITY_IDENTITY_CLASS_INVALID",
        ).upper()
        start = _day(self.effective_from, "SECURITY_IDENTITY_EFFECTIVE_FROM_INVALID")
        end = (
            None
            if self.effective_to is None
            else _day(self.effective_to, "SECURITY_IDENTITY_EFFECTIVE_TO_INVALID")
        )
        if end is not None and end < start:
            raise DecisionV1Error("SECURITY_IDENTITY_INTERVAL_INVALID")
        revision = _text(self.identity_revision, "SECURITY_IDENTITY_REVISION_INVALID")
        source_ref = _text(self.source_ref, "SECURITY_IDENTITY_SOURCE_REF_INVALID")
        source_sha = _sha(self.source_evidence_sha256)
        normalized = SecurityIdentityV1(
            canonical_security_id=canonical,
            ticker=ticker,
            instrument_class=instrument_class,
            effective_from=start,
            effective_to=end,
            identity_revision=revision,
            source_ref=source_ref,
            source_evidence_sha256=source_sha,
        )
        if normalized != self:
            raise DecisionV1Error("SECURITY_IDENTITY_NOT_CANONICAL")
        return self


def _overlap(left: SecurityIdentityV1, right: SecurityIdentityV1) -> bool:
    left_end = left.effective_to or "9999-12-31"
    right_end = right.effective_to or "9999-12-31"
    return left.effective_from <= right_end and right.effective_from <= left_end


def normalize_security_identities(
    rows: Sequence[SecurityIdentityV1],
) -> tuple[SecurityIdentityV1, ...]:
    normalized = tuple(row.validate() for row in rows)
    by_revision: dict[tuple[str, str], SecurityIdentityV1] = {}
    for row in normalized:
        key = (row.canonical_security_id, row.identity_revision)
        prior = by_revision.get(key)
        if prior is not None and prior != row:
            raise DecisionV1Error("SECURITY_IDENTITY_REVISION_CONFLICT")
        by_revision[key] = row
    ordered = tuple(sorted(by_revision.values(), key=lambda row: (
        row.ticker,
        row.effective_from,
        row.canonical_security_id,
        row.identity_revision,
    )))
    for index, left in enumerate(ordered):
        for right in ordered[index + 1:]:
            if not _overlap(left, right):
                continue
            if left.ticker == right.ticker and left.canonical_security_id != right.canonical_security_id:
                raise DecisionV1Error("SECURITY_IDENTITY_ALIAS_CONFLICT")
            if left.canonical_security_id == right.canonical_security_id and left.identity_revision != right.identity_revision:
                raise DecisionV1Error("SECURITY_IDENTITY_REVISION_OVERLAP")
    return ordered


def resolve_security_identity(
    rows: Sequence[SecurityIdentityV1],
    *,
    ticker: str,
    as_of_session_date: str,
) -> SecurityIdentityV1:
    normalized = normalize_security_identities(rows)
    session = _day(as_of_session_date, "SECURITY_IDENTITY_SESSION_INVALID")
    symbol = _ticker(ticker)
    matches = tuple(
        row for row in normalized
        if row.ticker == symbol
        and row.effective_from <= session
        and (row.effective_to is None or session <= row.effective_to)
    )
    if not matches:
        raise DecisionV1Error("SECURITY_IDENTITY_UNRESOLVED")
    if len(matches) != 1:
        raise DecisionV1Error("SECURITY_IDENTITY_AMBIGUOUS")
    return matches[0]


def security_identity_hash(rows: Sequence[SecurityIdentityV1]) -> str:
    payload = [
        {
            "schema_version": IDENTITY_SCHEMA,
            "canonical_security_id": row.canonical_security_id,
            "ticker": row.ticker,
            "instrument_class": row.instrument_class,
            "effective_from": row.effective_from,
            "effective_to": row.effective_to,
            "identity_revision": row.identity_revision,
            "source_ref": row.source_ref,
            "source_evidence_sha256": row.source_evidence_sha256,
        }
        for row in normalize_security_identities(rows)
    ]
    return hashlib.sha256(
        (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()


__all__ = [
    "IDENTITY_SCHEMA",
    "SecurityIdentityV1",
    "normalize_security_identities",
    "resolve_security_identity",
    "security_identity_hash",
]
