"""Outcome-blind audit of newly recovered free historical authority surfaces.

The audit is deliberately bounded.  It fingerprints locally retained public
artifacts, parses only identity/event metadata, and compares one public mirror
with an existing local CNTX file.  It never writes project data or promotes a
source into PIT/admission authority.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def parse_ksei_deflist(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    fields: dict[str, str] = {}
    for match in re.finditer(r"<dt>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", text, re.I | re.S):
        fields[_clean_html(match.group(1))] = _clean_html(match.group(2))
    return fields


def parse_ksei_archive(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    years = [int(value) for value in re.findall(r'<option value="(20\d{2})"', text)]
    dates = re.findall(r'<small[^>]*><b>([^<]+)</b></small>', text, re.I)
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "announcement_headers": len(re.findall(r'<h2 class="h4 no-margin">', text)),
        "new_isin_notices": len(re.findall(r"Announcement of New Isin Code|Pengumuman Kode Isin Baru", text, re.I)),
        "dated_notices": len(dates),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "year_option_min": min(years) if years else None,
        "year_option_max": max(years) if years else None,
    }


def parse_ksei_shares(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    codes = sorted(set(re.findall(r"/services/registered-securities/shares/lc/([A-Z0-9]+)", text)))
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "unique_codes": len(codes),
        "contains_cntx": "CNTX" in codes,
        "contains_cntb": "CNTB" in codes,
        "contains_emtk": "EMTK" in codes,
    }


def parse_cntx_anchor(path: Path) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("ticker", "").upper() == "CNTX":
                rows.append(row)
    active = [row for row in rows if row.get("state") == "ACTIVE"]
    return {
        "rows": len(rows),
        "active_rows": len(active),
        "no_trade_rows": sum(row.get("state") == "NO_TRADE" for row in rows),
        "active_min": min((row["as_of_date"] for row in active), default=None),
        "active_max": max((row["as_of_date"] for row in active), default=None),
        "all_min": min((row["as_of_date"] for row in rows), default=None),
        "all_max": max((row["as_of_date"] for row in rows), default=None),
    }


def parse_json_trading(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("replies", [])
    dates = [str(row["Date"])[:10] for row in rows if row.get("Date")]
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "rows": len(rows),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "nonzero_volume_rows": sum(float(row.get("Volume") or 0) != 0 for row in rows),
    }


def compare_cntx_csvs(mirror: Path, local: Path) -> dict[str, Any]:
    with mirror.open(encoding="utf-8-sig", newline="") as handle:
        mirror_rows = list(csv.DictReader(handle))
    with local.open(encoding="utf-8", newline="") as handle:
        local_rows = {row["date"]: row for row in csv.DictReader(handle)}
    fields = [("Previous", "previous"), ("Open", "open_price"), ("High", "high"), ("Low", "low"),
              ("Close", "close"), ("Volume", "volume"), ("Value", "value"), ("Frequency", "frequency"),
              ("ListedShares", "listed_shares"), ("TradebleShares", "tradeble_shares")]
    mismatches = {left: 0 for left, _ in fields}
    common = 0
    for row in mirror_rows:
        old = local_rows.get(row.get("Date", ""))
        if old is None:
            continue
        common += 1
        for left, right in fields:
            if float(row[left]) != float(old[right]):
                mismatches[left] += 1
    dates = [row["Date"] for row in mirror_rows]
    return {
        "mirror_rows": len(mirror_rows),
        "local_rows": len(local_rows),
        "mirror_min": min(dates) if dates else None,
        "mirror_max": max(dates) if dates else None,
        "common_date_rows": common,
        "field_mismatch_counts": mismatches,
        "mirror_has_delisting_date": "DelistingDate" in (mirror_rows[0] if mirror_rows else {}),
        "mirror_sha256": sha256_file(mirror),
        "local_sha256": sha256_file(local),
    }


def audit(staging_root: Path, anchor: Path) -> dict[str, Any]:
    free_root = staging_root / "public-source-probes/free-authority-research"
    ksei = free_root / "20260920-ksei-ojk-idx"
    issuer = free_root / "20260920-issuer-ir"
    github = free_root / "20260920-github"
    cntx_page = parse_ksei_deflist(ksei / "ksei-cntx.html")
    emtk_page = parse_ksei_deflist(ksei / "ksei-emtk.html")
    archive_2021 = parse_ksei_archive(ksei / "ksei-isin-2021-01.html")
    archive_2019 = parse_ksei_archive(ksei / "ksei-isin-2019-01.html")
    shares = parse_ksei_shares(ksei / "ksei-shares-list.html")
    anchor_stats = parse_cntx_anchor(anchor)
    trading = parse_json_trading(staging_root / "public-source-probes/idx-trading-routes/2026-09-20__cntx-trading-ss-length1000000.raw")
    comparison = compare_cntx_csvs(
        github / "pholenk-CNTX.csv",
        staging_root / "public-source-probes/dataset-saham-idx/Saham/Semua/CNTX.csv",
    )
    issuer_years = []
    for path in sorted(issuer.glob("centex-20??.html")):
        if re.fullmatch(r"centex-20\d{2}\.html", path.name):
            issuer_years.append(int(path.stem.split("-")[-1]))
    checks = {
        "ksei_current_shares_is_bounded_snapshot": shares["unique_codes"] == 984,
        "ksei_cntx_direct_fetch_fails_closed": cntx_page.get("Status") == "UNKNOWN ()" and cntx_page.get("Type", "").startswith("UNDEFINED"),
        "ksei_populated_sample_has_identity_fields": emtk_page.get("Short Code") == "EMTK" and emtk_page.get("ISIN Code") == "ID1000113905",
        "ksei_historical_archive_queries_are_nonempty": archive_2021["new_isin_notices"] == 52 and archive_2019["new_isin_notices"] == 110,
        "cntx_anchor_active_count": anchor_stats["active_rows"] == 458,
        "cntx_trading_history_is_nonempty": trading["rows"] == 1581,
        "github_overlap_has_no_numeric_mismatches": comparison["common_date_rows"] == 1243 and not any(comparison["field_mismatch_counts"].values()),
        "issuer_archive_has_bounded_year_pages": set(range(2013, 2022)).issubset(set(issuer_years)),
    }
    return {
        "schema_version": "1.0",
        "status": "PASS_FREE_AUTHORITY_SURFACE_AUDIT" if all(checks.values()) else "FAIL_FREE_AUTHORITY_SURFACE_AUDIT",
        "scope": "Free/public historical authority recovery; outcome-blind capability and bounded identity/CA evidence only",
        "protected_boundary": "CLOSED",
        "checks": checks,
        "ksei": {"shares_snapshot": shares, "cntx_direct_page": cntx_page, "emtk_direct_page": emtk_page, "isin_2021_01": archive_2021, "isin_2019_01": archive_2019},
        "cntx": {"anchor": anchor_stats, "official_trading": trading, "github_vs_local": comparison},
        "issuer_ir": {"year_pages": issuer_years, "financial_statement_pdf_sha256": sha256_file(issuer / "centex-2021-financial-statements-1.pdf")},
        "interpretation": {
            "cntx_population": "The observed panel is incomplete as a population enumerator: CNTX has zero panel rows but 458 ACTIVE anchor rows and official trading-history rows. This disproves panel-absence-as-population-absence, not the reverse claim that the anchor is population-complete.",
            "cntx_identity": "KSEI search evidence and the issuer financial statement distinguish CNTX Series A preference security from CNTB Series B common security. A ticker-only universe can therefore conflate security class and issuer identity.",
            "ksei_authority": "KSEI is a useful bounded security/ISIN/corporate-action source. Historical filtered notices and security pages do not establish daily exchange eligibility, publication/knowledge time, revision lineage, or complete historical population.",
            "issuer_authority": "The issuer archive provides bounded annual-report and historical share-structure evidence, including series/listing/split history, but report availability time and population-wide membership remain unresolved.",
            "mirror_authority": "The GitHub mirror reproduces overlapping CNTX numeric fields exactly against the local public dataset for 1,243 dates, but it is a derived mirror without independent PIT, delisting, issuer/ISIN, revision, or admission authority.",
        },
        "admission": {
            "historical_population_completeness": "MISSING",
            "daily_pit_eligibility": "MISSING",
            "issuer_isin_security_continuity": "BOUNDED_FOR_CNTX_SAMPLE_ONLY",
            "bounded_corporate_action_transition": "SUPPORTED_FOR_SAMPLED_CNTX_CARECORDS_ONLY",
            "financial_publication_vintage": "MISSING",
            "historical_research_admission": "BLOCKED",
        },
        "network_used_by_audit": False,
        "canonical_mutation": False,
        "provider_called_by_audit": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--anchor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.staging_root, args.anchor)
    if "idx-alpha-available-data-staging-20260919" not in str(args.output):
        raise ValueError("refusing output outside isolated alpha staging")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS_FREE_AUTHORITY_SURFACE_AUDIT":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
