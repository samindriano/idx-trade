"""Bounded live official-source discovery for the 19 V7 STOCK_SPLIT events.

Discovery and transition resolution are separate.  This runner never touches
BBRM, rights, other families, outcomes, models, counters, or canonical data.
It records every official KSEI/IDX request and only accepts an exact transition
when the retained document explicitly provides the regular-market first-new-
basis trading date.
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
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


AUDIT_DATE = "2026-08-29"
SCHEMA = "inc001_stock_split_discovery_v3"
PROJECT_ROOT = Path(r"D:\Documents\Project")
V7_ROOT_NAME = "idx-ca-economic-event-reconciliation-20260829-v7-split-wave"
V7_MANIFEST_SHA256 = "575982a3f1f179ff3b0267d40589f4886db6f593be49bcedb8aa1885f1b2725d"
KSEI_MASR = "https://web.ksei.co.id/publications/corporate-action-schedules/masr"
IDX_ISSUED_HISTORY = "https://www.idx.id/primary/ListingActivity/GetIssuedHistory"
MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
TD_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
HREF_RE = re.compile(r"href=[\"']([^\"']+\.pdf)[\"']", re.IGNORECASE)
STOCK_SPLIT_RE = re.compile(r"stock\s*split|pemecahan\s+saham", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{1,2})\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember|January|February|March|May|June|July|August|October|December)\s+(\d{4})\b", re.IGNORECASE)
RATIO_RE = re.compile(r"(?:Rasio pemecahan unit saham|(?:Stock\s+)?Split\s+Ratio)[^\r\n]*?(\d+(?:[.,]\d+)?\s*:\s*\d+(?:[.,]\d+)?)", re.IGNORECASE)
NOMINAL_RE = re.compile(
    r"(?:nilai nominal saham dari|Old Nominal Value of)\s+Rp\.?\s*([\d.,-]+).*?"
    r"(?:menjadi|to New Nominal Value of)\s+Rp\.?\s*([\d.,-]+)",
    re.IGNORECASE | re.DOTALL,
)
DATE_TOKEN_RE = r"(\d{1,2})\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember|January|February|March|May|June|July|August|October|December)\s+(\d{4})"


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


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_html(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def source_ids(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        parsed = None
    if isinstance(parsed, list):
        return [text(item) for item in parsed if text(item)]
    return [item for item in text(value).split("|") if item]


def load_targets(project_root: Path) -> list[dict[str, Any]]:
    v7 = project_root / V7_ROOT_NAME
    manifest = v7 / "MANIFEST.json"
    if sha256_file(manifest) != V7_MANIFEST_SHA256:
        raise RuntimeError("controlling V7 manifest hash mismatch")
    unresolved = [row for row in read_csv(v7 / "unresolved_economic_event_ledger.csv") if text(row.get("economic_family")) == "STOCK_SPLIT"]
    source_rows = {text(row.get("source_event_id")): row for row in read_csv(v7 / "source_evidence_ledger.csv")}
    geometry = {text(row.get("economic_family")): text(row.get("missing_semantic")) for row in read_csv(v7 / "remaining_gap_geometry.csv")}
    targets: list[dict[str, Any]] = []
    for event in unresolved:
        ids = source_ids(text(event.get("source_event_ids")))
        rows = [source_rows.get(item) for item in ids]
        if len(ids) != 1 and len(ids) != 2:
            raise RuntimeError(f"unexpected constituent source count for {event.get('economic_event_id')}: {len(ids)}")
        if any(row is None for row in rows):
            raise RuntimeError(f"missing V7 source evidence for {event.get('economic_event_id')}")
        concrete = [row for row in rows if row is not None]
        tickers = sorted({text(row.get("ticker")).upper() for row in concrete})
        if len(tickers) != 1:
            raise RuntimeError(f"target has non-single ticker identity: {event.get('economic_event_id')}")
        candidates = sorted({text(row.get("candidate_date")) for row in concrete if text(row.get("candidate_date"))})
        targets.append({
            "economic_event_id": text(event.get("economic_event_id")),
            "ticker": tickers[0],
            "source_event_ids": "|".join(ids),
            "source_kinds": "|".join(sorted({text(row.get("source_kind")) for row in concrete})),
            "source_native_labels": "|".join(sorted({text(row.get("source_native_label")) for row in concrete})),
            "candidate_dates": "|".join(candidates),
            "candidate_date": candidates[0] if candidates else "",
            "ratio_raw": "|".join(sorted({text(row.get("ratio_raw")) for row in concrete if text(row.get("ratio_raw"))})),
            "prior_source_refs": "|".join(sorted({text(row.get("source_ref")) for row in concrete})),
            "prior_evidence_sha256s": "|".join(sorted({text(row.get("evidence_sha256")) for row in concrete})),
            "prior_unresolved_reason": geometry.get("STOCK_SPLIT", "accepted REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"),
        })
    targets.sort(key=lambda row: (row["ticker"], row["candidate_date"], row["economic_event_id"]))
    if len(targets) != 19 or len({row["economic_event_id"] for row in targets}) != 19:
        raise RuntimeError(f"expected exactly 19 unique V7 STOCK_SPLIT economic events, got {len(targets)}")
    return targets


def ksei_query_keys(targets: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    keys: dict[tuple[str, str], dict[str, Any]] = {}
    for target in targets:
        candidate = text(target.get("candidate_date"))
        if len(candidate) != 10:
            raise RuntimeError(f"target lacks valid candidate date: {target.get('economic_event_id')}")
        year, month, _ = candidate.split("-")
        key = (year, month)
        keys.setdefault(key, {"year": year, "month": month, "tickers": set(), "event_ids": []})
        keys[key]["tickers"].add(text(target.get("ticker")))
        keys[key]["event_ids"].append(text(target.get("economic_event_id")))
    return [{**value, "tickers": sorted(value["tickers"]), "event_ids": sorted(value["event_ids"])} for _, value in sorted(keys.items())]


def official_url(value: str) -> str:
    absolute = html.unescape(text(value))
    return "https://web.ksei.co.id" + absolute if absolute.startswith("/") else absolute


def request_url(url: str, raw_path: Path, request_number: int, request_kind: str, scope: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "request_number": request_number,
        "request_kind": request_kind,
        "scope": scope,
        "requested_url": url,
        "final_url": "",
        "request_started_utc": now_utc(),
        "request_completed_utc": "",
        "status_code": "",
        "reason": "",
        "bytes": 0,
        "sha256": "",
        "raw_path": str(raw_path),
        "error": "",
        "retrieval_mode": "NEW_OFFICIAL_REQUEST",
    }
    request = urllib.request.Request(url, headers={"User-Agent": "IDX-Trade/INC001-stock-split-discovery-v3"})
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


def reuse_request(prior: Mapping[str, Any], reuse_root: Path, raw_path: Path, request_number: int, request_kind: str, scope: str) -> dict[str, Any]:
    old_path = Path(text(prior.get("raw_path")))
    if not old_path.is_file():
        old_path = reuse_root / "provider" / ("index" if request_kind == "KSEI_INDEX" else "idx_event") / Path(text(prior.get("raw_path"))).name
    if not old_path.is_file():
        if text(prior.get("status_code")) == "500" and text(prior.get("bytes")) == "0" and not text(prior.get("sha256")):
            raw_path.write_bytes(b"")
        else:
            raise RuntimeError(f"reuse root lacks raw response: {old_path}")
    else:
        shutil.copyfile(old_path, raw_path)
    row = dict(prior)
    row.update({"request_number": request_number, "request_kind": request_kind, "scope": scope, "raw_path": str(raw_path), "retrieval_mode": "REUSED_PRIOR_WAVE_BYTES"})
    if valid_sha(row.get("sha256")) and sha256_file(raw_path) != text(row.get("sha256")):
        raise RuntimeError(f"reused response hash mismatch: {raw_path}")
    if not valid_sha(row.get("sha256")) and not (text(row.get("status_code")) == "500" and text(row.get("bytes")) == "0" and raw_path.stat().st_size == 0):
        raise RuntimeError(f"reused response lacks a valid hash: {raw_path}")
    return row


def parse_ksei_index(path: Path, request: Mapping[str, Any]) -> list[dict[str, Any]]:
    body = path.read_text(encoding="utf-8", errors="replace")
    rows: list[dict[str, Any]] = []
    for fragment in TR_RE.findall(body):
        hrefs = [official_url(item) for item in HREF_RE.findall(fragment)]
        cells = [strip_html(item) for item in TD_RE.findall(fragment)]
        if not hrefs or len(cells) < 3:
            continue
        title = cells[1]
        if not STOCK_SPLIT_RE.search(title):
            continue
        rows.append({
            "request_number": request.get("request_number"),
            "index_raw_path": str(path),
            "index_sha256": text(request.get("sha256")),
            "source_ref": hrefs[0],
            "document_reference": cells[0],
            "title": title,
            "published_date_native": cells[2],
            "source_contract_id": "KSEI_MASR_OFFICIAL_INDEX_CONTRACT",
        })
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
            action = text(value.get("JenisTindakan"))
            date = text(value.get("TanggalPencatatan"))[:10]
            if code == ticker and date == candidate_date and action.lower() == "stocksplit":
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


def parse_document(document: Mapping[str, Any], text_path: Path) -> dict[str, Any]:
    body = text_path.read_text(encoding="utf-8", errors="replace") if text_path.is_file() else ""
    def labeled_date(label: str) -> str:
        match = re.search(rf"{label}.{{0,240}}?:\s*{DATE_TOKEN_RE}", body, re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        day, month, year = match.groups()
        return f"{int(year):04d}-{MONTHS[month.lower()]:02d}-{int(day):02d}"

    publication = re.search(rf"Jakarta,\s*{DATE_TOKEN_RE}", body, re.IGNORECASE)
    publication_date = ""
    if publication:
        day, month, year = publication.groups()
        publication_date = f"{int(year):04d}-{MONTHS[month.lower()]:02d}-{int(day):02d}"
    ratio_matches = list(RATIO_RE.finditer(body))
    ratio_match = ratio_matches[-1] if ratio_matches else None
    nominal = NOMINAL_RE.search(body)
    ratio = text(ratio_match.group(1)) if ratio_match else ""
    first_new = labeled_date(r"Start date of new securities trade in Regular and Negotiation Market")
    if not first_new:
        first_new = labeled_date(r"Mulai perdagangan saham dengan Nilai Nominal Baru.*?Pasar Reguler")
    explicit = bool(first_new)
    return {
        "document_id": text(document.get("document_id")),
        "ticker": text(document.get("ticker")),
        "document_reference": text(document.get("document_reference")),
        "source_ref": text(document.get("source_ref")),
        "evidence_sha256": text(document.get("sha256")).lower(),
        "actual_sha256": text(document.get("sha256")).lower(),
        "hash_matches_bytes": str(valid_sha(document.get("sha256"))).lower(),
        "status_code": text(document.get("status_code")),
        "publication_date": publication_date,
        "last_old_basis_trading_date": labeled_date(r"End of date old securities trade in Regular and Negotia(?:tion|ion) Market"),
        "first_new_basis_trading_date": first_new,
        "recording_date": labeled_date(r"Recording Date"),
        "distribution_date": labeled_date(r"Date of securities distribution"),
        "ratio": ratio,
        "old_nominal": nominal.group(1) if nominal else "",
        "new_nominal": nominal.group(2) if nominal else "",
        "explicit_regular_market_semantic": str(explicit).lower(),
        "parser_status": "PARSED_EXACT_STOCK_SPLIT_SCHEDULE" if first_new and ratio and nominal else "PARSED_BUT_INCOMPLETE_STOCK_SPLIT_SCHEDULE",
        "text_sha256": text_path.is_file() and sha256_file(text_path) or "",
        "body_contains_stock_split": bool(STOCK_SPLIT_RE.search(body)),
    }


def manifest_for(root: Path, artifact_root: Path, provider_calls: bool) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            outputs[str(path.relative_to(root)).replace("\\", "/")] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return {"manifest_version": f"{SCHEMA}_manifest", "artifact_root": str(artifact_root), "audit_date": AUDIT_DATE, "outcome_blind": True, "provider_calls": provider_calls, "output_hashes_excluding_manifest": outputs, "self_hash_policy": "MANIFEST.json excluded from its own hash"}


def final_artifact_path(path: Path, staging: Path, output_root: Path) -> str:
    """Return the immutable post-rename path for a staging artifact."""
    return str(output_root / path.relative_to(staging))


def build(project_root: Path, output_root: Path, reuse_root: Path | None = None) -> dict[str, Any]:
    staging = output_root.with_name(output_root.name + ".staging")
    if output_root.exists() or staging.exists():
        raise FileExistsError(f"immutable discovery root already exists: {output_root}")
    staging.mkdir(parents=True)
    try:
        targets = load_targets(project_root)
        target_by_ticker = {text(row["ticker"]): row for row in targets}
        query_keys = ksei_query_keys(targets)
        provider = staging / "provider"
        index_dir = provider / "index"
        idx_dir = provider / "idx_event"
        document_dir = provider / "documents"
        text_dir = provider / "text"
        for directory in (index_dir, idx_dir, document_dir, text_dir):
            directory.mkdir(parents=True)
        prior_indexes = read_json(reuse_root / "provider" / "search_request_ledger.json") if reuse_root is not None else []
        prior_idx = read_json(reuse_root / "provider" / "idx_event_request_ledger.json") if reuse_root is not None else []
        prior_docs = read_json(reuse_root / "provider" / "document_request_ledger.json") if reuse_root is not None else []
        search_ledger: list[dict[str, Any]] = []
        index_rows: list[dict[str, Any]] = []
        request_number = 1
        for query in query_keys:
            url = f"{KSEI_MASR}?Month={query['month']}&Year={query['year']}&setLocale=en-US"
            raw = index_dir / f"index_{request_number:03d}_{query['year']}{query['month']}.body"
            if reuse_root is not None:
                prior = next((row for row in prior_indexes if text(row.get("requested_url")) == url), None)
                if prior is None:
                    raise RuntimeError(f"reuse root lacks KSEI query: {url}")
                request = reuse_request(prior, reuse_root, raw, request_number, "KSEI_INDEX", "|".join(query["tickers"]))
            else:
                request = request_url(url, raw, request_number, "KSEI_INDEX", "|".join(query["tickers"]))
            request["raw_path"] = final_artifact_path(raw, staging, output_root)
            search_ledger.append(request)
            if text(request.get("status_code")) == "200" and valid_sha(request.get("sha256")):
                parsed_index_rows = parse_ksei_index(raw, request)
                for row in parsed_index_rows:
                    row["index_raw_path"] = final_artifact_path(raw, staging, output_root)
                index_rows.extend(parsed_index_rows)
            request_number += 1
        matches: dict[str, list[dict[str, Any]]] = {ticker: [] for ticker in target_by_ticker}
        for row in index_rows:
            for ticker in matches:
                if ticker_in_title(text(row.get("title")), ticker):
                    matches[ticker].append(row)
        idx_ledger: list[dict[str, Any]] = []
        idx_results: dict[str, list[dict[str, Any]]] = {text(row["economic_event_id"]): [] for row in targets}
        idx_request_number = 1
        for target in sorted(targets, key=lambda row: (text(row["ticker"]), text(row["candidate_date"]), text(row["economic_event_id"]))):
            ticker = text(target["ticker"])
            event_id = text(target["economic_event_id"])
            if matches[ticker]:
                continue
            candidate = text(target.get("candidate_date"))
            url = f"{IDX_ISSUED_HISTORY}?caType=stockSplit&dateFrom={candidate.replace('-', '')}&dateTo={candidate.replace('-', '')}&start=0&length=250"
            raw = idx_dir / f"idx_{idx_request_number:03d}_{ticker}_{candidate}.body"
            if reuse_root is not None:
                prior = next((row for row in prior_idx if text(row.get("requested_url")) == url), None)
                if prior is None:
                    raise RuntimeError(f"reuse root lacks IDX query: {url}")
                request = reuse_request(prior, reuse_root, raw, idx_request_number, "IDX_EVENT_SEARCH", ticker)
            else:
                request = request_url(url, raw, idx_request_number, "IDX_EVENT_SEARCH", ticker)
            request["raw_path"] = final_artifact_path(raw, staging, output_root)
            idx_ledger.append(request)
            if text(request.get("status_code")) == "200" and valid_sha(request.get("sha256")):
                idx_results[event_id] = extract_idx_records(raw.read_bytes(), ticker, candidate)
            idx_request_number += 1
        document_candidates: dict[str, list[dict[str, Any]]] = {ticker: list(rows) for ticker, rows in matches.items() if rows}
        unique_docs: dict[str, dict[str, Any]] = {}
        for ticker, rows in document_candidates.items():
            for row in rows:
                unique_docs.setdefault(text(row.get("source_ref")), {**row, "ticker": ticker})
        document_ledger: list[dict[str, Any]] = []
        parsed_documents: dict[str, dict[str, Any]] = {}
        for number, (url, candidate) in enumerate(sorted(unique_docs.items()), start=1):
            raw_name = f"download_{number:03d}_{re.sub(r'[^A-Za-z0-9_.-]+', '_', Path(url).name)}"
            raw = document_dir / raw_name
            if reuse_root is not None:
                prior = next((row for row in prior_docs if text(row.get("requested_url")) == url), None)
                if prior is None:
                    raise RuntimeError(f"reuse root lacks document: {url}")
                old_raw = Path(text(prior.get("raw_path")))
                if not old_raw.is_file():
                    old_raw = reuse_root / "provider" / "documents" / Path(text(prior.get("raw_path"))).name
                if not old_raw.is_file():
                    raise RuntimeError(f"reuse root lacks document bytes: {old_raw}")
                shutil.copyfile(old_raw, raw)
                row = dict(prior)
                row.update({"raw_path": str(raw), "retrieval_mode": "REUSED_PRIOR_WAVE_BYTES"})
                if sha256_file(raw) != text(row.get("sha256")):
                    raise RuntimeError(f"reused document hash mismatch: {raw}")
            else:
                row = request_url(url, raw, number, "OFFICIAL_DOCUMENT", text(candidate.get("ticker")))
            row["raw_path"] = final_artifact_path(raw, staging, output_root)
            txt = text_dir / (raw.stem + ".txt")
            if reuse_root is not None:
                old_txt = Path(text(next((item.get("text_path") for item in prior_docs if text(item.get("requested_url")) == url), "")))
                if not old_txt.is_file():
                    old_txt = reuse_root / "provider" / "text" / txt.name
                if old_txt.is_file():
                    shutil.copyfile(old_txt, txt)
                else:
                    raise RuntimeError(f"reuse root lacks extracted text: {old_txt}")
            else:
                status, text_sha = extract_pdf_text(raw, txt)
                row.update({"text_status": status, "text_sha256": text_sha})
            row.update({"document_id": f"DISC-V3-DOC-{number:03d}", "ticker": text(candidate.get("ticker")), "document_reference": text(candidate.get("document_reference")), "title": text(candidate.get("title")), "index_raw_path": text(candidate.get("index_raw_path")), "index_sha256": text(candidate.get("index_sha256")), "published_date_native": text(candidate.get("published_date_native")), "raw_path": final_artifact_path(raw, staging, output_root), "text_path": final_artifact_path(txt, staging, output_root)})
            if reuse_root is not None:
                row["text_sha256"] = sha256_file(txt)
            document_ledger.append(row)
            parsed = parse_document(row, txt)
            parsed["document_id"] = row["document_id"]
            parsed["ticker"] = row["ticker"]
            parsed["source_ref"] = row["requested_url"]
            parsed["document_reference"] = row["document_reference"]
            parsed["document_title"] = row["title"]
            parsed["status_code"] = text(row.get("status_code"))
            parsed["raw_path"] = final_artifact_path(raw, staging, output_root)
            parsed["text_path"] = final_artifact_path(txt, staging, output_root)
            parsed["bytes_ledger"] = text(row.get("bytes"))
            parsed["bytes_actual"] = str(raw.stat().st_size) if raw.is_file() else ""
            parsed["actual_sha256"] = sha256_file(raw)
            parsed["hash_matches_bytes"] = str(valid_sha(row.get("sha256")) and sha256_file(raw) == text(row.get("sha256"))).lower()
            parsed_documents[url] = parsed
        results: list[dict[str, Any]] = []
        for target in targets:
            ticker = text(target["ticker"])
            docs = [parsed_documents[row["source_ref"]] for row in matches[ticker] if row["source_ref"] in parsed_documents]
            distinct_docs = {text(row.get("source_ref")): row for row in docs}
            base_result = dict(target)
            base_result.update({"discovery_request_count": len([row for row in search_ledger + idx_ledger if ticker in text(row.get("scope")).split("|")]), "official_document_count": len(distinct_docs), "discovered_document_refs": "|".join(sorted(distinct_docs)), "discovered_document_sha256s": "|".join(sorted(text(row.get("evidence_sha256")) for row in distinct_docs.values()))})
            if len(distinct_docs) > 1:
                base_result.update({"result_classification": "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS", "reason": "multiple official KSEI stock-split documents match the target ticker in the bounded index scope", "transition_status": "UNRESOLVED"})
            elif len(distinct_docs) == 1:
                doc = next(iter(distinct_docs.values()))
                if text(doc.get("hash_matches_bytes")) != "true" or text(doc.get("status_code")) != "200":
                    base_result.update({"result_classification": "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE", "reason": "official index link was found but the retained document bytes are not valid", "transition_status": "UNRESOLVED"})
                elif text(doc.get("explicit_regular_market_semantic")) == "true" and text(doc.get("first_new_basis_trading_date")):
                    base_result.update({"result_classification": "RESOLVED_EXACT", "reason": "official KSEI document explicitly provides regular-market first-new-basis trading date", "transition_status": "RESOLVED", "transition_date": text(doc.get("first_new_basis_trading_date")), "transition_semantic": "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE", "authority_source_ref": text(doc.get("source_ref")), "authority_evidence_sha256": text(doc.get("evidence_sha256"))})
                else:
                    base_result.update({"result_classification": "OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT", "reason": "official stock-split document found but accepted regular-market first-new-basis semantic is absent", "transition_status": "UNRESOLVED"})
            elif idx_results.get(text(target["economic_event_id"])):
                base_result.update({"result_classification": "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE", "reason": "official IDX event evidence found but no exact transition document was exposed by the bounded path", "transition_status": "UNRESOLVED"})
            else:
                relevant = [row for row in search_ledger + idx_ledger if ticker in text(row.get("scope")).split("|")]
                if any(text(row.get("error")) or text(row.get("status_code")) not in {"200", "404"} for row in relevant):
                    base_result.update({"result_classification": "PROVIDER_DISCOVERY_FAILURE", "reason": "bounded official discovery request failed", "transition_status": "UNRESOLVED"})
                else:
                    base_result.update({"result_classification": "NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED", "reason": "no official event document was discovered in the bounded KSEI/IDX paths; not historical no-event authority", "transition_status": "UNRESOLVED"})
            results.append(base_result)
        allowed = {"RESOLVED_EXACT", "OFFICIAL_DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT", "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS", "OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE", "NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED", "PROVIDER_DISCOVERY_FAILURE"}
        if len(results) != 19 or any(text(row.get("result_classification")) not in allowed for row in results):
            raise RuntimeError("result conservation/classification validation failed")
        resolved = [row for row in results if row["result_classification"] == "RESOLVED_EXACT"]
        classifications = {key: sum(row["result_classification"] == key for row in results) for key in sorted({row["result_classification"] for row in results})}
        if len(resolved) == 19:
            capability = "HISTORICAL_SOURCE_PATH_PROVEN"
        elif any(row["result_classification"] == "OFFICIAL_DOCUMENT_FOUND_LINKAGE_AMBIGUOUS" for row in results):
            capability = "EVENT_SPECIFIC_MULTI_SOURCE_PATH_REQUIRED"
        elif any(row["result_classification"] == "PROVIDER_DISCOVERY_FAILURE" for row in results):
            capability = "CAPABILITY_NOT_RELIABLY_REPEATABLE"
        else:
            capability = "PARTIAL_HISTORICAL_CAPABILITY"
        findings = [
            "KSEI MASR monthly index discovery and exact document linkage were attempted only for the 19 target events.",
            "A positive event/document finding is not population-level historical completeness.",
            "IDX fallback results establish at most positive event evidence; candidate/record/listing dates are never transition authority.",
        ]
        summary = {
            "schema_version": SCHEMA, "audit_date": AUDIT_DATE, "status": "COMPLETE_BOUNDED_OFFICIAL_STOCK_SPLIT_DISCOVERY_OUTCOME_BLIND",
            "controlling_v7_manifest_sha256": V7_MANIFEST_SHA256,
            "target_stock_split_events": len(targets), "ksei_index_request_count": len(search_ledger), "idx_event_request_count": len(idx_ledger), "official_document_count": len(document_ledger),
            "classification_counts": classifications, "resolved_exact": len(resolved), "stock_split_source_capability_after_19": capability, "source_path_findings": findings,
            "provider_calls": reuse_root is None,
            "guardrails": {"target_stock_split_only": True, "bbrm": False, "rights_hmetd": False, "other_families": False, "phase_e": False, "outcomes_or_targets": False, "fit_refit_score": False, "counter_mutation": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False},
            "authority_blockers_unchanged": {"IDX_HISTORICAL_NEGATIVE_AUTHORITY": "UNSUPPORTED", "IDX_HISTORICAL_ASOF_AUTHORITY": "UNKNOWN", "KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY": "UNKNOWN"},
        }
        write_csv(staging / "target_event_ledger.csv", targets, list(targets[0].keys()))
        write_json(provider / "search_request_ledger.json", search_ledger)
        write_json(provider / "idx_event_request_ledger.json", idx_ledger)
        write_json(provider / "document_request_ledger.json", document_ledger)
        write_csv(staging / "ksei_index_candidate_rows.csv", index_rows, ["request_number", "index_raw_path", "index_sha256", "source_ref", "document_reference", "title", "published_date_native", "source_contract_id"])
        write_csv(staging / "official_document_evidence.csv", [parsed_documents[key] for key in sorted(parsed_documents)], sorted({field for row in parsed_documents.values() for field in row}))
        write_csv(staging / "target_event_results.csv", results, list(results[0].keys()))
        write_json(staging / "source_path_capability_assessment.json", {"verdict": capability, "findings": findings, "classification_counts": classifications, "historical_completeness_claim": "NOT_ESTABLISHED"})
        write_json(staging / "discovery_summary.json", summary)
        write_json(staging / "MANIFEST.json", manifest_for(staging, output_root, reuse_root is None))
        staging.rename(output_root)
        return summary
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--reuse-root", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.project_root, args.output_root, args.reuse_root), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
