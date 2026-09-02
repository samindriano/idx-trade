"""Bounded official-source discovery pilot for unresolved RIGHTS_HMETD events.

This runner is deliberately narrower than the V1.1 291-event acquisition
plan.  It loads exactly the 71 unresolved economic events from the controlling
V9 ledger, persists a deterministic <=12-event selection before any provider
request, and never infers a regular-market ex date from a candidate, record,
distribution, listing, or next-session date.

The runner has two explicit phases:

* ``--selection-only`` creates a provisional selection root without provider
  calls.
* ``--execute`` consumes that exact selection and performs one bounded,
  no-retry official KSEI/IDX discovery pass.

The resulting root is outcome-blind and does not touch canonical data,
outcomes, models, counters, or production state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

AUDIT_DATE = "2026-08-30"
SCHEMA = "inc001_rights_hmetd_pilot_v1"
PROJECT_ROOT = Path(r"D:\Documents\Project")
V9_ROOT_NAME = "idx-ca-economic-event-reconciliation-20260829-v9-stock-split-linkage-correction-final"
V9_MANIFEST_SHA256 = "dcc5e05ca3bc5fe7da148629a26fb913a6e85b92a88cbc88180cfde05eec30cc"
KSEI_MASR = "https://web.ksei.co.id/publications/corporate-action-schedules/masr"
KSEI_RIGHTS_DISTRIBUTION = "https://web.ksei.co.id/publications/corporate-action-schedules/rights-distribution"
IDX_ISSUED_HISTORY = "https://www.idx.id/primary/ListingActivity/GetIssuedHistory"
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
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
DATE_TOKEN_RE = r"(\d{1,2})\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember|January|February|March|May|June|July|August|October|December)\s+(\d{4})"
TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
TD_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
HREF_RE = re.compile(r"href=[\"']([^\"']+\.pdf(?:\?[^\"']*)?)[\"']", re.IGNORECASE)
RIGHTS_TITLE_RE = re.compile(
    r"HMETD|RIGHT(?:S)?\s+DISTRIBUTION|HAK\s+MEMESAN|PENAWARAN\s+UMUM\s+TERBATAS",
    re.IGNORECASE,
)
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

RESULT_CLASSES = {
    "RESOLVED_EXACT",
    "OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT",
    "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS",
    "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE",
    "NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED",
    "PROVIDER_DISCOVERY_FAILURE",
}

TARGET_FIELDS = [
    "economic_event_id",
    "ticker",
    "source_event_ids",
    "source_kinds",
    "source_native_labels",
    "candidate_dates",
    "candidate_date",
    "cum_dates",
    "record_dates",
    "distribution_dates",
    "ratio_raw",
    "source_refs",
    "evidence_sha256s",
    "source_contract_ids",
    "missing_semantic",
]
CANDIDATE_FIELDS = [
    "left_economic_event_id",
    "right_economic_event_id",
    "ticker",
    "left_source_kinds",
    "right_source_kinds",
    "left_candidate_dates",
    "right_candidate_dates",
    "date_gap_days",
    "classification",
    "reason",
]
SELECTION_FIELDS = [
    "economic_event_id",
    "ticker",
    "source_kind",
    "candidate_date",
    "temporal_stratum",
    "selection_rank",
    "selection_reason",
]


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value.strip()))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def source_ids(value: Any) -> list[str]:
    raw = text(value)
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        parsed = None
    if isinstance(parsed, list):
        return [text(item) for item in parsed if text(item)]
    return [item for item in raw.split("|") if item]


def iso_date(value: Any) -> str:
    raw = text(value)[:10]
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return ""


def date_values(row: Mapping[str, Any]) -> list[str]:
    return sorted({iso_date(row.get(key)) for key in ("candidate_date", "cum_date", "record_date", "distribution_date") if iso_date(row.get(key))})


def load_targets(v9_root: Path) -> list[dict[str, Any]]:
    manifest = v9_root / "MANIFEST.json"
    if not manifest.is_file() or sha256_file(manifest).lower() != V9_MANIFEST_SHA256.lower():
        raise RuntimeError("controlling V9 manifest hash mismatch")
    events = [
        row
        for row in read_csv(v9_root / "economic_event_ledger.csv")
        if text(row.get("economic_family")) == "RIGHTS_HMETD"
        and text(row.get("transition_status")) == "UNRESOLVED"
    ]
    source_rows = {text(row.get("source_event_id")): row for row in read_csv(v9_root / "source_evidence_ledger.csv")}
    targets: list[dict[str, Any]] = []
    for event in events:
        ids = source_ids(event.get("source_event_ids"))
        rows = [source_rows.get(item) for item in ids]
        if not ids or any(row is None for row in rows):
            raise RuntimeError(f"V9 rights event has missing source evidence: {event.get('economic_event_id')}")
        concrete = [row for row in rows if row is not None]
        tickers = sorted({text(row.get("ticker")).upper() for row in concrete})
        if len(tickers) != 1:
            raise RuntimeError(f"V9 rights event has non-single ticker identity: {event.get('economic_event_id')}")
        candidates = sorted({value for row in concrete for value in date_values(row)})
        if not candidates:
            raise RuntimeError(f"V9 rights event lacks a valid candidate date: {event.get('economic_event_id')}")
        targets.append(
            {
                "economic_event_id": text(event.get("economic_event_id")),
                "ticker": tickers[0],
                "source_event_ids": "|".join(ids),
                "source_kinds": "|".join(sorted({text(row.get("source_kind")) for row in concrete})),
                "source_native_labels": "|".join(sorted({text(row.get("source_native_label")) for row in concrete})),
                "candidate_dates": "|".join(candidates),
                "candidate_date": candidates[0],
                "cum_dates": "|".join(sorted({iso_date(row.get("cum_date")) for row in concrete if iso_date(row.get("cum_date"))})),
                "record_dates": "|".join(sorted({iso_date(row.get("record_date")) for row in concrete if iso_date(row.get("record_date"))})),
                "distribution_dates": "|".join(sorted({iso_date(row.get("distribution_date")) for row in concrete if iso_date(row.get("distribution_date"))})),
                "ratio_raw": "|".join(sorted({text(row.get("ratio_raw")) for row in concrete if text(row.get("ratio_raw"))})),
                "source_refs": "|".join(sorted({text(row.get("source_ref")) for row in concrete if text(row.get("source_ref"))})),
                "evidence_sha256s": "|".join(sorted({text(row.get("evidence_sha256")).lower() for row in concrete if text(row.get("evidence_sha256"))})),
                "source_contract_ids": "|".join(sorted({text(row.get("source_contract_id")) for row in concrete if text(row.get("source_contract_id"))})),
                "missing_semantic": "accepted REGULAR_MARKET_EX_DATE",
            }
        )
    targets.sort(key=lambda row: (row["ticker"], row["candidate_date"], row["economic_event_id"]))
    if len(targets) != 71 or len({row["economic_event_id"] for row in targets}) != 71:
        raise RuntimeError(f"expected exactly 71 unresolved RIGHTS_HMETD events, got {len(targets)}")
    return targets


def _date_gap(left: Mapping[str, Any], right: Mapping[str, Any]) -> int | None:
    left_dates = [date.fromisoformat(item) for item in text(left.get("candidate_dates")).split("|") if iso_date(item)]
    right_dates = [date.fromisoformat(item) for item in text(right.get("candidate_dates")).split("|") if iso_date(item)]
    if not left_dates or not right_dates:
        return None
    return min(abs((a - b).days) for a in left_dates for b in right_dates)


def candidate_linkage_audit(targets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_ticker: dict[str, list[Mapping[str, Any]]] = {}
    for target in targets:
        by_ticker.setdefault(text(target.get("ticker")).upper(), []).append(target)
    for ticker, group in sorted(by_ticker.items()):
        group = sorted(group, key=lambda row: (text(row.get("candidate_date")), text(row.get("economic_event_id"))))
        if len(group) == 1:
            rows.append({"left_economic_event_id": text(group[0].get("economic_event_id")), "right_economic_event_id": "", "ticker": ticker, "left_source_kinds": text(group[0].get("source_kinds")), "right_source_kinds": "", "left_candidate_dates": text(group[0].get("candidate_dates")), "right_candidate_dates": "", "date_gap_days": "", "classification": "NO_CANDIDATE", "reason": "no second unresolved rights economic event for this ticker"})
            continue
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                gap = _date_gap(left, right)
                left_kind = text(left.get("source_kinds"))
                right_kind = text(right.get("source_kinds"))
                if left_kind == right_kind:
                    classification = "PROVEN_DISTINCT"
                    reason = "same-source retained representations have distinct source-event identities and schedules; no cross-source merge is proposed"
                elif gap is not None and gap <= 31:
                    classification = "POSSIBLE_SAME_EVENT"
                    reason = "same ticker and bounded date-compatible cross-source candidate; source bytes do not yet prove identity"
                else:
                    classification = "AMBIGUOUS"
                    reason = "same ticker but date/source semantics do not prove identity or distinctness"
                rows.append({"left_economic_event_id": text(left.get("economic_event_id")), "right_economic_event_id": text(right.get("economic_event_id")), "ticker": ticker, "left_source_kinds": left_kind, "right_source_kinds": right_kind, "left_candidate_dates": text(left.get("candidate_dates")), "right_candidate_dates": text(right.get("candidate_dates")), "date_gap_days": "" if gap is None else str(gap), "classification": classification, "reason": reason})
    return sorted(rows, key=lambda row: (row["ticker"], row["left_economic_event_id"], row["right_economic_event_id"]))


def temporal_stratum(index: int, count: int) -> str:
    if count <= 1 or index / (count - 1) <= 1 / 3:
        return "EARLY"
    if index / (count - 1) <= 2 / 3:
        return "MIDDLE"
    return "RECENT"


def select_source_kind(rows: Sequence[Mapping[str, Any]], source_kind: str, limit: int = 6) -> list[dict[str, Any]]:
    ordered = sorted(
        [row for row in rows if source_kind in text(row.get("source_kinds")).split("|")],
        key=lambda row: (text(row.get("candidate_date")), text(row.get("economic_event_id"))),
    )
    if len(ordered) <= limit:
        chosen = ordered
    else:
        desired = [round(i * (len(ordered) - 1) / (limit - 1)) for i in range(limit)]
        chosen: list[Mapping[str, Any]] = []
        used_tickers: set[str] = set()
        for position in desired:
            candidates = sorted(ordered, key=lambda row: (abs(ordered.index(row) - position), text(row.get("candidate_date")), text(row.get("economic_event_id"))))
            pick = next((row for row in candidates if text(row.get("ticker")) not in used_tickers), None)
            if pick is None:
                pick = candidates[0]
            if pick not in chosen:
                chosen.append(pick)
                used_tickers.add(text(pick.get("ticker")))
        for row in ordered:
            if len(chosen) >= limit:
                break
            if row not in chosen and text(row.get("ticker")) not in used_tickers:
                chosen.append(row)
                used_tickers.add(text(row.get("ticker")))
    result = []
    for rank, row in enumerate(sorted(chosen, key=lambda item: (text(item.get("candidate_date")), text(item.get("economic_event_id")))), start=1):
        item = dict(row)
        item.update({"source_kind": source_kind, "temporal_stratum": temporal_stratum(ordered.index(row), len(ordered)), "selection_rank": str(rank), "selection_reason": "deterministic source-kind/date quantile with ticker diversity preference"})
        result.append(item)
    return result


def select_pilot(targets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected = select_source_kind(targets, "IDX_GET_ISSUED_HISTORY") + select_source_kind(targets, "KSEI_REGISTERED_SECURITY_HISTORY")
    selected.sort(key=lambda row: (text(row.get("source_kind")), text(row.get("candidate_date")), text(row.get("economic_event_id"))))
    if not 1 <= len(selected) <= 12 or len({text(row.get("economic_event_id")) for row in selected}) != len(selected):
        raise RuntimeError("pilot selection is not unique and bounded")
    return selected


def official_url(value: str) -> str:
    value = html.unescape(text(value))
    return "https://web.ksei.co.id" + value if value.startswith("/") else value


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_url(url: str, raw_path: Path, request_number: int, request_kind: str, scope: str) -> dict[str, Any]:
    row: dict[str, Any] = {"request_number": request_number, "request_kind": request_kind, "scope": scope, "requested_url": url, "final_url": "", "request_started_utc": now_utc(), "request_completed_utc": "", "status_code": "", "reason": "", "bytes": 0, "sha256": "", "raw_path": str(raw_path), "error": "", "retrieval_mode": "NEW_OFFICIAL_REQUEST"}
    request = urllib.request.Request(url, headers={"User-Agent": "IDX-Trade/INC001-rights-hmetd-pilot-v1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            raw_path.write_bytes(body)
            row.update({"final_url": response.geturl(), "status_code": int(response.status), "reason": text(response.reason), "bytes": len(body), "sha256": sha256_bytes(body)})
    except urllib.error.HTTPError as exc:
        body = exc.read()
        if body:
            raw_path.write_bytes(body)
        row.update({"final_url": text(exc.geturl()), "status_code": int(exc.code), "reason": text(exc.reason), "bytes": len(body), "sha256": sha256_bytes(body) if body else "", "error": "HTTP_ERROR"})
    except (OSError, urllib.error.URLError) as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    row["request_completed_utc"] = now_utc()
    return row


def strip_html(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_ksei_index(path: Path, request: Mapping[str, Any], source_contract_id: str = "KSEI_MASR_OFFICIAL_INDEX_CONTRACT") -> list[dict[str, Any]]:
    body = path.read_text(encoding="utf-8", errors="replace")
    rows: list[dict[str, Any]] = []
    for fragment in TR_RE.findall(body):
        hrefs = [official_url(item) for item in HREF_RE.findall(fragment)]
        cells = [strip_html(item) for item in TD_RE.findall(fragment)]
        if not hrefs or len(cells) < 2:
            continue
        title = " ".join(cells[1:])
        if not RIGHTS_TITLE_RE.search(title):
            continue
        rows.append({"request_number": request.get("request_number"), "index_raw_path": str(path), "index_sha256": text(request.get("sha256")), "source_ref": hrefs[0], "document_reference": cells[0], "title": title, "published_date_native": cells[2] if len(cells) > 2 else "", "source_contract_id": source_contract_id})
    return rows


def ticker_in_title(title: str, ticker: str) -> bool:
    return bool(re.search(rf"(?<![A-Z0-9]){re.escape(ticker)}(?![A-Z0-9])", title, re.IGNORECASE))


def extract_idx_records(body: bytes, ticker: str, candidate_date: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(body.decode("utf-8", errors="replace"))
    except (TypeError, ValueError, UnicodeDecodeError):
        return []
    records: list[dict[str, Any]] = []
    def visit(value: Any) -> None:
        if isinstance(value, dict):
            code = text(value.get("KodeEmiten")).upper()
            action = text(value.get("JenisTindakan")).lower()
            date_value = text(value.get("TanggalPencatatan"))[:10]
            if code == ticker.upper() and date_value == candidate_date and action in {"hmetd", "right distribution", "rights distribution"}:
                records.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(payload)
    return records


def extract_pdf_text(raw_path: Path, text_path: Path) -> tuple[str, str]:
    if not raw_path.is_file() or raw_path.stat().st_size == 0:
        return "NO_BYTES", ""
    try:
        subprocess.run(["pdftotext", "-enc", "UTF-8", str(raw_path), str(text_path)], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"EXTRACTION_FAILED:{type(exc).__name__}", ""
    return "EXTRACTED", sha256_file(text_path)


def parse_local_date(day: str, month: str, year: str) -> str:
    return f"{int(year):04d}-{MONTHS[month.lower()]:02d}-{int(day):02d}"


def parse_rights_document(entry: Mapping[str, Any], text_path: Path) -> dict[str, Any]:
    body = text_path.read_text(encoding="utf-8", errors="replace") if text_path.is_file() else ""
    def labeled_date(label: str) -> str:
        match = re.search(rf"{label}.{{0,260}}?:?\s*{DATE_TOKEN_RE}", body, re.IGNORECASE | re.DOTALL)
        return parse_local_date(*match.groups()) if match else ""
    ex = labeled_date(r"Tanggal\s+Ex\s+di\s+Pasar\s+(?:Regular|Reguler)\s+dan\s+Pasar\s+Negosiasi")
    cum = labeled_date(r"Tanggal\s+Cum\s+di\s+Pasar\s+(?:Regular|Reguler)\s+dan\s+Pasar\s+Negosiasi")
    record = labeled_date(r"Tanggal\s+Pencatatan(?:\s*\(Recording Date\))?")
    distribution = labeled_date(r"Tanggal\s+Distribusi")
    publication = re.search(rf"Jakarta,\s*{DATE_TOKEN_RE}", body, re.IGNORECASE)
    return {"document_id": text(entry.get("document_id")), "ticker": text(entry.get("ticker")), "document_reference": text(entry.get("document_reference")), "document_title": text(entry.get("title")), "source_ref": text(entry.get("source_ref")), "evidence_sha256": text(entry.get("sha256")).lower(), "actual_sha256": text(entry.get("sha256")).lower(), "bytes": text(entry.get("bytes")), "status_code": text(entry.get("status_code")), "raw_path": text(entry.get("raw_path")), "text_path": str(text_path), "hash_matches_bytes": str(valid_sha(entry.get("sha256")) and Path(text(entry.get("raw_path"))).is_file() and sha256_file(Path(text(entry.get("raw_path")))) == text(entry.get("sha256")).lower()).lower(), "publication_date": parse_local_date(*publication.groups()) if publication else "", "cum_date": cum, "ex_date": ex, "record_date": record, "distribution_date": distribution, "explicit_regular_market_ex_semantic": str(bool(ex)).lower(), "parser_status": "PARSED_EXACT_RIGHTS_SCHEDULE" if ex else "PARSED_BUT_INCOMPLETE_RIGHTS_SCHEDULE", "text_sha256": sha256_file(text_path) if text_path.is_file() else "", "body_contains_rights_semantics": str(bool(RIGHTS_TITLE_RE.search(body) or re.search(r"HMETD|Hak Memesan Efek Terlebih Dahulu", body, re.IGNORECASE))).lower()}


def document_matches_target(doc: Mapping[str, Any], target: Mapping[str, Any]) -> bool:
    candidate_dates = set(text(target.get("candidate_dates")).split("|"))
    schedule_dates = {text(doc.get(key)) for key in ("cum_date", "ex_date", "record_date", "distribution_date") if text(doc.get(key))}
    return bool(candidate_dates & schedule_dates)


def manifest_for(root: Path, provider_calls: bool) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in {"MANIFEST.json"}:
            outputs[str(path.relative_to(root)).replace("\\", "/")] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return {"manifest_version": f"{SCHEMA}_manifest", "artifact_root": str(root), "audit_date": AUDIT_DATE, "outcome_blind": True, "provider_calls": provider_calls, "output_hashes_excluding_manifest": outputs, "self_hash_policy": "MANIFEST.json excluded from its own hash"}


def selection_root(output_root: Path, v9_root: Path) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"immutable pilot root already exists: {output_root}")
    output_root.mkdir(parents=True)
    targets = load_targets(v9_root)
    candidates = candidate_linkage_audit(targets)
    selected = select_pilot(targets)
    write_csv(output_root / "rights_event_scope.csv", targets, TARGET_FIELDS)
    write_csv(output_root / "candidate_linkage_audit.csv", candidates, CANDIDATE_FIELDS)
    write_csv(output_root / "pilot_selection.csv", selected, SELECTION_FIELDS)
    selection = {"schema_version": f"{SCHEMA}_selection", "audit_date": AUDIT_DATE, "controlling_v9_root": str(v9_root), "controlling_v9_manifest_sha256": V9_MANIFEST_SHA256, "rights_total_current": len(targets), "pilot_tested": len(selected), "selected_economic_event_ids": sorted(text(row.get("economic_event_id")) for row in selected), "selection_algorithm": "source-kind stratified deterministic date quantiles with ticker diversity preference", "source_kind_counts": {kind: sum(kind in text(row.get("source_kinds")).split("|") for row in selected) for kind in ("IDX_GET_ISSUED_HISTORY", "KSEI_REGISTERED_SECURITY_HISTORY")}, "provider_lookup_started": False, "provider_calls": False, "guardrails": {"full_71_acquisition": False, "other_ca_acquisition": False, "phase_e": False, "outcomes_or_targets": False, "fit_refit_score": False, "counter_mutation": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False}}
    write_json(output_root / "selection_manifest.json", selection)
    return selection


def prepare_corrected_root(prior_root: Path, output_root: Path) -> dict[str, Any]:
    """Copy only the immutable 12-target selection into a new execution root."""
    if output_root.exists():
        raise FileExistsError(f"immutable corrected pilot root already exists: {output_root}")
    prior_manifest_path = prior_root / "MANIFEST.json"
    required = [prior_root / name for name in ("selection_manifest.json", "rights_event_scope.csv", "candidate_linkage_audit.csv", "pilot_selection.csv", "target_event_results.csv")]
    if not prior_manifest_path.is_file() or any(not path.is_file() for path in required):
        raise RuntimeError("corrected pilot requires the complete prior bounded pilot root")
    prior_manifest_sha = sha256_file(prior_manifest_path)
    prior_selection = read_json(prior_root / "selection_manifest.json")
    if prior_selection.get("provider_calls") or prior_selection.get("pilot_tested") != 12:
        raise RuntimeError("corrected pilot source is not the immutable 12-target selection root")
    output_root.mkdir(parents=True)
    for path in required[:-1]:
        shutil.copyfile(path, output_root / path.name)
    prior_results = read_csv(prior_root / "target_event_results.csv")
    prior_counts = {key: sum(text(row.get("result_classification")) == key for row in prior_results) for key in sorted(RESULT_CLASSES)}
    write_json(output_root / "prior_pilot_reference.json", {"root": str(prior_root), "manifest_sha256": prior_manifest_sha, "target_event_results_sha256": sha256_file(prior_root / "target_event_results.csv"), "pilot_tested": len(prior_results), "classification_counts": prior_counts, "immutable": True})
    return {"prior_root": str(prior_root), "prior_manifest_sha256": prior_manifest_sha, "prior_classification_counts": prior_counts}


def selected_targets(output_root: Path) -> list[dict[str, Any]]:
    """Restore full target identity fields from the immutable 12-row scope."""
    selections = read_csv(output_root / "pilot_selection.csv")
    scope = {text(row.get("economic_event_id")): row for row in read_csv(output_root / "rights_event_scope.csv")}
    selected: list[dict[str, Any]] = []
    for selection in selections:
        event_id = text(selection.get("economic_event_id"))
        if event_id not in scope:
            raise RuntimeError(f"pilot selection references missing rights scope event: {event_id}")
        item = dict(scope[event_id])
        item.update(selection)
        selected.append(item)
    if len(selected) != 12 or len({text(row.get("economic_event_id")) for row in selected}) != 12:
        raise RuntimeError("corrected pilot selection is not exactly 12 unique persisted targets")
    return selected


def execute_pilot(output_root: Path, prior_pilot_root: Path | None = None) -> dict[str, Any]:
    if not output_root.is_dir() or not (output_root / "selection_manifest.json").is_file():
        raise RuntimeError("execute requires an existing selection-only root")
    selection = read_json(output_root / "selection_manifest.json")
    if selection.get("provider_lookup_started") is True or (output_root / "execution_started.json").exists():
        raise RuntimeError("provider execution may not be retried or rerun")
    selected = selected_targets(output_root)
    if len(selected) > 12 or len({text(row.get("economic_event_id")) for row in selected}) != len(selected):
        raise RuntimeError("selection is not bounded and unique")
    (output_root / "execution_started.json").write_text(json.dumps({"started_utc": now_utc(), "provider_lookup_started": True, "no_retry": True}, indent=2) + "\n", encoding="utf-8")
    provider = output_root / "provider"
    for directory in (provider / "index", provider / "idx_event", provider / "documents", provider / "text"):
        directory.mkdir(parents=True, exist_ok=True)
    search_ledger: list[dict[str, Any]] = []
    idx_ledger: list[dict[str, Any]] = []
    document_ledger: list[dict[str, Any]] = []
    index_rows: list[dict[str, Any]] = []
    request_number = 1
    months = sorted({(text(row.get("candidate_date")).split("-")[0], text(row.get("candidate_date")).split("-")[1]) for row in selected})
    for year, month in months:
        url = f"{KSEI_RIGHTS_DISTRIBUTION}?Month={month}&Year={year}&setLocale=id-ID"
        raw = provider / "index" / f"index_{request_number:03d}_{year}{month}.body"
        req = request_url(url, raw, request_number, "KSEI_INDEX", "|".join(sorted({text(row.get("ticker")) for row in selected})))
        search_ledger.append(req)
        if text(req.get("status_code")) == "200" and valid_sha(req.get("sha256")):
            index_rows.extend(parse_ksei_index(raw, req, "KSEI_RIGHTS_DISTRIBUTION_OFFICIAL_INDEX_CONTRACT"))
        request_number += 1
    selected_by_id = {text(row.get("economic_event_id")): row for row in selected}
    match_refs: dict[str, list[dict[str, Any]]] = {key: [] for key in selected_by_id}
    for target_id, target in selected_by_id.items():
        for row in index_rows:
            if ticker_in_title(text(row.get("title")), text(target.get("ticker"))) and text(row.get("source_ref")) not in {item.get("source_ref") for item in match_refs[target_id]}:
                match_refs[target_id].append(row)
    fetched_docs: dict[str, dict[str, Any]] = {}
    for target_id in sorted(selected_by_id):
        target = selected_by_id[target_id]
        if match_refs[target_id]:
            for match in sorted(match_refs[target_id], key=lambda row: text(row.get("source_ref"))):
                url = text(match.get("source_ref"))
                if url in fetched_docs:
                    continue
                number = len(fetched_docs) + 1
                raw = provider / "documents" / f"document_{number:03d}.pdf"
                req = request_url(url, raw, request_number, "KSEI_DOCUMENT", target_id)
                request_number += 1
                req.update({"document_id": f"RIGHTS-PILOT-DOC-{number:03d}", "ticker": text(target.get("ticker")), "document_reference": text(match.get("document_reference")), "title": text(match.get("title")), "index_raw_path": text(match.get("index_raw_path")), "index_sha256": text(match.get("index_sha256")), "source_ref": url, "raw_path": str(raw)})
                txt = provider / "text" / f"document_{number:03d}.txt"
                status, text_sha = extract_pdf_text(raw, txt)
                req.update({"text_status": status, "text_sha256": text_sha})
                document_ledger.append(req)
                fetched_docs[url] = parse_rights_document(req, txt)
        if not match_refs[target_id] or not any(document_matches_target(doc, target) for doc in fetched_docs.values() if ticker_in_title(text(doc.get("document_title")), text(target.get("ticker")))):
            candidate_date = text(target.get("candidate_date"))
            url = f"{IDX_ISSUED_HISTORY}?caType=hmetd&dateFrom={candidate_date.replace('-', '')}&dateTo={candidate_date.replace('-', '')}&start=0&length=250"
            raw = provider / "idx_event" / f"idx_event_{len(idx_ledger) + 1:03d}_{text(target.get('ticker'))}_{candidate_date}.body"
            req = request_url(url, raw, request_number, "IDX_EVENT_EXACT", target_id)
            request_number += 1
            idx_ledger.append(req)
            req["matched_records"] = extract_idx_records(raw.read_bytes(), text(target.get("ticker")), candidate_date) if raw.is_file() else []
    parsed_docs = list(fetched_docs.values())
    results: list[dict[str, Any]] = []
    for target in selected:
        target_id = text(target.get("economic_event_id"))
        docs = [doc for doc in parsed_docs if ticker_in_title(text(doc.get("document_title")), text(target.get("ticker")))]
        exact_docs = [doc for doc in docs if document_matches_target(doc, target)]
        result = dict(target)
        result.update({"prior_result_classification": "", "prior_result_reason": "", "official_document_count": len(docs), "discovered_document_refs": "|".join(sorted({text(doc.get("source_ref")) for doc in docs})), "discovered_document_sha256s": "|".join(sorted({text(doc.get("evidence_sha256")) for doc in docs})), "transition_semantic": "", "transition_date": "", "authority_source_ref": "", "authority_evidence_sha256": "", "transition_status": "UNRESOLVED"})
        if len(exact_docs) > 1:
            result.update({"result_classification": "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS", "reason": "more than one official schedule matches the target candidate dates; no document identity is proven"})
        elif len(exact_docs) == 1:
            doc = exact_docs[0]
            if text(doc.get("status_code")) != "200" or text(doc.get("hash_matches_bytes")) != "true" or not valid_sha(doc.get("evidence_sha256")):
                result.update({"result_classification": "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE", "reason": "official document reference exists but retained bytes/ref/hash are not valid"})
            elif text(doc.get("explicit_regular_market_ex_semantic")) == "true" and iso_date(doc.get("ex_date")):
                result.update({"result_classification": "RESOLVED_EXACT", "reason": "official rights schedule explicitly states Tanggal Ex di Pasar Regular/Reguler dan Pasar Negosiasi", "transition_status": "RESOLVED", "transition_semantic": "REGULAR_MARKET_EX_DATE", "transition_date": iso_date(doc.get("ex_date")), "authority_source_ref": text(doc.get("source_ref")), "authority_evidence_sha256": text(doc.get("evidence_sha256")).lower()})
            else:
                result.update({"result_classification": "OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT", "reason": "official rights document found but accepted regular-market Ex semantic is absent"})
        elif any(text(row.get("matched_records")) not in {"", "[]"} for row in idx_ledger if text(row.get("scope")) == target_id):
            result.update({"result_classification": "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE", "reason": "official IDX event evidence found but no exact transition document was exposed by the bounded path"})
        else:
            requests = [row for row in [*search_ledger, *idx_ledger] if text(row.get("scope")) == target_id or text(row.get("request_kind")) == "KSEI_INDEX"]
            if any(text(row.get("error")) or text(row.get("status_code")) not in {"200", "404"} for row in requests):
                result.update({"result_classification": "PROVIDER_DISCOVERY_FAILURE", "reason": "bounded official discovery request failed"})
            else:
                result.update({"result_classification": "NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED", "reason": "no official event document discovered in bounded KSEI/IDX paths; this is not historical negative authority"})
        results.append(result)
    if len(results) != len(selected) or any(text(row.get("result_classification")) not in RESULT_CLASSES for row in results):
        raise RuntimeError("pilot result conservation/classification validation failed")
    counts = {key: sum(text(row.get("result_classification")) == key for row in results) for key in sorted(RESULT_CLASSES)}
    prior_reference = read_json(output_root / "prior_pilot_reference.json") if (output_root / "prior_pilot_reference.json").is_file() else None
    if prior_reference:
        prior_by_id = {text(row.get("economic_event_id")): row for row in read_csv(Path(prior_reference["root"]) / "target_event_results.csv")}
        for row in results:
            prior = prior_by_id.get(text(row.get("economic_event_id")), {})
            row["prior_result_classification"] = text(prior.get("result_classification"))
            row["prior_result_reason"] = text(prior.get("reason"))
    resolved = [row for row in results if text(row.get("result_classification")) == "RESOLVED_EXACT"]
    if len(resolved) == len(results):
        capability = "HISTORICAL_SOURCE_PATH_PROVEN"
    elif any(text(row.get("result_classification")) == "PROVIDER_DISCOVERY_FAILURE" for row in results):
        capability = "CAPABILITY_NOT_RELIABLY_REPEATABLE"
    elif any(text(row.get("result_classification")) == "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS" for row in results):
        capability = "EVENT_SPECIFIC_MULTI_SOURCE_PATH_REQUIRED"
    else:
        capability = "PARTIAL_HISTORICAL_CAPABILITY"
    write_json(provider / "search_request_ledger.json", search_ledger)
    write_json(provider / "idx_event_request_ledger.json", idx_ledger)
    write_json(provider / "document_request_ledger.json", document_ledger)
    write_csv(output_root / "ksei_index_candidate_rows.csv", index_rows, ["request_number", "index_raw_path", "index_sha256", "source_ref", "document_reference", "title", "published_date_native", "source_contract_id"])
    write_csv(output_root / "official_document_evidence.csv", parsed_docs, sorted({field for row in parsed_docs for field in row}))
    write_csv(output_root / "target_event_results.csv", results, list(results[0].keys()))
    summary = {"schema_version": SCHEMA, "audit_date": AUDIT_DATE, "status": "COMPLETE_BOUNDED_OFFICIAL_RIGHTS_HMETD_PILOT_OUTCOME_BLIND", "controlling_v9_root": selection.get("controlling_v9_root"), "controlling_v9_manifest_sha256": V9_MANIFEST_SHA256, "rights_total_current": 71, "pilot_tested": len(results), "pilot_resolved": len(resolved), "classification_counts": counts, "new_linkages": 0, "remaining_unresolved_pilot_events": len(results) - len(resolved), "rights_source_capability_after_pilot": capability, "discovery_path": {"prior_endpoint": KSEI_MASR, "corrected_endpoint": KSEI_RIGHTS_DISTRIBUTION, "locale": "id-ID", "source_contract_id": "KSEI_RIGHTS_DISTRIBUTION_OFFICIAL_INDEX_CONTRACT"}, "prior_pilot": prior_reference, "prior_classification_counts": prior_reference.get("classification_counts", {}) if prior_reference else {}, "corrected_classification_counts": counts, "source_path_findings": ["The prior pilot queried the general MASR index; this corrected run queries the official rights-distribution index with the same persisted 12 targets.", "A candidate/cum/record/distribution/listing date is not accepted as regular-market Ex authority.", "A positive official document result is event-specific and does not establish historical completeness.", "No retry or bulk acquisition is authorized by this root."], "provider_calls": True, "guardrails": {"full_71_acquisition": False, "other_ca_acquisition": False, "phase_e": False, "outcomes_or_targets": False, "fit_refit_score": False, "counter_mutation": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False}}
    write_json(output_root / "source_path_capability_assessment.json", {"verdict": capability, "classification_counts": counts, "historical_completeness_claim": "NOT_ESTABLISHED"})
    write_json(output_root / "pilot_summary.json", summary)
    write_json(output_root / "MANIFEST.json", manifest_for(output_root, True))
    return summary


def materialize_retained_mppa_evidence(base_root: Path, output_root: Path, retained_root: Path) -> dict[str, Any]:
    """Derive a new root from the corrected run plus one retained official MPPA source.

    This is an offline evidence replay.  It does not call a provider, retry a
    failed request, or change the persisted 12-target selection.
    """
    if output_root.exists():
        raise FileExistsError(f"immutable retained-evidence root already exists: {output_root}")
    required = [
        base_root / "MANIFEST.json",
        base_root / "target_event_results.csv",
        retained_root / "MANIFEST.json",
        retained_root / "raw" / "index" / "rights-distribution_202606_attempt_01.html",
        retained_root / "raw" / "documents" / "KSEI-15669_JKU_0626_attempt_01.pdf",
    ]
    if any(not path.is_file() for path in required):
        raise RuntimeError("retained MPPA materialization requires complete corrected and source roots")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base_root, output_root)
    retained = output_root / "retained_official_evidence"
    retained_index = retained / "index" / "rights-distribution_202606_attempt_01.html"
    retained_pdf = retained / "documents" / "KSEI-15669_JKU_0626_attempt_01.pdf"
    retained_text = retained / "text" / "KSEI-15669_JKU_0626_attempt_01.txt"
    retained_index.parent.mkdir(parents=True, exist_ok=True)
    retained_pdf.parent.mkdir(parents=True, exist_ok=True)
    retained_text.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(required[3], retained_index)
    shutil.copyfile(required[4], retained_pdf)
    retained_index_request = {"request_number": "RETAINED-001", "sha256": sha256_file(retained_index)}
    index_rows = [
        row
        for row in parse_ksei_index(retained_index, retained_index_request, "KSEI_RIGHTS_DISTRIBUTION_OFFICIAL_INDEX_CONTRACT")
        if ticker_in_title(text(row.get("title")), "MPPA")
        and text(row.get("document_reference")) == "KSEI-15669/JKU/0626"
    ]
    if len(index_rows) != 1:
        raise RuntimeError(f"retained MPPA index linkage is not unique: {len(index_rows)}")
    row = index_rows[0]
    if not text(row.get("source_ref")).endswith("MPPA_RIGHT_20260629_ID.pdf"):
        raise RuntimeError("retained MPPA index href mismatch")
    document_request = {"document_id": "RIGHTS-PILOT-RETAINED-MPPA-001", "ticker": "MPPA", "document_reference": text(row.get("document_reference")), "title": text(row.get("title")), "source_ref": text(row.get("source_ref")), "sha256": sha256_file(retained_pdf), "bytes": retained_pdf.stat().st_size, "status_code": 200, "raw_path": str(retained_pdf)}
    extraction_status, text_sha = extract_pdf_text(retained_pdf, retained_text)
    document_request.update({"text_status": extraction_status, "text_sha256": text_sha})
    document = parse_rights_document(document_request, retained_text)
    if text(document.get("explicit_regular_market_ex_semantic")) != "true" or text(document.get("ex_date")) != "2026-06-26":
        raise RuntimeError("retained MPPA document does not prove the accepted regular-market Ex semantic")
    documents_path = output_root / "official_document_evidence.csv"
    documents = read_csv(documents_path) if documents_path.is_file() else []
    documents.append(document)
    write_csv(output_root / "official_document_evidence.csv", documents, sorted({field for item in documents for field in item}))
    results = read_csv(output_root / "target_event_results.csv")
    target_rows = [item for item in results if text(item.get("ticker")) == "MPPA"]
    if len(target_rows) != 1:
        raise RuntimeError("corrected pilot does not contain exactly one MPPA target")
    target = target_rows[0]
    target.update({"official_document_count": "1", "discovered_document_refs": text(document.get("source_ref")), "discovered_document_sha256s": text(document.get("evidence_sha256")), "result_classification": "RESOLVED_EXACT", "reason": "retained official KSEI rights-distribution index row and PDF explicitly state the regular-market Ex date", "transition_status": "RESOLVED", "transition_semantic": "REGULAR_MARKET_EX_DATE", "transition_date": "2026-06-26", "authority_source_ref": text(document.get("source_ref")), "authority_evidence_sha256": text(document.get("evidence_sha256"))})
    write_csv(output_root / "target_event_results.csv", results, list(results[0].keys()))
    base_summary = read_json(output_root / "pilot_summary.json")
    live_counts = dict(base_summary.get("classification_counts", {}))
    counts = {key: sum(text(item.get("result_classification")) == key for item in results) for key in sorted(RESULT_CLASSES)}
    prior_reference = read_json(output_root / "prior_pilot_reference.json") if (output_root / "prior_pilot_reference.json").is_file() else None
    provenance = {"mode": "OFFLINE_REPLAY_OF_RETAINED_OFFICIAL_EVIDENCE", "base_corrected_root": str(base_root), "base_corrected_manifest_sha256": sha256_file(base_root / "MANIFEST.json"), "retained_source_root": str(retained_root), "retained_source_manifest_sha256": sha256_file(retained_root / "MANIFEST.json"), "retained_index_source_ref": "https://web.ksei.co.id/publications/corporate-action-schedules/rights-distribution?Month=06&Year=2026&setLocale=id-ID", "retained_index_raw_sha256": sha256_file(retained_index), "retained_document_source_ref": text(document.get("source_ref")), "retained_document_sha256": text(document.get("evidence_sha256")), "retained_document_reference": text(document.get("document_reference")), "accepted_transition_date": "2026-06-26", "provider_calls_in_this_materialization": False, "selection_unchanged": True}
    write_json(output_root / "retained_evidence_provenance.json", provenance)
    summary = {"schema_version": SCHEMA, "audit_date": AUDIT_DATE, "status": "COMPLETE_BOUNDED_OFFICIAL_RIGHTS_HMETD_PILOT_WITH_RETAINED_MPPA_EVIDENCE", "controlling_v9_root": base_summary.get("controlling_v9_root"), "controlling_v9_manifest_sha256": V9_MANIFEST_SHA256, "rights_total_current": 71, "pilot_tested": len(results), "pilot_resolved": sum(text(item.get("result_classification")) == "RESOLVED_EXACT" for item in results), "classification_counts": counts, "live_corrected_classification_counts": live_counts, "new_linkages": 0, "remaining_unresolved_pilot_events": len(results) - sum(text(item.get("result_classification")) == "RESOLVED_EXACT" for item in results), "rights_source_capability_after_pilot": "PARTIAL_HISTORICAL_CAPABILITY", "discovery_path": base_summary.get("discovery_path", {}), "prior_pilot": prior_reference, "prior_classification_counts": prior_reference.get("classification_counts", {}) if prior_reference else {}, "corrected_classification_counts": counts, "retained_evidence_correction": {"ticker": "MPPA", "result": "RESOLVED_EXACT", "document_reference": text(document.get("document_reference")), "source_ref": text(document.get("source_ref")), "evidence_sha256": text(document.get("evidence_sha256")), "transition_date": "2026-06-26", "source_contract": "KSEI_RIGHTS_DISTRIBUTION_OFFICIAL_INDEX_CONTRACT"}, "source_path_findings": base_summary.get("source_path_findings", []) + ["The live corrected provider result remains separately recorded; MPPA is resolved only by replaying retained official index/PDF bytes with matching source reference, document identity, ticker, and explicit Ex date.", "Historical completeness is not established by this one retained positive document."], "provider_calls": True, "retained_evidence_provider_calls": False, "guardrails": base_summary.get("guardrails", {})}
    write_json(output_root / "source_path_capability_assessment.json", {"verdict": "PARTIAL_HISTORICAL_CAPABILITY", "live_provider_verdict": base_summary.get("rights_source_capability_after_pilot"), "classification_counts": counts, "live_corrected_classification_counts": live_counts, "retained_exact_paths": 1, "historical_completeness_claim": "NOT_ESTABLISHED"})
    write_json(output_root / "pilot_summary.json", summary)
    write_json(output_root / "MANIFEST.json", manifest_for(output_root, True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v9-root", type=Path, default=PROJECT_ROOT / V9_ROOT_NAME)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--prior-pilot-root", type=Path)
    parser.add_argument("--materialize-retained-mppa-from", type=Path)
    parser.add_argument("--retained-mppa-root", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--selection-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.selection_only:
        result = selection_root(args.output_root, args.v9_root)
    elif args.materialize_retained_mppa_from:
        if not args.retained_mppa_root:
            parser.error("--materialize-retained-mppa-from requires --retained-mppa-root")
        result = materialize_retained_mppa_evidence(args.materialize_retained_mppa_from, args.output_root, args.retained_mppa_root)
    elif args.prior_pilot_root:
        prepare_corrected_root(args.prior_pilot_root, args.output_root)
        result = execute_pilot(args.output_root, args.prior_pilot_root)
    else:
        result = execute_pilot(args.output_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
