"""Build an outcome-blind, provenance-bound IDX identity/lifecycle crosswalk.

This module only reads retained local artifacts.  It deliberately distinguishes
observed source membership from historical population completeness, current
security identity from PIT eligibility, and event evidence from effective
membership.  It never calls a provider and never writes canonical data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


CODE_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}$")
ISIN_RE = re.compile(r"^ID[A-Z0-9]{9,11}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_code(value: Any) -> str | None:
    code = str(value or "").strip().upper()
    return code if CODE_RE.fullmatch(code) else None


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def first_column(frame: pd.DataFrame, names: Iterable[str]) -> str | None:
    lowered = {str(column).strip().lower(): str(column) for column in frame.columns}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def frame_codes(frame: pd.DataFrame, names: Iterable[str] = ("ticker", "ticker_code", "code", "KodeEmiten", "symbol")) -> set[str]:
    column = first_column(frame, names)
    if column is None:
        return set()
    return {code for value in frame[column].dropna().tolist() if (code := normalize_code(value))}


class DefinitionListParser(HTMLParser):
    """Parse KSEI's visible definition list without trusting presentation HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_dt = False
        self.in_dd = False
        self.buffer: list[str] = []
        self.pending_label: str | None = None
        self.fields: dict[str, str] = {}
        self.title = ""
        self.in_h1 = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "dt":
            self.in_dt = True
            self.buffer = []
        elif tag == "dd":
            self.in_dd = True
            self.buffer = []
        elif tag == "h1":
            self.in_h1 = True
            self.buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "dt" and self.in_dt:
            self.pending_label = clean_text("".join(self.buffer))
            self.in_dt = False
        elif tag == "dd" and self.in_dd:
            if self.pending_label:
                self.fields[self.pending_label] = clean_text("".join(self.buffer))
            self.pending_label = None
            self.in_dd = False
        elif tag == "h1" and self.in_h1:
            self.title = clean_text("".join(self.buffer))
            self.in_h1 = False

    def handle_data(self, data: str) -> None:
        if self.in_dt or self.in_dd or self.in_h1:
            self.buffer.append(data)


def parse_ksei_detail_html(payload: str, requested_code: str) -> dict[str, Any]:
    parser = DefinitionListParser()
    parser.feed(payload)
    fields = {clean_text(key): clean_text(value) for key, value in parser.fields.items()}
    normalized = {
        "requested_code": normalize_code(requested_code),
        "security_name": fields.get("Security name", ""),
        "issuer": fields.get("Issuer", ""),
        "isin": fields.get("ISIN Code", ""),
        "short_code": normalize_code(fields.get("Short Code", "")),
        "type": fields.get("Type", ""),
        "listing_date": fields.get("Listing Date", ""),
        "stock_exchange": fields.get("Stock Exchange", ""),
        "status": fields.get("Status", ""),
        "nominal": fields.get("Nominal", ""),
        "current_amount": fields.get("Current Amount", ""),
        "effective_date_isin": fields.get("Effective Date ISIN", ""),
        "raw_fields": fields,
        "title": parser.title,
    }
    normalized["field_presence"] = sorted(key for key, value in normalized.items() if value not in ("", None, []))
    return normalized


def classify_ksei_detail(payload: str, requested_code: str, http_status: int | None) -> dict[str, Any]:
    parsed = parse_ksei_detail_html(payload, requested_code) if http_status == 200 else {}
    if http_status != 200:
        status = "HTTP_NON_200"
    else:
        code_matches = parsed.get("short_code") == normalize_code(requested_code)
        isin_valid = bool(ISIN_RE.fullmatch(parsed.get("isin", "")))
        required = all(parsed.get(name) for name in ("security_name", "issuer", "type"))
        status = "DETAIL_VALID" if code_matches and isin_valid and required else "HTTP_200_EMPTY_OR_MISMATCH"
    return {"parse_status": status, **parsed}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def source_provenance(source_id: str, paths: list[Path], note: str = "") -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in paths:
        record: dict[str, Any] = {"path": str(path), "exists": path.exists()}
        if path.is_file():
            record.update({"bytes": path.stat().st_size, "sha256": sha256_file(path)})
        records.append(record)
    return {"source_id": source_id, "artifacts": records, "note": note}


def nested_codes(value: Any, keys: set[str] | None = None) -> set[str]:
    keys = keys or {"code", "Code", "ticker", "Ticker", "KodeEmiten", "kodeEmiten", "emitenCode"}
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                if code := normalize_code(item):
                    found.add(code)
                elif isinstance(item, list):
                    found |= {code for entry in item if (code := normalize_code(entry))}
            found |= nested_codes(item, keys)
    elif isinstance(value, list):
        for item in value:
            found |= nested_codes(item, keys)
    return found


def read_parquet_codes(path: Path, names: Iterable[str] = ("ticker", "code", "symbol")) -> tuple[set[str], dict[str, Any]]:
    frame = pd.read_parquet(path)
    column = first_column(frame, names)
    codes = frame_codes(frame, names)
    meta: dict[str, Any] = {"rows": int(len(frame)), "columns": [str(c) for c in frame.columns], "code_column": column}
    if column:
        meta["date_min"] = str(frame[first_column(frame, ("date", "session", "trading_date"))].min()) if first_column(frame, ("date", "session", "trading_date")) else None
        meta["date_max"] = str(frame[first_column(frame, ("date", "session", "trading_date"))].max()) if first_column(frame, ("date", "session", "trading_date")) else None
    return codes, meta


