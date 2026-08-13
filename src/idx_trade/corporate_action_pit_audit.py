"""Bounded live source/semantics audit for IDX corporate actions.

This module is deliberately an audit tool, not a canonical corporate-action
provider.  It preserves source-native dates and ratios, rejects incomplete
pages, and keeps raw captures outside Git through :class:`CaptureStore`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from lxml import html


IDX_ISSUED_HISTORY = "https://www.idx.id/primary/ListingActivity/GetIssuedHistory"
IDX_ANNOUNCEMENT = "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"
KSEI_BASE = "https://web.ksei.co.id"
KSEI_SECURITY = KSEI_BASE + "/services/registered-securities/shares/lc/{ticker}"
KSEI_SCHEDULES = {
    "cash_dividend": "/publications/corporate-action-schedules/cash-dividend",
    "share_bonus": "/publications/corporate-action-schedules/share-bonus",
    "rights_distribution": "/publications/corporate-action-schedules/rights-distribution",
    "mix_dividend": "/publications/corporate-action-schedules/mix-dividend",
    "masr": "/publications/corporate-action-schedules/masr",
}
JAKARTA = ZoneInfo("Asia/Jakarta")
UTC = timezone.utc


class AuditError(RuntimeError):
    """Raised when a source response cannot be classified safely."""


class CurlCffiTransport:
    """Chrome-impersonating transport used by the accepted direct-IDX lane."""

    def __init__(self, *, timeout: float = 60.0) -> None:
        from curl_cffi import requests

        # Keep the official IDX and public KSEI connection fingerprints
        # separate.  Reusing the IDX session can make KSEI return transient
        # 5xx pages after the IDX request batch; this is a transport guard,
        # not a retry or source substitution.
        self.idx_session = requests.Session(impersonate="chrome")
        # KSEI's public site currently serves its HTML reliably with the
        # stable Chrome 110 fingerprint; this remains the same curl_cffi
        # Chrome-impersonation transport, not a different provider.
        self.ksei_session = requests.Session(impersonate="chrome110")
        self.timeout = timeout
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "idx-trade-research/corporate-action-pit-audit-v1",
        }
        self.ksei_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": KSEI_BASE + "/",
            "User-Agent": "Mozilla/5.0",
        }

    def get(self, url: str, params: Mapping[str, Any] | None = None, *, ksei: bool = False) -> Any:
        session = self.ksei_session if ksei else self.idx_session
        return session.get(
            url,
            params=dict(params or {}),
            headers=self.ksei_headers if ksei else self.headers | {"Referer": "https://www.idx.co.id/"},
            timeout=self.timeout,
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


class CaptureStore:
    """Append-only raw capture store; existing bytes are never overwritten."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.raw = self.root / "raw"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.records: list[dict[str, Any]] = []

    def capture(
        self,
        *,
        name: str,
        response: Any,
        url: str,
        params: Mapping[str, Any] | None,
        source: str,
    ) -> dict[str, Any]:
        body = bytes(getattr(response, "content", b"") or b"")
        digest = sha256_bytes(body) if body else None
        path: Path | None = None
        if body:
            path = self.raw / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and sha256_file(path) != digest:
                path = path.with_name(f"{path.stem}__sha256_{digest[:16]}{path.suffix}")
            if not path.exists():
                path.write_bytes(body)
        record = {
            "source": source,
            "url": str(getattr(response, "url", url)),
            "requested_url": url,
            "params": dict(params or {}),
            "accessed_at_utc": _utc_now(),
            "status_code": int(getattr(response, "status_code", 0) or 0),
            "content_type": str(getattr(response, "headers", {}).get("content-type", "")),
            "bytes": len(body),
            "sha256": digest,
            "path": str(path) if path else None,
        }
        self.records.append(record)
        return record

    def write_manifest(
        self,
        *,
        inputs: Mapping[str, Any] | None = None,
        files: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> Path:
        manifest = {
            "manifest_version": "corporate_action_pit_source_audit_v1",
            "created_at_utc": _utc_now(),
            "inputs": dict(inputs or {}),
            "files": dict(files or {}),
            "requests": self.records,
        }
        path = self.root / "MANIFEST.json"
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return path


def _json_response(response: Any, *, source: str) -> Any:
    if int(getattr(response, "status_code", 0) or 0) != 200:
        raise AuditError(f"{source}: HTTP {getattr(response, 'status_code', None)}")
    try:
        return response.json()
    except Exception as exc:  # pragma: no cover - real transport guard
        raise AuditError(f"{source}: invalid JSON") from exc


def _int_field(value: Any, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise AuditError(f"invalid {name}: {value!r}") from exc
    if result < 0:
        raise AuditError(f"negative {name}: {result}")
    return result


def fetch_idx_issued_history(
    transport: CurlCffiTransport,
    store: CaptureStore,
    *,
    ca_type: str,
    date_from: str,
    date_to: str,
    page_size: int = 250,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch all declared rows and fail closed on partial pages."""

    if page_size <= 0:
        raise ValueError("page_size must be positive")
    rows: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    start = 0
    expected: int | None = None
    while True:
        params = {
            "caType": ca_type,
            "dateFrom": date_from,
            "dateTo": date_to,
            "start": start,
            "length": page_size,
        }
        response = transport.get(IDX_ISSUED_HISTORY, params)
        store.capture(name=f"idx_issued_{ca_type or 'all'}_{start}.json", response=response, url=IDX_ISSUED_HISTORY, params=params, source="IDX_ISSUED_HISTORY")
        payload = _json_response(response, source="IDX_ISSUED_HISTORY")
        if not isinstance(payload, Mapping) or not isinstance(payload.get("data"), list):
            raise AuditError("IDX_ISSUED_HISTORY: missing data list")
        declared = payload.get("recordsFiltered", payload.get("recordsTotal"))
        declared_total = _int_field(declared, "recordsFiltered")
        expected = declared_total if expected is None else expected
        if declared_total != expected:
            raise AuditError("IDX_ISSUED_HISTORY: declared total changed during pagination")
        page_rows = payload["data"]
        if len(page_rows) > page_size or start > declared_total:
            raise AuditError("IDX_ISSUED_HISTORY: invalid page size/offset")
        if declared_total > start and not page_rows:
            raise AuditError("IDX_ISSUED_HISTORY: empty page before declared total")
        for row in page_rows:
            if not isinstance(row, Mapping):
                raise AuditError("IDX_ISSUED_HISTORY: malformed row")
            rows.append(dict(row))
        pages.append({"start": start, "length": page_size, "declared_total": declared_total, "returned": len(page_rows)})
        if len(rows) >= declared_total:
            if len(rows) != declared_total:
                raise AuditError("IDX_ISSUED_HISTORY: returned rows do not equal declared total")
            break
        start += page_size
    return rows, pages


def _parse_source_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed.date().isoformat()


def _date_token(text: str) -> str | None:
    # KSEI renders a hidden YYYYMMDD token immediately adjacent to the
    # visible localized date (for example ``2026062929 Jun 2026``).
    match = re.search(r"(?<!\d)(20\d{6})", text)
    if not match:
        return None
    raw = match.group(1)
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def _cell_date(cell: Any) -> str | None:
    return _date_token(" ".join(cell.text_content().split()))


def _normalise_ratio(text: str) -> dict[str, Any]:
    clean = " ".join(text.split())
    match = re.search(r"\(\s*([0-9.]+)\s+([^:()]+?)\s*:\s*([0-9.]+)\s+([^()]+?)\s*\)", clean)
    if not match:
        return {"ratio_raw": clean, "ratio_parse_status": "UNRESOLVED"}
    return {
        "ratio_raw": clean,
        "ratio_left_value": match.group(1),
        "ratio_left_security": match.group(2).strip(),
        "ratio_right_value": match.group(3),
        "ratio_right_security": match.group(4).strip(),
        "ratio_parse_status": "PARSED_SOURCE_TEXT_ONLY",
    }


def parse_ksei_security_page(payload: bytes, *, ticker: str, source_url: str, source_sha256: str) -> list[dict[str, Any]]:
    """Parse the visible KSEI corporate-action table without inferring semantics."""

    document = html.fromstring(payload)
    tables = []
    for table in document.xpath("//table"):
        headers = [" ".join(cell.text_content().split()) for cell in table.xpath(".//thead//th")]
        if headers[:6] == ["Type of CA", "Ratio", "Cum Date", "Record Date", "Distribution Date", "Status"]:
            tables.append(table)
    if len(tables) != 1:
        raise AuditError(f"KSEI {ticker}: expected one visible corporate-action table")
    rows: list[dict[str, Any]] = []
    for tr in tables[0].xpath(".//tbody/tr"):
        cells = tr.xpath("./td")
        if len(cells) != 6:
            raise AuditError(f"KSEI {ticker}: malformed corporate-action row")
        values = [" ".join(cell.text_content().split()) for cell in cells]
        ratio = _normalise_ratio(values[1])
        rows.append({
            "ticker": ticker,
            "event_family_source": values[0],
            "cum_date": _cell_date(cells[2]),
            "record_date": _cell_date(cells[3]),
            "distribution_date": _cell_date(cells[4]),
            "status": values[5],
            "source_url": source_url,
            "source_sha256": source_sha256,
            **ratio,
        })
    return rows


def parse_ksei_schedule_page(payload: bytes, *, schedule_family: str, source_url: str, source_sha256: str) -> list[dict[str, Any]]:
    document = html.fromstring(payload)
    matches = []
    for table in document.xpath("//table"):
        headers = [" ".join(cell.text_content().split()) for cell in table.xpath(".//thead//th")]
        if headers[:3] == ["Nomor Surat", "Perihal", "Tanggal"]:
            matches.append(table)
    if len(matches) != 1:
        raise AuditError(f"KSEI schedule {schedule_family}: expected one table")
    rows: list[dict[str, Any]] = []
    for tr in matches[0].xpath(".//tbody/tr"):
        cells = tr.xpath("./td")
        if len(cells) < 3:
            raise AuditError(f"KSEI schedule {schedule_family}: malformed row")
        links = [urljoin(KSEI_BASE + "/", a.get("href")) for a in tr.xpath(".//a[@href]") if a.get("href")]
        rows.append({
            "schedule_family": schedule_family,
            "reference": " ".join(cells[0].text_content().split()),
            "subject": " ".join(cells[1].text_content().split()),
            "document_date": _cell_date(cells[2]),
            "document_url": links[0] if links else None,
            "source_url": source_url,
            "source_sha256": source_sha256,
        })
    return rows


def _parse_announcement_time(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise AuditError("IDX announcement: missing TglPengumuman")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=JAKARTA)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def fetch_idx_announcements(
    transport: CurlCffiTransport,
    store: CaptureStore,
    *,
    ticker: str,
    date_from: str,
    date_to: str,
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    params = {
        "kodeEmiten": ticker,
        "emitenType": "*",
        "indexFrom": 0,
        "pageSize": page_size,
        "dateFrom": date_from,
        "dateTo": date_to,
        "lang": "id",
        "keyword": "",
    }
    response = transport.get(IDX_ANNOUNCEMENT, params)
    store.capture(name=f"idx_announcement_{ticker}_{date_from}_{date_to}.json", response=response, url=IDX_ANNOUNCEMENT, params=params, source="IDX_ANNOUNCEMENT")
    payload = _json_response(response, source="IDX_ANNOUNCEMENT")
    if not isinstance(payload, Mapping) or not isinstance(payload.get("Replies"), list):
        raise AuditError("IDX_ANNOUNCEMENT: missing Replies")
    declared = _int_field(payload.get("ResultCount"), "ResultCount")
    replies = payload["Replies"]
    if declared != len(replies):
        raise AuditError(f"IDX_ANNOUNCEMENT: incomplete page {declared} != {len(replies)}")
    return [dict(row) for row in replies if isinstance(row, Mapping)]


EVENT_TOKENS = {
    "CASH_DIVIDEND": ("cash dividend", "dividen tunai", "dividen interim"),
    "STOCK_SPLIT": ("stock split", "pemecahan saham"),
    "RIGHTS_ISSUE": ("hmetd", "hak memesan efek", "penawaran umum terbatas"),
    "BONUS_SHARES": ("saham bonus", "bonus"),
    "STOCK_DIVIDEND": ("dividen saham", "stock dividend"),
    "CAPITAL_REDUCTION": ("pengurangan modal", "pengurangan jumlah saham", "capital reduction"),
    "PARTIAL_DELISTING": ("partial delisting", "penghapusan pencatatan", "pengurangan modal"),
    "IPO": ("pencatatan saham", "penawaran umum perdana", "ipo"),
}


def match_announcement_candidates(
    replies: Sequence[Mapping[str, Any]],
    *,
    ticker: str,
    event_family: str,
    action_date: str,
    max_days: int = 120,
) -> list[dict[str, Any]]:
    target = date.fromisoformat(action_date)
    tokens = EVENT_TOKENS.get(event_family, ())
    matches: list[dict[str, Any]] = []
    for reply in replies:
        announcement = reply.get("pengumuman") or reply.get("Pengumuman")
        attachments = reply.get("attachments") or reply.get("Attachments") or []
        if not isinstance(announcement, Mapping):
            continue
        announced_ticker = str(announcement.get("Kode_Emiten") or "").strip().upper()
        if announced_ticker not in {"", ticker.upper()}:
            continue
        announced_at = str(announcement.get("TglPengumuman") or "")
        try:
            announced_date = datetime.fromisoformat(announced_at.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        if abs((announced_date - target).days) > max_days:
            continue
        text_parts = [str(announcement.get(key) or "") for key in ("JudulPengumuman", "PerihalPengumuman")]
        usable_attachments = attachments if isinstance(attachments, list) else []
        for attachment in usable_attachments:
            if isinstance(attachment, Mapping):
                text_parts.extend(str(attachment.get(key) or "") for key in ("OriginalFilename", "PDFFilename"))
        haystack = " ".join(text_parts).casefold()
        if not any(token.casefold() in haystack for token in tokens):
            continue
        primary = next((a for a in usable_attachments if isinstance(a, Mapping) and a.get("FullSavePath") and not a.get("IsAttachment")), None)
        if primary is None:
            primary = next((a for a in usable_attachments if isinstance(a, Mapping) and a.get("FullSavePath")), None)
        matches.append({
            "ticker": ticker.upper(),
            "event_family": event_family,
            "action_date": action_date,
            "announcement_ref": announcement.get("NoPengumuman") or announcement.get("Id2"),
            "published_at_utc": _parse_announcement_time(announcement.get("TglPengumuman")),
            "title": announcement.get("JudulPengumuman"),
            "subject": announcement.get("PerihalPengumuman"),
            "attachment_url": primary.get("FullSavePath") if isinstance(primary, Mapping) else None,
            "attachment_filename": (primary.get("OriginalFilename") or primary.get("PDFFilename")) if isinstance(primary, Mapping) else None,
        })
    return matches


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, ensure_ascii=False) + "\n")


def run_bounded_audit(
    output_root: str | Path,
    *,
    date_from: str = "20180101",
    date_to: str = "20260814",
    ksei_tickers: Sequence[str] = ("IDPR", "TRST", "SINI", "MEGA", "MLPT", "RAJA"),
) -> dict[str, Any]:
    """Run the bounded live audit and persist all normalized evidence."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    transport = CurlCffiTransport()
    store = CaptureStore(root)

    # Acquire the small public-KSEI sample before the larger IDX request batch;
    # the public site can rate-limit later HTML requests after a burst of IDX
    # calls, even when the KSEI session itself is separate.
    ksei_rows: list[dict[str, Any]] = []
    ksei_failures: list[dict[str, Any]] = []
    ksei_home_url = KSEI_BASE + "/"
    ksei_home = transport.get(ksei_home_url, ksei=True)
    store.capture(name="ksei_home.html", response=ksei_home, url=ksei_home_url, params={}, source="KSEI_HOME")
    for ticker in ksei_tickers:
        url = KSEI_SECURITY.format(ticker=ticker)
        response = transport.get(url, ksei=True)
        record = store.capture(name=f"ksei_security_{ticker}.html", response=response, url=url, params={}, source="KSEI_REGISTERED_SECURITY")
        if record["status_code"] != 200 or not record["sha256"]:
            ksei_failures.append({"ticker": ticker, "status_code": record["status_code"]})
            continue
        try:
            ksei_rows.extend(parse_ksei_security_page(response.content, ticker=ticker, source_url=url, source_sha256=record["sha256"]))
        except AuditError as exc:
            ksei_failures.append({"ticker": ticker, "error": str(exc)})

    schedule_rows: list[dict[str, Any]] = []
    schedule_failures: list[dict[str, Any]] = []
    schedule_targets = {"cash_dividend": "IDPR", "share_bonus": "MEGA", "rights_distribution": "SINI", "mix_dividend": "MEGA", "masr": ""}
    for family, path in KSEI_SCHEDULES.items():
        url = KSEI_BASE + path
        response = transport.get(url, ksei=True)
        record = store.capture(name=f"ksei_schedule_{family}.html", response=response, url=url, params={}, source="KSEI_CA_SCHEDULE")
        if record["status_code"] != 200 or not record["sha256"]:
            schedule_failures.append({"schedule_family": family, "status_code": record["status_code"]})
            continue
        try:
            parsed = parse_ksei_schedule_page(response.content, schedule_family=family, source_url=url, source_sha256=record["sha256"])
            target = schedule_targets[family].casefold()
            schedule_rows.extend(row for row in parsed if not target or target in str(row.get("subject", "")).casefold())
        except AuditError as exc:
            schedule_failures.append({"schedule_family": family, "error": str(exc)})

    requested_types = ("hmetd", "PrivatePlacement", "stockSplit", "reverseStock", "BuybackSaham", "ipo", "companyListing", "partialDelisting")
    issued_by_query: dict[str, list[dict[str, Any]]] = {}
    page_meta: dict[str, list[dict[str, Any]]] = {}
    failures: list[dict[str, Any]] = []
    for ca_type in ("", *requested_types):
        try:
            rows, pages = fetch_idx_issued_history(transport, store, ca_type=ca_type, date_from=date_from, date_to=date_to, page_size=250)
            issued_by_query[ca_type or "ALL"] = rows
            page_meta[ca_type or "ALL"] = pages
        except AuditError as exc:
            failures.append({"source": "IDX_ISSUED_HISTORY", "ca_type": ca_type, "error": str(exc)})

    # One deliberately small page establishes that declared totals require pagination.
    probe_params = {"caType": "hmetd", "dateFrom": date_from, "dateTo": date_to, "start": 0, "length": 1}
    probe = transport.get(IDX_ISSUED_HISTORY, probe_params)
    store.capture(name="idx_issued_hmetd_pagination_probe.json", response=probe, url=IDX_ISSUED_HISTORY, params=probe_params, source="IDX_ISSUED_HISTORY_PAGINATION_PROBE")
    probe_payload = _json_response(probe, source="IDX_ISSUED_HISTORY_PAGINATION_PROBE")
    pagination_probe = {"declared_total": probe_payload.get("recordsFiltered"), "returned": len(probe_payload.get("data", [])) if isinstance(probe_payload, Mapping) else None, "length": 1}

    all_rows = issued_by_query.get("ALL", [])
    candidate_rows: list[dict[str, Any]] = []
    wanted_by_family = {
        "STOCK_SPLIT": {"MLPT", "BBNI", "ISAT", "SCMA", "RAJA"},
        "RIGHTS_ISSUE": {"SINI"},
        "BONUS_SHARES": {"MEGA"},
        "STOCK_DIVIDEND": {"MEGA"},
        "CAPITAL_REDUCTION": {"SCMA"},
        "PARTIAL_DELISTING": {"MEGA"},
        "IPO": {"RANS"},
    }
    family_map = {"stockSplit": "STOCK_SPLIT", "hmetd": "RIGHTS_ISSUE", "sahamBonus": "BONUS_SHARES", "Dividen Saham": "STOCK_DIVIDEND", "kurangModal": "CAPITAL_REDUCTION", "partialDelisting": "PARTIAL_DELISTING", "ipo": "IPO"}
    for row in all_rows:
        family = family_map.get(str(row.get("JenisTindakan")))
        if not family:
            continue
        ticker = str(row.get("KodeEmiten") or "").strip().upper()
        targets = wanted_by_family[family]
        if targets and ticker not in targets:
            continue
        candidate_rows.append({
            "ticker": ticker,
            "event_family": family,
            "source_action": row.get("JenisTindakan"),
            "source_id": row.get("id"),
            "listing_action_date": _parse_source_date(row.get("TanggalPencatatan")),
            "action_shares": row.get("JumlahSaham"),
            "total_shares_after_action": row.get("JumlahSahamSetelahTindakan"),
            "raw": row,
        })
    # Retain at most one non-placeholder row per family/ticker/date, plus every
    # duplicate stock-split row because duplicate handling is itself audited.
    selected: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in candidate_rows:
        key = (row["ticker"], row["event_family"], row["listing_action_date"], row["source_id"] if row["event_family"] == "STOCK_SPLIT" else None)
        if key not in seen:
            seen.add(key)
            selected.append(row)

    # Fetch only announcement windows for the selected direct-activity rows.
    announcement_rows: list[dict[str, Any]] = []
    announcement_failures: list[dict[str, Any]] = []
    announcement_targets = list(selected)
    # Add a few KSEI-led cases so cash-dividend history, a cancelled event,
    # and a KSEI/IDX non-join are explicitly tested without broad crawling.
    announcement_targets.extend([
        {"ticker": "IDPR", "event_family": "CASH_DIVIDEND", "listing_action_date": "2026-06-29", "source_id": "KSEI-IDPR-2026-06-29"},
        {"ticker": "TRST", "event_family": "CASH_DIVIDEND", "listing_action_date": "2020-09-04", "source_id": "KSEI-TRST-CANCELLED-2020-09-04"},
        {"ticker": "SINI", "event_family": "RIGHTS_ISSUE", "listing_action_date": "2026-07-08", "source_id": "KSEI-SINI-2026-07-08"},
        {"ticker": "MEGA", "event_family": "BONUS_SHARES", "listing_action_date": "2026-04-09", "source_id": "KSEI-MEGA-2026-04-09"},
    ])
    for index, candidate in enumerate(announcement_targets):
        action_date = candidate.get("listing_action_date")
        if not action_date:
            continue
        action = date.fromisoformat(action_date)
        window_from = (action - timedelta(days=120)).strftime("%Y%m%d")
        window_to = (action + timedelta(days=120)).strftime("%Y%m%d")
        ticker = str(candidate["ticker"])
        try:
            replies = fetch_idx_announcements(transport, store, ticker=ticker, date_from=window_from, date_to=window_to)
            matches = match_announcement_candidates(replies, ticker=ticker, event_family=str(candidate["event_family"]), action_date=action_date)
            for match in matches:
                match["source_action_id"] = candidate.get("source_id")
                match["join_status"] = "MULTIPLE_REVISION_CANDIDATES" if len(matches) > 1 else "UNIQUE_EVENT_FAMILY_CANDIDATE"
                if match.get("attachment_url"):
                    attachment_url = str(match["attachment_url"])
                    safe_name = f"idx_announcement_attachment_{index}_{Path(attachment_url.split('?')[0]).name}"
                    attachment_response = transport.get(attachment_url)
                    attachment_record = store.capture(name=safe_name, response=attachment_response, url=attachment_url, params={}, source="IDX_ANNOUNCEMENT_ATTACHMENT")
                    match["attachment_sha256"] = attachment_record["sha256"]
                    match["attachment_status_code"] = attachment_record["status_code"]
                announcement_rows.append(match)
        except AuditError as exc:
            announcement_failures.append({"ticker": ticker, "event_family": candidate["event_family"], "source_id": candidate.get("source_id"), "error": str(exc)})

    event_counts = Counter(str(row.get("event_family")) for row in selected)
    raw_type_counts = Counter(str(row.get("JenisTindakan")) for row in all_rows)
    date_values = [row["listing_action_date"] for row in selected if row.get("listing_action_date")]
    arithmetic = {"positive_derivable": 0, "placeholder_or_invalid": 0, "not_share_count_family": 0}
    for row in selected:
        action = row["source_action"]
        try:
            action_shares = float(row["action_shares"] or 0)
            after = float(row["total_shares_after_action"] or 0)
        except (TypeError, ValueError):
            action_shares = after = 0
        if action == "stockSplit":
            if action_shares > 0 and after > action_shares:
                arithmetic["positive_derivable"] += 1
            else:
                arithmetic["placeholder_or_invalid"] += 1
        else:
            arithmetic["not_share_count_family"] += 1

    linkage_rows: list[dict[str, Any]] = []
    for candidate in selected:
        matches = [row for row in announcement_rows if row.get("source_action_id") == candidate.get("source_id")]
        k_matches = [row for row in ksei_rows if row.get("ticker") == candidate.get("ticker")]
        exact_ksei = []
        for row in k_matches:
            dates = {row.get("cum_date"), row.get("record_date"), row.get("distribution_date")}
            if candidate.get("listing_action_date") in dates:
                exact_ksei.append(row)
        linkage_rows.append({
            "ticker": candidate["ticker"],
            "event_family": candidate["event_family"],
            "source_action_id": candidate["source_id"],
            "listing_action_date": candidate["listing_action_date"],
            "idx_announcement_candidate_count": len(matches),
            "ksei_security_candidate_count": len(k_matches),
            "strict_ksei_idx_date_join_count": len(exact_ksei),
            "publication_linkage_status": "UNRESOLVED" if len(matches) != 1 else "UNIQUE_EVENT_FAMILY_CANDIDATE",
            "ksei_idx_linkage_status": "EXACT_DATE_JOIN" if len(exact_ksei) == 1 else ("AMBIGUOUS" if len(exact_ksei) > 1 else "NO_EXACT_DATE_JOIN"),
        })

    unresolved = [row for row in linkage_rows if row["publication_linkage_status"] == "UNRESOLVED" or row["ksei_idx_linkage_status"] != "EXACT_DATE_JOIN"]
    summary = {
        "verdict": "CONDITIONAL_SOURCE_USEFUL_PIT_LINKAGE_INCOMPLETE",
        "scope": {"date_from": date_from, "date_to": date_to, "bounded_candidate_rows": len(selected), "announcement_target_rows": len(announcement_targets), "ksei_security_tickers": list(ksei_tickers)},
        "requests": {"total": len(store.records), "idx_issued_history": sum(1 for r in store.records if r["source"].startswith("IDX_ISSUED_HISTORY")), "idx_announcements": sum(1 for r in store.records if r["source"] == "IDX_ANNOUNCEMENT"), "idx_announcement_attachments": sum(1 for r in store.records if r["source"] == "IDX_ANNOUNCEMENT_ATTACHMENT"), "ksei_security": sum(1 for r in store.records if r["source"] == "KSEI_REGISTERED_SECURITY"), "ksei_schedules": sum(1 for r in store.records if r["source"] == "KSEI_CA_SCHEDULE")},
        "failures": {"idx": failures + announcement_failures, "ksei_security": ksei_failures, "ksei_schedule": schedule_failures},
        "idx_raw_type_counts": dict(sorted(raw_type_counts.items())),
        "requested_ca_type_results": {key or "ALL": {"rows": len(value), "pages": page_meta.get(key or "ALL", [])} for key, value in issued_by_query.items()},
        "pagination_probe": pagination_probe,
        "selected_event_counts": dict(sorted(event_counts.items())),
        "selected_date_range": {"earliest": min(date_values) if date_values else None, "latest": max(date_values) if date_values else None},
        "ksei_security_rows": len(ksei_rows),
        "ksei_event_family_counts": dict(sorted(Counter(str(row["event_family_source"]) for row in ksei_rows).items())),
        "ksei_date_range_by_ticker": {ticker: {"earliest": min((r["cum_date"] or r["record_date"] or r["distribution_date"] for r in ksei_rows if r["ticker"] == ticker), default=None), "latest": max((r["distribution_date"] or r["record_date"] or r["cum_date"] for r in ksei_rows if r["ticker"] == ticker), default=None)} for ticker in ksei_tickers},
        "ksei_status_counts": dict(sorted(Counter(str(row["status"]) for row in ksei_rows).items())),
        "ksei_revision_or_cancelled_rows": sum(1 for row in ksei_rows if str(row["status"]).casefold() in {"cancelled", "changed", "revised"}),
        "schedule_rows": len(schedule_rows),
        "announcement_candidate_rows": len(announcement_rows),
        "unique_publication_linkages": sum(1 for row in linkage_rows if row["publication_linkage_status"] == "UNIQUE_EVENT_FAMILY_CANDIDATE"),
        "strict_ksei_idx_linkages": sum(1 for row in linkage_rows if row["ksei_idx_linkage_status"] == "EXACT_DATE_JOIN"),
        "ambiguous_or_unresolved_rows": len(unresolved),
        "old_provider_arithmetic": arithmetic,
        "revision_cancellation_policy": "append-only source rows; no later status overwrites an earlier observation",
        "date_semantics": "TanggalPencatatan, Cum Date, Record Date, Distribution Date, and TglPengumuman remain source-specific; no generic effective_date was materialized",
        "boundaries": {"network_calls": True, "bulk_backfill": False, "ohlc_adjustment": False, "features_models": False, "protected_outcomes": False, "ksei_credentials": False},
    }
    _write_jsonl(root / "normalized_candidates.jsonl", selected)
    _write_jsonl(root / "ksei_security_actions.jsonl", ksei_rows)
    _write_jsonl(root / "ksei_schedule_rows.jsonl", schedule_rows)
    _write_jsonl(root / "idx_announcement_linkages.jsonl", announcement_rows)
    _write_jsonl(root / "cross_source_linkage.jsonl", linkage_rows)
    _write_jsonl(root / "unresolved_ambiguous.jsonl", unresolved)
    _write_json(root / "summary.json", summary)
    artifact_paths = [
        path for path in root.iterdir()
        if path.is_file() and path.name not in {"summary.json", "MANIFEST.json"}
    ]
    summary["artifact_hashes"] = {path.name: sha256_file(path) for path in artifact_paths}
    _write_json(root / "summary.json", summary)
    manifest_files = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in root.iterdir()
        if path.is_file() and path.name != "MANIFEST.json"
    }
    manifest = store.write_manifest(
        inputs={"date_from": date_from, "date_to": date_to, "selected_ksei_tickers": list(ksei_tickers), "source_branch": "data/corporate-action-pit-source-audit-v1"},
        files=manifest_files,
    )
    summary["manifest_sha256"] = sha256_file(manifest)
    # Do not rewrite summary.json after the manifest is written: that would
    # invalidate the summary hash recorded in the immutable manifest. The
    # returned in-memory summary still exposes the manifest hash to callers.
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--date-from", default="20180101")
    parser.add_argument("--date-to", default="20260814")
    args = parser.parse_args(argv)
    summary = run_bounded_audit(args.output_root, date_from=args.date_from, date_to=args.date_to)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
