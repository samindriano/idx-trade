from __future__ import annotations

import json
from pathlib import Path

from idx_trade.v4_3_ca_schedule59_ksei_news import (
    build_event_queries,
    encode_search_url,
    is_ksei_attachment_url,
    is_ksei_news_url,
    parse_news_page,
    parse_search_page,
)


def _contract() -> dict:
    return json.loads(
        Path("config/v4_3_ca_training_domain_schedule_59_ksei_news_v1.json").read_text(
            encoding="utf-8"
        )
    )["query_contract"]


def test_query_family_is_deterministic_and_source_specific() -> None:
    queries = build_event_queries(
        ticker="PBID",
        source_type="Stock Split",
        source_dates=("2024-06-04",),
        contract=_contract(),
    )
    assert queries == tuple(sorted(queries, key=lambda value: (value.casefold(), value)))
    assert "PBID" in queries
    assert "PBID 2024" in queries
    assert "PBID stock split" in queries
    assert "PBID pemecahan saham" in queries
    assert all(query.startswith("PBID") for query in queries)


def test_voluntary_query_family_is_cash_tender_specific() -> None:
    queries = build_event_queries(
        ticker="EDGE",
        source_type="Voluntary Conversion",
        source_dates=("2025-01-02", "2025-01-10"),
        contract=_contract(),
    )
    assert "EDGE penawaran tender" in queries
    assert "EDGE pembelian kembali" in queries
    assert "EDGE 2025" in queries


def test_search_url_uses_only_ksei_internal_search() -> None:
    url = encode_search_url("https://web.ksei.co.id", "PBID stock split")
    assert url == "https://web.ksei.co.id/search/results/PBID%20stock%20split"
    assert "google" not in url.casefold()
    assert "bing" not in url.casefold()


def test_search_page_extracts_only_news_and_next_link() -> None:
    payload = b"""
    <html><body>
      <div class='result'>
        <a href='/ksei_news/read/17025/Reminder-CA-PBID'>Reminder CA PBID</a>
        <p>PBID Stock Split detail</p>
      </div>
      <div><a href='/services/registered-securities/shares/lc/PBID'>PBID security</a></div>
      <div><a href='https://evil.example/ksei_news/read/1/x'>external</a></div>
      <div class='pagination'>
        <a href='/search/results/PBID/page:2'>Next</a>
      </div>
    </body></html>
    """
    results, next_url = parse_search_page(payload, base_url="https://web.ksei.co.id")
    assert len(results) == 1
    assert results[0].url == "https://web.ksei.co.id/ksei_news/read/17025/Reminder-CA-PBID"
    assert "PBID" in results[0].snippet
    assert next_url == "https://web.ksei.co.id/search/results/PBID/page:2"


def test_search_page_without_next_is_terminal() -> None:
    payload = b"<html><body><a href='/ksei_news/read/1/X'>X</a></body></html>"
    results, next_url = parse_search_page(payload, base_url="https://web.ksei.co.id")
    assert len(results) == 1
    assert next_url is None


def test_news_page_extracts_only_official_attachments() -> None:
    payload = b"""
    <html><body>
      <h1>Jadwal Stock Split PBID</h1>
      <p>PBID mulai perdagangan saham dengan nilai nominal baru.</p>
      <a href='/Content/Upload/schedule.pdf'>Lampiran</a>
      <a href='https://www.ksei.co.id/files/other.pdf'>Lampiran 2</a>
      <a href='https://evil.example/file.pdf'>External</a>
      <a href='/about'>About</a>
    </body></html>
    """
    title, body, attachments = parse_news_page(
        payload,
        page_url="https://web.ksei.co.id/ksei_news/read/1/test",
    )
    assert title == "Jadwal Stock Split PBID"
    assert "nilai nominal baru" in body
    assert attachments == (
        "https://web.ksei.co.id/Content/Upload/schedule.pdf",
        "https://www.ksei.co.id/files/other.pdf",
    )
    assert all(is_ksei_attachment_url(url) for url in attachments)


def test_allowed_news_url_is_exact_ksei_host_and_path() -> None:
    assert is_ksei_news_url("https://web.ksei.co.id/ksei_news/read/123/x")
    assert is_ksei_news_url("https://www.ksei.co.id/ksei_news/read/123/x")
    assert not is_ksei_news_url("https://evil.example/ksei_news/read/123/x")
    assert not is_ksei_news_url("https://web.ksei.co.id/ksei_news/browse")
