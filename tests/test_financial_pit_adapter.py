from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import pytest

from idx_trade.financial_pit_adapter import (
    DirectIdxFinancialPITAdapter,
    ResolutionStatus,
    parse_idx_publication_timestamp,
)


@dataclass
class FakeResponse:
    status_code: int
    content: bytes

    @property
    def headers(self):
        return {"content-type": "application/json"}

    def json(self):
        return json.loads(self.content)


class FakeTransport:
    def __init__(self, report_payload, announcement_payload, report_bytes=b"same"):
        self.report_payload = report_payload
        self.announcement_payload = announcement_payload
        self.report_bytes = report_bytes
        self.calls = []
        self.announcement_bytes = report_bytes

    def get(self, endpoint, params):
        self.calls.append((endpoint, dict(params)))
        if endpoint.endswith("GetFinancialReport"):
            payload = self.report_payload
            return FakeResponse(200, json.dumps(payload).encode())
        if endpoint.endswith("GetAnnouncement"):
            payload = self.announcement_payload
            return FakeResponse(200, json.dumps(payload).encode())
        if "report-file" in endpoint:
            return FakeResponse(200, self.report_bytes)
        if "announcement-file" in endpoint:
            return FakeResponse(200, self.announcement_bytes)
        raise AssertionError(endpoint)


def _payloads():
    report = {
        "ResultCount": 1,
        "Results": [{
            "KodeEmiten": "BBCA",
            "File_Modified": "2025-01-23T17:30:34.603",
            "Report_Period": "Audit",
            "Report_Year": "2024",
            "Attachments": [{
                "File_Name": "FinancialStatement-2024-BBCA.xlsx",
                "File_Path": "/report-file.xlsx",
                "File_Type": ".xlsx",
            }],
        }],
    }
    announcement = {
        "ResultCount": 1,
        "Replies": [{
            "pengumuman": {
                "Id2": "20250123173034-003/ACT/2025_id-id",
                "NoPengumuman": "003/ACT/2025",
                "Kode_Emiten": "BBCA       ",
                "TglPengumuman": "2025-01-23T17:30:34",
                "CreatedDate": "2026-02-20T14:31:04",
            },
            "attachments": [{
                "OriginalFilename": "FinancialStatement-2024-BBCA.xlsx",
                "PDFFilename": "FinancialStatement-2024-BBCA.xlsx",
                "FullSavePath": "https://www.idx.co.id/announcement-file.xlsx",
            }],
        }],
    }
    return report, announcement


def test_idx_naive_publication_time_is_interpreted_as_jakarta_then_utc():
    value, timezone = parse_idx_publication_timestamp("2025-01-23T17:30:34")
    assert value == "2025-01-23T10:30:34Z"
    assert timezone == "Asia/Jakarta"


def test_adapter_requires_complete_result_count_pagination():
    report, announcement = _payloads()
    report["ResultCount"] = 2
    transport = FakeTransport(report, announcement)
    result = DirectIdxFinancialPITAdapter(transport).resolve("BBCA", 2024, "audit")
    assert result.status is ResolutionStatus.INCOMPLETE_PAGINATION
    assert not result.pit_ready


def test_adapter_exact_hash_join_never_uses_created_date_and_requires_scope():
    report, announcement = _payloads()
    transport = FakeTransport(report, announcement)
    result = DirectIdxFinancialPITAdapter(transport).resolve("BBCA", 2024, "audit")
    assert result.status is ResolutionStatus.SCOPE_UNRESOLVED
    assert result.exact_attachment_join
    assert result.publication_at_utc == "2025-01-23T10:30:34Z"
    assert result.source_sha256 == (
        hashlib.sha256(b"same").hexdigest(),
        hashlib.sha256(b"same").hexdigest(),
    )


def test_adapter_can_be_pit_ready_only_with_explicit_scope():
    report, announcement = _payloads()
    transport = FakeTransport(report, announcement)
    result = DirectIdxFinancialPITAdapter(transport).resolve(
        "BBCA", 2024, "audit", statement_scope="CONSOLIDATED"
    )
    assert result.status is ResolutionStatus.PIT_READY
    assert result.pit_ready


def test_adapter_fails_closed_when_hashes_disagree():
    report, announcement = _payloads()
    transport = FakeTransport(report, announcement, report_bytes=b"report")
    transport.announcement_bytes = b"different"
    result = DirectIdxFinancialPITAdapter(transport).resolve(
        "BBCA", 2024, "audit", statement_scope="CONSOLIDATED"
    )
    assert result.status is ResolutionStatus.ATTACHMENT_HASH_CONFLICT
    assert not result.exact_attachment_join
    assert not result.pit_ready


def test_adapter_rejects_unverified_metadata_only_attachment_join():
    report, announcement = _payloads()
    transport = FakeTransport(report, announcement)
    result = DirectIdxFinancialPITAdapter(transport).resolve(
        "BBCA", 2024, "audit", statement_scope="CONSOLIDATED", download_attachments=False
    )
    assert result.status is ResolutionStatus.ATTACHMENT_HASH_UNVERIFIED
    assert not result.pit_ready


def test_adapter_rejects_malformed_publication_timestamp():
    report, announcement = _payloads()
    announcement["Replies"][0]["pengumuman"]["TglPengumuman"] = "2025-01-23"
    transport = FakeTransport(report, announcement)
    result = DirectIdxFinancialPITAdapter(transport).resolve(
        "BBCA", 2024, "audit", statement_scope="CONSOLIDATED"
    )
    assert result.status is ResolutionStatus.MALFORMED_TIMESTAMP


def test_revision_ledger_rejects_same_logical_filing_with_conflicting_bytes():
    report, announcement = _payloads()
    first_transport = FakeTransport(report, announcement, report_bytes=b"first")
    first_transport.announcement_bytes = b"first"
    adapter = DirectIdxFinancialPITAdapter(first_transport)
    assert adapter.resolve("BBCA", 2024, "audit", statement_scope="CONSOLIDATED").pit_ready

    second_transport = FakeTransport(report, announcement, report_bytes=b"second")
    second_transport.announcement_bytes = b"second"
    adapter.transport = second_transport
    result = adapter.resolve("BBCA", 2024, "audit", statement_scope="CONSOLIDATED")
    assert result.status is ResolutionStatus.REVISION_HASH_CONFLICT


def test_adapter_rejects_duplicate_announcement_ids():
    report, announcement = _payloads()
    announcement["Replies"].append(announcement["Replies"][0])
    announcement["ResultCount"] = 2
    transport = FakeTransport(report, announcement)
    result = DirectIdxFinancialPITAdapter(transport).resolve("BBCA", 2024, "audit")
    assert result.status is ResolutionStatus.INCOMPLETE_PAGINATION

