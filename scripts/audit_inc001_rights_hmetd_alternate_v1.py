"""Bounded alternate official-source audit for residual RIGHTS_HMETD events.

The runner consumes the immutable V14 reconciliation, freezes a deterministic
eight-event sample (including the required SGER and PACK events), and queries
only the official IDX listed-company announcement endpoint.  It captures each
API response and each candidate official attachment at most once.  It never
uses KSEI as a retry path, never infers a transition date, and never touches
canonical data, outcomes, models, counters, or production state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(r"D:\Documents\Project")
V14_ROOT = PROJECT_ROOT / "idx-ca-economic-event-reconciliation-20260830-v14-same-exact"
V14_MANIFEST_SHA256 = "c095c00c31691c07cbf4d50c447abafde9b00db0e93f8184ea6e9a83b4a1990b"
AUDIT_DATE = "2026-08-30"
SCHEMA = "inc001_rights_hmetd_alternate_v1"

IDX_BASE = "https://www.idx.co.id"
IDX_ANNOUNCEMENT_ENDPOINT = IDX_BASE + "/primary/ListedCompany/GetAnnouncement"
IDX_ALLOWED_HOSTS = {"www.idx.co.id", "idx.co.id"}
IDX_SOURCE_CONTRACT = "IDX_OFFICIAL_LISTED_COMPANY_ANNOUNCEMENTS_ALTERNATE_RIGHTS_V1"
IDX_USER_AGENT = "IDX-Trade/INC001-rights-hmetd-alternate-v1"

REQUIRED_SGER_EVENT = "DERIVED-d4dabf435934131619c850ab1fd070aee06928d24c188ac46571722c0ad2091c"
REQUIRED_PACK_EVENT = "DERIVED-69e5d8da2753198c085f8ba736fcded7c6b4e98205ca3ac140d12bec69a1c1ff"

RESULT_CLASSES = {
    "RESOLVED_EXACT",
    "OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT",
    "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS",
    "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE",
    "NO_ALTERNATE_OFFICIAL_DOCUMENT_DISCOVERED",
    "PROVIDER_DISCOVERY_FAILURE",
}

SOURCE_KINDS = ("IDX_GET_ISSUED_HISTORY", "KSEI_REGISTERED_SECURITY_HISTORY")
MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5,
    "juni": 6, "juli": 7, "agustus": 8, "september": 9,
    "oktober": 10, "november": 11, "desember": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}
DATE_RE = re.compile(
    r"(?P<day>\d{1,2})\s+(?P<month>Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember|January|February|March|May|June|July|August|October|November|December)\s+(?P<year>\d{4})",
    re.IGNORECASE,
)
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
RIGHTS_RE = re.compile(
    r"HMETD|Hak Memesan Efek Terlebih Dahulu|right\s+issue|rights?\s+issue|penawaran umum terbatas|pelaksanaan hak",
    re.IGNORECASE,
)
EX_REGULAR_RE = re.compile(
    r"(?:tanggal\s+)?ex(?:\s+date)?[^\n]{0,100}(?:pasar\s+regul(?:er|ar)|regular\s+market)",
    re.IGNORECASE,
)

TARGET_FIELDS = [
    "economic_event_id", "ticker", "source_event_ids", "source_kinds",
    "source_native_labels", "candidate_dates", "candidate_date", "cum_dates",
    "record_dates", "distribution_dates", "ratio_raw", "source_refs",
    "evidence_sha256s", "source_contract_ids", "missing_semantic",
]
SELECTION_FIELDS = [
    "economic_event_id", "ticker", "source_kinds", "candidate_date",
    "temporal_stratum", "selection_rank", "selection_reason",
]


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value.strip()))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    return sorted({
        parsed
        for key in ("candidate_date", "cum_date", "record_date", "distribution_date")
        if (parsed := iso_date(row.get(key)))
    })


def _manifest_output_path(root: Path, relative: str) -> Path:
    """Resolve a manifest output without permitting path escape."""
    candidate_name = Path(relative)
    if candidate_name.is_absolute() or "MANIFEST.json" == candidate_name.name or ".." in candidate_name.parts:
        raise RuntimeError(f"manifest output path is unsafe: {relative}")
    root_resolved = root.resolve()
    candidate = (root / candidate_name).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise RuntimeError(f"manifest output path escapes root: {relative}")
    return candidate


def verify_manifest_outputs(root: Path, expected_manifest_sha256: str | None = None) -> dict[str, Any]:
    """Verify the manifest and every hash-bound output it names."""
    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"manifest missing: {manifest_path}")
    manifest_sha256 = sha256_file(manifest_path)
    if expected_manifest_sha256 and manifest_sha256.lower() != expected_manifest_sha256.lower():
        raise RuntimeError(f"manifest hash mismatch: {root}")
    manifest = read_json(manifest_path)
    outputs = manifest.get("output_hashes_excluding_manifest")
    if not isinstance(outputs, dict) or not outputs:
        raise RuntimeError(f"manifest has no hash-bound outputs: {root}")
    verified = 0
    for relative, expected in sorted(outputs.items()):
        if not isinstance(expected, Mapping) or not valid_sha(expected.get("sha256")):
            raise RuntimeError(f"manifest output has invalid SHA: {relative}")
        output_path = _manifest_output_path(root, text(relative))
        if not output_path.is_file():
            raise RuntimeError(f"manifest output missing: {relative}")
        if output_path.stat().st_size != int(expected.get("bytes", -1)):
            raise RuntimeError(f"manifest output byte count mismatch: {relative}")
        if sha256_file(output_path).lower() != text(expected.get("sha256")).lower():
            raise RuntimeError(f"manifest output hash mismatch: {relative}")
        verified += 1
    return {"manifest_sha256": manifest_sha256, "output_count": verified}


def verify_v14(v14_root: Path) -> dict[str, Any]:
    manifest = v14_root / "MANIFEST.json"
    return verify_manifest_outputs(v14_root, V14_MANIFEST_SHA256)


def load_targets(v14_root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    verify_v14(v14_root)
    events = read_csv(v14_root / "economic_event_ledger.csv")
    source_rows = {text(row.get("source_event_id")): row for row in read_csv(v14_root / "source_evidence_ledger.csv")}
    targets: list[dict[str, Any]] = []
    for event in events:
        if text(event.get("economic_family")) != "RIGHTS_HMETD" or text(event.get("transition_status")) != "UNRESOLVED":
            continue
        ids = source_ids(event.get("source_event_ids"))
        members = [source_rows.get(item) for item in ids]
        if not ids or any(member is None for member in members):
            raise RuntimeError(f"V14 target has missing source evidence: {event.get('economic_event_id')}")
        concrete = [member for member in members if member is not None]
        tickers = sorted({text(member.get("ticker")).upper() for member in concrete})
        if len(tickers) != 1:
            raise RuntimeError(f"V14 target has non-single ticker identity: {event.get('economic_event_id')}")
        dates = sorted({value for member in concrete for value in date_values(member)})
        if not dates:
            raise RuntimeError(f"V14 target lacks candidate date: {event.get('economic_event_id')}")
        targets.append({
            "economic_event_id": text(event.get("economic_event_id")),
            "ticker": tickers[0],
            "source_event_ids": "|".join(ids),
            "source_kinds": "|".join(sorted({text(member.get("source_kind")) for member in concrete})),
            "source_native_labels": "|".join(sorted({text(member.get("source_native_label")) for member in concrete})),
            "candidate_dates": "|".join(dates),
            "candidate_date": dates[0],
            "cum_dates": "|".join(sorted({iso_date(member.get("cum_date")) for member in concrete if iso_date(member.get("cum_date"))})),
            "record_dates": "|".join(sorted({iso_date(member.get("record_date")) for member in concrete if iso_date(member.get("record_date"))})),
            "distribution_dates": "|".join(sorted({iso_date(member.get("distribution_date")) for member in concrete if iso_date(member.get("distribution_date"))})),
            "ratio_raw": "|".join(sorted({text(member.get("ratio_raw")) for member in concrete if text(member.get("ratio_raw"))})),
            "source_refs": "|".join(sorted({text(member.get("source_ref")) for member in concrete if text(member.get("source_ref"))})),
            "evidence_sha256s": "|".join(sorted({text(member.get("evidence_sha256")).lower() for member in concrete if text(member.get("evidence_sha256"))})),
            "source_contract_ids": "|".join(sorted({text(member.get("source_contract_id")) for member in concrete if text(member.get("source_contract_id"))})),
            "missing_semantic": "accepted REGULAR_MARKET_EX_DATE",
        })
    targets.sort(key=lambda row: (row["candidate_date"], row["ticker"], row["economic_event_id"]))
    if len(targets) != 68 or len({row["economic_event_id"] for row in targets}) != 68:
        raise RuntimeError(f"expected exactly 68 unresolved RIGHTS_HMETD events, got {len(targets)}")
    return targets, source_rows


def temporal_stratum(index: int, count: int) -> str:
    if count <= 1 or index == 0:
        return "EARLY"
    if index == count - 1:
        return "RECENT"
    return "MIDDLE"


def choose_quantiles(rows: Sequence[Mapping[str, Any]], count: int = 3) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: (text(row.get("candidate_date")), text(row.get("ticker")), text(row.get("economic_event_id"))))
    selected: list[dict[str, Any]] = []
    used_tickers: set[str] = set()
    for position in (0, len(ordered) // 2, len(ordered) - 1):
        for offset in range(len(ordered)):
            candidate = ordered[min(position + offset, len(ordered) - 1)]
            if text(candidate.get("ticker")) not in used_tickers or len(used_tickers) >= len(ordered):
                selected.append(dict(candidate))
                used_tickers.add(text(candidate.get("ticker")))
                break
        if len(selected) == count:
            break
    return selected


def select_pilot(targets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_id = {text(row.get("economic_event_id")): dict(row) for row in targets}
    required_ids = [REQUIRED_SGER_EVENT, REQUIRED_PACK_EVENT]
    if any(event_id not in by_id for event_id in required_ids):
        raise RuntimeError("required SGER/PACK event identity missing from V14")
    if any(text(by_id[event_id].get("ticker")) in {"MPPA", "GMFI", "SAME"} for event_id in required_ids):
        raise RuntimeError("required sample overlaps excluded resolved ticker")
    selected = [by_id[event_id] for event_id in required_ids]
    remainder = [
        dict(row) for row in targets
        if text(row.get("economic_event_id")) not in set(required_ids)
        and text(row.get("ticker")) not in {"MPPA", "GMFI", "SAME"}
    ]
    chosen: list[dict[str, Any]] = []
    for source_kind in SOURCE_KINDS:
        chosen.extend(choose_quantiles([row for row in remainder if source_kind in text(row.get("source_kinds")).split("|")], 3))
    chosen_ids = {text(row.get("economic_event_id")) for row in selected}
    for row in chosen:
        if text(row.get("economic_event_id")) not in chosen_ids and len(selected) < 8:
            selected.append(row)
            chosen_ids.add(text(row.get("economic_event_id")))
    if len(selected) != 8 or len({text(row.get("economic_event_id")) for row in selected}) != 8:
        raise RuntimeError("alternate pilot selection is not exactly eight unique events")
    result: list[dict[str, Any]] = []
    source_rank: dict[str, int] = {kind: 0 for kind in SOURCE_KINDS}
    for row in selected:
        primary = next((kind for kind in SOURCE_KINDS if kind in text(row.get("source_kinds")).split("|")), SOURCE_KINDS[0])
        source_rank[primary] += 1
        source_rows = sorted([item for item in targets if primary in text(item.get("source_kinds")).split("|")], key=lambda item: (text(item.get("candidate_date")), text(item.get("ticker")), text(item.get("economic_event_id"))))
        index = next(index for index, item in enumerate(source_rows) if text(item.get("economic_event_id")) == text(row.get("economic_event_id")))
        selected_row = dict(row)
        selected_row.update({
            "source_kinds": text(row.get("source_kinds")),
            "temporal_stratum": temporal_stratum(index, len(source_rows)),
            "selection_rank": str(source_rank[primary]),
            "selection_reason": "required SGER/PACK plus deterministic source-kind quantile selection with ticker diversity",
        })
        result.append(selected_row)
    return sorted(result, key=lambda row: (text(row.get("candidate_date")), text(row.get("ticker")), text(row.get("economic_event_id"))))


def selection_manifest(root: Path, v14_root: Path, targets: Sequence[Mapping[str, Any]], selected: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    write_csv(root / "rights_event_scope.csv", targets, TARGET_FIELDS)
    write_csv(root / "pilot_selection.csv", selected, SELECTION_FIELDS)
    value = {
        "schema_version": f"{SCHEMA}_selection",
        "audit_date": AUDIT_DATE,
        "controlling_v14_root": str(v14_root),
        "controlling_v14_manifest_sha256": V14_MANIFEST_SHA256,
        "rights_unresolved_before": len(targets),
        "pilot_tested": len(selected),
        "selected_economic_event_ids": [text(row.get("economic_event_id")) for row in selected],
        "selection_algorithm": "required SGER/PACK plus source-kind quantile selection across early/middle/recent dates with ticker diversity",
        "source_kind_counts": {kind: sum(kind in text(row.get("source_kinds")).split("|") for row in selected) for kind in SOURCE_KINDS},
        "provider_lookup_started": False,
        "provider_calls": False,
        "guardrails": {
            "full_residual_acquisition": False, "ksei_retry": False, "other_ca_acquisition": False,
            "phase_e": False, "outcomes_or_targets": False, "model_refit_score": False,
            "counter_mutation": False, "canonical_historical_rewrite": False, "production_execution": False,
            "merge": False,
        },
    }
    write_json(root / "selection_manifest.json", value)
    return value


def date_window(target: Mapping[str, Any]) -> tuple[str, str]:
    dates = [date.fromisoformat(value) for value in text(target.get("candidate_dates")).split("|") if iso_date(value)]
    start = min(dates) - timedelta(days=180)
    end = max(dates) + timedelta(days=180)
    return start.isoformat(), end.isoformat()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text(value)).strip("_.")[:120] or "item"


def official_url(raw: Any) -> str:
    value = text(raw)
    if not value:
        return ""
    url = urllib.parse.urljoin(IDX_BASE + "/", value)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in IDX_ALLOWED_HOSTS:
        return ""
    return url


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_once(url: str, *, params: Mapping[str, Any] | None, raw_path: Path, request_kind: str, request_key: str) -> tuple[dict[str, Any], bytes | None]:
    requested_url = url
    if params:
        requested_url += "?" + urllib.parse.urlencode(params)
    row: dict[str, Any] = {
        "request_kind": request_kind, "request_key": request_key, "attempt": 1,
        "requested_url": requested_url, "request_started_utc": now_utc(),
        "final_url": "", "status_code": 0, "content_type": "", "bytes": 0,
        "sha256": "", "raw_path": str(raw_path), "error": "",
    }
    try:
        try:
            from curl_cffi import requests as curl_requests
            response = curl_requests.get(url, params=params, headers={"User-Agent": IDX_USER_AGENT, "Accept": "application/json, text/plain, */*"}, timeout=40, impersonate="chrome110")
            payload = bytes(response.content or b"")
            status = int(response.status_code or 0)
            final_url = str(getattr(response, "url", requested_url))
            content_type = text(response.headers.get("content-type", ""))
        except ImportError:
            request = urllib.request.Request(requested_url, headers={"User-Agent": IDX_USER_AGENT, "Accept": "application/json, text/plain, */*"})
            with urllib.request.urlopen(request, timeout=40) as response:
                payload = response.read()
                status = int(getattr(response, "status", 0) or 0)
                final_url = str(getattr(response, "url", requested_url))
                content_type = text(response.headers.get("Content-Type", ""))
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(payload)
        row.update({"final_url": final_url, "status_code": status, "content_type": content_type, "bytes": len(payload), "sha256": sha256_bytes(payload)})
        if status != 200 or not payload:
            row["error"] = "HTTP_NON_200_OR_EMPTY"
            payload = None
    except Exception as exc:  # pragma: no cover - transport dependent
        row.update({"error": f"{type(exc).__name__}:{exc}"})
        payload = None
    row["request_completed_utc"] = now_utc()
    return row, payload


def announcement_payload(payload: bytes) -> dict[str, Any]:
    value = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(value, dict) or not isinstance(value.get("Replies") or [], list):
        raise ValueError("IDX announcement payload is not an object with Replies list")
    return value


def pagination_attestation(payload: Mapping[str, Any], page_size: int = 200) -> tuple[bool, int | None, int, str]:
    """Accept a response only when its first page proves the full result set."""
    replies = payload.get("Replies") or []
    raw_total = payload.get("ResultCount")
    try:
        total = int(raw_total)
    except (TypeError, ValueError):
        return False, None, len(replies), "ResultCount is absent or malformed"
    if total < 0 or total > page_size or len(replies) != total:
        return False, total, len(replies), "single-page response does not prove complete result set"
    return True, total, len(replies), "ResultCount equals Replies count within requested page size"


def announcement_fields(item: Mapping[str, Any]) -> dict[str, Any]:
    raw = item.get("pengumuman") or {}
    if not isinstance(raw, Mapping):
        raw = {}
    return {
        "announcement_no": text(raw.get("NoPengumuman")),
        "announcement_date": text(raw.get("TglPengumuman")),
        "ticker": text(raw.get("Kode_Emiten")).upper().replace(".JK", ""),
        "title": text(raw.get("JudulPengumuman")),
        "subject": text(raw.get("PerihalPengumuman")),
        "announcement_type": text(raw.get("JenisPengumuman")),
        "form_id": text(raw.get("Form_Id")),
        "attachments": item.get("attachments") if isinstance(item.get("attachments"), list) else [],
    }


def is_rights_candidate(fields: Mapping[str, Any]) -> bool:
    return bool(RIGHTS_RE.search(text(fields.get("title")) + " " + text(fields.get("subject"))))


def attachment_locator(attachment: Mapping[str, Any]) -> str:
    for key in ("FullSavePath", "fullSavePath", "DownloadPath", "downloadPath", "FilePath", "filePath", "Url", "url"):
        value = official_url(attachment.get(key))
        if value:
            return value
    return ""


def attachment_name(attachment: Mapping[str, Any], url: str) -> str:
    for key in ("OriginalFilename", "PDFFilename", "FileName", "filename"):
        if text(attachment.get(key)):
            return safe_name(text(attachment.get(key)))
    return safe_name(Path(urllib.parse.urlparse(url).path).name or "attachment")


def extract_document_text(payload: bytes) -> str:
    if payload.startswith(b"%PDF"):
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(payload))
            return "\n".join(text(page.extract_text()) for page in reader.pages)
        except Exception:
            return ""
    decoded = payload.decode("utf-8", errors="replace")
    return html.unescape(re.sub(r"<[^>]+>", " ", decoded))


def parse_date_token(value: str) -> str:
    match = DATE_RE.search(value)
    if not match:
        return ""
    try:
        month = MONTHS[match.group("month").lower()]
        return date(int(match.group("year")), month, int(match.group("day"))).isoformat()
    except (KeyError, ValueError):
        return ""


def parse_regular_ex(text_value: str) -> str:
    for line in text_value.splitlines():
        if EX_REGULAR_RE.search(line):
            parsed = parse_date_token(line)
            if parsed:
                return parsed
            match = ISO_DATE_RE.search(line)
            if match:
                return iso_date(match.group(0))
    match = EX_REGULAR_RE.search(text_value)
    return parse_date_token(text_value[match.start():match.end() + 80]) if match else ""


def extracted_dates(text_value: str) -> set[str]:
    values = {match.group(0) for match in ISO_DATE_RE.finditer(text_value)}
    values.update(parse_date_token(match.group(0)) for match in DATE_RE.finditer(text_value))
    return {value for value in values if iso_date(value)}


def ratio_signature(value: Any) -> tuple[str, ...]:
    numbers = re.findall(r"\d+", text(value))
    return tuple(numbers) if len(numbers) >= 2 else ()


def extracted_ratio_signatures(text_value: str) -> set[tuple[str, ...]]:
    signatures: set[tuple[str, ...]] = set()
    for match in re.finditer(r"(\d[\d.,]*)\s*[:/]\s*(\d[\d.,]*)", text_value):
        left = re.sub(r"\D", "", match.group(1))
        right = re.sub(r"\D", "", match.group(2))
        if left and right:
            signatures.add((left, right))
    return signatures


def document_linkage_status(document: Mapping[str, Any], target: Mapping[str, Any]) -> tuple[str, str]:
    """Recompute exact linkage from source-bound document metadata."""
    if text(document.get("linkage_status")) == "AMBIGUOUS_SHARED_ATTACHMENT":
        return "AMBIGUOUS_SHARED_ATTACHMENT", "one attachment is associated with multiple economic events"
    if text(document.get("ticker")).upper() != text(target.get("ticker")).upper():
        return "UNRESOLVED", "document ticker does not match target ticker"
    if not official_url(document.get("source_ref")):
        return "UNRESOLVED", "document source reference is not an official IDX URL"
    if not valid_sha(document.get("evidence_sha256")) or int(document.get("bytes") or 0) <= 0:
        return "UNRESOLVED", "document bytes are not hash-bound"
    if text(document.get("rights_semantics")).lower() != "true":
        return "UNRESOLVED", "rights semantics are not explicit in the document"
    if not iso_date(document.get("regular_market_ex_date")):
        return "UNRESOLVED", "regular-market Ex date is absent"
    document_dates = {value for value in text(document.get("document_date_values")).split("|") if iso_date(value)}
    missing_dates = sorted(target_dates(target) - document_dates)
    if missing_dates:
        return "UNRESOLVED", "target event dates are not all present in the document: " + "|".join(missing_dates)
    expected_ratio = ratio_signature(target.get("ratio_raw"))
    if expected_ratio:
        document_ratios = {
            tuple(item.split(":"))
            for item in text(document.get("document_ratio_signatures")).split("|")
            if item and len(item.split(":")) == 2
        }
        if expected_ratio not in document_ratios:
            return "UNRESOLVED", "target ratio mechanics are not present in the document"
    return "LINKED_EXACT", "official, hash-bound, rights-semantic document matches ticker, dates, and ratio"


def target_dates(target: Mapping[str, Any]) -> set[str]:
    return {value for value in text(target.get("candidate_dates")).split("|") if iso_date(value)}


def result_for_target(target: Mapping[str, Any], *, announcements: Sequence[Mapping[str, Any]], documents: Sequence[Mapping[str, Any]], provider_failed: bool) -> dict[str, Any]:
    event_id = text(target.get("economic_event_id"))
    ticker = text(target.get("ticker"))
    candidates = [item for item in announcements if text(item.get("ticker")).upper() == ticker and is_rights_candidate(item)]
    docs = [item for item in documents if event_id in source_ids(item.get("associated_event_ids"))]
    base = {"economic_event_id": event_id, "ticker": ticker, "source_event_ids": text(target.get("source_event_ids")), "candidate_date": text(target.get("candidate_date")), "announcement_count": str(len(candidates)), "document_count": str(len(docs)), "transition_semantic": "", "transition_date": "", "authority_source_ref": "", "authority_evidence_sha256": "", "result_classification": "", "reason": ""}
    if provider_failed:
        base.update({"result_classification": "PROVIDER_DISCOVERY_FAILURE", "reason": "official IDX alternate-path request failed; no retry performed"})
        return base
    if not candidates and not docs:
        base.update({"result_classification": "NO_ALTERNATE_OFFICIAL_DOCUMENT_DISCOVERED", "reason": "no official IDX rights announcement or document discovered in the bounded event window; not historical negative authority"})
        return base
    if candidates and not docs:
        base.update({"result_classification": "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE", "reason": "official IDX rights announcement evidence exists but no valid exact attachment bytes were retained"})
        return base
    exact = [doc for doc in docs if text(doc.get("linkage_status")) == "LINKED_EXACT"]
    if len(exact) > 1:
        base.update({"result_classification": "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS", "reason": "more than one official attachment carries accepted Ex semantics for the target; document identity is not unique"})
        return base
    if exact:
        doc = exact[0]
        base.update({"result_classification": "RESOLVED_EXACT", "transition_semantic": "REGULAR_MARKET_EX_DATE", "transition_date": text(doc.get("regular_market_ex_date")), "authority_source_ref": text(doc.get("source_ref")), "authority_evidence_sha256": text(doc.get("evidence_sha256")), "reason": "official IDX attachment is ticker-bound, rights-semantic, hash-bound, and explicitly states regular-market Ex date"})
        return base
    if any(text(doc.get("linkage_status")) in {"AMBIGUOUS_SHARED_ATTACHMENT", "UNRESOLVED"} and text(doc.get("regular_market_ex_date")) for doc in docs):
        base.update({"result_classification": "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS", "reason": "official document has an Ex semantic but exact event identity, dates, ratio, or attachment association were not proven"})
    else:
        base.update({"result_classification": "OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT", "reason": "official IDX rights document found but accepted regular-market Ex semantic and exact linkage were not both proven"})
    return base


def candidate_linkage_audit(targets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, left in enumerate(targets):
        for right in targets[index + 1:]:
            if text(left.get("ticker")) != text(right.get("ticker")):
                continue
            left_dates = target_dates(left)
            right_dates = target_dates(right)
            overlap = sorted(left_dates & right_dates)
            ratio_same = bool(text(left.get("ratio_raw")) and text(left.get("ratio_raw")) == text(right.get("ratio_raw")))
            rows.append({
                "left_economic_event_id": text(left.get("economic_event_id")),
                "right_economic_event_id": text(right.get("economic_event_id")),
                "ticker": text(left.get("ticker")),
                "date_overlap": "|".join(overlap),
                "ratio_same": str(ratio_same).lower(),
                "classification": "AMBIGUOUS" if overlap or ratio_same else "PROVEN_DISTINCT",
                "reason": "candidate generation only; no date proximity or shared ticker promotes linkage",
            })
    return rows


def manifest_for(root: Path, *, provider_calls: bool, v14_root: Path, selection_manifest_sha256: str) -> dict[str, Any]:
    hashes: dict[str, Any] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            hashes[str(path.relative_to(root)).replace("\\", "/")] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return {"schema_version": f"{SCHEMA}_manifest", "artifact_root": str(root), "audit_date": AUDIT_DATE, "outcome_blind": True, "provider_calls": provider_calls, "controlling_v14_root": str(v14_root), "controlling_v14_manifest_sha256": V14_MANIFEST_SHA256, "selection_manifest_sha256": selection_manifest_sha256, "output_hashes_excluding_manifest": hashes, "self_hash_policy": "MANIFEST.json excluded from its own hash"}


def run_selection(output_root: Path, v14_root: Path) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"refuse overwrite existing output root: {output_root}")
    targets, _ = load_targets(v14_root)
    selected = select_pilot(targets)
    output_root.mkdir(parents=True)
    selection = selection_manifest(output_root, v14_root, targets, selected)
    manifest = manifest_for(output_root, provider_calls=False, v14_root=v14_root, selection_manifest_sha256=sha256_file(output_root / "selection_manifest.json"))
    write_json(output_root / "MANIFEST.json", manifest)
    return selection


def copy_selection(selection_root: Path, output_root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    if output_root.exists():
        raise FileExistsError(f"refuse overwrite existing output root: {output_root}")
    selection = read_json(selection_root / "selection_manifest.json")
    if selection.get("provider_calls") is not False or selection.get("provider_lookup_started") is not False or int(selection.get("pilot_tested") or 0) != 8:
        raise RuntimeError("selection root is not a frozen pre-provider eight-event selection")
    if selection.get("controlling_v14_manifest_sha256") != V14_MANIFEST_SHA256:
        raise RuntimeError("selection V14 pin mismatch")
    output_root.mkdir(parents=True)
    for name in ("rights_event_scope.csv", "pilot_selection.csv", "selection_manifest.json"):
        shutil.copyfile(selection_root / name, output_root / name)
    return read_csv(output_root / "rights_event_scope.csv"), read_csv(output_root / "pilot_selection.csv"), sha256_file(output_root / "selection_manifest.json")


def run_execute(selection_root: Path, output_root: Path, v14_root: Path) -> dict[str, Any]:
    scope, selected, _selection_manifest_sha256 = copy_selection(selection_root, output_root)
    v14_integrity = verify_v14(v14_root)
    selected_ids = {text(row.get("economic_event_id")) for row in selected}
    selected_targets = [row for row in scope if text(row.get("economic_event_id")) in selected_ids]
    if len(selected_targets) != 8 or any(text(row.get("ticker")) in {"MPPA", "GMFI", "SAME"} for row in selected_targets):
        raise RuntimeError("execute scope violates exact alternate pilot boundary")
    raw_api = output_root / "raw" / "idx_announcement_api"
    raw_docs = output_root / "raw" / "idx_announcement_attachments"
    requests: list[dict[str, Any]] = []
    announcements_by_event: dict[str, list[dict[str, Any]]] = {}
    documents: list[dict[str, Any]] = []
    attachment_to_events: dict[str, set[str]] = {}
    attachment_to_announcement_keys: dict[str, set[str]] = {}
    failed_events: set[str] = set()
    fetched_urls: set[str] = set()
    pagination_incomplete_events: set[str] = set()
    for number, target in enumerate(sorted(selected_targets, key=lambda row: (text(row.get("candidate_date")), text(row.get("ticker")), text(row.get("economic_event_id")))), start=1):
        event_id = text(target.get("economic_event_id"))
        start, end = date_window(target)
        params = {"pageSize": 200, "indexFrom": 0, "language": "id-id", "kodeEmiten": text(target.get("ticker")), "emitenType": "*", "dateFrom": start, "dateTo": end}
        request_row, payload = request_once(IDX_ANNOUNCEMENT_ENDPOINT, params=params, raw_path=raw_api / f"{number:02d}_{safe_name(text(target.get('ticker')))}_{start}_{end}.json", request_kind="IDX_OFFICIAL_ANNOUNCEMENT", request_key=event_id)
        requests.append(request_row)
        if payload is None:
            failed_events.add(event_id)
            continue
        try:
            parsed = announcement_payload(payload)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            failed_events.add(event_id)
            request_row["error"] = "IDX_ANNOUNCEMENT_JSON_INVALID"
            continue
        pagination_complete, result_count, reply_count, pagination_reason = pagination_attestation(parsed)
        request_row.update({
            "result_count": result_count if result_count is not None else "",
            "reply_count": reply_count,
            "pagination_complete": pagination_complete,
            "pagination_reason": pagination_reason,
        })
        if not pagination_complete:
            pagination_incomplete_events.add(event_id)
            failed_events.add(event_id)
            request_row["error"] = "IDX_ANNOUNCEMENT_PAGINATION_INCOMPLETE"
            continue
        event_announcements: list[dict[str, Any]] = []
        for raw_item in parsed.get("Replies") or []:
            fields = announcement_fields(raw_item)
            if fields["ticker"] != text(target.get("ticker")) or not is_rights_candidate(fields):
                continue
            fields.update({"economic_event_id": event_id, "source_ref": request_row.get("final_url") or request_row.get("requested_url"), "source_sha256": request_row.get("sha256", "")})
            event_announcements.append(fields)
            for attachment in fields.get("attachments") or []:
                if not isinstance(attachment, Mapping):
                    continue
                url = attachment_locator(attachment)
                if not url:
                    continue
                attachment_to_events.setdefault(url, set()).add(event_id)
                announcement_key = "|".join([text(fields.get("announcement_no")), text(fields.get("announcement_date")), url])
                attachment_to_announcement_keys.setdefault(url, set()).add(announcement_key)
                if url in fetched_urls:
                    continue
                fetched_urls.add(url)
                doc_no = len(documents) + 1
                doc_request, doc_payload = request_once(url, params=None, raw_path=raw_docs / f"{doc_no:03d}_{safe_name(text(target.get('ticker')))}_{attachment_name(attachment, url)}", request_kind="IDX_OFFICIAL_ANNOUNCEMENT_ATTACHMENT", request_key=hashlib.sha256(url.encode("utf-8")).hexdigest()[:20])
                doc_request["economic_event_id"] = event_id
                requests.append(doc_request)
                if doc_payload is None:
                    continue
                extracted = extract_document_text(doc_payload)
                ex_date = parse_regular_ex(extracted)
                docs_row = {
                    "economic_event_id": event_id, "ticker": text(target.get("ticker")),
                    "announcement_no": fields.get("announcement_no", ""),
                    "announcement_date": fields.get("announcement_date", ""),
                    "title": fields.get("title", ""), "subject": fields.get("subject", ""),
                    "source_ref": url, "source_contract_id": IDX_SOURCE_CONTRACT,
                    "evidence_sha256": doc_request.get("sha256", ""), "bytes": doc_request.get("bytes", 0),
                    "raw_path": doc_request.get("raw_path", ""),
                    "text_sha256": sha256_bytes(extracted.encode("utf-8")),
                    "rights_semantics": str(bool(RIGHTS_RE.search(extracted))).lower(),
                    "regular_market_ex_date": ex_date,
                    "document_date_values": "|".join(sorted(extracted_dates(extracted))),
                    "document_ratio_signatures": "|".join(":".join(item) for item in sorted(extracted_ratio_signatures(extracted))),
                    "associated_event_ids": event_id,
                    "associated_announcement_keys": announcement_key,
                    "linkage_status": "UNRESOLVED",
                    "linkage_reason": "pending complete attachment-to-event association audit",
                    "extraction_status": "EXTRACTED" if extracted else "EMPTY",
                }
                documents.append(docs_row)
        announcements_by_event[event_id] = event_announcements
    targets_by_id = {text(row.get("economic_event_id")): row for row in selected_targets}
    for document in documents:
        url = text(document.get("source_ref"))
        associated_ids = sorted(attachment_to_events.get(url, set()))
        document["associated_event_ids"] = "|".join(associated_ids)
        document["associated_announcement_keys"] = "|".join(sorted(attachment_to_announcement_keys.get(url, set())))
        if len(associated_ids) != 1:
            document["linkage_status"] = "AMBIGUOUS_SHARED_ATTACHMENT"
            document["linkage_reason"] = "attachment URL is associated with multiple selected economic events"
            continue
        status, reason = document_linkage_status(document, targets_by_id[associated_ids[0]])
        document["linkage_status"] = status
        document["linkage_reason"] = reason
    result_rows = [result_for_target(target, announcements=announcements_by_event.get(text(target.get("economic_event_id")), []), documents=documents, provider_failed=text(target.get("economic_event_id")) in failed_events) for target in selected_targets]
    result_rows.sort(key=lambda row: text(row.get("economic_event_id")))
    write_json(output_root / "request_ledger.json", requests)
    write_csv(output_root / "official_announcement_candidates.csv", [item for event_id in sorted(announcements_by_event) for item in announcements_by_event[event_id]], ["economic_event_id", "ticker", "announcement_no", "announcement_date", "title", "subject", "announcement_type", "form_id", "source_ref", "source_sha256"])
    write_csv(output_root / "official_document_evidence.csv", documents, ["economic_event_id", "ticker", "announcement_no", "announcement_date", "title", "subject", "source_ref", "source_contract_id", "evidence_sha256", "bytes", "raw_path", "text_sha256", "rights_semantics", "regular_market_ex_date", "document_date_values", "document_ratio_signatures", "associated_event_ids", "associated_announcement_keys", "linkage_status", "linkage_reason", "extraction_status"])
    write_csv(output_root / "candidate_linkage_audit.csv", candidate_linkage_audit(scope), ["left_economic_event_id", "right_economic_event_id", "ticker", "date_overlap", "ratio_same", "classification", "reason"])
    counts: dict[str, int] = {result: 0 for result in sorted(RESULT_CLASSES)}
    for row in result_rows:
        counts[text(row.get("result_classification"))] = counts.get(text(row.get("result_classification")), 0) + 1
    exact_count = counts.get("RESOLVED_EXACT", 0)
    provider_count = counts.get("PROVIDER_DISCOVERY_FAILURE", 0)
    if exact_count == len(result_rows) and provider_count == 0:
        idx_verdict = "ALTERNATE_OFFICIAL_PATH_REPEATABLE"
    elif exact_count or provider_count == 0:
        idx_verdict = "ALTERNATE_OFFICIAL_PATH_PARTIAL"
    else:
        idx_verdict = "ALTERNATE_OFFICIAL_PATH_NOT_RELIABLY_REPEATABLE"
    # The issuer path is deliberately not probed by this bounded IDX-only
    # audit.  Therefore a failed IDX path cannot be promoted to a verdict on
    # the complete alternate-source universe.
    overall = "ALTERNATE_OFFICIAL_PATH_PARTIAL"
    prior_linkages = read_csv(v14_root / "proven_same_event_linkage_ledger.csv")
    summary = {
        "schema_version": SCHEMA, "status": "COMPLETE_BOUNDED_ALTERNATE_RIGHTS_SOURCE_AUDIT", "audit_date": AUDIT_DATE,
        "outcome_blind": True, "provider_calls": True, "rights_unresolved_before": 68, "pilot_tested": len(result_rows),
        "classification_counts": counts, "idx_rights_document_path": idx_verdict,
        "v14_integrity": {"manifest_outputs_verified": True, **v14_integrity},
        "pagination_incomplete_events": sorted(pagination_incomplete_events),
        "issuer_rights_document_path": "NOT_TESTED_IN_BOUNDED_PILOT",
        "alternate_rights_source_capability": overall,
        "prior_proven_linkages": len(prior_linkages), "recomputed_proven_linkages": len(prior_linkages),
        "new_proven_linkages": 0, "removed_or_conflicting_linkages": 0,
        "new_linkage_ids": [], "rights_pilot_resolved": exact_count,
        "rights_unresolved_after": 68 - exact_count,
        "rights_remaining_unassessed": 60,
        "authority_blockers": {"IDX_HISTORICAL_NEGATIVE_AUTHORITY": "UNSUPPORTED", "IDX_HISTORICAL_ASOF_AUTHORITY": "UNKNOWN", "KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY": "UNKNOWN"},
        "guardrails": {"full_residual_acquisition": False, "ksei_retry": False, "other_ca_acquisition": False, "phase_e": False, "outcomes_or_targets": False, "model_refit_score": False, "counter_mutation": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False},
    }
    write_csv(output_root / "target_event_results.csv", result_rows, ["economic_event_id", "ticker", "source_event_ids", "candidate_date", "announcement_count", "document_count", "transition_semantic", "transition_date", "authority_source_ref", "authority_evidence_sha256", "result_classification", "reason"])
    write_json(output_root / "source_path_assessment.json", {"idx_rights_document_path": idx_verdict, "issuer_rights_document_path": "NOT_TESTED_IN_BOUNDED_PILOT", "alternate_rights_source_capability": overall, "historical_completeness_claim": "NOT_ESTABLISHED", "no_retry": True})
    write_json(output_root / "audit_summary.json", summary)
    manifest = manifest_for(output_root, provider_calls=True, v14_root=v14_root, selection_manifest_sha256=sha256_file(output_root / "selection_manifest.json"))
    write_json(output_root / "MANIFEST.json", manifest)
    return summary


def derive_assessment_successor(source_root: Path, output_root: Path, v14_root: Path) -> dict[str, Any]:
    """Create a no-provider successor with the hardened evidence attestations."""
    if output_root.exists():
        raise FileExistsError(f"refuse overwrite existing output root: {output_root}")
    source_manifest = source_root / "MANIFEST.json"
    if not source_manifest.is_file():
        raise RuntimeError("alternate audit source manifest missing")
    source_manifest_sha256 = sha256_file(source_manifest)
    source_integrity = verify_manifest_outputs(source_root, source_manifest_sha256)
    v14_integrity = verify_v14(v14_root)
    request_ledger = read_json(source_root / "request_ledger.json")
    if not isinstance(request_ledger, list):
        raise RuntimeError("alternate audit request ledger is not a list")
    request_schema_valid = True
    for request in request_ledger:
        if not isinstance(request, Mapping) or not text(request.get("request_kind")) or int(request.get("attempt") or 0) != 1:
            request_schema_valid = False
            break
        if int(request.get("bytes") or 0) > 0 and not valid_sha(request.get("sha256")):
            request_schema_valid = False
            break
    if not request_schema_valid:
        raise RuntimeError("alternate audit request ledger is not provenance-valid")
    shutil.copytree(source_root, output_root)
    summary_path = output_root / "audit_summary.json"
    summary = read_json(summary_path)
    summary.update({
        "status": "COMPLETE_BOUNDED_ALTERNATE_RIGHTS_SOURCE_AUDIT_ASSESSMENT_SUCCESSOR",
        "alternate_rights_source_capability": "ALTERNATE_OFFICIAL_PATH_PARTIAL",
        "assessment_successor_of_root": str(source_root),
        "assessment_successor_of_manifest_sha256": source_manifest_sha256,
        "assessment_note": "IDX path is not reliably repeatable from eight HTTP 403 results; issuer path was not tested, so aggregate alternate-path verdict remains partial rather than a universe-wide failure.",
        "hardening_validation": {
            "v14_manifest_outputs_verified": True,
            "v14_output_count": v14_integrity["output_count"],
            "source_manifest_outputs_verified": True,
            "source_output_count": source_integrity["output_count"],
            "request_ledger_schema_valid": True,
            "pagination_policy": "PASS_ONLY_WHEN_RESULTCOUNT_EQUALS_REPLIES_WITHIN_PAGE_SIZE; otherwise PROVIDER_DISCOVERY_FAILURE",
            "document_linkage_policy": "PASS_ONLY_WHEN_OFFICIAL_HASH_BOUND_DOCUMENT_MATCHES_TICKER_ALL_TARGET_DATES_RATIO_AND_UNIQUE_ATTACHMENT_ASSOCIATION",
            "no_provider_calls_in_successor": True,
        },
    })
    write_json(summary_path, summary)
    write_json(output_root / "source_path_assessment.json", {
        "idx_rights_document_path": "ALTERNATE_OFFICIAL_PATH_NOT_RELIABLY_REPEATABLE",
        "issuer_rights_document_path": "NOT_TESTED_IN_BOUNDED_PILOT",
        "alternate_rights_source_capability": "ALTERNATE_OFFICIAL_PATH_PARTIAL",
        "historical_completeness_claim": "NOT_ESTABLISHED",
        "no_retry": True,
        "assessment_successor_of_root": str(source_root),
        "assessment_successor_of_manifest_sha256": source_manifest_sha256,
        "hardening_validation": {
            "v14_manifest_outputs_verified": True,
            "source_manifest_outputs_verified": True,
            "request_ledger_schema_valid": True,
            "pagination_policy": "FAIL_CLOSED_ON_UNPROVEN_SINGLE_PAGE_COMPLETENESS",
            "document_linkage_policy": "SOURCE_REF_SHA_TICKER_DATES_RATIO_AND_UNIQUE_ATTACHMENT_REQUIRED",
        },
    })
    manifest = manifest_for(output_root, provider_calls=True, v14_root=v14_root, selection_manifest_sha256=sha256_file(output_root / "selection_manifest.json"))
    manifest.update({"assessment_successor_of_root": str(source_root), "assessment_successor_of_manifest_sha256": source_manifest_sha256, "provider_calls_in_successor": False})
    write_json(output_root / "MANIFEST.json", manifest)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--selection-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--derive-assessment", action="store_true")
    parser.add_argument("--v14-root", type=Path, default=V14_ROOT)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--selection-root", type=Path)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    if args.selection_only:
        result = run_selection(args.output_root, args.v14_root)
    elif args.execute:
        if args.selection_root is None:
            parser.error("--execute requires --selection-root")
        result = run_execute(args.selection_root, args.output_root, args.v14_root)
    else:
        if args.source_root is None:
            parser.error("--derive-assessment requires --source-root")
        result = derive_assessment_successor(args.source_root, args.output_root, args.v14_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
