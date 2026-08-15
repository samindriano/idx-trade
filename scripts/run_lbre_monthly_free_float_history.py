from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from curl_cffi import requests

from idx_trade.historical_statutory_free_float import (
    FreeFloatRevisionKind,
    FreeFloatSourceFamily,
    HistoricalFreeFloatObservation,
    replay_historical_free_float,
)
from idx_trade.lbre_lineage_remediation import (
    classify_revision_kind,
    parse_lbre_current_fields,
)


IDX_ANNOUNCEMENT_URL = "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"
PAGE_SIZE = 1000
KEYWORD = "Laporan Bulanan Registrasi Pemegang Efek"
JAKARTA = timezone(timedelta(hours=7))
DISCOVERY_FROM = "20240501"
DISCOVERY_TO = "20260815"
EXPECTED_SNAPSHOT_MANIFEST = "7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e"
EXPECTED_REMEDIATION_MANIFEST = "cb2e929a8e7d5fc481c0eed6add4a6ba848c5a3374c65ea38e5fbe3fa5727244"
PARENT_SNAPSHOT_ROOT = Path(
    r"D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1"
)
PARENT_REMEDIATION_ROOT = Path(
    r"D:\Documents\Project\idx-lbre-lineage-parser-remediation-20260815-v1-final6"
)
MONTHS = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
def target_month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


TARGET_DATES = tuple(
    target_month_end(year, month)
    for year in range(2024, 2027)
    for month in range(1, 13)
    if (year > 2024 or month >= 4) and (year < 2026 or month <= 6)
)
TARGET_DATE_STRINGS = {value.isoformat() for value in TARGET_DATES}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_parent_manifests(output: Path) -> None:
    snapshot_manifest = PARENT_SNAPSHOT_ROOT / "artifact_manifest.json"
    remediation_manifest = PARENT_REMEDIATION_ROOT / "artifact_manifest.json"
    actual_snapshot = sha256_file(snapshot_manifest)
    actual_remediation = sha256_file(remediation_manifest)
    if actual_snapshot != EXPECTED_SNAPSHOT_MANIFEST:
        raise RuntimeError(f"snapshot parent manifest mismatch: {actual_snapshot}")
    if actual_remediation != EXPECTED_REMEDIATION_MANIFEST:
        raise RuntimeError(f"remediation parent manifest mismatch: {actual_remediation}")
    dump_json(
        output / "metadata/parent_manifest_verification.json",
        {
            "snapshot_root": str(PARENT_SNAPSHOT_ROOT),
            "snapshot_manifest_sha256": actual_snapshot,
            "remediation_root": str(PARENT_REMEDIATION_ROOT),
            "remediation_manifest_sha256": actual_remediation,
            "valid": True,
        },
    )


def fetch_page(page: int) -> bytes:
    params = {
        "kodeEmiten": "",
        "emitenType": "*",
        "indexFrom": page,
        "pageSize": PAGE_SIZE,
        "dateFrom": DISCOVERY_FROM,
        "dateTo": DISCOVERY_TO,
        "lang": "id",
        "keyword": KEYWORD,
    }
    response = requests.get(
        IDX_ANNOUNCEMENT_URL,
        params=params,
        impersonate="chrome",
        headers={"Referer": "https://www.idx.co.id/"},
        timeout=90,
    )
    if response.status_code != 200:
        raise RuntimeError(f"IDX announcement page {page} returned HTTP {response.status_code}")
    return bytes(response.content)


def parse_page(raw: bytes, page: int) -> tuple[int, list[dict[str, Any]]]:
    payload = json.loads(raw.decode("utf-8"))
    total = int(payload.get("ResultCount", 0))
    replies = payload.get("Replies")
    if not isinstance(replies, list):
        raise RuntimeError(f"IDX announcement page {page} has no Replies list")
    return total, replies


