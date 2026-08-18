"""Bounded diagnostic for Smartfren custom post 78437.

This script probes a small, explicit set of issuer-owned WordPress REST variants
for the already-identified Smartfren post ``78437`` (custom post type ``year``).
It does not perform broad crawling and does not change any scientific acceptance
rule. The goal is only to determine whether the post metadata exposes a hidden
PMHMETD attachment or related media locator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import requests

POST_ID = 78437
TIMEOUT = (5, 12)
ENDPOINTS = (
    "https://www.smartfren.com/wp-json/wp/v2/types",
    "https://www.smartfren.com/wp-json/wp/v2/types/year",
    f"https://www.smartfren.com/wp-json/wp/v2/year/{POST_ID}",
    "https://www.smartfren.com/wp/wp-json/wp/v2/types",
    "https://www.smartfren.com/wp/wp-json/wp/v2/types/year",
    f"https://www.smartfren.com/wp/wp-json/wp/v2/year/{POST_ID}",
    f"https://www.smartfren.com/index.php?rest_route=/wp/v2/year/{POST_ID}",
    f"https://www.smartfren.com/wp/index.php?rest_route=/wp/v2/year/{POST_ID}",
    f"https://www.smartfren.com/en/?p={POST_ID}",
)
KEYWORDS = ("pmhmetd", "prospektus", ".pdf", "uploads", "attachment", "download", "media", "file")


def _walk(value: Any, path: str = "$".strip()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            yield from _walk(item, f"{path}[{idx}]")
    elif isinstance(value, str):
        yield path, value


def _relevant_json_strings(value: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for path, text in _walk(value):
        low = text.casefold()
        if any(token in low for token in KEYWORDS):
            out.append({"path": path, "value": text[:2000]})
    return out[:100]


def probe(url: str) -> dict[str, Any]:
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 IDX-Trade-FREN-Post78437-Probe/1.0",
                "Accept": "application/json,text/html;q=0.9,*/*;q=0.5",
            },
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        payload = bytes(response.content or b"")
    except requests.RequestException as exc:
        return {
            "url": url,
            "error": f"{type(exc).__name__}:{exc}",
            "timeout": list(TIMEOUT),
        }

    content_type = response.headers.get("Content-Type", "")
    record: dict[str, Any] = {
        "url": url,
        "final_url": str(response.url),
        "status_code": int(response.status_code),
        "content_type": content_type,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "timeout": list(TIMEOUT),
        "prefix": payload[:240].decode("utf-8", errors="replace"),
    }
    try:
        parsed = response.json()
    except Exception:
        record["json"] = False
        text = payload.decode("utf-8", errors="ignore")
        low = text.casefold()
        record["html_keyword_hits"] = {
            token: low.count(token) for token in KEYWORDS if token in low
        }
    else:
        record["json"] = True
        record["json_type"] = type(parsed).__name__
        record["relevant_json_strings"] = _relevant_json_strings(parsed)
        if isinstance(parsed, dict):
            record["top_level_keys"] = sorted(str(k) for k in parsed.keys())[:100]
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    results = []
    for index, url in enumerate(ENDPOINTS, start=1):
        print(f"[FREN 78437] {index}/{len(ENDPOINTS)} {url}", flush=True)
        result = probe(url)
        results.append(result)
        print(
            json.dumps(
                {
                    "status_code": result.get("status_code"),
                    "content_type": result.get("content_type"),
                    "bytes": result.get("bytes"),
                    "json": result.get("json"),
                    "error": result.get("error"),
                    "relevant_count": len(result.get("relevant_json_strings", [])),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    rendered = json.dumps(
        {"schema_version": "fren_post_78437_probe_v1", "post_id": POST_ID, "results": results},
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
