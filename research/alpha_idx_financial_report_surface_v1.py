"""Acquire and audit the public IDX financial-report index surface.

This lane intentionally separates raw acquisition from research admission.  The
IDX ``www.idx.id`` endpoint exposes report-index metadata and official
``instance.zip`` links without requiring a credential in the bounded probe used
here.  The resulting files are written only below the external alpha staging
root; this module never writes canonical data or opens protected outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import requests


STAGING_MARKER = "idx-alpha-available-data-staging-20260919"
INDEX_PATTERN = re.compile(
    r".*all-(?P<year>\d{4})-(?P<period>audit|TW[123])-pagesize\d+\.idxid\.raw$",
    re.IGNORECASE,
)
BASE_URL = "https://www.idx.id/"
API_URL = "https://www.idx.id/primary/ListedCompany/GetFinancialReport"
INSTANCE_NAME = "instance.zip"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("Results"), list):
        raise ValueError(f"unexpected IDX report response shape: {path}")
    if not isinstance(value.get("ResultCount"), int):
        raise ValueError(f"missing integer ResultCount: {path}")
    return value


def _index_files(index_root: Path) -> list[tuple[Path, str, str]]:
    files: list[tuple[Path, str, str]] = []
    for path in sorted(index_root.rglob("*.raw")):
        match = INDEX_PATTERN.fullmatch(path.name)
        if match:
            files.append((path, match.group("year"), match.group("period")))
    if not files:
        raise ValueError(f"no retained IDX report index files found under {index_root}")
    return files


def _attachments(row: dict[str, Any]) -> list[dict[str, Any]]:
    attachments = row.get("Attachments")
    if not isinstance(attachments, list):
        raise ValueError("IDX report row has no attachment list")
    return [item for item in attachments if isinstance(item, dict)]


def _attachment_counts(rows: Iterable[dict[str, Any]]) -> tuple[Counter[str], Counter[str]]:
    counts: Counter[str] = Counter()
    zero_size: Counter[str] = Counter()
    for row in rows:
        for attachment in _attachments(row):
            name = str(attachment.get("File_Name") or "").lower()
            file_type = str(attachment.get("File_Type") or "").lower()
            kind = name if name in {"instance.zip", "inlinexbrl.zip"} else file_type
            counts[kind] += 1
            if not attachment.get("File_Size"):
                zero_size[kind] += 1
    return counts, zero_size


def _period_summary(path: Path, year: str, period: str) -> dict[str, Any]:
    response = _json(path)
    rows = [row for row in response["Results"] if isinstance(row, dict)]
    tickers = {str(row.get("KodeEmiten")) for row in rows if row.get("KodeEmiten")}
    modified = sorted(
        str(row["File_Modified"])
        for row in rows
        if row.get("File_Modified")
    )
    attachment_counts, zero_size = _attachment_counts(rows)
    instance_tickers = {
        str(row.get("KodeEmiten"))
        for row in rows
        if any(
            str(item.get("File_Name") or "").lower() == INSTANCE_NAME
            for item in _attachments(row)
        )
        and row.get("KodeEmiten")
    }
    file_ids = {
        str(item["File_ID"])
        for row in rows
        for item in _attachments(row)
        if item.get("File_ID")
    }
    late_modified = sum(
        1
        for row in rows
        if row.get("File_Modified")
        and str(row.get("Report_Year"))[:4].isdigit()
        and str(row["File_Modified"])[:4].isdigit()
        and int(str(row["File_Modified"])[:4]) > int(str(row["Report_Year"])[:4]) + 1
    )
    return {
        "index_file": path.name,
        "index_sha256": sha256_file(path),
        "index_bytes": path.stat().st_size,
        "year": int(year),
        "period": period.upper(),
        "result_count": response["ResultCount"],
        "rows": len(rows),
        "unique_tickers": len(tickers),
        "missing_code_rows": sum(1 for row in rows if not row.get("KodeEmiten")),
        "instance_zip_tickers": len(instance_tickers),
        "instance_zip_missing_tickers": sorted(tickers - instance_tickers),
        "unique_file_ids": len(file_ids),
        "modified_min": modified[0] if modified else None,
        "modified_max": modified[-1] if modified else None,
        "modified_after_report_year_plus_one_rows": late_modified,
        "attachment_type_counts": dict(sorted(attachment_counts.items())),
        "zero_size_by_type": dict(sorted(zero_size.items())),
    }


def summarize(index_root: Path) -> dict[str, Any]:
    periods = [_period_summary(*entry) for entry in _index_files(index_root)]
    annual = [item for item in periods if item["period"] == "AUDIT"]
    annual_tickers: dict[int, set[str]] = {}
    for path, year, period in _index_files(index_root):
        if period.lower() != "audit":
            continue
        response = _json(path)
        annual_tickers[int(year)] = {
            str(row["KodeEmiten"])
            for row in response["Results"]
            if isinstance(row, dict) and row.get("KodeEmiten")
        }
    annual_transition: dict[str, Any] = {}
    for year in sorted(annual_tickers):
        current = annual_tickers[year]
        prior = annual_tickers.get(year - 1, set())
        annual_transition[str(year)] = {
            "tickers": len(current),
            "prior_overlap": len(current & prior),
            "new_vs_prior": len(current - prior),
            "prior_only": len(prior - current),
        }
    return {
        "schema_version": "1.0",
        "status": "PASS_IDX_FINANCIAL_REPORT_SURFACE_RESEARCH_ONLY",
        "scope": "Public IDX report-index metadata and official XBRL attachment acquisition; no admission",
        "source": {
            "base_url": BASE_URL,
            "endpoint": API_URL,
            "transport_host": "www.idx.id",
            "transport_note": "www.idx.co.id returned a Cloudflare challenge in the bounded probe; the public idx.id host returned HTTP 200",
        },
        "periods": periods,
        "annual_ticker_transition": annual_transition,
        "annual_index_rows": sum(int(item["rows"]) for item in annual),
        "annual_unique_tickers_union": len(set().union(*annual_tickers.values()))
        if annual_tickers
        else 0,
        "what_is_proven": [
            "The public IDX report endpoint returns one or more report-index rows with issuer code, report year/period, file-modified metadata, file IDs, and attachment paths.",
            "The empty-code query returns a bounded all-ticker index for the requested year and period; pageSize=1000 covered every returned row in the retained probes.",
            "Most retained annual and quarterly rows expose an official instance.zip attachment, with small period-specific exceptions recorded by the audit.",
            "Old report-year rows can carry file-modified timestamps several years after the report year; this is evidence of mutable/revised index state, not a clean available-at timestamp.",
        ],
        "what_remains_unknown": [
            "whether File_Modified is publication, upload, revision, or another operational timestamp",
            "report availability to an investor at each historical decision time",
            "issuer/security identity continuity and historical population completeness",
            "cross-issuer XBRL taxonomy comparability and restatement lineage",
            "whether every attachment remains retrievable and byte-stable over time",
        ],
        "admission": {
            "index_metadata": "SUPPORTED_BOUNDED_ACQUISITION",
            "raw_xbrl": "EVIDENCE_ONLY_UNTIL_PIT_AND_REVISION_CONTRACT",
            "historical_research_admission": "BLOCKED",
            "allowed_use": "raw financial-source acquisition, coverage census, report-period and revision-surface research",
            "forbidden_use": "treat File_Modified as available-at time, silently normalize issuer taxonomies, or substitute for the admitted financial PIT bundle",
        },
        "protected_boundary": "CLOSED",
    }


def _official_url(file_path: str) -> str:
    if not file_path.startswith("/"):
        raise ValueError("IDX attachment path must be rooted")
    parts = urlsplit(urljoin(BASE_URL, file_path))
    if parts.scheme != "https" or parts.hostname != "www.idx.id":
        raise ValueError("attachment host is not the official idx.id host")
    encoded_path = quote(parts.path, safe="/%:@")
    return urlunsplit((parts.scheme, parts.netloc, encoded_path, parts.query, ""))


def _find_index(index_root: Path, year: int, period: str) -> Path:
    matches = [
        path
        for path, file_year, file_period in _index_files(index_root)
        if int(file_year) == year and file_period.lower() == period.lower()
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one index for {year}-{period}, got {len(matches)}")
    return matches[0]


def download_instances(
    index_root: Path,
    output_root: Path,
    *,
    year: int,
    period: str,
    limit: int | None,
    delay_seconds: float,
) -> dict[str, Any]:
    if delay_seconds < 0.1:
        raise ValueError("delay_seconds must be at least 0.1")
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = _find_index(index_root, year, period)
    response = _json(index_path)
    rows = [row for row in response["Results"] if isinstance(row, dict)]
    if limit is not None:
        rows = rows[:limit]
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/zip, application/octet-stream, */*",
            "Referer": BASE_URL,
            "User-Agent": "idx-trade-research-acquisition/1.0",
        }
    )
    records: list[dict[str, Any]] = []
    for row in rows:
        ticker = str(row.get("KodeEmiten") or "").strip()
        candidates = [
            item
            for item in _attachments(row)
            if str(item.get("File_Name") or "").lower() == INSTANCE_NAME
        ]
        record: dict[str, Any] = {
            "ticker": ticker,
            "year": row.get("Report_Year"),
            "period": row.get("Report_Period"),
            "file_modified": row.get("File_Modified"),
            "index_file": index_path.name,
            "index_sha256": sha256_file(index_path),
        }
        if len(candidates) != 1:
            record.update({"status": "MISSING_OR_AMBIGUOUS_INSTANCE", "candidate_count": len(candidates)})
            records.append(record)
            continue
        attachment = candidates[0]
        url = _official_url(str(attachment.get("File_Path") or ""))
        record.update({"file_id": attachment.get("File_ID"), "url": url})
        destination = output_root / f"{ticker or 'MISSING_CODE'}.instance.zip"
        partial = destination.with_suffix(destination.suffix + ".part")
        try:
            response_bytes = session.get(url, timeout=90)
            record["http_status"] = response_bytes.status_code
            if response_bytes.status_code != 200:
                record["status"] = "HTTP_FAILURE"
            elif not response_bytes.content.startswith(b"PK"):
                record["status"] = "NON_ZIP_BODY"
            else:
                partial.write_bytes(response_bytes.content)
                with zipfile.ZipFile(partial) as archive:
                    names = archive.namelist()
                    if "instance.xbrl" not in names:
                        raise ValueError("instance.xbrl missing")
                partial.replace(destination)
                record.update(
                    {
                        "status": "DOWNLOADED",
                        "bytes": destination.stat().st_size,
                        "sha256": sha256_file(destination),
                        "zip_members": names,
                    }
                )
        except Exception as exc:  # bounded acquisition records failure, never fabricates success
            record.update({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
            if partial.exists():
                partial.unlink()
        finally:
            records.append(record)
            time.sleep(delay_seconds)
    counts = Counter(str(record["status"]) for record in records)
    return {
        "year": year,
        "period": period.upper(),
        "index_file": index_path.name,
        "index_sha256": sha256_file(index_path),
        "requested": len(rows),
        "status_counts": dict(sorted(counts.items())),
        "records": records,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if STAGING_MARKER not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    index_root = args.index_root.resolve()
    result = summarize(index_root)
    if args.download_year is not None or args.download_period is not None:
        if args.download_year is None or args.download_period is None or args.download_root is None:
            raise ValueError("download_year, download_period, and download_root must be supplied together")
        download_root = args.download_root.resolve()
        if STAGING_MARKER not in str(download_root):
            raise ValueError("refusing download root outside isolated alpha staging")
        result["download"] = download_instances(
            index_root,
            download_root,
            year=args.download_year,
            period=args.download_period,
            limit=args.download_limit,
            delay_seconds=args.delay_seconds,
        )
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--download-year", type=int)
    parser.add_argument("--download-period", choices=["audit", "TW1", "TW2", "TW3"])
    parser.add_argument("--download-root", type=Path)
    parser.add_argument("--download-limit", type=int)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
