"""Offline forensic for Smartfren PMHMETD attachment locators.

Reads already-downloaded issuer HTML from a failed FREN archive replay. No
network calls are made. The goal is to expose attachment/file locator strings
that generic discovery may have missed (escaped JSON, data-* attributes,
iframes, object/embed tags, relative upload paths, etc.).
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse

BASE = "https://www.smartfren.com/en/connect-with-us/whats-new/year/prospektus-pmhmetd-v-pt-smartfren-telecom-tbk/"
KEYWORDS = ("pmhmetd", "prospektus", "pdf", "attachment", "download", "file", "uploads", "iframe", "embed", "object")


def decode_text(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="ignore")
    text = html.unescape(text)
    text = text.replace("\\/", "/")
    text = re.sub(r"\\u002[fF]", "/", text)
    text = re.sub(r"\\u003[aA]", ":", text)
    return text


def looks_relevant(value: str) -> bool:
    low = value.casefold()
    return any(k in low for k in KEYWORDS)


def same_domain_locator(value: str, base: str = BASE) -> str | None:
    raw = value.strip().strip('"\'')
    if not raw or any(ch.isspace() for ch in raw):
        return None
    if not (raw.startswith(("http://", "https://", "//", "/", "./", "../")) or "/" in raw or re.search(r"\.[a-z0-9]{2,8}(?:[?#].*)?$", raw, re.I)):
        return None
    url = urljoin(base, raw)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc.lower().endswith("smartfren.com"):
        return None
    return url


def inspect(payload: bytes) -> dict[str, object]:
    text = decode_text(payload)
    quoted: set[str] = set()
    locators: set[str] = set()
    tag_fragments: set[str] = set()

    for m in re.finditer(r'''["']([^"']{1,1200})["']''', text):
        value = m.group(1)
        if looks_relevant(value):
            quoted.add(value)
            locator = same_domain_locator(value)
            if locator:
                locators.add(locator)

    for m in re.finditer(r"https?://[^\s\"'<>]+", text, re.I):
        value = m.group(0)
        if looks_relevant(value):
            locator = same_domain_locator(value)
            if locator:
                locators.add(locator)

    for m in re.finditer(r"<(?:iframe|object|embed|a)\b[^>]{0,2000}>", text, re.I):
        fragment = " ".join(m.group(0).split())
        if looks_relevant(fragment):
            tag_fragments.add(fragment)

    contexts: list[str] = []
    low = text.casefold()
    for needle in ("pmhmetd", "prospektus"):
        start = 0
        while len(contexts) < 30:
            idx = low.find(needle, start)
            if idx < 0:
                break
            contexts.append(" ".join(text[max(0, idx - 350): idx + 700].split()))
            start = idx + len(needle)

    return {
        "bytes": len(payload),
        "same_domain_locators": sorted(locators),
        "relevant_quoted_values": sorted(quoted),
        "relevant_tag_fragments": sorted(tag_fragments),
        "keyword_contexts": contexts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.html.is_file():
        raise RuntimeError(f"FREN_SAVED_HTML_MISSING:{args.html}")
    result = inspect(args.html.read_bytes())
    rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
