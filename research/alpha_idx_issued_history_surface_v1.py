"""Acquire and audit the public IDX issued-history event surface.

This lane preserves the official per-ticker issuance/action history as raw
evidence.  It intentionally does not infer a complete daily lifecycle, issuer
continuity, or an exchange-effective corporate-action price basis from event
rows.
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
ENDPOINT = "https://www.idx.id/primary/ListingActivity/GetIssuedHistory"
TICKER_RE = re.compile(r"^[A-Z0-9]{4,5}$")
REQUIRED_FIELDS = {"KodeEmiten", "TanggalPencatatan", "JenisTindakan"}


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


def parse_codes(value: str | None) -> list[str]:
    if not value:
        return []
    codes = sorted({item.strip().upper() for item in value.split(",") if item.strip()})
    if any(not TICKER_RE.fullmatch(code) for code in codes):
        raise ValueError("--codes contains an invalid ticker")
    return codes


def _payload(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("data"), list):
        raise ValueError(f"unexpected issued-history response shape: {path}")
    return value


def audit_raw_file(path: Path) -> dict[str, Any]:
    payload = _payload(path)
    rows = [row for row in payload["data"] if isinstance(row, dict)]
    requested_code = path.stem.upper()
    dates = [str(row["TanggalPencatatan"])[:10] for row in rows if row.get("TanggalPencatatan")]
    parsed_dates = sorted(datetime.strptime(value, "%Y-%m-%d").date() for value in dates)
    action_counts = Counter(str(row.get("JenisTindakan") or "").strip() for row in rows)
    row_codes = sorted({str(row.get("KodeEmiten") or "").strip().upper() for row in rows if row.get("KodeEmiten")})
    return {
        "path": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "requested_code": requested_code,
        "rows": len(rows),
        "records_total": payload.get("recordsTotal"),
        "date_min": parsed_dates[0].isoformat() if parsed_dates else None,
        "date_max": parsed_dates[-1].isoformat() if parsed_dates else None,
        "missing_required_field_rows": sum(1 for row in rows if not REQUIRED_FIELDS.issubset(row)),
        "row_codes": row_codes,
        "code_mismatch_rows": sum(
            1 for row in rows if str(row.get("KodeEmiten") or "").strip().upper() not in {requested_code}
        ),
        "action_counts": dict(sorted(action_counts.items())),
    }


def summarize_raw(raw_root: Path) -> dict[str, Any]:
    files = sorted(raw_root.glob("*.json"))
    if not files:
        raise ValueError(f"no issued-history raw JSON files found under {raw_root}")
    records = [audit_raw_file(path) for path in files]
    dates = [item["date_min"] for item in records if item["date_min"]]
    ends = [item["date_max"] for item in records if item["date_max"]]
    action_counts = Counter()
    for item in records:
        action_counts.update(item["action_counts"])
    return {
        "schema_version": "1.0",
        "status": "PASS_IDX_ISSUED_HISTORY_SURFACE_RESEARCH_ONLY",
        "scope": "Official IDX per-ticker issuance/action history; event coverage only",
        "source": {
            "base_url": BASE_URL,
            "endpoint": ENDPOINT,
            "query_contract": "kodeEmiten=<ticker>",
        },
        "raw_files": len(records),
        "raw_rows": sum(item["rows"] for item in records),
        "nonempty_history_codes": sum(item["rows"] > 0 for item in records),
        "empty_history_codes": sum(item["rows"] == 0 for item in records),
        "date_min": min(dates) if dates else None,
        "date_max": max(ends) if ends else None,
        "missing_required_field_rows": sum(item["missing_required_field_rows"] for item in records),
        "code_mismatch_rows": sum(item["code_mismatch_rows"] for item in records),
        "action_counts": dict(sorted(action_counts.items())),
        "records": records,
        "what_is_proven": [
            "The official route returns structured per-ticker issuance/action rows with action type, date, share-count, and status fields when present.",
            "The route can return delisting and partial-delisting rows for securities that are not in the current company directory.",
            "Empty responses are retained as bounded source observations rather than treated as proof that no historical event existed.",
        ],
        "what_remains_unknown": [
            "complete historical event-index coverage and query completeness",
            "issuer/ISIN continuity, ticker reuse, and security replacement semantics",
            "exchange-effective trading transition and first-session price basis",
            "publication/knowledge time, revision, and correction lineage",
            "whether an empty history reflects no event, source truncation, or route coverage limits",
        ],
        "admission": {
            "raw_event_coverage": "SUPPORTED_BOUNDED_ACQUISITION",
            "historical_research_admission": "BLOCKED",
            "allowed_use": "event discovery, source reconciliation, and lifecycle-contract design",
            "forbidden_use": "complete PIT universe, issuer continuity, or price-basis repair from event rows alone",
        },
        "protected_boundary": "CLOSED",
    }


def acquire(codes: list[str], raw_root: Path, *, delay_seconds: float) -> dict[str, Any]:
    if delay_seconds < 0.1:
        raise ValueError("delay_seconds must be at least 0.1")
    raw_root.mkdir(parents=True, exist_ok=True)
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
    for code in codes:
        destination = raw_root / f"{code}.json"
        record: dict[str, Any] = {"code": code, "path": destination.name}
        try:
            if destination.exists():
                record.update({"status": "REUSED_EXISTING", "audit": audit_raw_file(destination)})
            else:
                response = session.get(ENDPOINT, params={"kodeEmiten": code}, timeout=90)
                record["http_status"] = response.status_code
                if response.status_code != 200:
                    record["status"] = "HTTP_FAILURE"
                else:
                    payload = response.json()
                    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                        raise ValueError("unexpected issued-history response shape")
                    destination.write_bytes(response.content)
                    record.update({"status": "DOWNLOADED", "audit": audit_raw_file(destination)})
        except Exception as exc:  # bounded acquisition records failure, never fabricates success
            record.update({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
        records.append(record)
        time.sleep(delay_seconds)
    return {
        "requested": len(codes),
        "status_counts": dict(sorted(Counter(item["status"] for item in records).items())),
        "records": records,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    raw_root = args.raw_root.resolve()
    output = args.output.resolve()
    if STAGING_MARKER not in str(raw_root) or STAGING_MARKER not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    codes = set(parse_codes(args.codes))
    if args.codes_dir is not None:
        codes.update(discover_codes(args.codes_dir.resolve()))
    if not codes:
        raise ValueError("provide --codes-dir or --codes")
    ordered_codes = sorted(codes)
    result: dict[str, Any] = {
        "codes_requested": len(ordered_codes),
        "codes_source_dir": str(args.codes_dir.resolve()) if args.codes_dir else None,
    }
    if args.acquire:
        result["acquisition"] = acquire(ordered_codes, raw_root, delay_seconds=args.delay_seconds)
    result.update(summarize_raw(raw_root))
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codes-dir", type=Path)
    parser.add_argument("--codes")
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
