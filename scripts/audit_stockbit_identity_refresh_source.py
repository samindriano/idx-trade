from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable

import requests

API_BASE = "https://api.zpi.web.id/v1"
KEY = os.environ.get("ZAPI_API_KEY", "")
TIMEOUT_SECONDS = 30
PAGE_SIZE = 500
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{1,5}$")
PINNED_ROSTER = Path("config/stockbit_stream_universe_v1.csv")
PINNED_EXPECTED_COUNT = 963
COMPLETED_CROSSCHECK_DATE = "2026-08-20"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(raw)


def unwrap(payload: Any) -> Any:
    if (
        isinstance(payload, dict)
        and "project" in payload
        and "timestamp" in payload
        and isinstance(payload.get("data"), dict)
    ):
        return payload["data"]
    return payload


def get_with_retry(path: str, params: dict[str, Any], *, max_attempts: int = 3) -> tuple[requests.Response, bytes, int, list[str]]:
    transient: list[str] = []
    url = f"{API_BASE}/{path}"
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers={"x-api-key": KEY},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            transient.append(f"attempt={attempt} transport={type(exc).__name__}")
            if attempt >= max_attempts:
                raise
            time.sleep(float(attempt))
            continue

        if response.status_code in {401, 403, 429}:
            raise RuntimeError(f"blocked provider request {path}: HTTP {response.status_code}")
        if 500 <= response.status_code <= 599:
            transient.append(f"attempt={attempt} http={response.status_code}")
            if attempt >= max_attempts:
                raise RuntimeError(f"provider {path} remained HTTP {response.status_code}")
            time.sleep(float(attempt))
            continue
        if response.status_code != 200:
            raise RuntimeError(f"provider request {path} failed: HTTP {response.status_code}: {response.text[:240]}")
        return response, bytes(response.content), attempt, transient
    raise AssertionError("unreachable")


def fetch_paginated(
    *,
    path: str,
    expected_dataset: str,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    raw_pages: list[dict[str, Any]] = []
    total_expected: int | None = None
    filtered_expected: int | None = None
    start = 0
    page_index = 0

    while True:
        params: dict[str, Any] = {"length": PAGE_SIZE, "start": start}
        if extra_params:
            params.update(extra_params)
        response, raw, attempts, transient = get_with_retry(path, params)
        try:
            outer = response.json()
        except Exception as exc:
            raise RuntimeError(f"{path} returned non-JSON page at start={start}") from exc
        payload = unwrap(outer)
        if not isinstance(payload, dict):
            raise RuntimeError(f"{path} payload is not an object")
        if payload.get("provider") != "idx":
            raise RuntimeError(f"{path} provider mismatch: {payload.get('provider')!r}")
        if payload.get("dataset") != expected_dataset:
            raise RuntimeError(f"{path} dataset mismatch: {payload.get('dataset')!r}")
        page_rows = payload.get("data")
        if not isinstance(page_rows, list):
            raise RuntimeError(f"{path} page data is not a list")
        try:
            total = int(payload["recordsTotal"])
            filtered = int(payload.get("recordsFiltered", total))
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"{path} row-count metadata malformed") from exc
        if total < 0 or filtered < 0 or filtered > total:
            raise RuntimeError(f"{path} inconsistent row-count metadata total={total} filtered={filtered}")
        if total != filtered:
            raise RuntimeError(f"{path} unfiltered audit expected recordsTotal==recordsFiltered, got {total}!={filtered}")

        if total_expected is None:
            total_expected = total
            filtered_expected = filtered
        elif total != total_expected or filtered != filtered_expected:
            raise RuntimeError(
                f"{path} metadata changed across pages: expected {total_expected}/{filtered_expected}, got {total}/{filtered}"
            )

        raw_pages.append(
            {
                "page_index": page_index,
                "request_start": start,
                "returned_rows": len(page_rows),
                "raw_sha256": sha256_bytes(raw),
                "attempts": attempts,
                "transient_events": transient,
            }
        )
        for row in page_rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"{path} contains non-object row")
            rows.append(row)

        if len(rows) >= total:
            break
        if not page_rows:
            raise RuntimeError(f"{path} pagination stalled before recordsTotal at start={start}")
        start += PAGE_SIZE
        page_index += 1
        if page_index > 20:
            raise RuntimeError(f"{path} pagination exceeded safety bound")

    if total_expected is None:
        raise RuntimeError(f"{path} returned no metadata")
    if len(rows) != total_expected:
        raise RuntimeError(f"{path} pagination incomplete: rows={len(rows)} recordsTotal={total_expected}")
    return {
        "path": path,
        "dataset": expected_dataset,
        "records_total": total_expected,
        "rows": rows,
        "raw_pages": raw_pages,
    }


