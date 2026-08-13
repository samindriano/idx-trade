from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd


SECTOR_SOURCE_FEATURES = (
    "close_return_5",
    "close_return_20",
    "close_position_20",
)

SECTOR_RANK_COLUMNS = tuple(f"sector_rank_{name}" for name in SECTOR_SOURCE_FEATURES)
SECTOR_RELATIVE_COLUMNS = tuple(f"sector_relative_{name}" for name in SECTOR_SOURCE_FEATURES)
SECTOR_RELATIVE_FEATURE_COLUMNS = (
    "sector_rank_close_return_5",
    "sector_rank_close_return_20",
    "sector_rank_close_position_20",
    "sector_relative_close_return_5",
    "sector_relative_close_return_20",
    "sector_relative_close_position_20",
)

SECTOR_HISTORY_REQUIRED_COLUMNS = (
    "ticker",
    "sector_code",
    "effective_from",
    "effective_to_exclusive",
    "available_at",
    "source_id",
    "source_sha256",
)

MIN_FINITE_SECTOR_MEMBERS = 5
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_FORBIDDEN_OUTCOME_COLUMNS = {
    "binary_target",
    "label_status",
    "actual_up",
    "actual_return",
    "actual_return_pct",
    "future_return",
    "outcome",
}


@dataclass(frozen=True)
class SectorHistoryAudit:
    rows: int
    tickers: int
    sectors: int
    source_ids: int
    source_hashes: int
    first_effective_from: str
    last_effective_from: str
    first_available_at: str
    last_available_at: str


def _normalize_ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _normalize_date(series: pd.Series, *, field: str, allow_missing: bool = False) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce", utc=True)
    if not allow_missing and values.isna().any():
        raise ValueError(f"sector history contains invalid {field}")
    values = values.dt.tz_convert(None).dt.normalize()
    return values


def normalize_sector_history(history: pd.DataFrame) -> pd.DataFrame:
    missing = set(SECTOR_HISTORY_REQUIRED_COLUMNS) - set(history.columns)
    if missing:
        raise ValueError(f"sector history missing columns: {sorted(missing)}")

    data = history.loc[:, SECTOR_HISTORY_REQUIRED_COLUMNS].copy()
    data["ticker"] = _normalize_ticker(data["ticker"])
    data["sector_code"] = data["sector_code"].astype(str).str.strip()
    data["source_id"] = data["source_id"].astype(str).str.strip()
    data["source_sha256"] = data["source_sha256"].astype(str).str.strip().str.lower()
    data["effective_from"] = _normalize_date(data["effective_from"], field="effective_from")
    data["effective_to_exclusive"] = _normalize_date(
        data["effective_to_exclusive"], field="effective_to_exclusive", allow_missing=True
    )
    data["available_at"] = _normalize_date(data["available_at"], field="available_at")

    if data["ticker"].eq("").any() or data["sector_code"].eq("").any() or data["source_id"].eq("").any():
        raise ValueError("sector history contains empty ticker/sector/source id")
    if not data["source_sha256"].map(lambda value: bool(_SHA256_RE.fullmatch(value))).all():
        raise ValueError("sector history contains invalid source_sha256")
    if data.duplicated().any():
        raise ValueError("sector history contains duplicate rows")

    closed = data["effective_to_exclusive"].notna()
    if (data.loc[closed, "effective_to_exclusive"] <= data.loc[closed, "effective_from"]).any():
        raise ValueError("sector history contains non-positive effective interval")
    if (data.loc[closed, "available_at"] >= data.loc[closed, "effective_to_exclusive"]).any():
        raise ValueError("sector history classification became available only after its interval ended")

    data["usable_from"] = data[["effective_from", "available_at"]].max(axis=1)
    data = data.sort_values(
        ["ticker", "usable_from", "effective_from", "sector_code", "source_id"],
        kind="mergesort",
    ).reset_index(drop=True)

    for ticker, block in data.groupby("ticker", sort=False):
        previous_end: pd.Timestamp | None = None
        previous_open = False
        for row in block.itertuples(index=False):
            start = pd.Timestamp(row.usable_from)
            end = None if pd.isna(row.effective_to_exclusive) else pd.Timestamp(row.effective_to_exclusive)
            if previous_open:
                raise ValueError(f"sector history has interval after open-ended interval for {ticker}")
            if previous_end is not None and start < previous_end:
                raise ValueError(f"sector history has overlapping usable intervals for {ticker}")
            previous_open = end is None
            previous_end = end

    return data


def validate_sector_history(history: pd.DataFrame) -> tuple[pd.DataFrame, SectorHistoryAudit]:
    data = normalize_sector_history(history)
    audit = SectorHistoryAudit(
        rows=int(len(data)),
        tickers=int(data["ticker"].nunique()),
        sectors=int(data["sector_code"].nunique()),
        source_ids=int(data["source_id"].nunique()),
        source_hashes=int(data["source_sha256"].nunique()),
        first_effective_from=str(data["effective_from"].min().date()),
        last_effective_from=str(data["effective_from"].max().date()),
        first_available_at=str(data["available_at"].min().date()),
        last_available_at=str(data["available_at"].max().date()),
    )
    return data, audit


