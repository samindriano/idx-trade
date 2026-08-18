"""One-shot offline audit of residual V4 CA events against prior KSEI bytes."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
from typing import Any

from lxml import html
import pandas as pd
from pypdf import PdfReader

from idx_trade.v4_ca_residual_document_semantics import (
    ParsedResidualDocument,
    parse_residual_document,
    resolve_event_document_evidence,
)


POLICY_ID = "V4_CA_RESIDUAL_DOCUMENT_SEMANTICS_V1"
EXPECTED_RESIDUAL_EVENTS = 61
EXPECTED_RESIDUAL_VOLUNTARY = 29
PINS = {
    "stage2_manifest": "5073adb3178a90e71ea9105ddb6ff737896e86a709d1998eefbdb14ca12b6f8c",
    "stage2_request_records": "96a7a2d6013f6a6f86bc7548c9cda90514eb03a50d9b56039ec15c07969f6155",
    "stage2_document_parse_audit": "d7ded2bf29ad8355ff7ce22af89004a4bbe7e7fd0bb01524f582be2ad1e4e796",
    "residual_needs": "aec30360dad932001d04bbb2fb6a2f772f9cfb1930f5a4336a0f699eb924d4be",
    "official_calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise RuntimeError(f"REQUIRED_INPUT_MISSING:{label}:{path}")
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"PINNED_INPUT_HASH_MISMATCH:{label}:{actual}")
    return actual


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _document_text(payload: bytes) -> tuple[str, str]:
    if payload.startswith(b"%PDF"):
        reader = PdfReader(BytesIO(payload))
        plain_parts: list[str] = []
        layout_parts: list[str] = []
        for page in reader.pages:
            plain_parts.append(page.extract_text() or "")
            try:
                layout_parts.append(page.extract_text(extraction_mode="layout") or "")
            except (TypeError, ValueError, NotImplementedError):
                layout_parts.append(page.extract_text() or "")
        return "\n".join(plain_parts), "\n".join(layout_parts)
    document = html.fromstring(payload)
    text = "\n".join(
        " ".join(str(value).split())
        for value in document.xpath("//body//text()")
        if " ".join(str(value).split())
    )
    return text, text


def _successful_documents(stage2_root: Path, request_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for row in request_rows:
        if str(row.get("request_kind")) != "SCHEDULE_DOCUMENT":
            continue
        if int(row.get("status_code") or 0) != 200 or int(row.get("bytes") or 0) <= 0:
            continue
        raw_path = Path(str(row.get("path") or ""))
        if not raw_path.is_file():
            # Preserve fail-closed behavior if the prior absolute root moved.
            candidate = stage2_root / "raw" / "documents" / raw_path.name
            if candidate.is_file():
                raw_path = candidate
            else:
                continue
        key = str(raw_path.resolve())
        if key in seen_paths:
            continue
        seen_paths.add(key)
        recorded_sha = str(row.get("sha256") or "")
        actual_sha = sha256(raw_path)
        if not recorded_sha or actual_sha != recorded_sha:
            raise RuntimeError(f"STAGE2_RAW_DOCUMENT_SHA_MISMATCH:{raw_path}:{actual_sha}")
        payload = raw_path.read_bytes()
        plain, layout = _document_text(payload)
        documents.append(
            {
                "request_key": str(row.get("request_key") or ""),
                "reference": str(row.get("request_key") or ""),
                "source_url": str(row.get("final_url") or row.get("requested_url") or ""),
                "source_sha256": actual_sha,
                "raw_path": str(raw_path),
                "plain_text": plain,
                "layout_text": layout,
            }
        )
    return documents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage2-root", type=Path, required=True)
    parser.add_argument("--residual-needs", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    args.output_dir.mkdir(parents=True)

    manifest_path = args.stage2_root / "MANIFEST.json"
    request_path = args.stage2_root / "request_records.jsonl"
    parse_audit_path = args.stage2_root / "schedule_document_parse_audit.csv"
    input_hashes = {
        "stage2_manifest": verify(manifest_path, PINS["stage2_manifest"], "stage2_manifest"),
        "stage2_request_records": verify(request_path, PINS["stage2_request_records"], "stage2_request_records"),
        "stage2_document_parse_audit": verify(parse_audit_path, PINS["stage2_document_parse_audit"], "stage2_document_parse_audit"),
        "residual_needs": verify(args.residual_needs, PINS["residual_needs"], "residual_needs"),
        "official_calendar": verify(args.official_calendar, PINS["official_calendar"], "official_calendar"),
    }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "V4_CA_TARGETED_KSEI_SCHEDULE_ACQUISITION_COMPLETE":
        raise RuntimeError(f"STAGE2_MANIFEST_STATUS_INVALID:{manifest.get('status')}")
    if manifest.get("outcome_blind") is not True:
        raise RuntimeError("STAGE2_MANIFEST_NOT_OUTCOME_BLIND")
    output_hashes = manifest.get("output_hashes") or {}
    if output_hashes.get("request_records") != PINS["stage2_request_records"]:
        raise RuntimeError("STAGE2_MANIFEST_REQUEST_HASH_MISMATCH")
    if output_hashes.get("schedule_document_parse_audit") != PINS["stage2_document_parse_audit"]:
        raise RuntimeError("STAGE2_MANIFEST_PARSE_HASH_MISMATCH")

    residual = pd.read_csv(args.residual_needs, dtype=str).fillna("")
    if len(residual) != EXPECTED_RESIDUAL_EVENTS:
        raise RuntimeError(f"RESIDUAL_EVENT_COUNT_CHANGED:{len(residual)}")
    if residual["event_id"].duplicated().any():
        raise RuntimeError("RESIDUAL_EVENT_ID_DUPLICATE")
    voluntary_count = int(residual["source_type"].str.casefold().eq("voluntary conversion").sum())
    if voluntary_count != EXPECTED_RESIDUAL_VOLUNTARY:
        raise RuntimeError(f"RESIDUAL_VOLUNTARY_COUNT_CHANGED:{voluntary_count}")

    calendar = pd.read_csv(args.official_calendar)
    if "date" not in calendar.columns:
        raise RuntimeError("OFFICIAL_CALENDAR_DATE_COLUMN_MISSING")
    calendar["date"] = pd.to_datetime(calendar["date"], errors="raise").dt.normalize()
    official_sessions = calendar["date"].tolist()

    request_rows = read_jsonl(request_path)
    raw_documents = _successful_documents(args.stage2_root, request_rows)
    stage2_parse = pd.read_csv(parse_audit_path, dtype=str).fillna("")
    meta_by_url = {
        str(row.source_url): row._asdict()
        for row in stage2_parse.itertuples(index=False)
        if str(getattr(row, "source_url", ""))
    }

    event_evidence_rows: list[dict[str, Any]] = []
    document_audit_rows: list[dict[str, Any]] = []
    for event in residual.to_dict("records"):
        ticker = str(event["ticker"]).upper().strip()
        candidates: list[dict[str, Any]] = []
        for raw in raw_documents:
            meta = meta_by_url.get(raw["source_url"], {})
            index_subject = str(meta.get("subject") or "")
            parsed: ParsedResidualDocument = parse_residual_document(
                raw["plain_text"],
                expected_ticker=ticker,
                index_subject=index_subject,
                layout_text=raw["layout_text"],
            )
            if not parsed.ticker_evidenced:
                continue
            candidate = {
                **raw,
                "reference": str(meta.get("reference") or raw["reference"]),
                "index_subject": index_subject,
                "stage2_parse_status": str(meta.get("parse_status") or ""),
                "parsed": parsed,
            }
            candidates.append(candidate)
            document_audit_rows.append(
                {
                    "event_id": event["event_id"],
                    "ticker": ticker,
                    "event_source_type": event["source_type"],
                    "reference": candidate["reference"],
                    "source_url": raw["source_url"],
                    "source_sha256": raw["source_sha256"],
                    "stage2_parse_status": candidate["stage2_parse_status"],
                    "document_class": parsed.document_class,
                    "event_family": parsed.event_family,
                    "payment_dates": "|".join(parsed.payment_dates),
                    "settlement_dates": "|".join(parsed.settlement_dates),
                    "cash_purchase_dates": "|".join(parsed.cash_purchase_dates),
                    "record_date": parsed.record_date or "",
                    "distribution_date": parsed.distribution_date or "",
                    "transition_date": parsed.transition_date or "",
                    "transition_semantic": parsed.transition_semantic or "",
                    "diagnostics": "|".join(parsed.diagnostics),
                }
            )

        evidence = resolve_event_document_evidence(
            event,
            candidates,
            official_sessions=official_sessions,
        )
        evidence_dict = asdict(evidence)
        event_evidence_rows.append(
            {
                **{key: value for key, value in evidence_dict.items() if key not in {"ksei_references", "source_urls", "source_sha256s", "diagnostics"}},
                "ksei_reference": "|".join(evidence.ksei_references),
                "source_url": "|".join(evidence.source_urls),
                "source_sha256": "|".join(evidence.source_sha256s),
                "diagnostics": "|".join(evidence.diagnostics),
            }
        )

    evidence_frame = pd.DataFrame(event_evidence_rows).sort_values(
        ["ticker", "event_source_type", "event_id"], kind="mergesort"
    )
    if len(evidence_frame) != EXPECTED_RESIDUAL_EVENTS:
        raise RuntimeError("EVENT_EVIDENCE_ROW_COUNT_CHANGED")
    audit_frame = pd.DataFrame(document_audit_rows)
    if not audit_frame.empty:
        audit_frame = audit_frame.sort_values(
            ["ticker", "event_id", "reference", "source_sha256"], kind="mergesort"
        )

    evidence_path = args.output_dir / "residual_event_document_evidence.csv"
    audit_path = args.output_dir / "residual_document_audit.csv"
    evidence_frame.to_csv(evidence_path, index=False, lineterminator="\n")
    audit_frame.to_csv(audit_path, index=False, lineterminator="\n")

    status_counts = evidence_frame["linkage_status"].value_counts().to_dict()
    exact_nonblocking = int(evidence_frame["linkage_status"].eq("EXACT_NON_BLOCKING").sum())
    exact_transition = int(evidence_frame["linkage_status"].eq("EXACT").sum())
    conflicts = int(evidence_frame["linkage_status"].eq("CONFLICT").sum())
    unresolved = int(evidence_frame["linkage_status"].eq("UNRESOLVED").sum())
    summary = {
        "schema_version": "v4_ca_residual_document_semantics_v1",
        "status": "V4_CA_RESIDUAL_DOCUMENT_SEMANTICS_COMPLETE",
        "policy_id": POLICY_ID,
        "outcome_blind": True,
        "provider_calls": False,
        "source_substitution": False,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "residual_events": int(len(evidence_frame)),
        "residual_voluntary_conversion_events": voluntary_count,
        "successful_stage2_raw_documents_verified": int(len(raw_documents)),
        "event_document_candidate_rows": int(len(audit_frame)),
        "exact_nonblocking_events": exact_nonblocking,
        "exact_transition_events": exact_transition,
        "conflict_events": conflicts,
        "unresolved_events": unresolved,
        "linkage_status_counts": {str(key): int(value) for key, value in sorted(status_counts.items())},
        "input_hashes": input_hashes,
        "output_hashes": {
            "residual_event_document_evidence": sha256(evidence_path),
            "residual_document_audit": sha256(audit_path),
        },
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_out = {
        "schema_version": "v4_ca_residual_document_semantics_manifest_v1",
        "created_at_utc": utc_now(),
        "status": summary["status"],
        "outcome_blind": True,
        "provider_calls": False,
        "source_substitution": False,
        "summary_sha256": sha256(summary_path),
        "input_hashes": input_hashes,
        "output_hashes": summary["output_hashes"],
    }
    manifest_out_path = args.output_dir / "MANIFEST.json"
    manifest_out_path.write_text(
        json.dumps(manifest_out, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({**summary, "manifest_sha256": sha256(manifest_out_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
