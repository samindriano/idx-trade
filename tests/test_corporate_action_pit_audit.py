from __future__ import annotations

import json
from pathlib import Path

import pytest

from idx_trade.corporate_action_pit_audit import (
    IDX_ISSUED_HISTORY,
    AuditError,
    CaptureStore,
    fetch_idx_issued_history,
    match_announcement_candidates,
    parse_ksei_security_page,
)


class FakeResponse:
    def __init__(self, payload, *, status_code: int = 200, url: str = "https://example.test"):
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self.url = url
        self._payload = payload
        self.content = json.dumps(payload).encode()

    def json(self):
        return self._payload


class QueueTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, **kwargs):
        self.calls.append((url, dict(params or {})))
        return self.responses.pop(0)


def test_idx_issued_history_requires_all_declared_pages(tmp_path: Path):
    transport = QueueTransport(
        [
            FakeResponse({"recordsTotal": 3, "recordsFiltered": 3, "data": [{"id": 1}, {"id": 2}]}),
            FakeResponse({"recordsTotal": 3, "recordsFiltered": 3, "data": [{"id": 3}]}),
        ]
    )
    rows, pages = fetch_idx_issued_history(
        transport,
        CaptureStore(tmp_path),
        ca_type="stockSplit",
        date_from="20180101",
        date_to="20260814",
        page_size=2,
    )
    assert [row["id"] for row in rows] == [1, 2, 3]
    assert [page["returned"] for page in pages] == [2, 1]
    assert [call[1]["start"] for call in transport.calls] == [0, 2]


def test_idx_issued_history_fails_closed_on_empty_partial_page(tmp_path: Path):
    transport = QueueTransport(
        [FakeResponse({"recordsTotal": 3, "recordsFiltered": 3, "data": [{"id": 1}, {"id": 2}]}), FakeResponse({"recordsTotal": 3, "recordsFiltered": 3, "data": []})]
    )
    with pytest.raises(AuditError, match="empty page"):
        fetch_idx_issued_history(
            transport,
            CaptureStore(tmp_path),
            ca_type="stockSplit",
            date_from="20180101",
            date_to="20260814",
            page_size=2,
        )


def test_ksei_visible_security_table_preserves_source_dates_and_ratio():
    payload = b"""
    <html><body><table><thead><tr>
      <th>Type of CA</th><th>Ratio</th><th>Cum Date</th>
      <th>Record Date</th><th>Distribution Date</th><th>Status</th>
    </tr></thead><tbody><tr>
      <td>Cash Dividend</td><td>(1 IDPR : 5 IDR)</td>
      <td><span class='hidden'>20260629</span>29 Jun 2026</td>
      <td><span class='hidden'>20260701</span>01 Jul 2026</td>
      <td><span class='hidden'>20260717</span>17 Jul 2026</td><td>Active</td>
    </tr></tbody></table></body></html>
    """
    rows = parse_ksei_security_page(payload, ticker="IDPR", source_url="u", source_sha256="h")
    assert rows == [
        {
            "ticker": "IDPR",
            "event_family_source": "Cash Dividend",
            "cum_date": "2026-06-29",
            "record_date": "2026-07-01",
            "distribution_date": "2026-07-17",
            "status": "Active",
            "source_url": "u",
            "source_sha256": "h",
            "ratio_raw": "(1 IDPR : 5 IDR)",
            "ratio_left_value": "1",
            "ratio_left_security": "IDPR",
            "ratio_right_value": "5",
            "ratio_right_security": "IDR",
            "ratio_parse_status": "PARSED_SOURCE_TEXT_ONLY",
        }
    ]


def test_ksei_parser_rejects_missing_or_ambiguous_table():
    with pytest.raises(AuditError, match="expected one visible"):
        parse_ksei_security_page(b"<html><table><tr><td>Cash Dividend</td></tr></table></html>", ticker="X", source_url="u", source_sha256="h")


def test_announcement_join_requires_event_family_text_and_keeps_publication_time():
    replies = [
        {
            "pengumuman": {
                "Kode_Emiten": "IDPR",
                "TglPengumuman": "2026-06-20T10:00:00",
                "NoPengumuman": "1/IDPR/VI/2026",
                "JudulPengumuman": "Keterbukaan Informasi Dividen Tunai",
                "PerihalPengumuman": "Dividen Tunai",
            },
            "attachments": [{"FullSavePath": "https://idx.test/div.pdf", "OriginalFilename": "div.pdf", "IsAttachment": False}],
        },
        {
            "pengumuman": {
                "Kode_Emiten": "IDPR",
                "TglPengumuman": "2026-06-20T10:00:00",
                "NoPengumuman": "2/IDPR/VI/2026",
                "JudulPengumuman": "RUPS",
                "PerihalPengumuman": "RUPS",
            },
            "attachments": [],
        },
    ]
    matches = match_announcement_candidates(
        replies,
        ticker="IDPR",
        event_family="CASH_DIVIDEND",
        action_date="2026-06-29",
    )
    assert len(matches) == 1
    assert matches[0]["announcement_ref"] == "1/IDPR/VI/2026"
    assert matches[0]["published_at_utc"] == "2026-06-20T03:00:00Z"
    assert matches[0]["attachment_url"] == "https://idx.test/div.pdf"
