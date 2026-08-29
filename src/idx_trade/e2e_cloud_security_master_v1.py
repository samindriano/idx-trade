"""Causal security-master bootstrap for ephemeral cloud E2E POST_EOD runners.

The accepted clean scorer deliberately keeps a frozen historical identity
baseline while allowing only genuinely post-freeze listing identities from the
mutable canonical runtime master. Local/Windows runtimes historically had
that runtime master on disk. A fresh GitHub runner does not, so cloud POST_EOD
must materialize the mutable identity reference explicitly before the existing
canonical EOD engine starts.

This module uses only official IDX identity/reference endpoints. It does not
read model targets, outcomes, paper state, or protected forward artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from math import isfinite
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import pandas as pd

from .forward_monitoring import runtime_paths
from .provenance import sha256_file, write_manifest_atomic
from .providers.idx import IDX_DELISTING_URL, IDX_STOCK_LIST_URL, _get_json, fetch_active_listings
from .security_master import SECURITY_COLUMNS, build_security_master, normalise_ticker
from .storage import write_csv_atomic


SCHEMA_VERSION = "idx_e2e_cloud_runtime_security_master_v1"
FREEZE_LOCAL_DATE = pd.Timestamp("2026-08-20")
JAKARTA = ZoneInfo("Asia/Jakarta")
DELISTING_PAGE_SIZE = 9999
MAX_DELISTING_PAGES_PER_MONTH = 1000
TICKER_PATTERN = r"[A-Z0-9]{4}"
BASELINE_CONTINUITY_SOURCE = "IDX_FROZEN_BASELINE_IDENTITY_CONTINUITY"


class CloudSecurityMasterError(RuntimeError):
    pass


def _integer_metadata(payload: Mapping[str, object], name: str, *, label: str) -> int | None:
    value = payload.get(name)
    if value is None:
        return None
    if isinstance(value, bool):
        raise CloudSecurityMasterError(f"{label}_{name}_NOT_INTEGER")
    try:
        numeric = float(value)
        parsed = int(numeric)
    except (TypeError, ValueError, OverflowError) as error:
        raise CloudSecurityMasterError(f"{label}_{name}_NOT_INTEGER") from error
    if not isfinite(numeric) or numeric != parsed or parsed < 0:
        raise CloudSecurityMasterError(f"{label}_{name}_NOT_NONNEGATIVE_INTEGER")
    return parsed


def _required_integer_metadata(payload: Mapping[str, object], name: str, *, label: str) -> int:
    value = _integer_metadata(payload, name, label=label)
    if value is None:
        raise CloudSecurityMasterError(f"{label}_{name}_MISSING")
    return value


def _validate_complete_active_payload(payload: Mapping[str, object]) -> int:
    label = "IDX_ACTIVE_LISTINGS"
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise CloudSecurityMasterError(f"{label}_DATA_NOT_LIST")
    records_total = _required_integer_metadata(payload, "recordsTotal", label=label)
    records_filtered = _integer_metadata(payload, "recordsFiltered", label=label)
    if records_filtered is not None and records_filtered > records_total:
        raise CloudSecurityMasterError(f"{label}_RECORDS_FILTERED_EXCEEDS_TOTAL")
    if records_filtered is not None and records_filtered != records_total:
        raise CloudSecurityMasterError(f"{label}_UNEXPECTED_FILTERED_RESPONSE")
    if records_total == 0:
        raise CloudSecurityMasterError(f"{label}_EMPTY_RESPONSE")
    if len(rows) != records_total:
        raise CloudSecurityMasterError(
            f"{label}_PARTIAL_RESPONSE:rows={len(rows)} recordsTotal={records_total}"
        )
    return records_total


def fetch_complete_active_listings() -> pd.DataFrame:
    """Fetch current IDX listings and require full-page count proof."""

    params = {
        "start": 0,
        "length": 9999,
        "code": "",
        "sector": "",
        "board": "",
        "language": "en-us",
    }
    payload = _get_json(IDX_STOCK_LIST_URL, params)
    if not isinstance(payload, Mapping):
        raise CloudSecurityMasterError("IDX_ACTIVE_LISTINGS_PAYLOAD_NOT_OBJECT")
    expected = _validate_complete_active_payload(payload)
    frame = fetch_active_listings(get_json=lambda _url, _params: dict(payload))
    if len(frame) != expected:
        raise CloudSecurityMasterError(
            f"IDX_ACTIVE_LISTINGS_NORMALIZATION_DROPPED_ROWS:{len(frame)}!={expected}"
        )
    if frame["ticker"].duplicated().any():
        raise CloudSecurityMasterError("IDX_ACTIVE_LISTINGS_DUPLICATE_TICKER")
    return frame


def _validate_delisting_row(row: object, *, label: str, position: int) -> dict[str, object]:
    required = {"code", "issuerName", "ListingDate", "DeListingDate"}
    if not isinstance(row, Mapping) or not required.issubset(row.keys()):
        raise CloudSecurityMasterError(f"{label}_ROW_SCHEMA_INVALID:{position}")
    ticker = normalise_ticker(row.get("code"))
    listed_from = pd.to_datetime(row.get("ListingDate"), errors="coerce")
    listed_to = pd.to_datetime(row.get("DeListingDate"), errors="coerce")
    if (
        not ticker
        or not pd.Series([ticker]).str.fullmatch(r"[A-Z0-9]{4}", na=False).iloc[0]
        or pd.isna(listed_from)
        or pd.isna(listed_to)
    ):
        raise CloudSecurityMasterError(f"{label}_ROW_IDENTITY_INVALID:{position}")
    return dict(row)


def _fetch_complete_delisting_month(year: int, month: int) -> list[dict[str, object]]:
    """Exhaust one official monthly delisting result using ``meta.totalItems``."""

    label = f"IDX_DELISTINGS_{year:04d}_{month:02d}"
    accumulated: list[dict[str, object]] = []
    expected_total: int | None = None
    page_number = 1

    while True:
        if page_number > MAX_DELISTING_PAGES_PER_MONTH:
            raise CloudSecurityMasterError(f"{label}_MAX_PAGE_GUARD_EXCEEDED")
        params = {
            "urlName": "LINK_DELISTING",
            "periodYear": year,
            "periodMonth": month,
            "periodType": "monthly",
            "isPrint": "False",
            "cumulative": "false",
            "pageSize": DELISTING_PAGE_SIZE,
            "pageNumber": page_number,
            "orderBy": "",
        }
        payload = _get_json(IDX_DELISTING_URL, params)
        if not isinstance(payload, Mapping):
            raise CloudSecurityMasterError(f"{label}_PAYLOAD_NOT_OBJECT")
        rows = payload.get("data")
        meta = payload.get("meta")
        if not isinstance(rows, list):
            raise CloudSecurityMasterError(f"{label}_DATA_NOT_LIST")
        if not isinstance(meta, Mapping):
            raise CloudSecurityMasterError(f"{label}_META_NOT_OBJECT")

        meta_page = _required_integer_metadata(meta, "pageNumber", label=label)
        meta_page_size = _required_integer_metadata(meta, "pageSize", label=label)
        total_items = _required_integer_metadata(meta, "totalItems", label=label)
        if meta_page != page_number:
            raise CloudSecurityMasterError(
                f"{label}_PAGE_NUMBER_MISMATCH:requested={page_number} returned={meta_page}"
            )
        if meta_page_size != DELISTING_PAGE_SIZE:
            raise CloudSecurityMasterError(
                f"{label}_PAGE_SIZE_MISMATCH:requested={DELISTING_PAGE_SIZE} returned={meta_page_size}"
            )
        if expected_total is None:
            expected_total = total_items
        elif total_items != expected_total:
            raise CloudSecurityMasterError(
                f"{label}_TOTAL_ITEMS_CHANGED:{expected_total}->{total_items}"
            )

        if expected_total == 0:
            if rows:
                raise CloudSecurityMasterError(f"{label}_ZERO_TOTAL_WITH_NONEMPTY_DATA")
            return []
        if not rows:
            raise CloudSecurityMasterError(
                f"{label}_EMPTY_PAGE_BEFORE_TOTAL:accumulated={len(accumulated)} total={expected_total}"
            )
        if len(rows) > DELISTING_PAGE_SIZE:
            raise CloudSecurityMasterError(f"{label}_PAGE_EXCEEDS_REQUESTED_SIZE")

        offset = len(accumulated)
        accumulated.extend(
            _validate_delisting_row(row, label=label, position=offset + index)
            for index, row in enumerate(rows)
        )
        if len(accumulated) > expected_total:
            raise CloudSecurityMasterError(
                f"{label}_ACCUMULATED_EXCEEDS_TOTAL:{len(accumulated)}>{expected_total}"
            )
        if len(accumulated) == expected_total:
            return accumulated
        page_number += 1


def fetch_complete_delisted_listings(start_year: int, *, end: date) -> pd.DataFrame:
    """Fetch post-freeze monthly IDX delisting history with exhaustive pagination."""

    if end < FREEZE_LOCAL_DATE.date():
        return pd.DataFrame(
            columns=["ticker", "company_name", "listed_from", "listed_to", "source"]
        )
    effective_start_year = max(int(start_year), FREEZE_LOCAL_DATE.year)
    records: list[dict[str, object]] = []
    for year in range(effective_start_year, end.year + 1):
        first_month = FREEZE_LOCAL_DATE.month if year == FREEZE_LOCAL_DATE.year else 1
        last_month = end.month if year == end.year else 12
        if first_month > last_month:
            continue
        for month in range(first_month, last_month + 1):
            records.extend(_fetch_complete_delisting_month(year, month))

    if not records:
        return pd.DataFrame(
            columns=["ticker", "company_name", "listed_from", "listed_to", "source"]
        )
    rows = pd.DataFrame(records)
    result = pd.DataFrame(
        {
            "ticker": rows["code"].map(normalise_ticker),
            "company_name": rows["issuerName"].astype(str).str.strip(),
            "listed_from": pd.to_datetime(rows["ListingDate"], errors="coerce").dt.normalize(),
            "listed_to": pd.to_datetime(rows["DeListingDate"], errors="coerce").dt.normalize(),
            "source": "IDX_DIGITAL_STATISTIC_DELISTING",
        }
    )
    duplicate_events = result.duplicated(["ticker", "listed_from", "listed_to"], keep=False)
    if duplicate_events.any():
        raise CloudSecurityMasterError("IDX_DELISTINGS_DUPLICATE_EVENT_ACROSS_MONTHS")
    return result.sort_values(["listed_to", "ticker"], kind="mergesort").reset_index(drop=True)


def _normalize_identity(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise CloudSecurityMasterError(f"{label}_NOT_DATAFRAME")
    required = {"ticker", "listed_from", "listed_to"}
    missing = required - set(frame.columns)
    if missing:
        raise CloudSecurityMasterError(f"{label}_MISSING_COLUMNS:{sorted(missing)}")
    data = frame.copy()
    raw_ticker = data["ticker"]
    if raw_ticker.isna().any() or (~raw_ticker.map(lambda value: isinstance(value, str))).any():
        raise CloudSecurityMasterError(f"{label}_INVALID_IDENTITY")
    data["ticker"] = raw_ticker.map(normalise_ticker)
    data["listed_from"] = pd.to_datetime(data["listed_from"], errors="coerce").dt.normalize()
    raw_listed_to = data["listed_to"]
    data["listed_to"] = pd.to_datetime(raw_listed_to, errors="coerce").dt.normalize()
    invalid_ticker = data["ticker"].eq("") | ~data["ticker"].str.fullmatch(
        TICKER_PATTERN, na=False
    )
    if invalid_ticker.any() or data["listed_from"].isna().any():
        raise CloudSecurityMasterError(f"{label}_INVALID_IDENTITY")
    nonempty_listed_to = (
        raw_listed_to.notna()
        & raw_listed_to.astype("string").fillna("").str.strip().ne("")
    )
    if (nonempty_listed_to & data["listed_to"].isna()).any():
        raise CloudSecurityMasterError(f"{label}_INVALID_LISTED_TO")
    invalid_intervals = data["listed_to"].notna() & data["listed_to"].lt(data["listed_from"])
    if invalid_intervals.any():
        raise CloudSecurityMasterError(f"{label}_INVALID_LISTING_INTERVAL")
    if data["ticker"].duplicated().any():
        duplicates = sorted(
            data.loc[data["ticker"].duplicated(keep=False), "ticker"].unique()
        )[:10]
        raise CloudSecurityMasterError(f"{label}_DUPLICATE_TICKER:{duplicates}")
    return data.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def refresh_cloud_runtime_security_master(
    runtime_root: str | Path,
    *,
    baseline_master: str | Path,
    observed_at: datetime,
    active_fetcher: Callable[[], pd.DataFrame] = fetch_complete_active_listings,
    delisted_fetcher: Callable[..., pd.DataFrame] = fetch_complete_delisted_listings,
) -> dict[str, object]:
    """Refresh the mutable runtime listing reference from official IDX data.

    The frozen clean baseline is never rewritten. It is used as an identity
    continuity anchor: every security that was live at the model freeze and
    remains legally live at observation must be represented by either the
    current active listing response, the post-freeze delisting history, or its
    unchanged baseline identity. Absence from a current-active snapshot alone
    is not evidence of delisting because a legally listed security may be
    suspended. Any identity absent from the baseline is admissible only when
    its official ``listed_from`` is strictly after the freeze date, matching
    the clean scorer's preregistered future-IPO rule.
    """

    if observed_at.tzinfo is None:
        raise CloudSecurityMasterError("RUNTIME_SECURITY_MASTER_CLOCK_NOT_TIMEZONE_AWARE")
    local_observed = observed_at.astimezone(JAKARTA)
    observed_date = pd.Timestamp(local_observed.date()).normalize()
    if observed_date < FREEZE_LOCAL_DATE:
        raise CloudSecurityMasterError("RUNTIME_SECURITY_MASTER_OBSERVED_BEFORE_FREEZE")

    baseline_path = Path(baseline_master).expanduser().resolve()
    if not baseline_path.is_file():
        raise CloudSecurityMasterError(
            f"RUNTIME_SECURITY_MASTER_BASELINE_MISSING:{baseline_path}"
        )
    baseline = _normalize_identity(
        pd.read_csv(baseline_path),
        label="RUNTIME_SECURITY_MASTER_BASELINE",
    )

    active = _normalize_identity(active_fetcher(), label="RUNTIME_SECURITY_MASTER_ACTIVE")
    delisted = _normalize_identity(
        delisted_fetcher(FREEZE_LOCAL_DATE.year, end=local_observed.date()),
        label="RUNTIME_SECURITY_MASTER_DELISTED",
    )
    current_full = build_security_master(active, delisted).loc[:, list(SECURITY_COLUMNS)]
    current = _normalize_identity(
        current_full,
        label="RUNTIME_SECURITY_MASTER_CURRENT",
    )

    if current["listed_from"].gt(observed_date).any():
        raise CloudSecurityMasterError(
            "RUNTIME_SECURITY_MASTER_CURRENT_LISTING_AFTER_OBSERVED_DATE"
        )
    if current["listed_to"].gt(observed_date).any():
        raise CloudSecurityMasterError(
            "RUNTIME_SECURITY_MASTER_CURRENT_DELISTING_AFTER_OBSERVED_DATE"
        )

    baseline_live_at_observed = baseline[
        baseline["listed_from"].le(FREEZE_LOCAL_DATE)
        & (baseline["listed_to"].isna() | baseline["listed_to"].ge(observed_date))
    ]
    current_tickers = set(current["ticker"])
    baseline_tickers = set(baseline["ticker"])

    common = baseline[baseline["ticker"].isin(current_tickers)].merge(
        current.loc[:, ["ticker", "listed_from"]],
        on="ticker",
        how="inner",
        suffixes=("_baseline", "_current"),
    )
    conflicting_identity = common[
        common["listed_from_baseline"] != common["listed_from_current"]
    ]
    if not conflicting_identity.empty:
        raise CloudSecurityMasterError(
            "RUNTIME_SECURITY_MASTER_BASELINE_IDENTITY_CONFLICT:"
            + ",".join(sorted(conflicting_identity["ticker"].tolist())[:20])
        )

    missing_live = sorted(set(baseline_live_at_observed["ticker"]) - current_tickers)
    preserved_baseline = baseline[baseline["ticker"].isin(missing_live)].copy()
    if not preserved_baseline.empty:
        if "company_name" not in preserved_baseline.columns:
            preserved_baseline["company_name"] = preserved_baseline["ticker"]
        else:
            preserved_baseline["company_name"] = preserved_baseline["company_name"].fillna(
                preserved_baseline["ticker"]
            )
        preserved_baseline["security_id"] = (
            "IDX:"
            + preserved_baseline["ticker"]
            + ":"
            + preserved_baseline["listed_from"].dt.strftime("%Y%m%d")
        )
        preserved_baseline["source"] = BASELINE_CONTINUITY_SOURCE
        preserved_baseline = preserved_baseline.loc[:, list(SECURITY_COLUMNS)]
        current_full = pd.concat([current_full, preserved_baseline], ignore_index=True)
        current = _normalize_identity(
            current_full,
            label="RUNTIME_SECURITY_MASTER_CURRENT_WITH_BASELINE_CONTINUITY",
        )
        current_full = current.loc[:, list(SECURITY_COLUMNS)]

    additions = current.loc[~current["ticker"].isin(baseline_tickers)].copy()
    invalid_additions = additions[additions["listed_from"].le(FREEZE_LOCAL_DATE)]
    if not invalid_additions.empty:
        sample = invalid_additions.loc[:, ["ticker", "listed_from"]].copy()
        sample["listed_from"] = sample["listed_from"].dt.strftime("%Y-%m-%d")
        raise CloudSecurityMasterError(
            "RUNTIME_SECURITY_MASTER_PRE_FREEZE_EXTRA_IDENTITY:"
            + sample.head(20).to_json(orient="records")
        )

    output = runtime_paths(runtime_root).listings_root / "security_master.csv"
    write_csv_atomic(current_full, output)
    artifact_sha = sha256_file(output)

    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "authority": "IDX",
        "semantics": "CURRENT_ACTIVE_REFERENCE_PLUS_FROZEN_BASELINE_IDENTITY_CONTINUITY_AND_POST_FREEZE_DELISTING_HISTORY",
        "observed_at_jakarta": local_observed.isoformat(),
        "observed_date": observed_date.date().isoformat(),
        "freeze_local_date": FREEZE_LOCAL_DATE.date().isoformat(),
        "baseline_path": str(baseline_path),
        "baseline_sha256": sha256_file(baseline_path),
        "active_source": IDX_STOCK_LIST_URL,
        "active_completeness": "RECORDS_TOTAL_EXACT_SINGLE_RESPONSE",
        "delisting_source": IDX_DELISTING_URL,
        "delisting_start_year": int(FREEZE_LOCAL_DATE.year),
        "delisting_start_month": int(FREEZE_LOCAL_DATE.month),
        "delisting_completeness": "MONTHLY_META_TOTAL_ITEMS_EXHAUSTIVE_PAGINATION",
        "active_rows": int(len(active)),
        "delisted_rows": int(len(delisted)),
        "runtime_rows": int(len(current_full)),
        "baseline_identities_preserved_not_in_current_active": missing_live,
        "baseline_identities_preserved_count": int(len(missing_live)),
        "post_freeze_new_tickers": sorted(additions["ticker"].astype(str).tolist()),
        "security_master_path": str(output.resolve()),
        "security_master_sha256": artifact_sha,
        "guards": {
            "outcome_accessed": False,
            "protected_forward_accessed": False,
            "model_refit": False,
            "paper_state_mutated": False,
            "retroactive_capture_authorized": False,
        },
    }
    manifest_path = output.with_name("security_master_refresh_manifest.json")
    write_manifest_atomic(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path.resolve())
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest
