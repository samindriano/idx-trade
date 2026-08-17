"""Targeted official-KSEI schedule acquisition for unresolved V4 CA events.

Provider scope is derived only from the immutable KSEI history census and the
frozen event-window semantics.  It does not inspect V4 returns, targets,
predictions, or performance.  Raw index/document responses are append-only and
external.  Missing or ambiguous schedule evidence remains unresolved.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urljoin

from lxml import html
import pandas as pd
from pypdf import PdfReader

from idx_trade.v4_ca_event_windows import classify_event, event_relevant_to_study_period
from idx_trade.v4_ca_schedule_semantics import clean, date_iso, parse_ksei_schedule_transition


PINNED = {
    "continuity_ledger": "52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb",
    "official_calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "ksei_manifest": "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25",
    "ksei_summary": "a046637fbcff69cbc42c09e4cac30d9181b2ce93a3cf7297a9a01cfc23a2f422",
    "ksei_history": "3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d",
}
KSEI_BASE = "https://web.ksei.co.id"
INDEX_TEMPLATE = KSEI_BASE + "/publications/corporate-action-schedules/{slug}?Month={month:02d}&Year={year}&setLocale=id-ID"
MONTH_OFFSETS = (-2, -1, 0, 1, 2)
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 3.0)
INTER_REQUEST_SLEEP = 0.15
SELECTION_HALO_DAYS = 60


SLUGS_BY_SOURCE = {
    "right distribution": ("rights-distribution",),
    "stock dividend": ("share-dividend", "mix-dividend"),
    "mixed dividend": ("mix-dividend",),
    "share bonus": ("share-bonus",),
    "bonus shares": ("share-bonus",),
    "bonus share": ("share-bonus",),
    "bonus distribution": ("share-bonus",),
    "mandatory conversion": ("masr",),
    "voluntary conversion": ("masr",),
    "stock split": ("masr",),
    "reverse stock": ("masr",),
    "reverse stock split": ("masr",),
    "reverse split": ("masr",),
    "merger": ("masr",),
    "capital restructuring": ("masr",),
    "capital reduction": ("masr",),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def make_session() -> Any:
    try:
        from curl_cffi import requests as curl_requests
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("CURL_CFFI_REQUIRED") from exc
    session = curl_requests.Session(impersonate="chrome110")
    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": KSEI_BASE + "/",
            "User-Agent": "Mozilla/5.0",
        }
    )
    return session


def capture_request(
    session: Any,
    *,
    url: str,
    raw_path_prefix: Path,
    timeout_seconds: float,
    request_kind: str,
    request_key: str,
) -> tuple[bytes | None, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        record: dict[str, Any] = {
            "request_kind": request_kind,
            "request_key": request_key,
            "attempt": attempt,
            "requested_url": url,
            "accessed_at_utc": utc_now(),
        }
        try:
            response = session.get(url, timeout=timeout_seconds)
            payload = bytes(getattr(response, "content", b"") or b"")
            suffix = ".pdf" if payload.startswith(b"%PDF") else ".html"
            path = Path(str(raw_path_prefix) + f"_attempt_{attempt:02d}{suffix}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            record.update(
                {
                    "final_url": str(getattr(response, "url", url)),
                    "status_code": int(getattr(response, "status_code", 0) or 0),
                    "content_type": str(getattr(response, "headers", {}).get("content-type", "")),
                    "bytes": len(payload),
                    "sha256": sha256_bytes(payload),
                    "path": str(path),
                }
            )
            attempts.append(record)
            if record["status_code"] == 200 and payload:
                return payload, attempts
            record["error"] = "HTTP_OR_EMPTY"
        except Exception as exc:  # pragma: no cover - transport dependent
            record.update(
                {
                    "status_code": 0,
                    "bytes": 0,
                    "sha256": None,
                    "path": None,
                    "error": f"{type(exc).__name__}:{exc}",
                }
            )
            attempts.append(record)
        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_SECONDS[attempt - 1])
    return None, attempts


def add_month(year: int, month: int, offset: int) -> tuple[int, int]:
    ordinal = year * 12 + (month - 1) + offset
    return ordinal // 12, ordinal % 12 + 1


def event_query_months(event: Any) -> list[tuple[int, int]]:
    months: set[tuple[int, int]] = set()
    for value in event.source_dates:
        for offset in MONTH_OFFSETS:
            months.add(add_month(value.year, value.month, offset))
    return sorted(months)


def source_slugs(source_type: str) -> tuple[str, ...]:
    key = clean(source_type).casefold()
    return SLUGS_BY_SOURCE.get(key, ("masr", "rights-distribution", "share-dividend", "mix-dividend", "share-bonus"))


def parse_index(payload: bytes, *, requested_month: int, requested_year: int) -> list[dict[str, Any]]:
    try:
        document = html.fromstring(payload)
    except Exception as exc:
        raise RuntimeError("KSEI_SCHEDULE_INDEX_INVALID_HTML") from exc
    matches: list[Any] = []
    for table in document.xpath("//table"):
        headers = [clean(cell.text_content()).casefold() for cell in table.xpath(".//thead//th")[:3]]
        if headers in (["nomor surat", "perihal", "tanggal"], ["reference no.", "about", "date"]):
            matches.append(table)
    if len(matches) != 1:
        raise RuntimeError(f"KSEI_SCHEDULE_INDEX_TABLE_COUNT:{len(matches)}")
    rows: list[dict[str, Any]] = []
    for tr in matches[0].xpath(".//tbody/tr"):
        cells = tr.xpath("./td")
        if len(cells) < 3:
            continue
        reference = clean(cells[0].text_content())
        subject = clean(cells[1].text_content())
        document_date = date_iso(clean(cells[2].text_content()))
        hrefs = [a.get("href") for a in tr.xpath(".//a[@href]") if a.get("href")]
        url = urljoin(KSEI_BASE + "/", hrefs[0]) if hrefs else None
        if document_date:
            parsed = pd.Timestamp(document_date)
            if parsed.year != requested_year or parsed.month != requested_month:
                raise RuntimeError(
                    f"KSEI_SCHEDULE_INDEX_MONTH_IDENTITY_MISMATCH:{document_date}:{requested_year}-{requested_month:02d}"
                )
        rows.append(
            {
                "reference": reference,
                "subject": subject,
                "document_date": document_date,
                "document_url": url,
            }
        )
    return rows


def ticker_in_subject(ticker: str, subject: str) -> bool:
    return bool(re.search(rf"(?<![A-Z0-9]){re.escape(ticker)}(?![A-Z0-9])", subject.upper()))


def pdf_text(payload: bytes) -> str:
    reader = PdfReader(BytesIO(payload))
    texts: list[str] = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts)


def document_text(payload: bytes) -> str:
    if payload.startswith(b"%PDF"):
        return pdf_text(payload)
    document = html.fromstring(payload)
    return "\n".join(clean(value) for value in document.xpath("//body//text()") if clean(value))


def compatible_family(source_type: str, parsed_family: str) -> bool:
    source = clean(source_type).casefold()
    if source == "right distribution":
        return parsed_family == "RIGHTS_HMETD"
    if source == "stock dividend":
        return parsed_family in {"STOCK_DIVIDEND", "MIXED_DIVIDEND"}
    if source == "mixed dividend":
        return parsed_family == "MIXED_DIVIDEND"
    if "bonus" in source:
        return parsed_family == "BONUS_SHARES"
    if source == "mandatory conversion":
        return parsed_family in {
            "STOCK_SPLIT",
            "REVERSE_SPLIT",
            "MERGER_OR_RESTRUCTURING",
            "CONVERSION",
        }
    if source == "voluntary conversion":
        return parsed_family in {"CONVERSION", "MERGER_OR_RESTRUCTURING"}
    return parsed_family != "UNKNOWN"


def exact_source_date_link(event: Any, parsed: Any) -> bool:
    source_dates = {value.date().isoformat() for value in event.source_dates}
    document_dates = {value for value in (parsed.record_date, parsed.distribution_date) if value}
    return bool(source_dates & document_dates)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--ksei-census-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    args.output_dir.mkdir(parents=True)
    raw_root = args.output_dir / "raw"
    raw_root.mkdir()

    input_hashes = {
        "continuity_ledger": verify(args.continuity_ledger, PINNED["continuity_ledger"], "continuity_ledger"),
        "official_calendar": verify(args.official_calendar, PINNED["official_calendar"], "official_calendar"),
        "ksei_manifest": verify(args.ksei_census_root / "MANIFEST.json", PINNED["ksei_manifest"], "ksei_manifest"),
        "ksei_summary": verify(args.ksei_census_root / "summary.json", PINNED["ksei_summary"], "ksei_summary"),
        "ksei_history": verify(args.ksei_census_root / "ksei_ca_history.jsonl", PINNED["ksei_history"], "ksei_history"),
    }

    ledger = pd.read_csv(args.continuity_ledger)
    for column in ("entry_date", "terminal_date"):
        ledger[column] = pd.to_datetime(ledger[column], errors="raise").dt.normalize()
    period_start = ledger["entry_date"].min()
    period_end = ledger["terminal_date"].max()

    calendar = pd.read_csv(args.official_calendar)
    calendar["date"] = pd.to_datetime(calendar["date"], errors="raise").dt.normalize()
    official_sessions = calendar["date"].tolist()

    history = read_jsonl(args.ksei_census_root / "ksei_ca_history.jsonl")
    schedule_required: list[Any] = []
    for row in history:
        event = classify_event(row, official_sessions=official_sessions)
        if event.semantic_class != "SCHEDULE_REQUIRED":
            continue
        if event_relevant_to_study_period(
            event,
            period_start=period_start,
            period_end=period_end,
            selection_halo_calendar_days=SELECTION_HALO_DAYS,
        ):
            schedule_required.append(event)

    session = make_session()
    request_records: list[dict[str, Any]] = []
    index_cache: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    candidate_documents: dict[str, dict[str, Any]] = {}

    # Fetch only month/category pages implied by frozen unresolved events.
    for event in schedule_required:
        months = event_query_months(event)
        for slug in source_slugs(event.source_type):
            for year, month in months:
                key = (slug, year, month)
                if key not in index_cache:
                    url = INDEX_TEMPLATE.format(slug=slug, month=month, year=year)
                    prefix = raw_root / "index" / f"{slug}_{year}{month:02d}"
                    payload, attempts = capture_request(
                        session,
                        url=url,
                        raw_path_prefix=prefix,
                        timeout_seconds=args.timeout_seconds,
                        request_kind="SCHEDULE_INDEX",
                        request_key=f"{slug}:{year}-{month:02d}",
                    )
                    request_records.extend(attempts)
                    if payload is None:
                        index_cache[key] = []
                    else:
                        try:
                            index_cache[key] = parse_index(
                                payload,
                                requested_month=month,
                                requested_year=year,
                            )
                        except Exception as exc:
                            index_cache[key] = []
                            request_records.append(
                                {
                                    "request_kind": "SCHEDULE_INDEX_PARSE",
                                    "request_key": f"{slug}:{year}-{month:02d}",
                                    "attempt": 0,
                                    "requested_url": url,
                                    "accessed_at_utc": utc_now(),
                                    "status_code": 200,
                                    "bytes": len(payload),
                                    "sha256": sha256_bytes(payload),
                                    "path": str(prefix),
                                    "error": f"{type(exc).__name__}:{exc}",
                                }
                            )
                    time.sleep(INTER_REQUEST_SLEEP)
                for item in index_cache[key]:
                    if not item.get("document_url"):
                        continue
                    if not ticker_in_subject(event.ticker, str(item.get("subject", ""))):
                        continue
                    candidate_documents[str(item["document_url"])] = {
                        **item,
                        "slug": slug,
                    }

    parse_rows: list[dict[str, Any]] = []
    for index, (url, meta) in enumerate(sorted(candidate_documents.items()), start=1):
        reference_safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(meta.get("reference") or f"doc_{index}"))
        prefix = raw_root / "documents" / reference_safe
        payload, attempts = capture_request(
            session,
            url=url,
            raw_path_prefix=prefix,
            timeout_seconds=args.timeout_seconds,
            request_kind="SCHEDULE_DOCUMENT",
            request_key=str(meta.get("reference") or url),
        )
        request_records.extend(attempts)
        if payload is None:
            parse_rows.append(
                {
                    **meta,
                    "source_url": url,
                    "source_sha256": "",
                    "parse_status": "UNRESOLVED_PROVIDER",
                    "ticker": "",
                    "event_family": "UNKNOWN",
                    "record_date": "",
                    "distribution_date": "",
                    "transition_date": "",
                    "transition_semantic": "",
                    "diagnostics": "PROVIDER_FAILED",
                }
            )
            continue
        digest = sha256_bytes(payload)
        try:
            text = document_text(payload)
            parsed = parse_ksei_schedule_transition(text)
            parse_rows.append(
                {
                    **meta,
                    **asdict(parsed),
                    "diagnostics": "|".join(parsed.diagnostics),
                    "source_url": url,
                    "source_sha256": digest,
                }
            )
        except Exception as exc:
            parse_rows.append(
                {
                    **meta,
                    "source_url": url,
                    "source_sha256": digest,
                    "parse_status": "UNRESOLVED_PARSE",
                    "ticker": "",
                    "event_family": "UNKNOWN",
                    "record_date": "",
                    "distribution_date": "",
                    "transition_date": "",
                    "transition_semantic": "",
                    "diagnostics": f"{type(exc).__name__}:{exc}",
                }
            )
        time.sleep(INTER_REQUEST_SLEEP)

    parse_frame = pd.DataFrame(parse_rows)
    evidence_rows: list[dict[str, Any]] = []
    linkage_audit: list[dict[str, Any]] = []
    for event in schedule_required:
        candidates: list[dict[str, Any]] = []
        for row in parse_rows:
            parsed_ticker = clean(row.get("ticker")).upper()
            parsed_family = clean(row.get("event_family"))
            if row.get("parse_status") != "PARSED_EXACT_TRANSITION":
                continue
            if parsed_ticker != event.ticker:
                continue
            if not compatible_family(event.source_type, parsed_family):
                continue
            # Deterministic economic linkage requires at least one exact
            # Record/Distribution date match to the immutable static history.
            class ParsedProxy:
                record_date = row.get("record_date") or None
                distribution_date = row.get("distribution_date") or None
            if not exact_source_date_link(event, ParsedProxy):
                continue
            candidates.append(row)

        transitions = {
            clean(row.get("transition_date"))
            for row in candidates
            if clean(row.get("transition_date"))
        }
        if len(transitions) == 1:
            transition = next(iter(transitions))
            exact_rows = [row for row in candidates if clean(row.get("transition_date")) == transition]
            refs = sorted({clean(row.get("ksei_reference") or row.get("reference")) for row in exact_rows if clean(row.get("ksei_reference") or row.get("reference"))})
            shas = sorted({clean(row.get("source_sha256")) for row in exact_rows if clean(row.get("source_sha256"))})
            semantics = sorted({clean(row.get("transition_semantic")) for row in exact_rows if clean(row.get("transition_semantic"))})
            if len(semantics) == 1 and refs and shas:
                for row in exact_rows:
                    evidence_rows.append(
                        {
                            "event_id": event.event_id,
                            "ticker": event.ticker,
                            "event_source_type": event.source_type,
                            "linkage_status": "EXACT",
                            "transition_semantic": semantics[0],
                            "transition_date": transition,
                            "ksei_reference": clean(row.get("ksei_reference") or row.get("reference")),
                            "document_date": clean(row.get("document_date")),
                            "source_url": clean(row.get("source_url")),
                            "source_sha256": clean(row.get("source_sha256")),
                            "linkage_basis": "TICKER_FAMILY_AND_EXACT_RECORD_OR_DISTRIBUTION_DATE",
                        }
                    )
                linkage_status = "EXACT"
            else:
                linkage_status = "UNRESOLVED_METADATA"
        elif len(transitions) > 1:
            linkage_status = "CONFLICTING_EXACT_TRANSITIONS"
        else:
            linkage_status = "NO_EXACT_LINKED_TRANSITION"
        linkage_audit.append(
            {
                "event_id": event.event_id,
                "ticker": event.ticker,
                "source_type": event.source_type,
                "source_dates": "|".join(value.date().isoformat() for value in event.source_dates),
                "candidate_document_count": len(candidates),
                "transition_dates": "|".join(sorted(transitions)),
                "linkage_status": linkage_status,
            }
        )

    evidence = pd.DataFrame(evidence_rows)
    if evidence.empty:
        evidence = pd.DataFrame(
            columns=[
                "event_id", "ticker", "event_source_type", "linkage_status",
                "transition_semantic", "transition_date", "ksei_reference",
                "document_date", "source_url", "source_sha256", "linkage_basis"
            ]
        )
    evidence = evidence.drop_duplicates().sort_values(
        ["ticker", "event_id", "transition_date", "ksei_reference"], kind="mergesort"
    ).reset_index(drop=True)
    linkage = pd.DataFrame(linkage_audit).sort_values(
        ["ticker", "source_dates", "event_id"], kind="mergesort"
    ).reset_index(drop=True)

    evidence_path = args.output_dir / "schedule_evidence.csv"
    linkage_path = args.output_dir / "event_schedule_linkage_audit.csv"
    parse_path = args.output_dir / "schedule_document_parse_audit.csv"
    requests_path = args.output_dir / "request_records.jsonl"
    evidence.to_csv(evidence_path, index=False, lineterminator="\n")
    linkage.to_csv(linkage_path, index=False, lineterminator="\n")
    parse_frame.to_csv(parse_path, index=False, lineterminator="\n")
    write_jsonl(requests_path, request_records)

    summary = {
        "schema_version": "v4_ca_schedule_acquisition_v1",
        "status": "V4_CA_TARGETED_KSEI_SCHEDULE_ACQUISITION_COMPLETE",
        "outcome_blind": True,
        "provider_calls": True,
        "source_substitution": False,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "schedule_required_events": len(schedule_required),
        "schedule_required_tickers": len({event.ticker for event in schedule_required}),
        "index_pages_requested": len(index_cache),
        "candidate_documents": len(candidate_documents),
        "parsed_exact_transition_documents": int((parse_frame.get("parse_status", pd.Series(dtype=str)) == "PARSED_EXACT_TRANSITION").sum()),
        "exact_event_links": int((linkage["linkage_status"] == "EXACT").sum()) if len(linkage) else 0,
        "unresolved_event_links": int((linkage["linkage_status"] != "EXACT").sum()) if len(linkage) else 0,
        "input_hashes": input_hashes,
        "policy": {
            "month_offsets": list(MONTH_OFFSETS),
            "max_attempts": MAX_ATTEMPTS,
            "backoff_seconds": list(BACKOFF_SECONDS),
            "exact_link_requires_record_or_distribution_date_match": True,
            "record_or_distribution_never_used_as_transition": True,
            "price_inference": False,
        },
        "output_hashes": {},
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["output_hashes"] = {
        "schedule_evidence": sha256(evidence_path),
        "event_schedule_linkage_audit": sha256(linkage_path),
        "schedule_document_parse_audit": sha256(parse_path),
        "request_records": sha256(requests_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ca_schedule_acquisition_manifest_v1",
        "status": summary["status"],
        "outcome_blind": True,
        "summary_sha256": sha256(summary_path),
        "input_hashes": input_hashes,
        "output_hashes": summary["output_hashes"],
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
