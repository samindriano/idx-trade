from __future__ import annotations

import re

import numpy as np
import pandas as pd


SECTOR_SOURCE_COLUMNS = (
    "close_return_5",
    "close_return_20",
    "close_position_20",
)

SECTOR_RANK_COLUMNS = (
    "sector_rank_close_return_5",
    "sector_rank_close_return_20",
    "sector_rank_close_position_20",
)

SECTOR_RELATIVE_COLUMNS = (
    "sector_relative_close_return_5",
    "sector_relative_close_return_20",
    "sector_relative_close_position_20",
)

SECTOR_FEATURE_COLUMNS = (*SECTOR_RANK_COLUMNS, *SECTOR_RELATIVE_COLUMNS)
SECTOR_MIN_FINITE_MEMBERS = 5

SECTOR_HISTORY_REQUIRED_COLUMNS = (
    "ticker",
    "sector_code",
    "effective_from",
    "effective_to_exclusive",
    "available_at",
    "source_id",
    "source_sha256",
)

SECTOR_ASSIGNMENT_AUDIT_COLUMNS = (
    "sector_code",
    "sector_usable_from",
    "sector_effective_to_exclusive",
    "sector_source_id",
    "sector_source_sha256",
)

_BANNED_OUTCOME_COLUMNS = {
    "binary_target",
    "label_status",
    "tp_first",
    "sl_first",
    "outcome",
    "realized_return",
}
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _normalize_ticker(values: pd.Series) -> pd.Series:
    return (
        values.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _normalize_date(values: pd.Series, *, column: str, allow_missing: bool = False) -> pd.Series:
    original = values.copy()
    parsed = pd.to_datetime(values, errors="coerce")
    if getattr(parsed.dt, "tz", None) is not None:
        parsed = parsed.dt.tz_localize(None)
    parsed = parsed.dt.normalize()
    if allow_missing:
        original_missing = original.isna() | original.astype(str).str.strip().isin({"", "NaT", "None", "nan"})
        invalid = parsed.isna() & ~original_missing
        if invalid.any():
            raise ValueError(f"invalid {column} value")
    elif parsed.isna().any():
        raise ValueError(f"invalid {column} value")
    return parsed


def _security_master_tickers(security_master: pd.DataFrame) -> set[str]:
    ticker_column = next(
        (
            column
            for column in ("ticker", "normalized_ticker", "security_ticker", "symbol")
            if column in security_master.columns
        ),
        None,
    )
    if ticker_column is None:
        raise ValueError("security master has no recognized ticker column")
    normalized = _normalize_ticker(security_master[ticker_column])
    if normalized.eq("").any():
        raise ValueError("security master contains empty ticker")
    return set(normalized)


def validate_sector_history(
    history: pd.DataFrame,
    security_master: pd.DataFrame,
) -> pd.DataFrame:
    """Validate and normalize the frozen point-in-time sector-history contract."""

    missing = set(SECTOR_HISTORY_REQUIRED_COLUMNS) - set(history.columns)
    if missing:
        raise ValueError(f"sector history missing columns: {sorted(missing)}")

    data = history.copy()
    data["ticker"] = _normalize_ticker(data["ticker"])
    data["sector_code"] = data["sector_code"].astype(str).str.strip()
    data["source_id"] = data["source_id"].astype(str).str.strip()
    data["source_sha256"] = data["source_sha256"].astype(str).str.strip().str.lower()

    if data["ticker"].eq("").any():
        raise ValueError("sector history contains empty ticker")
    if data["sector_code"].eq("").any():
        raise ValueError("sector history contains empty sector_code")
    if data["source_id"].eq("").any():
        raise ValueError("sector history contains empty source_id")
    if not data["source_sha256"].map(lambda value: bool(_SHA256_RE.fullmatch(value))).all():
        raise ValueError("sector history contains invalid source_sha256")

    data["effective_from"] = _normalize_date(data["effective_from"], column="effective_from")
    data["effective_to_exclusive"] = _normalize_date(
        data["effective_to_exclusive"],
        column="effective_to_exclusive",
        allow_missing=True,
    )
    available = pd.to_datetime(data["available_at"], errors="coerce", utc=True)
    if available.isna().any():
        raise ValueError("sector history contains invalid available_at")
    data["available_at"] = available.dt.tz_convert(None)
    available_date = data["available_at"].dt.normalize()
    data["usable_from"] = pd.concat([data["effective_from"], available_date], axis=1).max(axis=1)

    closed = data["effective_to_exclusive"].notna()
    if (data.loc[closed, "effective_to_exclusive"] <= data.loc[closed, "effective_from"]).any():
        raise ValueError("sector history effective_to_exclusive must be after effective_from")
    if (available_date.loc[closed] >= data.loc[closed, "effective_to_exclusive"]).any():
        raise ValueError("sector history available_at is not usable before interval end")
    if (data.loc[closed, "usable_from"] >= data.loc[closed, "effective_to_exclusive"]).any():
        raise ValueError("sector history usable interval is empty")

    master = _security_master_tickers(security_master)
    unknown = sorted(set(data["ticker"]) - master)
    if unknown:
        raise ValueError(f"sector history contains untraceable tickers: {unknown[:20]}")

    identity_cols = ["ticker", "effective_from", "effective_to_exclusive"]
    for _, block in data.groupby(identity_cols, dropna=False, sort=False):
        if len(block) <= 1:
            continue
        compare_cols = ["sector_code", "available_at", "source_id", "source_sha256"]
        if block[compare_cols].drop_duplicates().shape[0] != 1:
            raise ValueError("sector history contains inconsistent duplicate interval metadata")
    data = data.drop_duplicates(subset=[*identity_cols, "sector_code", "available_at", "source_id", "source_sha256"])

    data = data.sort_values(["ticker", "usable_from", "effective_from", "sector_code"], kind="mergesort").reset_index(drop=True)
    for ticker, block in data.groupby("ticker", sort=False):
        previous_end: pd.Timestamp | None = None
        previous_open = False
        for row in block.itertuples(index=False):
            start = pd.Timestamp(row.usable_from)
            end = row.effective_to_exclusive
            if previous_open:
                raise ValueError(f"sector history usable intervals overlap for {ticker}")
            if previous_end is not None and start < previous_end:
                raise ValueError(f"sector history usable intervals overlap for {ticker}")
            if pd.isna(end):
                previous_open = True
                previous_end = None
            else:
                previous_end = pd.Timestamp(end)

    return data


def sector_history_provenance(history: pd.DataFrame) -> dict[str, object]:
    if history.empty:
        raise ValueError("validated sector history is empty")
    return {
        "rows": int(len(history)),
        "tickers": int(history["ticker"].nunique()),
        "sectors": int(history["sector_code"].nunique()),
        "first_effective_from": str(pd.Timestamp(history["effective_from"].min()).date()),
        "last_effective_from": str(pd.Timestamp(history["effective_from"].max()).date()),
        "first_usable_from": str(pd.Timestamp(history["usable_from"].min()).date()),
        "last_usable_from": str(pd.Timestamp(history["usable_from"].max()).date()),
        "source_inventory": [
            {"source_id": source_id, "source_sha256": source_sha}
            for source_id, source_sha in (
                history[["source_id", "source_sha256"]]
                .drop_duplicates()
                .sort_values(["source_id", "source_sha256"], kind="mergesort")
                .itertuples(index=False, name=None)
            )
        ],
        "overlap_audit_pass": True,
    }


def assign_pit_sector(features: pd.DataFrame, validated_history: pd.DataFrame) -> pd.DataFrame:
    """Assign only sector intervals already usable on each feature date."""

    banned = _BANNED_OUTCOME_COLUMNS.intersection(features.columns)
    if banned:
        raise ValueError(f"sector feature input may not contain label/outcome columns: {sorted(banned)}")
    required = {"ticker", "date"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"sector feature input missing columns: {sorted(missing)}")

    data = features.copy()
    data["ticker"] = _normalize_ticker(data["ticker"])
    data["date"] = _normalize_date(data["date"], column="date")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("sector feature input contains duplicate ticker/date rows")

    data["sector_code"] = pd.Series(pd.NA, index=data.index, dtype="object")
    data["sector_usable_from"] = pd.Series(pd.NaT, index=data.index, dtype="datetime64[ns]")
    data["sector_effective_to_exclusive"] = pd.Series(pd.NaT, index=data.index, dtype="datetime64[ns]")
    data["sector_source_id"] = pd.Series(pd.NA, index=data.index, dtype="object")
    data["sector_source_sha256"] = pd.Series(pd.NA, index=data.index, dtype="object")

    history_by_ticker = {
        ticker: block.reset_index(drop=True)
        for ticker, block in validated_history.groupby("ticker", sort=False)
    }

    for ticker, positions in data.groupby("ticker", sort=False).groups.items():
        history = history_by_ticker.get(str(ticker))
        if history is None or history.empty:
            continue
        starts = history["usable_from"].to_numpy(dtype="datetime64[ns]")
        dates = data.loc[positions, "date"].to_numpy(dtype="datetime64[ns]")
        selected = np.searchsorted(starts, dates, side="right") - 1
        for local_position, history_position in enumerate(selected):
            if history_position < 0:
                continue
            row = history.iloc[int(history_position)]
            signal_date = pd.Timestamp(dates[local_position])
            end = row["effective_to_exclusive"]
            if pd.notna(end) and signal_date >= pd.Timestamp(end):
                continue
            target_index = positions[local_position]
            data.at[target_index, "sector_code"] = row["sector_code"]
            data.at[target_index, "sector_usable_from"] = row["usable_from"]
            data.at[target_index, "sector_effective_to_exclusive"] = row["effective_to_exclusive"]
            data.at[target_index, "sector_source_id"] = row["source_id"]
            data.at[target_index, "sector_source_sha256"] = row["source_sha256"]

    assigned = data["sector_code"].notna()
    if assigned.any():
        if (data.loc[assigned, "sector_usable_from"] > data.loc[assigned, "date"]).any():
            raise RuntimeError("PIT sector assignment used a future classification")
        closed = assigned & data["sector_effective_to_exclusive"].notna()
        if (data.loc[closed, "date"] >= data.loc[closed, "sector_effective_to_exclusive"]).any():
            raise RuntimeError("PIT sector assignment escaped effective interval")
    return data


def build_sector_relative_features(
    v2_features: pd.DataFrame,
    validated_history: pd.DataFrame,
) -> pd.DataFrame:
    """Append the frozen six same-date PIT sector-relative features outcome-independently."""

    banned = _BANNED_OUTCOME_COLUMNS.intersection(v2_features.columns)
    if banned:
        raise ValueError(f"sector feature input may not contain label/outcome columns: {sorted(banned)}")
    required = {"ticker", "date", "universe_primary_liquid", *SECTOR_SOURCE_COLUMNS}
    missing = required - set(v2_features.columns)
    if missing:
        raise ValueError(f"sector feature input missing columns: {sorted(missing)}")

    data = assign_pit_sector(v2_features, validated_history)
    for source in SECTOR_SOURCE_COLUMNS:
        values = pd.to_numeric(data[source], errors="coerce").astype(float)
        data[source] = values.where(np.isfinite(values))

    primary = data["universe_primary_liquid"].astype(bool) & data["sector_code"].notna()
    for source, rank_column, relative_column in zip(
        SECTOR_SOURCE_COLUMNS,
        SECTOR_RANK_COLUMNS,
        SECTOR_RELATIVE_COLUMNS,
        strict=True,
    ):
        data[rank_column] = np.nan
        data[relative_column] = np.nan
        count_column = f"sector_group_finite_count_{source}"
        data[count_column] = np.nan

        subset = data.loc[primary, ["date", "sector_code", source]].copy()
        finite = subset[source].notna()
        if not finite.any():
            continue
        valid = subset.loc[finite].copy()
        grouped = valid.groupby(["date", "sector_code"], sort=True)[source]
        counts = grouped.transform("count").astype(float)
        medians = grouped.transform("median").astype(float)
        ranks = grouped.rank(method="average", pct=True).astype(float)
        eligible = counts >= SECTOR_MIN_FINITE_MEMBERS

        eligible_index = valid.index[eligible]
        data.loc[eligible_index, rank_column] = ranks.loc[eligible].to_numpy(dtype=float)
        data.loc[eligible_index, relative_column] = (
            valid.loc[eligible_index, source].to_numpy(dtype=float)
            - medians.loc[eligible].to_numpy(dtype=float)
        )
        data.loc[valid.index, count_column] = counts.to_numpy(dtype=float)

    return data.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def sector_group_diagnostics(feature_frame: pd.DataFrame) -> dict[str, object]:
    primary = feature_frame[feature_frame["universe_primary_liquid"].astype(bool)].copy()
    assigned = primary["sector_code"].notna()
    report: dict[str, object] = {
        "primary_rows": int(len(primary)),
        "assigned_rows": int(assigned.sum()),
        "assignment_rate": float(assigned.mean()) if len(primary) else 0.0,
        "sectors": int(primary.loc[assigned, "sector_code"].nunique()),
    }
    for source in SECTOR_SOURCE_COLUMNS:
        count_column = f"sector_group_finite_count_{source}"
        counts = pd.to_numeric(primary[count_column], errors="coerce")
        finite = counts[np.isfinite(counts.to_numpy(dtype=float))]
        report[count_column] = {
            "observed_rows": int(len(finite)),
            "lt_min_rows": int((finite < SECTOR_MIN_FINITE_MEMBERS).sum()),
            "median": float(finite.median()) if len(finite) else None,
            "q25": float(finite.quantile(0.25)) if len(finite) else None,
            "minimum": float(finite.min()) if len(finite) else None,
        }
    return report
