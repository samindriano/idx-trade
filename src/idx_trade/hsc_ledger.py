from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import Enum
from math import isfinite
import re
from typing import Iterable, Mapping


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TICKER_RE = re.compile(r"^[A-Z0-9]{4,5}$")


class HSCStatus(str, Enum):
    ACTIVE = "HSC_ACTIVE"
    REMOVED = "HSC_REMOVED"


class HSCRevisionKind(str, Enum):
    ORIGINAL = "ORIGINAL"
    CORRECTION = "CORRECTION"
    REMOVAL = "REMOVAL"


class HSCMethodologyVersion(str, Enum):
    INITIAL_2026 = "HSC_2026_INITIAL"
    PRICE_IMPACT_REVISION_2026 = "HSC_2026_PRICE_IMPACT_REVISION"


@dataclass(frozen=True)
class HSCEvent:
    event_id: str
    ticker: str
    status: HSCStatus
    ownership_as_of_date: date
    published_at: datetime
    concentration_pct: float | None
    determination_methodology_version: HSCMethodologyVersion
    idx_announcement_no: str
    ksei_announcement_no: str
    revision_kind: HSCRevisionKind
    supersedes_event_id: str | None
    source_url: str
    source_sha256: str
    metadata_source_sha256: str

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id is empty")
        ticker = self.ticker.strip().upper()
        if not _TICKER_RE.fullmatch(ticker):
            raise ValueError(f"invalid ticker: {self.ticker!r}")
        object.__setattr__(self, "ticker", ticker)
        if self.published_at.tzinfo is None or self.published_at.utcoffset() is None:
            raise ValueError("published_at must be timezone-aware")
        if self.ownership_as_of_date > self.published_at.date():
            raise ValueError("ownership_as_of_date cannot be after publication date")
        if self.concentration_pct is not None:
            value = float(self.concentration_pct)
            if not isfinite(value) or not 0.0 <= value <= 100.0:
                raise ValueError("concentration_pct must be finite and within [0, 100]")
            object.__setattr__(self, "concentration_pct", value)
        if not self.idx_announcement_no.strip():
            raise ValueError("idx_announcement_no is empty")
        if not self.ksei_announcement_no.strip():
            raise ValueError("ksei_announcement_no is empty")
        if not self.source_url.startswith(("https://www.idx.id/", "https://www.idx.co.id/")):
            raise ValueError("source_url must be an official IDX URL")
        for name, value in (
            ("source_sha256", self.source_sha256),
            ("metadata_source_sha256", self.metadata_source_sha256),
        ):
            if not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{name} must be lowercase SHA-256 hex")

        if self.revision_kind is HSCRevisionKind.ORIGINAL:
            if self.status is not HSCStatus.ACTIVE:
                raise ValueError("ORIGINAL event must be HSC_ACTIVE")
            if self.concentration_pct is None:
                raise ValueError("ORIGINAL HSC event requires explicit concentration_pct")
            if self.supersedes_event_id is not None:
                raise ValueError("ORIGINAL event cannot supersede another event")
        elif self.revision_kind is HSCRevisionKind.CORRECTION:
            if self.status is not HSCStatus.ACTIVE:
                raise ValueError("CORRECTION event must remain HSC_ACTIVE")
            if self.concentration_pct is None:
                raise ValueError("CORRECTION HSC event requires explicit concentration_pct")
            if not self.supersedes_event_id:
                raise ValueError("CORRECTION event requires supersedes_event_id")
        elif self.revision_kind is HSCRevisionKind.REMOVAL:
            if self.status is not HSCStatus.REMOVED:
                raise ValueError("REMOVAL event must be HSC_REMOVED")
            if self.supersedes_event_id is not None:
                raise ValueError("REMOVAL event does not use supersedes_event_id")


@dataclass(frozen=True)
class HSCActiveState:
    ticker: str
    active_since: datetime
    last_event_id: str
    ownership_as_of_date: date
    concentration_pct: float
    determination_methodology_version: HSCMethodologyVersion


