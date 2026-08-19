"""Offline adjudication helpers for frozen schedule-59 KSEI News evidence.

No provider calls occur here.  The only admissive semantics are the already
frozen residual-document rules: exact voluntary cash identity -> NON_BLOCKING,
or exact regular-market Ex / first-new-basis transition with exact ticker,
compatible family, source-date linkage, and official-session validation.

HTML is converted to conservative semantic lines.  Dates are admissible only
when they are bound to an explicit paragraph/list/heading/table row; a flattened
page body is never used as layout evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from lxml import html
from typing import Iterable

from idx_trade.v4_ca_schedule_semantics import clean


BLOCK_XPATH = "//h1|//h2|//h3|//h4|//h5|//h6|//p|//li|//tr"


@dataclass(frozen=True)
class NewsDocumentText:
    title: str
    plain_text: str
    layout_text: str


def _direct_block_line(node: object) -> str:
    # Table rows retain column order while paragraphs/list items/headings retain
    # their rendered text.  Nested blocks are intentionally not synthesized.
    try:
        tag = str(getattr(node, "tag", "")).casefold()
        if tag == "tr":
            cells = node.xpath("./th|./td")
            value = " | ".join(clean(cell.text_content()) for cell in cells if clean(cell.text_content()))
            return clean(value)
        return clean(node.text_content())
    except Exception:
        return ""


def parse_news_document(payload: bytes) -> NewsDocumentText:
    try:
        document = html.fromstring(payload)
    except Exception as exc:
        raise RuntimeError("KSEI_NEWS_ADJUDICATION_INVALID_HTML") from exc

    title_nodes = document.xpath("//h1")
    title = clean(title_nodes[0].text_content()) if title_nodes else ""
    body_nodes = document.xpath("//body//text()")
    plain_text = "\n".join(clean(value) for value in body_nodes if clean(value))

    lines: list[str] = []
    seen: set[str] = set()
    for node in document.xpath(BLOCK_XPATH):
        value = _direct_block_line(node)
        if not value or value in seen:
            continue
        seen.add(value)
        lines.append(value)
    layout_text = "\n".join(lines)
    return NewsDocumentText(title=title, plain_text=plain_text, layout_text=layout_text)


def successful_request_urls(rows: Iterable[dict[str, object]], *, request_kind: str) -> set[str]:
    result: set[str] = set()
    for row in rows:
        if clean(row.get("request_kind")) != request_kind:
            continue
        if int(row.get("status_code") or 0) != 200 or int(row.get("bytes") or 0) <= 0:
            continue
        for key in ("requested_url", "final_url"):
            value = clean(row.get(key))
            if value:
                result.add(value)
    return result
