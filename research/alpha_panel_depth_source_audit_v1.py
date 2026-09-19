"""Outcome-blind audit of the staged multi-symbol IDX history probe."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_FIELDS = {
    "bid",
    "change",
    "close",
    "date",
    "foreignBuyShares",
    "foreignBuyValue",
    "foreignSellShares",
    "foreignSellValue",
    "frequency",
    "high",
    "listedShares",
    "low",
    "netForeignShares",
    "netForeignValue",
    "offer",
    "open",
    "previous",
    "value",
    "volume",
}
NUMERIC_FIELDS = sorted(REQUIRED_FIELDS - {"date"})
OFFICIAL_FIELDS = {
    "bid": "Bid",
    "change": "Change",
    "close": "Close",
    "date": "Date",
    "foreignBuyShares": "ForeignBuy",
    "foreignSellShares": "ForeignSell",
    "frequency": "Frequency",
    "high": "High",
    "listedShares": "ListedShares",
    "low": "Low",
    "offer": "Offer",
    "open": "OpenPrice",
    "previous": "Previous",
    "value": "Value",
    "volume": "Volume",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_number(value: Any) -> bool:
    if value is None or value == "":
        return False
    try:
        return bool(pd.notna(float(value)))
    except (TypeError, ValueError):
        return False


def numeric_equal(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left == right
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return str(left) == str(right)


def load_items(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object payload: {path}")
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError(f"expected data.items payload: {path}")
    return data, [row for row in data["items"] if isinstance(row, dict)]


def row_quality(code: str, data: dict[str, Any], rows: list[dict[str, Any]], official_dates: set[str], panel_keys: set[tuple[str, str]]) -> dict[str, Any]:
    dates = [str(row.get("date", ""))[:10] for row in rows]
    parsed = pd.to_datetime(pd.Series(dates), errors="coerce")
    date_counts = pd.Series(dates).value_counts()
    field_keys = sorted(set().union(*(row.keys() for row in rows))) if rows else []
    missing_fields = sorted(REQUIRED_FIELDS - set(field_keys))
    numeric_missing = {field: sum(not finite_number(row.get(field)) for row in rows) for field in NUMERIC_FIELDS}
    negative_counts = {
        field: sum(finite_number(row.get(field)) and float(row[field]) < 0 for row in rows)
        for field in NUMERIC_FIELDS
    }
    arithmetic_net_shares = sum(
        finite_number(row.get("netForeignShares"))
        and finite_number(row.get("foreignBuyShares"))
        and finite_number(row.get("foreignSellShares"))
        and float(row["netForeignShares"]) == float(row["foreignBuyShares"]) - float(row["foreignSellShares"])
        for row in rows
    )
    arithmetic_net_value = sum(
        finite_number(row.get("netForeignValue"))
        and finite_number(row.get("foreignBuyValue"))
        and finite_number(row.get("foreignSellValue"))
        and float(row["netForeignValue"]) == float(row["foreignBuyValue"]) - float(row["foreignSellValue"])
        for row in rows
    )
    high_low_valid = sum(
        finite_number(row.get("high")) and finite_number(row.get("low")) and float(row["high"]) >= float(row["low"])
        for row in rows
    )
    bid_offer_valid = sum(
        not (finite_number(row.get("bid")) and finite_number(row.get("offer")) and float(row["bid"]) > 0 and float(row["offer"]) > 0)
        or float(row["bid"]) <= float(row["offer"])
        for row in rows
    )
    date_set = set(dates)
    panel_date_set = {date for ticker, date in panel_keys if ticker == code}
    return {
        "code": code,
        "name": data.get("name"),
        "dataset": data.get("dataset"),
        "provider": data.get("provider"),
        "unit": data.get("unit"),
        "value_basis": data.get("valueBasis"),
        "declared_count": data.get("count"),
        "rows": len(rows),
        "field_keys": field_keys,
        "missing_required_fields": missing_fields,
        "first_row_date": min(date_set) if date_set else None,
        "last_row_date": max(date_set) if date_set else None,
        "declared_from": data.get("from"),
        "declared_to": data.get("to"),
        "invalid_date_rows": int(parsed.isna().sum()),
        "unique_dates": len(date_set),
        "duplicate_date_rows": int(sum(count - 1 for count in date_counts if count > 1)),
        "descending_date_order": all(dates[index] >= dates[index + 1] for index in range(len(dates) - 1)),
        "official_calendar_overlap_dates": len(date_set & official_dates),
        "outside_official_calendar_dates": len(date_set - official_dates),
        "panel_date_overlap": len(date_set & panel_date_set),
        "panel_dates_available": len(panel_date_set),
        "numeric_missing": numeric_missing,
        "negative_counts": negative_counts,
        "net_foreign_shares_exact_rows": int(arithmetic_net_shares),
        "net_foreign_value_exact_rows": int(arithmetic_net_value),
        "high_ge_low_rows": int(high_low_valid),
        "bid_le_offer_rows_or_not_applicable": int(bid_offer_valid),
    }


def official_parity(code: str, rows: list[dict[str, Any]], official_rows: list[dict[str, Any]], requested_date: str) -> dict[str, Any]:
    panel_map = {str(row.get("date", ""))[:10] + "|" + code: row for row in rows if str(row.get("date", ""))[:10] == requested_date}
    official_map = {
        str(row.get("Date", ""))[:10] + "|" + str(row.get("StockCode")): row
        for row in official_rows
        if str(row.get("Date", ""))[:10] == requested_date
    }
    key = f"{requested_date}|{code}"
    left = panel_map.get(key)
    right = official_map.get(key)
    if left is None or right is None:
        return {"code": code, "date": requested_date, "panel_present": left is not None, "official_present": right is not None, "all_shared_fields_exact": None, "field_match": {}}
    field_match = {
        name: (str(left.get(name, ""))[:10] == str(right.get(official_name, ""))[:10] if name == "date" else numeric_equal(left.get(name), right.get(official_name)))
        for name, official_name in OFFICIAL_FIELDS.items()
    }
    return {"code": code, "date": requested_date, "panel_present": True, "official_present": True, "all_shared_fields_exact": all(field_match.values()), "field_match": field_match}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--historical-depth-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    records = manifest.get("records", [])
    session_frame = pd.read_csv(args.sessions)
    official_dates = set(pd.to_datetime(session_frame["date"], errors="coerce").dt.strftime("%Y-%m-%d").dropna())
    panel = pd.read_parquet(args.panel, columns=["ticker", "date"])
    panel["ticker"] = panel["ticker"].astype(str)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    panel_keys = set(zip(panel["ticker"], panel["date"]))

    source_hashes: dict[str, str] = {
        "manifest": sha256_file(args.manifest),
        "sessions": sha256_file(args.sessions),
        "panel": sha256_file(args.panel),
    }
    symbol_results: list[dict[str, Any]] = []
    parity_results: list[dict[str, Any]] = []
    raw_hash_checks: list[dict[str, Any]] = []
    all_codes: list[str] = []
    for record in records:
        code = str(record.get("code_requested"))
        all_codes.append(code)
        normalized_path = args.root / "normalized" / f"{code}.json"
        raw_path = args.root / "raw" / f"{code}.response.bin"
        data, rows = load_items(normalized_path)
        source_hashes[f"normalized_{code}"] = sha256_file(normalized_path)
        source_hashes[f"raw_{code}"] = sha256_file(raw_path)
        raw_actual = source_hashes[f"raw_{code}"]
        raw_hash_checks.append({
            "code": code,
            "raw_exists": raw_path.exists(),
            "manifest_response_sha256": record.get("response_sha256"),
            "actual_raw_sha256": raw_actual,
            "hash_matches": record.get("response_sha256") == raw_actual,
            "manifest_response_bytes": record.get("response_bytes"),
            "actual_response_bytes": raw_path.stat().st_size,
            "bytes_match": record.get("response_bytes") == raw_path.stat().st_size,
        })
        symbol_results.append({
            **row_quality(code, data, rows, official_dates, panel_keys),
            "manifest_status": record.get("status"),
            "http_status": record.get("http_status"),
            "manifest_source": record.get("source"),
            "request_url_present": bool(record.get("request_url")),
            "observed_at_utc": record.get("observed_at_utc"),
            "row_code_field_absent": all("code" not in row for row in rows),
            "row_name_absent": all("name" not in row for row in rows),
            "identity_fields_absent": all(field not in data for field in ("isin", "issuer", "issuerId", "available_at", "knowledge_time", "published_at", "revision", "vintage")),
        })
        for requested_date, official_name in (("2020-01-02", "20200102.json"), ("2026-09-18", "20260918.json")):
            official_payload = json.loads((args.official_root / official_name).read_text(encoding="utf-8"))
            official_rows = official_payload.get("data", [])
            if isinstance(official_rows, dict):
                official_rows = official_rows.get("data", [])
            parity_results.append(official_parity(code, rows, official_rows, requested_date))

    historical_duplicate: dict[str, Any] = {"checked": False}
    if args.historical_depth_root is not None:
        hist_path = args.historical_depth_root / "normalized" / "zapi_idx_stock_history_bbca.json"
        panel_bbca_path = args.root / "normalized" / "BBCA.json"
        if hist_path.exists() and panel_bbca_path.exists():
            _, panel_bbca_rows = load_items(panel_bbca_path)
            hist_payload = json.loads(hist_path.read_text(encoding="utf-8"))
            hist_rows = hist_payload.get("data", {}).get("items", [])
            panel_set = {json.dumps(row, sort_keys=True, separators=(",", ":")) for row in panel_bbca_rows}
            hist_set = {json.dumps(row, sort_keys=True, separators=(",", ":")) for row in hist_rows}
            historical_duplicate = {
                "checked": True,
                "panel_depth_rows": len(panel_set),
                "historical_depth_rows": len(hist_set),
                "intersection_rows": len(panel_set & hist_set),
                "exact_rowset_duplicate": panel_set == hist_set,
                "historical_normalized_sha256": sha256_file(hist_path),
            }
            source_hashes["historical_depth_bbca_normalized"] = sha256_file(hist_path)

    result = {
        "audit": "ALPHA_PANEL_DEPTH_SOURCE_AUDIT_V1",
        "status": "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED",
        "code_sha256": sha256_file(Path(__file__)),
        "source_hashes": source_hashes,
        "scope": {
            "outcome_accessed": False,
            "target_accessed": False,
            "provider_accessed": False,
            "feature_created": False,
            "candidate_id_created": False,
            "canonical_mutation": False,
        },
        "manifest": {
            "schema": manifest.get("schema"),
            "run_id": manifest.get("run_id"),
            "source_count": manifest.get("source_count"),
            "record_count": len(records),
            "symbols": manifest.get("symbols", []),
            "retry_policy": manifest.get("retry_policy"),
            "all_safe_flags_false": all(manifest.get(key) is False for key in ("outcome_accessed", "model_scoring", "canonical_write", "cloud_or_r2_write")),
        },
        "symbols": symbol_results,
        "raw_hash_checks": raw_hash_checks,
        "official_parity": parity_results,
        "historical_duplicate_check": historical_duplicate,
        "coverage": {
            "official_calendar_rows": int(len(official_dates)),
            "panel_rows": int(len(panel)),
            "panel_dates": int(panel["date"].nunique()),
            "panel_tickers": int(panel["ticker"].nunique()),
            "panel_depth_symbols": len(set(all_codes)),
            "panel_depth_rows": int(sum(item["rows"] for item in symbol_results)),
        },
        "admission": {
            "feature_ready": False,
            "reason": [
                "surface contains only 12 selected symbols rather than the population-wide panel",
                "manifest observed_at and response timestamp are capture times, not row-level knowledge/publication times",
                "normalized rows have no available_at, revision, vintage, ISIN, issuer-transition, or corporate-action fields",
                "official-date parity is a field cross-check, not historical PIT or source-authority certification",
                "history extends outside the frozen official-session horizon and has no admitted listing/delisting transition contract",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "symbols": len(symbol_results), "rows": result["coverage"]["panel_depth_rows"], "official_parity_rows": len(parity_results)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
