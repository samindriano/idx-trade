from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from idx_trade.stockbit_identity_refresh import IdentityRefreshError, reconstruct_active_roster

BASE_URL = "https://api.zpi.web.id/v1"
TIMEOUT = 30
PAGE_SIZE = 500
MAX_MONTH_PAGES = 100
IDENTITY_CSV = Path("config/stockbit_stream_universe_v1.csv")
IDENTITY_MANIFEST = Path("config/stockbit_stream_universe_v1.json")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def unwrap(value: Any) -> Any:
    if isinstance(value, dict) and "project" in value and "timestamp" in value and isinstance(value.get("data"), dict):
        return value["data"]
    return value


def request_json(api_key: str, path: str, params: dict[str, Any]) -> tuple[dict[str, Any], str]:
    response = requests.get(
        f"{BASE_URL}/{path}",
        params=params,
        headers={"x-api-key": api_key},
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        raise IdentityRefreshError(f"{path} {params} HTTP {response.status_code}: {response.text[:160]}")
    raw_sha = sha256_bytes(bytes(response.content))
    payload = unwrap(response.json())
    if not isinstance(payload, dict):
        raise IdentityRefreshError(f"{path} payload is not object")
    return payload, raw_sha


def fetch_offset_dataset(api_key: str, endpoint: str, dataset: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    start = 0
    expected_total: int | None = None
    while True:
        payload, raw_sha = request_json(api_key, f"finance:idx/{endpoint}", {"length": PAGE_SIZE, "start": start})
        if payload.get("provider") != "idx" or payload.get("dataset") != dataset:
            raise IdentityRefreshError(f"{endpoint} provider/dataset mismatch")
        data = payload.get("data")
        if not isinstance(data, list):
            raise IdentityRefreshError(f"{endpoint} data is not list")
        try:
            total = int(payload.get("recordsTotal"))
            filtered = int(payload.get("recordsFiltered", total))
        except Exception as exc:
            raise IdentityRefreshError(f"{endpoint} invalid total metadata") from exc
        if total != filtered:
            raise IdentityRefreshError(f"{endpoint} filtered result is not full identity set")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise IdentityRefreshError(f"{endpoint} total changed during pagination")
        provenance.append({"start": start, "returned": len(data), "raw_sha256": raw_sha})
        for row in data:
            if not isinstance(row, dict):
                raise IdentityRefreshError(f"{endpoint} non-object row")
            rows.append(row)
        start += len(data)
        if start >= total:
            break
        if not data:
            raise IdentityRefreshError(f"{endpoint} pagination stalled")
    if expected_total is None or len(rows) != expected_total:
        raise IdentityRefreshError(f"{endpoint} incomplete pagination")
    return rows, provenance


def month_range(start: date, end: date) -> list[tuple[int, int]]:
    cursor = date(start.year, start.month, 1)
    final = date(end.year, end.month, 1)
    result: list[tuple[int, int]] = []
    while cursor <= final:
        result.append((cursor.year, cursor.month))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return result


def fetch_month_dataset(
    api_key: str,
    endpoint: str,
    dataset: str,
    year: int,
    month: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pages: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    page = 1
    while True:
        payload, raw_sha = request_json(
            api_key,
            f"finance:idx/{endpoint}",
            {"year": year, "month": month, "page": page},
        )
        if payload.get("provider") != "idx" or payload.get("dataset") != dataset:
            raise IdentityRefreshError(f"{endpoint} provider/dataset mismatch")
        pages.append(payload)
        provenance.append(
            {
                "year": year,
                "month": month,
                "page": page,
                "count": payload.get("count"),
                "total": payload.get("total"),
                "raw_sha256": raw_sha,
            }
        )
        has_more = payload.get("hasMore")
        if not isinstance(has_more, bool):
            raise IdentityRefreshError(f"{endpoint} invalid hasMore")
        if not has_more:
            break
        next_page = payload.get("nextPage")
        if not isinstance(next_page, int) or next_page <= page:
            raise IdentityRefreshError(f"{endpoint} invalid nextPage")
        page = next_page
        if len(pages) >= MAX_MONTH_PAGES:
            raise IdentityRefreshError(f"{endpoint} pagination exceeded safety bound")
    return pages, provenance


def fetch_ipo_year(api_key: str, year: int) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, raw_sha = request_json(
        api_key,
        "finance:idx/ipo",
        {"year": year, "length": 200, "start": 0},
    )
    if payload.get("provider") != "idx" or payload.get("dataset") != "ipo":
        raise IdentityRefreshError("ipo provider/dataset mismatch")
    return payload, {"year": year, "total": payload.get("total"), "raw_sha256": raw_sha}


def load_previous() -> tuple[set[str], date, str]:
    manifest = json.loads(IDENTITY_MANIFEST.read_text(encoding="utf-8"))
    previous_as_of = date.fromisoformat(str(manifest["derivation"]["as_of_panel_date"]))
    expected_csv_sha = str(manifest["output_sha256"])
    actual_csv_sha = sha256_bytes(IDENTITY_CSV.read_bytes())
    if expected_csv_sha != actual_csv_sha:
        raise IdentityRefreshError("pinned identity CSV SHA mismatch")
    tickers: set[str] = set()
    with IDENTITY_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ticker = str(row.get("ticker", "")).strip().upper()
            if str(row.get("listed_to", "")).strip():
                continue
            if not ticker or ticker in tickers:
                raise IdentityRefreshError(f"invalid/duplicate pinned ticker: {ticker!r}")
            tickers.add(ticker)
    return tickers, previous_as_of, actual_csv_sha


def main() -> int:
    api_key = os.environ.get("ZAPI_API_KEY", "")
    if not api_key:
        raise SystemExit("ZAPI_API_KEY missing")

    previous, previous_as_of, previous_csv_sha = load_previous()
    as_of = datetime.now(ZoneInfo("Asia/Jakarta")).date()
    if as_of < previous_as_of:
        raise IdentityRefreshError("current Jakarta date precedes pinned as-of")

    securities, securities_prov = fetch_offset_dataset(api_key, "securities", "securities")
    companies, companies_prov = fetch_offset_dataset(api_key, "companies", "listed-companies")

    # Inclusive start month is deliberate: it catches a listing-status event that
    # was already effective by the prior snapshot but was missing from that snapshot.
    delisting_pages: list[dict[str, Any]] = []
    new_listing_pages: list[dict[str, Any]] = []
    delisting_prov: list[dict[str, Any]] = []
    new_listing_prov: list[dict[str, Any]] = []
    for year, month in month_range(previous_as_of, as_of):
        pages, prov = fetch_month_dataset(api_key, "delistings", "delistings", year, month)
        delisting_pages.extend(pages)
        delisting_prov.extend(prov)
        pages, prov = fetch_month_dataset(api_key, "new-listings", "new-listings", year, month)
        new_listing_pages.extend(pages)
        new_listing_prov.extend(prov)

    ipo_payloads: list[dict[str, Any]] = []
    ipo_prov: list[dict[str, Any]] = []
    for year in range(previous_as_of.year, as_of.year + 1):
        payload, prov = fetch_ipo_year(api_key, year)
        ipo_payloads.append(payload)
        ipo_prov.append(prov)

    result = reconstruct_active_roster(
        securities_rows=securities,
        companies_rows=companies,
        delisting_pages=delisting_pages,
        new_listing_pages=new_listing_pages,
        ipo_payloads=ipo_payloads,
        previous_tickers=previous,
        previous_as_of=previous_as_of,
        as_of=as_of,
    )

    output = {
        "schema_version": "stockbit_identity_refresh_candidate_v1",
        "status": "ACTIVATION_SAFE_CANDIDATE" if result.activation_safe else "BLOCKED_UNEXPLAINED_DELTA",
        "as_of": as_of.isoformat(),
        "previous_as_of": previous_as_of.isoformat(),
        "previous_count": len(previous),
        "previous_csv_sha256": previous_csv_sha,
        "base_current_count": result.diagnostics["base_count"],
        "candidate_count": len(result.tickers),
        "candidate_snapshot_sha256": result.snapshot_sha256,
        "additions": result.additions,
        "removals": result.removals,
        "explained_additions": result.explained_additions,
        "unexplained_additions": result.unexplained_additions,
        "explained_removals": result.explained_removals,
        "unexplained_removals": result.unexplained_removals,
        "effective_delistings": result.effective_delistings,
        "effective_positive_listings": result.effective_positive_listings,
        "diagnostics": result.diagnostics,
        "source_provenance": {
            "securities": securities_prov,
            "companies": companies_prov,
            "delistings": delisting_prov,
            "new_listings": new_listing_prov,
            "ipo": ipo_prov,
        },
        "roster_mutated": False,
        "outcome_accessed": False,
        "model_accessed": False,
        "stock_summary_used_for_membership": False,
    }
    print(json.dumps(output, sort_keys=True, indent=2, ensure_ascii=False))

    if not result.activation_safe:
        raise SystemExit("candidate blocked by unexplained identity delta")
    if result.diagnostics["listing_date_mismatches"]:
        raise SystemExit("candidate blocked by cross-source listing-date mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
