"""Offline inspect an already-downloaded Smartfren 2024 annual report for PMHMETD-V schedule evidence.

No network calls. The script recursively scans a prior FREN replay root for the
known issuer-official 2024 Annual Report SHA, extracts text with pypdf, and
prints only narrowly relevant page/context evidence around PMHMETD/right issue
and 17 April 2024. It does not certify the event by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable

from pypdf import PdfReader

TARGET_SHA256 = "980b8bd046a828f48fe4bb645a1b687acc9f183ad6da8c3a75c49d5e80386887"
KEYWORDS = (
    "pmhmetd",
    "right issue",
    "hak memesan efek terlebih dahulu",
    "17 april 2024",
    "17 april",
    "ex-right",
    "ex right",
    "cum-right",
    "cum right",
    "pasar reguler",
    "regular market",
    "pasar negosiasi",
    "negotiated market",
    "178",
    "75",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(text: str) -> str:
    return " ".join(text.replace("\u00a0", " ").replace("\u00ad", " ").split())


def relevant(text: str) -> bool:
    low = text.casefold()
    return any(token in low for token in KEYWORDS)


def contexts(text: str, needles: Iterable[str], radius: int = 700) -> list[dict[str, str]]:
    norm = normalize(text)
    low = norm.casefold()
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for needle in needles:
        start = 0
        nlow = needle.casefold()
        while True:
            idx = low.find(nlow, start)
            if idx < 0:
                break
            excerpt = norm[max(0, idx - radius): idx + len(needle) + radius]
            key = excerpt.casefold()
            if key not in seen:
                seen.add(key)
                out.append({"needle": needle, "context": excerpt})
            start = idx + max(1, len(needle))
    return out


def inspect_pdf(path: Path) -> dict[str, object]:
    reader = PdfReader(str(path))
    pages: list[dict[str, object]] = []
    full_text_parts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        full_text_parts.append(text)
        if not relevant(text):
            continue
        page_contexts = contexts(
            text,
            (
                "17 April 2024",
                "PMHMETD",
                "right issue",
                "Ex-Right",
                "Ex Right",
                "Pasar Reguler",
                "Regular Market",
            ),
            radius=900,
        )
        if page_contexts:
            pages.append({"page": index, "contexts": page_contexts})

    full = normalize(" ".join(full_text_parts))
    low = full.casefold()
    markers = {
        token: (token.casefold() in low)
        for token in (
            "17 April 2024",
            "16 April 2024",
            "18 April 2024",
            "19 April 2024",
            "22 April 2024",
            "6 Mei 2024",
            "178",
            "75",
            "PMHMETD",
            "Pasar Reguler",
            "Pasar Negosiasi",
            "Regular Market",
            "Negotiated Market",
            "Ex-Right",
            "Ex Right",
        )
    }
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "pages": len(reader.pages),
        "markers": markers,
        "relevant_pages": pages,
    }


def find_target(root: Path, target_sha256: str = TARGET_SHA256) -> Path:
    candidates = sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.stat().st_size > 1_000_000
    )
    for path in candidates:
        if sha256_file(path) == target_sha256:
            return path
    raise RuntimeError(
        f"FREN_SAVED_2024_ANNUAL_REPORT_NOT_FOUND:{target_sha256}:scanned={len(candidates)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.root.is_dir():
        raise RuntimeError(f"FREN_FORENSIC_ROOT_MISSING:{args.root}")
    target = find_target(args.root)
    result = inspect_pdf(target)
    rendered = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
