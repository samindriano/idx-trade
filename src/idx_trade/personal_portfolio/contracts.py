from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass, fields
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from .schema import GOKSEI_PIN, KSEI_MCP_PIN, validate_snapshot_payload

SCHEMA_VERSION = "personal-portfolio-snapshot-v1"
SOURCE_ID = "AKSES_KSEI_PERSONAL"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9._-]{1,24}$")
_SCOPE_REF_RE = re.compile(r"^ps_[0-9a-f]{32}$")
_SUBACCOUNT_REF_RE = re.compile(r"^ksa_[0-9a-f]{64}$")
_ADAPTER_VERSION_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?62|0)8\d{7,12}(?!\d)")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b")
_AUTH_RE = re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9+/=_\-.]{6,}")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret)\s*[:=]\s*\S+"
)
_LONG_DIGIT_RE = re.compile(r"(?<!\d)\d{8,20}(?!\d)")

_FORBIDDEN_CANONICAL_KEYS = {
    "username",
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "authorization",
    "bearer",
    "nik",
    "npwp",
    "passport",
    "email",
    "phone",
    "fullname",
    "full_name",
    "investorid",
    "investor_id",
    "sid",
    "loginid",
    "login_id",
    "rekening",
    "account_number",
    "account_no",
}

_REQUIRED_SOURCE_COMMIT_PINS_DICT = {
    "nichsedge/ksei-mcp": KSEI_MCP_PIN,
    "chickenzord/goksei": GOKSEI_PIN,
}
REQUIRED_SOURCE_COMMIT_PINS: Mapping[str, str] = MappingProxyType(
    dict(_REQUIRED_SOURCE_COMMIT_PINS_DICT)
)


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _require_non_negative(value: Decimal, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError(f"{field_name} must be a finite non-negative Decimal")


def _require_currency(value: str) -> None:
    if not _CURRENCY_RE.fullmatch(value):
        raise ValueError("currency must be a three-letter uppercase code")


def _require_sha256(value: str, field_name: str) -> None:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase SHA-256 hex")


def _require_safe_text(value: str, field_name: str, max_length: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length {max_length}")
    if _CONTROL_CHAR_RE.search(normalized):
        raise ValueError(f"{field_name} contains control characters")
    _assert_value_not_sensitive(normalized, field_name)
    return normalized


def _optional_safe_text(value: str | None, field_name: str, max_length: int) -> str | None:
    if value is None:
        return None
    return _require_safe_text(value, field_name, max_length)


def _assert_value_not_sensitive(value: str, field_name: str) -> None:
    if _EMAIL_RE.search(value):
        raise ValueError(f"{field_name} must not contain email/identity material")
    if _PHONE_RE.search(value):
        raise ValueError(f"{field_name} must not contain phone/identity material")
    if _JWT_RE.search(value):
        raise ValueError(f"{field_name} must not contain JWT material")
    if _AUTH_RE.search(value):
        raise ValueError(f"{field_name} must not contain authorization material")
    if _SECRET_ASSIGNMENT_RE.search(value):
        raise ValueError(f"{field_name} must not contain secret material")
    if _LONG_DIGIT_RE.search(value):
        raise ValueError(f"{field_name} must not contain raw account/identity numbers")


def _canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("non-finite Decimal cannot be canonicalized")
    if value == 0:
        return "0"
    normalized = value.normalize()
    rendered = format(normalized, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def new_scope_ref() -> str:
    """Return a random opaque scope identifier containing no account identity."""
    return f"ps_{secrets.token_hex(16)}"


def derive_subaccount_ref(raw_account_identifier: str, hmac_key: bytes) -> str:
    """Derive a stable opaque subaccount ref without persisting the raw identifier.

    The key is an application/backend secret and must be at least 256 bits. Neither
    the raw account identifier nor this key belongs in canonical snapshots/logs.
    """
    raw = raw_account_identifier.strip()
    if not raw:
        raise ValueError("raw_account_identifier is required")
    if len(hmac_key) < 32:
        raise ValueError("hmac_key must contain at least 32 bytes")
    digest = hmac.new(hmac_key, raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"ksa_{digest}"


class AssetClass(StrEnum):
    EQUITY = "EQUITY"
    CASH = "CASH"
    MUTUAL_FUND = "MUTUAL_FUND"
    BOND = "BOND"
    OTHER = "OTHER"


class SnapshotCompleteness(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"


class EndpointClass(StrEnum):
    PORTFOLIO_SUMMARY = "PORTFOLIO_SUMMARY"
    CASH = "CASH"
    EQUITY = "EQUITY"
    MUTUAL_FUND = "MUTUAL_FUND"
    BOND = "BOND"
    OTHER = "OTHER"


class EndpointFailureCode(StrEnum):
    HTTP_ERROR = "HTTP_ERROR"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    TIMEOUT = "TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    ROW_VALIDATION_FAILED = "ROW_VALIDATION_FAILED"
    UNKNOWN = "UNKNOWN"


REQUIRED_ENDPOINT_CLASSES: tuple[EndpointClass, ...] = tuple(EndpointClass)


@dataclass(frozen=True, slots=True)
class SecurityIdentity:
    symbol: str
    security_name: str | None = None
    security_code: str | None = None

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not _SYMBOL_RE.fullmatch(symbol):
            raise ValueError("symbol must be a safe 1-24 character identifier")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(
            self,
            "security_name",
            _optional_safe_text(self.security_name, "security_name", 160),
        )
        object.__setattr__(
            self,
            "security_code",
            _optional_safe_text(self.security_code, "security_code", 64),
        )


@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    security: SecurityIdentity
    asset_class: AssetClass
    quantity: Decimal
    currency: str | None = None
    broker_or_custodian: str | None = None
    subaccount_ref: str | None = None

    def __post_init__(self) -> None:
        if self.asset_class == AssetClass.CASH:
            raise ValueError("cash must use CashBalance, not PortfolioPosition")
        _require_non_negative(self.quantity, "quantity")
        if self.currency is not None:
            _require_currency(self.currency)
        object.__setattr__(
            self,
            "broker_or_custodian",
            _optional_safe_text(self.broker_or_custodian, "broker_or_custodian", 120),
        )
        if self.subaccount_ref is not None and not _SUBACCOUNT_REF_RE.fullmatch(self.subaccount_ref):
            raise ValueError("subaccount_ref must be a server-derived keyed-HMAC reference")

    def identity_key(self) -> tuple[Any, ...]:
        return (
            self.security.symbol,
            self.security.security_code,
            self.asset_class.value,
            self.currency,
            self.broker_or_custodian,
            self.subaccount_ref,
        )


@dataclass(frozen=True, slots=True)
class CashBalance:
    currency: str
    amount: Decimal
    bank_or_custodian: str | None = None
    subaccount_ref: str | None = None

    def __post_init__(self) -> None:
        _require_currency(self.currency)
        _require_non_negative(self.amount, "amount")
        object.__setattr__(
            self,
            "bank_or_custodian",
            _optional_safe_text(self.bank_or_custodian, "bank_or_custodian", 120),
        )
        if self.subaccount_ref is not None and not _SUBACCOUNT_REF_RE.fullmatch(self.subaccount_ref):
            raise ValueError("subaccount_ref must be a server-derived keyed-HMAC reference")

    def identity_key(self) -> tuple[Any, ...]:
        return (self.currency, self.bank_or_custodian, self.subaccount_ref)


@dataclass(frozen=True, slots=True)
class EndpointEvidence:
    endpoint_class: EndpointClass
    succeeded: bool
    observed_rows: int
    accepted_rows: int
    rejected_rows: int
    failure_code: EndpointFailureCode | None = None

    def __post_init__(self) -> None:
        for name in ("observed_rows", "accepted_rows", "rejected_rows"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.succeeded:
            if self.observed_rows != self.accepted_rows + self.rejected_rows:
                raise ValueError("successful endpoint row accounting must balance")
            if self.rejected_rows == 0 and self.failure_code is not None:
                raise ValueError("clean endpoint success must not carry a failure_code")
            if self.rejected_rows > 0 and self.failure_code is None:
                raise ValueError("rejected rows require an explicit failure_code")
        else:
            if self.failure_code is None:
                raise ValueError("failed endpoint requires failure_code")
            if self.accepted_rows != 0 or self.rejected_rows != 0:
                raise ValueError("failed endpoint cannot claim accepted/rejected rows")


@dataclass(frozen=True, slots=True)
class PortfolioProvenance:
    source: str
    adapter_version: str
    raw_response_sha256: str
    endpoint_set: tuple[EndpointClass, ...]
    source_commit_pins: Mapping[str, str]

    def __post_init__(self) -> None:
        if self.source != SOURCE_ID:
            raise ValueError(f"source must be {SOURCE_ID}")
        if not _ADAPTER_VERSION_RE.fullmatch(self.adapter_version):
            raise ValueError("adapter_version must be a safe 1-64 character identifier")
        _require_sha256(self.raw_response_sha256, "raw_response_sha256")
        endpoint_set = tuple(self.endpoint_set)
        if endpoint_set != REQUIRED_ENDPOINT_CLASSES:
            raise ValueError("endpoint_set must exactly contain all required endpoint classes in canonical order")
        object.__setattr__(self, "endpoint_set", endpoint_set)

        pins = dict(self.source_commit_pins)
        if pins != _REQUIRED_SOURCE_COMMIT_PINS_DICT:
            raise ValueError("source_commit_pins must exactly match both reviewed upstream commits")
        object.__setattr__(self, "source_commit_pins", MappingProxyType(dict(sorted(pins.items()))))


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
        _require_aware(self.snapshot_at, "snapshot_at")
        _require_aware(self.fetched_at, "fetched_at")
        if self.fetched_at < self.snapshot_at:
            raise ValueError("fetched_at must be >= snapshot_at")
        if not _SCOPE_REF_RE.fullmatch(self.scope_ref):
            raise ValueError("scope_ref must be a random opaque server-side reference")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")

        positions = tuple(self.positions)
        cash_balances = tuple(self.cash_balances)
        endpoint_evidence = tuple(self.endpoint_evidence)
        object.__setattr__(self, "positions", positions)
        object.__setattr__(self, "cash_balances", cash_balances)
        object.__setattr__(self, "endpoint_evidence", endpoint_evidence)

        actual_endpoint_classes = tuple(item.endpoint_class for item in endpoint_evidence)
        if actual_endpoint_classes != REQUIRED_ENDPOINT_CLASSES:
            raise ValueError("endpoint_evidence must contain every required endpoint exactly once in canonical order")

        position_keys = [item.identity_key() for item in positions]
        if len(position_keys) != len(set(position_keys)):
            raise ValueError("duplicate portfolio position identity is not allowed")
        cash_keys = [item.identity_key() for item in cash_balances]
        if len(cash_keys) != len(set(cash_keys)):
            raise ValueError("duplicate cash balance identity is not allowed")

        actual_rows = {
            EndpointClass.CASH: len(cash_balances),
            EndpointClass.EQUITY: sum(item.asset_class == AssetClass.EQUITY for item in positions),
            EndpointClass.MUTUAL_FUND: sum(item.asset_class == AssetClass.MUTUAL_FUND for item in positions),
            EndpointClass.BOND: sum(item.asset_class == AssetClass.BOND for item in positions),
            EndpointClass.OTHER: sum(item.asset_class == AssetClass.OTHER for item in positions),
        }
        evidence_by_class = {item.endpoint_class: item for item in endpoint_evidence}
        for endpoint_class, actual_count in actual_rows.items():
            if evidence_by_class[endpoint_class].accepted_rows != actual_count:
                raise ValueError(f"accepted row accounting mismatch for {endpoint_class.value}")

        has_problem = any((not item.succeeded) or item.rejected_rows > 0 for item in endpoint_evidence)
        if self.completeness == SnapshotCompleteness.COMPLETE and has_problem:
            raise ValueError("COMPLETE requires every endpoint to succeed with zero rejected rows")
        if self.completeness == SnapshotCompleteness.PARTIAL and not has_problem:
            raise ValueError("PARTIAL requires explicit endpoint failure or row rejection evidence")

    def canonical_dict(self) -> dict[str, Any]:
        value = _jsonable(self)
        assert_minimized_canonical_payload(value)
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
                security=SecurityIdentity(**item["security"]),
                asset_class=AssetClass(item["asset_class"]),
                quantity=Decimal(item["quantity"]),
                currency=item["currency"],
                broker_or_custodian=item["broker_or_custodian"],
                subaccount_ref=item["subaccount_ref"],
            )
            for item in payload["positions"]
        )
        cash_balances = tuple(
            CashBalance(
                currency=item["currency"],
                amount=Decimal(item["amount"]),
                bank_or_custodian=item["bank_or_custodian"],
                subaccount_ref=item["subaccount_ref"],
            )
            for item in payload["cash_balances"]
        )
        endpoint_evidence = tuple(
            EndpointEvidence(
                endpoint_class=EndpointClass(item["endpoint_class"]),
                succeeded=item["succeeded"],
                observed_rows=item["observed_rows"],
                accepted_rows=item["accepted_rows"],
                rejected_rows=item["rejected_rows"],
                failure_code=(EndpointFailureCode(item["failure_code"]) if item["failure_code"] else None),
            )
            for item in payload["endpoint_evidence"]
        )
        provenance_payload = payload["provenance"]
        snapshot = cls(
            snapshot_at=datetime.fromisoformat(payload["snapshot_at"]),
            fetched_at=datetime.fromisoformat(payload["fetched_at"]),
            scope_ref=payload["scope_ref"],
            positions=positions,
            cash_balances=cash_balances,
            provenance=PortfolioProvenance(
                source=provenance_payload["source"],
                adapter_version=provenance_payload["adapter_version"],
                raw_response_sha256=provenance_payload["raw_response_sha256"],
                endpoint_set=tuple(EndpointClass(item) for item in provenance_payload["endpoint_set"]),
                source_commit_pins=provenance_payload["source_commit_pins"],
            ),
            completeness=SnapshotCompleteness(payload["completeness"]),
            endpoint_evidence=endpoint_evidence,
            schema_version=payload["schema_version"],
        )
        if snapshot.canonical_dict() != dict(payload):
            raise ValueError("canonical payload does not round-trip exactly")
        return snapshot

    @classmethod
    def from_canonical_json(cls, payload_json: str) -> "PortfolioSnapshot":
        value = json.loads(payload_json)
        if not isinstance(value, dict):
            raise ValueError("canonical snapshot JSON must be an object")
        return cls.from_canonical_dict(value)


@dataclass(frozen=True, slots=True)
class PricePerformanceContext:
    price_as_of: datetime
    currency: str
    current_price: Decimal
    market_value: Decimal | None = None
    performance_since_reference: Decimal | None = None

    def __post_init__(self) -> None:
        _require_aware(self.price_as_of, "price_as_of")
        _require_currency(self.currency)
        _require_non_negative(self.current_price, "current_price")


@dataclass(frozen=True, slots=True)
class FinancialPITContext:
    knowledge_at: datetime
    facts_snapshot_ref: str

    def __post_init__(self) -> None:
        _require_aware(self.knowledge_at, "knowledge_at")
        _require_safe_text(self.facts_snapshot_ref, "facts_snapshot_ref", 128)


@dataclass(frozen=True, slots=True)
class CorporateActionContext:
    knowledge_at: datetime
    event_ref: str
    event_type: str

    def __post_init__(self) -> None:
        _require_aware(self.knowledge_at, "knowledge_at")
        _require_safe_text(self.event_ref, "event_ref", 128)
        _require_safe_text(self.event_type, "event_type", 80)


@dataclass(frozen=True, slots=True)
class InvestmentHealthContext:
    price_performance: PricePerformanceContext | None = None
    financial_pit: FinancialPITContext | None = None
    corporate_actions: tuple[CorporateActionContext, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "corporate_actions", tuple(self.corporate_actions))


@dataclass(frozen=True, slots=True)
class ShortHorizonModelContext:
    as_of: datetime
    model_id: str
    horizon_sessions: int
    rank: int | None = None
    score: Decimal | None = None
    interpretation: str = "CONTEXT_ONLY_NO_LONG_TERM_ACTION"

    def __post_init__(self) -> None:
        _require_aware(self.as_of, "as_of")
        _require_safe_text(self.model_id, "model_id", 128)
        if self.horizon_sessions <= 0:
            raise ValueError("horizon_sessions must be positive")
        if self.rank is not None and self.rank <= 0:
            raise ValueError("rank must be positive")
        if self.interpretation != "CONTEXT_ONLY_NO_LONG_TERM_ACTION":
            raise ValueError("short-horizon model context cannot encode an investment action")


@dataclass(frozen=True, slots=True)
class TradingOpportunityContext:
    short_horizon_model: ShortHorizonModelContext | None = None


@dataclass(frozen=True, slots=True)
class HoldingEnrichment:
    security: SecurityIdentity
    investment_health: InvestmentHealthContext
    trading_opportunity: TradingOpportunityContext


@dataclass(frozen=True, slots=True)
class AppendResult:
    inserted: bool
    snapshot_id: str
    dedup_key: str


@runtime_checkable
class PersonalPortfolioAdapter(Protocol):
    """Provider-neutral boundary. No MCP dependency and no credential arguments."""

    def fetch_snapshot(self) -> PortfolioSnapshot:
        ...


@runtime_checkable
class PortfolioSnapshotStore(Protocol):
    """Append-only storage boundary; implementations expose no update/delete method."""

    def append_if_new(self, snapshot: PortfolioSnapshot) -> AppendResult:
        ...

    def latest_observation(self, scope_ref: str) -> PortfolioSnapshot | None:
        ...

    def latest_complete(self, scope_ref: str) -> PortfolioSnapshot | None:
        ...


def assert_minimized_canonical_payload(value: Any, *, _path: tuple[str, ...] = ()) -> None:
    """Fail closed if canonical payloads contain secrets or unnecessary identity material."""
    if isinstance(value, Mapping):
        forbidden = {item.replace("_", "") for item in _FORBIDDEN_CANONICAL_KEYS}
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "").replace("_", "")
            if normalized in forbidden:
                raise ValueError(f"forbidden sensitive field in canonical payload: {key}")
            assert_minimized_canonical_payload(child, _path=(*_path, str(key)))
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            assert_minimized_canonical_payload(child, _path=(*_path, str(index)))
        return
    if isinstance(value, str):
        # Hashes, reviewed commit SHAs and opaque refs are intentionally high-entropy
        # values. Their structure is validated separately by the contract/schema.
        leaf = _path[-1] if _path else ""
        if leaf in {"raw_response_sha256", "subaccount_ref", "scope_ref"} or "source_commit_pins" in _path:
            return
        _assert_value_not_sensitive(value, ".".join(_path) or "value")


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return _canonical_decimal(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(child) for child in value]
    if isinstance(value, list):
        return [_jsonable(child) for child in value]
    if hasattr(value, "__dataclass_fields__"):
        return {item.name: _jsonable(getattr(value, item.name)) for item in fields(value)}
    return value
