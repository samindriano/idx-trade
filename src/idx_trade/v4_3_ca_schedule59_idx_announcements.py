"""Deterministic helpers for official IDX announcement discovery.

This module is outcome-blind and non-admissive. It only derives frozen query
windows, identifies deterministic candidate announcements from title/subject,
and validates official IDX attachment URLs. Semantic admission is a later
offline step.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import pandas as pd


@dataclass(frozen=True)
class AnnouncementCandidate:
    event_id: str
    ticker: str
    source_type: str
    source_dates: str
    announcement_no: str
    announcement_date: str
    title: str
    subject: str
    attachment_url: str
    attachment_filename: str


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def normalize_ticker(value: Any) -> str:
    return clean(value).upper().replace(".JK", "")


def parse_pipe_dates(value: Any) -> tuple[pd.Timestamp, ...]:
    result: set[pd.Timestamp] = set()
    for token in str(value or "").split("|"):
        token = clean(token)
        if not token:
            continue
        parsed = pd.to_datetime(token, errors="coerce")
        if pd.isna(parsed):
            raise RuntimeError(f"SOURCE_DATE_INVALID:{token}")
        stamp = pd.Timestamp(parsed)
        if stamp.tz is not None:
            stamp = stamp.tz_localize(None)
        result.add(stamp.normalize())
    if not result:
        raise RuntimeError("SOURCE_DATES_EMPTY")
    return tuple(sorted(result))


def date_window(source_dates: Iterable[pd.Timestamp], *, before_days: int, after_days: int) -> tuple[str, str]:
    dates = tuple(source_dates)
    if not dates:
        raise RuntimeError("DATE_WINDOW_SOURCE_DATES_EMPTY")
    start = min(dates) - timedelta(days=int(before_days))
    end = max(dates) + timedelta(days=int(after_days))
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def candidate_terms(source_type: str, config: dict[str, Any]) -> tuple[str, ...]:
    source = clean(source_type).casefold()
    family = config.get("candidate_terms") or {}
    values = family.get(source) or []
    generic = config.get("generic_candidate_terms") or []
    terms = {clean(value).casefold() for value in [*values, *generic] if clean(value)}
    if not terms:
        raise RuntimeError(f"CANDIDATE_TERMS_EMPTY:{source_type}")
    return tuple(sorted(terms))


def announcement_is_candidate(title: str, subject: str, *, source_type: str, config: dict[str, Any]) -> bool:
    text = clean(f"{title} {subject}").casefold()
    return any(term in text for term in candidate_terms(source_type, config))


def official_idx_attachment_url(raw_path: str, *, base_url: str, allowed_hosts: Iterable[str]) -> str | None:
    value = clean(raw_path)
    if not value:
        return None
    url = urljoin(base_url.rstrip("/") + "/", value)
    parsed = urlparse(url)
    allowed = {clean(host).casefold() for host in allowed_hosts}
    if parsed.scheme != "https" or (parsed.hostname or "").casefold() not in allowed:
        return None
    return url


def request_identity(records: Iterable[dict[str, Any]]) -> str:
    rows = sorted(
        {
            f"{clean(row.get('request_kind'))}|{clean(row.get('request_key'))}|"
            f"{clean(row.get('requested_url'))}|{clean(row.get('sha256'))}|{clean(row.get('path'))}"
            for row in records
            if int(row.get("status_code") or 0) == 200 and clean(row.get("sha256"))
        }
    )
    payload = "\n".join(rows) + ("\n" if rows else "")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
