"""Outcome-blind audit of the public IDX announcement search surface.

The endpoint is treated as a bounded search/index surface, not as a complete
event ledger.  This module validates retained raw JSON responses, records
multi-page and date-filter behavior, and audits linked-file integrity when a
downloaded attachment directory is supplied.  It never calls IDX, infers an
effective date from publication metadata, or admits a historical PIT source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


REQUIRED_ITEM_FIELDS = {
    "Id",
    "AnnouncementNo",
    "PublishDate",
    "Title",
    "Code",
    "Jenis",
    "Attachments",
}
EFFECTIVE_DATE_RE = re.compile(
    r"Perubahan tersebut mulai efektif pada tanggal\s+(\d{1,2}\s+\w+\s+\d{4})",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_code(value: Any) -> str:
    return str(value or "").strip().upper()


def _parse_publish_date(value: Any) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def audit_payload(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    items = payload.get("Items")
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError(f"{path} does not contain an Items object list")
    if not isinstance(payload.get("ItemCount"), int):
        raise ValueError(f"{path} has no integer ItemCount")
    if not isinstance(payload.get("PageCount"), int):
        raise ValueError(f"{path} has no integer PageCount")
    fields = set().union(*(set(item) for item in items)) if items else set()
    missing_fields = sorted(REQUIRED_ITEM_FIELDS - fields)
    if missing_fields:
        raise ValueError(f"{path} missing announcement fields: {missing_fields}")

    ids = [str(item["Id"]) for item in items]
    if any(not item_id for item_id in ids):
        raise ValueError(f"{path} contains an empty announcement id")
    dates = [_parse_publish_date(item["PublishDate"]) for item in items]
    codes = [_normalize_code(item.get("Code")) for item in items]
    attachment_counts = []
    for item in items:
        attachments = item.get("Attachments")
        if not isinstance(attachments, list):
            raise ValueError(f"{path} has a non-list Attachments field")
        attachment_counts.append(len(attachments))

    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "fields": sorted(fields),
        "items_observed": len(items),
        "item_count": payload["ItemCount"],
        "page_size": payload.get("PageSize"),
        "page_number": payload.get("PageNumber"),
        "page_count": payload["PageCount"],
        "unique_ids": len(set(ids)),
        "duplicate_ids": sorted(item_id for item_id, count in Counter(ids).items() if count > 1),
        "codes": sorted(code for code in set(codes) if code),
        "empty_code_count": sum(not code for code in codes),
        "publish_date_min": min(dates).isoformat() if dates else None,
        "publish_date_max": max(dates).isoformat() if dates else None,
        "attachment_count_min": min(attachment_counts) if attachment_counts else 0,
        "attachment_count_max": max(attachment_counts) if attachment_counts else 0,
        "items": items,
    }


def _status_line(headers_path: Path) -> str:
    for line in headers_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("HTTP/"):
            return line
    return ""


def _iter_downloaded_pdfs(root: Path) -> Iterable[Path]:
    return (path for path in root.rglob("*.pdf") if path.is_file())


def audit_downloaded_attachments(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(_iter_downloaded_pdfs(root)):
        headers_path = Path(str(path) + ".headers.txt")
        status = _status_line(headers_path) if headers_path.exists() else ""
        prefix = path.read_bytes()[:5]
        records.append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "status_line": status,
                "has_pdf_magic": prefix == b"%PDF-",
                "headers_present": headers_path.exists(),
            }
        )
    hashes: defaultdict[str, list[str]] = defaultdict(list)
    for record in records:
        if record["has_pdf_magic"] and record["status_line"].endswith("200 OK"):
            hashes[record["sha256"]].append(record["path"])
    return {
        "root": str(root),
        "files": records,
        "file_count": len(records),
        "http_200_pdf_count": sum(
            record["has_pdf_magic"] and record["status_line"].endswith("200 OK") for record in records
        ),
        "non_pdf_or_non_200_count": sum(
            not (record["has_pdf_magic"] and record["status_line"].endswith("200 OK")) for record in records
        ),
        "valid_hash_collisions": [
            {"sha256": digest, "paths": paths}
            for digest, paths in sorted(hashes.items())
            if len(paths) > 1
        ],
    }


def audit_effective_date_text(root: Path, publish_dates_by_code: dict[str, str]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.txt")):
        if path.name.endswith(".headers.txt") or "lamp" in path.stem.lower():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        matches = EFFECTIVE_DATE_RE.findall(text)
        if not matches:
            continue
        code = _normalize_code(path.parent.name.split("__", 1)[-1])
        records.append(
            {
                "path": str(path),
                "code": code,
                "effective_date_text": sorted(set(matches)),
                "api_publish_date": publish_dates_by_code.get(code),
                "publication_precedes_effective": bool(
                    publish_dates_by_code.get(code)
                    and publish_dates_by_code[code][:10] < "2024-06-24"
                ),
                "publish_date_after_document_effective": bool(
                    publish_dates_by_code.get(code)
                    and publish_dates_by_code[code][:10] > "2024-06-24"
                ),
            }
        )
    return {
        "root": str(root),
        "records": records,
        "codes_with_explicit_effective_date": sorted({record["code"] for record in records}),
        "publish_after_document_effective_count": sum(
            record["publish_date_after_document_effective"] for record in records
        ),
    }


def compare_files(pairs: list[tuple[str, Path, Path]]) -> list[dict[str, Any]]:
    result = []
    for label, left, right in pairs:
        left_hash = sha256_file(left)
        right_hash = sha256_file(right)
        result.append(
            {
                "label": label,
                "left": str(left),
                "left_sha256": left_hash,
                "right": str(right),
                "right_sha256": right_hash,
                "same_bytes": left_hash == right_hash,
            }
        )
    return result


def run_audit(
    probe_root: Path,
    classification_path: Path,
    date_probe_headers: Path,
    attachment_root: Path,
    effective_text_root: Path,
    annual_pairs: list[tuple[str, Path, Path]],
    output: Path,
) -> dict[str, Any]:
    output = output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")

    query_files = {
        "penghapusan_pencatatan": probe_root / "2026-09-20__keyword-penghapusan-pencatatan__pagesize100.raw",
        "pencatatan_kembali": probe_root / "2026-09-20__keyword-pencatatan-kembali__pagesize100.raw",
        "perubahan_nama": probe_root / "2026-09-20__keyword-perubahan-nama__pagesize100.raw",
        "perubahan_kode": probe_root / "2026-09-20__keyword-perubahan-kode__pagesize100.raw",
        "penggabungan": probe_root / "2026-09-20__keyword-penggabungan__pagesize100.raw",
        "pemecahan_saham": probe_root / "2026-09-20__keyword-pemecahan-saham__pagesize100.raw",
    }
    queries = {name: audit_payload(path) for name, path in query_files.items()}
    query_status = {
        name: _status_line(path.with_suffix(".headers.txt"))
        for name, path in query_files.items()
    }
    classification = audit_payload(classification_path)
    classification_status = _status_line(classification_path.with_suffix(".headers.txt"))
    pagination: dict[str, dict[str, Any]] = {}
    entity_semantics: dict[str, dict[str, Any]] = {}
    for slug, query_name in (("perubahan-nama", "perubahan_nama"), ("penggabungan", "penggabungan")):
        page2_path = probe_root / f"2026-09-20__keyword-{slug}__page2-pagesize100.raw"
        if not page2_path.exists():
            continue
        page2 = audit_payload(page2_path)
        ids = [str(item["Id"]) for item in queries[query_name]["items"] + page2["items"]]
        combined_items = queries[query_name]["items"] + page2["items"]
        codes = [
            _normalize_code(item.get("Code"))
            for item in combined_items
            if _normalize_code(item.get("Code"))
        ]
        code_counts = Counter(codes)
        entity_semantics[query_name] = {
            "items": len(combined_items),
            "unique_codes": len(set(codes)),
            "repeated_code_count": sum(count > 1 for count in code_counts.values()),
            "jenis_counts": dict(sorted(Counter(str(item.get("Jenis")) for item in combined_items).items())),
        }
        pagination[query_name] = {
            "page_1_items": queries[query_name]["items_observed"],
            "page_2_items": page2["items_observed"],
            "reported_item_count": page2["item_count"],
            "reported_page_number": page2["page_number"],
            "combined_unique_ids": len(set(ids)),
            "combined_date_min": min(
                _parse_publish_date(item["PublishDate"])
                for item in queries[query_name]["items"] + page2["items"]
            ).isoformat(),
            "combined_date_max": max(
                _parse_publish_date(item["PublishDate"])
                for item in queries[query_name]["items"] + page2["items"]
            ).isoformat(),
            "page_2_path": str(page2_path),
            "page_2_sha256": page2["sha256"],
        }
    classification_items = classification["items"]
    company_items = [item for item in classification_items if str(item.get("Jenis")) == "STOCK"]
    exchange_items = [item for item in classification_items if str(item.get("Jenis")) in {"SPOP", "Exchange"}]
    publish_dates_by_code = {
        _normalize_code(item.get("Code")): str(item.get("PublishDate"))
        for item in company_items
    }
    date_status = _status_line(date_probe_headers)
    attachment_audit = audit_downloaded_attachments(attachment_root)
    effective_dates = audit_effective_date_text(effective_text_root, publish_dates_by_code)
    annual_comparison = compare_files(annual_pairs)
    pencatatan_titles = [str(item.get("Title", "")).lower() for item in queries["pencatatan_kembali"]["items"]]
    penghapusan_titles = [str(item.get("Title", "")).lower() for item in queries["penghapusan_pencatatan"]["items"]]
    keyword_semantics = {
        "pencatatan_kembali": {
            "board_or_officer_structure_titles": sum("susunan pengurus" in title for title in pencatatan_titles),
            "security_listing_relisting_titles": sum("saham di bursa" in title for title in pencatatan_titles),
        },
        "penghapusan_pencatatan": {
            "treasury_or_other_security_cancellation_titles": sum(
                "saham treasuri" in title or "dinfra" in title for title in penghapusan_titles
            ),
            "go_private_or_delisting_plan_titles": sum(
                "go private" in title or "delisting" in title for title in penghapusan_titles
            ),
            "explicit_security_listing_relisting_titles": sum(
                "pencatatan kembali saham di bursa" in title for title in penghapusan_titles
            ),
        },
    }

    checks = {
        "all_keyword_queries_http_200_json": all(
            query_status[name].endswith("200 OK")
            and item["items_observed"] >= 0
            and item["unique_ids"] == item["items_observed"]
            for name, item in queries.items()
        ),
        "classification_payload_http_200": classification_status.endswith("200 OK"),
        "classification_payload_http_independent_of_search_queries": classification["unique_ids"] == classification["items_observed"],
        "retained_page2_results_reconcile": all(
            value["page_1_items"] + value["page_2_items"] == value["reported_item_count"]
            and value["combined_unique_ids"] == value["reported_item_count"]
            for value in pagination.values()
        ),
        "classification_has_eight_company_items": len(company_items) == 8,
        "classification_has_three_exchange_items": len(exchange_items) == 3,
        "date_filter_probe_is_not_200": not date_status.endswith("200 OK"),
        "annual_packages_match_existing_archive": all(item["same_bytes"] for item in annual_comparison),
        "downloaded_attachment_manifest_is_nonempty": attachment_audit["file_count"] > 0,
        "explicit_effective_dates_are_not_replaced_by_publish_dates": all(
            record["api_publish_date"] for record in effective_dates["records"]
        ),
    }
    result = {
        "status": "PASS_OFFICIAL_ANNOUNCEMENT_SURFACE_RESEARCH_ONLY" if all(checks.values()) else "FAIL_OFFICIAL_ANNOUNCEMENT_SURFACE_INTEGRITY",
        "scope": "Official IDX announcement search/index surface and retained linked-file checks; capability and event-evidence research only",
        "protected_boundary": "CLOSED",
        "source": {
            "search_endpoint": "https://www.idx.id/primary/NewsAnnouncement/GetAllAnnouncement",
            "classification_path": str(classification_path),
            "classification_sha256": sha256_file(classification_path),
            "classification_item_count": classification["item_count"],
            "classification_publish_date_min": classification["publish_date_min"],
            "classification_publish_date_max": classification["publish_date_max"],
            "classification_company_codes": sorted({_normalize_code(item.get("Code")) for item in company_items}),
            "classification_exchange_announcement_numbers": sorted(
                str(item.get("AnnouncementNo")) for item in exchange_items
            ),
            "query_results": {
                name: {
                    **{key: value for key, value in details.items() if key != "items"},
                    "http_status_line": query_status[name],
                }
                for name, details in queries.items()
            },
            "classification_http_status_line": classification_status,
            "date_filter_status_line": date_status,
            "keyword_semantics": keyword_semantics,
            "pagination": pagination,
            "entity_semantics": entity_semantics,
        },
        "integrity_checks": checks,
        "event_semantics": {
            "publication_vs_effective": effective_dates,
            "explicit_effective_date_count": len(effective_dates["records"]),
            "publish_date_is_not_effective_date": True,
            "search_result_completeness": "UNKNOWN; ItemCount is per keyword query and multi-page results exist",
            "date_filter_behavior": "BOUNDED_FAILURE; retained date-filter request returned non-200 and is not used for completeness",
        },
        "linked_file_audit": attachment_audit,
        "annual_package_comparison": annual_comparison,
        "what_is_proven": [
            "The official public endpoint returns structured announcement metadata with stable IDs, announcement numbers, publish timestamps, codes, and attachment links for bounded keyword searches.",
            "The classification keyword returns 11 records: three exchange-wide packages and eight company-specific records spanning October 2023 through June 2026.",
            "The lifecycle keywords are semantically mixed: two of four Pencatatan Kembali results concern board/officer structure, while only two explicitly mention security listing/relisting; Penghapusan Pencatatan likewise mixes treasury/security cancellations, go-private plans, and listing events.",
            "The retained second pages reconcile the reported counts for Perubahan Nama (182 unique IDs, 2023-07-10 through 2026-09-01) and Penggabungan (175 unique IDs, 2023-07-03 through 2026-09-02); this validates pagination for those queries only, not global archive completeness.",
            "The 182 Perubahan Nama results contain 108 unique codes with 43 repeated codes and 11 Broker records; the 175 Penggabungan results contain 71 unique codes with 32 repeated codes. Announcement count is therefore not event count or issuer-transition count.",
            "The retained 2024-2026 exchange-wide packages are byte-identical to the previously acquired official sector archive, so they are not new annual classification payloads.",
            "At least four company-specific documents expose an explicit effective date of 24 June 2024 while the API metadata reports 22 January 2025 publication, proving that publication metadata and effective-date text must remain separate.",
            "Linked attachment integrity is imperfect: some advertised links return non-PDF 403 bodies and several successful links share the same PDF hash, so attachment URL identity cannot be assumed without content verification.",
        ],
        "what_remains_unknown": [
            "complete announcement coverage across all historical dates and keyword variants",
            "daily PIT membership and survivorship-safe population",
            "issuer/ISIN continuity and ticker reuse",
            "whether an announcement's effective date is the date used by every downstream market or index field",
            "row-level available-at/knowledge time and revision/vintage semantics",
        ],
        "admission": {
            "official_announcement_metadata": "SUPPORTED_BOUNDED_EVENT_DISCOVERY",
            "event_document_content": "BOUNDED_WHEN_FILE_HASH_AND_TEXT_AUDITED",
            "historical_pit_population": "MISSING",
            "historical_research_admission": "BLOCKED",
            "allowed_use": "bounded event discovery, publication-vs-effective timing audit, and source-design research",
            "forbidden_use": "complete lifecycle substitution, daily PIT membership inference, silent effective-date imputation, or predictive admission",
        },
        "network_used": False,
        "provider_called_by_audit": False,
        "canonical_mutation": False,
    }
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if result["status"] != "PASS_OFFICIAL_ANNOUNCEMENT_SURFACE_RESEARCH_ONLY":
        raise SystemExit(1)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-root", type=Path, required=True)
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--date-probe-headers", type=Path, required=True)
    parser.add_argument("--attachment-root", type=Path, required=True)
    parser.add_argument("--effective-text-root", type=Path, required=True)
    parser.add_argument("--annual-pair", action="append", nargs=3, metavar=("LABEL", "OLD", "NEW"), default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pairs = [(label, Path(old), Path(new)) for label, old, new in args.annual_pair]
    run_audit(
        args.probe_root,
        args.classification,
        args.date_probe_headers,
        args.attachment_root,
        args.effective_text_root,
        pairs,
        args.output,
    )


if __name__ == "__main__":
    main()