def load_pinned_roster() -> tuple[dict[str, dict[str, str]], str]:
    raw = PINNED_ROSTER.read_bytes()
    with PINNED_ROSTER.open(newline="", encoding="utf-8") as handle:
        parsed = list(csv.DictReader(handle))
    active: dict[str, dict[str, str]] = {}
    for row in parsed:
        ticker = str(row.get("ticker", "")).strip().upper()
        if str(row.get("listed_to", "")).strip():
            continue
        if not TICKER_RE.fullmatch(ticker):
            raise RuntimeError(f"pinned roster invalid ticker {ticker!r}")
        if ticker in active:
            raise RuntimeError(f"pinned roster duplicate ticker {ticker}")
        active[ticker] = row
    if len(active) != PINNED_EXPECTED_COUNT:
        raise RuntimeError(f"pinned roster active count changed: expected {PINNED_EXPECTED_COUNT}, got {len(active)}")
    return active, sha256_bytes(raw)


def parse_iso_date(value: Any) -> bool:
    if value in {None, ""}:
        return False
    text = str(value)[:10]
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def securities_index(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    diagnostics = {
        "blank_name": [],
        "missing_or_invalid_listing_date": [],
        "nonpositive_or_invalid_shares": [],
        "blank_listing_board": [],
    }
    for row in rows:
        code = str(row.get("Code", "")).strip().upper()
        if not TICKER_RE.fullmatch(code):
            raise RuntimeError(f"securities invalid ticker {code!r}")
        if code in out:
            raise RuntimeError(f"securities duplicate ticker {code}")
        if not str(row.get("Name", "")).strip():
            diagnostics["blank_name"].append(code)
        if not parse_iso_date(row.get("ListingDate")):
            diagnostics["missing_or_invalid_listing_date"].append(code)
        try:
            shares = float(row.get("Shares"))
            if not (shares > 0):
                raise ValueError
        except (TypeError, ValueError):
            diagnostics["nonpositive_or_invalid_shares"].append(code)
        if not str(row.get("ListingBoard", "")).strip():
            diagnostics["blank_listing_board"].append(code)
        out[code] = row
    return out, diagnostics


def companies_index(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    stock_rows: dict[str, dict[str, Any]] = {}
    non_stock_rows = 0
    non_boolean_stock_flag: list[str] = []
    diagnostics = {
        "blank_name": [],
        "missing_or_invalid_listing_date": [],
    }
    for row in rows:
        flag = row.get("EfekEmiten_Saham")
        raw_code = str(row.get("KodeEmiten", "")).strip().upper()
        if not isinstance(flag, bool):
            non_boolean_stock_flag.append(raw_code or "<BLANK>")
        if flag is not True:
            non_stock_rows += 1
            continue
        code = raw_code
        if not TICKER_RE.fullmatch(code):
            raise RuntimeError(f"companies invalid stock ticker {code!r}")
        if code in stock_rows:
            raise RuntimeError(f"companies duplicate stock ticker {code}")
        if not str(row.get("NamaEmiten", "")).strip():
            diagnostics["blank_name"].append(code)
        if not parse_iso_date(row.get("TanggalPencatatan")):
            diagnostics["missing_or_invalid_listing_date"].append(code)
        stock_rows[code] = row
    diagnostics["non_stock_rows"] = non_stock_rows
    diagnostics["non_boolean_stock_flag"] = sorted(non_boolean_stock_flag)
    return stock_rows, diagnostics


def stock_summary_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = str(row.get("StockCode", "")).strip().upper()
        if not TICKER_RE.fullmatch(code):
            raise RuntimeError(f"stock-summary invalid ticker {code!r}")
        if code in out:
            raise RuntimeError(f"stock-summary duplicate ticker {code}")
        if str(row.get("Date", ""))[:10] != COMPLETED_CROSSCHECK_DATE:
            raise RuntimeError(f"stock-summary wrong session for {code}: {row.get('Date')!r}")
        out[code] = row
    return out


def set_sha(values: set[str]) -> str:
    return canonical_sha(sorted(values))


def row_map_sha(rows: dict[str, dict[str, Any]]) -> str:
    return canonical_sha({code: rows[code] for code in sorted(rows)})


def slim_metadata(source: str, row: dict[str, Any]) -> dict[str, Any]:
    if source == "pinned":
        return {
            "ticker": row.get("ticker"),
            "company_name": row.get("company_name"),
            "listed_from": row.get("listed_from"),
        }
    if source == "securities":
        return {
            "Code": row.get("Code"),
            "Name": row.get("Name"),
            "Shares": row.get("Shares"),
            "ListingDate": row.get("ListingDate"),
            "ListingBoard": row.get("ListingBoard"),
        }
    if source == "companies":
        return {
            "KodeEmiten": row.get("KodeEmiten"),
            "NamaEmiten": row.get("NamaEmiten"),
            "TanggalPencatatan": row.get("TanggalPencatatan"),
            "PapanPencatatan": row.get("PapanPencatatan"),
            "Status": row.get("Status"),
            "EfekEmiten_Saham": row.get("EfekEmiten_Saham"),
        }
    if source == "stock_summary":
        return {
            "StockCode": row.get("StockCode"),
            "StockName": row.get("StockName"),
            "Date": row.get("Date"),
            "ListedShares": row.get("ListedShares"),
            "DelistingDate": row.get("DelistingDate"),
        }
    return {}


def diff_payload(
    left_name: str,
    left: dict[str, dict[str, Any]],
    right_name: str,
    right: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    left_codes = set(left)
    right_codes = set(right)
    only_left = sorted(left_codes - right_codes)
    only_right = sorted(right_codes - left_codes)
    return {
        "left": left_name,
        "right": right_name,
        "intersection_count": len(left_codes & right_codes),
        "only_left_count": len(only_left),
        "only_right_count": len(only_right),
        "only_left": [
            {"ticker": code, "metadata": slim_metadata(left_name, left[code])} for code in only_left
        ],
        "only_right": [
            {"ticker": code, "metadata": slim_metadata(right_name, right[code])} for code in only_right
        ],
    }


def repeat_summary(
    first_fetch: dict[str, Any],
    second_fetch: dict[str, Any],
    indexer: Callable[[list[dict[str, Any]]], tuple[dict[str, dict[str, Any]], dict[str, Any]]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    first_index, first_diag = indexer(first_fetch["rows"])
    second_index, second_diag = indexer(second_fetch["rows"])
    first_set = set(first_index)
    second_set = set(second_index)
    result = {
        "first_count": len(first_index),
        "second_count": len(second_index),
        "first_set_sha256": set_sha(first_set),
        "second_set_sha256": set_sha(second_set),
        "ticker_set_equal": first_set == second_set,
        "first_row_map_sha256": row_map_sha(first_index),
        "second_row_map_sha256": row_map_sha(second_index),
        "row_content_equal": first_index == second_index,
        "only_first": sorted(first_set - second_set),
        "only_second": sorted(second_set - first_set),
        "first_raw_pages": first_fetch["raw_pages"],
        "second_raw_pages": second_fetch["raw_pages"],
        "first_diagnostics": first_diag,
        "second_diagnostics": second_diag,
    }
    return first_index, first_diag, result


def main() -> int:
    if not KEY:
        print(json.dumps({"status": "BLOCKED", "detail": "ZAPI_API_KEY missing"}))
        return 2

    output: dict[str, Any] = {
        "schema_version": "stockbit_identity_refresh_source_audit_v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "crosscheck_completed_session": COMPLETED_CROSSCHECK_DATE,
        "roster_mutated": False,
        "model_accessed": False,
        "outcome_accessed": False,
        "counter_mutated": False,
    }
    try:
        pinned, pinned_sha = load_pinned_roster()
        output["pinned_roster"] = {
            "count": len(pinned),
            "csv_sha256": pinned_sha,
            "ticker_set_sha256": set_sha(set(pinned)),
        }

        sec_first = fetch_paginated(path="finance:idx/securities", expected_dataset="securities")
        sec_second = fetch_paginated(path="finance:idx/securities", expected_dataset="securities")
        securities, sec_diag, sec_repeat = repeat_summary(sec_first, sec_second, securities_index)
        output["securities"] = sec_repeat

        comp_first = fetch_paginated(path="finance:idx/companies", expected_dataset="listed-companies")
        comp_second = fetch_paginated(path="finance:idx/companies", expected_dataset="listed-companies")
        companies, comp_diag, comp_repeat = repeat_summary(comp_first, comp_second, companies_index)
        output["companies_stock_enabled"] = comp_repeat

        stock_fetch = fetch_paginated(
            path="finance:idx/stock-summary",
            expected_dataset="stock-summary",
            extra_params={"date": COMPLETED_CROSSCHECK_DATE},
        )
        stock_summary = stock_summary_index(stock_fetch["rows"])
        output["stock_summary_crosscheck"] = {
            "count": len(stock_summary),
            "ticker_set_sha256": set_sha(set(stock_summary)),
            "row_map_sha256": row_map_sha(stock_summary),
            "raw_pages": stock_fetch["raw_pages"],
        }

        output["deltas"] = {
            "pinned_vs_securities": diff_payload("pinned", pinned, "securities", securities),
            "pinned_vs_companies": diff_payload("pinned", pinned, "companies", companies),
            "securities_vs_companies": diff_payload("securities", securities, "companies", companies),
            "pinned_vs_stock_summary": diff_payload("pinned", pinned, "stock_summary", stock_summary),
            "securities_vs_stock_summary": diff_payload("securities", securities, "stock_summary", stock_summary),
            "companies_vs_stock_summary": diff_payload("companies", companies, "stock_summary", stock_summary),
        }

        hard_failures: list[str] = []
        if not sec_repeat["ticker_set_equal"]:
            hard_failures.append("securities ticker set changed across immediate repeat")
        if not comp_repeat["ticker_set_equal"]:
            hard_failures.append("companies stock-enabled ticker set changed across immediate repeat")
        if sec_diag["blank_name"]:
            hard_failures.append("securities contains blank names")
        if comp_diag["blank_name"]:
            hard_failures.append("companies stock-enabled rows contain blank names")
        if sec_diag["missing_or_invalid_listing_date"]:
            hard_failures.append("securities contains missing/invalid listing dates")
        if comp_diag["missing_or_invalid_listing_date"]:
            hard_failures.append("companies stock-enabled rows contain missing/invalid listing dates")

        output["hard_integrity_failures"] = hard_failures
        output["status"] = "AUDIT_INTEGRITY_FAIL" if hard_failures else "AUDIT_EVIDENCE_READY_REVIEW_REQUIRED"
        print(json.dumps(output, sort_keys=True, indent=2, ensure_ascii=False))
        return 2 if hard_failures else 0
    except Exception as exc:
        output["status"] = "AUDIT_EXECUTION_FAILED"
        output["detail"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(output, sort_keys=True, indent=2, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
