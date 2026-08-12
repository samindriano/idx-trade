from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import pandas as pd

from .security_master import normalise_ticker


DISCOVERY_ROLES = {
    "SECONDARY_DISCOVERY_NOT_CANONICAL",
    "ISSUER_CORROBORATION_NOT_CANONICAL",
    "BROKER_MIRROR_NOT_CANONICAL",
}
REQUIRED_EVIDENCE_FIELDS = {
    "evidence_id",
    "canonical_source_id",
    "role",
    "publisher",
    "published_at",
    "url",
    "claims",
    "note",
}


def _https_url(value: object) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme.lower() == "https" and bool(parsed.hostname)


def _date(value: object, *, field: str, evidence_id: str) -> pd.Timestamp:
    try:
        parsed = pd.Timestamp(value).normalize()
    except Exception as error:  # pragma: no cover - pandas error shape varies
        raise ValueError(f"invalid {field} for {evidence_id}") from error
    if pd.isna(parsed):
        raise ValueError(f"invalid {field} for {evidence_id}")
    return parsed


def validate_discovery_evidence_registry(
    payload: dict[str, Any],
    canonical_inventory: dict[str, Any],
) -> dict[str, Any]:
    """Validate non-canonical PIT-sector recovery evidence.

    This registry is deliberately incapable of satisfying the canonical source
    gate. It exists to retain reproducible discovery/corroboration leads while
    the authoritative inventory continues to require official IDX provenance.
    Every referenced canonical source must therefore still be
    ``DISCOVERY_REQUIRED``.
    """

    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("discovery evidence registry must contain a non-empty evidence list")

    sources = canonical_inventory.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("canonical inventory must contain sources")
    canonical_by_id = {
        str(item.get("source_id") or "").strip(): item
        for item in sources
        if isinstance(item, dict)
    }

    seen: set[str] = set()
    touched: set[str] = set()
    roles: dict[str, int] = {}
    claim_dates: dict[str, set[str]] = {}

    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("every discovery evidence row must be an object")
        missing = REQUIRED_EVIDENCE_FIELDS - set(item)
        if missing:
            raise ValueError(f"discovery evidence row missing fields: {sorted(missing)}")

        evidence_id = str(item["evidence_id"] or "").strip()
        if not evidence_id or evidence_id in seen:
            raise ValueError(f"duplicate or empty evidence_id: {evidence_id!r}")
        seen.add(evidence_id)

        canonical_source_id = str(item["canonical_source_id"] or "").strip()
        source = canonical_by_id.get(canonical_source_id)
        if source is None:
            raise ValueError(f"unknown canonical_source_id for {evidence_id}: {canonical_source_id}")
        if str(source.get("status") or "").strip() != "DISCOVERY_REQUIRED":
            raise ValueError(
                f"discovery evidence may only target a blocked canonical source: {canonical_source_id}"
            )
        touched.add(canonical_source_id)

        role = str(item["role"] or "").strip()
        if role not in DISCOVERY_ROLES:
            raise ValueError(f"unsupported discovery role for {evidence_id}: {role}")
        roles[role] = roles.get(role, 0) + 1

        if not str(item["publisher"] or "").strip():
            raise ValueError(f"empty publisher for {evidence_id}")
        _date(item["published_at"], field="published_at", evidence_id=evidence_id)
        if not _https_url(item["url"]):
            raise ValueError(f"discovery evidence URL must be HTTPS: {evidence_id}")
        if not str(item["note"] or "").strip():
            raise ValueError(f"empty note for {evidence_id}")

        claims = item["claims"]
        if not isinstance(claims, dict) or not claims:
            raise ValueError(f"claims must be a non-empty object: {evidence_id}")

        dates: set[str] = set()
        for field in ("announcement_date", "effective_date"):
            if claims.get(field) not in (None, ""):
                dates.add(_date(claims[field], field=field, evidence_id=evidence_id).date().isoformat())
        claim_dates.setdefault(canonical_source_id, set()).update(dates)

        tickers = claims.get("affected_tickers")
        if tickers is not None:
            if not isinstance(tickers, list) or not tickers:
                raise ValueError(f"affected_tickers must be a non-empty list: {evidence_id}")
            normalised = [normalise_ticker(value) for value in tickers]
            if any(not value for value in normalised) or len(set(normalised)) != len(normalised):
                raise ValueError(f"affected_tickers contains empty/duplicate values: {evidence_id}")

        count = claims.get("affected_count")
        if count is not None and (not isinstance(count, int) or count <= 0):
            raise ValueError(f"affected_count must be a positive integer: {evidence_id}")
        if isinstance(tickers, list) and count is not None and len(tickers) != count:
            raise ValueError(f"affected_count disagrees with affected_tickers: {evidence_id}")

    return {
        "schema_version": payload.get("schema_version"),
        "evidence_total": len(evidence),
        "canonical_sources_touched": sorted(touched),
        "roles": roles,
        "claimed_dates_by_source": {
            source_id: sorted(values) for source_id, values in sorted(claim_dates.items())
        },
        "canonical_promotions_authorized": 0,
        "canonical_gate_unchanged": True,
    }
