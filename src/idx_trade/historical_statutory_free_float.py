from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from math import isfinite
import re
from typing import Iterable, Mapping


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TICKER_RE = re.compile(r"^[A-Z0-9]{4,5}$")
_OFFICIAL_HOST_PREFIXES = (
    "https://www.idx.id/",
    "https://www.idx.co.id/",
    "https://idx.id/",
    "https://idx.co.id/",
)


class FreeFloatSourceFamily(str, Enum):
    IDX_MARKET_WIDE_STATUS = "IDX_MARKET_WIDE_FF_STATUS"
    ISSUER_LBRE = "ISSUER_LBRE"


class FreeFloatRevisionKind(str, Enum):
    ORIGINAL = "ORIGINAL"
    CORRECTION = "CORRECTION"


class FreeFloatCrossSourceStatus(str, Enum):
    SINGLE_SOURCE = "SINGLE_SOURCE"
    AGREE = "AGREE"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class HistoricalFreeFloatObservation:
    record_id: str
    ticker: str
    as_of_date: date
    published_at: datetime
    free_float_shares: int
    free_float_pct: float
    total_listed_shares: int | None
    source_family: FreeFloatSourceFamily
    revision_kind: FreeFloatRevisionKind
    supersedes_record_id: str | None
    announcement_no: str
    source_url: str
    source_sha256: str
    metadata_source_sha256: str
    source_row_key: str | None = None

    def __post_init__(self) -> None:
        if not self.record_id.strip():
            raise ValueError("record_id is empty")

        ticker = self.ticker.strip().upper()
        if not _TICKER_RE.fullmatch(ticker):
            raise ValueError(f"invalid ticker: {self.ticker!r}")
        object.__setattr__(self, "ticker", ticker)

        if self.published_at.tzinfo is None or self.published_at.utcoffset() is None:
            raise ValueError("published_at must be timezone-aware")
        if self.as_of_date > self.published_at.date():
            raise ValueError("as_of_date cannot be after publication date")

        if isinstance(self.free_float_shares, bool) or not isinstance(self.free_float_shares, int):
            raise ValueError("free_float_shares must be an integer")
        if self.free_float_shares < 0:
            raise ValueError("free_float_shares must be non-negative")

        pct = float(self.free_float_pct)
        if not isfinite(pct) or not 0.0 <= pct <= 100.0:
            raise ValueError("free_float_pct must be finite and within [0, 100]")
        object.__setattr__(self, "free_float_pct", pct)

        if self.total_listed_shares is not None:
            if (
                isinstance(self.total_listed_shares, bool)
                or not isinstance(self.total_listed_shares, int)
                or self.total_listed_shares <= 0
            ):
                raise ValueError("total_listed_shares must be a positive integer or None")
            if self.free_float_shares > self.total_listed_shares:
                raise ValueError("free_float_shares cannot exceed total_listed_shares")

        if not self.announcement_no.strip():
            raise ValueError("announcement_no is empty")
        if not self.source_url.startswith(_OFFICIAL_HOST_PREFIXES):
            raise ValueError("source_url must be an official IDX URL")
        for name, value in (
            ("source_sha256", self.source_sha256),
            ("metadata_source_sha256", self.metadata_source_sha256),
        ):
            if not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{name} must be lowercase SHA-256 hex")

        if self.source_family is FreeFloatSourceFamily.IDX_MARKET_WIDE_STATUS:
            if self.source_row_key is None or not self.source_row_key.strip():
                raise ValueError("market-wide observation requires source_row_key")

        if self.revision_kind is FreeFloatRevisionKind.ORIGINAL:
            if self.supersedes_record_id is not None:
                raise ValueError("ORIGINAL observation cannot supersede another record")
        elif self.revision_kind is FreeFloatRevisionKind.CORRECTION:
            if not self.supersedes_record_id:
                raise ValueError("CORRECTION observation requires supersedes_record_id")


ObservationKey = tuple[str, date, FreeFloatSourceFamily]


@dataclass(frozen=True)
class HistoricalFreeFloatReplay:
    admitted: tuple[HistoricalFreeFloatObservation, ...]
    current: Mapping[ObservationKey, HistoricalFreeFloatObservation]


@dataclass(frozen=True)
class FreeFloatCrossSourceReconciliation:
    ticker: str
    as_of_date: date
    status: FreeFloatCrossSourceStatus
    observations: tuple[HistoricalFreeFloatObservation, ...]
    share_spread: int | None
    percentage_point_spread: float | None


@dataclass(frozen=True)
class HistoricalFreeFloatCensus:
    admitted_record_count: int
    current_observation_count: int
    unique_ticker_count: int
    unique_as_of_dates: tuple[date, ...]
    issuer_count_by_as_of_date: Mapping[date, int]
    current_source_family_counts: Mapping[str, int]
    admitted_correction_count: int
    cross_source_status_counts: Mapping[str, int]