def discover(output: Path) -> None:
    raw_dir = output / "raw/discovery"
    raw_dir.mkdir(parents=True, exist_ok=True)
    first = fetch_page(0)
    total, replies = parse_page(first, 0)
    page_count = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page_records: list[dict[str, Any]] = []
    all_replies: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for page in range(page_count):
        target = raw_dir / f"page_{page:04d}.bin"
        raw = first if page == 0 else fetch_page(page)
        if target.exists():
            if sha256_file(target) != sha256_bytes(raw):
                raise RuntimeError(f"refusing to overwrite changed discovery page: {target}")
        else:
            target.write_bytes(raw)
        page_total, page_replies = parse_page(raw, page)
        if page_total != total:
            raise RuntimeError(f"ResultCount changed on page {page}: {page_total} != {total}")
        expected_rows = PAGE_SIZE if page < page_count - 1 else total - PAGE_SIZE * (page_count - 1)
        if len(page_replies) != expected_rows:
            raise RuntimeError(f"partial page {page}: {len(page_replies)} != {expected_rows}")
        ids = [str(item.get("pengumuman", {}).get("Id2", "")) for item in page_replies]
        if any(not item_id for item_id in ids) or len(set(ids)) != len(ids):
            raise RuntimeError(f"missing/duplicate announcement identities on page {page}")
        if seen_ids.intersection(ids):
            raise RuntimeError(f"cross-page duplicate announcement identity on page {page}")
        seen_ids.update(ids)
        all_replies.extend(page_replies)
        page_records.append(
            {
                "page": page,
                "index_from": page,
                "expected_rows": expected_rows,
                "actual_rows": len(page_replies),
                "bytes": len(raw),
                "sha256": sha256_bytes(raw),
                "path": str(target),
            }
        )
    if len(all_replies) != total or len(seen_ids) != total:
        raise RuntimeError(f"pagination incomplete: {len(all_replies)} unique rows for {total}")

    candidates: list[dict[str, Any]] = []
    for page_item, reply in zip(
        [record for record in page_records for _ in range(record["actual_rows"])],
        all_replies,
    ):
        announcement = reply.get("pengumuman", {})
        title = str(announcement.get("JudulPengumuman") or "").strip()
        if KEYWORD.lower() not in title.lower():
            continue
        ticker = str(announcement.get("Kode_Emiten") or "").strip().upper()
        announcement_no = str(announcement.get("NoPengumuman") or "").strip()
        announced_at = str(announcement.get("TglPengumuman") or "").strip()
        if not ticker or not announcement_no or not announced_at:
            continue
        attachments = reply.get("attachments") or []
        main_attachments = [
            attachment
            for attachment in attachments
            if attachment.get("FullSavePath")
            and attachment.get("IsAttachment") is False
        ]
        for attachment in main_attachments:
            candidates.append(
                {
                    "candidate_id": sha256_bytes(
                        "|".join(
                            [ticker, announcement_no, announced_at, str(attachment["FullSavePath"])]
                        ).encode()
                    ),
                    "ticker": ticker,
                    "announcement_no": announcement_no,
                    "announced_at": announced_at,
                    "title": title,
                    "id2": str(announcement.get("Id2") or ""),
                    "source_url": str(attachment["FullSavePath"]),
                    "original_filename": attachment.get("OriginalFilename"),
                    "pdf_filename": attachment.get("PDFFilename"),
                    "metadata_page": page_item["page"],
                    "metadata_path": page_item["path"],
                    "metadata_sha256": page_item["sha256"],
                }
            )
    unique: dict[str, dict[str, Any]] = {row["candidate_id"]: row for row in candidates}
    dump_json(
        output / "metadata/discovery_manifest.json",
        {
            "endpoint": IDX_ANNOUNCEMENT_URL,
            "params": {
                "dateFrom": DISCOVERY_FROM,
                "dateTo": DISCOVERY_TO,
                "keyword": KEYWORD,
                "pageSize": PAGE_SIZE,
                "indexFrom_semantics": "zero-based page number",
            },
            "result_count": total,
            "page_count": page_count,
            "pages": page_records,
            "unique_announcement_ids": len(seen_ids),
            "candidate_count": len(unique),
            "pagination_complete": True,
        },
    )
    dump_json(output / "metadata/discovery_candidates.json", list(unique.values()))
    print(json.dumps({"result_count": total, "pages": page_count, "lbre_candidates": len(unique)}, indent=2))