def assign_pit_sector(features: pd.DataFrame, sector_history: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"sector assignment input missing columns: {sorted(missing)}")
    forbidden = _FORBIDDEN_OUTCOME_COLUMNS.intersection(features.columns)
    if forbidden:
        raise ValueError(f"sector assignment input contains label/outcome columns: {sorted(forbidden)}")

    history, _ = validate_sector_history(sector_history)
    data = features.copy()
    data["ticker"] = _normalize_ticker(data["ticker"])
    dates = pd.to_datetime(data["date"], errors="coerce")
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_localize(None)
    data["date"] = dates.dt.normalize()
    if data["date"].isna().any():
        raise ValueError("sector assignment input contains invalid dates")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("sector assignment input contains duplicate ticker/date rows")

    data["sector_code"] = pd.Series(pd.NA, index=data.index, dtype="string")
    data["sector_source_id"] = pd.Series(pd.NA, index=data.index, dtype="string")
    data["sector_source_sha256"] = pd.Series(pd.NA, index=data.index, dtype="string")
    data["sector_usable_from"] = pd.NaT

    positions_by_ticker = {
        ticker: np.asarray(index, dtype=int)
        for ticker, index in data.groupby("ticker", sort=False).groups.items()
    }
    for ticker, block in history.groupby("ticker", sort=False):
        positions = positions_by_ticker.get(ticker)
        if positions is None:
            continue
        row_dates = data.loc[positions, "date"]
        assigned = np.zeros(len(positions), dtype=bool)
        for row in block.itertuples(index=False):
            start = pd.Timestamp(row.usable_from)
            mask = row_dates.ge(start).to_numpy(dtype=bool)
            if not pd.isna(row.effective_to_exclusive):
                mask &= row_dates.lt(pd.Timestamp(row.effective_to_exclusive)).to_numpy(dtype=bool)
            if (assigned & mask).any():
                raise RuntimeError(f"multiple PIT sector assignments for {ticker}")
            if not mask.any():
                continue
            target = positions[mask]
            data.loc[target, "sector_code"] = str(row.sector_code)
            data.loc[target, "sector_source_id"] = str(row.source_id)
            data.loc[target, "sector_source_sha256"] = str(row.source_sha256)
            data.loc[target, "sector_usable_from"] = pd.Timestamp(row.usable_from)
            assigned |= mask

    return data


def _finite_numeric(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    return values.where(np.isfinite(values))


def build_sector_relative_features(
    features: pd.DataFrame,
    sector_history: pd.DataFrame,
    *,
    min_finite_members: int = MIN_FINITE_SECTOR_MEMBERS,
) -> pd.DataFrame:
    if min_finite_members != MIN_FINITE_SECTOR_MEMBERS:
        raise ValueError("V3-D min_finite_members is frozen at 5")
    required = {"ticker", "date", "universe_primary_liquid", *SECTOR_SOURCE_FEATURES}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"sector feature input missing columns: {sorted(missing)}")
    forbidden = _FORBIDDEN_OUTCOME_COLUMNS.intersection(features.columns)
    if forbidden:
        raise ValueError(f"sector feature input contains label/outcome columns: {sorted(forbidden)}")

    data = assign_pit_sector(features, sector_history)
    for source in SECTOR_SOURCE_FEATURES:
        data[source] = _finite_numeric(data[source])

    primary = data["universe_primary_liquid"].astype(bool)
    known_sector = data["sector_code"].notna()
    eligible_base = primary & known_sector

    data["sector_member_count"] = np.nan
    member_counts = (
        data.loc[eligible_base]
        .groupby(["date", "sector_code"], sort=True)["ticker"]
        .transform("size")
        .astype(float)
    )
    data.loc[member_counts.index, "sector_member_count"] = member_counts

    for source in SECTOR_SOURCE_FEATURES:
        rank_column = f"sector_rank_{source}"
        relative_column = f"sector_relative_{source}"
        data[rank_column] = np.nan
        data[relative_column] = np.nan

        finite_mask = eligible_base & data[source].notna()
        if not finite_mask.any():
            continue
        finite = data.loc[finite_mask, ["date", "sector_code", source]].copy()
        counts = finite.groupby(["date", "sector_code"], sort=True)[source].transform("count")
        valid = counts.ge(MIN_FINITE_SECTOR_MEMBERS)
        valid_index = finite.index[valid]
        if len(valid_index) == 0:
            continue

        valid_frame = data.loc[valid_index, ["date", "sector_code", source]].copy()
        ranks = valid_frame.groupby(["date", "sector_code"], sort=True)[source].rank(
            method="average", pct=True
        )
        medians = valid_frame.groupby(["date", "sector_code"], sort=True)[source].transform("median")
        data.loc[valid_index, rank_column] = ranks.astype(float)
        data.loc[valid_index, relative_column] = (
            data.loc[valid_index, source].astype(float) - medians.astype(float)
        )

    return data.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
