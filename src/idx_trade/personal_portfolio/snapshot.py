from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Protocol, runtime_checkable

from .schema import validate_snapshot_payload
from .semantics import validate_snapshot_semantics
from .types import (
    AssetClass,
    CashBalance,
    EndpointClass,
    EndpointEvidence,
    EndpointFailureCode,
    PortfolioPosition,
    PortfolioProvenance,
    REQUIRED_ENDPOINT_CLASSES,
    SecurityIdentity,
    SnapshotCompleteness,
    reject_duplicate_rows,
)
from .validation import (
    SCHEMA_VERSION,
    SCOPE_REF_RE,
    assert_minimized_canonical_payload,
    jsonable,
    require_aware,
)


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    snapshot_at: datetime
    fetched_at: datetime
    scope_ref: str
    positions: tuple[PortfolioPosition, ...]
    cash_balances: tuple[CashBalance, ...]
    provenance: PortfolioProvenance
    completeness: SnapshotCompleteness
    endpoint_evidence: tuple[EndpointEvidence, ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_aware(self.snapshot_at, "snapshot_at")
        require_aware(self.fetched_at, "fetched_at")
        if self.fetched_at < self.snapshot_at:
            raise ValueError("fetched_at must be >= snapshot_at")
        if not SCOPE_REF_RE.fullmatch(self.scope_ref):
            raise ValueError("scope_ref must be a backend-generated opaque reference")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")

        positions = tuple(self.positions)
        cash = tuple(self.cash_balances)
        evidence = tuple(self.endpoint_evidence)
        object.__setattr__(self, "positions", positions)
        object.__setattr__(self, "cash_balances", cash)
        object.__setattr__(self, "endpoint_evidence", evidence)

        if tuple(item.endpoint_class for item in evidence) != REQUIRED_ENDPOINT_CLASSES:
            raise ValueError("endpoint_evidence must contain every required endpoint exactly once in canonical order")
        reject_duplicate_rows(positions, "portfolio position")
        reject_duplicate_rows(cash, "cash balance")

        semantic_payload = jsonable(self)
        assert_minimized_canonical_payload(semantic_payload)
        validate_snapshot_semantics(semantic_payload)

    def canonical_dict(self) -> dict[str, Any]:
        value = jsonable(self)
        validate_snapshot_payload(value)
        return value

    def canonical_json(self) -> str:
        return json.dumps(self.canonical_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def snapshot_id(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def history_dedup_key(self) -> str:
        payload = self.canonical_dict()
        payload.pop("fetched_at", None)
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def from_canonical_dict(cls, payload: Mapping[str, Any]) -> "PortfolioSnapshot":
        validate_snapshot_payload(payload)
        positions = tuple(
            PortfolioPosition(
                SecurityIdentity(**item["security"]),
                AssetClass(item["asset_class"]),
                Decimal(item["quantity"]),
                item["currency"],
                item["broker_or_custodian"],
                item["subaccount_ref"],
            )
            for item in payload["positions"]
        )
        cash = tuple(
            CashBalance(
                item["currency"],
                Decimal(item["amount"]),
                item["bank_or_custodian"],
                item["subaccount_ref"],
            )
            for item in payload["cash_balances"]
        )
        evidence = tuple(
            EndpointEvidence(
                EndpointClass(item["endpoint_class"]),
                item["succeeded"],
                item["observed_rows"],
                item["accepted_rows"],
                item["rejected_rows"],
                EndpointFailureCode(item["failure_code"])
                if item["failure_code"] is not None
                else None,
            )
            for item in payload["endpoint_evidence"]
        )
        provenance = payload["provenance"]
        result = cls(
            datetime.fromisoformat(payload["snapshot_at"].replace("Z", "+00:00")),
            datetime.fromisoformat(payload["fetched_at"].replace("Z", "+00:00")),
            payload["scope_ref"],
            positions,
            cash,
            PortfolioProvenance(
                provenance["source"],
                provenance["adapter_version"],
                provenance["raw_response_sha256"],
                tuple(EndpointClass(item) for item in provenance["endpoint_set"]),
                provenance["source_commit_pins"],
            ),
            SnapshotCompleteness(payload["completeness"]),
            evidence,
            payload["schema_version"],
        )
        result.canonical_dict()
        return result

    @classmethod
    def from_canonical_json(cls, payload_json: str) -> "PortfolioSnapshot":
        payload = json.loads(payload_json)
        if not isinstance(payload, dict):
            raise ValueError("canonical snapshot JSON must be an object")
        return cls.from_canonical_dict(payload)


@dataclass(frozen=True, slots=True)
class AppendResult:
    inserted: bool
    snapshot_id: str
    dedup_key: str


@runtime_checkable
class PersonalPortfolioAdapter(Protocol):
    def fetch_snapshot(self) -> PortfolioSnapshot: ...


@runtime_checkable
class PortfolioSnapshotStore(Protocol):
    def append_if_new(self, snapshot: PortfolioSnapshot) -> AppendResult: ...
    def latest_observation(self, scope_ref: str) -> PortfolioSnapshot | None: ...
    def latest_complete(self, scope_ref: str) -> PortfolioSnapshot | None: ...
