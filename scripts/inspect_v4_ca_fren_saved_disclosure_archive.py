"""Offline forensic for Smartfren 2024 disclosure archive PMHMETD items.

Reads the already-downloaded issuer disclosure archive HTML. No network calls.
The goal is to recover exact post ids, href-like locators, and surrounding HTML
for the three PMHMETD-V disclosure entries that the rendered archive still lists.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re

TITLES = (
    "Perubahan Jadwal PMHMETD V",
    "Informasi Tambahan PMHMETD V FREN",
    "Prospektus Ringkas PMHMETD V FREN",
)


def decode(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="ignore")
    text = html.unescape(text).replace("\\/", "/")
    return text


def inspect(payload: bytes) -> dict[str, object]:
    text = decode(payload)
    rows: list[dict[str, object]] = []
    for title in TITLES:
        matches = list(re.finditer(re.escape(title), text, flags=re.I))
        title_rows: list[dict[str, object]] = []
        for m in matches[:10]:
            lo = max(0, m.start() - 1800)
            hi = min(len(text), m.end() + 1800)
            frag = text[lo:hi]
            post_ids = sorted(set(re.findall(r"post-(\d+)", frag, flags=re.I)))
            hrefs = sorted(set(html.unescape(x) for x in re.findall(r'''href\s*=\s*["']([^"']+)["']''', frag, flags=re.I)))
            shortlinks = sorted(set(re.findall(r"https://www\.smartfren\.com/(?:en/)?\?p=\d+", frag, flags=re.I)))
            title_rows.append(
                {
                    "post_ids": post_ids,
                    "hrefs": hrefs,
                    "shortlinks": shortlinks,
                    "context": " ".join(frag.split()),
                }
            )
        rows.append({"title": title, "occurrences": len(matches), "matches": title_rows})

    all_post_ids = sorted(set(re.findall(r"post-(\d+)", text, flags=re.I)))
    all_shortlinks = sorted(set(re.findall(r"https://www\.smartfren\.com/(?:en/)?\?p=\d+", text, flags=re.I)))
    return {
        "bytes": len(payload),
        "items": rows,
        "all_post_ids": all_post_ids,
        "all_shortlinks": all_shortlinks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.html.is_file():
        raise RuntimeError(f"FREN_DISCLOSURE_ARCHIVE_HTML_MISSING:{args.html}")
    result = inspect(args.html.read_bytes())
    rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