def parse_official_trading_summary(path: Path) -> tuple[set[str], dict[str, dict[str, Any]]]:
    payload = load_json(path)
    records = payload.get("records", payload if isinstance(payload, list) else [])
    by_code: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        code = normalize_code(record.get("code") or record.get("ticker") or record.get("KodeEmiten"))
        if code:
            by_code[code] = record
    return set(by_code), by_code


def parse_profiles(root: Path) -> tuple[set[str], dict[str, dict[str, Any]], dict[str, Any]]:
    by_code: dict[str, dict[str, Any]] = {}
    populated = 0
    empty = 0
    candidate_paths = sorted(path for path in root.iterdir() if path.is_file() and path.suffix.lower() in {".json", ".raw"}) if root.is_dir() else []
    for path in candidate_paths:
        code = normalize_code(path.stem)
        if not code:
            continue
        try:
            payload = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            by_code[code] = {"parse_status": "JSON_ERROR", "path": str(path)}
            continue
        profiles = payload.get("Profiles", []) if isinstance(payload, dict) else []
        profile = profiles[0] if isinstance(profiles, list) and profiles and isinstance(profiles[0], dict) else {}
        by_code[code] = {
            "path": str(path),
            "profile": profile,
            "parse_status": "POPULATED" if profile else "EMPTY",
        }
        if profile:
            populated += 1
        else:
            empty += 1
    return set(by_code), by_code, {"files": len(by_code), "populated": populated, "empty": empty}


def parse_issued_history(root: Path) -> tuple[set[str], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted(root.glob("*.json")) if root.is_dir() else []:
        code = normalize_code(path.stem)
        if not code:
            continue
        try:
            payload = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict):
                event = dict(row)
                event["source_path"] = str(path)
                events[code].append(event)
    types = Counter(clean_text(event.get("JenisTindakan")) for rows in events.values() for event in rows)
    return set(events), dict(events), {"codes": len(events), "events": sum(len(rows) for rows in events.values()), "event_types": dict(types)}


def parse_report_index(roots: Iterable[Path]) -> tuple[set[str], dict[str, dict[str, Any]], dict[str, int]]:
    by_code: dict[str, dict[str, Any]] = defaultdict(lambda: {"rows": 0, "years": set(), "files": set()})
    annual = 0
    quarterly = 0
    for root in roots:
        candidate_paths = sorted(path for path in root.iterdir() if path.is_file() and path.suffix.lower() in {".json", ".raw"}) if root.is_dir() else []
        for path in candidate_paths:
            is_quarterly = bool(re.search(r"TW[123]", path.name, re.IGNORECASE))
            try:
                payload = load_json(path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            rows = payload.get("Results", []) if isinstance(payload, dict) else []
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict):
                    continue
                code = normalize_code(row.get("KodeEmiten") or row.get("code") or row.get("ticker"))
                if not code:
                    continue
                item = by_code[code]
                item["rows"] += 1
                item["files"].add(path.name)
                if row.get("Report_Year"):
                    item["years"].add(str(row["Report_Year"]))
                if is_quarterly:
                    quarterly += 1
                else:
                    annual += 1
    normalized = {code: {"rows": item["rows"], "years": sorted(item["years"]), "files": sorted(item["files"])} for code, item in by_code.items()}
    return set(normalized), normalized, {"annual_rows": annual, "quarterly_rows": quarterly}


def parse_ksei_sources(table_path: Path, detail_root: Path) -> tuple[set[str], dict[str, dict[str, Any]], dict[str, Any]]:
    table = load_json(table_path) if table_path.is_file() else {}
    basic: dict[str, dict[str, Any]] = {}
    for row in table.get("codes", []) if isinstance(table, dict) else []:
        code = normalize_code(row.get("code")) if isinstance(row, dict) else None
        if code:
            basic[code] = dict(row)
    metadata: dict[str, dict[str, Any]] = {}
    metadata_path = detail_root / "acquisition_metadata.jsonl"
    if metadata_path.is_file():
        for line in metadata_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if code := normalize_code(row.get("code")):
                metadata[code] = row
    details: dict[str, dict[str, Any]] = {}
    raw_dir = detail_root / "raw"
    for code, meta in metadata.items():
        payload = ""
        raw_path = Path(meta.get("raw_path", ""))
        if not raw_path.is_file() and raw_dir.is_dir():
            raw_path = raw_dir / f"{code}.html"
        if raw_path.is_file() and meta.get("http_status") == 200:
            payload = raw_path.read_text(encoding="utf-8", errors="replace")
        parsed = classify_ksei_detail(payload, code, meta.get("http_status"))
        details[code] = {
            "basic": basic.get(code),
            "acquisition": meta,
            **parsed,
        }
    for code, row in basic.items():
        details.setdefault(code, {"basic": row, "parse_status": "NOT_ATTEMPTED"})
    counts = Counter(row.get("parse_status", "UNKNOWN") for row in details.values())
    return set(basic), details, {"share_table_codes": len(basic), "detail_codes": len(details), "detail_status_counts": dict(counts), "metadata_sha256": sha256_file(metadata_path) if metadata_path.is_file() else None, "table_sha256": sha256_file(table_path) if table_path.is_file() else None}


