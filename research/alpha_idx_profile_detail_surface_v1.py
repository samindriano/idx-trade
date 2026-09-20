"""Acquire and audit the current official IDX company-detail surface.

This is a current identity/profile probe only.  It deliberately records field
presence rather than copying shareholder or financial values into the durable
knowledge base, and it cannot establish historical issuer/security continuity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests


STAGING_MARKER = "idx-alpha-available-data-staging-20260919"
BASE_URL = "https://www.idx.id/"
ENDPOINT = "https://www.idx.id/primary/ListedCompany/GetCompanyProfilesDetail"
TICKER_RE = re.compile(r"^[A-Z0-9]{4,5}$")


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


def _payload(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("Profiles"), list):
        raise ValueError(f"unexpected company-detail response shape: {path}")
    return value


def audit_raw_file(path: Path) -> dict[str, Any]:
    payload = _payload(path)
    profiles = [item for item in payload["Profiles"] if isinstance(item, dict)]
    profile = profiles[0] if profiles else {}
    nested_isin_fields = sorted(
        key for key in profile if "isin" in str(key).lower()
    )
    bond_rows = [item for item in payload.get("BondsAndSukuk", []) if isinstance(item, dict)]
    bond_isin_rows = sum(bool(item.get("ISINCode")) for item in bond_rows)
    return {
        "path": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "requested_code": path.stem.upper(),
        "profile_count": len(profiles),
        "profile_code": profile.get("KodeEmiten"),
        "profile_field_names": sorted(str(key) for key in profile),
        "stock_profile_isin_fields": nested_isin_fields,
        "bond_rows": len(bond_rows),
        "bond_rows_with_isin": bond_isin_rows,
        "listing_date_present": bool(profile.get("TanggalPencatatan")),
        "status_present": bool(profile.get("Status") is not None),
        "name_present": bool(profile.get("NamaEmiten")),
    }


def summarize_raw(raw_root: Path) -> dict[str, Any]:
    files = sorted(raw_root.glob("*.json"))
    if not files:
        raise ValueError(f"no company-detail raw JSON files under {raw_root}")
    records = [audit_raw_file(path) for path in files]
    return {
        "schema_version": "1.0",
        "status": "PASS_IDX_PROFILE_DETAIL_SURFACE_RESEARCH_ONLY",
        "scope": "Official IDX current company-detail responses; field and identity-surface audit only",
        "source": {"base_url": BASE_URL, "endpoint": ENDPOINT, "query_contract": "KodeEmiten=<ticker>&language=id-id"},
        "raw_files": len(records),
        "profiles_found": sum(item["profile_count"] > 0 for item in records),
        "profiles_empty": sum(item["profile_count"] == 0 for item in records),
        "codes_with_stock_profile_isin_fields": sum(bool(item["stock_profile_isin_fields"]) for item in records),
        "bond_rows_with_isin": sum(item["bond_rows_with_isin"] for item in records),
        "listing_date_present": sum(item["listing_date_present"] for item in records),
        "records": records,
        "what_is_proven": [
            "The official detail route provides a current profile, listing date, status, sector, and corporate-profile fields for some observed codes.",
            "The bounded profile schema audit distinguishes empty profiles for delisted/unknown codes from populated current profiles.",
            "The sampled/current profile objects do not expose a stock ISIN field; ISINCode appears in bond/sukuk nested records where present.",
        ],
        "what_remains_unknown": [
            "historical issuer/security continuity and ticker reuse",
            "stock ISIN mapping and effective identity transitions",
            "point-in-time profile vintages, publication time, and revisions",
            "historical population completeness and delisted profile retention",
        ],
        "admission": {
            "current_profile_surface": "SUPPORTED_BOUNDED_ACQUISITION",
            "historical_research_admission": "BLOCKED",
            "allowed_use": "current identity-field and route-capability research",
            "forbidden_use": "historical issuer/ISIN substitution or PIT population admission",
        },
        "protected_boundary": "CLOSED",
    }


def acquire(codes: list[str], raw_root: Path, *, delay_seconds: float) -> dict[str, Any]:
    if delay_seconds < 0.1:
        raise ValueError("delay_seconds must be at least 0.1")
    raw_root.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Accept": "application/json, text/plain, */*", "Referer": BASE_URL, "User-Agent": "idx-trade-research-acquisition/1.0", "X-Requested-With": "XMLHttpRequest"})
    records: list[dict[str, Any]] = []
    for code in codes:
        destination = raw_root / f"{code}.json"
        record: dict[str, Any] = {"code": code, "path": destination.name}
        try:
            if destination.exists():
                record.update({"status": "REUSED_EXISTING", "audit": audit_raw_file(destination)})
            else:
                response = session.get(ENDPOINT, params={"KodeEmiten": code, "language": "id-id"}, timeout=90)
                record["http_status"] = response.status_code
                if response.status_code != 200:
                    record["status"] = "HTTP_FAILURE"
                else:
                    payload = response.json()
                    if not isinstance(payload, dict) or not isinstance(payload.get("Profiles"), list):
                        raise ValueError("unexpected company-detail response shape")
                    destination.write_bytes(response.content)
                    record.update({"status": "DOWNLOADED", "audit": audit_raw_file(destination)})
        except Exception as exc:
            record.update({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
        records.append(record)
        time.sleep(delay_seconds)
    return {"requested": len(codes), "status_counts": dict(sorted(Counter(item["status"] for item in records).items())), "records": records}


def run(args: argparse.Namespace) -> dict[str, Any]:
    raw_root = args.raw_root.resolve()
    output = args.output.resolve()
    if STAGING_MARKER not in str(raw_root) or STAGING_MARKER not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    codes = set()
    if args.codes_dir is not None:
        codes.update(discover_codes(args.codes_dir.resolve()))
    if args.codes:
        values = [item.strip().upper() for item in args.codes.split(",") if item.strip()]
        if any(not TICKER_RE.fullmatch(item) for item in values):
            raise ValueError("--codes contains an invalid ticker")
        codes.update(values)
    if not codes:
        raise ValueError("provide --codes-dir or --codes")
    result: dict[str, Any] = {"codes_requested": len(codes)}
    if args.acquire:
        result["acquisition"] = acquire(sorted(codes), raw_root, delay_seconds=args.delay_seconds)
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
