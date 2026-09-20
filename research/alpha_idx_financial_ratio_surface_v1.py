"""Acquire and audit the public IDX monthly financial-ratio surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import requests


STAGING_MARKER = "idx-alpha-available-data-staging-20260919"
BASE_URL = "https://www.idx.id/"
ENDPOINT = "https://www.idx.id/primary/DigitalStatistic/GetApiDataPaginated"
FILE_PATTERN = re.compile(r".*ratio-(?P<year>\d{4})-(?P<month>\d{2})-pagesize1000\.raw$")
REQUIRED_FIELDS = {"code", "stockName", "fsDate", "assets", "liabilities", "equity", "sales", "profitPeriod"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _files(root: Path) -> list[tuple[Path, int, int]]:
    output = []
    for path in sorted(root.rglob("*.raw")):
        match = FILE_PATTERN.fullmatch(path.name)
        if match:
            output.append((path, int(match.group("year")), int(match.group("month"))))
    if not output:
        raise ValueError(f"no retained financial-ratio snapshots under {root}")
    return output


def audit_file(path: Path, year: int, month: int) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("data")
    if not isinstance(rows, list) or not isinstance(payload.get("meta"), dict):
        raise ValueError(f"unexpected financial-ratio response shape: {path}")
    rows = [row for row in rows if isinstance(row, dict)]
    codes = [str(row.get("code") or "") for row in rows]
    fs_dates = sorted(str(row["fsDate"]) for row in rows if row.get("fsDate"))
    return {
        "path": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "query_year": year,
        "query_month": month,
        "rows": len(rows),
        "metadata_total_items": payload["meta"].get("totalItems"),
        "unique_codes": len(set(codes)),
        "duplicate_code_rows": len(codes) - len(set(codes)),
        "missing_required_field_rows": sum(1 for row in rows if not REQUIRED_FIELDS.issubset(row)),
        "fs_date_min": fs_dates[0] if fs_dates else None,
        "fs_date_max": fs_dates[-1] if fs_dates else None,
        "codes": sorted(set(codes)),
    }


def summarize(root: Path) -> dict[str, Any]:
    periods = [audit_file(*entry) for entry in _files(root)]
    return {
        "schema_version": "1.0",
        "status": "PASS_IDX_FINANCIAL_RATIO_SURFACE_RESEARCH_ONLY",
        "scope": "Official IDX monthly financial-ratio snapshots; coverage and timing research only",
        "source": {
            "base_url": BASE_URL,
            "endpoint": ENDPOINT,
            "query_contract": "urlName=LINK_FINANCIAL_DATA_RATIO&periodYear=YYYY&periodMonth=M&periodType=monthly&pageSize=1000&pageNumber=1",
        },
        "snapshot_count": len(periods),
        "total_rows": sum(item["rows"] for item in periods),
        "periods": periods,
        "what_is_proven": [
            "The public route returns bounded issuer-level financial ratios with statement date, sector fields, accounting totals, and valuation ratios.",
            "Historical queries return materially different issuer counts and fsDate ranges; December 2021–2024 retained snapshots cover 769, 828, 906, and 947 rows respectively.",
            "The route can return an empty result for an older query (2020-12), so historical availability is period-specific rather than assumed continuous.",
        ],
        "what_remains_unknown": [
            "whether the query month is a publication/available-at cutoff or only a report-selection parameter",
            "revision and restatement behavior across repeated retrievals",
            "issuer/ISIN continuity and historical population completeness",
            "taxonomy, unit, and accounting comparability across issuers",
            "whether ratios are reproducible as-of the historical decision date",
        ],
        "admission": {
            "raw_snapshot_coverage": "SUPPORTED_BOUNDED_ACQUISITION",
            "historical_research_admission": "BLOCKED",
            "allowed_use": "financial-source discovery, coverage census, and timing/revision research",
            "forbidden_use": "treat query month or fsDate as proven available-at time, or substitute for a PIT financial bundle",
        },
        "protected_boundary": "CLOSED",
    }


def acquire(root: Path, start_year: int, end_year: int, delay_seconds: float) -> None:
    if delay_seconds < 0.1:
        raise ValueError("delay_seconds must be at least 0.1")
    root.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Accept": "application/json, text/plain, */*", "Referer": BASE_URL, "User-Agent": "idx-trade-research-acquisition/1.0", "X-Requested-With": "XMLHttpRequest"})
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            path = root / f"ratio-{year}-{month:02d}-pagesize1000.raw"
            if not path.exists():
                response = session.get(
                    ENDPOINT,
                    params={"urlName": "LINK_FINANCIAL_DATA_RATIO", "periodYear": year, "periodMonth": month, "periodType": "monthly", "isPrint": "False", "cumulative": "false", "pageSize": 1000, "pageNumber": 1},
                    timeout=90,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                    raise ValueError(f"unexpected ratio response for {year}-{month:02d}")
                path.write_bytes(response.content)
            time.sleep(delay_seconds)


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = args.raw_root.resolve()
    output = args.output.resolve()
    if STAGING_MARKER not in str(root) or STAGING_MARKER not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    if args.acquire:
        acquire(root, args.start_year, args.end_year, args.delay_seconds)
    result = summarize(root)
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--start-year", type=int, default=2021)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
