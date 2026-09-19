"""Outcome-blind audit of locally persisted IDX market-context snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


PARITY_INDEX_FIELDS = [
    "Date",
    "Previous",
    "Highest",
    "Lowest",
    "Close",
    "NumberOfStock",
    "Change",
    "Volume",
    "Value",
    "Frequency",
    "MarketCapital",
]
PARITY_STOCK_FIELDS = [
    "Date",
    "Previous",
    "High",
    "Low",
    "Close",
    "Change",
    "Volume",
    "Value",
    "Frequency",
    "ListedShares",
    "ForeignBuy",
    "ForeignSell",
    "NonRegularVolume",
    "NonRegularValue",
    "NonRegularFrequency",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unwrap(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        if isinstance(data, list):
            return data
    return []


def numeric_equal(left: object, right: object) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return left == right


def parity(source: list[dict[str, object]], direct: list[dict[str, object]], key: str, fields: list[str]) -> dict[str, object]:
    source_map = {str(row.get(key)): row for row in source}
    direct_map = {str(row.get(key)): row for row in direct}
    common = sorted(set(source_map) & set(direct_map))
    field_rates = {
        field: sum(numeric_equal(source_map[code].get(field), direct_map[code].get(field)) for code in common)
        / len(common)
        if common
        else 0.0
        for field in fields
    }
    return {
        "source_rows": len(source),
        "direct_rows": len(direct),
        "common_keys": len(common),
        "source_only_keys": len(set(source_map) - set(direct_map)),
        "direct_only_keys": len(set(direct_map) - set(source_map)),
        "field_match_rates": field_rates,
        "all_fields_exact": all(rate == 1.0 for rate in field_rates.values())
        and len(common) == len(source) == len(direct),
    }


def stock_quality(rows: list[dict[str, object]], date: str, panel: pd.DataFrame) -> dict[str, object]:
    codes = [str(row.get("StockCode")) for row in rows]
    volumes = [float(row.get("Volume") or 0) for row in rows]
    changes = [float(row.get("Change") or 0) for row in rows]
    closes = [row.get("Close") for row in rows]
    panel_slice = panel.loc[panel["date"].eq(pd.Timestamp(date).date())]
    panel_codes = set(panel_slice["ticker"].astype(str))
    source_codes = set(codes)
    return {
        "rows": len(rows),
        "unique_codes": len(source_codes),
        "duplicate_codes": len(codes) - len(source_codes),
        "all_rows_same_date": all(str(row.get("Date", "")).startswith(date) for row in rows),
        "positive_volume": sum(value > 0 for value in volumes),
        "zero_volume": sum(value == 0 for value in volumes),
        "positive_frequency": sum(float(row.get("Frequency") or 0) > 0 for row in rows),
        "advance": sum(value > 0 for value in changes),
        "decline": sum(value < 0 for value in changes),
        "unchanged": sum(value == 0 for value in changes),
        "zero_volume_nonzero_change": sum(volume == 0 and change != 0 for volume, change in zip(volumes, changes)),
        "missing_close": sum(value in (None, "") for value in closes),
        "panel_rows_on_date": int(len(panel_slice)),
        "panel_ticker_overlap": int(len(source_codes & panel_codes)),
        "panel_ticker_coverage": float(len(source_codes & panel_codes) / len(panel_codes)) if panel_codes else None,
    }


def market_reconciliation(stock_rows: list[dict[str, object]], index_rows: list[dict[str, object]]) -> dict[str, object]:
    composite = next(row for row in index_rows if row.get("IndexCode") == "COMPOSITE")
    regular_sums = {
        field: sum(float(row.get(field) or 0) for row in stock_rows)
        for field in ("Volume", "Value", "Frequency")
    }
    nonregular_sums = {
        field: sum(float(row.get(field) or 0) for row in stock_rows)
        for field in ("NonRegularVolume", "NonRegularValue", "NonRegularFrequency")
    }
    total_sums = {
        "Volume": regular_sums["Volume"] + nonregular_sums["NonRegularVolume"],
        "Value": regular_sums["Value"] + nonregular_sums["NonRegularValue"],
        "Frequency": regular_sums["Frequency"] + nonregular_sums["NonRegularFrequency"],
    }
    diffs = {field: total_sums[field] - float(composite.get(field) or 0) for field in total_sums}
    relative_diffs = {
        field: (diffs[field] / abs(float(composite.get(field) or 1)))
        for field in diffs
    }
    return {
        "regular_sums": regular_sums,
        "nonregular_sums": nonregular_sums,
        "total_sums": total_sums,
        "composite": {field: composite.get(field) for field in total_sums},
        "diffs": diffs,
        "relative_diffs": relative_diffs,
        "exact": all(value == 0 for value in diffs.values()),
        "status": "EXACT" if all(value == 0 for value in diffs.values()) else "LOCALIZED_SOURCE_ARITHMETIC_DISCREPANCY",
    }


def audit_digital(path: Path, nested_indices: bool) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("data", [])
    if nested_indices:
        series = rows
        daily = [item for row in series for item in (row.get("months") or [])]
        dates = sorted(str(item.get("date")) for item in daily if item.get("date"))
        return {
            "file": path.name,
            "sha256": sha256_file(path),
            "series": len(series),
            "daily_rows": len(daily),
            "date_first": dates[0] if dates else None,
            "date_last": dates[-1] if dates else None,
            "null_close_rows": sum(item.get("close") in (None, {}) for item in daily),
            "series_names": [str(row.get("Name")) for row in series],
        }
    dates = sorted(str(row.get("date")) for row in rows if row.get("date"))
    return {
        "file": path.name,
        "sha256": sha256_file(path),
        "rows": len(rows),
        "date_first": dates[0] if dates else None,
        "date_last": dates[-1] if dates else None,
        "keys": sorted(rows[0]) if rows else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    panel = pd.read_parquet(args.panel, columns=["ticker", "date"])
    panel["date"] = pd.to_datetime(panel["date"]).dt.date
    dates = ["2021-01-04", "2024-06-21", "2026-07-31"]
    date_results = []
    for date in dates:
        compact = date.replace("-", "")
        z_index_path = args.root / "zapi" / f"IndexSummary_{compact}.json"
        z_stock_path = args.root / "zapi" / f"StockSummary_{compact}.json"
        d_index_path = args.root / "crosscheck" / f"index_{date}_direct.json"
        d_stock_path = args.root / "crosscheck" / f"stock_{date}_direct.json"
        z_index = json.loads(z_index_path.read_text(encoding="utf-8"))
        z_stock = json.loads(z_stock_path.read_text(encoding="utf-8"))
        d_index = json.loads(d_index_path.read_text(encoding="utf-8"))
        d_stock = json.loads(d_stock_path.read_text(encoding="utf-8"))
        index_rows = unwrap(z_index)
        stock_rows = unwrap(z_stock)
        direct_index = unwrap(d_index)
        direct_stock = unwrap(d_stock)
        date_results.append(
            {
                "date": date,
                "zapi_index_timestamp": z_index.get("timestamp"),
                "zapi_stock_timestamp": z_stock.get("timestamp"),
                "index_parity": parity(index_rows, direct_index, "IndexCode", PARITY_INDEX_FIELDS),
                "stock_parity": parity(stock_rows, direct_stock, "StockCode", PARITY_STOCK_FIELDS),
                "stock_quality": stock_quality(stock_rows, date, panel),
                "market_reconciliation": market_reconciliation(stock_rows, index_rows),
            }
        )

    digital = [audit_digital(path, nested_indices=False) for path in sorted((args.root / "digital").glob("market_*.json"))]
    indices = [audit_digital(path, nested_indices=True) for path in sorted((args.root / "digital").glob("indices_*.json"))]
    source_paths: dict[str, Path] = {"panel": args.panel}
    for date in dates:
        compact = date.replace("-", "")
        source_paths[f"rich_{compact}_zapi_index"] = args.root / "zapi" / f"IndexSummary_{compact}.json"
        source_paths[f"rich_{compact}_zapi_stock"] = args.root / "zapi" / f"StockSummary_{compact}.json"
        source_paths[f"rich_{compact}_direct_index"] = args.root / "crosscheck" / f"index_{date}_direct.json"
        source_paths[f"rich_{compact}_direct_stock"] = args.root / "crosscheck" / f"stock_{date}_direct.json"
    for path in sorted((args.root / "digital").glob("market_*.json")):
        source_paths[f"digital_{path.stem}"] = path
    for path in sorted((args.root / "digital").glob("indices_*.json")):
        source_paths[f"digital_{path.stem}"] = path
    source_hashes = {name: sha256_file(path) for name, path in source_paths.items()}
    result = {
        "audit": "ALPHA_MARKET_CONTEXT_SOURCE_AUDIT_V1",
        "status": "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED",
        "code_sha256": sha256_file(Path(__file__)),
        "source_hashes": source_hashes,
        "scope": {
            "outcome_accessed": False,
            "target_accessed": False,
            "provider_accessed": False,
            "feature_created": False,
            "canonical_mutation": False,
        },
        "panel": {
            "path": str(args.panel),
            "sha256": sha256_file(args.panel),
            "rows": int(len(panel)),
            "dates": int(panel["date"].nunique()),
            "tickers": int(panel["ticker"].nunique()),
        },
        "rich_daily_crosschecks": date_results,
        "digital_monthly_blocks": {"market": digital, "indices": indices},
        "admission": {
            "daily_population_complete": False,
            "feature_ready": False,
            "reason": [
                "rich per-stock/index data is persisted for only three exact dates",
                "digital files cover three sampled months rather than the full panel horizon",
                "response timestamps are retrieval times, not row-level publication/knowledge times",
                "source identity and direct-vs-Zapi parity pass only for the sampled dates",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "dates": len(date_results), "digital_market_files": len(digital), "digital_index_files": len(indices)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