def parse_public_ipo_surface(ipo_root: Path) -> tuple[set[str], set[str]]:
    """Read issuer ticker fields only; never treat underwriter/warrant codes as tickers."""
    ipo_codes: set[str] = set()
    nonstandard: set[str] = set()
    ipo_csv = ipo_root / "stocks.csv"
    if ipo_csv.is_file():
        try:
            ipo_codes |= frame_codes(pd.read_csv(ipo_csv, sep=";"), ("ticker_code",))
        except (OSError, ValueError, pd.errors.ParserError):
            pass
    stock_json_root = ipo_root / "stock"
    for path in sorted(stock_json_root.glob("*.json")) if stock_json_root.is_dir() else []:
        raw_code = path.stem
        if code := normalize_code(raw_code):
            ipo_codes.add(code)
        else:
            nonstandard.add(raw_code)
        try:
            payload = load_json(path)
            if isinstance(payload, dict):
                raw_code = str(payload.get("ticker_code", "")).strip().upper()
                if code := normalize_code(raw_code):
                    ipo_codes.add(code)
                elif raw_code:
                    nonstandard.add(raw_code)
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return ipo_codes, nonstandard


def parse_corporate_action_probe(path: Path | None) -> tuple[set[str], dict[str, list[dict[str, Any]]]]:
    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not path or not path.is_file():
        return set(), {}
    payload = load_json(path)
    source = payload.get("source", {}) if isinstance(payload, dict) else {}
    for code in source.get("codes", []) if isinstance(source, dict) else []:
        if normalized := normalize_code(code):
            by_code[normalized].append({"source": "corporate_action_probe", "path": str(path), "raw_sha256": source.get("raw_sha256"), "sample_records": source.get("sample_records")})
    for document in payload.get("document_evidence", []) if isinstance(payload, dict) else []:
        if not isinstance(document, dict):
            continue
        if code := normalize_code(document.get("code")):
            by_code[code].append({key: document.get(key) for key in ("code", "publish_date", "document_sha256", "semantics", "effective_transition_stated")})
    return set(by_code), dict(by_code)