def parent_reuse_index() -> dict[str, dict[str, Any]]:
    manifest = load_json(PARENT_SNAPSHOT_ROOT / "metadata/lbre_download_manifest.json")
    return {
        str(row["url"]): row
        for row in manifest.get("records", [])
        if row.get("status") == 200 and row.get("url") and row.get("path")
    }


def download_one(row: dict[str, Any], output: Path) -> dict[str, Any]:
    pdf_dir = output / "attachments/lbre"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    target = pdf_dir / f"{row['candidate_id']}.pdf"
    errors: list[str] = []
    for attempt in range(1, 4):
        try:
            response = requests.get(
                row["source_url"],
                impersonate="chrome",
                headers={"Referer": "https://www.idx.co.id/"},
                timeout=60,
            )
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}")
            content = bytes(response.content)
            if not content.startswith(b"%PDF"):
                raise RuntimeError("response is not a PDF")
            digest = sha256_bytes(content)
            if target.exists():
                if sha256_file(target) != digest:
                    raise RuntimeError("existing artifact hash conflict")
            else:
                target.write_bytes(content)
            return {
                **row,
                "status": "DOWNLOADED",
                "http_status": 200,
                "bytes": len(content),
                "source_sha256": digest,
                "path": str(target),
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "attempts": attempt,
            }
        except Exception as exc:  # bounded transport result is retained
            errors.append(f"attempt_{attempt}:{exc}")
    return {
        **row,
        "status": "DOWNLOAD_ERROR",
        "http_status": None,
        "bytes": 0,
        "source_sha256": None,
        "path": None,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "attempts": 3,
        "error": ";".join(errors),
    }


def acquire(output: Path, workers: int = 6) -> None:
    candidates = load_json(output / "metadata/discovery_candidates.json")
    reuse = parent_reuse_index()
    inventory_path = output / "metadata/acquisition_inventory.json"
    existing = {}
    if inventory_path.exists():
        existing = {row["candidate_id"]: row for row in load_json(inventory_path)}
    rows: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        old = existing.get(candidate_id)
        if old and old.get("status") in {"DOWNLOADED", "REUSED_PARENT", "DOWNLOAD_ERROR"}:
            if old.get("status") == "DOWNLOADED" and old.get("path") and Path(old["path"]).exists() and sha256_file(Path(old["path"])) == old.get("source_sha256"):
                rows.append(old)
                continue
            if old.get("status") == "REUSED_PARENT" and old.get("path") and Path(old["path"]).exists() and sha256_file(Path(old["path"])) == old.get("source_sha256"):
                rows.append(old)
                continue
        parent = reuse.get(candidate["source_url"])
        if parent:
            parent_path = Path(parent["path"])
            if not parent_path.exists() or sha256_file(parent_path) != parent["sha256"]:
                raise RuntimeError(f"parent reuse artifact missing/hash mismatch: {parent_path}")
            rows.append(
                {
                    **candidate,
                    "status": "REUSED_PARENT",
                    "http_status": 200,
                    "bytes": parent["bytes"],
                    "source_sha256": parent["sha256"],
                    "path": str(parent_path),
                    "retrieved_at_utc": parent.get("retrieved_at_utc"),
                    "attempts": 0,
                    "reused_parent": True,
                }
            )
        else:
            pending.append(candidate)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(download_one, row, output): row for row in pending}
        for index, future in enumerate(as_completed(future_map), start=1):
            rows.append(future.result())
            if index % 100 == 0:
                dump_json(inventory_path, rows)
                print(f"acquired {index}/{len(pending)} new attachments")
    rows.sort(key=lambda row: row["candidate_id"])
    dump_json(inventory_path, rows)
    print(json.dumps(Counter(row["status"] for row in rows), indent=2, sort_keys=True))


def month_end(year: int, month: int) -> date:
    return target_month_end(year, month)


