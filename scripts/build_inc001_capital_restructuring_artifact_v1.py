"""Build one bounded Phase-C CAPITAL_RESTRUCTURING artifact.

The retained V16 ledger is decomposed into the observed 0->0 and nonzero
issued-share-change shapes.  Only the latter subgroup receives one official
IDX announcement discovery request per event.  This is not a generic capital
action crawler and it never promotes a transition from a label, date, or
issued-share count alone.
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


INPUT_MANIFEST_SHA256 = "3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030"
AUDIT_DATE = "2026-08-31"
SCHEMA = "inc001_capital_restructuring_artifact_v1"
IDX_ANNOUNCEMENT_ENDPOINT = "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"
CAPITAL_TERMS = re.compile(
    r"\b(modal|capital|saham|share|pengurangan\s+modal|perubahan\s+modal|"
    r"restrukturisasi|restructuring|konversi|conversion|penggabungan|merger)\b",
    re.IGNORECASE,
)
ACCEPTED_TRANSITION_SEMANTICS = {
    "OLD_SECURITY_LAST_TRADING_DATE",
    "REGULAR_MARKET_EFFECTIVE_BASIS_DATE",
    "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


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


def verify_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "MANIFEST.json"
    if sha256_file(manifest_path) != INPUT_MANIFEST_SHA256:
        raise RuntimeError("controlling V16 manifest hash mismatch")
    manifest = read_json(manifest_path)
    for item in manifest.get("files", []):
        path = root / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"controlling V16 file is not manifest-bound: {path}")
    return manifest


def date_window(candidate: str) -> tuple[str, str]:
    center = date.fromisoformat(candidate[:10])
    return (center - timedelta(days=180)).isoformat(), (center + timedelta(days=180)).isoformat()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text(value)).strip("_.")[:120] or "item"


def artifact_raw_path(raw_path: Any, staging: Path) -> str:
    path = Path(text(raw_path))
    try:
        return path.relative_to(staging).as_posix()
    except ValueError:
        return path.as_posix()


def exact_transition_from_document(document_text: str) -> tuple[str, str]:
    for semantic in sorted(ACCEPTED_TRANSITION_SEMANTICS):
        match = re.search(rf"{re.escape(semantic)}\s*[:=]\s*(\d{{4}}-\d{{2}}-\d{{2}})", document_text, re.IGNORECASE)
        if match:
            return semantic, match.group(1)
    return "", ""


def build(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve()
    output_root = args.output_root.resolve()
    verify_manifest(input_root)
    if output_root.exists():
        raise FileExistsError(f"refuse overwrite existing capital artifact: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"staging capital artifact already exists: {staging}")
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
        )

        sources = read_csv(input_root / "source_evidence_ledger.csv")
        events = read_csv(input_root / "economic_event_ledger.csv")
        source_by_id = {row["source_event_id"]: row for row in sources}
        targets: list[dict[str, str]] = []
        for event in events:
            if event.get("economic_family") != "CAPITAL_RESTRUCTURING":
                continue
            members = [value for value in event.get("source_event_ids", "").split("|") if value]
            if len(members) != 1 or members[0] not in source_by_id:
                raise RuntimeError("capital event must have exactly one retained source")
            source = source_by_id[members[0]]
            raw = Path(source["raw_capture_path"])
            if not raw.is_file() or source.get("source_hash_matches_bytes", "").lower() != "true" or sha256_file(raw) != source["evidence_sha256"].lower():
                raise RuntimeError(f"capital source bytes are not hash-matched: {members[0]}")
            if event.get("transition_status") != "UNRESOLVED" or source.get("source_kind") != "IDX_GET_ISSUED_HISTORY":
                raise RuntimeError(f"unexpected retained capital state: {members[0]}")
            shares = text(source.get("idx_shares"))
            shares_after = text(source.get("idx_shares_after"))
            if shares == "0.0" and shares_after == "0.0":
                group = "ZERO_TO_ZERO_ISSUED_SHARE_MECHANICS"
                acquisition_scope = "PARKED_NO_TARGETED_ACQUISITION"
            elif shares and shares_after and shares != "0.0" and shares_after != "0.0":
                group = "NONZERO_ISSUED_SHARE_CHANGE"
                acquisition_scope = "TARGETED_OFFICIAL_IDX_DISCOVERY"
            else:
                raise RuntimeError(f"unclassified retained capital mechanics: {members[0]}")
            targets.append({
                "economic_event_id": event["economic_event_id"],
                "source_event_id": members[0],
                "ticker": source["ticker"].upper(),
                "candidate_date": source["candidate_date"][:10],
                "source_ref": source["source_ref"],
                "evidence_sha256": source["evidence_sha256"].lower(),
                "raw_capture_path": source["raw_capture_path"],
                "source_native_label": source["source_native_label"],
                "idx_action_id": source["idx_action_id"],
                "idx_date_native": source["idx_date_native"],
                "idx_shares": shares,
                "idx_shares_after": shares_after,
                "mechanics_group": group,
                "acquisition_scope": acquisition_scope,
                "basis_effect": event["basis_effect"],
                "transition_status": "UNRESOLVED",
            })
        if len(targets) != 19:
            raise RuntimeError(f"expected 19 retained capital events, got {len(targets)}")
        groups = {row["mechanics_group"] for row in targets}
        if groups != {"ZERO_TO_ZERO_ISSUED_SHARE_MECHANICS", "NONZERO_ISSUED_SHARE_CHANGE"}:
            raise RuntimeError(f"unexpected capital groups: {groups}")
        group_counts = {group: sum(row["mechanics_group"] == group for row in targets) for group in sorted(groups)}
        if group_counts != {"NONZERO_ISSUED_SHARE_CHANGE": 13, "ZERO_TO_ZERO_ISSUED_SHARE_MECHANICS": 6}:
            raise RuntimeError(f"unexpected capital group counts: {group_counts}")

        requests: list[dict[str, Any]] = []
        announcements: list[dict[str, Any]] = []
        documents: list[dict[str, Any]] = []
        failed_events: set[str] = set()
        attachment_events: dict[str, set[str]] = {}
        fetched_urls: set[str] = set()
        api_root = staging / "raw" / "idx_announcement_api"
        document_root = staging / "raw" / "idx_announcement_attachments"
        selected = [row for row in targets if row["acquisition_scope"] == "TARGETED_OFFICIAL_IDX_DISCOVERY"]
        for number, target in enumerate(sorted(selected, key=lambda row: (row["candidate_date"], row["ticker"])), start=1):
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
                request_kind="IDX_OFFICIAL_CAPITAL_ANNOUNCEMENT",
                request_key=target["economic_event_id"],
            )
            request_row["raw_path"] = artifact_raw_path(request_row.get("raw_path"), staging)
            request_row["economic_event_id"] = target["economic_event_id"]
            requests.append(request_row)
            if payload is None:
                failed_events.add(target["economic_event_id"])
                continue
            try:
                parsed = announcement_payload(payload)
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                request_row["error"] = "IDX_ANNOUNCEMENT_JSON_INVALID"
                failed_events.add(target["economic_event_id"])
                continue
            replies = parsed.get("Replies") or []
            try:
                result_count = int(parsed.get("ResultCount"))
            except (TypeError, ValueError):
                result_count = -1
            request_row.update({"result_count": result_count, "reply_count": len(replies), "pagination_complete": result_count >= 0 and result_count <= 200 and result_count == len(replies)})
            if not request_row["pagination_complete"]:
                request_row["error"] = "IDX_ANNOUNCEMENT_PAGINATION_INCOMPLETE"
                failed_events.add(target["economic_event_id"])
                continue
            for raw_item in replies:
                fields = announcement_fields(raw_item)
                combined = f"{fields.get('title', '')} {fields.get('subject', '')}"
                if fields["ticker"] != target["ticker"] or not CAPITAL_TERMS.search(combined):
                    continue
                announcement = {
                    "economic_event_id": target["economic_event_id"],
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
                    attachment_events.setdefault(url, set()).add(target["economic_event_id"])
                    if url in fetched_urls:
                        continue
                    fetched_urls.add(url)
                    document_path = document_root / f"{len(documents) + 1:03d}_{safe_name(target['ticker'])}_{attachment_name(attachment, url)}"
                    document_request, document_payload = request_once(
                        url,
                        params=None,
                        raw_path=document_path,
                        request_kind="IDX_OFFICIAL_CAPITAL_ANNOUNCEMENT_ATTACHMENT",
                        request_key=hashlib.sha256(url.encode("utf-8")).hexdigest()[:20],
                    )
                    document_request["raw_path"] = artifact_raw_path(document_request.get("raw_path"), staging)
                    document_request["economic_event_id"] = target["economic_event_id"]
                    requests.append(document_request)
                    if document_payload is None:
                        continue
                    extracted = extract_document_text(document_payload)
                    semantic, transition_date = exact_transition_from_document(extracted)
                    documents.append({
                        "economic_event_id": target["economic_event_id"],
                        "source_event_id": target["source_event_id"],
                        "ticker": target["ticker"],
                        "source_ref": url,
                        "evidence_sha256": document_request.get("sha256", ""),
                        "bytes": document_request.get("bytes", 0),
                        "raw_path": document_request.get("raw_path", ""),
                        "text_sha256": sha256_bytes(extracted.encode("utf-8")),
                        "capital_terms_explicit": str(bool(CAPITAL_TERMS.search(extracted))).lower(),
                        "transition_semantic": semantic,
                        "transition_date": transition_date,
                        "linkage_status": "UNRESOLVED",
                        "extraction_status": "EXTRACTED" if extracted else "EMPTY",
                    })

        results: list[dict[str, Any]] = []
        for target in targets:
            event_id = target["economic_event_id"]
            if target["acquisition_scope"] == "PARKED_NO_TARGETED_ACQUISITION":
                classification = "PARKED_ZERO_TO_ZERO_RETAINED_MECHANICS"
                reason = "retained source shows 0->0 issued-share mechanics; no affirmative basis disposition or event-specific transition is proven"
            elif event_id in failed_events:
                classification = "PROVIDER_DISCOVERY_FAILURE"
                reason = "official IDX capital query failed or did not prove complete pagination; no retry performed"
            else:
                event_docs = [row for row in documents if row["economic_event_id"] == event_id]
                event_announcements = [row for row in announcements if row["economic_event_id"] == event_id]
                if not event_announcements and not event_docs:
                    classification = "NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED"
                    reason = "no capital-term official IDX announcement or attachment was retained in the bounded window; not historical negative authority"
                elif event_announcements and not event_docs:
                    classification = "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE"
                    reason = "official capital-term announcement exists but no valid attachment bytes were retained"
                else:
                    classification = "OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT"
                    reason = "official document retained, but old/new security identity and accepted market-basis transition are not jointly proven"
            results.append({**target, "acquisition_classification": classification, "scientific_admission": "FALSE", "transition_status": "UNRESOLVED", "transition_semantic": "", "transition_date": "", "reason": reason})

        selected_manifest = {
            "schema_version": f"{SCHEMA}_selection",
            "audit_date": AUDIT_DATE,
            "controlling_input_root": str(input_root),
            "controlling_input_manifest_sha256": INPUT_MANIFEST_SHA256,
            "retained_event_count": len(targets),
            "targeted_event_count": len(selected),
            "parked_zero_to_zero_count": len(targets) - len(selected),
            "selected_tickers": [row["ticker"] for row in sorted(selected, key=lambda row: row["ticker"])],
            "selection_rule": "target only retained nonzero issued-share changes; park retained 0->0 mechanics",
            "provider_calls": bool(selected),
            "outcome_blind": True,
            "not_historical_negative_authority": True,
        }
        write_json(staging / "selection_manifest.json", selected_manifest)
        write_json(staging / "request_ledger.json", requests)
        write_csv(staging / "official_announcement_candidates.csv", announcements, ["economic_event_id", "source_event_id", "ticker", "announcement_no", "announcement_date", "title", "subject", "announcement_type", "form_id", "source_ref", "source_sha256"])
        write_csv(staging / "official_document_evidence.csv", documents, ["economic_event_id", "source_event_id", "ticker", "source_ref", "evidence_sha256", "bytes", "raw_path", "text_sha256", "capital_terms_explicit", "transition_semantic", "transition_date", "linkage_status", "extraction_status"])
        write_csv(staging / "capital_restructuring_decomposition.csv", sorted(results, key=lambda row: (row["mechanics_group"], row["ticker"])), list(results[0]))
        write_json(staging / "input_provenance.json", {"root": str(input_root), "manifest_sha256": INPUT_MANIFEST_SHA256, "source_kind": "IDX_GET_ISSUED_HISTORY", "source_rows_consumed": 19})
        result_counts = {key: sum(row["acquisition_classification"] == key for row in results) for key in sorted({row["acquisition_classification"] for row in results})}
        summary = {
            "schema_version": SCHEMA,
            "audit_date": AUDIT_DATE,
            "status": "LOCAL_PHASE_C_CAPITAL_RESTRUCTURING_COMPLETE_NO_SCIENTIFIC_ADMISSION",
            "controlling_predecessor": {"root": str(input_root), "manifest_sha256": INPUT_MANIFEST_SHA256},
            "scope": {"economic_family": "CAPITAL_RESTRUCTURING", "event_count": 19, "mechanics_group_counts": group_counts},
            "acquisition": {"targeted_event_count": len(selected), "request_count": len(requests), "result_counts": result_counts, "provider_calls": bool(selected), "no_retry": True},
            "disposition": "No CAPITAL_RESTRUCTURING event is promoted. Retained issued-share mechanics and any discovery failures do not establish an exact old/new market-basis transition or affirmative NON_BASIS semantics.",
            "successor_reconciliation": {"created": False, "reason": "no family, transition, or linkage state changed"},
            "scientific_verdict": {"DATA_ADMISSION": "FAIL", "RESEARCH_ADMISSION": "FAIL", "MODEL_PROMOTION": "NOT_EVALUATED", "REFIT_AUTHORIZED": False, "COUNTER_ACTION": "NONE"},
            "guardrails": {"outcomes_or_targets": False, "fit_refit_score": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False},
        }
        validation = {
            "input_manifest_verified": True,
            "retained_event_count_19": len(results) == 19,
            "zero_to_zero_count_6": group_counts.get("ZERO_TO_ZERO_ISSUED_SHARE_MECHANICS") == 6,
            "nonzero_change_count_13": group_counts.get("NONZERO_ISSUED_SHARE_CHANGE") == 13,
            "all_transitions_unresolved": all(row["transition_status"] == "UNRESOLVED" for row in results),
            "no_non_basis_promotion": all(row["basis_effect"] != "NON_BASIS" for row in results),
            "raw_source_hashes_verified": True,
            "official_request_scope_bounded": len(requests) >= len(selected),
            "no_scientific_admission": True,
        }
        write_json(staging / "reconciliation_summary.json", summary)
        write_json(staging / "validation_report.json", validation)
        manifest = {"schema_version": f"{SCHEMA}_manifest", "audit_date": AUDIT_DATE, "predecessor_manifest_sha256": INPUT_MANIFEST_SHA256, "files": [], "self_hash_policy": "MANIFEST.json excluded from its own hash"}
        for path in sorted(staging.rglob("*")):
            if path.is_file() and path.name != "MANIFEST.json":
                manifest["files"].append({"path": path.relative_to(staging).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        write_json(staging / "MANIFEST.json", manifest)
        staging.rename(output_root)
        return {"summary": summary, "validation": validation, "manifest_sha256": sha256_file(output_root / "MANIFEST.json")}
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
