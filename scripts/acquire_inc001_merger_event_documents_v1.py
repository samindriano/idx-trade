"""Acquire official IDX merger evidence for exactly the current five events.

This is a bounded, outcome-blind acquisition utility. It performs one official
IDX announcement query per selected event, fetches each discovered merger-term
attachment at most once, and never infers a transition from dates or price
movement. It does not touch canonical data, models, outcomes, or production.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(r"D:\Documents\Project")
V15_MANIFEST_SHA256 = "d5a4a21beb2f065502fef3899b3a4f4f7204e0fbbed6f05ae7f4a0119fed6025"
AUDIT_DATE = "2026-08-31"
SCHEMA = "inc001_merger_event_document_acquisition_v1"
IDX_ANNOUNCEMENT_ENDPOINT = "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"
MERGER_TERMS = re.compile(r"\b(merger|penggabungan|gabung\s+usaha|peleburan|konsolidasi)\b", re.IGNORECASE)
ACCEPTED_TRANSITION_SEMANTICS = {
    "REGULAR_MARKET_EX_DATE",
    "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[Mapping[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field, "") for field in fields})


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def date_window(candidate: str) -> tuple[str, str]:
    center = date.fromisoformat(candidate[:10])
    return (center - timedelta(days=180)).isoformat(), (center + timedelta(days=180)).isoformat()


def source_sha_matches(row: Mapping[str, Any]) -> bool:
    path = Path(text(row.get("raw_capture_path")))
    return bool(path.is_file() and sha256_file(path) == text(row.get("evidence_sha256")).lower())


def artifact_raw_path(raw_path: Any, staging: Path) -> str:
    """Store raw captures as stable paths relative to the immutable artifact."""

    path = Path(text(raw_path))
    try:
        return path.relative_to(staging).as_posix()
    except ValueError:
        return path.as_posix()


def load_targets(input_root: Path) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    source = read_csv(input_root / "source_evidence_ledger.csv")
    events = read_csv(input_root / "economic_event_ledger.csv")
    source_by_id = {row["source_event_id"]: row for row in source}
    targets: list[dict[str, str]] = []
    for event in events:
        if text(event.get("economic_family")) != "MERGER":
            continue
        members = [value for value in text(event.get("source_event_ids")).split("|") if value]
        if len(members) != 1 or members[0] not in source_by_id:
            raise RuntimeError("MERGER target must have exactly one source member")
        source_row = source_by_id[members[0]]
        if not source_sha_matches(source_row):
            raise RuntimeError(f"MERGER source bytes are not hash-matched: {members[0]}")
        targets.append({
            "economic_event_id": text(event.get("economic_event_id")),
            "source_event_id": members[0],
            "ticker": text(source_row.get("ticker")).upper(),
            "candidate_date": text(source_row.get("candidate_date"))[:10],
            "ratio_raw": text(source_row.get("ratio_raw")),
            "source_ref": text(source_row.get("source_ref")),
            "source_evidence_sha256": text(source_row.get("evidence_sha256")).lower(),
        })
    if len(targets) != 5 or {row["ticker"] for row in targets} != {"ADMF", "EXCL", "JARR", "MORA", "PGUN"}:
        raise RuntimeError("controlling V15 MERGER scope is not exactly the five authorized events")
    return sorted(targets, key=lambda row: (row["candidate_date"], row["ticker"])), source_by_id


def exact_transition_from_document(document_text: str) -> tuple[str, str]:
    """Return an exact transition only for explicit accepted semantic tokens.

    Natural-language merger documents are retained for review unless a parser
    can identify an accepted semantic and date without interpretation. This
    conservative boundary prevents announcement/record/listing dates from
    becoming market-transition authority.
    """

    for semantic in sorted(ACCEPTED_TRANSITION_SEMANTICS):
        match = re.search(rf"{re.escape(semantic)}\s*[:=]\s*(\d{{4}}-\d{{2}}-\d{{2}})", document_text, re.IGNORECASE)
        if match:
            return semantic, match.group(1)
    return "", ""


def build(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve()
    output_root = args.output_root.resolve()
    manifest_path = input_root / "MANIFEST.json"
    if sha256_file(manifest_path) != V15_MANIFEST_SHA256:
        raise RuntimeError("controlling V15 manifest hash mismatch")
    if output_root.exists():
        raise FileExistsError(f"refuse overwrite existing acquisition root: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"staging acquisition root already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        scripts_root = Path(__file__).resolve().parent
        sys.path.insert(0, str(scripts_root))
        from audit_inc001_rights_hmetd_alternate_v1 import (
            announcement_fields,
            announcement_payload,
            attachment_locator,
            attachment_name,
            extract_document_text,
            official_url,
            request_once,
            safe_name,
        )

        targets, source_by_id = load_targets(input_root)
        api_root = staging / "raw" / "idx_announcement_api"
        document_root = staging / "raw" / "idx_announcement_attachments"
        requests: list[dict[str, Any]] = []
        announcements: list[dict[str, Any]] = []
        documents: list[dict[str, Any]] = []
        failed_events: set[str] = set()
        attachment_events: dict[str, set[str]] = {}
        attachment_announcement_keys: dict[str, set[str]] = {}
        fetched_urls: set[str] = set()

        for number, target in enumerate(targets, start=1):
            event_id = target["economic_event_id"]
            start, end = date_window(target["candidate_date"])
            params = {
                "pageSize": 200,
                "indexFrom": 0,
                "language": "id-id",
                "kodeEmiten": target["ticker"],
                "emitenType": "*",
                "dateFrom": start,
                "dateTo": end,
            }
            request_row, payload = request_once(
                IDX_ANNOUNCEMENT_ENDPOINT,
                params=params,
                raw_path=api_root / f"{number:02d}_{safe_name(target['ticker'])}_{start}_{end}.json",
                request_kind="IDX_OFFICIAL_MERGER_ANNOUNCEMENT",
                request_key=event_id,
            )
            requests.append(request_row)
            request_row["raw_path"] = artifact_raw_path(request_row.get("raw_path"), staging)
            if payload is None:
                failed_events.add(event_id)
                continue
            try:
                parsed = announcement_payload(payload)
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                request_row["error"] = "IDX_ANNOUNCEMENT_JSON_INVALID"
                failed_events.add(event_id)
                continue
            replies = parsed.get("Replies") or []
            try:
                result_count = int(parsed.get("ResultCount"))
            except (TypeError, ValueError):
                result_count = -1
            request_row.update({
                "result_count": result_count,
                "reply_count": len(replies),
                "pagination_complete": result_count >= 0 and result_count <= 200 and result_count == len(replies),
            })
            if not request_row["pagination_complete"]:
                request_row["error"] = "IDX_ANNOUNCEMENT_PAGINATION_INCOMPLETE"
                failed_events.add(event_id)
                continue
            for raw_item in replies:
                fields = announcement_fields(raw_item)
                combined = f"{fields.get('title', '')} {fields.get('subject', '')}"
                if fields["ticker"] != target["ticker"] or not MERGER_TERMS.search(combined):
                    continue
                announcement_key = f"{fields.get('announcement_no', '')}|{fields.get('announcement_date', '')}"
                announcement = {
                    "economic_event_id": event_id,
                    "source_event_id": target["source_event_id"],
                    "ticker": target["ticker"],
                    "announcement_no": fields.get("announcement_no", ""),
                    "announcement_date": fields.get("announcement_date", ""),
                    "title": fields.get("title", ""),
                    "subject": fields.get("subject", ""),
                    "announcement_type": fields.get("announcement_type", ""),
                    "form_id": fields.get("form_id", ""),
                    "source_ref": request_row.get("final_url") or request_row.get("requested_url", ""),
                    "source_sha256": request_row.get("sha256", ""),
                }
                announcements.append(announcement)
                for attachment in fields.get("attachments") or []:
                    if not isinstance(attachment, Mapping):
                        continue
                    url = attachment_locator(attachment)
                    if not url:
                        continue
                    attachment_events.setdefault(url, set()).add(event_id)
                    attachment_announcement_keys.setdefault(url, set()).add(f"{announcement_key}|{url}")
                    if url in fetched_urls:
                        continue
                    fetched_urls.add(url)
                    document_no = len(documents) + 1
                    document_path = document_root / f"{document_no:03d}_{safe_name(target['ticker'])}_{attachment_name(attachment, url)}"
                    document_request, document_payload = request_once(
                        url,
                        params=None,
                        raw_path=document_path,
                        request_kind="IDX_OFFICIAL_MERGER_ANNOUNCEMENT_ATTACHMENT",
                        request_key=hashlib.sha256(url.encode("utf-8")).hexdigest()[:20],
                    )
                    document_request["economic_event_id"] = event_id
                    requests.append(document_request)
                    document_request["raw_path"] = artifact_raw_path(document_request.get("raw_path"), staging)
                    if document_payload is None:
                        continue
                    extracted = extract_document_text(document_payload)
                    semantic, transition_date = exact_transition_from_document(extracted)
                    documents.append({
                        "economic_event_id": event_id,
                        "source_event_id": target["source_event_id"],
                        "ticker": target["ticker"],
                        "announcement_no": fields.get("announcement_no", ""),
                        "announcement_date": fields.get("announcement_date", ""),
                        "title": fields.get("title", ""),
                        "subject": fields.get("subject", ""),
                        "source_ref": url,
                        "evidence_sha256": document_request.get("sha256", ""),
                        "bytes": document_request.get("bytes", 0),
                        "raw_path": document_request.get("raw_path", ""),
                        "text_sha256": hashlib.sha256(extracted.encode("utf-8")).hexdigest(),
                        "merger_terms_explicit": str(bool(MERGER_TERMS.search(extracted))).lower(),
                        "transition_semantic": semantic,
                        "transition_date": transition_date,
                        "associated_event_ids": "",
                        "associated_announcement_keys": "",
                        "linkage_status": "UNRESOLVED",
                        "linkage_reason": "pending exact merger identity and transition audit",
                        "extraction_status": "EXTRACTED" if extracted else "EMPTY",
                    })

        for document in documents:
            url = text(document.get("source_ref"))
            event_ids = sorted(attachment_events.get(url, set()))
            document["associated_event_ids"] = "|".join(event_ids)
            document["associated_announcement_keys"] = "|".join(sorted(attachment_announcement_keys.get(url, set())))
            if len(event_ids) != 1:
                document["linkage_status"] = "AMBIGUOUS_SHARED_ATTACHMENT"
                document["linkage_reason"] = "attachment URL is associated with multiple merger events"
            elif not official_url(url) or not document["evidence_sha256"] or not document["bytes"]:
                document["linkage_status"] = "UNRESOLVED"
                document["linkage_reason"] = "document bytes are not valid official hash-bound evidence"
            elif not document["merger_terms_explicit"] == "true":
                document["linkage_status"] = "UNRESOLVED"
                document["linkage_reason"] = "document does not contain explicit merger terms"
            else:
                document["linkage_reason"] = "official merger document retained; accepted transition/identity contract not proven"

        results: list[dict[str, Any]] = []
        for target in targets:
            event_id = target["economic_event_id"]
            event_announcements = [row for row in announcements if row["economic_event_id"] == event_id]
            event_documents = [row for row in documents if event_id in text(row.get("associated_event_ids")).split("|")]
            exact = [row for row in event_documents if row["linkage_status"] == "LINKED_EXACT" and row["transition_semantic"] in ACCEPTED_TRANSITION_SEMANTICS and row["transition_date"]]
            if event_id in failed_events:
                classification = "PROVIDER_DISCOVERY_FAILURE"
                reason = "official IDX merger query failed or did not prove complete pagination; no retry performed"
            elif not event_announcements and not event_documents:
                classification = "NO_EVENT_SPECIFIC_OFFICIAL_DOCUMENT_DISCOVERED"
                reason = "no merger-term official IDX announcement or attachment was retained in the bounded event window; not historical negative authority"
            elif event_announcements and not event_documents:
                classification = "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE"
                reason = "official merger-term announcement exists but no valid exact attachment bytes were retained"
            elif len(exact) == 1:
                classification = "RESOLVED_EXACT"
                reason = "official attachment passed the exact merger identity and accepted-transition contract"
            elif any(row["linkage_status"] == "AMBIGUOUS_SHARED_ATTACHMENT" for row in event_documents):
                classification = "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS"
                reason = "official attachment association is not unique across selected events"
            else:
                classification = "OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT"
                reason = "official merger evidence exists but predecessor/survivor mechanics and an accepted regular-market transition are not both proven"
            results.append({
                **target,
                "announcement_count": len(event_announcements),
                "document_count": len(event_documents),
                "transition_semantic": exact[0]["transition_semantic"] if len(exact) == 1 else "",
                "transition_date": exact[0]["transition_date"] if len(exact) == 1 else "",
                "authority_source_ref": exact[0]["source_ref"] if len(exact) == 1 else "",
                "authority_evidence_sha256": exact[0]["evidence_sha256"] if len(exact) == 1 else "",
                "result_classification": classification,
                "reason": reason,
            })

        selection = {
            "schema_version": f"{SCHEMA}_selection",
            "audit_date": AUDIT_DATE,
            "controlling_v15_root": str(input_root),
            "controlling_v15_manifest_sha256": V15_MANIFEST_SHA256,
            "selected_count": len(targets),
            "selected_economic_event_ids": [row["economic_event_id"] for row in targets],
            "selected_tickers": [row["ticker"] for row in targets],
            "request_policy": "one official IDX announcement query per exact event; one fetch per discovered attachment URL; no retry",
            "provider_calls": True,
            "outcome_blind": True,
            "not_historical_negative_authority": True,
        }
        write_json(staging / "selection_manifest.json", selection)
        write_json(staging / "request_ledger.json", requests)
        write_csv(staging / "official_announcement_candidates.csv", announcements, list(announcements[0]) if announcements else ["economic_event_id", "source_event_id", "ticker", "announcement_no", "announcement_date", "title", "subject", "announcement_type", "form_id", "source_ref", "source_sha256"])
        write_csv(staging / "official_document_evidence.csv", documents, [
            "economic_event_id", "source_event_id", "ticker", "announcement_no", "announcement_date", "title", "subject", "source_ref", "evidence_sha256", "bytes", "raw_path", "text_sha256", "merger_terms_explicit", "transition_semantic", "transition_date", "associated_event_ids", "associated_announcement_keys", "linkage_status", "linkage_reason", "extraction_status",
        ])
        write_csv(staging / "target_event_results.csv", results, list(results[0]))
        summary = {
            "schema_version": SCHEMA,
            "audit_date": AUDIT_DATE,
            "status": "LOCAL_MERGER_ACQUISITION_COMPLETE_NO_SCIENTIFIC_ADMISSION",
            "controlling_v15_root": str(input_root),
            "controlling_v15_manifest_sha256": V15_MANIFEST_SHA256,
            "selected_count": len(targets),
            "request_count": len(requests),
            "announcement_candidate_count": len(announcements),
            "document_count": len(documents),
            "result_counts": dict(sorted({key: sum(row["result_classification"] == key for row in results) for key in sorted({row["result_classification"] for row in results})}.items())),
            "no_retry": True,
            "provider_calls": True,
            "outcomes_or_targets": False,
            "model_or_score": False,
            "canonical_historical_rewrite": False,
            "production_execution": False,
        }
        write_json(staging / "acquisition_summary.json", summary)
        manifest = {
            "schema_version": f"{SCHEMA}_manifest",
            "audit_date": AUDIT_DATE,
            "controlling_v15_manifest_sha256": V15_MANIFEST_SHA256,
            "provider_calls": True,
            "outcome_blind": True,
            "files": [],
            "self_hash_policy": "MANIFEST.json excluded from its own hash",
        }
        for path in sorted(staging.rglob("*")):
            if path.is_file() and path.name != "MANIFEST.json":
                manifest["files"].append({"path": str(path.relative_to(staging)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        write_json(staging / "MANIFEST.json", manifest)
        staging.rename(output_root)
        return {"summary": summary, "manifest_sha256": sha256_file(output_root / "MANIFEST.json")}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