def parse_position_date(text: str) -> tuple[date | None, tuple[str, ...]]:
    pattern = re.compile(
        r"(?:berakhir\s+pada\s+(?:akhir\s+bulan\s+)?|ends\s+in\s+|ending\s+on\s+)"
        r"(?:tanggal\s+)?(?:\d{1,2}\s+)?([A-Za-z]+)\s*[-–]?\s*(20\d{2})",
        re.IGNORECASE,
    )
    found: set[date] = set()
    evidence: list[str] = []
    for match in pattern.finditer(text):
        month = MONTHS.get(match.group(1).lower())
        if month is None:
            continue
        value = month_end(int(match.group(2)), month)
        found.add(value)
        evidence.append(match.group(0))
    if len(found) != 1:
        return None, tuple(evidence)
    return next(iter(found)), tuple(evidence)


def text_for_pdf(pdf_path: Path, output: Path) -> Path:
    if "idx-historical-statutory-free-float-snapshot-20260815-v1" in str(pdf_path):
        text_path = pdf_path.parent.parent / ".." / "text" / pdf_path.parent.name / f"{pdf_path.stem}.txt"
        text_path = text_path.resolve()
    else:
        text_path = output / "text" / f"{pdf_path.stem}.txt"
    if text_path.exists() and text_path.stat().st_size > 0:
        return text_path
    text_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), str(text_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0 or not text_path.exists():
        raise RuntimeError(f"pdftotext failed: {result.stderr.strip()[:300]}")
    return text_path


def _parse_one_document(index: int, row: dict[str, Any], output: Path) -> tuple[int, dict[str, Any] | None, dict[str, Any] | None]:
    base = {
        "candidate_id": row["candidate_id"],
        "ticker": row["ticker"],
        "announcement_no": row["announcement_no"],
        "announced_at": row["announced_at"],
        "title": row["title"],
        "source_url": row["source_url"],
        "source_sha256": row.get("source_sha256"),
        "metadata_source_sha256": row["metadata_sha256"],
        "path": row.get("path"),
        "status": row["status"],
    }
    if row["status"] not in {"DOWNLOADED", "REUSED_PARENT"} or not row.get("path"):
        return index, None, {**base, "parse_status": "DOWNLOAD_ERROR", "reason": row.get("error", row["status"])}
    try:
        pdf_path = Path(row["path"])
        text_path = text_for_pdf(pdf_path, output)
        text = text_path.read_text(encoding="utf-8", errors="replace")
        as_of, position_evidence = parse_position_date(text)
        if as_of is None:
            return index, None, {**base, "parse_status": "UNRESOLVED_POSITION", "position_evidence": list(position_evidence)}
        if as_of.isoformat() not in TARGET_DATE_STRINGS:
            return index, None, {**base, "parse_status": "NON_TARGET_POSITION", "as_of_date": as_of.isoformat()}
        parsed = parse_lbre_current_fields(text)
        if parsed.status != "EXACT" or parsed.fields is None:
            return index, None, {
                **base,
                "parse_status": "UNRESOLVED_FIELDS",
                "as_of_date": as_of.isoformat(),
                "diagnostics": list(parsed.diagnostics),
                "position_evidence": list(position_evidence),
            }
        fields = parsed.fields
        revision = classify_revision_kind(row["announcement_no"], row["title"], "ORIGINAL")
        published_at = datetime.fromisoformat(row["announced_at"]).replace(tzinfo=JAKARTA)
        return index, {
            **base,
            "parse_status": "EXACT",
            "as_of_date": as_of.isoformat(),
            "published_at": published_at.isoformat(),
            "free_float_shares": fields.free_float_shares,
            "free_float_pct": fields.free_float_pct,
            "total_listed_shares": fields.total_listed_shares,
            "revision_kind": revision,
            "supersedes_record_id": None,
            "text_path": str(text_path),
            "evidence_locations": list(fields.evidence_locations),
            "position_evidence": list(position_evidence),
        }, None
    except Exception as exc:
        return index, None, {**base, "parse_status": "PARSER_ERROR", "reason": str(exc)}


def parse_documents(output: Path, workers: int = 6) -> None:
    inventory = load_json(output / "metadata/acquisition_inventory.json")
    exact: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(_parse_one_document, index, row, output) for index, row in enumerate(inventory)]
        results = []
        for future in as_completed(futures):
            results.append(future.result())
            completed += 1
            if completed % 1000 == 0:
                print(f"parsed {completed}/{len(inventory)}")
    for _, exact_row, audit_row in sorted(results, key=lambda item: item[0]):
        if exact_row is not None:
            exact.append(exact_row)
        if audit_row is not None:
            audit.append(audit_row)
    dump_json(output / "normalized/lbre_exact_observations.json", exact)
    dump_json(output / "reports/lbre_parse_audit.json", {
        "candidate_count": len(inventory),
        "exact_count": len(exact),
        "audit_count": len(audit),
        "parse_status_counts": dict(sorted(Counter(row["parse_status"] for row in audit).items())),
        "position_counts": dict(sorted(Counter(row.get("as_of_date") for row in exact).items())),
        "audit_rows": audit,
    })
    print(json.dumps({"exact": len(exact), "audit": len(audit)}, indent=2))


