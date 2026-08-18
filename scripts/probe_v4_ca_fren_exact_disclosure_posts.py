from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import requests


POSTS = (
    {
        "post_id": 78197,
        "title": "Perubahan Jadwal PMHMETD V",
        "permalink": "https://www.smartfren.com/connect-with-us/whats-new/year/perubahan-jadwal-pmhmetd-v/",
    },
    {
        "post_id": 78122,
        "title": "Informasi Tambahan PMHMETD V FREN",
        "permalink": "https://www.smartfren.com/connect-with-us/whats-new/year/informasi-tambahan-pmhmetd-v-fren/",
    },
    {
        "post_id": 74393,
        "title": "Prospektus Ringkas PMHMETD V FREN",
        "permalink": "https://www.smartfren.com/connect-with-us/whats-new/year/prospektus-ringkas-pmhmetd-v-fren/",
    },
)

MARKERS = (
    "PMHMETD V",
    "17 April 2024",
    "18 April 2024",
    "19 April 2024",
    "Ex Right",
    "Ex-Right",
    "Pasar Reguler",
    "Pasar Negosiasi",
    "Regular Market",
    "Negotiated Market",
    "178",
    "75",
)

_ALLOWED_HOSTS = {"smartfren.com", "www.smartfren.com", "ucms-api.smartfren.com"}
_RELEVANT_URL_TOKENS = (".pdf", "/uploads/", "pmhmetd", "prospektus", "hmetd", "jadwal", "right")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _visible_text(payload: bytes) -> str:
    raw = payload.decode("utf-8", errors="ignore")
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(html.unescape(raw).split())


def _marker_contexts(text: str, width: int = 420) -> list[dict[str, str]]:
    low = text.casefold()
    output: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for marker in MARKERS:
        start = 0
        needle = marker.casefold()
        while True:
            idx = low.find(needle, start)
            if idx < 0:
                break
            context = text[max(0, idx - width): idx + len(marker) + width]
            key = (marker, context)
            if key not in seen:
                output.append({"marker": marker, "context": context})
                seen.add(key)
            start = idx + len(needle)
            if sum(1 for row in output if row["marker"] == marker) >= 4:
                break
    return output


def _candidate_strings(payload: bytes) -> set[str]:
    raw = payload.decode("utf-8", errors="ignore")
    decoded = html.unescape(raw).replace("\\/", "/")
    values: set[str] = set()
    patterns = (
        r'''(?:href|src|data-src|data-url|data-href|data-file|data-download)\s*=\s*["']([^"']+)["']''',
        r'''https?://[^\s"'<>]+''',
        r'''["']([^"']*(?:\.pdf|/uploads/|pmhmetd|prospektus|hmetd|jadwal)[^"']*)["']''',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, decoded, flags=re.I):
            value = match.group(1) if match.lastindex else match.group(0)
            values.add(unquote(value.strip()))
    return values


def extract_relevant_locators(payload: bytes, base_url: str) -> tuple[str, ...]:
    output: set[str] = set()
    for candidate in _candidate_strings(payload):
        candidate = candidate.strip().strip("\\\"")
        if not candidate or candidate.startswith(("javascript:", "mailto:", "#")):
            continue
        low = candidate.casefold()
        if not any(token in low for token in _RELEVANT_URL_TOKENS):
            continue
        url = urljoin(base_url, candidate)
        parsed = urlparse(url)
        host = parsed.netloc.casefold()
        if parsed.scheme not in {"http", "https"} or host not in _ALLOWED_HOSTS:
            continue
        output.add(url)
    return tuple(sorted(output))


def _fetch(session: requests.Session, url: str) -> tuple[bytes, dict[str, Any]]:
    try:
        response = session.get(url, timeout=(5, 12), allow_redirects=True)
    except requests.RequestException as exc:
        return b"", {"url": url, "error": f"{type(exc).__name__}:{exc}"}
    payload = response.content
    return payload, {
        "url": url,
        "final_url": response.url,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "bytes": len(payload),
        "sha256": _sha256(payload),
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "idx-trade-fren-exact-disclosure-probe/1.0"})

    results: list[dict[str, Any]] = []
    for post in POSTS:
        endpoints = (
            ("permalink", post["permalink"]),
            ("shortlink", f"https://www.smartfren.com/?p={post['post_id']}"),
        )
        post_result: dict[str, Any] = {
            "post_id": post["post_id"],
            "title": post["title"],
            "requests": [],
        }
        for kind, url in endpoints:
            print(f"[FREN exact disclosure] {post['post_id']} {kind}: {url}", flush=True)
            payload, record = _fetch(session, url)
            if payload:
                path = args.raw_dir / f"{post['post_id']}_{kind}.bin"
                path.write_bytes(payload)
                text = _visible_text(payload)
                record["markers"] = {marker: marker.casefold() in text.casefold() for marker in MARKERS}
                record["marker_contexts"] = _marker_contexts(text)
                record["relevant_locators"] = extract_relevant_locators(payload, record.get("final_url", url))
                record["raw_path"] = str(path)
            post_result["requests"].append(record)
        results.append(post_result)

    summary = {
        "schema_version": "fren_exact_disclosure_probe_v1",
        "bounded_request_count": len(POSTS) * 2,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
