"""Fail-closed direct IDX Financial PIT publication-chain adapter.

The adapter intentionally stops at source-readiness.  It does not parse
financial facts or derive features.  A filing is PIT-ready only when the
report row, complete issuer-announcement response, exact attachment filename,
matching bytes, explicit statement scope, and a valid publication timestamp
are all present.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import urljoin
from zoneinfo import ZoneInfo


IDX_BASE_URL = "https://www.idx.co.id/primary"
FINANCIAL_REPORT_ENDPOINT = "/ListedCompany/GetFinancialReport"
ANNOUNCEMENT_ENDPOINT = "/ListedCompany/GetAnnouncement"
JAKARTA = ZoneInfo("Asia/Jakarta")


class AdapterError(RuntimeError):
    """Raised only for transport/storage failures that cannot be classified."""


class ResolutionStatus(StrEnum):
    PIT_READY = "PIT_READY"
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"
    REPORT_AMBIGUOUS = "REPORT_AMBIGUOUS"
    ANNOUNCEMENT_NOT_FOUND = "ANNOUNCEMENT_NOT_FOUND"
    INCOMPLETE_PAGINATION = "INCOMPLETE_PAGINATION"
    ATTACHMENT_NOT_MATCHED = "ATTACHMENT_NOT_MATCHED"
    ATTACHMENT_AMBIGUOUS = "ATTACHMENT_AMBIGUOUS"
    ATTACHMENT_HASH_UNVERIFIED = "ATTACHMENT_HASH_UNVERIFIED"
    ATTACHMENT_HASH_CONFLICT = "ATTACHMENT_HASH_CONFLICT"
    SCOPE_UNRESOLVED = "SCOPE_UNRESOLVED"
    MALFORMED_TIMESTAMP = "MALFORMED_TIMESTAMP"
    HTTP_FAILURE = "HTTP_FAILURE"
    PAYLOAD_INVALID = "PAYLOAD_INVALID"
    REVISION_HASH_CONFLICT = "REVISION_HASH_CONFLICT"


class ResponseLike(Protocol):
    status_code: int
    content: bytes
    headers: Mapping[str, str]

    def json(self) -> Any: ...


class Transport(Protocol):
    def get(self, endpoint: str, params: Mapping[str, Any]) -> ResponseLike: ...


class CurlCffiTransport:
    """Small direct IDX transport; curl_cffi is imported only at runtime."""

    def __init__(
        self,
        base_url: str = IDX_BASE_URL,
        *,
        timeout: float = 60.0,
        impersonate: str = "chrome",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.impersonate = impersonate

    def get(self, endpoint: str, params: Mapping[str, Any]) -> ResponseLike:
        from curl_cffi import requests

        url = endpoint if endpoint.startswith("http") else self.base_url + endpoint
        return requests.get(
            url,
            params=dict(params),
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-language": "en-US,en;q=0.9",
                "referer": "https://www.idx.co.id/",
            },
            impersonate=self.impersonate,
            timeout=self.timeout,
        )


class ImmutableCaptureStore:
    """External raw store. Existing bytes are never overwritten."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, relative_name: str, payload: bytes) -> tuple[str, str]:
        if not payload:
            raise AdapterError(f"empty raw payload: {relative_name}")
        target = self.root / relative_name
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(payload).hexdigest()
        if target.exists():
            existing = target.read_bytes()
            existing_digest = hashlib.sha256(existing).hexdigest()
            if existing_digest != digest:
                # Preserve a changed response as a separate observed version;
                # logical filing conflicts are rejected by RevisionLedger.
                target = target.with_name(f"{target.stem}__sha256_{digest[:16]}{target.suffix}")
                if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                    raise AdapterError(f"immutable capture conflict: {target}")
                target.write_bytes(payload)
                return str(target), digest
        else:
            target.write_bytes(payload)
        return str(target), digest


