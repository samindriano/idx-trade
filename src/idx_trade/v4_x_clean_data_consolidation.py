"""Outcome-blind helpers for V4-X clean-data consolidation Stage A.

This module has one narrow purpose: apply already accepted H/L/C and Open
price-basis overlays to an immutable parent panel while proving that all other
parent fields and row identities remain unchanged. It does not decide listing
or universe membership, fit/score models, or access targets/outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

IDENTITY = ("ticker", "date")
HLC = ("high", "low", "close")
MUTABLE_FIELDS = frozenset({"high", "low", "close", "open"})
HLC_SOURCE = "IDX_PUBLIC_STOCK_SUMMARY_CERTIFIED_PRICE_BASIS_OVERLAY"
OPEN_PARENT_SOURCE = "PARENT_UNCHANGED_OPEN_PROVENANCE_UNSPECIFIED"
VOLUME_SOURCE = "PARENT_UNCHANGED_OFFICIAL_IDX_PARITY_CERTIFIED"
VALUE_SOURCE = "PARENT_UNCHANGED_OFFICIAL_IDX_PARITY_CERTIFIED"
FAIL_CLOSED_SOURCE = "FAIL_CLOSED_UNAVAILABLE"
CONSOLIDATION_POLICY = "FROZEN_PARENT_PLUS_ACCEPTED_HLC_OPEN_OVERLAYS_NO_UNIVERSE_MUTATION_V1"


@dataclass(frozen=True)
class ConsolidationResult:
    panel: pd.DataFrame
    provenance: pd.DataFrame
    correction_ledger: pd.DataFrame
    summary: dict[str, Any]


def normalize_ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def normalize_date(series: pd.Series, label: str) -> pd.Series:
    out = pd.to_datetime(series, errors="coerce", utc=False)
    try:
        out = out.dt.tz_localize(None)
    except TypeError:
        # Already timezone-naive.
        pass
    out = out.dt.normalize()
    if out.isna().any():
        raise ValueError(f"{label} contains invalid dates")
    return out


def _identity_frame(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    missing = set(IDENTITY) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing identity columns: {sorted(missing)}")
    keys = pd.DataFrame(
        {
            "_ticker_key": normalize_ticker(frame["ticker"]),
            "_date_key": normalize_date(frame["date"], f"{label} date"),
        },
        index=frame.index,
    )
    if keys["_ticker_key"].eq("").any():
        raise ValueError(f"{label} contains empty ticker identity")
    if keys.duplicated(["_ticker_key", "_date_key"]).any():
        raise ValueError(f"{label} contains duplicate ticker-date identity")
    return keys


def _numeric_required(series: pd.Series, label: str, *, positive: bool = True) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce").astype(float)
    valid = np.isfinite(out.to_numpy(dtype=float))
    if positive:
        valid &= out.to_numpy(dtype=float) > 0.0
    if not bool(np.all(valid)):
        raise ValueError(f"{label} contains invalid numeric values")
    return out


def _positions_for_overlay(
    parent_keys: pd.DataFrame,
    overlay: pd.DataFrame,
    label: str,
) -> tuple[pd.DataFrame, np.ndarray]:
    overlay_keys = _identity_frame(overlay, label).reset_index(drop=True)
    lookup = parent_keys.reset_index(drop=True).copy()
    lookup["_row_pos"] = np.arange(len(lookup), dtype=np.int64)
    joined = overlay_keys.merge(
        lookup,
        on=["_ticker_key", "_date_key"],
        how="left",
        validate="one_to_one",
    )
    if joined["_row_pos"].isna().any():
        raise ValueError(f"{label} contains identities absent from frozen parent")
    return overlay_keys, joined["_row_pos"].astype(np.int64).to_numpy()


def _equal_with_nan(left: pd.Series, right: pd.Series) -> bool:
    if left.dtype == right.dtype:
        return left.equals(right)
    # Some parquet/assignment paths can retain numerically equivalent values
    # with a wider numeric dtype. For immutable numeric columns, compare exact
    # values with NaN equality rather than accepting tolerance-based drift.
    if pd.api.types.is_numeric_dtype(left.dtype) and pd.api.types.is_numeric_dtype(right.dtype):
        a = pd.to_numeric(left, errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(right, errors="coerce").to_numpy(dtype=float)
        return bool(np.array_equal(a, b, equal_nan=True))
    return left.astype(object).where(left.notna(), None).equals(
        right.astype(object).where(right.notna(), None)
    )


def assert_immutable_parent_fields(parent: pd.DataFrame, corrected: pd.DataFrame) -> None:
    if list(parent.columns) != list(corrected.columns):
        raise ValueError("consolidated panel column identity changed")
    if len(parent) != len(corrected):
        raise ValueError("consolidated panel row count changed")
    for column in parent.columns:
        if column in MUTABLE_FIELDS:
            continue
        if not _equal_with_nan(parent[column], corrected[column]):
            raise ValueError(f"immutable parent field changed: {column}")


def _validate_expected_counts(
    parent: pd.DataFrame,
    hlc_overlay: pd.DataFrame,
    open_overlay: pd.DataFrame,
    open_fail_closed: pd.DataFrame,
    expected: dict[str, int] | None,
) -> None:
    if not expected:
        return
    checks = {
        "parent_rows": len(parent),
        "parent_tickers": int(normalize_ticker(parent["ticker"]).nunique()),
        "hlc_overlay_rows": len(hlc_overlay),
        "hlc_overlay_tickers": int(normalize_ticker(hlc_overlay["ticker"]).nunique()),
        "open_overlay_rows": len(open_overlay),
        "open_fail_closed_rows": len(open_fail_closed),
    }
    if "open_remediation_source" in open_overlay.columns:
        source = open_overlay["open_remediation_source"].astype(str)
        checks["open_official_primary_rows"] = int(source.eq("IDX_OFFICIAL_OPENPRICE").sum())
        checks["open_factor_fallback_rows"] = int(source.eq("CA_FACTOR_RECONSTRUCTION").sum())
    for key, wanted in expected.items():
        if key in checks and int(checks[key]) != int(wanted):
            raise ValueError(f"expected population changed: {key}={checks[key]} != {wanted}")


def consolidate_stage_a(
    parent: pd.DataFrame,
    hlc_overlay: pd.DataFrame,
    open_overlay: pd.DataFrame,
    open_fail_closed: pd.DataFrame,
    *,
    expected: dict[str, int] | None = None,
) -> ConsolidationResult:
    """Apply accepted Stage-A corrections with exact identity/parity guards."""

    required_parent = {
        "ticker",
        "date",
        "high",
        "low",
        "close",
        "open",
        "volume",
        "regular_market_value",
        "price_provenance",
    }
    missing = required_parent - set(parent.columns)
    if missing:
        raise ValueError(f"parent panel missing columns: {sorted(missing)}")

    required_hlc = {"ticker", "date", "remediated_high", "remediated_low", "remediated_close"}
    missing = required_hlc - set(hlc_overlay.columns)
    if missing:
        raise ValueError(f"HLC overlay missing columns: {sorted(missing)}")

    required_open = {
        "ticker",
        "date",
        "remediated_open",
        "open_remediation_source",
        "open_remediation_policy",
    }
    missing = required_open - set(open_overlay.columns)
    if missing:
        raise ValueError(f"Open overlay missing columns: {sorted(missing)}")

    required_fail = {"ticker", "date", "open_remediation_source", "open_remediation_policy"}
    missing = required_fail - set(open_fail_closed.columns)
    if missing:
        raise ValueError(f"Open fail-closed rows missing columns: {sorted(missing)}")

    parent_keys = _identity_frame(parent, "frozen parent").reset_index(drop=True)
    hlc_keys, hlc_pos = _positions_for_overlay(parent_keys, hlc_overlay, "HLC overlay")
    open_keys, open_pos = _positions_for_overlay(parent_keys, open_overlay, "Open overlay")
    fail_keys, fail_pos = _positions_for_overlay(parent_keys, open_fail_closed, "Open fail-closed")

    if len(set(open_pos.tolist()).intersection(set(fail_pos.tolist()))) != 0:
        raise ValueError("Open admitted and fail-closed identities overlap")

    # Both Open outputs must partition exactly the already accepted HLC
    # candidate population; otherwise cross-lane lineage has drifted.
    hlc_key_set = set(map(tuple, hlc_keys[["_ticker_key", "_date_key"]].to_numpy()))
    open_all = pd.concat([open_keys, fail_keys], ignore_index=True)
    open_key_set = set(map(tuple, open_all[["_ticker_key", "_date_key"]].to_numpy()))
    if hlc_key_set != open_key_set:
        raise ValueError("HLC and Open remediation candidate identities disagree")

    _validate_expected_counts(parent, hlc_overlay, open_overlay, open_fail_closed, expected)

    corrected = parent.copy(deep=True)

    # Apply H/L/C exact accepted values.
    rem_high = _numeric_required(hlc_overlay["remediated_high"], "remediated_high")
    rem_low = _numeric_required(hlc_overlay["remediated_low"], "remediated_low")
    rem_close = _numeric_required(hlc_overlay["remediated_close"], "remediated_close")
    if not bool((rem_high >= rem_low).all() and (rem_close >= rem_low).all() and (rem_close <= rem_high).all()):
        raise ValueError("HLC overlay violates low <= close <= high")
    for column, values in (
        ("high", rem_high),
        ("low", rem_low),
        ("close", rem_close),
    ):
        corrected.iloc[hlc_pos, corrected.columns.get_loc(column)] = values.to_numpy(dtype=float)

    # Apply admitted Open values and explicitly fail-close the two unsupported
    # candidate identities, regardless of any finite parent Open that existed.
    rem_open = _numeric_required(open_overlay["remediated_open"], "remediated_open")
    allowed_sources = {"IDX_OFFICIAL_OPENPRICE", "CA_FACTOR_RECONSTRUCTION"}
    actual_sources = set(open_overlay["open_remediation_source"].astype(str).unique())
    if not actual_sources.issubset(allowed_sources):
        raise ValueError(f"unexpected admitted Open sources: {sorted(actual_sources)}")
    if not open_fail_closed["open_remediation_source"].astype(str).eq(FAIL_CLOSED_SOURCE).all():
        raise ValueError("fail-closed Open source changed")
    corrected.iloc[open_pos, corrected.columns.get_loc("open")] = rem_open.to_numpy(dtype=float)
    corrected.iloc[fail_pos, corrected.columns.get_loc("open")] = np.nan

    post_low = pd.to_numeric(corrected.iloc[open_pos]["low"], errors="coerce").to_numpy(dtype=float)
    post_high = pd.to_numeric(corrected.iloc[open_pos]["high"], errors="coerce").to_numpy(dtype=float)
    post_open = pd.to_numeric(corrected.iloc[open_pos]["open"], errors="coerce").to_numpy(dtype=float)
    within = (
        np.isfinite(post_low)
        & np.isfinite(post_high)
        & np.isfinite(post_open)
        & (post_low > 0.0)
        & (post_high >= post_low)
        & (post_open >= post_low)
        & (post_open <= post_high)
    )
    if not bool(np.all(within)):
        raise ValueError("admitted Open falls outside post-HLC envelope")
    if corrected.iloc[fail_pos]["open"].notna().any():
        raise ValueError("fail-closed Open candidate remains finite")

    assert_immutable_parent_fields(parent, corrected)
    # Explicitly call out the two fields whose full-panel parity was separately
    # certified; no tolerant comparison is allowed here.
    for column in ("volume", "regular_market_value"):
        if not _equal_with_nan(parent[column], corrected[column]):
            raise ValueError(f"certified immutable field changed: {column}")

    n = len(parent)
    parent_price_source = "PARENT:" + parent["price_provenance"].astype(str)
    high_source = parent_price_source.to_numpy(dtype=object, copy=True)
    low_source = parent_price_source.to_numpy(dtype=object, copy=True)
    close_source = parent_price_source.to_numpy(dtype=object, copy=True)
    open_source = np.full(n, OPEN_PARENT_SOURCE, dtype=object)
    hlc_repaired = np.zeros(n, dtype=bool)
    open_repaired = np.zeros(n, dtype=bool)
    open_fail = np.zeros(n, dtype=bool)

    for target in (high_source, low_source, close_source):
        target[hlc_pos] = HLC_SOURCE
    hlc_repaired[hlc_pos] = True
    open_source[open_pos] = open_overlay["open_remediation_source"].astype(str).to_numpy()
    open_source[fail_pos] = FAIL_CLOSED_SOURCE
    open_repaired[open_pos] = True
    open_fail[fail_pos] = True

    provenance = pd.DataFrame(
        {
            "ticker": parent["ticker"].to_numpy(copy=True),
            "date": parent["date"].to_numpy(copy=True),
            "high_source": high_source,
            "low_source": low_source,
            "close_source": close_source,
            "open_source": open_source,
            "volume_source": np.full(n, VOLUME_SOURCE, dtype=object),
            "regular_market_value_source": np.full(n, VALUE_SOURCE, dtype=object),
            "hlc_repaired": hlc_repaired,
            "open_repaired": open_repaired,
            "open_fail_closed_candidate": open_fail,
            "consolidation_policy": np.full(n, CONSOLIDATION_POLICY, dtype=object),
        }
    )

    # Correction ledger is intentionally small: one row for each accepted HLC
    # candidate identity, with Open admitted/fail-closed status attached.
    ledger_pos = hlc_pos
    pos_to_open_source = dict(zip(open_pos.tolist(), open_overlay["open_remediation_source"].astype(str)))
    fail_set = set(fail_pos.tolist())
    ledger = pd.DataFrame(
        {
            "ticker": parent.iloc[ledger_pos]["ticker"].to_numpy(copy=True),
            "date": parent.iloc[ledger_pos]["date"].to_numpy(copy=True),
            "original_high": pd.to_numeric(parent.iloc[ledger_pos]["high"], errors="coerce").to_numpy(),
            "clean_high": pd.to_numeric(corrected.iloc[ledger_pos]["high"], errors="coerce").to_numpy(),
            "original_low": pd.to_numeric(parent.iloc[ledger_pos]["low"], errors="coerce").to_numpy(),
            "clean_low": pd.to_numeric(corrected.iloc[ledger_pos]["low"], errors="coerce").to_numpy(),
            "original_close": pd.to_numeric(parent.iloc[ledger_pos]["close"], errors="coerce").to_numpy(),
            "clean_close": pd.to_numeric(corrected.iloc[ledger_pos]["close"], errors="coerce").to_numpy(),
            "original_open": pd.to_numeric(parent.iloc[ledger_pos]["open"], errors="coerce").to_numpy(),
            "clean_open": pd.to_numeric(corrected.iloc[ledger_pos]["open"], errors="coerce").to_numpy(),
            "hlc_source": np.full(len(ledger_pos), HLC_SOURCE, dtype=object),
            "open_source": [
                FAIL_CLOSED_SOURCE if int(pos) in fail_set else pos_to_open_source[int(pos)]
                for pos in ledger_pos
            ],
            "open_fail_closed": [int(pos) in fail_set for pos in ledger_pos],
        }
    )
    ledger = ledger.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)

    summary = {
        "status": "STAGE_A_CONSOLIDATION_MATERIALIZED_WAITING_FOR_IDENTITY_ADJUDICATION",
        "policy": CONSOLIDATION_POLICY,
        "parent_rows": int(len(parent)),
        "parent_tickers": int(normalize_ticker(parent["ticker"]).nunique()),
        "output_rows": int(len(corrected)),
        "output_tickers": int(normalize_ticker(corrected["ticker"]).nunique()),
        "hlc_repair_rows": int(len(hlc_overlay)),
        "hlc_repair_tickers": int(normalize_ticker(hlc_overlay["ticker"]).nunique()),
        "open_repair_rows": int(len(open_overlay)),
        "open_fail_closed_rows": int(len(open_fail_closed)),
        "open_official_primary_rows": int(open_overlay["open_remediation_source"].astype(str).eq("IDX_OFFICIAL_OPENPRICE").sum()),
        "open_factor_fallback_rows": int(open_overlay["open_remediation_source"].astype(str).eq("CA_FACTOR_RECONSTRUCTION").sum()),
        "identity_preserved": True,
        "volume_preserved": True,
        "regular_market_value_preserved": True,
        "other_parent_fields_preserved": True,
        "universe_repair_performed": False,
        "next": "WAIT_FOR_INDEPENDENT_PIT_IDENTITY_LISTING_DOMAIN_ADJUDICATION_BEFORE_FINAL_CLEAN_UNIVERSE_MANIFEST",
    }
    return ConsolidationResult(corrected, provenance, ledger, summary)
