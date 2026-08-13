"""Provider-neutral public contract surface for the private portfolio adapter."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .snapshot import AppendResult, PersonalPortfolioAdapter, PortfolioSnapshot, PortfolioSnapshotStore
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
)
from .validation import (
    REQUIRED_SOURCE_COMMIT_PINS,
    SCHEMA_VERSION,
    SOURCE_ID,
    assert_minimized_canonical_payload,
    derive_subaccount_ref,
    new_scope_ref,
    require_aware,
    require_currency,
    require_non_negative,
    require_safe_text,
)


@dataclass(frozen=True, slots=True)
class PricePerformanceContext:
    price_as_of: datetime
    currency: str
    current_price: Decimal
    market_value: Decimal | None = None
    performance_since_reference: Decimal | None = None

    def __post_init__(self) -> None:
        require_aware(self.price_as_of, "price_as_of")
        require_currency(self.currency)
        require_non_negative(self.current_price, "current_price")


@dataclass(frozen=True, slots=True)
class FinancialPITContext:
    knowledge_at: datetime
    facts_snapshot_ref: str

    def __post_init__(self) -> None:
        require_aware(self.knowledge_at, "knowledge_at")
        object.__setattr__(self, "facts_snapshot_ref", require_safe_text(self.facts_snapshot_ref, "facts_snapshot_ref", 128))


@dataclass(frozen=True, slots=True)
class CorporateActionContext:
    knowledge_at: datetime
    event_ref: str
    event_type: str

    def __post_init__(self) -> None:
        require_aware(self.knowledge_at, "knowledge_at")
        object.__setattr__(self, "event_ref", require_safe_text(self.event_ref, "event_ref", 128))
        object.__setattr__(self, "event_type", require_safe_text(self.event_type, "event_type", 64))


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
        require_aware(self.as_of, "as_of")
        object.__setattr__(self, "model_id", require_safe_text(self.model_id, "model_id", 96))
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


__all__ = [
    "AppendResult",
    "AssetClass",
    "CashBalance",
    "CorporateActionContext",
    "EndpointClass",
    "EndpointEvidence",
    "EndpointFailureCode",
    "FinancialPITContext",
    "HoldingEnrichment",
    "InvestmentHealthContext",
    "PersonalPortfolioAdapter",
    "PortfolioPosition",
    "PortfolioProvenance",
    "PortfolioSnapshot",
    "PortfolioSnapshotStore",
    "PricePerformanceContext",
    "REQUIRED_ENDPOINT_CLASSES",
    "REQUIRED_SOURCE_COMMIT_PINS",
    "SCHEMA_VERSION",
    "SOURCE_ID",
    "SecurityIdentity",
    "ShortHorizonModelContext",
    "SnapshotCompleteness",
    "TradingOpportunityContext",
    "assert_minimized_canonical_payload",
    "derive_subaccount_ref",
    "new_scope_ref",
]