def parse_idx_publication_timestamp(value: Any) -> tuple[str, str]:
    """Parse IDX naive local time, attach Asia/Jakarta, and return UTC ISO."""

    text = str(value or "").strip()
    if not text or re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError("publication timestamp must include a time")
    try:
        timestamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"malformed IDX timestamp: {value!r}") from exc
    if timestamp.tzinfo is None:
        local = timestamp.replace(tzinfo=JAKARTA)
    else:
        local = timestamp
    utc = local.astimezone(ZoneInfo("UTC"))
    return utc.isoformat().replace("+00:00", "Z"), "Asia/Jakarta" if timestamp.tzinfo is None else str(timestamp.tzinfo)


def _as_int(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field_name}: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"negative {field_name}: {parsed}")
    return parsed


def _period_key(value: Any) -> str:
    return str(value or "").strip().upper()


def _reply_parts(reply: Mapping[str, Any]) -> tuple[Mapping[str, Any], list[Mapping[str, Any]]]:
    announcement = reply.get("pengumuman") or reply.get("Pengumuman")
    attachments = reply.get("attachments") or reply.get("Attachments") or []
    if not isinstance(announcement, Mapping) or not isinstance(attachments, list):
        raise ValueError("invalid IDX announcement reply shape")
    return announcement, [item for item in attachments if isinstance(item, Mapping)]


@dataclass(frozen=True)
class Resolution:
    ticker: str
    year: int
    requested_period: str
    status: ResolutionStatus
    report_found: bool = False
    announcement_found: bool = False
    exact_attachment_join: bool = False
    pit_ready: bool = False
    report_row: Mapping[str, Any] | None = None
    matched_attachments: tuple[Mapping[str, Any], ...] = ()
    publication_at_utc: str | None = None
    publication_timezone: str | None = None
    source_sha256: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    detail: str = ""


@dataclass
class RevisionLedger:
    """Preserve versions and reject same logical filing/time hash conflicts."""

    _seen: dict[tuple[str, int, str, str, str], set[str]] = field(default_factory=dict)

    def add(
        self,
        *,
        ticker: str,
        year: int,
        period: str,
        scope: str,
        knowledge_at_utc: str,
        source_sha256: str,
    ) -> None:
        key = (ticker, year, period, scope, knowledge_at_utc)
        hashes = self._seen.setdefault(key, set())
        hashes.add(source_sha256)
        if len(hashes) > 1:
            raise ValueError(f"conflicting hashes for logical filing {key}")