def replay_historical_free_float(
    observations: Iterable[HistoricalFreeFloatObservation],
    *,
    cutoff: datetime | None = None,
) -> HistoricalFreeFloatReplay:
    materialized = tuple(observations)
    if cutoff is not None and (cutoff.tzinfo is None or cutoff.utcoffset() is None):
        raise ValueError("cutoff must be timezone-aware")

    seen: dict[str, HistoricalFreeFloatObservation] = {}
    current: dict[ObservationKey, HistoricalFreeFloatObservation] = {}
    admitted: list[HistoricalFreeFloatObservation] = []

    ordered = sorted(materialized, key=lambda row: (row.published_at, row.record_id))
    for row in ordered:
        if cutoff is not None and row.published_at > cutoff:
            continue
        if row.record_id in seen:
            raise ValueError(f"duplicate record_id: {row.record_id}")

        key: ObservationKey = (row.ticker, row.as_of_date, row.source_family)
        active = current.get(key)

        if row.revision_kind is FreeFloatRevisionKind.ORIGINAL:
            if active is not None:
                raise ValueError(
                    "duplicate original observation for ticker/as-of/source family"
                )
            current[key] = row
        else:
            superseded = seen.get(row.supersedes_record_id or "")
            if superseded is None:
                raise ValueError("correction supersedes unknown/not-yet-published record")
            if (
                superseded.ticker != row.ticker
                or superseded.as_of_date != row.as_of_date
                or superseded.source_family is not row.source_family
            ):
                raise ValueError("correction identity differs from superseded record")
            if row.published_at <= superseded.published_at:
                raise ValueError("correction must be published after superseded record")
            if active is None or active.record_id != superseded.record_id:
                raise ValueError("correction lineage is ambiguous or stale")
            current[key] = row

        seen[row.record_id] = row
        admitted.append(row)

    return HistoricalFreeFloatReplay(
        admitted=tuple(admitted),
        current=dict(
            sorted(
                current.items(),
                key=lambda item: (item[0][0], item[0][1], item[0][2].value),
            )
        ),
    )


def reconcile_cross_source(
    replay: HistoricalFreeFloatReplay,
    *,
    percentage_tolerance: float = 0.01,
) -> tuple[FreeFloatCrossSourceReconciliation, ...]:
    if not isfinite(percentage_tolerance) or percentage_tolerance < 0:
        raise ValueError("percentage_tolerance must be finite and non-negative")

    grouped: dict[tuple[str, date], list[HistoricalFreeFloatObservation]] = {}
    for row in replay.current.values():
        grouped.setdefault((row.ticker, row.as_of_date), []).append(row)

    result: list[FreeFloatCrossSourceReconciliation] = []
    for (ticker, as_of_date), rows in sorted(grouped.items()):
        ordered_rows = tuple(sorted(rows, key=lambda row: row.source_family.value))
        if len(ordered_rows) == 1:
            result.append(
                FreeFloatCrossSourceReconciliation(
                    ticker=ticker,
                    as_of_date=as_of_date,
                    status=FreeFloatCrossSourceStatus.SINGLE_SOURCE,
                    observations=ordered_rows,
                    share_spread=None,
                    percentage_point_spread=None,
                )
            )
            continue

        shares = [row.free_float_shares for row in ordered_rows]
        pcts = [row.free_float_pct for row in ordered_rows]
        share_spread = max(shares) - min(shares)
        pct_spread = max(pcts) - min(pcts)
        status = (
            FreeFloatCrossSourceStatus.AGREE
            if share_spread == 0 and pct_spread <= percentage_tolerance
            else FreeFloatCrossSourceStatus.CONFLICT
        )
        result.append(
            FreeFloatCrossSourceReconciliation(
                ticker=ticker,
                as_of_date=as_of_date,
                status=status,
                observations=ordered_rows,
                share_spread=share_spread,
                percentage_point_spread=pct_spread,
            )
        )

    return tuple(result)


def census_historical_free_float(
    replay: HistoricalFreeFloatReplay,
) -> HistoricalFreeFloatCensus:
    current_rows = tuple(replay.current.values())
    as_of_dates = tuple(sorted({row.as_of_date for row in current_rows}))
    issuer_count_by_as_of = {
        as_of: len({row.ticker for row in current_rows if row.as_of_date == as_of})
        for as_of in as_of_dates
    }
    family_counts = Counter(row.source_family.value for row in current_rows)
    correction_count = sum(
        row.revision_kind is FreeFloatRevisionKind.CORRECTION
        for row in replay.admitted
    )
    reconciliations = reconcile_cross_source(replay)
    status_counts = Counter(row.status.value for row in reconciliations)

    return HistoricalFreeFloatCensus(
        admitted_record_count=len(replay.admitted),
        current_observation_count=len(current_rows),
        unique_ticker_count=len({row.ticker for row in current_rows}),
        unique_as_of_dates=as_of_dates,
        issuer_count_by_as_of_date=dict(issuer_count_by_as_of),
        current_source_family_counts=dict(sorted(family_counts.items())),
        admitted_correction_count=correction_count,
        cross_source_status_counts=dict(sorted(status_counts.items())),
    )


def arithmetic_percentage_difference(
    observation: HistoricalFreeFloatObservation,
) -> float | None:
    """Diagnostic only; never replaces the explicit official percentage."""
    if observation.total_listed_shares is None:
        return None
    arithmetic_pct = (
        observation.free_float_shares / observation.total_listed_shares * 100.0
    )
    return observation.free_float_pct - arithmetic_pct
