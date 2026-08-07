from __future__ import annotations

from enum import StrEnum


class ExistenceState(StrEnum):
    """Whether an exchange security legally exists on a session date."""

    NOT_LISTED = "NOT_LISTED"
    LISTED = "LISTED"
    DELISTED = "DELISTED"


class TradabilityState(StrEnum):
    """Exchange/trading-state information independent of provider price data."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    FCA_WATCHLIST = "FCA_WATCHLIST"
    NO_TRADE = "NO_TRADE"
    UNKNOWN = "UNKNOWN"


class DataAvailability(StrEnum):
    """Whether the selected market-data source supplied an expected record."""

    PRESENT = "PRESENT"
    DATA_MISSING = "DATA_MISSING"
