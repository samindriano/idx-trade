"""Outcome-blind audit of independently acquired public IDX EOD snapshots.

This module measures what two pinned public GitHub snapshots actually contain.
It deliberately treats them as capability evidence only: no provider call,
canonical-data write, feature construction, target access, or admission decision
is performed here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


PHOLENK_COLUMNS = [
    "Date",
    "Ticker",
    "Name",
    "Volume",
    "Open",
    "High",
    "Low",
    "Close",
    "ListedShares",
    "Remarks",
]
DATASET_SAHAM_COLUMNS = ["date", "delisting_date"]
FORBIDDEN_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _date_set(values: pd.Series) -> set[str]:
    parsed = pd.to_datetime(values, errors="raise").dt.normalize()
    return set(parsed.dt.strftime("%Y-%m-%d"))


def _base_inventory(files: list[Path]) -> dict[str, Any]:
    if not files:
        raise ValueError("source directory has no CSV files")
    return {
        "file_count": len(files),
        "row_count": 0,
        "min_date": None,
        "max_date": None,
        "duplicate_key_rows": 0,
        "date_sets": {},
    }


def _stored_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in inventory.items() if key not in {"per_ticker", "date_sets"}}


def summarize_pholenk(root: Path) -> tuple[dict[str, Any], dict[str, set[str]]]:
    files = sorted(root.glob("*.csv"))
    result = _base_inventory(files)
    date_sets: dict[str, set[str]] = {}
    zero_volume = 0
    any_zero_ohlc = 0
    files_with_multiple_names = 0
    files_with_listed_share_changes = 0
    ticker_field_mismatch = 0
    per_ticker: dict[str, dict[str, Any]] = {}

    for path in files:
        frame = pd.read_csv(path, usecols=PHOLENK_COLUMNS, low_memory=False)
        parsed = pd.to_datetime(frame["Date"], errors="raise").dt.normalize()
        ticker = path.stem.upper()
        if frame["Ticker"].astype("string").str.upper().ne(ticker).any():
            ticker_field_mismatch += 1
        keys = pd.DataFrame({"date": parsed, "ticker": frame["Ticker"].astype("string").str.upper()})
        result["duplicate_key_rows"] += int(keys.duplicated(["date", "ticker"]).sum())
        dates = set(parsed.dt.strftime("%Y-%m-%d"))
        date_sets[ticker] = dates
        result["row_count"] += len(frame)
        mn = parsed.min().strftime("%Y-%m-%d")
        mx = parsed.max().strftime("%Y-%m-%d")
        result["min_date"] = mn if result["min_date"] is None or mn < result["min_date"] else result["min_date"]
        result["max_date"] = mx if result["max_date"] is None or mx > result["max_date"] else result["max_date"]
        zero_volume += int(frame["Volume"].fillna(0).eq(0).sum())
        any_zero_ohlc += int(frame[["Open", "High", "Low", "Close"]].fillna(0).eq(0).any(axis=1).sum())
        files_with_multiple_names += int(frame["Name"].astype("string").nunique(dropna=False) > 1)
        files_with_listed_share_changes += int(frame["ListedShares"].nunique(dropna=False) > 1)
        per_ticker[ticker] = {
            "rows": int(len(frame)),
            "min_date": mn,
            "max_date": mx,
            "zero_volume_rows": int(frame["Volume"].fillna(0).eq(0).sum()),
        }

    result.update(
        {
            "zero_volume_rows": zero_volume,
            "any_zero_ohlc_rows": any_zero_ohlc,
            "files_with_multiple_names": files_with_multiple_names,
            "files_with_listed_share_changes": files_with_listed_share_changes,
            "files_with_ticker_field_mismatch": ticker_field_mismatch,
            "per_ticker": per_ticker,
        }
    )
    return result, date_sets


def summarize_dataset_saham(root: Path) -> tuple[dict[str, Any], dict[str, set[str]]]:
    files = sorted(root.glob("*.csv"))
    result = _base_inventory(files)
    date_sets: dict[str, set[str]] = {}
    non_null_delisting = 0
    for path in files:
        frame = pd.read_csv(path, usecols=DATASET_SAHAM_COLUMNS, low_memory=False)
        parsed = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
        ticker = path.stem.upper()
        result["duplicate_key_rows"] += int(frame.duplicated(["date"]).sum())
        date_sets[ticker] = set(parsed.dt.strftime("%Y-%m-%d"))
        result["row_count"] += len(frame)
        mn = parsed.min().strftime("%Y-%m-%d")
        mx = parsed.max().strftime("%Y-%m-%d")
        result["min_date"] = mn if result["min_date"] is None or mn < result["min_date"] else result["min_date"]
        result["max_date"] = mx if result["max_date"] is None or mx > result["max_date"] else result["max_date"]
        non_null_delisting += int(frame["delisting_date"].notna().sum())
    result["non_null_delisting_date_cells"] = non_null_delisting
    return result, date_sets


def summarize_ipo(root: Path, information_path: Path) -> dict[str, Any]:
    information = json.loads(information_path.read_text(encoding="utf-8"))
    files = sorted(root.glob("*.json"))
    rows: dict[str, dict[str, Any]] = {}
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows[path.stem.upper()] = {
            "ipo_status": payload.get("ipo_status"),
            "company_name": payload.get("company_name"),
            "book_building_opening": payload.get("book_building_opening"),
            "book_building_closing": payload.get("book_building_closing"),
            "listing_date": payload.get("listing_date"),
        }
    return {
        "file_count": len(files),
        "ticker_count": len(rows),
        "updated_at": information.get("updated_at"),
        "declared_stock_count": information.get("count", {}).get("stocks"),
        "declared_new_stocks": sorted(str(value).upper() for value in information.get("new", {}).get("stocks", [])),
        "rows": rows,
    }


def exact_key_coverage(frame: pd.DataFrame, ticker_column: str, date_column: str, date_sets: dict[str, set[str]], cutoff: str | None = None) -> dict[str, Any]:
    work = frame[[ticker_column, date_column]].copy()
    work["ticker"] = work[ticker_column].astype("string").str.upper()
    work["date"] = pd.to_datetime(work[date_column], errors="raise").dt.strftime("%Y-%m-%d")
    if cutoff is not None:
        work = work[work["date"].le(cutoff)]
    found = sum(date in date_sets.get(ticker, set()) for ticker, date in zip(work["ticker"], work["date"], strict=True))
    missing = len(work) - found
    return {"rows": int(len(work)), "found": int(found), "missing": int(missing), "fraction": float(found / len(work)) if len(work) else None}


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    for path in (args.pholenk, args.dataset_saham, args.dataset_saham_listing, args.ipo_root, args.ipo_information, args.anchor, args.panel):
        if any(marker in str(path).lower() for marker in FORBIDDEN_MARKERS):
            raise ValueError(f"refusing protected-looking input path: {path}")

    pholenk, pholenk_dates = summarize_pholenk(args.pholenk)
    dataset_saham, dataset_saham_dates = summarize_dataset_saham(args.dataset_saham)
    ipo = summarize_ipo(args.ipo_root, args.ipo_information)
    listing = pd.read_csv(args.dataset_saham_listing)
    anchor = pd.read_csv(args.anchor, usecols=["ticker", "as_of_date", "state"])
    panel = pd.read_parquet(args.panel, columns=["ticker", "date"])
    ph_tickers = set(pholenk_dates)
    ds_tickers = set(dataset_saham_dates)
    anchor["as_of_date"] = pd.to_datetime(anchor["as_of_date"], errors="raise")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise")
    snapshot_date = pholenk["max_date"]
    cntx = pholenk["per_ticker"].get("CNTX", {})
    anchor_missing_from_pholenk = sorted(set(anchor["ticker"].astype("string").str.upper()) - ph_tickers)

    result: dict[str, Any] = {
        "status": "PASS_PUBLIC_SOURCE_COVERAGE_RESEARCH_ONLY",
        "scope": "Pinned public IDX-derived EOD snapshots; capability and authority-boundary research only",
        "protected_boundary": "CLOSED",
        "sources": {
            "pholenk_idx_dataset": {
                "repository": "https://github.com/Pholenk/IDX-Dataset",
                "commit": args.pholenk_commit,
                "tree": args.pholenk_tree,
                "metadata_sha256": sha256_file(args.pholenk_metadata),
                "inventory": _stored_inventory(pholenk),
                "ticker_count": len(ph_tickers),
                "authority_limits": [
                    "no row-level publication or available-at timestamp",
                    "no revision/vintage identifier or historical membership completeness contract",
                    "no issuer/ISIN continuity or corporate-action transition authority",
                ],
            },
            "dataset_saham_idx": {
                "repository": "https://github.com/wildangunawan/Dataset-Saham-IDX",
                "commit": args.dataset_saham_commit,
                "tree": args.dataset_saham_tree,
                "info_sha256": sha256_file(args.dataset_saham_info),
                "listing_metadata_sha256": sha256_file(args.dataset_saham_listing),
                "inventory": _stored_inventory(dataset_saham),
                "ticker_count": len(ds_tickers),
                "listing_metadata_rows": int(len(listing)),
                "has_cntx": "CNTX" in ds_tickers,
                "authority_limits": [
                    "metadata timestamp is not a row-level knowledge-time contract",
                    "no issuer/ISIN continuity or historical population completeness contract",
                    "delisting_date cells are empty in the acquired all-ticker surface",
                ],
            },
            "public_ipo_dataset": {
                "repository": "https://github.com/ricotandrio/web-indonesia-ipo-data",
                "commit": args.ipo_commit,
                "tree": args.ipo_tree,
                "information_sha256": sha256_file(args.ipo_information),
                "file_count": ipo["file_count"],
                "ticker_count": ipo["ticker_count"],
                "updated_at": ipo["updated_at"],
                "declared_new_stocks": ipo["declared_new_stocks"],
                "authority_limits": [
                    "IPO-only curated surface, not a population-wide security master",
                    "dataset update time is not row-level source publication or available-at authority",
                    "does not establish delisting, ticker reuse, issuer/ISIN continuity, or historical survivorship safety",
                ],
            },
        },
        "cross_source": {
            "ticker_intersection": len(ph_tickers & ds_tickers),
            "pholenk_only_tickers": sorted(ph_tickers - ds_tickers),
            "dataset_saham_only_tickers": sorted(ds_tickers - ph_tickers),
            "both_contain_cntx": "CNTX" in ph_tickers and "CNTX" in ds_tickers,
            "eod_snapshot_gap_tickers": anchor_missing_from_pholenk,
            "ipo_declared_new_gap_ticker_intersection": sorted(set(anchor_missing_from_pholenk) & set(ipo["declared_new_stocks"])),
            "ipo_declared_new_equals_eod_gap": set(anchor_missing_from_pholenk) == set(ipo["declared_new_stocks"]),
            "ipo_gap_ticker_details": {ticker: ipo["rows"].get(ticker) for ticker in anchor_missing_from_pholenk},
        },
        "frozen_surface_overlap": {
            "pholenk_snapshot_date": snapshot_date,
            "anchor_full": exact_key_coverage(anchor, "ticker", "as_of_date", pholenk_dates),
            "anchor_through_snapshot": exact_key_coverage(anchor, "ticker", "as_of_date", pholenk_dates, snapshot_date),
            "panel_full": exact_key_coverage(panel, "ticker", "date", pholenk_dates),
            "panel_through_snapshot": exact_key_coverage(panel, "ticker", "date", pholenk_dates, snapshot_date),
            "anchor_tickers_missing_from_pholenk": anchor_missing_from_pholenk,
            "panel_tickers_missing_from_pholenk": sorted(set(panel["ticker"].astype("string").str.upper()) - ph_tickers),
        },
        "cntx": {
            "pholenk": cntx,
            "anchor_rows": int(anchor[anchor["ticker"].astype("string").str.upper().eq("CNTX")].shape[0]),
            "anchor_active_rows": int(anchor[anchor["ticker"].astype("string").str.upper().eq("CNTX") & anchor["state"].eq("ACTIVE")].shape[0]),
            "anchor_no_trade_rows": int(anchor[anchor["ticker"].astype("string").str.upper().eq("CNTX") & anchor["state"].eq("NO_TRADE")].shape[0]),
            "interpretation": "CNTX is discoverable in both public snapshots; this disproves only the stronger claim that the panel-absent ticker is absent from every available public EOD source. It does not prove population completeness, PIT eligibility, issuer continuity, or survivorship safety.",
        },
        "admission": {
            "historical_population_completeness": "UNKNOWN",
            "survivorship_safety": "UNKNOWN",
            "pit_available_at_authority": "MISSING",
            "identity_issuer_isin_authority": "MISSING",
            "corporate_action_basis_authority": "MISSING",
            "historical_research_admission": "BLOCKED",
        },
        "inputs": {
            "anchor": {"path": str(args.anchor), "sha256": sha256_file(args.anchor), "rows": int(len(anchor))},
            "panel": {"path": str(args.panel), "sha256": sha256_file(args.panel), "rows": int(len(panel))},
        },
    }
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pholenk", type=Path, required=True)
    parser.add_argument("--pholenk-metadata", type=Path, required=True)
    parser.add_argument("--pholenk-commit", required=True)
    parser.add_argument("--pholenk-tree", required=True)
    parser.add_argument("--dataset-saham", type=Path, required=True)
    parser.add_argument("--dataset-saham-info", type=Path, required=True)
    parser.add_argument("--dataset-saham-listing", type=Path, required=True)
    parser.add_argument("--dataset-saham-commit", required=True)
    parser.add_argument("--dataset-saham-tree", required=True)
    parser.add_argument("--ipo-root", type=Path, required=True)
    parser.add_argument("--ipo-information", type=Path, required=True)
    parser.add_argument("--ipo-commit", required=True)
    parser.add_argument("--ipo-tree", required=True)
    parser.add_argument("--anchor", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