@dataclass(frozen=True)
class HSCReplayResult:
    events: tuple[HSCEvent, ...]
    active: Mapping[str, HSCActiveState]

    @property
    def active_tickers(self) -> frozenset[str]:
        return frozenset(self.active)


def replay_hsc_events(
    events: Iterable[HSCEvent],
    *,
    cutoff: datetime | None = None,
) -> HSCReplayResult:
    materialized = tuple(events)
    if cutoff is not None and (cutoff.tzinfo is None or cutoff.utcoffset() is None):
        raise ValueError("cutoff must be timezone-aware")

    seen_ids: dict[str, HSCEvent] = {}
    seen_source_hashes: dict[str, str] = {}
    active: dict[str, HSCActiveState] = {}
    admitted: list[HSCEvent] = []

    ordered = sorted(materialized, key=lambda event: (event.published_at, event.event_id))
    for event in ordered:
        if cutoff is not None and event.published_at > cutoff:
            continue
        if event.event_id in seen_ids:
            raise ValueError(f"duplicate event_id: {event.event_id}")
        prior_hash_event = seen_source_hashes.get(event.source_sha256)
        if prior_hash_event is not None:
            raise ValueError(
                "duplicate source_sha256 for distinct events: "
                f"{prior_hash_event} and {event.event_id}"
            )

        if event.revision_kind is HSCRevisionKind.ORIGINAL:
            if event.ticker in active:
                raise ValueError(
                    f"duplicate active addition without correction: {event.ticker}"
                )
            assert event.concentration_pct is not None
            active[event.ticker] = HSCActiveState(
                ticker=event.ticker,
                active_since=event.published_at,
                last_event_id=event.event_id,
                ownership_as_of_date=event.ownership_as_of_date,
                concentration_pct=event.concentration_pct,
                determination_methodology_version=event.determination_methodology_version,
            )
        elif event.revision_kind is HSCRevisionKind.CORRECTION:
            superseded = seen_ids.get(event.supersedes_event_id or "")
            if superseded is None:
                raise ValueError(
                    "correction supersedes unknown/not-yet-published event: "
                    f"{event.event_id}"
                )
            if superseded.ticker != event.ticker:
                raise ValueError("correction ticker differs from superseded event")
            if event.published_at <= superseded.published_at:
                raise ValueError("correction must be published after superseded event")
            state = active.get(event.ticker)
            if state is None:
                raise ValueError("correction cannot revive an inactive HSC state")
            if state.last_event_id != superseded.event_id:
                raise ValueError(
                    "correction lineage is ambiguous: superseded event is not current state event"
                )
            assert event.concentration_pct is not None
            active[event.ticker] = replace(
                state,
                last_event_id=event.event_id,
                ownership_as_of_date=event.ownership_as_of_date,
                concentration_pct=event.concentration_pct,
                determination_methodology_version=event.determination_methodology_version,
            )
        else:
            state = active.get(event.ticker)
            if state is None:
                raise ValueError(f"removal of inactive ticker: {event.ticker}")
            if event.published_at <= state.active_since:
                raise ValueError("removal must be published after active state begins")
            del active[event.ticker]

        seen_ids[event.event_id] = event
        seen_source_hashes[event.source_sha256] = event.event_id
        admitted.append(event)

    return HSCReplayResult(
        events=tuple(admitted),
        active=dict(sorted(active.items())),
    )


def validate_active_reconciliation(
    replay: HSCReplayResult,
    expected_active_tickers: Iterable[str],
) -> None:
    expected = frozenset(str(ticker).strip().upper() for ticker in expected_active_tickers)
    invalid = sorted(ticker for ticker in expected if not _TICKER_RE.fullmatch(ticker))
    if invalid:
        raise ValueError(f"invalid expected ticker(s): {invalid}")
    actual = replay.active_tickers
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise ValueError(
            "HSC active-set reconciliation failed: "
            f"expected={len(expected)} actual={len(actual)} "
            f"missing={missing} unexpected={unexpected}"
        )