def _choose_report_attachments(attachments: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Pick one deterministic representation; preserve versions, not duplicates."""

    valid = [item for item in attachments if str(item.get("File_Name") or "").strip()]
    if not valid:
        return []

    def rank(item: Mapping[str, Any]) -> tuple[int, str]:
        name = str(item.get("File_Name") or "").lower()
        if name.endswith(".xlsx") and "financialstatement" in name:
            priority = 0
        elif name.endswith(".zip") and ("xbrl" in name or "instance" in name):
            priority = 1
        elif name.endswith(".pdf") and "financialstatement" in name:
            priority = 2
        else:
            priority = 3
        return priority, name

    return [sorted(valid, key=rank)[0]]


class DirectIdxFinancialPITAdapter:
    """Resolve direct IDX financial-report rows into fail-closed PIT records."""

    def __init__(
        self,
        transport: Transport,
        *,
        capture_store: ImmutableCaptureStore | None = None,
        base_url: str = IDX_BASE_URL,
        statement_scope_resolver: Callable[[bytes, Mapping[str, Any]], str | None] | None = None,
        page_size: int = 1000,
    ) -> None:
        self.transport = transport
        self.capture_store = capture_store
        self.base_url = base_url.rstrip("/")
        self.statement_scope_resolver = statement_scope_resolver
        self.page_size = page_size
        self.revisions = RevisionLedger()

    def _request_json(self, endpoint: str, params: Mapping[str, Any], capture_name: str) -> Any:
        response = self.transport.get(endpoint, params)
        if response is None or response.status_code != 200:
            raise AdapterError(f"HTTP_FAILURE {endpoint}: {getattr(response, 'status_code', None)}")
        payload = bytes(response.content)
        if self.capture_store is not None:
            self.capture_store.put(f"raw/{capture_name}.json", payload)
        try:
            return response.json()
        except Exception as exc:
            raise AdapterError(f"invalid JSON from {endpoint}") from exc

    def _request_bytes(self, url: str, capture_name: str) -> tuple[bytes, str]:
        if self.capture_store is not None:
            cached_target = self.capture_store.root / "attachments" / capture_name
            if cached_target.exists():
                cached = cached_target.read_bytes()
                if cached:
                    return cached, hashlib.sha256(cached).hexdigest()
        response = self.transport.get(url, {})
        if response is None or response.status_code != 200:
            raise AdapterError(f"HTTP_FAILURE attachment {url}: {getattr(response, 'status_code', None)}")
        payload = bytes(response.content)
        digest = hashlib.sha256(payload).hexdigest()
        if self.capture_store is not None:
            self.capture_store.put(f"attachments/{capture_name}", payload)
        return payload, digest

    def _report_response(self, ticker: str, year: int, period: str) -> Mapping[str, Any]:
        params = {
            "periode": period.lower(),
            "year": str(year),
            "indexFrom": 0,
            "pageSize": self.page_size,
            "reportType": "rdf",
            "kodeEmiten": ticker,
        }
        payload = self._request_json(
            FINANCIAL_REPORT_ENDPOINT,
            params,
            f"financial_report_{ticker}_{year}_{period}",
        )
        if not isinstance(payload, Mapping) or not isinstance(payload.get("Results"), list):
            raise ValueError("invalid financial-report payload")
        total = _as_int(payload.get("ResultCount"), "ResultCount")
        results = payload["Results"]
        if total != len(results) or total > self.page_size:
            raise ValueError(f"incomplete financial-report pagination: {total} vs {len(results)}")
        return payload

    def _announcement_response(
        self,
        ticker: str,
        date_from: str,
        date_to: str,
        *,
        keyword: str = "",
    ) -> Mapping[str, Any]:
        params = {
            "kodeEmiten": ticker,
            "emitenType": "*",
            "indexFrom": 0,
            "pageSize": self.page_size,
            "dateFrom": date_from,
            "dateTo": date_to,
            "lang": "id",
            "keyword": keyword,
        }
        payload = self._request_json(
            ANNOUNCEMENT_ENDPOINT,
            params,
            f"announcement_{ticker}_{date_from}_{date_to}_{hashlib.sha1(keyword.encode()).hexdigest()[:8]}",
        )
        if not isinstance(payload, Mapping) or not isinstance(payload.get("Replies"), list):
            raise ValueError("invalid announcement payload")
        total = _as_int(payload.get("ResultCount"), "ResultCount")
        replies = payload["Replies"]
        ids: list[str] = []
        for reply in replies:
            announcement, _ = _reply_parts(reply)
            ids.append(str(announcement.get("Id2") or announcement.get("NoPengumuman") or ""))
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate announcement rows")
        if total != len(replies) or total > self.page_size:
            raise ValueError(f"incomplete announcement pagination: {total} vs {len(replies)}")
        return payload

    def resolve(
        self,
        ticker: str,
        year: int,
        period: str,
        *,
        statement_scope: str | None = None,
        download_attachments: bool = True,
    ) -> Resolution:
        ticker = ticker.strip().upper()
        period = _period_key(period)
        try:
            report_payload = self._report_response(ticker, year, period)
        except AdapterError:
            return Resolution(ticker, year, period, ResolutionStatus.HTTP_FAILURE)
        except ValueError as exc:
            return Resolution(ticker, year, period, ResolutionStatus.INCOMPLETE_PAGINATION, detail=str(exc))

        rows = [
            row
            for row in report_payload["Results"]
            if str(row.get("KodeEmiten") or ticker).strip().upper() == ticker
            and _period_key(row.get("Report_Period")) == period
            and str(row.get("Report_Year") or "") == str(year)
        ]
        if not rows:
            return Resolution(ticker, year, period, ResolutionStatus.REPORT_NOT_FOUND)
        if len(rows) != 1:
            return Resolution(ticker, year, period, ResolutionStatus.REPORT_AMBIGUOUS, report_found=True)
        return self.resolve_report_row(
            rows[0],
            ticker=ticker,
            year=year,
            period=period,
            statement_scope=statement_scope,
            download_attachments=download_attachments,
        )

    def resolve_report_row(
        self,
        report_row: Mapping[str, Any],
        *,
        ticker: str,
        year: int,
        period: str,
        statement_scope: str | None = None,
        announcement_payload: Mapping[str, Any] | None = None,
        download_attachments: bool = True,
    ) -> Resolution:
        report_attachments = _choose_report_attachments(report_row.get("Attachments") or [])
        if not report_attachments:
            return Resolution(ticker, year, period, ResolutionStatus.ATTACHMENT_NOT_MATCHED, report_found=True)
        modified = str(report_row.get("File_Modified") or report_attachments[0].get("File_Modified") or "")
        try:
            report_date = datetime.fromisoformat(modified.replace("Z", "+00:00"))
            report_date = report_date.astimezone(JAKARTA) if report_date.tzinfo else report_date.replace(tzinfo=JAKARTA)
        except (TypeError, ValueError) as exc:
            return Resolution(ticker, year, period, ResolutionStatus.MALFORMED_TIMESTAMP, report_found=True, detail=str(exc))

        if announcement_payload is None:
            day = report_date.strftime("%Y%m%d")
            try:
                announcement_payload = self._announcement_response(ticker, day, day)
            except AdapterError:
                return Resolution(ticker, year, period, ResolutionStatus.HTTP_FAILURE, report_found=True)
            except ValueError as exc:
                return Resolution(ticker, year, period, ResolutionStatus.INCOMPLETE_PAGINATION, report_found=True, detail=str(exc))

        replies = announcement_payload.get("Replies") or []
        matches: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
        wanted_names = {str(item.get("File_Name") or "").strip().casefold() for item in report_attachments}
        for reply in replies:
            try:
                announcement, attachments = _reply_parts(reply)
            except ValueError as exc:
                return Resolution(ticker, year, period, ResolutionStatus.PAYLOAD_INVALID, report_found=True, detail=str(exc))
            if str(announcement.get("Kode_Emiten") or "").strip().upper() not in {"", ticker}:
                continue
            for attachment in attachments:
                names = {
                    str(attachment.get("OriginalFilename") or "").strip().casefold(),
                    str(attachment.get("PDFFilename") or "").strip().casefold(),
                }
                if wanted_names.intersection(names):
                    matches.append((announcement, attachment))
        distinct_refs = {str(announcement.get("NoPengumuman") or announcement.get("Id2") or "") for announcement, _ in matches}
        if not matches:
            return Resolution(ticker, year, period, ResolutionStatus.ATTACHMENT_NOT_MATCHED, report_found=True, announcement_found=False)
        if len(distinct_refs) != 1:
            return Resolution(ticker, year, period, ResolutionStatus.ATTACHMENT_AMBIGUOUS, report_found=True, announcement_found=True)

        announcement, announcement_attachment = matches[0]
        try:
            publication_utc, publication_tz = parse_idx_publication_timestamp(announcement.get("TglPengumuman"))
        except ValueError as exc:
            return Resolution(ticker, year, period, ResolutionStatus.MALFORMED_TIMESTAMP, report_found=True, announcement_found=True, exact_attachment_join=False, detail=str(exc))

        report_attachment = next(
            item for item in report_attachments
            if str(item.get("File_Name") or "").strip().casefold()
            in {
                str(announcement_attachment.get("OriginalFilename") or "").strip().casefold(),
                str(announcement_attachment.get("PDFFilename") or "").strip().casefold(),
            }
        )
        hashes: list[str] = []
        if download_attachments:
            report_path = str(report_attachment.get("File_Path") or "").strip()
            announcement_path = str(announcement_attachment.get("FullSavePath") or "").strip()
            if not report_path or not announcement_path:
                return Resolution(ticker, year, period, ResolutionStatus.ATTACHMENT_NOT_MATCHED, report_found=True, announcement_found=True, exact_attachment_join=False, detail="missing attachment path")
            # File_Path is rooted at the IDX web origin, not at the /primary
            # API prefix used by JSON endpoints.
            api_origin = self.base_url.split("/primary", 1)[0].rstrip("/")
            report_url = urljoin(api_origin + "/", report_path.lstrip("/"))
            try:
                report_bytes, report_hash = self._request_bytes(report_url, f"report_{ticker}_{year}_{period}_{Path(report_path).name}")
                announcement_bytes, announcement_hash = self._request_bytes(announcement_path, f"announcement_{ticker}_{year}_{period}_{Path(announcement_path).name}")
            except AdapterError as exc:
                return Resolution(ticker, year, period, ResolutionStatus.HTTP_FAILURE, report_found=True, announcement_found=True, exact_attachment_join=False, detail=str(exc))
            hashes = [report_hash, announcement_hash]
            if report_hash != announcement_hash or not report_bytes or not announcement_bytes:
                return Resolution(ticker, year, period, ResolutionStatus.ATTACHMENT_HASH_CONFLICT, report_found=True, announcement_found=True, exact_attachment_join=False, publication_at_utc=publication_utc, publication_timezone=publication_tz, source_sha256=tuple(hashes), detail="report and announcement bytes differ")
            if self.statement_scope_resolver is not None:
                statement_scope = statement_scope or self.statement_scope_resolver(report_bytes, report_row)

        if len(hashes) != 2:
            return Resolution(ticker, year, period, ResolutionStatus.ATTACHMENT_HASH_UNVERIFIED, report_found=True, announcement_found=True, exact_attachment_join=False, publication_at_utc=publication_utc, publication_timezone=publication_tz, source_sha256=tuple(hashes), source_refs=(str(announcement.get("NoPengumuman") or announcement.get("Id2") or ""),), detail="attachment bytes were not verified")
        if not statement_scope:
            return Resolution(ticker, year, period, ResolutionStatus.SCOPE_UNRESOLVED, report_found=True, announcement_found=True, exact_attachment_join=True, publication_at_utc=publication_utc, publication_timezone=publication_tz, source_sha256=tuple(hashes), source_refs=(str(announcement.get("NoPengumuman") or announcement.get("Id2") or ""),))

        try:
            self.revisions.add(ticker=ticker, year=year, period=period, scope=statement_scope, knowledge_at_utc=publication_utc, source_sha256=hashes[0] if hashes else "metadata-only")
        except ValueError as exc:
            return Resolution(ticker, year, period, ResolutionStatus.REVISION_HASH_CONFLICT, report_found=True, announcement_found=True, exact_attachment_join=True, publication_at_utc=publication_utc, publication_timezone=publication_tz, source_sha256=tuple(hashes), detail=str(exc))
        return Resolution(ticker, year, period, ResolutionStatus.PIT_READY, report_found=True, announcement_found=True, exact_attachment_join=True, pit_ready=True, publication_at_utc=publication_utc, publication_timezone=publication_tz, source_sha256=tuple(hashes), source_refs=(str(announcement.get("NoPengumuman") or announcement.get("Id2") or ""),))


def write_json_manifest(path: str | Path, payload: Mapping[str, Any]) -> str:
    """Write a deterministic external manifest and return its SHA-256."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if target.exists() and target.read_bytes() != encoded:
        raise AdapterError(f"manifest overwrite refused: {target}")
    target.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()