def observation_id(row: dict[str, Any]) -> str:
    return f"LBRE:{row['ticker']}:{row['as_of_date']}:{row['source_sha256']}"


def economic_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["free_float_shares"], row["free_float_pct"], row["total_listed_shares"])


def make_observation(row: dict[str, Any]) -> HistoricalFreeFloatObservation:
    return HistoricalFreeFloatObservation(
        record_id=observation_id(row),
        ticker=row["ticker"],
        as_of_date=date.fromisoformat(row["as_of_date"]),
        published_at=datetime.fromisoformat(row["published_at"]),
        free_float_shares=int(row["free_float_shares"]),
        free_float_pct=float(row["free_float_pct"]),
        total_listed_shares=int(row["total_listed_shares"]),
        source_family=FreeFloatSourceFamily.ISSUER_LBRE,
        revision_kind=FreeFloatRevisionKind(row["revision_kind"]),
        supersedes_record_id=row.get("supersedes_record_id"),
        announcement_no=row["announcement_no"],
        source_url=row["source_url"],
        source_sha256=row["source_sha256"],
        metadata_source_sha256=row["metadata_source_sha256"],
        source_row_key=None,
    )


def observation_payload(row: HistoricalFreeFloatObservation) -> dict[str, Any]:
    return {
        "record_id": row.record_id,
        "ticker": row.ticker,
        "as_of_date": row.as_of_date.isoformat(),
        "published_at": row.published_at.isoformat(),
        "free_float_shares": row.free_float_shares,
        "free_float_pct": row.free_float_pct,
        "total_listed_shares": row.total_listed_shares,
        "source_family": row.source_family.value,
        "revision_kind": row.revision_kind.value,
        "supersedes_record_id": row.supersedes_record_id,
        "announcement_no": row.announcement_no,
        "source_url": row.source_url,
        "source_sha256": row.source_sha256,
        "metadata_source_sha256": row.metadata_source_sha256,
        "source_row_key": row.source_row_key,
    }


