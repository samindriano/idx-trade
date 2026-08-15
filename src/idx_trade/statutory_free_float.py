from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from math import isfinite
import re


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TICKER_RE = re.compile(r"^[A-Z0-9]{4,5}$")
_OFFICIAL_HOST_PREFIXES = (
    "https://www.idx.id/",
    "https://www.idx.co.id/",
    "https://idx.id/",
    "https://idx.co.id/",
    "https://web.ksei.co.id/",
)


class FreeFloatRuleVersion(str, Enum):
    IDX_I_A_2021 = "IDX_I_A_2021"
    IDX_I_A_2026 = "IDX_I_A_2026"


class FreeFloatSnapshotStatus(str, Enum):
    OFFICIAL_REPORTED = "OFFICIAL_REPORTED"
    RECONSTRUCTED_VERIFIED = "RECONSTRUCTED_VERIFIED"
    BOUNDED_ONLY = "BOUNDED_ONLY"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class FreeFloatSource:
    source_type: str
    source_url: str
    source_sha256: str
    announcement_no: str | None = None

    def __post_init__(self) -> None:
        if not self.source_type.strip():
            raise ValueError("source_type is empty")
        if not self.source_url.startswith(_OFFICIAL_HOST_PREFIXES):
            raise ValueError("source_url must be an official IDX/KSEI URL")
        if not _SHA256_RE.fullmatch(self.source_sha256):
            raise ValueError("source_sha256 must be lowercase SHA-256 hex")
        if self.announcement_no is not None and not self.announcement_no.strip():
            raise ValueError("announcement_no cannot be blank")


@dataclass(frozen=True)
class StatutoryFreeFloatSnapshot:
    ticker: str
    as_of_date: date
    published_at: datetime
    rule_version: FreeFloatRuleVersion
    status: FreeFloatSnapshotStatus
    free_float_shares: int | None
    free_float_pct: float | None
    total_listed_shares: int | None
    confirmed_eligible_shares: int | None
    confirmed_excluded_shares: int | None
    unresolved_shares: int | None
    lower_bound_shares: int | None
    upper_bound_shares: int | None
    sources: tuple[FreeFloatSource, ...]

    def __post_init__(self) -> None:
        ticker = self.ticker.strip().upper()
        if not _TICKER_RE.fullmatch(ticker):
            raise ValueError(f"invalid ticker: {self.ticker!r}")
        object.__setattr__(self, "ticker", ticker)

        if self.published_at.tzinfo is None or self.published_at.utcoffset() is None:
            raise ValueError("published_at must be timezone-aware")
        if self.as_of_date > self.published_at.date():
            raise ValueError("as_of_date cannot be after publication date")
        if self.rule_version is FreeFloatRuleVersion.IDX_I_A_2026 and self.as_of_date < date(2026, 3, 31):
            raise ValueError("IDX_I_A_2026 cannot apply before 2026-03-31")
        if self.rule_version is FreeFloatRuleVersion.IDX_I_A_2021 and self.as_of_date >= date(2026, 3, 31):
            raise ValueError("IDX_I_A_2021 cannot apply on/after 2026-03-31")
        if not self.sources:
            raise ValueError("at least one official source is required")

        for name in (
            "free_float_shares",
            "total_listed_shares",
            "confirmed_eligible_shares",
            "confirmed_excluded_shares",
            "unresolved_shares",
            "lower_bound_shares",
            "upper_bound_shares",
        ):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError(f"{name} must be a non-negative integer or None")

        if self.free_float_pct is not None:
            value = float(self.free_float_pct)
            if not isfinite(value) or not 0.0 <= value <= 100.0:
                raise ValueError("free_float_pct must be finite and within [0, 100]")
            object.__setattr__(self, "free_float_pct", value)

        if self.status is FreeFloatSnapshotStatus.OFFICIAL_REPORTED:
            if self.free_float_shares is None or self.free_float_pct is None:
                raise ValueError("OFFICIAL_REPORTED requires explicit shares and percentage")
            if any(
                value is not None
                for value in (
                    self.confirmed_eligible_shares,
                    self.confirmed_excluded_shares,
                    self.unresolved_shares,
                    self.lower_bound_shares,
                    self.upper_bound_shares,
                )
            ):
                raise ValueError("OFFICIAL_REPORTED must not fabricate reconstruction buckets")

        elif self.status is FreeFloatSnapshotStatus.RECONSTRUCTED_VERIFIED:
            self._validate_reconstruction(require_complete=True)
            if self.free_float_shares != self.confirmed_eligible_shares:
                raise ValueError("verified free_float_shares must equal confirmed eligible shares")
            if self.lower_bound_shares != self.free_float_shares or self.upper_bound_shares != self.free_float_shares:
                raise ValueError("verified reconstruction bounds must collapse to the exact free float")
            if self.free_float_pct is None:
                raise ValueError("RECONSTRUCTED_VERIFIED requires free_float_pct")

        elif self.status is FreeFloatSnapshotStatus.BOUNDED_ONLY:
            self._validate_reconstruction(require_complete=False)
            if not self.unresolved_shares:
                raise ValueError("BOUNDED_ONLY requires positive unresolved_shares")
            if self.free_float_shares is not None or self.free_float_pct is not None:
                raise ValueError("BOUNDED_ONLY forbids a point free-float estimate")
            expected_lower = self.confirmed_eligible_shares
            expected_upper = self.confirmed_eligible_shares + self.unresolved_shares
            if self.lower_bound_shares != expected_lower or self.upper_bound_shares != expected_upper:
                raise ValueError("bounded reconstruction limits are inconsistent")

        else:
            if any(
                value is not None
                for value in (
                    self.free_float_shares,
                    self.free_float_pct,
                    self.total_listed_shares,
                    self.confirmed_eligible_shares,
                    self.confirmed_excluded_shares,
                    self.unresolved_shares,
                    self.lower_bound_shares,
                    self.upper_bound_shares,
                )
            ):
                raise ValueError("UNRESOLVED must not expose numeric free-float values")

    def _validate_reconstruction(self, *, require_complete: bool) -> None:
        if self.total_listed_shares is None or self.total_listed_shares <= 0:
            raise ValueError("reconstruction requires positive total_listed_shares")
        if self.confirmed_eligible_shares is None or self.confirmed_excluded_shares is None or self.unresolved_shares is None:
            raise ValueError("reconstruction requires eligible/excluded/unresolved buckets")
        classified = (
            self.confirmed_eligible_shares
            + self.confirmed_excluded_shares
            + self.unresolved_shares
        )
        if classified != self.total_listed_shares:
            raise ValueError("reconstruction buckets must exactly reconcile to total_listed_shares")
        if require_complete and self.unresolved_shares != 0:
            raise ValueError("verified reconstruction requires zero unresolved shares")


