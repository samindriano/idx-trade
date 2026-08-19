"""Frozen helpers for the final residual-47 IDX Digital Statistic split lane."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

import pandas as pd


ELIGIBLE_SOURCE_TYPES = {
    "stock split",
    "reverse stock",
    "reverse stock split",
    "reverse split",
}


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def ticker(value: object) -> str:
    return clean(value).upper().replace(".JK", "")


def timestamp(value: object) -> pd.Timestamp | None:
    text = clean(value)
    if text in {"", "-", "None", "nan", "NaT"}:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    result = pd.Timestamp(parsed)
    if result.tz is not None:
        result = result.tz_localize(None)
    return result.normalize()


def parse_source_dates(value: object) -> tuple[pd.Timestamp, ...]:
    dates: set[pd.Timestamp] = set()
    for token in clean(value).split("|"):
        parsed = timestamp(token)
        if parsed is not None:
            dates.add(parsed)
    return tuple(sorted(dates))


def month_scope(source_dates: Iterable[pd.Timestamp], *, radius: int) -> tuple[tuple[int, int], ...]:
    months: set[tuple[int, int]] = set()
    for value in source_dates:
        base = pd.Timestamp(value).normalize().replace(day=1)
        for offset in range(-radius, radius + 1):
            candidate = base + pd.DateOffset(months=offset)
            months.add((int(candidate.year), int(candidate.month)))
    return tuple(sorted(months))


def normalize_split_row(row: dict[str, Any]) -> dict[str, Any]:
    code = ticker(row.get("code") or row.get("Code") or row.get("KodeEmiten"))
    name = clean(row.get("issuerName") or row.get("name") or row.get("IssuerName"))
    action_type = clean(row.get("Type") or row.get("type") or row.get("ActionType"))
    listing_date = clean(row.get("ListingDate") or row.get("listingDate") or row.get("Date"))
    ratio = clean(row.get("Ratio") or row.get("ratio"))
    old_nominal = row.get("OldNominal") if row.get("OldNominal") is not None else row.get("oldNominal")
    new_nominal = row.get("NewNominal") if row.get("NewNominal") is not None else row.get("newNominal")
    listed_shares = row.get("ListedShares") if row.get("ListedShares") is not None else row.get("listedShares")
    additional_shares = row.get("NumOfShares") if row.get("NumOfShares") is not None else row.get("additionalShares")
    normalized = {
        "ticker": code,
        "issuer_name": name,
        "action_type": action_type,
        "listing_date": listing_date,
        "ratio": ratio,
        "old_nominal": clean(old_nominal),
        "new_nominal": clean(new_nominal),
        "listed_shares": clean(listed_shares),
        "additional_shares": clean(additional_shares),
    }
    normalized["row_identity_sha256"] = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return normalized


def source_type_compatible(source_type: object, action_type: object) -> bool:
    expected = clean(source_type).casefold()
    observed = clean(action_type).casefold()
    if expected not in ELIGIBLE_SOURCE_TYPES or not observed:
        return False
    if "reverse" in expected:
        return "reverse" in observed
    return "split" in observed and "reverse" not in observed


def listing_date_linked(
    listing_date: object,
    source_dates: Iterable[pd.Timestamp],
    *,
    max_distance_days: int,
) -> bool:
    listing = timestamp(listing_date)
    dates = tuple(source_dates)
    if listing is None or not dates:
        return False
    return min(abs((listing - value).days) for value in dates) <= int(max_distance_days)
