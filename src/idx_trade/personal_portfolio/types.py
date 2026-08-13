from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .semantics import validate_endpoint_evidence_values
from .validation import (
    ADAPTER_VERSION_RE,
    REQUIRED_SOURCE_COMMIT_PINS,
    SHA256_RE,
    SOURCE_ID,
    SYMBOL_RE,
    SubaccountRef,
    require_currency,
    require_non_negative,
    require_safe_text,
)


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


REQUIRED_ENDPOINT_CLASSES: tuple[EndpointClass, ...] = tuple(EndpointClass)


class EndpointFailureCode(StrEnum):
    HTTP_ERROR = "HTTP_ERROR"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    TIMEOUT = "TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    ROW_VALIDATION_FAILED = "ROW_VALIDATION_FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SecurityIdentity:
    symbol: str
    security_name: str | None = None
    security_code: str | None = None

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not SYMBOL_RE.fullmatch(symbol):
            raise ValueError("symbol must be a compact public security identifier")
        object.__setattr__(self, "symbol", symbol)
        if self.security_name is not None:
            object.__setattr__(self, "security_name", require_safe_text(self.security_name, "security_name", 160))
        if self.security_code is not None:
            object.__setattr__(self, "security_code", require_safe_text(self.security_code, "security_code", 64))


@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    security: SecurityIdentity
    asset_class: AssetClass
    quantity: Decimal
    currency: str | None = None
    broker_or_custodian: str | None = None
    subaccount_ref: SubaccountRef | None = None

    def __post_init__(self) -> None:
        if self.asset_class == AssetClass.CASH:
            raise ValueError("cash must use CashBalance, not PortfolioPosition")
        require_non_negative(self.quantity, "quantity")
        if self.currency is not None:
            require_currency(self.currency)
        if self.broker_or_custodian is not None:
            object.__setattr__(self, "broker_or_custodian", require_safe_text(self.broker_or_custodian, "broker_or_custodian", 120))
        if self.subaccount_ref is not None and not isinstance(self.subaccount_ref, SubaccountRef):
            raise ValueError("subaccount_ref must come from derive_subaccount_ref")

    def identity_key(self) -> tuple[Any, ...]:
        return (self.security.symbol, self.security.security_code, self.asset_class.value, self.currency, self.broker_or_custodian, self.subaccount_ref)


@dataclass(frozen=True, slots=True)
class CashBalance:
    currency: str
    amount: Decimal
    bank_or_custodian: str | None = None
    subaccount_ref: SubaccountRef | None = None

    def __post_init__(self) -> None:
        require_currency(self.currency)
        require_non_negative(self.amount, "amount")
        if self.bank_or_custodian is not None:
            object.__setattr__(self, "bank_or_custodian", require_safe_text(self.bank_or_custodian, "bank_or_custodian", 120))
        if self.subaccount_ref is not None and not isinstance(self.subaccount_ref, SubaccountRef):
            raise ValueError("subaccount_ref must come from derive_subaccount_ref")

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
        validate_endpoint_evidence_values(
            succeeded=self.succeeded,
            observed_rows=self.observed_rows,
            accepted_rows=self.accepted_rows,
            rejected_rows=self.rejected_rows,
            failure_code=self.failure_code.value if self.failure_code is not None else None,
        )


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
        if not ADAPTER_VERSION_RE.fullmatch(self.adapter_version):
            raise ValueError("adapter_version must be a compact allowlisted identifier")
        if not SHA256_RE.fullmatch(self.raw_response_sha256):
            raise ValueError("raw_response_sha256 must be lowercase SHA-256 hex")
        endpoint_set = tuple(self.endpoint_set)
        if endpoint_set != REQUIRED_ENDPOINT_CLASSES:
            raise ValueError("endpoint_set must exactly match the required V1 endpoint classes")
        object.__setattr__(self, "endpoint_set", endpoint_set)
        pins = dict(self.source_commit_pins)
        if pins != dict(REQUIRED_SOURCE_COMMIT_PINS):
            raise ValueError("source_commit_pins must exactly match the reviewed V1 commit pins")
        object.__setattr__(self, "source_commit_pins", MappingProxyType(dict(sorted(pins.items()))))


def reject_duplicate_rows(rows: Sequence[Any], label: str) -> None:
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        key = row.identity_key()
        if key in seen:
            raise ValueError(f"duplicate {label} identity is not allowed")
        seen.add(key)