def replay(output: Path) -> None:
    exact = load_json(output / "normalized/lbre_exact_observations.json")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in exact:
        grouped[(row["ticker"], row["as_of_date"])].append(row)
    canonical_rows: list[dict[str, Any]] = []
    aliases: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    admitted_rows: list[dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        canonical_by_signature: dict[tuple[Any, ...], dict[str, Any]] = {}
        for row in sorted(rows, key=lambda item: (item["published_at"], item["source_url"], item["source_sha256"])):
            signature = (row["announcement_no"], economic_signature(row))
            canonical = canonical_by_signature.get(signature)
            if canonical is not None:
                alias_type = (
                    "BYTE_IDENTICAL_DUPLICATE_TRANSPORT"
                    if canonical["source_sha256"] == row["source_sha256"]
                    else "SAME_ANNOUNCEMENT_SAME_ECONOMIC_CONTENT_REUPLOAD"
                )
                aliases.append({"ticker": key[0], "as_of_date": key[1], "canonical_record_id": observation_id(canonical), "alias_record_id": observation_id(row), "alias_type": alias_type, "alias_source_sha256": row["source_sha256"], "canonical_source_sha256": canonical["source_sha256"]})
                continue
            canonical_by_signature[signature] = row
            canonical_rows.append(row)
        originals = [row for row in canonical_by_signature.values() if row["revision_kind"] == "ORIGINAL"]
        corrections = sorted((row for row in canonical_by_signature.values() if row["revision_kind"] == "CORRECTION"), key=lambda row: (row["published_at"], row["source_url"]))
        if len(originals) != 1:
            reason = "SOURCE_EVIDENCE_MISSING_NO_ORIGINAL" if len(originals) == 0 else "GENUINE_SOURCE_AMBIGUITY_MULTIPLE_ORIGINALS"
            unresolved.extend({"ticker": key[0], "as_of_date": key[1], "record_id": observation_id(row), "reason": reason, "announcement_no": row["announcement_no"], "source_sha256": row["source_sha256"]} for row in canonical_by_signature.values())
            continue
        active = dict(originals[0])
        active["supersedes_record_id"] = None
        admitted_rows.append(active)
        for correction in corrections:
            if datetime.fromisoformat(correction["published_at"]) <= datetime.fromisoformat(active["published_at"]):
                unresolved.append({"ticker": key[0], "as_of_date": key[1], "record_id": observation_id(correction), "reason": "INVALID_CORRECTION_CHRONOLOGY", "announcement_no": correction["announcement_no"], "source_sha256": correction["source_sha256"]})
                continue
            linked = dict(correction)
            linked["supersedes_record_id"] = observation_id(active)
            admitted_rows.append(linked)
            active = linked
    observations = [make_observation(row) for row in admitted_rows]
    replayed = replay_historical_free_float(observations)
    current = [
        {
            "record_id": row.record_id,
            "ticker": row.ticker,
            "as_of_date": row.as_of_date.isoformat(),
            "published_at": row.published_at.isoformat(),
            "free_float_shares": row.free_float_shares,
            "free_float_pct": row.free_float_pct,
            "total_listed_shares": row.total_listed_shares,
            "source_family": row.source_family.value,
            "revision_kind": row.revision_kind.value,
            "supersedes_record_id": row.supersedes_record_id,
            "announcement_no": row.announcement_no,
            "source_url": row.source_url,
            "source_sha256": row.source_sha256,
            "metadata_source_sha256": row.metadata_source_sha256,
        }
        for row in replayed.current.values()
    ]
    dump_json(output / "normalized/lbre_admitted_observations.json", [observation_payload(row) for row in replayed.admitted])
    dump_json(output / "normalized/lbre_canonical_observations.json", canonical_rows)
    dump_json(output / "normalized/lbre_current_observations.json", current)
    dump_json(output / "reports/lbre_alias_audit.json", aliases)
    dump_json(output / "reports/lbre_lineage_audit.json", {"admitted_count": len(replayed.admitted), "current_count": len(current), "unresolved_count": len(unresolved), "unresolved": unresolved, "lineage_disposition_counts": dict(sorted(Counter(row["reason"] for row in unresolved).items()))})
    dump_json(output / "reports/lbre_replay_summary.json", {"exact_input": len(exact), "canonical_rows": len(canonical_rows), "aliases": len(aliases), "admitted": len(replayed.admitted), "current": len(current), "unresolved": len(unresolved), "revision_counts": dict(sorted(Counter(row.revision_kind.value for row in replayed.admitted).items()))})
    print(json.dumps({"exact": len(exact), "aliases": len(aliases), "admitted": len(replayed.admitted), "current": len(current), "unresolved": len(unresolved)}, indent=2))


def reconcile_and_census(output: Path) -> None:
    current = load_json(output / "normalized/lbre_current_observations.json")
    audit = load_json(output / "reports/lbre_parse_audit.json")["audit_rows"]
    exact = load_json(output / "normalized/lbre_exact_observations.json")
    canonical = load_json(output / "normalized/lbre_canonical_observations.json")
    admitted = load_json(output / "normalized/lbre_admitted_observations.json")
    aliases = load_json(output / "reports/lbre_alias_audit.json")
    unresolved = load_json(output / "reports/lbre_lineage_audit.json")["unresolved"]
    month_rows: dict[str, dict[str, Any]] = {}
    for target in sorted(TARGET_DATE_STRINGS):
        exact_month = [row for row in exact if row["as_of_date"] == target]
        audit_month = [row for row in audit if row.get("as_of_date") == target]
        canonical_month = [row for row in canonical if row["as_of_date"] == target]
        admitted_month = [row for row in admitted if row["as_of_date"] == target]
        aliases_month = [row for row in aliases if row["as_of_date"] == target]
        unresolved_month = [row for row in unresolved if row.get("as_of_date") == target]
        current_month = [row for row in current if row["as_of_date"] == target]
        month_rows[target] = {
            "discovered_position_candidates": len(exact_month) + len(audit_month),
            "download_success_or_reused": len([row for row in exact_month + audit_month if row["status"] in {"DOWNLOADED", "REUSED_PARENT"}]),
            "exact_parsed": len(exact_month),
            "parser_unresolved": len(audit_month),
            "lineage_canonical": len(canonical_month),
            "lineage_aliases": len(aliases_month),
            "lineage_admitted": len(admitted_month),
            "lineage_unresolved": len(unresolved_month),
            "current_exact": len(current_month),
            "current_tickers": sorted({row["ticker"] for row in current_month}),
        }
    market = load_json(PARENT_SNAPSHOT_ROOT / "normalized/market_anchor_2025_12_31.json")
    market_rows = {row["ticker"]: row for row in market["rows"]}
    lbre_rows = {row["ticker"]: row for row in current if row["as_of_date"] == "2025-12-31"}
    reconciliation: list[dict[str, Any]] = []
    for ticker in sorted(set(market_rows) | set(lbre_rows)):
        left, right = lbre_rows.get(ticker), market_rows.get(ticker)
        if left is None or right is None:
            reconciliation.append({"ticker": ticker, "status": "SINGLE_SOURCE", "lbre_present": left is not None, "market_present": right is not None})
        else:
            reconciliation.append({"ticker": ticker, "status": "AGREE" if left["free_float_shares"] == right["free_float_shares"] and abs(float(left["free_float_pct"]) - float(right["free_float_pct"])) <= 0.01 else "CONFLICT", "lbre_shares": left["free_float_shares"], "market_shares": right["free_float_shares"], "lbre_pct": left["free_float_pct"], "market_pct": right["free_float_pct"]})
    dump_json(output / "reports/monthly_census.json", {"target_dates": sorted(TARGET_DATE_STRINGS), "months": month_rows})
    dump_json(output / "reports/reconciliation_2025_12_31.json", {"market_source": market["source"], "counts": dict(sorted(Counter(row["status"] for row in reconciliation).items())), "rows": reconciliation})


def _manifest_entry(path: Path, output: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(output).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def finalize_manifest(output: Path, workers: int = 6) -> str:
    paths = [
        path
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name not in {"artifact_manifest.json", "artifact_manifest.sha256"}
    ]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        files = list(executor.map(lambda path: _manifest_entry(path, output), paths))
    manifest = {"schema": "IDX_LBRE_MONTHLY_FREE_FLOAT_HISTORY_V1", "target_first": min(TARGET_DATE_STRINGS), "target_last": max(TARGET_DATE_STRINGS), "target_count": len(TARGET_DATE_STRINGS), "file_count": len(files), "files": files}
    dump_json(output / "artifact_manifest.json", manifest)
    digest = sha256_file(output / "artifact_manifest.json")
    (output / "artifact_manifest.sha256").write_text(digest + "  artifact_manifest.json\n", encoding="utf-8")
    return digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["discover", "acquire", "parse", "replay", "all"])
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    output = args.output_root
    output.mkdir(parents=True, exist_ok=True)
    verify_parent_manifests(output)
    if args.stage in {"discover", "all"}:
        discover(output)
    if args.stage in {"acquire", "all"}:
        acquire(output, workers=args.workers)
    if args.stage in {"parse", "all"}:
        parse_documents(output, workers=args.workers)
    if args.stage in {"replay", "all"}:
        replay(output)
        reconcile_and_census(output)
        digest = finalize_manifest(output, workers=args.workers)
        print(json.dumps({"manifest_sha256": digest, "output_root": str(output)}, indent=2))


if __name__ == "__main__":
    main()
