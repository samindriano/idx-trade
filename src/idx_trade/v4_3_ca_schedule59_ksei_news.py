"""Deterministic helpers for secondary official-KSEI schedule discovery.

The helpers in this module do not perform network calls and do not admit event
semantics. They freeze query derivation and parse only KSEI's own site-search
and KSEI News navigation surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable
from urllib.parse import quote, urljoin, urlparse

from lxml import html


KSEI_HOSTS = {"web.ksei.co.id", "www.ksei.co.id", "ksei.co.id"}
NEWS_PATH_PREFIX = "/ksei_news/read/"
SEARCH_PATH_PREFIX = "/search/results/"
ATTACHMENT_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx")
ATTACHMENT_PATH_TOKENS = ("/content/upload/", "/upload/", "/uploads/", "/files/")


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    snippet: str


def clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def normalize_ticker(value: Any) -> str:
    return clean(value).upper().replace(".JK", "")


def exact_ticker_token(text: str, ticker: str) -> bool:
    ticker = normalize_ticker(ticker)
    if not ticker:
        return False
    return bool(
        re.search(
            rf"(?<![A-Z0-9]){re.escape(ticker)}(?![A-Z0-9])",
            str(text or "").upper(),
        )
    )


def parse_pipe_dates(value: Any) -> tuple[str, ...]:
    parts = [clean(part) for part in str(value or "").split("|") if clean(part)]
    result: list[str] = []
    for part in parts:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", part):
            raise RuntimeError(f"SOURCE_DATE_FORMAT_INVALID:{part}")
        result.append(part)
    if not result:
        raise RuntimeError("SOURCE_DATES_EMPTY")
    return tuple(sorted(set(result)))


def _terms_for_source_type(source_type: str, contract: dict[str, Any]) -> tuple[str, ...]:
    source = clean(source_type).casefold()
    if source == "stock split":
        return tuple(contract["stock_split_terms"])
    if source in {"reverse stock", "reverse stock split", "reverse split"}:
        return tuple(contract["reverse_stock_terms"])
    if source == "merger":
        return tuple(contract["merger_terms"])
    if source == "mandatory conversion":
        return tuple(contract["mandatory_conversion_terms"])
    if source in {"capital restructuring", "capital reduction"}:
        return tuple(contract["capital_restructuring_terms"])
    if source == "voluntary conversion":
        return tuple(contract["voluntary_conversion_terms"])
    return tuple(contract["unknown_mechanical_terms"])


def build_event_queries(
    *,
    ticker: str,
    source_type: str,
    source_dates: Iterable[str],
    contract: dict[str, Any],
) -> tuple[str, ...]:
    """Build the complete preregistered KSEI search query family for an event."""

    code = normalize_ticker(ticker)
    if not code:
        raise RuntimeError("QUERY_TICKER_EMPTY")
    dates = tuple(source_dates)
    if not dates:
        raise RuntimeError("QUERY_SOURCE_DATES_EMPTY")
    queries: set[str] = set()
    if contract.get("always_query_exact_ticker") is True:
        queries.add(code)
    if contract.get("always_query_exact_ticker_plus_each_source_year") is True:
        for value in dates:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise RuntimeError(f"QUERY_SOURCE_DATE_FORMAT_INVALID:{value}")
            queries.add(f"{code} {value[:4]}")
    for term in _terms_for_source_type(source_type, contract):
        term = clean(term)
        if term:
            queries.add(f"{code} {term}")
    if not queries:
        raise RuntimeError("QUERY_FAMILY_EMPTY")
    return tuple(sorted(queries, key=lambda value: (value.casefold(), value)))


def encode_search_url(base_url: str, query: str) -> str:
    return f"{base_url.rstrip('/')}{SEARCH_PATH_PREFIX}{quote(clean(query), safe='')}"


def _official_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.hostname in KSEI_HOSTS


def is_ksei_news_url(url: str) -> bool:
    if not _official_url(url):
        return False
    return urlparse(url).path.casefold().startswith(NEWS_PATH_PREFIX)


def is_ksei_search_url(url: str) -> bool:
    if not _official_url(url):
        return False
    return urlparse(url).path.casefold().startswith(SEARCH_PATH_PREFIX)


def is_ksei_attachment_url(url: str) -> bool:
    if not _official_url(url):
        return False
    path = urlparse(url).path.casefold()
    if path.endswith(ATTACHMENT_EXTENSIONS):
        return True
    return any(token in path for token in ATTACHMENT_PATH_TOKENS)


def _parent_snippet(anchor: Any) -> str:
    node = anchor
    for _ in range(3):
        parent = node.getparent()
        if parent is None:
            break
        node = parent
        text = clean(node.text_content())
        if len(text) >= 30:
            return text[:1500]
    return clean(anchor.text_content())


def parse_search_page(payload: bytes, *, base_url: str) -> tuple[list[SearchResult], str | None]:
    try:
        document = html.fromstring(payload)
    except Exception as exc:
        raise RuntimeError("KSEI_SEARCH_PAGE_INVALID_HTML") from exc

    results: dict[str, SearchResult] = {}
    next_urls: set[str] = set()
    for anchor in document.xpath("//a[@href]"):
        href = clean(anchor.get("href"))
        if not href:
            continue
        url = urljoin(base_url.rstrip("/") + "/", href)
        text = clean(anchor.text_content())
        if is_ksei_news_url(url):
            title = text or clean(anchor.get("title"))
            results[url] = SearchResult(
                url=url,
                title=title,
                snippet=_parent_snippet(anchor),
            )
        if is_ksei_search_url(url):
            folded = text.casefold().replace("\u00a0", " ").strip()
            if folded in {"next", "berikutnya", ">", "›", "»"}:
                next_urls.add(url)

    if len(next_urls) > 1:
        raise RuntimeError(f"KSEI_SEARCH_MULTIPLE_NEXT_LINKS:{sorted(next_urls)}")
    next_url = next(iter(next_urls)) if next_urls else None
    return sorted(results.values(), key=lambda item: item.url), next_url


def parse_news_page(payload: bytes, *, page_url: str) -> tuple[str, str, tuple[str, ...]]:
    try:
        document = html.fromstring(payload)
    except Exception as exc:
        raise RuntimeError("KSEI_NEWS_PAGE_INVALID_HTML") from exc
    title_nodes = document.xpath("//h1")
    title = clean(title_nodes[0].text_content()) if title_nodes else ""
    body = clean(document.text_content())
    attachments: set[str] = set()
    for anchor in document.xpath("//a[@href]"):
        href = clean(anchor.get("href"))
        if not href:
            continue
        url = urljoin(page_url, href)
        if is_ksei_attachment_url(url):
            attachments.add(url)
    return title, body, tuple(sorted(attachments))


def request_identity(records: Iterable[dict[str, Any]]) -> str:
    import hashlib

    rows = sorted(
        {
            f"{clean(row.get('request_kind'))}|{clean(row.get('request_key'))}|"
            f"{clean(row.get('requested_url'))}|{clean(row.get('sha256'))}|{clean(row.get('path'))}"
            for row in records
            if int(row.get("status_code") or 0) == 200 and clean(row.get("sha256"))
        }
    )
    payload = "\n".join(rows) + ("\n" if rows else "")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
