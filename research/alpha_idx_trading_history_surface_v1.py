"""Acquire and audit official IDX per-security trading history.

The endpoint is public and returns daily OHLCV, foreign buy/sell shares,
listed/tradable shares, and notation fields.  This module preserves raw JSON
responses under the external alpha staging root and never writes canonical
data or protected outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


STAGING_MARKER = "idx-alpha-available-data-staging-20260919"
BASE_URL = "https://www.idx.id/"
ENDPOINT = "https://www.idx.id/primary/ListedCompany/GetTradingInfoSS"
TICKER_RE = re.compile(r"^[A-Z0-9]{4,5}$")
REQUIRED_FIELDS = {
    "Date",
    "StockCode",
    "Previous",
    "OpenPrice",
    "High",
    "Low",
    "Close",
    "Volume",
    "Value",
    "Frequency",
    "ListedShares",
    "TradebleShares",
    "ForeignBuy",
    "ForeignSell",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover_codes(codes_dir: Path) -> list[str]:
    codes = sorted({path.stem.upper() for path in codes_dir.glob("*.csv")})
    if not codes or any(not TICKER_RE.fullmatch(code) for code in codes):
        raise ValueError(f"no clean ticker CSV inventory found under {codes_dir}")
    return codes


def _parse_response(path: Path) -> tuple[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("replies"), list):
        raise ValueError(f"unexpected trading response shape: {path}")
    code = str(payload.get("KodeEmiten") or "").strip().upper()
    rows = [row for row in payload["replies"] if isinstance(row, dict)]
    return code, rows


def audit_raw_file(path: Path) -> dict[str, Any]:
    code, rows = _parse_response(path)
    dates = [str(row["Date"])[:10] for row in rows if row.get("Date")]
    parsed_dates = sorted(datetime.strptime(value, "%Y-%m-%d").date() for value in dates)
    missing_fields = sum(
        1 for row in rows if not REQUIRED_FIELDS.issubset(set(row))
    )
    def count_zero(field: str) -> int:
        return sum(1 for row in rows if row.get(field) in (0, 0.0, None, ""))

    return {
        "path": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "code": code,
        "rows": len(rows),
        "unique_dates": len(set(dates)),
        "duplicate_date_rows": len(rows) - len(set(dates)),
        "date_min": parsed_dates[0].isoformat() if parsed_dates else None,
        "date_max": parsed_dates[-1].isoformat() if parsed_dates else None,
        "missing_required_field_rows": missing_fields,
        "zero_open_rows": count_zero("OpenPrice"),
        "zero_high_rows": count_zero("High"),
        "zero_low_rows": count_zero("Low"),
        "zero_close_rows": count_zero("Close"),
        "zero_volume_rows": count_zero("Volume"),
        "foreign_nonzero_rows": sum(
            1
            for row in rows
            if (row.get("ForeignBuy") or 0) != 0 or (row.get("ForeignSell") or 0) != 0
        ),
        "listed_shares_distinct": len({row.get("ListedShares") for row in rows}),
        "tradable_shares_distinct": len({row.get("TradebleShares") for row in rows}),
        "nonempty_delisting_date_rows": sum(bool(row.get("DelistingDate")) for row in rows),
        "nonempty_remarks_rows": sum(bool(row.get("Remarks")) for row in rows),
        "response_ticker": code,
    }


def summarize_raw(raw_root: Path) -> dict[str, Any]:
    files = sorted(raw_root.glob("*.json"))
    if not files:
        raise ValueError(f"no trading-history raw JSON files found under {raw_root}")
    records = [audit_raw_file(path) for path in files]
    status_counts = Counter("VALID" if item["missing_required_field_rows"] == 0 else "FIELD_GAPS" for item in records)
    dates = [item["date_min"] for item in records if item["date_min"]]
    ends = [item["date_max"] for item in records if item["date_max"]]
    return {
        "schema_version": "1.0",
        "status": "PASS_IDX_TRADING_HISTORY_SURFACE_RESEARCH_ONLY",
        "scope": "Official IDX per-security trading history; raw coverage and field semantics only",
        "source": {
            "base_url": BASE_URL,
            "endpoint": ENDPOINT,
            "query_contract": "code=<ticker>&start=0&length=1000000",
            "pagination_observation": "bounded probes returned identical bodies for nonzero start values; length=1000000 returned the full observed history",
        },
        "raw_files": len(records),
        "raw_rows": sum(item["rows"] for item in records),
        "unique_codes": len({item["code"] for item in records if item["code"]}),
        "date_min": min(dates) if dates else None,
        "date_max": max(ends) if ends else None,
        "status_counts": dict(sorted(status_counts.items())),
        "zero_volume_rows": sum(item["zero_volume_rows"] for item in records),
        "foreign_nonzero_rows": sum(item["foreign_nonzero_rows"] for item in records),
        "codes_with_multiple_listed_share_values": sum(item["listed_shares_distinct"] > 1 for item in records),
        "codes_with_delisting_date": sum(item["nonempty_delisting_date_rows"] > 0 for item in records),
        "records": records,
        "what_is_proven": [
            "The official endpoint returns daily per-security rows with OHLCV, foreign buy/sell shares, listed/tradable shares, and a remarks/notation field.",
            "The bounded full-history query can return more than 1,000 rows and reached 2020-01-02 for the tested BBCA and CNTX securities.",
            "Zero-volume and zero-open rows occur in the raw feed and must not be silently converted into missing or tradable observations.",
        ],
        "what_remains_unknown": [
            "historical population completeness and survivorship safety",
            "issuer/ISIN continuity and ticker reuse",
            "adjusted versus unadjusted price-basis semantics and corporate-action transitions",
            "row publication/available-at and revision/vintage semantics",
            "whether a zero-volume row represents a suspension, no trade, or another exchange state",
        ],
        "admission": {
            "raw_coverage": "SUPPORTED_BOUNDED_ACQUISITION",
            "historical_research_admission": "BLOCKED",
            "allowed_use": "coverage recovery, structural field audit, and source reconciliation",
            "forbidden_use": "population-complete PIT substitution, lifecycle inference from ticker/date alone, or price-basis repair",
        },
        "protected_boundary": "CLOSED",
    }


def acquire(
    codes: list[str],
    raw_root: Path,
    *,
    limit: int | None,
    delay_seconds: float,
) -> dict[str, Any]:
    if delay_seconds < 0.1:
        raise ValueError("delay_seconds must be at least 0.1")
    raw_root.mkdir(parents=True, exist_ok=True)
    requested = codes[:limit] if limit is not None else codes
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Referer": BASE_URL,
            "User-Agent": "idx-trade-research-acquisition/1.0",
            "X-Requested-With": "XMLHttpRequest",
        }
    )
    records: list[dict[str, Any]] = []
    for code in requested:
        destination = raw_root / f"{code}.json"
        record: dict[str, Any] = {"code": code, "path": destination.name}
        try:
            if destination.exists():
                audit = audit_raw_file(destination)
                record.update({"status": "REUSED_EXISTING", "audit": audit})
            else:
                response = session.get(
                    ENDPOINT,
                    params={"code": code, "start": 0, "length": 1000000},
                    timeout=90,
                )
                record["http_status"] = response.status_code
                if response.status_code != 200:
                    record["status"] = "HTTP_FAILURE"
                else:
                    payload = response.json()
                    if not isinstance(payload, dict) or not isinstance(payload.get("replies"), list):
                        raise ValueError("unexpected trading response shape")
                    destination.write_bytes(response.content)
                    record.update({"status": "DOWNLOADED", "audit": audit_raw_file(destination)})
        except Exception as exc:  # acquisition failure is recorded, never fabricated as data
            record.update({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
        records.append(record)
        time.sleep(delay_seconds)
    return {
        "requested": len(requested),
        "status_counts": dict(sorted(Counter(item["status"] for item in records).items())),
        "records": records,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    raw_root = args.raw_root.resolve()
    if STAGING_MARKER not in str(output) or STAGING_MARKER not in str(raw_root):
        raise ValueError("refusing output outside isolated alpha staging")
    result: dict[str, Any] = {
        "codes_source": str(args.codes_dir.resolve()),
        "codes_source_files": len(list(args.codes_dir.glob("*.csv"))),
    }
    if args.acquire:
        result["acquisition"] = acquire(
            discover_codes(args.codes_dir),
            raw_root,
            limit=args.limit,
            delay_seconds=args.delay_seconds,
        )
    result.update(summarize_raw(raw_root))
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codes-dir", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