def official_reported_free_float(
    *,
    ticker: str,
    as_of_date: date,
    published_at: datetime,
    rule_version: FreeFloatRuleVersion,
    free_float_shares: int,
    free_float_pct: float,
    sources: tuple[FreeFloatSource, ...],
    total_listed_shares: int | None = None,
) -> StatutoryFreeFloatSnapshot:
    return StatutoryFreeFloatSnapshot(
        ticker=ticker,
        as_of_date=as_of_date,
        published_at=published_at,
        rule_version=rule_version,
        status=FreeFloatSnapshotStatus.OFFICIAL_REPORTED,
        free_float_shares=free_float_shares,
        free_float_pct=free_float_pct,
        total_listed_shares=total_listed_shares,
        confirmed_eligible_shares=None,
        confirmed_excluded_shares=None,
        unresolved_shares=None,
        lower_bound_shares=None,
        upper_bound_shares=None,
        sources=sources,
    )


def reconstruct_statutory_free_float(
    *,
    ticker: str,
    as_of_date: date,
    published_at: datetime,
    rule_version: FreeFloatRuleVersion,
    total_listed_shares: int,
    confirmed_eligible_shares: int,
    confirmed_excluded_shares: int,
    unresolved_shares: int,
    sources: tuple[FreeFloatSource, ...],
) -> StatutoryFreeFloatSnapshot:
    if total_listed_shares <= 0:
        raise ValueError("total_listed_shares must be positive")
    if unresolved_shares == 0:
        pct = confirmed_eligible_shares / total_listed_shares * 100.0
        return StatutoryFreeFloatSnapshot(
            ticker=ticker,
            as_of_date=as_of_date,
            published_at=published_at,
            rule_version=rule_version,
            status=FreeFloatSnapshotStatus.RECONSTRUCTED_VERIFIED,
            free_float_shares=confirmed_eligible_shares,
            free_float_pct=pct,
            total_listed_shares=total_listed_shares,
            confirmed_eligible_shares=confirmed_eligible_shares,
            confirmed_excluded_shares=confirmed_excluded_shares,
            unresolved_shares=0,
            lower_bound_shares=confirmed_eligible_shares,
            upper_bound_shares=confirmed_eligible_shares,
            sources=sources,
        )

    return StatutoryFreeFloatSnapshot(
        ticker=ticker,
        as_of_date=as_of_date,
        published_at=published_at,
        rule_version=rule_version,
        status=FreeFloatSnapshotStatus.BOUNDED_ONLY,
        free_float_shares=None,
        free_float_pct=None,
        total_listed_shares=total_listed_shares,
        confirmed_eligible_shares=confirmed_eligible_shares,
        confirmed_excluded_shares=confirmed_excluded_shares,
        unresolved_shares=unresolved_shares,
        lower_bound_shares=confirmed_eligible_shares,
        upper_bound_shares=confirmed_eligible_shares + unresolved_shares,
        sources=sources,
    )