def parse_announcement_hits(root: Path, codes: set[str]) -> dict[str, list[dict[str, Any]]]:
    """Find exact issuer-code hits in retained announcement result pages only.

    A code absent from this bounded search is not treated as an absent event.
    Titles are retained because a code hit may describe a subsidiary or another
    non-listing matter rather than a ticker/lifecycle transition.
    """
    hits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    announcement_root = root / "idx-announcements"
    for path in sorted(announcement_root.glob("*.raw")) if announcement_root.is_dir() else []:
        try:
            payload = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        items = payload.get("Items", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            code = normalize_code(item.get("Code"))
            if code not in codes:
                continue
            hits[code].append({
                "source_path": str(path),
                "source_sha256": sha256_file(path),
                "publish_date": item.get("PublishDate"),
                "title": item.get("Title"),
                "announcement_no": item.get("AnnouncementNo"),
            })
    return dict(hits)


def parse_lifecycle_rows(current_path: Path, delisting_path: Path, security_master_path: Path, conflict_path: Path | None = None) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    intervals: dict[str, list[dict[str, Any]]] = defaultdict(list)
    current_rows = read_csv_rows(current_path)
    delisting_rows = read_csv_rows(delisting_path)
    for index, row in enumerate(current_rows):
        code = normalize_code(row.get("ticker"))
        if code:
            intervals[code].append({"kind": "CURRENT_LISTING_RECORD", "row_id": f"current:{index}", "listed_from": row.get("listed_from", ""), "listed_to": row.get("listed_to", ""), "company_name": row.get("company_name", ""), "source": row.get("source", ""), "source_ref": row.get("source_ref", ""), "source_path": str(current_path)})
    for index, row in enumerate(delisting_rows):
        code = normalize_code(row.get("ticker"))
        if code:
            intervals[code].append({"kind": "DELISTING_RECORD", "row_id": f"delisting:{index}", "listed_from": row.get("listed_from", ""), "listed_to": row.get("listed_to", ""), "company_name": row.get("company_name", ""), "source": row.get("source", ""), "source_ref": row.get("source_ref", ""), "source_path": str(delisting_path)})
    master_rows = read_csv_rows(security_master_path)
    for index, row in enumerate(master_rows):
        code = normalize_code(row.get("ticker"))
        if code:
            intervals[code].append({"kind": "SECURITY_MASTER_INTERVAL", "row_id": f"security_master:{index}", "listed_from": row.get("listed_from", ""), "listed_to": row.get("listed_to", ""), "company_name": row.get("company_name", ""), "source": row.get("source", ""), "source_ref": "", "source_path": str(security_master_path), "security_id": row.get("security_id", "")})
    conflicts: set[str] = set()
    if conflict_path and conflict_path.is_file():
        for row in read_csv_rows(conflict_path):
            if code := normalize_code(row.get("ticker")):
                conflicts.add(code)
    else:
        for code, rows in intervals.items():
            # Names may differ in punctuation/translation across official IDX
            # surfaces.  A date disagreement is the conservative conflict test.
            signatures = {(row.get("listed_from", ""), row.get("listed_to", "")) for row in rows}
            if len(signatures) > 1:
                conflicts.add(code)
    return dict(intervals), {"current_rows": len(current_rows), "delisting_rows": len(delisting_rows), "security_master_rows": len(master_rows), "codes_with_intervals": len(intervals), "conflict_codes": sorted(conflicts), "conflict_source_path": str(conflict_path) if conflict_path else "derived_date_signature"}


def normalize_source_sets(source_sets: dict[str, set[str]]) -> dict[str, set[str]]:
    return {source: {code for code in codes if normalize_code(code)} for source, codes in source_sets.items()}


def build_identity_graph(codes: list[str], ksei: dict[str, dict[str, Any]], profiles: dict[str, dict[str, Any]], issued: dict[str, list[dict[str, Any]]], security_master_rows: dict[str, list[dict[str, Any]]], intervals: dict[str, list[dict[str, Any]]], conflict_codes_override: set[str] | None = None) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    conflict_codes = conflict_codes_override or {
        code
        for code, rows in intervals.items()
        if len({(row.get("listed_from", ""), row.get("listed_to", ""), row.get("company_name", "")) for row in rows}) > 1
    }

    def add_node(node_id: str, kind: str, status: str, **extra: Any) -> None:
        nodes.setdefault(node_id, {"node_id": node_id, "kind": kind, "status": status, **extra})

    def add_edge(source: str, relation: str, target: str, status: str, provenance: list[dict[str, Any]], **extra: Any) -> None:
        edges.append({"source": source, "relation": relation, "target": target, "status": status, "provenance": provenance, **extra})

    for code in codes:
        ticker_id = f"TICKER:{code}"
        add_node(ticker_id, "TICKER_CODE", "UNKNOWN", code=code)
        detail = ksei.get(code, {})
        if detail.get("parse_status") == "DETAIL_VALID":
            isin = detail.get("isin", "")
            issuer = detail.get("issuer", "")
            ksei_id = f"KSEI_SECURITY:{code}:{isin}"
            isin_id = f"ISIN:{isin}"
            issuer_id = f"ISSUER_NAME:{hashlib.sha256(clean_text(issuer).upper().encode()).hexdigest()[:16]}"
            provenance = [{"source": "KSEI_REGISTERED_SECURITY_DETAIL", "path": detail.get("acquisition", {}).get("raw_path"), "sha256": detail.get("acquisition", {}).get("sha256"), "retrieved_at_utc": detail.get("acquisition", {}).get("retrieved_at_utc")}]
            add_node(ksei_id, "SECURITY", "SUPPORTED_BOUNDED", code=code, isin=isin, security_name=detail.get("security_name", ""), security_type=detail.get("type", ""))
            add_node(isin_id, "ISIN", "SUPPORTED_BOUNDED", isin=isin)
            add_node(issuer_id, "ISSUER_NAME", "SUPPORTED_BOUNDED", issuer_name=issuer)
            add_edge(ticker_id, "IDENTIFIED_BY_ISIN", isin_id, "SUPPORTED_BOUNDED", provenance, authority_note="Current public KSEI detail; not historical PIT identity")
            add_edge(ksei_id, "ISSUED_BY", issuer_id, "SUPPORTED_BOUNDED", provenance, authority_note="Issuer string, not legal-entity continuity proof")
            add_edge(ticker_id, "REPRESENTED_BY", ksei_id, "SUPPORTED_BOUNDED", provenance, authority_note="Current registered-security surface")
        for index, row in enumerate(security_master_rows.get(code, [])):
            security_id = clean_text(row.get("security_id")) or f"SECURITY_MASTER:{code}:{index}"
            security_node = f"SECURITY:{security_id}"
            add_node(security_node, "SECURITY", "SUPPORTED_BOUNDED", security_id=security_id, code=code)
            provenance = [{"source": "SECURITY_MASTER", "path": row.get("_source_path"), "sha256": row.get("_source_sha256")}]
            add_edge(ticker_id, "TRADED_AS", security_node, "SUPPORTED_BOUNDED", provenance, authority_note="Retained reconciled security-master mapping; not population/PIT proof")
        profile = profiles.get(code, {}).get("profile", {})
        issuer_name = clean_text(profile.get("NamaEmiten") or profile.get("NamaEmitenEng") or "") if isinstance(profile, dict) else ""
        if issuer_name:
            issuer_id = f"ISSUER_NAME:{hashlib.sha256(issuer_name.upper().encode()).hexdigest()[:16]}"
            add_node(issuer_id, "ISSUER_NAME", "SUPPORTED_BOUNDED", issuer_name=issuer_name)
            provenance = [{"source": "IDX_PROFILE_DETAIL", "path": profiles[code].get("path"), "sha256": sha256_file(Path(profiles[code]["path"])) if profiles[code].get("path") and Path(profiles[code]["path"]).is_file() else None}]
            add_edge(ticker_id, "PROFILE_NAMED_ISSUER", issuer_id, "SUPPORTED_BOUNDED", provenance, authority_note="Current profile name; not issuer continuity proof")
        for index, event in enumerate(issued.get(code, [])):
            event_id = f"LIFECYCLE_EVENT:{code}:{index}"
            add_node(event_id, "LIFECYCLE_EVENT", "SUPPORTED_BOUNDED", event_type=clean_text(event.get("JenisTindakan")), date=clean_text(event.get("TanggalPencatatan")))
            add_edge(ticker_id, "HAS_LIFECYCLE_EVENT", event_id, "SUPPORTED_BOUNDED", [{"source": "IDX_ISSUED_HISTORY", "path": event.get("source_path")}], authority_note="Event record; exchange-effective membership semantics unknown")
        for index, interval in enumerate(intervals.get(code, [])):
            event_id = f"LIFECYCLE_INTERVAL:{code}:{index}"
            interval_status = "CONFLICTING" if code in conflict_codes else "SUPPORTED_BOUNDED"
            add_node(event_id, "LIFECYCLE_EVENT", interval_status, interval_kind=interval.get("kind", ""), listed_from=interval.get("listed_from", ""), listed_to=interval.get("listed_to", ""), company_name=interval.get("company_name", ""))
            add_edge(ticker_id, "HAS_LISTING_INTERVAL", event_id, interval_status, [{"source": interval.get("kind"), "path": interval.get("source_path"), "row_id": interval.get("row_id")}], authority_note="Observed interval record; do not infer daily PIT")
    return {"schema_version": "1.0", "status_legend": ["PROVEN", "SUPPORTED_BOUNDED", "CONFLICTING", "UNKNOWN", "INFERRED_NOT_ADMITTED"], "nodes": sorted(nodes.values(), key=lambda item: item["node_id"]), "edges": edges, "global_constraints": {"historical_population_completeness": "UNKNOWN", "pit_effective_date_authority": "UNKNOWN", "issuer_legal_continuity": "UNKNOWN", "ticker_security_issuer_series_are_distinct": True}}


def build_crosswalk(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    panel_codes, panel_meta = read_parquet_codes(args.panel)
    anchor_frame = pd.read_csv(args.anchor)
    anchor_codes = frame_codes(anchor_frame)
    security_master_rows_raw = read_csv_rows(args.security_master)
    security_master_codes = {code for row in security_master_rows_raw if (code := normalize_code(row.get("ticker")))}
    security_master_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in security_master_rows_raw:
        if code := normalize_code(row.get("ticker")):
            row = dict(row)
            row["_source_path"] = str(args.security_master)
            row["_source_sha256"] = sha256_file(args.security_master)
            security_master_rows[code].append(row)
    trading_codes, trading_meta = parse_official_trading_summary(args.official_summary)
    profile_codes, profiles, profile_meta = parse_profiles(args.profile_root)
    issued_codes, issued, issued_meta = parse_issued_history(args.issued_root)
    quarterly_root = args.quarterly_index_root or (args.annual_index_root.parent / "quarterly-index")
    annual_codes, report_meta, report_counts = parse_report_index([args.annual_index_root, quarterly_root])
    financial_codes, financial_meta = read_parquet_codes(args.financial_bundle)
    foreign_codes: set[str] = set()
    foreign_sessions = 0
    foreign_rows = 0
    for path in sorted(args.foreign_flow_root.glob("sessions/*/foreign_flow.parquet")) if args.foreign_flow_root.is_dir() else []:
        try:
            codes, meta = read_parquet_codes(path)
            foreign_codes |= codes
            foreign_sessions += 1
            foreign_rows += int(meta.get("rows", 0))
        except (OSError, ValueError, ImportError):
            continue
    sector_payload = load_json(args.sector_audit) if args.sector_audit.is_file() else {}
    sector_codes = nested_codes(sector_payload, {"ticker_values", "ticker", "code", "Code", "Ticker"})
    active_codes = nested_codes(load_json(args.active_listings), {"code", "Code", "ticker", "Ticker", "KodeEmiten"}) if args.active_listings.is_file() else set()
    current_rows = read_csv_rows(args.current_listings)
    delisting_rows = read_csv_rows(args.delisting_records)
    current_codes = {code for row in current_rows if (code := normalize_code(row.get("ticker")))}
    delisting_codes = {code for row in delisting_rows if (code := normalize_code(row.get("ticker")))}
    ksei_codes, ksei_details, ksei_meta = parse_ksei_sources(args.ksei_table, args.ksei_detail_root)

    public_sets: dict[str, set[str]] = {}
    dataset_saham_root = args.public_probes_root / "dataset-saham-idx" / "Saham" / "Semua"
    public_sets["public_dataset_saham_idx"] = {code for path in dataset_saham_root.glob("*.csv") if (code := normalize_code(path.stem))} if dataset_saham_root.is_dir() else set()
    mirror_root = args.public_probes_root / "idx-dataset" / "dataset" / "stocks" / "csv"
    public_sets["public_idx_dataset_mirror"] = {code for path in mirror_root.glob("*.csv") if (code := normalize_code(path.stem))} if mirror_root.is_dir() else set()
    ipo_root = args.public_probes_root / "web-indonesia-ipo-data" / "public" / "data"
    ipo_codes, ipo_nonstandard = parse_public_ipo_surface(ipo_root)
    ca_codes, ca_evidence = parse_corporate_action_probe(args.ca_announcement)
    public_sets["public_ipo_data"] = ipo_codes

    source_sets = normalize_source_sets({
        "clean_ohlcv_panel": panel_codes,
        "official_trading_history": trading_codes,
        "historical_anchor": anchor_codes,
        "security_master": security_master_codes,
        "official_current_listings": current_codes,
        "official_delisting_records": delisting_codes,
        "official_profiles": profile_codes,
        "official_issued_history": issued_codes,
        "annual_report_index": annual_codes,
        "financial_bundle": financial_codes,
        "official_foreign_flow": foreign_codes,
        "official_sector_constituents": sector_codes,
        "official_active_listings": active_codes,
        "official_corporate_action_events": ca_codes,
        "ksei_registered_shares_table": ksei_codes,
        **public_sets,
    })
    observed_union = set().union(*source_sets.values()) if source_sets else set()
    source_only_sets = {
        source: codes - set().union(*(other_codes for other_source, other_codes in source_sets.items() if other_source != source))
        for source, codes in source_sets.items()
    }
    intervals, lifecycle_meta = parse_lifecycle_rows(args.current_listings, args.delisting_records, args.security_master, args.lifecycle_conflicts)
    announcement_hits = parse_announcement_hits(args.public_probes_root, set(lifecycle_meta["conflict_codes"]))
    delisting_only_announcement_hits = parse_announcement_hits(args.public_probes_root, set(source_only_sets.get("official_delisting_records", set())))
    historical_only_announcement_audit = {
        "searched_code_count": len(source_only_sets.get("official_delisting_records", set())),
        "exact_hit_count": sum(len(items) for items in delisting_only_announcement_hits.values()),
        "exact_code_count": len(delisting_only_announcement_hits),
        "exact_hits": delisting_only_announcement_hits,
        "interpretation": "bounded retained announcement-search evidence only; zero exact hits are not evidence that historical delisting-only codes had no announcements",
    }
    conflict_source_audit = {
        code: {
            "interval_records_present": sum(1 for interval in intervals.get(code, []) if interval.get("kind") in {"DELISTING_RECORD", "CURRENT_LISTING_RECORD"}),
            "current_listing_records": sum(1 for interval in intervals.get(code, []) if interval.get("kind") == "CURRENT_LISTING_RECORD"),
            "delisting_records": sum(1 for interval in intervals.get(code, []) if interval.get("kind") == "DELISTING_RECORD"),
            "issued_event_count": len(issued.get(code, [])),
            "issued_event_types": sorted({clean_text(event.get("JenisTindakan")) for event in issued.get(code, []) if clean_text(event.get("JenisTindakan"))}),
            "profile_present": bool(profiles.get(code, {}).get("profile")),
            "ksei_detail_status": ksei_details.get(code, {}).get("parse_status"),
            "ksei_isin": ksei_details.get(code, {}).get("isin"),
            "exact_announcement_hits": announcement_hits.get(code, []),
            "announcement_search_interpretation": "bounded retained-search evidence only; no exact hit is not evidence of no announcement",
        }
        for code in lifecycle_meta["conflict_codes"]
    }
    rows: list[dict[str, Any]] = []
    for code in sorted(observed_union):
        memberships = sorted(source for source, codes in source_sets.items() if code in codes)
        detail = ksei_details.get(code, {})
        lifecycle_status = "CONFLICTING" if code in lifecycle_meta["conflict_codes"] else ("LIFECYCLE_PARTIAL" if intervals.get(code) or issued.get(code) else "UNKNOWN")
        identity_status = "IDENTITY_BOUNDED" if detail.get("parse_status") == "DETAIL_VALID" else ("IDENTITY_BOUNDED" if profiles.get(code, {}).get("profile") or security_master_rows.get(code) else "UNKNOWN")
        profile_record = profiles.get(code, {})
        profile_fields = profile_record.get("profile", {}) if isinstance(profile_record, dict) else {}
        profile_issuer = clean_text(profile_fields.get("NamaEmiten")) if isinstance(profile_fields, dict) else ""
        profile_summary = {
            "path": profile_record.get("path"),
            "parse_status": profile_record.get("parse_status"),
            "fields": {key: profile_fields.get(key) for key in ("KodeEmiten", "NamaEmiten", "TanggalPencatatan", "Status", "PapanPencatatan", "Sektor", "SubSektor", "Industri", "SubIndustri", "BAE") if profile_fields.get(key) not in (None, "")},
        }
        master_issuer = any(clean_text(item.get("company_name")) for item in security_master_rows.get(code, []))
        residual_flags = {
            "no_valid_ksei_detail": detail.get("parse_status") != "DETAIL_VALID",
            "no_isin": not bool(detail.get("isin")),
            "no_issuer": not bool(detail.get("issuer") or profile_issuer or master_issuer),
            "no_interval": not bool(intervals.get(code)),
            "lifecycle_conflict": code in lifecycle_meta["conflict_codes"],
            "pit_effective_date_unknown": True,
            "series_or_class_unknown": detail.get("parse_status") != "DETAIL_VALID" or not detail.get("type"),
        }
        residual_class = "LIFECYCLE_CONFLICT" if residual_flags["lifecycle_conflict"] else "PIT_EFFECTIVE_DATE_UNKNOWN" if residual_flags["pit_effective_date_unknown"] and not residual_flags["no_valid_ksei_detail"] and not residual_flags["no_interval"] else "IDENTITY_OR_LIFECYCLE_RESIDUAL"
        rows.append({
            "code": code,
            "source_membership": memberships,
            "source_count": len(memberships),
            "identity_status": identity_status,
            "lifecycle_status": lifecycle_status,
            "pit_effective_date_status": "UNKNOWN",
            "population_status": "OBSERVED_ONLY_POPULATION_UNKNOWN",
            "sources_examined": sorted(source_sets),
            "residual_class": residual_class,
            "missing_authority": [key for key, value in residual_flags.items() if value],
            "ksei": {key: detail.get(key) for key in ("parse_status", "security_name", "issuer", "isin", "short_code", "type", "listing_date", "status", "basic", "acquisition") if key in detail},
            "profile": profile_summary,
            "issued_history_events": issued.get(code, []),
            "lifecycle_intervals": intervals.get(code, []),
            "trading_summary": trading_meta.get(code),
            "report_summary": report_meta.get(code),
            "corporate_action_evidence": ca_evidence.get(code, []),
            "residual_flags": residual_flags,
        })
    source_census: dict[str, Any] = {}
    for source, codes in sorted(source_sets.items()):
        source_census[source] = {"count": len(codes), "codes": sorted(codes), "union_minus_source": sorted(observed_union - codes)}
    comparison_sources = ["clean_ohlcv_panel", "historical_anchor", "security_master", "official_trading_history", "official_profiles", "ksei_registered_shares_table", "official_current_listings", "official_delisting_records", "annual_report_index", "financial_bundle", "official_foreign_flow"]
    pairwise_differences: dict[str, Any] = {}
    for left in comparison_sources:
        for right in comparison_sources:
            if left >= right or left not in source_sets or right not in source_sets:
                continue
            left_codes = source_sets[left]
            right_codes = source_sets[right]
            pairwise_differences[f"{left}__vs__{right}"] = {"left_only_count": len(left_codes - right_codes), "right_only_count": len(right_codes - left_codes), "intersection_count": len(left_codes & right_codes), "left_only": sorted(left_codes - right_codes), "right_only": sorted(right_codes - left_codes)}
    profile_name_to_codes: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        profile_fields = row.get("profile", {}).get("fields", {})
        profile_name = clean_text(profile_fields.get("NamaEmiten")) if isinstance(profile_fields, dict) else ""
        if profile_name:
            profile_name_to_codes[profile_name.upper()].add(row["code"])
    ksei_issuer_to_securities: dict[str, list[dict[str, str | None]]] = defaultdict(list)
    for row in rows:
        detail = row.get("ksei", {})
        issuer = clean_text(detail.get("issuer"))
        if detail.get("parse_status") == "DETAIL_VALID" and issuer:
            ksei_issuer_to_securities[issuer.upper()].append({"code": row["code"], "isin": detail.get("isin"), "type": detail.get("type"), "security_name": detail.get("security_name")})
    identity_collision_census = {
        "status": "COUNTEREXAMPLES_PRESERVED_NO_COLLAPSE",
        "profile_name_multiple_code_groups": [
            {"normalized_profile_name": name, "codes": sorted(codes)}
            for name, codes in sorted(profile_name_to_codes.items())
            if len(codes) > 1
        ],
        "ksei_issuer_string_multiple_security_groups": [
            {"normalized_issuer_string": issuer, "securities": sorted(securities, key=lambda item: item["code"])}
            for issuer, securities in sorted(ksei_issuer_to_securities.items())
            if len({item["code"] for item in securities}) > 1
        ],
        "lifecycle_conflict_codes": sorted(lifecycle_meta["conflict_codes"]),
        "current_detail_contract_limits": {
            "one_attempt_per_code": True,
            "historical_ticker_reuse_proven": False,
            "multiple_isins_per_code_tested": False,
            "series_continuity_proven": False,
            "interpretation": "Repeated issuer/name strings and lifecycle conflicts are counterexamples to identity collapse, not proof of legal continuity or ticker reuse."
        },
    }
    packet = {
        "schema_version": "1.0",
        "status": "PASS_OBSERVED_POPULATION_CROSSWALK_NO_COMPLETENESS_ADMISSION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_used_by_parser": False,
        "canonical_mutation": False,
        "protected_boundary": "CLOSED",
        "authority_classifications": {"identity": "IDENTITY_BOUNDED", "lifecycle": "LIFECYCLE_PARTIAL", "pit_effective_date": "PIT_EFFECTIVE_DATE_UNKNOWN", "population": "POPULATION_UNKNOWN"},
        "observed_research_population": {"count": len(observed_union), "codes": sorted(observed_union), "definition": "Union of retained source populations; not a complete historical IDX denominator."},
        "source_census": source_census,
        "pairwise_differences": pairwise_differences,
        "identity_collision_census": identity_collision_census,
        "ksei_population_surface": ksei_meta,
        "lifecycle_surface": lifecycle_meta,
        "lifecycle_conflict_source_audit": conflict_source_audit,
        "historical_only_announcement_audit": historical_only_announcement_audit,
        "coverage_counts": {
            "identity_bounded_codes": sum(row["identity_status"] == "IDENTITY_BOUNDED" for row in rows),
            "identity_unknown_codes": sum(row["identity_status"] == "UNKNOWN" for row in rows),
            "lifecycle_partial_codes": sum(row["lifecycle_status"] == "LIFECYCLE_PARTIAL" for row in rows),
            "lifecycle_conflicting_codes": sum(row["lifecycle_status"] == "CONFLICTING" for row in rows),
            "lifecycle_unknown_codes": sum(row["lifecycle_status"] == "UNKNOWN" for row in rows),
            "issuer_name_evidence_codes": sum(not row["residual_flags"]["no_issuer"] for row in rows),
            "issuer_legal_continuity_proven_codes": 0,
            "pit_effective_date_proven_codes": 0,
            "pit_effective_date_unknown_codes": len(rows),
            "valid_ksei_detail_codes": sum(detail.get("parse_status") == "DETAIL_VALID" for detail in ksei_details.values()),
            "ksei_http_200_empty_or_mismatch_codes": sum(detail.get("parse_status") == "HTTP_200_EMPTY_OR_MISMATCH" for detail in ksei_details.values()),
            "ksei_http_non_200_codes": sum(detail.get("parse_status") == "HTTP_NON_200" for detail in ksei_details.values()),
        },
        "adversarial_counterexample_sets": {
            "official_trading_not_in_panel": sorted(trading_codes - panel_codes),
            "historical_anchor_not_in_panel": sorted(anchor_codes - panel_codes),
            "ksei_share_table_not_in_panel": sorted(ksei_codes - panel_codes),
            "observed_union_not_in_security_master": sorted(observed_union - security_master_codes),
            "observed_union_not_in_current_profile_files": sorted(observed_union - profile_codes),
            "profile_files_not_in_panel": sorted(profile_codes - panel_codes),
            "official_delisting_only": sorted(source_only_sets["official_delisting_records"]),
            "public_ipo_only": sorted(source_only_sets.get("public_ipo_data", set())),
            "public_ipo_nonstandard_identifiers": sorted(ipo_nonstandard),
            "profile_present_not_panel_or_master": sorted(profile_codes - panel_codes - security_master_codes),
        },
        "panel_meta": panel_meta,
        "financial_meta": financial_meta,
        "foreign_flow_meta": {"codes": len(foreign_codes), "sessions": foreign_sessions, "rows": foreign_rows},
        "report_index_meta": report_counts,
        "crosswalk_rows": rows,
        "downstream_impact": {
            "before": {"panel_codes": len(panel_codes), "security_master_codes": len(security_master_codes), "anchor_codes": len(anchor_codes), "financial_codes": len(financial_codes), "foreign_flow_codes": len(foreign_codes)},
            "after_observed_union": {"observed_union_codes": len(observed_union), "ksei_share_table_codes": len(ksei_codes), "ksei_valid_detail_codes": sum(detail.get("parse_status") == "DETAIL_VALID" for detail in ksei_details.values()), "lifecycle_interval_codes": len(intervals), "lifecycle_conflict_codes": len(lifecycle_meta["conflict_codes"])},
            "delta": {"observed_union_minus_panel": len(observed_union - panel_codes), "observed_union_minus_security_master": len(observed_union - security_master_codes), "observed_union_minus_anchor": len(observed_union - anchor_codes)},
            "still_unknown": ["historical population denominator", "daily PIT membership", "effective/knowledge timestamps", "issuer legal continuity", "corporate-action basis and identity linkage", "ticker reuse and relisting resolution"],
        },
        "source_provenance": [
            source_provenance("panel", [args.panel]), source_provenance("anchor", [args.anchor]), source_provenance("security_master", [args.security_master]), source_provenance("official_trading_summary", [args.official_summary]), source_provenance("ksei_share_table", [args.ksei_table]), source_provenance("ksei_detail_metadata", [args.ksei_detail_root / "acquisition_metadata.jsonl"]), source_provenance("current_listings", [args.current_listings]), source_provenance("delisting_records", [args.delisting_records]),
            source_provenance("financial_bundle", [args.financial_bundle]), source_provenance("profile_raw_root", [args.profile_root], "Per-code raw JSON files retained under this directory"), source_provenance("issued_history_raw_root", [args.issued_root], "Per-code raw JSON files retained under this directory"), source_provenance("annual_report_index_root", [args.annual_index_root], "Raw response files retained under this directory"), source_provenance("quarterly_report_index_root", [quarterly_root], "Raw response files retained under this directory"), source_provenance("foreign_flow_root", [args.foreign_flow_root], "Per-session parquet files retained under this directory"), source_provenance("sector_audit", [args.sector_audit]), source_provenance("active_listings", [args.active_listings]), source_provenance("corporate_action_probe", [args.ca_announcement] if args.ca_announcement else []), source_provenance("lifecycle_conflict_rows", [args.lifecycle_conflicts] if args.lifecycle_conflicts else []), source_provenance("public_probes_root", [args.public_probes_root], "Retained public-source cross-check roots; not authority"),
        ],
    }
    graph = build_identity_graph(sorted(observed_union), ksei_details, profiles, issued, security_master_rows, intervals, set(lifecycle_meta["conflict_codes"]))
    residuals = [row for row in rows if any(row["residual_flags"].values())]
    residual_packet = {"schema_version": "1.0", "status": "RESIDUALS_EXPLICIT_NO_INFERENCE", "count": len(residuals), "rows": residuals, "classes": dict(Counter("lifecycle_conflict" if row["residual_flags"]["lifecycle_conflict"] else "no_valid_ksei_detail" if row["residual_flags"]["no_valid_ksei_detail"] else "pit_effective_date_unknown" for row in residuals))}
    return packet, graph, residual_packet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--anchor", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--financial-bundle", type=Path, required=True)
    parser.add_argument("--official-summary", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, required=True)
    parser.add_argument("--issued-root", type=Path, required=True)
    parser.add_argument("--annual-index-root", type=Path, required=True)
    parser.add_argument("--quarterly-index-root", type=Path)
    parser.add_argument("--current-listings", type=Path, required=True)
    parser.add_argument("--delisting-records", type=Path, required=True)
    parser.add_argument("--lifecycle-conflicts", type=Path)
    parser.add_argument("--foreign-flow-root", type=Path, required=True)
    parser.add_argument("--sector-audit", type=Path, required=True)
    parser.add_argument("--active-listings", type=Path, required=True)
    parser.add_argument("--ca-announcement", type=Path)
    parser.add_argument("--ksei-table", type=Path, required=True)
    parser.add_argument("--ksei-detail-root", type=Path, required=True)
    parser.add_argument("--public-probes-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--graph-output", type=Path, required=True)
    parser.add_argument("--residual-output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    packet, graph, residuals = build_crosswalk(args)
    write_json(args.output, packet)
    write_json(args.graph_output, graph)
    write_json(args.residual_output, residuals)
    print(json.dumps({"status": packet["status"], "observed_union": packet["observed_research_population"]["count"], "ksei_valid_detail": packet["downstream_impact"]["after_observed_union"]["ksei_valid_detail_codes"], "lifecycle_conflicts": packet["lifecycle_surface"]["conflict_codes"], "output": str(args.output), "graph": str(args.graph_output), "residuals": str(args.residual_output)}, indent=2))


if __name__ == "__main__":
    main()
