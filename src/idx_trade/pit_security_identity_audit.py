"""Outcome-blind PIT security-identity/listing-domain audit utilities."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .ranking_v4_3_features import (
    V4_CONTROL_FEATURE_COLUMNS,
    V4_MARKET_CONTEXT_COLUMNS,
    V4_MARKET_RELATIVE_COLUMNS,
    V4_XS_FEATURE_COLUMNS,
)


IDENTITY_COLUMNS = (
    "security_id",
    "ticker",
    "company_name",
    "listed_from",
    "listed_to",
    "source",
)
IDENTITY_POLICY = "RESTORE_AUTHORITATIVE_HISTORICAL_MASTER_RIGHT_ONLY_IDENTITIES_V1"
IDENTITY_OVERLAY_COLUMNS = IDENTITY_COLUMNS
KEY_COLUMNS = ("ticker", "date")
NON_REPRESENTATION_COLUMNS = {"ticker", "date", "listed_from", "listed_to"}
REPRESENTATION_COLUMNS = tuple(
    [
        *V4_XS_FEATURE_COLUMNS,
        *V4_MARKET_CONTEXT_COLUMNS,
        *V4_MARKET_RELATIVE_COLUMNS,
        "universe_history_qualified",
        "universe_primary_liquid",
        "market_primary_liquid_count",
        "close_return_5",
        "close_return_20",
        "atr14_over_close",
        "close_position_20",
        "distance_high_20_atr",
        "distance_low_20_atr",
        "distance_high_60_atr",
        "distance_low_60_atr",
        "relative_volume_20",
        "log_regular_value_relative_20",
        "liquidity_active_observations_60",
        "median_regular_value_60",
        "atr14",
        "session_index",
        "high",
        "low",
        "close",
        "volume",
        "regular_market_value",
    ]
)


@dataclass(frozen=True)
class IdentityOverlayDiagnostics:
    frozen_rows: int
    historical_rows: int
    overlay_rows: int
    overlay_tickers: tuple[str, ...]
    duplicate_identity_rows: int
    overlapping_identity_rows: int


@dataclass(frozen=True)
class RepresentationDiff:
    shared_rows: int
    changed_rows: int
    changed_tickers: tuple[str, ...]
    changed_dates: tuple[str, ...]
    changed_by_column: dict[str, int]
    direct_new_rows: int
    direct_new_tickers: tuple[str, ...]
    direct_new_dates: tuple[str, ...]
    spillover_changed_rows: int
    spillover_changed_tickers: tuple[str, ...]
    spillover_changed_dates: tuple[str, ...]
    primary_membership_changes: int
    primary_membership_changed_tickers: tuple[str, ...]
    primary_membership_changed_dates: tuple[str, ...]


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_ticker(values: pd.Series) -> pd.Series:
    return values.astype(str).str.upper().str.strip()


def _normalize_master(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    missing = set(IDENTITY_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {sorted(missing)}")
    out = frame.loc[:, IDENTITY_COLUMNS].copy()
    out["security_id"] = out["security_id"].astype(str).str.strip()
    out["ticker"] = _normalize_ticker(out["ticker"])
    out["company_name"] = out["company_name"].astype(str).str.strip()
    out["source"] = out["source"].astype(str).str.strip()
    if out[["security_id", "ticker", "company_name", "source"]].eq("").any().any():
        raise ValueError(f"{label} contains empty identity metadata")
    for column in ("listed_from", "listed_to"):
        out[column] = pd.to_datetime(out[column], errors="coerce").dt.normalize()
    if out["listed_from"].isna().any():
        raise ValueError(f"{label} contains invalid listed_from")
    if (out["listed_to"].notna() & out["listed_to"].lt(out["listed_from"])).any():
        raise ValueError(f"{label} contains listed_to before listed_from")
    if out["security_id"].duplicated().any() or out["ticker"].duplicated().any():
        raise ValueError(f"{label} must have unique security_id and ticker")
    return out


def _overlap_count(frame: pd.DataFrame) -> int:
    count = 0
    for _, group in frame.groupby("ticker", sort=False):
        rows = group.sort_values("listed_from", kind="mergesort")
        previous_to: pd.Timestamp | None = None
        for listed_from, listed_to in zip(rows["listed_from"], rows["listed_to"], strict=True):
            if previous_to is not None and listed_from <= previous_to:
                count += 1
            if pd.isna(listed_to):
                previous_to = None
            elif previous_to is None or listed_to > previous_to:
                previous_to = listed_to
    return count


def derive_right_only_identity_overlay(
    frozen_master: pd.DataFrame,
    historical_master: pd.DataFrame,
) -> tuple[pd.DataFrame, IdentityOverlayDiagnostics]:
    """Derive all authoritative identities absent from the frozen master.

    The policy is intentionally generic: no ticker allow-list is accepted and
    no existing frozen ticker may be silently replaced or supplemented.
    """

    frozen = _normalize_master(frozen_master, label="frozen security master")
    historical = _normalize_master(historical_master, label="historical security master")
    frozen_ids = set(frozen["security_id"])
    missing = historical.loc[~historical["security_id"].isin(frozen_ids)].copy()
    overlap_tickers = sorted(set(missing["ticker"]) & set(frozen["ticker"]))
    if overlap_tickers:
        raise ValueError(
            "historical right-only overlay overlaps frozen ticker identities: "
            + ",".join(overlap_tickers)
        )
    duplicate_identity_rows = int(
        missing["security_id"].duplicated().sum() + missing["ticker"].duplicated().sum()
    )
    overlapping_identity_rows = _overlap_count(pd.concat([frozen, missing], ignore_index=True))
    if duplicate_identity_rows or overlapping_identity_rows:
        raise ValueError("authoritative identity overlay is duplicate or overlapping")
    missing = missing.sort_values(["ticker", "listed_from"], kind="mergesort").reset_index(drop=True)
    diagnostics = IdentityOverlayDiagnostics(
        frozen_rows=int(len(frozen)),
        historical_rows=int(len(historical)),
        overlay_rows=int(len(missing)),
        overlay_tickers=tuple(missing["ticker"].tolist()),
        duplicate_identity_rows=duplicate_identity_rows,
        overlapping_identity_rows=overlapping_identity_rows,
    )
    return missing.loc[:, IDENTITY_OVERLAY_COLUMNS], diagnostics


def merge_identity_overlay(
    frozen_master: pd.DataFrame,
    overlay: pd.DataFrame,
) -> pd.DataFrame:
    frozen = _normalize_master(frozen_master, label="frozen security master")
    added = _normalize_master(overlay, label="identity overlay")
    merged = pd.concat([frozen, added], ignore_index=True)
    _normalize_master(merged, label="merged security master")
    return merged.sort_values(["ticker", "listed_from"], kind="mergesort").reset_index(drop=True)


def _same_value(left: object, right: object, tolerance: float) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    if pd.isna(left) or pd.isna(right):
        return False
    if isinstance(left, (bool, np.bool_)) or isinstance(right, (bool, np.bool_)):
        return bool(left) == bool(right)
    if isinstance(left, (int, float, np.number)) and isinstance(right, (int, float, np.number)):
        return bool(np.isclose(float(left), float(right), rtol=0.0, atol=tolerance, equal_nan=True))
    return str(left) == str(right)


def compare_representation_tables(
    base: pd.DataFrame,
    counterfactual: pd.DataFrame,
    *,
    tolerance: float = 1e-12,
) -> RepresentationDiff:
    for label, frame in (("base", base), ("counterfactual", counterfactual)):
        missing = set(KEY_COLUMNS) - set(frame.columns)
        if missing:
            raise ValueError(f"{label} representation missing columns: {sorted(missing)}")
        if frame.duplicated(list(KEY_COLUMNS)).any():
            raise ValueError(f"{label} representation has duplicate ticker/date keys")
    base_key = pd.MultiIndex.from_frame(base.loc[:, KEY_COLUMNS])
    counter_key = pd.MultiIndex.from_frame(counterfactual.loc[:, KEY_COLUMNS])
    direct_keys = counter_key.difference(base_key)
    shared_keys = base_key.intersection(counter_key)
    base_indexed = base.set_index(list(KEY_COLUMNS))
    counter_indexed = counterfactual.set_index(list(KEY_COLUMNS))
    columns = tuple(
        column
        for column in REPRESENTATION_COLUMNS
        if column in base_indexed.columns and column in counter_indexed.columns
    )
    changed_keys: set[tuple[object, object]] = set()
    changed_by_column: dict[str, int] = {}
    for column in columns:
        changed = []
        for key in shared_keys:
            if not _same_value(base_indexed.at[key, column], counter_indexed.at[key, column], tolerance):
                changed.append(key)
                changed_keys.add(key)
        if changed:
            changed_by_column[column] = len(changed)

    def key_values(keys: Iterable[tuple[object, object]]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        pairs = sorted((str(key[0]), str(pd.Timestamp(key[1]).date())) for key in keys)
        return tuple(sorted({item[0] for item in pairs})), tuple(sorted({item[1] for item in pairs}))

    changed_tickers, changed_dates = key_values(changed_keys)
    direct_tickers, direct_dates = key_values(direct_keys)
    spillover_keys = {key for key in changed_keys if str(key[0]) != "FREN"}
    spill_tickers, spill_dates = key_values(spillover_keys)

    primary_changes: set[tuple[object, object]] = set()
    if "universe_primary_liquid" in base_indexed and "universe_primary_liquid" in counter_indexed:
        for key in shared_keys:
            if bool(base_indexed.at[key, "universe_primary_liquid"]) != bool(
                counter_indexed.at[key, "universe_primary_liquid"]
            ):
                primary_changes.add(key)
        for key in direct_keys:
            primary_changes.add(key)
    primary_tickers, primary_dates = key_values(primary_changes)
    return RepresentationDiff(
        shared_rows=len(shared_keys),
        changed_rows=len(changed_keys),
        changed_tickers=changed_tickers,
        changed_dates=changed_dates,
        changed_by_column=changed_by_column,
        direct_new_rows=len(direct_keys),
        direct_new_tickers=direct_tickers,
        direct_new_dates=direct_dates,
        spillover_changed_rows=len(spillover_keys),
        spillover_changed_tickers=spill_tickers,
        spillover_changed_dates=spill_dates,
        primary_membership_changes=len(primary_changes),
        primary_membership_changed_tickers=primary_tickers,
        primary_membership_changed_dates=primary_dates,
    )


def json_safe(value: object) -> object:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.date().isoformat()
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    return value
